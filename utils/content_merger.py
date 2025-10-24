# -*- coding: utf-8 -*-
"""
内容合并工具

用于合并多个URL提取的内容，实现去重与智能合并
"""

import hashlib
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Set, Optional

from utils.config_manager import config

logger = logging.getLogger(__name__)


class ContentMerger:
    """内容合并器 - 合并多个URL的提取内容"""

    def __init__(self, title_similarity_threshold: Optional[float] = None):
        """
        初始化内容合并器

        Args:
            title_similarity_threshold: 标题相似度阈值（0-1），默认从配置读取
        """
        if title_similarity_threshold is None:
            self.threshold = config.get("text_processing.title_similarity_threshold", 0.85)
        else:
            self.threshold = title_similarity_threshold

        logger.info(f"初始化ContentMerger: 标题相似度阈值={self.threshold}")

    def merge(self, contents: List[Dict]) -> Dict:
        """
        合并多个内容，去重

        Args:
            contents: 内容列表，每个元素包含 url, title, sections, images 等字段

        Returns:
            合并后的内容字典
        """
        if not contents:
            raise ValueError("内容列表不能为空")

        if len(contents) == 1:
            logger.info("只有一个来源，直接返回")
            result = contents[0].copy()
            result['source_urls'] = [result.get('source_url', '')]
            result['merge_time'] = datetime.now().isoformat()
            return result

        logger.info(f"开始合并{len(contents)}个来源的内容")

        merged = {
            'source_urls': [c.get('source_url', '') for c in contents],
            'merged_title': self._generate_merged_title(contents),
            'sections': [],
            'images': [],
            'merge_time': datetime.now().isoformat()
        }

        # 合并章节（去重）
        merged['sections'] = self._merge_sections(contents)

        # 合并图片（URL去重）
        merged['images'] = self._merge_images(contents)

        logger.info(f"合并完成: {len(merged['sections'])}个章节, {len(merged['images'])}张图片")
        return merged

    def _generate_merged_title(self, contents: List[Dict]) -> str:
        """
        生成合并后的标题

        Args:
            contents: 内容列表

        Returns:
            合并标题
        """
        titles = [c.get('title', '') for c in contents if c.get('title')]

        if not titles:
            return "多来源综合分析"

        # 如果所有标题相似，使用第一个
        if len(titles) > 1:
            first_title = titles[0]
            all_similar = all(
                SequenceMatcher(None, first_title, t).ratio() >= self.threshold
                for t in titles[1:]
            )
            if all_similar:
                return first_title

        # 否则生成综合标题
        return f"综合分析（基于{len(contents)}个来源）"

    def _merge_sections(self, contents: List[Dict]) -> List[Dict]:
        """
        合并章节，去除重复

        Args:
            contents: 内容列表

        Returns:
            合并后的章节列表
        """
        seen_titles = {}  # {标题: 章节数据}
        seen_content_hashes = set()  # 内容哈希集合

        for content in contents:
            source_url = content.get('source_url', '')

            for section in content.get('sections', []):
                title = section.get('title', '')
                section_content = section.get('content', [])
                level = section.get('level', 2)

                # 查找相似标题
                similar_key = self._find_similar_title(title, seen_titles.keys())

                if similar_key:
                    # 合并到现有章节
                    logger.debug(f"标题相似，合并: '{title}' -> '{similar_key}'")

                    # 去重添加内容
                    for item in section_content:
                        item_hash = self._hash_content(item)
                        if item_hash not in seen_content_hashes:
                            seen_titles[similar_key]['content'].append(item)
                            seen_content_hashes.add(item_hash)

                    # 添加来源
                    if source_url not in seen_titles[similar_key]['sources']:
                        seen_titles[similar_key]['sources'].append(source_url)
                else:
                    # 新章节
                    unique_content = []
                    for item in section_content:
                        item_hash = self._hash_content(item)
                        if item_hash not in seen_content_hashes:
                            unique_content.append(item)
                            seen_content_hashes.add(item_hash)

                    if unique_content:  # 只添加有内容的章节
                        seen_titles[title] = {
                            'title': title,
                            'content': unique_content,
                            'sources': [source_url],
                            'level': level
                        }

        return list(seen_titles.values())

    def _merge_images(self, contents: List[Dict]) -> List:
        """
        合并图片，URL去重

        Args:
            contents: 内容列表

        Returns:
            合并后的图片列表（字符串URL列表）
        """
        seen_image_urls = set()
        merged_images = []

        for content in contents:
            for img in content.get('images', []):
                # 兼容两种格式：字符串URL 或 字典 {'url': '...'}
                if isinstance(img, str):
                    img_url = img
                elif isinstance(img, dict):
                    img_url = img.get('url', '')
                else:
                    logger.warning(f"未知的图片格式: {type(img)}")
                    continue

                if img_url and img_url not in seen_image_urls:
                    merged_images.append(img_url)  # 统一返回字符串URL
                    seen_image_urls.add(img_url)

        logger.info(f"图片去重: 原始{sum(len(c.get('images', [])) for c in contents)}张 -> 去重后{len(merged_images)}张")
        return merged_images

    def _find_similar_title(self, title: str, existing_titles: List[str]) -> Optional[str]:
        """
        查找相似标题

        Args:
            title: 待查找的标题
            existing_titles: 已存在的标题列表

        Returns:
            相似的标题，如果没有则返回None
        """
        for existing in existing_titles:
            similarity = SequenceMatcher(None, title, existing).ratio()
            if similarity >= self.threshold:
                logger.debug(f"找到相似标题: '{title}' vs '{existing}' (相似度={similarity:.2f})")
                return existing

        return None

    def _hash_content(self, content: str) -> str:
        """
        计算内容哈希

        Args:
            content: 内容字符串

        Returns:
            MD5哈希值
        """
        # 去除空白字符后计算哈希
        normalized = ''.join(content.split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
