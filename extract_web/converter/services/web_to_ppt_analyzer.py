# -*- coding: utf-8 -*-
"""
网页内容到PPT分析器

使用AI智能分析网页内容，生成PPT结构
"""

import json
import logging
from typing import Dict, List, Optional
from http import HTTPStatus
import dashscope
from utils.config_manager import config

logger = logging.getLogger(__name__)


class WebToPPTAnalyzer:
    """网页内容到PPT分析器"""
    
    def __init__(self, model: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            model: AI模型名称，默认从配置加载
        """
        if model is None:
            self.model = config.get("ai_document_analysis.model", "qwen-max")
            self.temperature = config.get("ai_document_analysis.temperature", 0.1)
            self.max_tokens = config.get("ai_document_analysis.max_tokens", 4000)
        else:
            self.model = model
            self.temperature = 0.1
            self.max_tokens = 4000
        
        logger.info(f"初始化WebToPPTAnalyzer: model={self.model}")
    
    def analyze_content(self, article: Dict) -> Dict:
        """
        分析文章内容，生成PPT结构
        
        Args:
            article: 文章信息字典，包含：
                - title: 标题
                - subtitle: 副标题
                - author: 作者
                - publish_time: 发布时间
                - content: 正文内容
                - sections: 章节列表
                
        Returns:
            PPT结构字典：
            {
                'cover': {首页信息},
                'slides': [幻灯片列表]
            }
        """
        logger.info(f"开始分析文章内容: {article.get('title')}")
        
        try:
            # 构建提示词
            prompt = self._build_prompt(article)
            
            # 调用AI分析
            try:
                response = dashscope.Generation.call(
                    model=self.model,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    result_format='message'
                )
            except Exception as api_error:
                error_msg = str(api_error)
                if "500" in error_msg:
                    raise Exception(f"AI服务暂时不可用（500错误），请稍后重试。")
                elif "timeout" in error_msg.lower():
                    raise Exception(f"AI服务响应超时，请稍后重试。")
                else:
                    raise Exception(f"AI服务调用失败: {error_msg}")
            
            if response.status_code != HTTPStatus.OK:
                if response.status_code == 500:
                    raise Exception(f"AI服务暂时不可用（500错误），请稍后重试。")
                else:
                    raise Exception(f"AI调用失败（状态码{response.status_code}）: {response.message}")
            
            # 记录Token使用情况
            usage = response.usage
            input_tokens = usage.input_tokens if usage else 0
            output_tokens = usage.output_tokens if usage else 0
            total_tokens = input_tokens + output_tokens
            
            # 解析AI返回的结果
            ai_result = response.output.choices[0].message.content
            logger.info(f"AI返回结果长度: {len(ai_result)}，Token使用: Input={input_tokens}, Output={output_tokens}, Total={total_tokens}")
            
            # 解析JSON结构
            ppt_structure = self._parse_ai_result(ai_result, article)
            
            # 添加Token统计信息
            ppt_structure["token_usage"] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
            
            logger.info(f"分析完成: 生成{len(ppt_structure['slides'])}页幻灯片")
            return ppt_structure
            
        except Exception as e:
            logger.error(f"分析文章内容失败: {e}", exc_info=True)
            # 返回基础结构
            return self._create_fallback_structure(article)
    
    def _build_prompt(self, article: Dict) -> str:
        """
        构建AI提示词
        
        Args:
            article: 文章信息
            
        Returns:
            提示词字符串
        """
        sections_text = ""
        if article.get('sections'):
            for i, section in enumerate(article['sections'], 1):
                # 取更多内容，确保AI能看到实质性内容
                # 如果内容太少，说明提取不完整
                content = section.get('content', [])
                if len(content) < 3:
                    # 内容太少，可能是提取问题，使用全部内容
                    content_preview = '\n'.join(content)
                else:
                    # 取前10段，确保覆盖关键信息
                    content_preview = '\n'.join(content[:10])
                
                sections_text += f"\n## {i}. {section['title']}\n{content_preview}\n"
        
        prompt = f"""
你是一个专业的PPT内容策划师。请分析以下文章内容，为其设计一个专业的PPT演示文稿结构。

文章信息：
标题：{article.get('title', '未知标题')}
作者：{article.get('author', '未知作者')}
发布时间：{article.get('publish_time', '')}

文章共有 {len(article.get('sections', []))} 个章节：
{sections_text}

请按照以下要求生成PPT结构：

1. **首页（封面页）**：
   - 主标题：使用文章标题
   - 副标题：提炼文章的核心主题（10-20字）
   - 作者：{article.get('author', '未知作者')}
   - 日期：{article.get('publish_time', '')}

2. **内容页**：
   - **必须覆盖所有章节**，为每个章节生成一页PPT
   - 每个章节对应一页幻灯片，包含：
     * 标题：章节标题
     * 要点列表：提炼章节核心内容，**每个要点必须精炼简洁**
   - **字数限制要求**（严格遵守）：
     * 每个要点：**不超过25字**（用于卡片/流程图布局）
     * 如果是对比/列表布局：每个要点不超过40字
     * 保留[图片]标记和缩进格式
   - **精炼原则**：
     * 提取核心观点，去除冗余描述
     * 使用简洁的短句，避免长句
     * 保留关键术语和数据
     * 如果原文很长，提炼成多个短要点

3. **格式保留原则**：
   - ✅ 保留缩进：如果原文有"  - "开头的行，必须保留
   - ✅ 保留[图片]标记：如果原文有"[图片]XXX"，必须保留
   - ✅ 精炼内容：将长句提炼成25字以内的短句
   - ❌ 禁止冗长：不要保留冗长的描述性文字
   - ❌ 禁止超长：单个要点不得超过25字（卡片/流程图）或40字（列表）

**精炼示例**：
原文："本章从开发一个简单的 Agent 开始，介绍了标准的智能体开发流程以及业内主流的智能体开发范式，并围绕工作流模式、对话模式进行展开。"
精炼后："介绍Agent开发流程和主流范式"（15字）

原文："随后，介绍了业内讨论较多的多智能体、A2A反馈，以及一些实践我们认为多智能体是智能体发展的必然形态。"
精炼后："多智能体与A2A反馈实践"（12字）

请以JSON格式返回，格式如下：
{{
  "cover": {{
    "title": "主标题",
    "subtitle": "副标题",
    "author": "作者",
    "date": "日期"
  }},
  "slides": [
    {{
      "title": "页面标题",
      "points": ["精炼要点1（≤25字）", "精炼要点2（≤25字）", "精炼要点3（≤25字）"]
    }}
  ]
}}

注意：
- 只返回JSON，不要包含markdown代码块标记
- 确保JSON格式正确
- 必须为所有 {len(article.get('sections', []))} 个章节生成对应的幻灯片
- **不要生成summary字段**，只需要title和points
- 要点必须是具体知识，不能是空泛的描述或总结
"""
        return prompt
    
    def _parse_ai_result(self, ai_result: str, article: Dict) -> Dict:
        """
        解析AI返回的结果
        
        Args:
            ai_result: AI返回的文本
            article: 原始文章信息
            
        Returns:
            PPT结构字典
        """
        try:
            # 尝试提取JSON
            # 移除可能的markdown代码块标记
            ai_result = ai_result.strip()
            if ai_result.startswith('```'):
                ai_result = ai_result.split('```')[1]
                if ai_result.startswith('json'):
                    ai_result = ai_result[4:]
            
            # 解析JSON
            ppt_data = json.loads(ai_result)
            
            # 验证结构
            if 'cover' not in ppt_data or 'slides' not in ppt_data:
                raise ValueError("AI返回的JSON缺少必要字段")
            
            # 补充缺失的封面信息
            if 'title' not in ppt_data['cover']:
                ppt_data['cover']['title'] = article.get('title', '未知标题')
            if 'author' not in ppt_data['cover']:
                ppt_data['cover']['author'] = article.get('author', '')
            if 'date' not in ppt_data['cover']:
                ppt_data['cover']['date'] = article.get('publish_time', '')
            
            return ppt_data
            
        except Exception as e:
            logger.error(f"解析AI结果失败: {e}", exc_info=True)
            logger.debug(f"AI原始返回: {ai_result[:500]}")
            # 返回备用结构
            return self._create_fallback_structure(article)
    
    def _create_fallback_structure(self, article: Dict) -> Dict:
        """
        创建备用PPT结构（当AI分析失败时）
        
        Args:
            article: 文章信息
            
        Returns:
            基础PPT结构
        """
        logger.info("使用备用PPT结构生成器")
        
        # 封面页
        cover = {
            'title': article.get('title', '未知标题'),
            'subtitle': article.get('subtitle', ''),
            'author': article.get('author', ''),
            'date': article.get('publish_time', '')
        }
        
        # 内容页
        slides = []
        
        # 从章节生成幻灯片
        sections = article.get('sections', [])
        for section in sections:  # 不限制页数
            slide = {
                'title': section['title'],
                'points': section.get('content', []),  # 直接使用content，保留[图片]标记和缩进
                'summary': ''
            }
            slides.append(slide)
        
        # 如果没有章节，从正文创建一页
        if not slides:
            slides.append({
                'title': '内容概述',
                'points': [
                    article.get('content', '')[:100] + '...'
                ],
                'summary': ''
            })
        
        return {
            'cover': cover,
            'slides': slides
        }
