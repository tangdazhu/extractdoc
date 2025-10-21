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
            response = dashscope.Generation.call(
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                result_format='message'
            )
            
            if response.status_code != HTTPStatus.OK:
                raise Exception(f"AI调用失败: {response.message}")
            
            # 解析AI返回的结果
            ai_result = response.output.choices[0].message.content
            logger.info(f"AI返回结果长度: {len(ai_result)}")
            
            # 解析JSON结构
            ppt_structure = self._parse_ai_result(ai_result, article)
            
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
     * 要点列表：从章节内容中提取3-7个核心知识点（每个要点保留原文精华，15-50字）
   - **严格禁止**：不要生成"总结"或"概括性语句"，只提取具体知识点
   - **重要**：要点必须是可直接学习的知识，不能是"介绍了XX"、"阐述了XX"等描述

3. **要点提取原则**（参考原文结构）：
   - ✅ 提取具体列表：如"上下文工程3个核心组件：外部知识库动态供给、长短期记忆系统、运行时上下文管理"
   - ✅ 保留原文表述：如"外部知识库动态供给：为解决LLM知识陈旧和领域知识缺乏的问题"
   - ✅ 提取定义和特点：保留关键术语的准确定义和核心特征
   - ❌ 禁止元描述：不要写"介绍了"、"讨论了"、"阐述了"等
   - ❌ 禁止总结语句：不要写"通过XX提升XX效果"等空话

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
      "points": ["知识点1（保留原文精华）", "知识点2", "知识点3"]
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
        for section in sections[:8]:  # 最多8页
            slide = {
                'title': section['title'],
                'points': [],
                'summary': ''
            }
            
            # 提取要点（取前5段作为要点）
            for content in section['content'][:5]:
                # 简化内容
                point = content[:50] + ('...' if len(content) > 50 else '')
                slide['points'].append(point)
            
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
