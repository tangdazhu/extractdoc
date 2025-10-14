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


def _extract_pdf_multimodal(pdf_path: Path, temp_dir: Path) -> Dict[str, any]:
    """
    从 PDF 提取多模态内容：文本、表格、图片。
    
    Returns:
        {
            "text": "全文文本",
            "tables": [{"page": 1, "data": [[row1], [row2], ...]}, ...],
            "images": [{"page": 1, "path": Path(...), "bbox": (x0,y0,x1,y1)}, ...]
        }
    """
    result = {"text": "", "tables": [], "images": [], "pages": []}
    
    if not PYMUPDF_AVAILABLE:
        logger.warning("PyMuPDF 未安装，无法提取图片。")
        return result
    
    try:
        import pdfplumber
        
        # 使用 pdfplumber 提取文本和表格
        with pdfplumber.open(str(pdf_path)) as pdf:
            text_parts = []
            for page_num, page in enumerate(pdf.pages, start=1):
                # 提取文本
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                # 保存每页的文本（用于生成单独的幻灯片）
                result["pages"].append({
                    "page": page_num,
                    "text": page_text if page_text else ""
                })
                
                # 提取表格
                tables = page.extract_tables()
                for table in tables:
                    if table and len(table) > 1:  # 至少有标题行和一行数据
                        result["tables"].append({
                            "page": page_num,
                            "data": table
                        })
            
            result["text"] = "\n".join(text_parts)
        
        # 使用 PyMuPDF 提取图片（过滤小图）
        # 注意:不在此阶段去重,因为PDF图片资源可能被多页共享,需要在PPT生成时智能判断
        pdf_document = fitz.open(str(pdf_path))
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            img_count = 0  # 当前页面有效图片计数
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 检查图片尺寸
                    img_pil = Image.open(io.BytesIO(image_bytes))
                    width, height = img_pil.size
                    
                    # 过滤条件：宽度或高度小于 200px 的图片（通常是装饰性元素）
                    if width < 200 or height < 200:
                        logger.debug("跳过小图片: %dx%d (页面 %d)", width, height, page_num + 1)
                        continue
                    
                    # 过滤条件：宽高比极端的图片（如横幅、分隔线）
                    aspect_ratio = max(width, height) / min(width, height)
                    if aspect_ratio > 10:
                        logger.debug("跳过极端宽高比图片: %.1f (页面 %d)", aspect_ratio, page_num + 1)
                        continue
                    
                    # 保存图片到临时目录
                    img_count += 1
                    img_filename = f"page{page_num + 1}_img{img_count}.{image_ext}"
                    img_path = temp_dir / img_filename
                    img_path.write_bytes(image_bytes)
                    
                    result["images"].append({
                        "page": page_num + 1,
                        "path": img_path,
                        "index": img_count,
                        "width": width,
                        "height": height,
                        "bytes": image_bytes,  # 用于去重
                        "xref": xref  # 记录xref用于调试
                    })
                    
                    logger.debug("提取有效图片: %s (%dx%d, 页面 %d, xref=%d)", 
                                img_filename, width, height, page_num + 1, xref)
                    
                except Exception as e:
                    logger.warning("图片提取失败 xref=%d (页面 %d): %s", xref, page_num + 1, e)
                    continue
        
        pdf_document.close()
        logger.info("PDF 多模态提取完成: 文本 %d 字符, 表格 %d 个, 图片 %d 张",
                    len(result["text"]), len(result["tables"]), len(result["images"]))
        return result
    
    except Exception as exc:
        logger.error("PDF 多模态提取失败: %s", exc, exc_info=True)
        return result


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

    # 1. 检测是否为 PDF 并提取多模态内容
    is_pdf = source_file_path and source_file_path.suffix.lower() == ".pdf"
    multimodal_data = None
    
    if is_pdf:
        logger.info("检测到 PDF 文件，使用页面保留模式生成PPT...")
        multimodal_data = _extract_pdf_multimodal(source_file_path, temp_dir)
        text = multimodal_data["text"]
        
        # 使用 AI 提取标题和副标题
        logger.info("使用 AI 提取文档标题...")
        structure = _analyze_content_with_ai(text, request_id)
    else:
        logger.info("提取文本内容...")
        text = _collect_source_text(source_file_path, source_url)
        
        if not text:
            raise ValueError("未能从输入源提取到有效文本。")
        
        # 非 PDF 文件使用 AI 分析模式
        logger.info("使用 AI 分析文档结构...")
        structure = _analyze_content_with_ai(text, request_id)
    
    # 3. 加载预定义模板
    template_path = template_config.get("template_path")
    if template_path:
        # 转换为绝对路径
        tpl_path = Path(settings.BASE_DIR).parent / template_path
        if not tpl_path.exists():
            logger.warning("PPT 模板 %s 不存在，使用空白模板。", tpl_path)
            presentation = Presentation()
        else:
            logger.info("加载预定义模板: %s", tpl_path)
            presentation = Presentation(str(tpl_path))
            # 删除模板中的示例页面（保留布局和主题）
            # 注意：不删除所有页面，保留第一页以维持主题样式
            slide_count = len(presentation.slides)
            if slide_count > 0:
                # 只删除示例页面，保留布局定义
                xml_slides = presentation.slides._sldIdLst
                while len(xml_slides) > 0:
                    rId = xml_slides[0].rId
                    presentation.part.drop_rel(rId)
                    del xml_slides[0]
                logger.debug("已清除模板示例页面，保留布局和主题")
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

    # 5. 根据文件类型选择生成模式
    if is_pdf and multimodal_data:
        # PDF 文件：页面保留模式
        logger.info("使用页面保留模式生成PPT...")
        pages_added = _generate_ppt_from_pdf_pages(
            presentation, multimodal_data, template_config
        )
        logger.info("已生成 %d 页内容（页面保留模式）", pages_added)
    else:
        # 非 PDF 文件：AI 分析模式
        logger.info("使用 AI 分析模式生成PPT...")
        sections = structure.get("sections", [])
        bullet_layout_index = template_config.get("bullet_layout_index", 1)
        try:
            body_layout = presentation.slide_layouts[bullet_layout_index]
        except IndexError:
            body_layout = presentation.slide_layouts[1]

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

    total_pages = len(presentation.slides)
    logger.info(
        "PPT 文档生成完成: %s，共 %d 页 (user=%s, request=%s)",
        output_path,
        total_pages,
        username,
        request_id,
    )
    return output_filename, f"PPT 文档生成成功，共 {total_pages} 页。"


