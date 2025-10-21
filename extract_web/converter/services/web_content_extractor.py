# -*- coding: utf-8 -*-
"""
网页内容提取器

从URL中提取文章内容，支持微信公众号文章等
"""

import re
import json
import logging
import os
from typing import Dict, Optional, List
from datetime import datetime
from http import HTTPStatus
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import dashscope
from utils.config_manager import config

logger = logging.getLogger(__name__)


class WebContentExtractor:
    """网页内容提取器"""

    def __init__(self, use_ai: bool = True):
        """
        初始化提取器

        Args:
            use_ai: 是否使用AI分析HTML（默认True）
        """
        self.timeout = 30
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.use_ai = use_ai
        if use_ai:
            # 从配置加载AI参数
            self.model = config.get("ai_document_analysis.model", "qwen-max")
            self.temperature = config.get("ai_document_analysis.temperature", 0.1)
            self.max_tokens = config.get("ai_document_analysis.max_tokens", 4000)

            # 初始化OpenAI客户端（兼容dashscope）
            # 优先从dashscope模块获取API Key（已在settings.py中设置）
            api_key = dashscope.api_key or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError(
                    "DASHSCOPE_API_KEY未配置，请在config/application.yaml中设置或设置环境变量"
                )

            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            logger.info(f"AI内容提取已启用: model={self.model}")

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
            # 如果启用AI，优先使用AI提取
            if self.use_ai:
                try:
                    logger.info("使用AI分析HTML内容")
                    return self._extract_with_ai(url)
                except Exception as e:
                    logger.warning(f"AI提取失败，回退到传统方法: {e}")
                    # AI失败后回退到传统方法

            # 传统方法：判断URL类型
            if "mp.weixin.qq.com" in url:
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
        response.encoding = "utf-8"
        html = response.text

        # 检测是否被反爬虫拦截
        if "环境异常" in html or "完成验证" in html:
            logger.warning(
                "检测到微信反爬虫验证页面，请尝试在浏览器中打开URL或使用其他方式"
            )
            raise ValueError(
                "微信文章需要验证，无法直接访问。建议：1) 在浏览器中打开并复制内容 2) 使用微信文章采集工具"
            )

        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title_elem = soup.find("h1", class_="rich_media_title") or soup.find(
            "h1", id="activity-name"
        )
        title = title_elem.get_text(strip=True) if title_elem else "未知标题"

        # 提取作者（尝试多个选择器）
        author = "未知作者"
        author_selectors = [
            ("a", {"class": "rich_media_meta_link"}),
            ("span", {"class": "rich_media_meta rich_media_meta_text"}),
            ("div", {"id": "js_name"}),
            ("strong", {"class": "profile_nickname"}),
        ]
        for tag, attrs in author_selectors:
            author_elem = soup.find(tag, attrs)
            if author_elem:
                author = author_elem.get_text(strip=True)
                if author and author != "未知作者":
                    break

        # 从meta标签提取作者
        if author == "未知作者":
            meta_author = soup.find("meta", {"name": "author"}) or soup.find(
                "meta", {"property": "og:article:author"}
            )
            if meta_author:
                author = meta_author.get("content", "未知作者")

        # 提取发布时间（尝试多个选择器）
        publish_time = ""
        time_selectors = [
            ("em", {"id": "publish_time"}),
            ("span", {"class": "rich_media_meta rich_media_meta_text"}),
            ("div", {"class": "publish_time"}),
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
            meta_time = soup.find(
                "meta", {"property": "og:article:published_time"}
            ) or soup.find("meta", {"name": "publish_time"})
            if meta_time:
                publish_time = meta_time.get("content", "")

        # 提取正文内容
        content_elem = soup.find("div", class_="rich_media_content")
        if not content_elem:
            raise ValueError("未找到文章正文内容")

        # 提取段落和标题
        sections = []
        images = []
        current_section = None
        processed_texts = set()  # 用于去重

        # 遍历所有元素，包括section标签内的内容
        for elem in content_elem.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "section", "div"]
        ):
            # 提取图片
            img_tags = elem.find_all("img")
            for img in img_tags:
                img_url = img.get("data-src") or img.get("src")
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
            is_heading = elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
            is_section_title = self._is_section_title(text)

            # 检查是否有特殊样式（加粗、大字体等）
            has_strong_style = False
            if elem.find("strong") or elem.find("b"):
                strong_text = elem.find("strong") or elem.find("b")
                if (
                    strong_text
                    and len(strong_text.get_text(strip=True)) > len(text) * 0.7
                ):
                    has_strong_style = True

            if is_heading or is_section_title or (has_strong_style and len(text) < 50):
                # 保存上一个章节
                if current_section and current_section["content"]:
                    sections.append(current_section)

                # 开始新章节
                current_section = {
                    "title": text,
                    "content": [],
                    "level": int(elem.name[1]) if elem.name.startswith("h") else 2,
                }
                logger.debug(
                    f"识别到章节标题: {text} (标签={elem.name}, is_heading={is_heading}, is_section_title={is_section_title}, has_strong_style={has_strong_style})"
                )
            else:
                # 添加到当前章节
                if current_section is None:
                    # 如果还没有章节，创建一个默认章节
                    current_section = {"title": "引言", "content": [], "level": 2}
                # 只添加有意义的段落（长度大于10）
                if len(text) > 10:
                    current_section["content"].append(text)

        # 添加最后一个章节
        if current_section:
            sections.append(current_section)

        # 提取完整正文
        content = content_elem.get_text(separator="\n", strip=True)

        result = {
            "url": url,
            "title": title,
            "subtitle": "",  # 微信文章通常没有副标题
            "author": author,
            "publish_time": publish_time,
            "content": content,
            "sections": sections,
            "images": images,
            "source": "weixin",
        }

        logger.info(
            f"提取成功: 标题={title}, 章节数={len(sections)}, 图片数={len(images)}"
        )
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
        soup = BeautifulSoup(html, "html.parser")

        # 尝试提取标题
        title = None
        for selector in ["h1", "title", ".article-title", ".post-title"]:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break

        if not title:
            title = "未知标题"

        # 尝试提取作者
        author = "未知作者"
        for selector in [".author", ".post-author", '[rel="author"]']:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get_text(strip=True)
                break

        # 尝试提取时间
        publish_time = datetime.now().strftime("%Y-%m-%d")
        for selector in [".publish-time", ".post-date", "time"]:
            elem = soup.select_one(selector)
            if elem:
                publish_time = elem.get_text(strip=True)
                break

        # 提取正文（尝试多种选择器）
        content_elem = None
        for selector in [
            "article",
            ".article-content",
            ".post-content",
            ".content",
            "main",
        ]:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            # 如果找不到，使用body
            content_elem = soup.find("body")

        # 提取段落
        sections = []
        images = []
        current_section = None

        for elem in content_elem.find_all(["p", "h1", "h2", "h3", "h4"]):
            # 提取图片
            img_tags = elem.find_all("img")
            for img in img_tags:
                img_url = img.get("src")
                if img_url and img_url not in images:
                    # 处理相对URL
                    if img_url.startswith("/"):
                        from urllib.parse import urljoin

                        img_url = urljoin(url, img_url)
                    images.append(img_url)

            # 提取文本
            text = elem.get_text(strip=True)
            if not text:
                continue

            # 判断是否为标题
            if elem.name in ["h1", "h2", "h3", "h4"]:
                # 保存上一个章节
                if current_section:
                    sections.append(current_section)

                # 开始新章节
                current_section = {
                    "title": text,
                    "content": [],
                    "level": int(elem.name[1]),
                }
            else:
                # 添加到当前章节
                if current_section is None:
                    current_section = {"title": "正文", "content": [], "level": 2}
                current_section["content"].append(text)

        # 添加最后一个章节
        if current_section:
            sections.append(current_section)

        # 提取完整正文
        content = content_elem.get_text(separator="\n", strip=True)

        result = {
            "url": url,
            "title": title,
            "subtitle": "",
            "author": author,
            "publish_time": publish_time,
            "content": content,
            "sections": sections,
            "images": images,
            "source": "generic",
        }

        logger.info(
            f"提取成功: 标题={title}, 章节数={len(sections)}, 图片数={len(images)}"
        )
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
            r"^[一二三四五六七八九十百千]+[、\.]",  # 一、二、三、
            r"^\d+[、\.]",  # 1. 2. 3.
            r"^第[一二三四五六七八九十百千\d]+[章节部分条]",  # 第一章、第1节
            r"第\s*[一二三四五六七八九十百千\d]+\s*章",  # 第 1 章（允许空格）
            r"^\([一二三四五六七八九十\d]+\)",  # (一) (1)
            r"^[\d]+\)",  # 1) 2) 3)
            r"^【.*】$",  # 【标题】
            r"^\d+\s*[、\.]",  # 1 . 2 . (允许空格)
        ]

        for pattern in patterns:
            if re.match(pattern, text):
                return True

        # 检查是否包含标题关键词
        title_keywords = [
            "概述",
            "介绍",
            "背景",
            "定义",
            "特点",
            "优势",
            "挑战",
            "方案",
            "架构",
            "实践",
            "总结",
            "展望",
            "关键",
            "要素",
            "能力",
        ]
        if len(text) < 30 and any(keyword in text for keyword in title_keywords):
            return True

        return False

    def _extract_with_ai(self, url: str) -> Dict:
        """
        使用AI分析HTML并提取内容

        Args:
            url: 文章URL

        Returns:
            文章信息字典
        """
        logger.info("使用AI提取器分析网页内容")

        # 获取网页HTML
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.encoding = response.apparent_encoding or "utf-8"
        html = response.text

        # 使用BeautifulSoup清理HTML，移除script、style等无用标签
        soup = BeautifulSoup(html, "html.parser")

        # 移除无用标签
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "iframe",
                "noscript",
            ]
        ):
            tag.decompose()

        # 对于微信文章，只提取正文部分
        content_elem = None
        if "mp.weixin.qq.com" in url:
            content_elem = soup.find("div", class_="rich_media_content")
            if content_elem:
                logger.info("检测到微信文章，只提取正文内容")

        # 如果找到了正文，只用正文；否则用整个body
        if content_elem:
            cleaned_html = str(content_elem)
        else:
            body = soup.find("body")
            if body:
                cleaned_html = str(body)
            else:
                cleaned_html = str(soup)

        # 进一步清理：移除所有HTML标签，只保留文本和结构
        # 这样可以大幅减少token消耗
        text_soup = BeautifulSoup(cleaned_html, "html.parser")

        # 先提取图片（在清理文本之前）
        images = []
        for img in text_soup.find_all("img"):
            img_url = img.get("data-src") or img.get("src")
            if img_url and img_url not in images:
                # 处理相对URL
                if img_url.startswith("/"):
                    from urllib.parse import urljoin
                    img_url = urljoin(url, img_url)
                images.append(img_url)
        
        logger.info(f"提取到{len(images)}张图片")

        # 提取纯文本，但保留标题结构
        text_parts = []
        seen_texts = set()  # 用于去重

        for elem in text_soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "section"]
        ):
            text = elem.get_text(strip=True)
            if not text or len(text) < 5:  # 过滤太短的文本
                continue

            # 去重：避免嵌套元素导致的重复
            # 但对于标题，即使重复也保留（因为可能是重要的章节标题）
            is_heading = elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]

            if is_heading:
                text_parts.append(f"[标题] {text}")
            elif text not in seen_texts:
                text_parts.append(text)
                seen_texts.add(text)

        cleaned_html = "\n\n".join(text_parts)  # 使用双换行分隔，更清晰

        logger.info(f"提取的内容长度: {len(cleaned_html)}字符")

        # 分批处理：将文章按段落分组，避免单个message超过30720字符
        # 策略：每批最多25000字符（留5000给提示词）
        text_parts_list = cleaned_html.split("\n\n")
        batches = []
        current_batch = []
        current_length = 0
        max_batch_length = 25000

        for part in text_parts_list:
            part_length = len(part) + 2  # +2 for \n\n
            if current_length + part_length > max_batch_length and current_batch:
                batches.append("\n\n".join(current_batch))
                current_batch = [part]
                current_length = part_length
            else:
                current_batch.append(part)
                current_length += part_length

        if current_batch:
            batches.append("\n\n".join(current_batch))

        logger.info(f"文章分为{len(batches)}个批次处理")

        # 构建完整的AI提示词（不简化）
        system_prompt = """你是技术知识提取专家。

【核心规则 - 必须100%遵守】
1. 原文说"N个要素"，必须提取N个（提取后数一遍）
2. 有父子关系必须缩进（子项前加"  - "）
3. 有架构图必须在content中添加"[图片]架构图"
4. 禁止写"介绍了"等废话

【输出格式】
{"title":"","sections":[{"title":"第X章","content":["知识点1","  - 子知识点1","[图片]架构图"],"level":2}],"images":[]}

【示例1 - 完整列表】
原文："AI应用11个关键要素包括：大模型、提示词、RAG..."
✅ 正确：content中必须有11个要素，每个独立一行
❌ 错误：只提取8个

【示例2 - 层次结构】
原文："FlowAgent包含SequentialAgent、ParallelAgent、LoopAgent"
✅ 正确：
- **FlowAgent**：包含多个ReactAgent
  - SequentialAgent：串行执行
  - ParallelAgent：并行执行
  - LoopAgent：循环执行
❌ 错误：平铺列出，无缩进

【示例3 - 图片标记】
原文：有架构图
✅ 正确：content中添加"[图片]AI原生应用架构图"
❌ 错误：不添加标记

【数量验证】
原文说"11个要素"，提取后必须有11个，不能是8个或10个"""

        # 分批调用AI，收集结果
        all_sections = []
        article_title = ""
        article_author = ""

        for i, batch_content in enumerate(batches):
            # 构建已提取章节列表（用于去重）
            extracted_titles = [s.get("title", "") for s in all_sections]
            dedup_hint = ""
            if extracted_titles:
                dedup_hint = (
                    f"\n\n已提取的章节（不要重复）：{', '.join(extracted_titles)}"
                )

            user_prompt = f"""【文章内容第{i+1}/{len(batches)}部分】
{batch_content}

【任务】提取每个章节的知识点

【强制规则】
1. 如果原文说"11个要素"，必须列出全部11个（不能是8个）
2. 如果有父子关系（如"FlowAgent包含4个子类型"），子项必须缩进：
   - **FlowAgent**：说明
     - SequentialAgent：说明
     - ParallelAgent：说明
     - LoopAgent：说明
     - LlmRoutingAgent：说明
3. 如果原文说"介绍A和B两个技术，B包含B1和B2"，必须归类：
   - **A**：说明
   - **B**：说明
     - B1：说明
     - B2：说明

【示例】
错误❌："大模型、提示词、RAG、记忆、工具、网关、运行时、可观测"（只有8个）
正确✅："1.大模型 2.提示词 3.RAG 4.记忆 5.工具 6.网关 7.运行时 8.可观测 9.评估 10.安全 11.XXX"（11个）

错误❌："ReactAgent、FlowAgent、SequentialAgent、ParallelAgent"（平铺）
正确✅："- **ReactAgent**：基础Agent
- **FlowAgent**：包含多个ReactAgent
  - SequentialAgent：串行
  - ParallelAgent：并行"（缩进）

【去重】{dedup_hint}

返回JSON：{{"title":"","sections":[{{"title":"第X章","content":["知识点","  - 子知识点"],"level":2}}],"images":[]}}"""

            logger.info(f"处理第{i+1}/{len(batches)}批次，长度:{len(user_prompt)}字符")

            # 重试机制：最多重试2次
            max_retries = 2
            retry_count = 0
            batch_success = False

            while retry_count <= max_retries and not batch_success:
                try:
                    if retry_count > 0:
                        logger.warning(f"批次{i+1}第{retry_count}次重试...")
                    else:
                        logger.info(f"批次{i+1}开始调用AI...")

                    import time

                    start_time = time.time()

                    completion = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        # 不设置timeout，使用默认值
                    )

                    elapsed = time.time() - start_time
                    logger.info(f"批次{i+1}AI调用完成，耗时{elapsed:.1f}秒")

                    batch_response = completion.choices[0].message.content
                    logger.debug(f"批次{i+1}返回长度: {len(batch_response)}字符")
                    logger.debug(f"批次{i+1}返回前200字符: {batch_response[:200]}...")

                    # 解析JSON - 更健壮的处理
                    json_match = re.search(
                        r"```(?:json)?\s*(\{.*?\})\s*```", batch_response, re.DOTALL
                    )
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 尝试找到第一个{和最后一个}
                        start_idx = batch_response.find("{")
                        end_idx = batch_response.rfind("}")
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            json_str = batch_response[start_idx : end_idx + 1]
                        else:
                            json_str = batch_response.strip()

                    logger.debug(f"批次{i+1}提取的JSON长度: {len(json_str)}字符")

                    try:
                        batch_result = json.loads(json_str)
                    except json.JSONDecodeError as json_err:
                        logger.error(f"批次{i+1} JSON解析失败: {json_err}")
                        logger.error(f"批次{i+1}完整返回内容:\n{batch_response}")
                        logger.error(f"批次{i+1}提取的JSON:\n{json_str[:500]}...")
                        raise

                    # 收集标题和章节
                    if i == 0 and batch_result.get("title"):
                        article_title = batch_result["title"]
                        article_author = batch_result.get("author", "")

                    if batch_result.get("sections"):
                        # 去重：检查章节标题是否已存在（模糊匹配）
                        new_sections = []
                        for section in batch_result["sections"]:
                            section_title = section.get("title", "")
                            # 提取章节编号（如"第1章"、"第2章"）
                            match = re.search(r'第\s*(\d+)\s*章', section_title)
                            chapter_num = match.group(1) if match else None
                            
                            # 检查是否已存在相同章节编号
                            is_duplicate = False
                            if chapter_num:
                                for existing in all_sections:
                                    existing_title = existing.get("title", "")
                                    existing_match = re.search(r'第\s*(\d+)\s*章', existing_title)
                                    if existing_match and existing_match.group(1) == chapter_num:
                                        is_duplicate = True
                                        logger.debug(f"跳过重复章节（章节号匹配）: {section_title} vs {existing_title}")
                                        break
                            
                            if not is_duplicate:
                                new_sections.append(section)
                            else:
                                logger.debug(f"跳过重复章节: {section_title}")

                        all_sections.extend(new_sections)
                        logger.info(
                            f"批次{i+1}提取到{len(batch_result['sections'])}个章节，去重后新增{len(new_sections)}个，当前总计{len(all_sections)}个"
                        )
                        
                        # 验证提取质量
                        for section in new_sections:
                            content = section.get('content', [])
                            # 检查是否有缩进（"  - "开头）
                            has_indent = any(str(item).startswith('  - ') for item in content)
                            if not has_indent and len(content) > 3:
                                logger.warning(f"章节 {section.get('title')} 可能缺少层次结构（无缩进）")

                    batch_success = True

                except Exception as e:
                    retry_count += 1
                    logger.error(
                        f"批次{i+1}处理失败(尝试{retry_count}/{max_retries+1}): {e}"
                    )

                    if retry_count > max_retries:
                        logger.error(f"批次{i+1}达到最大重试次数，跳过")
                        # 如果是第一批次失败，抛出异常
                        if i == 0 and not all_sections:
                            raise Exception(f"第一批次处理失败: {e}")
                        break

                    # 等待后重试
                    time.sleep(2)

        # 组装最终结果为JSON字符串
        response_text = json.dumps(
            {
                "title": article_title,
                "subtitle": "",
                "author": article_author,
                "publish_time": "",
                "sections": all_sections,
                "images": images,  # 使用提取到的图片
            },
            ensure_ascii=False,
        )

        logger.info(f"所有批次处理完成，共提取{len(all_sections)}个章节")

        # 解析JSON响应
        try:
            # 尝试提取JSON（可能被markdown代码块包裹）
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(1)
            else:
                # 直接尝试解析整个响应
                json_str = response_text.strip()

            result = json.loads(json_str)

            # 验证必需字段
            if "title" not in result:
                result["title"] = "未知标题"
            if "sections" not in result:
                result["sections"] = []
            if "images" not in result:
                result["images"] = []

            # 添加额外字段
            result["url"] = url
            result["source"] = "ai_extracted"

            # 生成完整正文
            content_parts = []
            for section in result["sections"]:
                if section.get("title"):
                    content_parts.append(section["title"])
                if section.get("content"):
                    if isinstance(section["content"], list):
                        content_parts.extend(section["content"])
                    else:
                        content_parts.append(str(section["content"]))
            result["content"] = "\n\n".join(content_parts)

            logger.info(
                f"AI提取成功: 标题={result['title']}, 章节数={len(result['sections'])}, 图片数={len(result['images'])}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM返回的JSON失败: {e}")
            logger.error(f"LLM返回内容: {response_text}")
            raise ValueError(f"AI返回的内容不是有效的JSON格式: {e}")
        except Exception as e:
            logger.error(f"AI提取过程出错: {e}", exc_info=True)
            raise
