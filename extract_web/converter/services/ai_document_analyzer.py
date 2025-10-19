# -*- coding: utf-8 -*-
"""
AI驱动的文档分析模块

负责使用AI理解文档结构和内容,替代固定规则判断
"""

import json
import logging
from typing import Dict, List, Optional

import dashscope
from dashscope import Generation

logger = logging.getLogger("converter")


class AIDocumentAnalyzer:
    """AI驱动的文档结构分析器"""

    def __init__(self, model: str = "qwen-max"):
        """
        初始化AI文档分析器

        Args:
            model: AI模型名称
        """
        self.model = model

    def analyze_document_structure(
        self, multimodal_data: dict, request_id: str
    ) -> dict:
        """
        分析文档整体结构

        Args:
            multimodal_data: 多模态提取的数据
            request_id: 请求ID

        Returns:
            文档结构分析结果
        """
        logger.info("开始AI文档结构分析,RequestID=%s", request_id)

        # 1. 构建文档概览
        overview = self._build_document_overview(multimodal_data)

        # 2. 构建AI提示词
        prompt = self._build_structure_analysis_prompt(overview)

        # 3. 调用AI分析
        try:
            response = self._call_ai(prompt, request_id)

            # 4. 解析AI返回的JSON - 增强提取
            response_text = response.strip()

            # 移除markdown代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 提取JSON对象(处理AI返回额外说明的情况)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx : end_idx + 1]
                structure = json.loads(json_text)
                logger.info(
                    "AI文档结构分析完成,识别标题页=%s,内容页=%d个",
                    structure.get("title_page", {}).get("page_number"),
                    len(structure.get("content_pages", [])),
                )
                return structure
            else:
                raise ValueError("未找到有效的JSON对象")

        except json.JSONDecodeError as e:
            logger.error(
                "AI返回JSON解析失败: %s,响应内容: %s",
                e,
                response[:500] if "response" in locals() else "N/A",
            )
            return self._get_default_structure(multimodal_data)
        except Exception as e:
            logger.error("AI文档结构分析失败: %s", e, exc_info=True)
            return self._get_default_structure(multimodal_data)

    def analyze_page_content(
        self,
        page_num: int,
        page_text: str,
        page_tables: list,
        page_images: list,
        request_id: str,
    ) -> dict:
        """
        分析单个页面的内容

        Args:
            page_num: 页码
            page_text: 页面文本
            page_tables: 页面表格列表
            page_images: 页面图片列表
            request_id: 请求ID

        Returns:
            页面内容分析结果
        """
        logger.debug("分析第%d页内容,RequestID=%s", page_num, request_id)

        # 1. 构建页面内容摘要
        content_summary = {
            "page_num": page_num,
            "text": page_text[:1000] if page_text else "",  # 前1000字
            "text_length": len(page_text) if page_text else 0,
            "tables": [self._summarize_table(t) for t in page_tables],
            "images": [self._summarize_image(i) for i in page_images],
        }

        # 2. 构建AI提示词
        prompt = self._build_content_analysis_prompt(content_summary)

        # 3. 调用AI分析
        try:
            response = self._call_ai(prompt, request_id)

            # 4. 解析结果 - 增强JSON提取
            response_text = response.strip()

            # 移除markdown代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 尝试提取JSON对象(处理AI返回额外说明的情况)
            # 查找第一个{和最后一个}
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx : end_idx + 1]
                analysis = json.loads(json_text)
                logger.debug(
                    "第%d页分析完成,标题=%s,布局=%s",
                    page_num,
                    analysis.get("title"),
                    analysis.get("suggested_layout"),
                )
                return analysis
            else:
                raise ValueError("未找到有效的JSON对象")

        except Exception as e:
            logger.error("第%d页内容分析失败: %s", page_num, e)
            # 返回默认分析
            return self._get_default_page_analysis(
                page_num, page_text, page_tables, page_images
            )

    def _build_document_overview(self, data: dict) -> dict:
        """构建文档概览信息"""
        pages_summary = []

        for page_data in data.get("pages", []):
            page_num = page_data["page"]
            text = page_data.get("text", "")

            # 获取该页的表格和图片
            page_tables = [t for t in data.get("tables", []) if t["page"] == page_num]
            page_images = [i for i in data.get("images", []) if i["page"] == page_num]

            pages_summary.append(
                {
                    "page": page_num,
                    "text_preview": text[:200] if text else "",  # 前200字
                    "text_length": len(text),
                    "table_count": len(page_tables),
                    "table_info": [
                        f"{len(t['data'])}行x{len(t['data'][0]) if t['data'] else 0}列"
                        for t in page_tables
                    ],
                    "image_count": len(page_images),
                    "image_sizes": [f"{i['width']}x{i['height']}" for i in page_images],
                }
            )

        return {
            "total_pages": len(data.get("pages", [])),
            "total_tables": len(data.get("tables", [])),
            "total_images": len(data.get("images", [])),
            "pages_summary": pages_summary,
        }

    def _build_structure_analysis_prompt(self, overview: dict) -> str:
        """构建文档结构分析提示词"""

        pages_desc = []
        for page in overview["pages_summary"]:
            desc = f"第{page['page']}页:\n"
            desc += f"  文本长度: {page['text_length']}字\n"
            desc += f"  文本预览: \"{page['text_preview']}\"\n"
            if page["table_count"] > 0:
                desc += f"  表格: {page['table_count']}个 ({', '.join(page['table_info'])})\n"
            if page["image_count"] > 0:
                desc += f"  图片: {page['image_count']}张 ({', '.join(page['image_sizes'])})\n"
            pages_desc.append(desc)

        prompt = f"""你是一个专业的文档结构分析专家。请分析以下文档的结构:

【文档概览】
- 总页数: {overview['total_pages']}
- 包含表格: {overview['total_tables']}个
- 包含图片: {overview['total_images']}张

【各页内容摘要】
{chr(10).join(pages_desc)}

【分析任务】
1. 哪一页是标题页? 为什么?
2. 标题页包含哪些元素? (标题/副标题/元数据表等)
3. 每一页的主要内容类型? (标题页/内容页/图表页)
4. **表格分类** - 分析每个表格的用途和位置:
   - **元数据表**: 包含文档元信息(作者/版本/日期/团队等),通常是键值对形式,列数较少
   - **内容表**: 包含正文数据(更新记录/统计数据/对比信息等),通常是多列多行的详细数据
   - **判断依据**: 
     * 表格内容(是否包含Team/Version/Date等元信息关键词)
     * 表格位置(标题页的表格更可能是元数据表)
     * 表格大小(元数据表通常较小,内容表通常较大)
   - **重要**: 根据实际内容判断,不要假设元数据表一定在第1页或一定是某个列数
5. 哪些图片可能是背景装饰? (全屏/重复/装饰性)
6. 建议的PPT结构是什么?

【输出格式】
必须返回严格的JSON格式,不要有任何额外说明:
{{
  "document_type": "<从内容推断文档类型,如技术白皮书/产品手册/研究报告等>",
  "title_page": {{
    "page_number": <标题页页码>,
    "elements": {{
      "title": "<从文本提取的主标题>",
      "subtitle": "<从文本提取的副标题,如果没有则为空字符串>",
      "metadata_table": {{
        "page": <元数据表所在页码,如果没有元数据表则省略此字段>,
        "purpose": "<从表格内容推断的用途>",
        "should_include": <true/false,判断是否应该包含在标题页>,
        "reason": "<为什么应该/不应该包含的原因>"
      }}
    }}
  }},
  "content_pages": [
    {{
      "page_number": 2,
      "page_type": "table_page",
      "main_topic": "更新记录",
      "importance": "high"
    }}
  ],
  "background_images": [
    {{
      "pages": [1, 2, 3],
      "reason": "全屏背景图,在多页重复",
      "should_filter": true
    }}
  ]
}}
"""
        return prompt

    def _build_content_analysis_prompt(self, content_summary: dict) -> str:
        """构建页面内容分析提示词"""

        page_num = content_summary["page_num"]
        text = content_summary["text"]
        tables_desc = (
            ", ".join(content_summary["tables"]) if content_summary["tables"] else "无"
        )
        images_desc = (
            ", ".join(content_summary["images"]) if content_summary["images"] else "无"
        )

        prompt = f"""你是一个专业的内容分析专家。请分析第{page_num}页的内容:

【页面文本】
{text}

【页面表格】
{tables_desc}

【页面图片】
{images_desc}

【分析任务】
1. 这一页的核心主题是什么?
2. 页面标题应该是什么? 
   - 从文本中找到最显眼、最大字号的标题文字
   - 忽略页眉页脚(如"Proprietary and Confidential"、页码等)
   - 如果文本开头有明显的标题(如"更新记录"、"Content"、"Background"等),使用它
   - 不要使用页眉页脚或页码作为标题
3. 文本内容是否需要重新组织?
   - 检查文本是否因PDF布局导致顺序混乱
   - **特别注意**:如果列表项格式为"• Encoder Bert 架构",这是错误的
   - 正确格式应该是:"• Encoder 架构:... 典型模型如 Bert"
   - 如果发现此类问题,在 formatted_content 字段中提供重新组织后的文本
   - **重要**:重新组织时必须保留所有原始内容,包括标题、段落、列表项等,只调整顺序,不要删除任何内容
   - 如果文本顺序正常,不需要提供 formatted_content 字段
4. 如果有表格,表格的作用是什么? (元数据表/数据表/内容表)
5. 如果有图片,图片是否应该在PPT中显示? **请基于以下原则智能判断**:
   
   **判断原则**:
   a) **尺寸判断**:
      - 1920x1080 全屏图片 → 通常是装饰性背景,should_keep=false
      - 1000x700 ~ 1500x1200 中等尺寸图片 → 通常是内容图(架构图/流程图),需进一步判断
      - 小于 500x500 的图片 → 通常是图标/装饰,should_keep=false
   
   b) **内容相关性判断**(最重要):
      - 图片是否与页面主题直接相关?
      - 页面文本是否在描述/解释图片内容?
      - 图片是否是页面核心内容的可视化表达?
   
   c) **页面类型判断**:
      - 如果页面是"架构介绍"、"模型分类"、"流程说明"等,图片很可能是核心内容
      - 如果页面是"基础知识"、"实践案例"、"应用场景"等文字说明,图片可能只是装饰
      - 如果页面主要是表格或文本列表,图片通常不是必需的
   
   **判断流程**:
   1. 先判断尺寸(过滤全屏背景和小图标)
   2. 再判断内容相关性(图片是否与页面主题匹配)
   3. 最后综合判断(是否应该在PPT中显示)
   
6. 这一页的重要程度? (high/medium/low)
7. 建议的PPT布局类型? **请根据以下规则严格判断**:
   - `title_and_table`: 页面主要内容是表格
   - `title_and_image`: 页面主要内容是图片(架构图/流程图/示意图),且图片与主题直接相关
   - `title_and_text`: 页面主要内容是文字说明/列表

【关键规则 - 必须严格遵守】
- 标题必须从文本中提取,不要生成新标题
- 忽略"Proprietary and Confidential"、页码等页眉页脚信息

- **图片判断要点**(最重要): 
  * 1920x1080 的全屏图片 → 一律 should_keep=false (装饰性背景)
  * 其他尺寸图片 → 判断内容相关性:
    - 如果页面文本在描述/解释图片内容 → should_keep=true
    - 如果图片是页面核心内容的可视化 → should_keep=true  
    - 如果图片与页面主题无直接关系 → should_keep=false
  
- **布局判断要点**:
  * 如果有 should_keep=true 的图片,且图片是页面核心内容 → suggested_layout="title_and_image"
  * 如果有图片但 should_keep=false,或图片只是装饰 → suggested_layout="title_and_text"
  * 布局类型必须与 should_keep 判断一致

- **判断示例**:
  * 页面标题"Background",主题"模型分类与架构",有架构图 → 图片 should_keep=true, 布局 title_and_image
  * 页面标题"大语言模型基础及实践案例",主题"知识介绍",有架构图 → 图片 should_keep=false, 布局 title_and_text
  * **关键**:如果页面标题包含"基础"、"实践"、"案例"等词,通常是文字说明页,图片只是装饰 → should_keep=false
  
- 不要因为"多页重复"就过滤内容图,只过滤装饰性背景图

【文本重组示例】
如果原始文本是:
```
Transform
模型分类
• Encoder Bert
架构：不适合做生成...典型模型如 。
• Decoder LLM GPT Llama
架构：适合生成任务...
```

正确的 formatted_content 应该是:
```
Transform 模型分类
• Encoder 架构：不适合做生成，在任务理解上性价比较高，如句子分类、命名实体识别等。典型模型如 Bert。
• Decoder 架构：适合生成任务，大模型 LLM 的主流结构，典型模型有 GPT、Llama 等。
• Encoder-Decoder 架构：理论上结合了 GPT 和 Bert 的优点，训练成本很高，典型模型是 T5、BART。
```

注意:
1. 保留"Transform 模型分类"标题
2. 将关键词(Bert, LLM, GPT, Llama)移到正确位置
3. 保持完整的列表结构

【输出格式】
必须返回严格的JSON格式,不要有任何额外说明:
{{
  "page_number": {page_num},
  "title": "从文本中提取的真实标题(不是页眉页脚)",
  "theme": "页面核心主题",
  "importance": "high",
  "suggested_layout": "title_and_table",
  "formatted_content": "重新组织后的文本内容(可选,仅当文本顺序混乱时提供,必须保留所有原始内容)",
  "elements": [
    {{
      "type": "table",
      "purpose": "版本历史",
      "should_keep": true,
      "reason": "包含重要信息"
    }},
    {{
      "type": "image",
      "size": "1263x1153",
      "purpose": "架构图",
      "should_keep": true,
      "reason": "内容图,尺寸符合保留规则"
    }},
    {{
      "type": "image",
      "size": "1246x707",
      "purpose": "流程图",
      "should_keep": true,
      "reason": "内容图,尺寸符合保留规则"
    }},
    {{
      "type": "image",
      "size": "1920x1080",
      "purpose": "背景装饰",
      "should_keep": false,
      "reason": "全屏背景图,必须过滤"
    }}
  ]
}}
"""
        return prompt

    def _call_ai(self, prompt: str, request_id: str) -> str:
        """调用AI模型"""
        messages = [{"role": "user", "content": prompt}]

        response = Generation.call(
            model=self.model,
            messages=messages,
            result_format="message",
            temperature=0.1,
            max_tokens=4000,
        )

        if response.status_code == 200:
            content = response.output.choices[0].message.content
            logger.debug(
                "AI调用成功,RequestID=%s,返回长度=%d", request_id, len(content)
            )
            return content
        else:
            error_msg = f"AI调用失败: {response.code} - {response.message}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _summarize_table(self, table_data: dict) -> str:
        """总结表格信息"""
        data = table_data.get("data", [])
        if not data:
            return "空表格"
        rows = len(data)
        cols = len(data[0]) if data else 0
        return f"{rows}行x{cols}列表格"

    def _summarize_image(self, image_data: dict) -> str:
        """总结图片信息"""
        width = image_data.get("width", 0)
        height = image_data.get("height", 0)
        return f"{width}x{height}图片"

    def _get_default_structure(self, multimodal_data: dict) -> dict:
        """获取默认文档结构(AI失败时的后备方案)"""
        pages = multimodal_data.get("pages", [])

        return {
            "document_type": "未知文档",
            "title_page": {
                "page_number": 1,
                "elements": {"title": "文档标题", "subtitle": "AI智能生成"},
            },
            "content_pages": [
                {
                    "page_number": i,
                    "page_type": "content_page",
                    "main_topic": f"第{i}页",
                    "importance": "medium",
                }
                for i in range(2, len(pages) + 1)
            ],
            "background_images": [],
        }

    def _get_default_page_analysis(
        self, page_num: int, page_text: str, page_tables: list, page_images: list
    ) -> dict:
        """获取默认页面分析(AI失败时的后备方案)"""

        # 尝试从文本提取标题
        title = f"第{page_num}页"
        if page_text:
            lines = [line.strip() for line in page_text.split("\n") if line.strip()]
            if lines:
                title = lines[0][:50]  # 使用第一行作为标题

        # 判断布局类型
        has_table = len(page_tables) > 0
        has_image = len(page_images) > 0

        if has_table and has_image:
            layout = "title_table_image"
        elif has_table:
            layout = "title_and_table"
        elif has_image:
            layout = "title_and_image"
        else:
            layout = "title_and_text"

        # 构建元素列表
        elements = []
        for table in page_tables:
            elements.append(
                {
                    "type": "table",
                    "purpose": "数据表",
                    "should_keep": True,
                    "reason": "包含表格数据",
                }
            )

        for image in page_images:
            # 简单判断是否为背景图
            width = image.get("width", 0)
            height = image.get("height", 0)
            area = width * height
            is_background = area > 1500000

            elements.append(
                {
                    "type": "image",
                    "size": f"{width}x{height}",
                    "purpose": "背景装饰" if is_background else "内容图",
                    "should_keep": not is_background,
                    "reason": "全屏背景图" if is_background else "内容图片",
                }
            )

        return {
            "page_number": page_num,
            "title": title,
            "theme": "页面内容",
            "importance": "medium",
            "suggested_layout": layout,
            "elements": elements,
        }