def _generate_ppt_from_pdf_pages(
    presentation: Presentation,
    multimodal_data: Dict[str, any],
    template_config: dict
) -> int:
    """
    按 PDF 页面结构生成 PPT（页面保留模式）。
    每个 PDF 页面对应一个或多个 PPT 页面（表格+图片）。
    
    Returns:
        生成的页面数量
    """
    blank_layout = presentation.slide_layouts[6]  # 空白布局
    pages_added = 0
    
    # 按页面分组
    pages_with_content = {}
    
    # 初始化所有页面（包含文本）
    for page_data in multimodal_data.get("pages", []):
        page_num = page_data["page"]
        pages_with_content[page_num] = {
            "text": page_data["text"],
            "tables": [],
            "images": []
        }
    
    # 收集表格
    for table_data in multimodal_data["tables"]:
        page_num = table_data["page"]
        if page_num not in pages_with_content:
            pages_with_content[page_num] = {"text": "", "tables": [], "images": []}
        pages_with_content[page_num]["tables"].append(table_data)
    
    # 收集图片（过滤背景装饰图 + 智能去重）
    import hashlib
    
    # 第一步：先收集所有图片（仅过滤背景图）
    temp_images_by_page = {}  # {page_num: [img_data, ...]}
    
    for img_data in multimodal_data["images"]:
        page_num = img_data["page"]
        width = img_data["width"]
        height = img_data["height"]
        
        # 通用背景图过滤规则：
        # 1. 常见演示文稿尺寸（16:9 或 4:3 比例，且尺寸较大）
        # 2. 宽高比接近 16:9 (1.77) 或 4:3 (1.33)，且面积超过 1.5M 像素
        aspect_ratio = width / height if height > 0 else 0
        area = width * height
        
        # 判断是否为全屏背景图（常见演示文稿尺寸）
        is_16_9 = 1.7 <= aspect_ratio <= 1.8  # 16:9 比例
        is_4_3 = 1.3 <= aspect_ratio <= 1.4   # 4:3 比例
        is_large = area > 1500000  # 面积超过 1.5M 像素
        
        if (is_16_9 or is_4_3) and is_large:
            logger.debug("跳过背景装饰图: %dx%d (页面 %d, 宽高比=%.2f, 面积=%d)", 
                        width, height, page_num, aspect_ratio, area)
            continue
        
        if page_num not in temp_images_by_page:
            temp_images_by_page[page_num] = []
        temp_images_by_page[page_num].append(img_data)
    
    # 第二步：全局去重 - 每张图片只保留在最后一个无表格的页面
    global_image_registry = {}  # {hash: [page_num1, page_num2, ...]}
    
    # 先收集每张图片出现在哪些页面
    for page_num in sorted(temp_images_by_page.keys()):
        page_images = temp_images_by_page[page_num]
        
        for img_data in page_images:
            img_bytes = img_data.get("bytes")
            if img_bytes:
                img_hash = hashlib.md5(img_bytes).hexdigest()
                if img_hash not in global_image_registry:
                    global_image_registry[img_hash] = []
                global_image_registry[img_hash].append({
                    "page": page_num,
                    "data": img_data
                })
    
    # 决定每张图片应该保留在哪个页面
    for img_hash, occurrences in global_image_registry.items():
        # 找到最后一个没有表格的页面
        target_page = None
        for occurrence in reversed(occurrences):
            page_num = occurrence["page"]
            page_has_table = page_num in [t["page"] for t in multimodal_data["tables"]]
            if not page_has_table:
                target_page = page_num
                break
        
        # 如果所有页面都有表格,则不保留此图片
        if target_page is None:
            logger.debug("图片 hash=%s 在所有页面都有表格,不保留", img_hash[:8])
            continue
        
        # 只在目标页面保留此图片
        for occurrence in occurrences:
            page_num = occurrence["page"]
            img_data = occurrence["data"]
            
            if page_num not in pages_with_content:
                pages_with_content[page_num] = {"text": "", "tables": [], "images": []}
            
            if page_num == target_page:
                pages_with_content[page_num]["images"].append(img_data)
                logger.debug("保留图片: %dx%d (hash=%s, 保留在第 %d 页)", 
                            img_data["width"], img_data["height"], img_hash[:8], page_num)
            else:
                logger.debug("跳过重复图片: %dx%d (hash=%s, 首次出现于第 %d 页，当前第 %d 页)", 
                            img_data["width"], img_data["height"], img_hash[:8], target_page, page_num)
    
    # 按页面顺序处理（每页创建一个综合页面）
    for page_num in sorted(pages_with_content.keys()):
        page_content = pages_with_content[page_num]
        page_text = page_content.get("text", "")
        tables = page_content["tables"]
        images = page_content["images"]
        
        # 跳过完全空白的页面
        if not page_text.strip() and not tables and not images:
            logger.debug("跳过空白页面: 第 %d 页", page_num)
            continue
        
        # 创建一个页面，包含该页的所有内容
        slide = presentation.slides.add_slide(blank_layout)
        
        # 添加标题
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(9), Inches(0.5)
        )
        title_frame = title_box.text_frame
        title_frame.text = f"第 {page_num} 页"
        title_frame.paragraphs[0].font.size = PptPt(24)
        title_frame.paragraphs[0].font.bold = True
        
        current_top = Inches(1.0)  # 当前垂直位置
        
        # 1. 优先添加表格（如果有）
        for table_data in tables:
            rows_data = table_data["data"]
            rows = len(rows_data)
            cols = len(rows_data[0]) if rows_data else 0
            
            if rows > 0 and cols > 0:
                left = Inches(0.5)
                width = Inches(9)
                # 根据行数动态计算高度
                row_height = min(0.4, 2.5 / rows)  # 每行最多 0.4 英寸，总高度不超过 2.5 英寸
                height = Inches(row_height * rows)
                
                table = slide.shapes.add_table(rows, cols, left, current_top, width, height).table
                
                # 填充表格数据
                for row_idx, row_data in enumerate(rows_data):
                    for col_idx, cell_value in enumerate(row_data):
                        cell = table.cell(row_idx, col_idx)
                        cell.text = str(cell_value) if cell_value else ""
                        cell.text_frame.paragraphs[0].font.size = PptPt(11)
                        
                        # 标题行加粗
                        if row_idx == 0:
                            cell.text_frame.paragraphs[0].font.bold = True
                
                current_top += height + Inches(0.3)  # 表格后留间距
                logger.debug("已添加表格: 第 %d 页, %d 行 x %d 列", page_num, rows, cols)
        
        # 2. 添加图片（如果有，且空间足够）
        # PPT标准页面高度7.5英寸,预留底部0.3英寸,可用高度约7.2英寸
        max_content_height = Inches(7.2)
        
        if images and current_top < max_content_height:
            for img_idx, img_data in enumerate(images, start=1):
                # 检查是否还有足够空间添加图片(至少需要1英寸高度)
                if current_top >= max_content_height - Inches(0.5):
                    logger.warning("空间不足，跳过剩余 %d 张图片 (第 %d 页, current_top=%.2f英寸)", 
                                  len(images) - img_idx + 1, page_num, current_top / 914400)
                    break  # 空间不足，停止添加图片
                
                img_path = img_data["path"]
                
                if img_path.exists():
                    try:
                        # 计算可用空间
                        available_height = max_content_height - current_top - Inches(0.2)
                        max_width = Inches(9)
                        
                        img_width_px = img_data["width"]
                        img_height_px = img_data["height"]
                        
                        # 将像素转换为英寸（假设96 DPI）
                        img_width_inch = img_width_px / 96.0
                        img_height_inch = img_height_px / 96.0
                        
                        logger.debug("图片 %d/%d: 原始尺寸=%dx%d像素, 转换=%.2fx%.2f英寸, 可用高度=%.2f英寸", 
                                    img_idx, len(images), img_width_px, img_height_px, 
                                    img_width_inch, img_height_inch, available_height / 914400)
                        
                        # 计算缩放比例
                        # 如果有多张图片,限制单张图片最大高度为可用高度的60%,为其他图片留空间
                        if len(images) > 1:
                            max_single_img_height = available_height * 0.6
                        else:
                            max_single_img_height = available_height
                        
                        width_ratio = max_width / Inches(img_width_inch)
                        height_ratio = max_single_img_height / Inches(img_height_inch)
                        scale_ratio = min(width_ratio, height_ratio, 1.0)  # 不放大
                        
                        logger.debug("缩放比例: width_ratio=%.2f, height_ratio=%.2f, scale_ratio=%.2f", 
                                    width_ratio, height_ratio, scale_ratio)
                        
                        # 计算最终尺寸（英寸对象）
                        final_width = Inches(img_width_inch * scale_ratio)
                        final_height = Inches(img_height_inch * scale_ratio)
                        
                        logger.debug("最终尺寸: %.2fx%.2f英寸", 
                                    final_width / 914400, final_height / 914400)
                        
                        # 居中放置
                        left = (Inches(10) - final_width) / 2
                        
                        slide.shapes.add_picture(
                            str(img_path),
                            left=left,
                            top=current_top,
                            width=final_width,
                            height=final_height
                        )
                        
                        current_top += final_height + Inches(0.2)  # 图片后留间距
                        logger.debug("已添加图片: 第 %d 页 (%dx%d)", 
                                    page_num, img_width_px, img_height_px)
                    except Exception as img_error:
                        logger.error("插入图片失败: %s", img_error, exc_info=True)
        
        # 3. 最后添加文本内容（如果有，且没有表格和图片）
        if page_text.strip() and not tables and not images:
            # 提取第一行作为标题（如果是纯大写或包含关键词）
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            # 检查是否有明显的标题行
            first_line = lines[0] if lines else ""
            if first_line and (first_line.isupper() or len(first_line) < 50):
                # 使用第一行作为标题
                title_frame.text = first_line
                content_lines = lines[1:]
            else:
                content_lines = lines
            
            # 添加文本内容
            if content_lines:
                text_box = slide.shapes.add_textbox(
                    Inches(0.5), current_top, Inches(9), Inches(4.0)
                )
                text_frame = text_box.text_frame
                text_frame.word_wrap = True
                
                # 添加内容（限制行数，避免溢出）
                max_lines = 15
                for idx, line in enumerate(content_lines[:max_lines]):
                    if idx == 0:
                        text_frame.text = line
                        text_frame.paragraphs[0].font.size = PptPt(14)
                    else:
                        p = text_frame.add_paragraph()
                        p.text = line
                        p.font.size = PptPt(12)
                        p.level = 0
                
                current_top += Inches(4.2)
                logger.debug("已添加文本内容: 第 %d 页, %d 行", page_num, min(len(content_lines), max_lines))
        
        pages_added += 1
        has_text = 1 if (page_text.strip() and not tables and not images) else 0
        logger.debug("已创建综合页面: 第 %d 页 (文本:%d, 表格:%d, 图片:%d)", 
                    page_num, has_text, len(tables), len(images))
    
    return pages_added


# 旧代码已删除，新逻辑在 _generate_ppt_from_pdf_pages() 中实现
