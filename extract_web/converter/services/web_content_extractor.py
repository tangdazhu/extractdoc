# -*- coding: utf-8 -*-
"""
网页内容提取器

从URL中提取文章内容，支持微信公众号文章等
"""

import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from utils.config_manager import config

logger = logging.getLogger(__name__)


class WebContentExtractor:
    """网页内容提取器"""
    
    def __init__(self):
        """初始化提取器"""
        self.timeout = 30
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_from_url(self, url: str) -> Dict:
        """
        从URL提取文章内容
        
        Args:
            url: 文章URL
            
        Returns:
            包含文章信息的字典：
            {
                'title': 标题,
                'subtitle': 副标题,
                'author': 作者,
                'publish_time': 发布时间,
                'content': 正文内容,
                'sections': [章节列表],
                'images': [图片URL列表]
            }
        """
        logger.info(f"开始提取URL内容: {url}")
        
        try:
            # 判断URL类型
            if 'mp.weixin.qq.com' in url:
                return self._extract_weixin_article(url)
            else:
                return self._extract_generic_article(url)
        except Exception as e:
            logger.error(f"提取URL内容失败: {e}", exc_info=True)
            raise
    
    def _extract_weixin_article(self, url: str) -> Dict:
        """
        提取微信公众号文章
        
        Args:
            url: 微信文章URL
            
        Returns:
            文章信息字典
        """
        logger.info("识别为微信公众号文章")
        
        # 获取网页内容
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.encoding = 'utf-8'
        html = response.text
        
        # 检测是否被反爬虫拦截
        if '环境异常' in html or '完成验证' in html:
            logger.warning("检测到微信反爬虫验证页面，请尝试在浏览器中打开URL或使用其他方式")
            raise ValueError("微信文章需要验证，无法直接访问。建议：1) 在浏览器中打开并复制内容 2) 使用微信文章采集工具")
        
        # 解析HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取标题
        title_elem = soup.find('h1', class_='rich_media_title') or soup.find('h1', id='activity-name')
        title = title_elem.get_text(strip=True) if title_elem else "未知标题"
        
        # 提取作者（尝试多个选择器）
        author = "未知作者"
        author_selectors = [
            ('a', {'class': 'rich_media_meta_link'}),
            ('span', {'class': 'rich_media_meta rich_media_meta_text'}),
            ('div', {'id': 'js_name'}),
            ('strong', {'class': 'profile_nickname'}),
        ]
        for tag, attrs in author_selectors:
            author_elem = soup.find(tag, attrs)
            if author_elem:
                author = author_elem.get_text(strip=True)
                if author and author != '未知作者':
                    break
        
        # 从meta标签提取作者
        if author == "未知作者":
            meta_author = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'og:article:author'})
            if meta_author:
                author = meta_author.get('content', '未知作者')
        
        # 提取发布时间（尝试多个选择器）
        publish_time = ""
        time_selectors = [
            ('em', {'id': 'publish_time'}),
            ('span', {'class': 'rich_media_meta rich_media_meta_text'}),
            ('div', {'class': 'publish_time'}),
        ]
        for tag, attrs in time_selectors:
            time_elem = soup.find(tag, attrs)
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                if time_text and any(char.isdigit() for char in time_text):
                    publish_time = time_text
                    break
        
        # 从meta标签提取时间
        if not publish_time:
            meta_time = soup.find('meta', {'property': 'og:article:published_time'}) or soup.find('meta', {'name': 'publish_time'})
            if meta_time:
                publish_time = meta_time.get('content', '')
        
        # 提取正文内容
        content_elem = soup.find('div', class_='rich_media_content')
        if not content_elem:
            raise ValueError("未找到文章正文内容")
        
        # 提取段落和标题
        sections = []
        images = []
        current_section = None
        processed_texts = set()  # 用于去重
        
        # 遍历所有元素，包括section标签内的内容
        for elem in content_elem.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'div']):
            # 提取图片
            img_tags = elem.find_all('img')
            for img in img_tags:
                img_url = img.get('data-src') or img.get('src')
                if img_url and img_url not in images:
                    images.append(img_url)
            
            # 提取文本
            text = elem.get_text(strip=True)
            if not text or len(text) < 2:
                continue
            
            # 去重：跳过已经处理过的文本
            if text in processed_texts:
                continue
            processed_texts.add(text)
            
            # 判断是否为标题
            is_heading = elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            is_section_title = self._is_section_title(text)
            
            # 检查是否有特殊样式（加粗、大字体等）
            has_strong_style = False
            if elem.find('strong') or elem.find('b'):
                strong_text = elem.find('strong') or elem.find('b')
                if strong_text and len(strong_text.get_text(strip=True)) > len(text) * 0.7:
                    has_strong_style = True
            
            if is_heading or is_section_title or (has_strong_style and len(text) < 50):
                # 保存上一个章节
                if current_section and current_section['content']:
                    sections.append(current_section)
                
                # 开始新章节
                current_section = {
                    'title': text,
                    'content': [],
                    'level': int(elem.name[1]) if elem.name.startswith('h') else 2
                }
                logger.debug(f"识别到章节标题: {text} (标签={elem.name}, is_heading={is_heading}, is_section_title={is_section_title}, has_strong_style={has_strong_style})")
            else:
                # 添加到当前章节
                if current_section is None:
                    # 如果还没有章节，创建一个默认章节
                    current_section = {
                        'title': '引言',
                        'content': [],
                        'level': 2
                    }
                # 只添加有意义的段落（长度大于10）
                if len(text) > 10:
                    current_section['content'].append(text)
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        # 提取完整正文
        content = content_elem.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'title': title,
            'subtitle': '',  # 微信文章通常没有副标题
            'author': author,
            'publish_time': publish_time,
            'content': content,
            'sections': sections,
            'images': images,
            'source': 'weixin'
        }
        
        logger.info(f"提取成功: 标题={title}, 章节数={len(sections)}, 图片数={len(images)}")
        return result
    
    def _extract_generic_article(self, url: str) -> Dict:
        """
        提取通用网页文章
        
        Args:
            url: 文章URL
            
        Returns:
            文章信息字典
        """
        logger.info("使用通用提取器")
        
        # 获取网页内容
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.encoding = response.apparent_encoding
        html = response.text
        
        # 解析HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试提取标题
        title = None
        for selector in ['h1', 'title', '.article-title', '.post-title']:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        if not title:
            title = "未知标题"
        
        # 尝试提取作者
        author = "未知作者"
        for selector in ['.author', '.post-author', '[rel="author"]']:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get_text(strip=True)
                break
        
        # 尝试提取时间
        publish_time = datetime.now().strftime("%Y-%m-%d")
        for selector in ['.publish-time', '.post-date', 'time']:
            elem = soup.select_one(selector)
            if elem:
                publish_time = elem.get_text(strip=True)
                break
        
        # 提取正文（尝试多种选择器）
        content_elem = None
        for selector in ['article', '.article-content', '.post-content', '.content', 'main']:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            # 如果找不到，使用body
            content_elem = soup.find('body')
        
        # 提取段落
        sections = []
        images = []
        current_section = None
        
        for elem in content_elem.find_all(['p', 'h1', 'h2', 'h3', 'h4']):
            # 提取图片
            img_tags = elem.find_all('img')
            for img in img_tags:
                img_url = img.get('src')
                if img_url and img_url not in images:
                    # 处理相对URL
                    if img_url.startswith('/'):
                        from urllib.parse import urljoin
                        img_url = urljoin(url, img_url)
                    images.append(img_url)
            
            # 提取文本
            text = elem.get_text(strip=True)
            if not text:
                continue
            
            # 判断是否为标题
            if elem.name in ['h1', 'h2', 'h3', 'h4']:
                # 保存上一个章节
                if current_section:
                    sections.append(current_section)
                
                # 开始新章节
                current_section = {
                    'title': text,
                    'content': [],
                    'level': int(elem.name[1])
                }
            else:
                # 添加到当前章节
                if current_section is None:
                    current_section = {
                        'title': '正文',
                        'content': [],
                        'level': 2
                    }
                current_section['content'].append(text)
        
        # 添加最后一个章节
        if current_section:
            sections.append(current_section)
        
        # 提取完整正文
        content = content_elem.get_text(separator='\n', strip=True)
        
        result = {
            'url': url,
            'title': title,
            'subtitle': '',
            'author': author,
            'publish_time': publish_time,
            'content': content,
            'sections': sections,
            'images': images,
            'source': 'generic'
        }
        
        logger.info(f"提取成功: 标题={title}, 章节数={len(sections)}, 图片数={len(images)}")
        return result
    
    def _is_section_title(self, text: str) -> bool:
        """
        判断文本是否为章节标题
        
        Args:
            text: 文本内容
            
        Returns:
            是否为章节标题
        """
        # 章节标题特征：
        # 1. 较短（通常少于50个字符）
        # 2. 以数字、一、二、三等开头
        # 3. 包含"第X章"、"第X节"等
        # 4. 包含特定关键词
        
        if len(text) > 60:
            return False
        
        # 匹配模式
        patterns = [
            r'^[一二三四五六七八九十百千]+[、\.]',  # 一、二、三、
            r'^\d+[、\.]',  # 1. 2. 3.
            r'^第[一二三四五六七八九十百千\d]+[章节部分条]',  # 第一章、第1节
            r'第\s*[一二三四五六七八九十百千\d]+\s*章',  # 第 1 章（允许空格）
            r'^\([一二三四五六七八九十\d]+\)',  # (一) (1)
            r'^[\d]+\)',  # 1) 2) 3)
            r'^【.*】$',  # 【标题】
            r'^\d+\s*[、\.]',  # 1 . 2 . (允许空格)
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        # 检查是否包含标题关键词
        title_keywords = ['概述', '介绍', '背景', '定义', '特点', '优势', '挑战', '方案', '架构', '实践', '总结', '展望', '关键', '要素', '能力']
        if len(text) < 30 and any(keyword in text for keyword in title_keywords):
            return True
        
        return False
