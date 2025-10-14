"""文档生成服务模块。

负责加载模板配置、整理输入内容，并生成 PPT / Word 文件。
"""

from __future__ import annotations

import json
import logging
import os
import re
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from docx import Document as WordDocument
from docx.shared import Pt
from PIL import Image
import dashscope
from dashscope import Generation

logger = logging.getLogger("converter")

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt as PptPt

    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False
    logger.warning("python-pptx 未安装，PPT 生成功能不可用。")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF 未安装，PDF 转图片功能不可用。")

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
        para_len = len(para)
        if length + para_len > 500 and current:
            chunks.append("\n".join(current))
            current = [para]
            length = para_len
        else:
            current.append(para)
            length += para_len
    if current:
        chunks.append("\n".join(current))
    return chunks if chunks else [text]


def _analyze_content_with_ai(text: str, request_id: str) -> Dict[str, any]:
    """
    使用 DashScope AI 分析文档内容，提取结构化信息。
    
    Args:
        text: 原始文本内容
        request_id: 请求 ID
    
    Returns:
        结构化数据：
        {
            "title": "文档标题",
            "subtitle": "副标题",
            "sections": [
                {
                    "title": "章节标题",
                    "points": ["要点1", "要点2", ...]
                },
                ...
            ]
        }
    """
    logger.info("开始 AI 内容分析，RequestID=%s", request_id)
    
    prompt = f"""请分析以下文档内容，提取结构化信息并以 JSON 格式返回。

要求：
1. 识别文档的主标题和副标题
2. 将内容分为多个章节（每个章节包含标题和3-5个要点）
3. 每个要点应简洁明了，适合在 PPT 中展示
4. 返回格式必须是有效的 JSON

文档内容：
{text[:4000]}

请返回 JSON 格式：
{{
  "title": "主标题",
  "subtitle": "副标题",
  "sections": [
    {{
      "title": "章节1标题",
      "points": ["要点1", "要点2", "要点3"]
    }}
  ]
}}"""
    
    try:
        response = Generation.call(
            model="qwen-plus",
            prompt=prompt,
            result_format="message"
        )
        
        if response.status_code == 200:
            ai_output = response.output.choices[0].message.content
            logger.debug("AI 返回内容: %s", ai_output)
            
            # 提取 JSON 部分（去除可能的 Markdown 代码块标记）
            json_match = re.search(r'```json\s*({.*?})\s*```', ai_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = ai_output.strip()
            
            result = json.loads(json_str)
            logger.info("AI 内容分析成功，提取 %d 个章节。", len(result.get("sections", [])))
            return result
        else:
            logger.error("AI 调用失败: %s", response.message)
            return _fallback_structure(text)
    
    except Exception as exc:
        logger.error("AI 内容分析失败: %s", exc, exc_info=True)
        return _fallback_structure(text)


def _fallback_structure(text: str) -> Dict[str, any]:
    """
    当 AI 分析失败时的降级方案：简单分段。
    """
    logger.warning("使用降级方案进行内容结构化。")
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # 简单启发式：第一行作为标题
    title = lines[0] if lines else "文档内容"
    subtitle = lines[1] if len(lines) > 1 else "自动生成"
    
    # 将剩余内容分为若干段
    sections = []
    chunk_size = 5
    for i in range(2, len(lines), chunk_size):
        chunk = lines[i:i+chunk_size]
        sections.append({
            "title": f"内容概览 {len(sections) + 1}",
            "points": chunk
        })
    
    return {
        "title": title,
        "subtitle": subtitle,
        "sections": sections if sections else [{"title": "内容", "points": lines[2:]}]
    }


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

    # 1. 提取文本内容
    logger.info("开始提取文档内容，RequestID=%s", request_id)
    text = _collect_source_text(source_file_path, source_url)
    if not text:
        raise ValueError("未能从输入源提取到有效文本。")
    
    # 2. 使用 AI 分析内容结构
    logger.info("使用 AI 分析文档结构...")
    structure = _analyze_content_with_ai(text, request_id)
    
    # 3. 创建 PPT 并应用模板
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

    # 4. 创建标题页
    title_text = structure.get("title", template_config.get("title", "文档演示"))
    subtitle_text = structure.get("subtitle", template_config.get("subtitle", "AI 智能生成"))
    
    title_layout = presentation.slide_layouts[0]
    title_slide = presentation.slides.add_slide(title_layout)
    title_slide.shapes.title.text = title_text
    if len(title_slide.placeholders) > 1:
        title_slide.placeholders[1].text = subtitle_text
    
    logger.info("已创建标题页: %s", title_text)

    # 5. 为每个章节创建内容页
    bullet_layout_index = template_config.get("bullet_layout_index", 1)
    try:
        body_layout = presentation.slide_layouts[bullet_layout_index]
    except IndexError:
        body_layout = presentation.slide_layouts[1]

    sections = structure.get("sections", [])
    for idx, section in enumerate(sections, start=1):
        section_title = section.get("title", f"章节 {idx}")
        points = section.get("points", [])
        
        if not points:
            continue
        
        slide = presentation.slides.add_slide(body_layout)
        
        # 设置章节标题
        if slide.shapes.title:
            slide.shapes.title.text = section_title
        
        # 查找内容占位符
        body_shape = None
        for shape in slide.shapes:
            if shape.has_text_frame and shape != slide.shapes.title:
                body_shape = shape
                break
        
        if not body_shape:
            logger.warning("幻灯片 %d 未找到内容占位符，已跳过。", idx)
            continue
        
        # 填充要点
        text_frame = body_shape.text_frame
        text_frame.clear()
        
        for point_idx, point in enumerate(points):
            if not point.strip():
                continue
            
            if point_idx == 0:
                text_frame.text = point
                if text_frame.paragraphs:
                    text_frame.paragraphs[0].font.size = PptPt(18)
            else:
                p = text_frame.add_paragraph()
                p.text = point
                p.level = 0
                p.font.size = PptPt(16)
        
        logger.debug("已创建章节页: %s (%d 个要点)", section_title, len(points))

    # 6. 保存 PPT
    output_filename = f"{request_id}_slides.pptx"
    output_path = converted_dir / output_filename
    presentation.save(str(output_path))

    logger.info(
        "PPT 文档生成完成（AI 智能模式）: %s，共 %d 个章节 (user=%s, request=%s)",
        output_path,
        len(sections),
        username,
        request_id,
    )
    return output_filename, f"PPT 文档生成成功，共 {len(sections) + 1} 页（AI 智能模式）。"
