"""文档生成服务模块。

负责加载模板配置、整理输入内容，并生成 PPT / Word 文件。
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from docx import Document as WordDocument
from docx.shared import Pt

logger = logging.getLogger("converter")

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt as PptPt

    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False
    logger.warning("python-pptx 未安装，PPT 生成功能不可用。")

TEMPLATES_CONFIG_PATH = Path(settings.BASE_DIR).parent / "config" / "document_generation_templates.json"


def load_generation_templates() -> Dict[str, Dict[str, dict]]:
    """加载文档生成模板配置。

    返回结构:
        {
            "ppt": {"style_key": {...}},
            "word": {"style_key": {...}}
        }
    若文件缺失，返回空配置并记录日志。
    """

    if not TEMPLATES_CONFIG_PATH.exists():
        logger.warning("未找到模板配置文件 %s。", TEMPLATES_CONFIG_PATH)
        return {"ppt": {}, "word": {}}

    try:
        with TEMPLATES_CONFIG_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            logger.warning("模板配置文件结构非法，已忽略。")
            return {"ppt": {}, "word": {}}
        return {
            "ppt": data.get("ppt", {}),
            "word": data.get("word", {}),
        }
    except Exception as exc:
        logger.error("加载模板配置失败: %s", exc, exc_info=True)
        return {"ppt": {}, "word": {}}


def _read_text_from_file(file_path: Path) -> str:
    if not file_path or not file_path.exists():
        return ""
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(str(file_path)) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    return "\n".join(text_parts)
            except ImportError:
                logger.warning("pdfplumber 未安装，无法提取 PDF 文本。")
                return ""
        elif suffix == ".docx":
            doc = WordDocument(str(file_path))
            return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        elif suffix in {".txt", ".md", ".csv"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.error("读取本地文件失败: %s", exc, exc_info=True)
        return ""


def _read_text_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text
        # 简单去除 HTML 标签
        text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
        return re.sub(r"\n{2,}", "\n", text)
    except Exception as exc:
        logger.error("下载 URL 文本失败，URL=%s，错误=%s", url, exc, exc_info=True)
        return ""


def _collect_source_text(source_file_path: Optional[Path], source_url: str) -> str:
    collected = []
    if source_file_path:
        collected.append(_read_text_from_file(source_file_path))
    if source_url:
        collected.append(_read_text_from_url(source_url))
    text = "\n".join(part.strip() for part in collected if part and part.strip())
    return text.strip()


def _ensure_text_chunks(text: str) -> List[str]:
    if not text:
        return []
    paragraphs = [seg.strip() for seg in text.split("\n") if seg.strip()]
    chunks: List[str] = []
    current = []
    length = 0
    for para in paragraphs:
        if length + len(para) > 800:
            chunks.append("\n".join(current))
            current = [para]
            length = len(para)
        else:
            current.append(para)
            length += len(para)
    if current:
        chunks.append("\n".join(current))
    return chunks


def generate_word_document(
    *,
    request_id: str,
    username: str,
    upload_dir: Path,
    converted_dir: Path,
    temp_dir: Path,
    source_file_path: Optional[Path],
    source_url: str,
    template_config: Optional[dict] = None,
) -> Tuple[str, str]:
    """生成 Word 文档，返回 (文件名, 提示信息)。"""

    text = _collect_source_text(source_file_path, source_url)
    if not text:
        raise ValueError("未能从输入源提取到有效文本。")

    if template_config and template_config.get("template_path"):
        template_path = Path(template_config["template_path"])
        if template_path.exists():
            doc = WordDocument(str(template_path))
        else:
            logger.warning("模板 %s 不存在，使用空白文档。", template_path)
            doc = WordDocument()
    else:
        doc = WordDocument()

    style_name = template_config.get("paragraph_style") if template_config else None
    for chunk in _ensure_text_chunks(text):
        paragraph = doc.add_paragraph(chunk)
        if style_name and style_name in doc.styles:
            paragraph.style = style_name
        else:
            run = paragraph.runs[0]
            run.font.size = Pt(12)

    output_filename = f"{request_id}_document.docx"
    output_path = converted_dir / output_filename
    doc.save(output_path)

    logger.info(
        "Word 文档生成完成: %s (user=%s, request=%s)",
        output_path,
        username,
        request_id,
    )
    return output_filename, "Word 文档生成成功。"


def generate_ppt_document(
    *,
    request_id: str,
    username: str,
    upload_dir: Path,
    converted_dir: Path,
    temp_dir: Path,
    source_file_path: Optional[Path],
    source_url: str,
    template_config: dict,
) -> Tuple[str, str]:
    if not PPTX_AVAILABLE:
        raise RuntimeError("python-pptx 未安装，无法生成 PPT。")

    text = _collect_source_text(source_file_path, source_url)
    if not text:
        raise ValueError("未能从输入源提取到有效文本。")

    template_path = template_config.get("template_path")
    if template_path:
        tpl_path = Path(template_path)
        if not tpl_path.exists():
            logger.warning("PPT 模板 %s 不存在，使用空白模板。", tpl_path)
            presentation = Presentation()
        else:
            presentation = Presentation(str(tpl_path))
    else:
        presentation = Presentation()

    title_text = template_config.get("title", "自动生成演示文稿")
    subtitle_text = template_config.get("subtitle", "来源内容整理")

    if presentation.slides:
        title_slide = presentation.slides[0]
        if title_slide.shapes.title:
            title_slide.shapes.title.text = title_text
        if title_slide.placeholders and len(title_slide.placeholders) > 1:
            try:
                title_slide.placeholders[1].text = subtitle_text
            except Exception:  # 某些模板索引不同
                pass
    else:
        title_layout = presentation.slide_layouts[0]
        slide = presentation.slides.add_slide(title_layout)
        slide.shapes.title.text = title_text
        if len(slide.placeholders) > 1:
            slide.placeholders[1].text = subtitle_text

    bullet_layout_index = template_config.get("bullet_layout_index", 1)
    try:
        body_layout = presentation.slide_layouts[bullet_layout_index]
    except IndexError:
        body_layout = presentation.slide_layouts[1]

    for idx, chunk in enumerate(_ensure_text_chunks(text), start=1):
        slide = presentation.slides.add_slide(body_layout)
        title = slide.shapes.title
        content = chunk.split("\n")
        if title:
            title.text = f"内容概览 {idx}"
        
        # 尝试找到内容占位符
        body_shape = None
        for shape in slide.shapes:
            if shape.has_text_frame and shape != title:
                body_shape = shape
                break
        
        if not body_shape:
            # 如果没有找到合适的占位符，跳过此页
            logger.warning("幻灯片 %d 未找到内容占位符，已跳过内容填充。", idx)
            continue
        
        text_frame = body_shape.text_frame
        text_frame.clear()
        for line_idx, line in enumerate(content):
            if not line.strip():
                continue
            if line_idx == 0:
                text_frame.text = line
                if text_frame.paragraphs:
                    text_frame.paragraphs[0].font.size = PptPt(18)
            else:
                p = text_frame.add_paragraph()
                p.text = line
                p.level = 0
                p.font.size = PptPt(16)

    output_filename = f"{request_id}_slides.pptx"
    output_path = converted_dir / output_filename
    presentation.save(output_path)

    logger.info(
        "PPT 文档生成完成: %s (user=%s, request=%s)",
        output_path,
        username,
        request_id,
    )
    return output_filename, "PPT 文档生成成功。"
