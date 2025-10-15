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
            # 删除模板中除第一页外的示例页面
            slide_count = len(presentation.slides)
            if slide_count > 1:
                xml_slides = presentation.slides._sldIdLst
                slides_to_delete = list(range(1, len(xml_slides)))
                for idx in reversed(slides_to_delete):
                    rId = xml_slides[idx].rId
                    presentation.part.drop_rel(rId)
                    del xml_slides[idx]
                logger.debug("已清除模板示例页面(保留第一页)")
    else:
        presentation = Presentation()

    # 4. 修改模板第一页的内容为实际文档内容
    title_text = structure.get("title", template_config.get("title", "文档演示"))
    subtitle_text = structure.get("subtitle", template_config.get("subtitle", "AI 智能生成"))
    
    if len(presentation.slides) > 0:
        # 使用模板第一页,只修改文字内容
        title_slide = presentation.slides[0]
        # 修改标题
        if title_slide.shapes.title:
            title_slide.shapes.title.text = title_text
        # 修改副标题
        if len(title_slide.placeholders) > 1:
            title_slide.placeholders[1].text = subtitle_text
        logger.info("已修改模板第一页内容为: %s", title_text)
    else:
        # 如果没有模板页面,创建新的标题页
        title_layout = presentation.slide_layouts[0]
        title_slide = presentation.slides.add_slide(title_layout)
        title_slide.shapes.title.text = title_text
        if len(title_slide.placeholders) > 1:
            title_slide.placeholders[1].text = subtitle_text
        logger.info("已创建标题页: %s", title_text)
    
    # 如果是PDF且第1页有小表格(<=3行),将其添加到标题页
    if is_pdf and multimodal_data:
        first_page_tables = [t for t in multimodal_data.get("tables", []) if t["page"] == 1]
        if first_page_tables and len(first_page_tables) == 1:
            table_data = first_page_tables[0]["data"]
            if len(table_data) <= 3:
                # 在标题页底部添加小表格
                from pptx.util import Inches, Pt as PptPt
                rows = len(table_data)
                cols = len(table_data[0]) if table_data else 0
                
                if rows > 0 and cols > 0:
                    left = Inches(3.0)  # 居中
                    top = Inches(5.5)   # 底部
                    width = Inches(4.0)
                    height = Inches(0.4 * rows)
                    
                    table = title_slide.shapes.add_table(rows, cols, left, top, width, height).table
                    
                    # 填充表格数据
                    for row_idx, row_data in enumerate(table_data):
                        for col_idx, cell_value in enumerate(row_data):
                            cell = table.cell(row_idx, col_idx)
                            cell.text = str(cell_value) if cell_value else ""
                            cell.text_frame.paragraphs[0].font.size = PptPt(11)
                            if row_idx == 0:
                                cell.text_frame.paragraphs[0].font.bold = True
                    
                    logger.info("已将第1页小表格添加到标题页")

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
    # 使用模板的内容布局(通常是索引1或5),而非空白布局(索引6)
    # 索引1通常是"标题和内容"布局,有模板样式
    try:
        content_layout = presentation.slide_layouts[1]  # 标题和内容布局
    except IndexError:
        content_layout = presentation.slide_layouts[0]  # 回退到标题布局
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
    
    # 收集表格(智能合并连续小表格页)
    # 如果连续两页都只有表格且第一页是小表格,则合并到第一页
    tables_by_page = {}
    for table_data in multimodal_data["tables"]:
        page_num = table_data["page"]
        if page_num not in tables_by_page:
            tables_by_page[page_num] = []
        tables_by_page[page_num].append(table_data)
        logger.debug("收集表格: 第 %d 页, %d 行 x %d 列", 
                    page_num, len(table_data["data"]), len(table_data["data"][0]) if table_data["data"] else 0)
    
    # 不进行表格合并,保持PDF原始页面结构
    # (之前的合并逻辑导致错误地将两个独立页面的表格合并)
    
    # 将修正后的表格分配到页面
    for page_num, tables in tables_by_page.items():
        if page_num not in pages_with_content:
            pages_with_content[page_num] = {"text": "", "tables": [], "images": []}
        pages_with_content[page_num]["tables"].extend(tables)
    
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
    
    # 按页面顺序处理,支持智能合并小内容页面
    sorted_pages = sorted(pages_with_content.keys())
    i = 0
    while i < len(sorted_pages):
        page_num = sorted_pages[i]
        page_content = pages_with_content[page_num]
        page_text = page_content.get("text", "")
        tables = page_content["tables"]
        images = page_content["images"]
        
        # 跳过第1页(如果只有小表格,已添加到标题页)
        if page_num == 1 and len(tables) == 1 and len(tables[0]["data"]) <= 3 and not images:
            logger.debug("跳过第 1 页(小表格已添加到标题页)")
            i += 1
            continue
        
        # 跳过完全空白的页面
        if not page_text.strip() and not tables and not images:
            logger.debug("跳过空白页面: 第 %d 页", page_num)
            i += 1
            continue
        
        # 判断当前页面是否为"小内容页"(可以与下一页合并)
        # 条件: 只有一个小表格(<=3行),无图片
        # 注意:不检查文本,因为pdfplumber会把表格内容也提取为文本
        is_small_content = (
            len(tables) == 1 and 
            len(tables[0]["data"]) <= 3 and 
            not images
        )
        
        logger.debug("第 %d 页判断: 表格数=%d, 表格行数=%d, 图片数=%d, 是否小内容页=%s",
                    page_num, len(tables), 
                    len(tables[0]["data"]) if tables else 0,
                    len(images), is_small_content)
        
        # 不进行页面合并,保持PDF原始页面结构
        pages_to_merge = [page_num]
        
        # 创建一个PPT页面,包含合并后的所有内容
        slide = presentation.slides.add_slide(content_layout)
        
        # 从PDF文本中提取页面标题
        page_title = None
        if page_text:
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            if lines:
                # 查找可能的标题(长度<50字符,不包含过多标点)
                for line in lines[:5]:  # 检查前5行
                    # 过滤掉页眉页脚特征的文本
                    line_lower = line.lower()
                    is_header_footer = (
                        'proprietary' in line_lower or
                        'confidential' in line_lower or
                        'content' in line_lower or
                        line.startswith('第') and '页' in line or  # "第X页"
                        line.isdigit() or  # 纯数字(页码)
                        len(line) < 3  # 太短
                    )
                    
                    if not is_header_footer and len(line) < 50 and line.count(',') < 3 and line.count('，') < 3:
                        page_title = line
                        break
        
        # 使用模板的标题占位符(而不是创建新textbox)
        if slide.shapes.title:
            if page_title:
                slide.shapes.title.text = page_title
            elif len(pages_to_merge) > 1:
                slide.shapes.title.text = f"第 {pages_to_merge[0]}-{pages_to_merge[-1]} 页"
            else:
                slide.shapes.title.text = f"第 {page_num} 页"
        
        current_top = Inches(1.0)  # 当前垂直位置
        
        # 处理所有合并的页面内容
        for merge_page_num in pages_to_merge:
            merge_content = pages_with_content[merge_page_num]
            merge_tables = merge_content["tables"]
            merge_images = merge_content["images"]
            merge_text = merge_content.get("text", "")
            
            # 1. 添加表格（如果有）
            for table_data in merge_tables:
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
                    logger.debug("已添加表格: 第 %d 页, %d 行 x %d 列, 位置=%.2f英寸, 高度=%.2f英寸", 
                                merge_page_num, rows, cols, (current_top - height - Inches(0.3)) / 914400, height / 914400)
            
            # 2. 添加图片（如果有，且空间足够）
            # PPT标准页面高度7.5英寸,预留底部1.5英寸给文本,可用高度约5.5英寸
            max_content_height = Inches(5.5)
            
            if merge_images and current_top < max_content_height:
                # 如果有2张图片,左右并排显示
                if len(merge_images) == 2:
                    available_height = max_content_height - current_top
                    available_width_per_img = Inches(4.5)  # 每张图片最大宽度4.5英寸
                    
                    img_positions = []  # 存储每张图片的位置和尺寸
                    max_img_height = 0
                    
                    for img_idx, img_data in enumerate(merge_images):
                        img_path = img_data["path"]
                        if not img_path.exists():
                            continue
                        
                        try:
                            img_width_px = img_data["width"]
                            img_height_px = img_data["height"]
                            
                            # 将像素转换为英寸
                            img_width_inch = img_width_px / 96.0
                            img_height_inch = img_height_px / 96.0
                            
                            # 计算缩放比例
                            width_ratio = available_width_per_img / Inches(img_width_inch)
                            height_ratio = available_height / Inches(img_height_inch)
                            scale_ratio = min(width_ratio, height_ratio, 1.0)
                            
                            final_width = Inches(img_width_inch * scale_ratio)
                            final_height = Inches(img_height_inch * scale_ratio)
                            
                            # 计算水平位置(左右并排)
                            if img_idx == 0:
                                left = Inches(0.5)  # 左侧图片
                            else:
                                left = Inches(5.5)  # 右侧图片
                            
                            img_positions.append({
                                "path": img_path,
                                "left": left,
                                "top": current_top,
                                "width": final_width,
                                "height": final_height
                            })
                            
                            max_img_height = max(max_img_height, final_height)
                            
                        except Exception as e:
                            logger.warning("图片尺寸计算失败: %s", e)
                    
                    # 添加所有图片
                    for img_pos in img_positions:
                        slide.shapes.add_picture(
                            str(img_pos["path"]),
                            left=img_pos["left"],
                            top=img_pos["top"],
                            width=img_pos["width"],
                            height=img_pos["height"]
                        )
                        logger.debug("已添加图片: 第 %d 页 (左右并排)")
                    
                    current_top += max_img_height + Inches(0.3)
                else:
                    # 单张图片或多张图片,垂直排列
                    for img_idx, img_data in enumerate(merge_images, start=1):
                        if current_top >= max_content_height - Inches(0.5):
                            logger.warning("空间不足，跳过剩余 %d 张图片", len(merge_images) - img_idx + 1)
                            break
                        
                        img_path = img_data["path"]
                        if not img_path.exists():
                            continue
                        
                        try:
                            available_height = max_content_height - current_top - Inches(0.2)
                            max_width = Inches(9)
                            
                            img_width_px = img_data["width"]
                            img_height_px = img_data["height"]
                            img_width_inch = img_width_px / 96.0
                            img_height_inch = img_height_px / 96.0
                            
                            width_ratio = max_width / Inches(img_width_inch)
                            height_ratio = available_height / Inches(img_height_inch)
                            scale_ratio = min(width_ratio, height_ratio, 1.0)
                            
                            final_width = Inches(img_width_inch * scale_ratio)
                            final_height = Inches(img_height_inch * scale_ratio)
                            left = (Inches(10) - final_width) / 2
                            
                            slide.shapes.add_picture(
                                str(img_path),
                                left=left,
                                top=current_top,
                                width=final_width,
                                height=final_height
                            )
                            
                            current_top += final_height + Inches(0.2)
                            logger.debug("已添加图片: 第 %d 页 (%dx%d)", merge_page_num, img_width_px, img_height_px)
                        except Exception as img_error:
                            logger.error("插入图片失败: %s", img_error, exc_info=True)
            
            # 3. 添加文本内容（如果有）
            if merge_text.strip() and not merge_tables:
                # 提取第一行作为标题（如果是纯大写或包含关键词）
                lines = [line.strip() for line in merge_text.split('\n') if line.strip()]
                
                # 检查是否有明显的标题行
                first_line = lines[0] if lines else ""
                if first_line and (first_line.isupper() or len(first_line) < 50):
                    # 使用第一行作为标题(如果之前没有设置标题)
                    if slide.shapes.title and not slide.shapes.title.text:
                        slide.shapes.title.text = first_line
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
                    logger.debug("已添加文本内容: 第 %d 页, %d 行", merge_page_num, min(len(content_lines), max_lines))
        
        pages_added += 1
        # 统计合并页面的内容
        total_tables = sum(len(pages_with_content[p]["tables"]) for p in pages_to_merge)
        total_images = sum(len(pages_with_content[p]["images"]) for p in pages_to_merge)
        total_text = sum(1 if pages_with_content[p].get("text", "").strip() else 0 for p in pages_to_merge)
        logger.debug("已创建综合页面: 第 %s 页 (文本:%d, 表格:%d, 图片:%d)", 
                    "-".join(map(str, pages_to_merge)) if len(pages_to_merge) > 1 else str(pages_to_merge[0]),
                    total_text, total_tables, total_images)
        
        i += 1  # 移动到下一个未处理的页面
    
    return pages_added


# 旧代码已删除，新逻辑在 _generate_ppt_from_pdf_pages() 中实现
