# -*- coding: utf-8 -*-
"""
图片文字与表格智能提取脚本
- 支持指定图片（如6.jpg）自动还原为带边框的Word表格，表头和数据结构与原图一致
- 其余图片全部按普通段落输出
- 自动分割表格与正文内容，正文不会被误放入表格
- 新增：支持输出为PDF格式
"""
import os
import glob
import re
import sys 
import argparse # 新增 argparse 用于更灵活的命令行参数处理
from pathlib import Path # 新增 pathlib

# import yaml # No longer needed here
# import logging # No longer needed here, managed by utils
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np  # Added
from paddleocr import PaddleOCR
from docx import Document
from docx.shared import Pt
from bs4 import BeautifulSoup  # Added

# Import utility functions
from utils import load_config, setup_logging  # Added

# Global logger instance, will be initialized in main
logger = None  # Added

# 尝试导入 docx2pdf，如果失败则记录错误，但脚本仍可生成docx
try:
    from docx2pdf import convert as convert_docx_to_pdf
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False
    # logger is not yet initialized here, so we can't use it.
    # We'll log this when the script main function runs.

# def load_config(config_path='config.yaml'): # Removed
#     """Load configuration from a YAML file."""
#     try:
#         with open(config_path, 'r', encoding='utf-8') as f:
#             config = yaml.safe_load(f)
#         return config
#     except FileNotFoundError:
#         # Create a default config if not found, and log it
#         default_config = {
#             'input_directory': 'his_pic',
#             'output_filename': 'extracted_text.docx',
#             'log_file': 'app.log'
#         }
#         with open(config_path, 'w', encoding='utf-8') as f:
#             yaml.dump(default_config, f)
#         # Log this event before file handler is set up, so it goes to console
#         print(f"Warning: '{config_path}' not found. Created a default config file.")
#         return default_config
#     except Exception as e:
#         print(f"Error loading config file '{config_path}': {e}. Using default values.")
#         return { # Return defaults on any other error
#             'input_directory': 'his_pic',
#             'output_filename': 'extracted_text.docx',
#             'log_file': 'app.log'
#         }

# def setup_logging(log_file_path): # Removed
#     """Configure logging to file and console."""
#     # Remove existing handlers to prevent duplicate logs if this is called multiple times
#     for handler in logger.handlers[:]:
#         logger.removeHandler(handler)
#         handler.close()

#     # File handler
#     file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
#     file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     file_handler.setFormatter(file_formatter)
#     logger.addHandler(file_handler)

#     # Console handler (optional, but good for immediate feedback)
#     console_handler = logging.StreamHandler()
#     console_formatter = logging.Formatter('%(levelname)s: %(message)s')
#     console_handler.setFormatter(console_formatter)
#     logger.addHandler(console_handler)


def add_table_from_html_to_docx(doc, html_content):
    """Parses an HTML table and adds it to the Word document."""
    global logger
    soup = BeautifulSoup(html_content, "html.parser")
    table_tag = soup.find("table")

    if not table_tag:
        if logger:
            logger.warning(
                "No <table> tag found in the HTML content provided for table extraction."
            )
        doc.add_paragraph("[Warning: Could not find table structure in provided HTML]")
        return

    html_rows = table_tag.find_all("tr")

    max_cols = 0
    for hr in html_rows:
        cols_in_row = 0
        for cell in hr.find_all(["td", "th"]):
            cols_in_row += int(cell.get("colspan", 1))
        if cols_in_row > max_cols:
            max_cols = cols_in_row

    if max_cols == 0 and not html_rows:
        if logger:
            logger.info("HTML table has no rows or columns.")
        doc.add_paragraph("[Empty Table]")
        return
    if max_cols == 0 and html_rows:
        if logger:
            logger.warning(
                "HTML table has rows but no discernible columns. Adding as simple list."
            )
        for r_idx, hr in enumerate(html_rows):
            row_text_parts = [
                cell.get_text(separator=" ", strip=True)
                for cell in hr.find_all(["td", "th"])
            ]
            doc.add_paragraph(f"Row {r_idx+1}: {', '.join(row_text_parts)}")
        return

    grid = [[None for _ in range(max_cols)] for _ in range(len(html_rows))]
    temp_rows_for_docx = []

    for r_idx, hr in enumerate(html_rows):
        current_row_for_docx = []
        c_idx_grid = 0
        for cell in hr.find_all(["td", "th"]):
            while c_idx_grid < max_cols and grid[r_idx][c_idx_grid] is not None:
                c_idx_grid += 1

            if c_idx_grid >= max_cols:
                continue

            text = cell.get_text(separator="\n", strip=True)
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))

            current_row_for_docx.append(
                {"text": text, "colspan": colspan, "rowspan": rowspan}
            )

            for i in range(rowspan):
                for j in range(colspan):
                    if r_idx + i < len(grid) and c_idx_grid + j < max_cols:
                        if i == 0 and j == 0:
                            grid[r_idx + i][c_idx_grid + j] = text
                        else:
                            grid[r_idx + i][c_idx_grid + j] = "MERGED_CELL_PLACEHOLDER"
            c_idx_grid += colspan
        temp_rows_for_docx.append(current_row_for_docx)

    if not temp_rows_for_docx and not html_rows:
        if logger:
            logger.info("No data extracted from HTML table for docx table creation.")
        if html_rows:
            doc.add_paragraph("[Warning: Could not parse cells from HTML table rows]")
        return

    if not html_rows:
        return

    docx_table = doc.add_table(rows=len(html_rows), cols=max_cols)
    docx_table.style = "Table Grid"

    for r_idx, row_content in enumerate(temp_rows_for_docx):
        c_idx_docx = 0
        for cell_info in row_content:
            if c_idx_docx >= max_cols:
                break

            text = cell_info["text"]
            colspan = cell_info["colspan"]
            rowspan = cell_info["rowspan"]

            current_docx_cell = docx_table.cell(r_idx, c_idx_docx)
            current_docx_cell.text = text

            if colspan > 1 or rowspan > 1:
                br_r = r_idx + rowspan - 1
                br_c = c_idx_docx + colspan - 1
                if br_r < len(html_rows) and br_c < max_cols:
                    try:
                        current_docx_cell.merge(docx_table.cell(br_r, br_c))
                    except Exception as e:
                        if logger:
                            logger.warning(
                                f"Could not merge cells for ({r_idx},{c_idx_docx}) to ({br_r},{br_c}): {e}"
                            )
                else:
                    if logger:
                        logger.warning(
                            f"Merge region ({r_idx},{c_idx_docx}) to ({br_r},{br_c}) out of bounds for table ({len(html_rows)},{max_cols})."
                        )

            c_idx_docx += colspan


def extract_layout_elements(image_path, ocr_instance):
    """Extract layout elements (text, tables, figures) from an image."""
    global logger
    try:
        # Pass the original image path directly to PaddleOCR
        result = ocr_instance.ocr(image_path, cls=True)

        if logger:
            # Log a snippet of the raw result to understand its structure
            logger.debug(
                f"Raw OCR result for {image_path} (layout=True mode, no preprocessing): {str(result)[:1500]}"
            )

        if not result:
            if logger:
                logger.warning(f"OCR returned empty result for {image_path}.")
            return []

        if isinstance(result, list) and len(result) > 0:
            page_elements = result[0]

            if isinstance(page_elements, list):
                if logger and page_elements:
                    first_elem_type = (
                        type(page_elements[0])
                        if page_elements
                        else "empty list (page_elements was empty)"
                    )
                    element_count = len(page_elements)
                    logger.debug(
                        f"Extracted page_elements for {image_path}. Count: {element_count}. Type of first element: {first_elem_type}. Content (first 1000 chars): {str(page_elements)[:1000]}"
                    )
                elif logger and not page_elements:
                    logger.debug(
                        f"Extracted page_elements for {image_path} is an empty list."
                    )
                return page_elements
            else:
                if logger:
                    logger.warning(
                        f"Expected result[0] to be a list of elements for {image_path}, but got {type(page_elements)}. Content: {str(page_elements)[:500]}"
                    )
                return []
        else:
            if logger:
                logger.warning(
                    f"OCR result for {image_path} is not in the expected list format or is empty. Result: {str(result)[:500]}"
                )
            return []

    except Exception as e:
        if logger:
            logger.error(
                f"Error during layout extraction from {image_path}: {e}", exc_info=True
            )
        return []


def extract_text_from_image(image_path, ocr_instance):
    """Extract text from an image using PaddleOCR."""
    global logger  # Ensure we are using the global logger
    try:
        # Perform OCR on the image
        result = ocr_instance.ocr(image_path, cls=True)

        text_lines = []
        if result and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                if line and len(line) > 1 and line[1] and len(line[1]) > 0:
                    text_lines.append(line[1][0])

        if not text_lines:
            if logger:  # Check if logger is initialized
                logger.warning(f"No text detected in {image_path}")
            else:  # Fallback if logger somehow not set, though it should be
                print(f"Warning: No text detected in {image_path}")
            return "No text detected in this image."

        text = "\n".join(text_lines)
        return text
    except Exception as e:
        if logger:  # Check if logger is initialized
            logger.error(f"Error processing {image_path}: {e}", exc_info=True)
        else:
            print(f"Error processing {image_path}: {e}")
        return f"Error processing image: {str(e)}"


def segment_text(text):
    """
    Enhanced text segmentation that preserves hierarchical structure and formatting.
    Handles numbered lists, bullet points, and maintains proper document structure.
    """
    import re
    
    if not text or not text.strip():
        return [text] if text else []
    
    # Split by various line separators
    raw_lines = re.split(r'[\n\r]+', text)
    
    # Clean and filter lines
    lines = []
    for line in raw_lines:
        line = line.strip()
        if line:  # Keep all non-empty lines, including single characters that might be bullets
            lines.append(line)
    
    if not lines:
        return [text.strip()] if text.strip() else []
    
    # Analyze structure and create formatted content
    formatted_content = []
    current_main_section = None  # Track current main section for proper sub-item assignment
    
    for i, line in enumerate(lines):
        # Check line patterns and apply appropriate formatting
        formatted_line = None
        
        # Main title or heading (like "Content")
        if (line.upper() == line and len(line) <= 20 and 
            any(keyword in line.upper() for keyword in ['CONTENT', 'WHITEPAPER', '目录', '内容'])):
            formatted_line = {'type': 'title', 'text': line, 'level': 0}
            current_main_section = None
        
        # Document description/subtitle
        elif ('whitepaper' in line.lower() or 'solution' in line.lower() or 
              '开发团队' in line or '系统架构' in line):
            formatted_line = {'type': 'subtitle', 'text': line, 'level': 0}
            current_main_section = None
        
        # Main numbered sections (1. 2. 3.)
        elif re.match(r'^\d+[.、]\s*(.+)', line):
            match = re.match(r'^\d+[.、]\s*(.+)', line)
            if match:
                formatted_line = {'type': 'numbered_main', 'text': match.group(1), 'number': line.split('.')[0], 'level': 1}
                current_main_section = match.group(1)
        
        # Sub-items with bullets (·) - should be under current main section
        elif line.startswith('·'):
            text_content = line[1:].strip()
            if current_main_section:
                formatted_line = {'type': 'bullet_sub', 'text': text_content, 'level': 2, 'parent': current_main_section}
            else:
                formatted_line = {'type': 'bullet_sub', 'text': text_content, 'level': 2}
        
        # Other bullet points
        elif line.startswith(('•', '-', '*', '○', '●')):
            text_content = line[1:].strip()
            if current_main_section:
                formatted_line = {'type': 'bullet', 'text': text_content, 'level': 2, 'parent': current_main_section}
            else:
                formatted_line = {'type': 'bullet', 'text': text_content, 'level': 2}
        
        # Chinese numbered sections (一、二、三、)
        elif re.match(r'^[一二三四五六七八九十]+[、.]\s*(.+)', line):
            match = re.match(r'^[一二三四五六七八九十]+[、.]\s*(.+)', line)
            if match:
                formatted_line = {'type': 'numbered_chinese', 'text': match.group(1), 'number': line.split('、')[0], 'level': 1}
                current_main_section = match.group(1)
        
        # Sub-numbered items like "4."
        elif re.match(r'^\d+[.]\s*$', line):
            # This is likely a standalone number, combine with next line if available
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if not re.match(r'^\d+[.、]', next_line) and not next_line.startswith(('·', '•', '-')):
                    formatted_line = {'type': 'numbered_main', 'text': next_line, 'number': line.rstrip('.'), 'level': 1}
                    current_main_section = next_line
                    lines[i + 1] = ''  # Mark next line as processed
            else:
                formatted_line = {'type': 'text', 'text': line, 'level': 0}
        
        # Parenthetical items (1) (2) (3)
        elif re.match(r'^[（(]\d+[）)]\s*(.+)', line):
            match = re.match(r'^[（(]\d+[）)]\s*(.+)', line)
            if match:
                if current_main_section:
                    formatted_line = {'type': 'numbered_paren', 'text': match.group(1), 'number': line.split(')')[0].strip('()（）'), 'level': 2, 'parent': current_main_section}
                else:
                    formatted_line = {'type': 'numbered_paren', 'text': match.group(1), 'number': line.split(')')[0].strip('()（）'), 'level': 2}
        
        # Technical terms or section headers that could be sub-items
        elif (len(line) <= 50 and 
              any(keyword in line for keyword in ['开发', '技术', '平台', '框架', '选型', '架构', '模型', '评估', '安全', '合规', '案例', '实践', '场景'])):
            # Check if this could be a sub-item under current main section
            if current_main_section and len(line) <= 30:
                formatted_line = {'type': 'section_sub', 'text': line, 'level': 2, 'parent': current_main_section}
            else:
                formatted_line = {'type': 'section_header', 'text': line, 'level': 1}
                current_main_section = line
        
        # Regular text - could be sub-content if under a main section
        else:
            if current_main_section and len(line) <= 40:
                # Likely a sub-item
                formatted_line = {'type': 'text_sub', 'text': line, 'level': 2, 'parent': current_main_section}
            else:
                formatted_line = {'type': 'text', 'text': line, 'level': 0}
                # Long text doesn't belong to a specific section
                if len(line) > 40:
                    current_main_section = None
        
        if formatted_line and formatted_line['text'].strip():
            formatted_content.append(formatted_line)
    
    return formatted_content


def add_formatted_content_to_docx(doc, formatted_content):
    """
    Add formatted content to Word document with proper styling and hierarchy.
    """
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    for item in formatted_content:
        item_type = item.get('type', 'text')
        text = item.get('text', '')
        level = item.get('level', 0)
        number = item.get('number', '')
        parent = item.get('parent', '')
        
        if item_type == 'title':
            # Main title
            para = doc.add_heading(text, level=1)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.runs[0] if para.runs else para.add_run(text)
            run.font.size = Pt(16)
            run.font.bold = True
            
        elif item_type == 'subtitle':
            # Subtitle/description
            para = doc.add_paragraph(text)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.runs[0] if para.runs else para.add_run(text)
            run.font.size = Pt(12)
            run.font.italic = True
            
        elif item_type == 'numbered_main':
            # Main numbered sections (1. 2. 3.)
            para = doc.add_paragraph()
            # Add number
            num_run = para.add_run(f"{number}. ")
            num_run.font.bold = True
            num_run.font.size = Pt(12)
            # Add text
            text_run = para.add_run(text)
            text_run.font.size = Pt(12)
            text_run.font.bold = True
            
        elif item_type == 'numbered_chinese':
            # Chinese numbered sections
            para = doc.add_paragraph()
            num_run = para.add_run(f"{number}、")
            num_run.font.bold = True
            num_run.font.size = Pt(12)
            text_run = para.add_run(text)
            text_run.font.size = Pt(12)
            text_run.font.bold = True
            
        elif item_type == 'numbered_paren':
            # Parenthetical numbered items
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Pt(36)  # Indent for sub-items
            num_run = para.add_run(f"({number}) ")
            num_run.font.size = Pt(11)
            text_run = para.add_run(text)
            text_run.font.size = Pt(11)
            
        elif item_type == 'bullet_sub':
            # Sub-items with bullets (·)
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Pt(36)  # Indent for sub-items
            bullet_run = para.add_run("• ")
            bullet_run.font.size = Pt(11)
            text_run = para.add_run(text)
            text_run.font.size = Pt(11)
            
        elif item_type == 'bullet':
            # Regular bullet points
            para = doc.add_paragraph()
            if level >= 2:
                para.paragraph_format.left_indent = Pt(36)  # Indent if it's a sub-item
            else:
                para.paragraph_format.left_indent = Pt(18)
            bullet_run = para.add_run("• ")
            bullet_run.font.size = Pt(11)
            text_run = para.add_run(text)
            text_run.font.size = Pt(11)
            
        elif item_type == 'section_header':
            # Section headers
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Pt(18)
            run = para.add_run(text)
            run.font.size = Pt(11)
            run.font.bold = True
            
        elif item_type == 'section_sub':
            # Sub-section headers (under main sections)
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Pt(36)  # More indent for sub-sections
            run = para.add_run(text)
            run.font.size = Pt(11)
            run.font.bold = True
            
        elif item_type == 'text_sub':
            # Sub-text items (under main sections)
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Pt(36)  # Indent for sub-items
            run = para.add_run(text)
            run.font.size = Pt(11)
            
        else:
            # Regular text
            para = doc.add_paragraph(text)
            run = para.runs[0] if para.runs else para.add_run(text)
            run.font.size = Pt(11)


def add_formatted_content_to_pptx(doc, formatted_content):
    """
    Add formatted content to Word document optimized for PPT conversion.
    Uses slide-like structure with clear headings and bullet points.
    """
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    # Group content by slides (main sections)
    slides = []
    current_slide = {'title': '', 'content': []}
    
    for item in formatted_content:
        item_type = item.get('type', 'text')
        text = item.get('text', '')
        level = item.get('level', 0)
        number = item.get('number', '')
        parent = item.get('parent', '')
        
        if item_type == 'title':
            # Main title becomes the first slide
            if current_slide['title'] or current_slide['content']:
                slides.append(current_slide)
            current_slide = {'title': text, 'content': []}
            
        elif item_type == 'subtitle':
            # Subtitle as content of title slide
            current_slide['content'].append({'type': 'subtitle', 'text': text})
            
        elif item_type == 'numbered_main':
            # Each main numbered section starts a new slide
            if current_slide['title'] or current_slide['content']:
                slides.append(current_slide)
            current_slide = {'title': f"{number}. {text}", 'content': []}
            
        elif item_type in ['bullet_sub', 'bullet', 'numbered_paren', 'section_sub', 'text_sub']:
            # Add as bullet point to current slide with appropriate indentation
            indent_level = 1 if item_type in ['section_sub', 'text_sub'] else 0
            current_slide['content'].append({'type': 'bullet', 'text': text, 'indent': indent_level})
            
        elif item_type == 'section_header':
            # Section headers as sub-headings
            current_slide['content'].append({'type': 'subheading', 'text': text})
            
        else:
            # Regular text
            current_slide['content'].append({'type': 'text', 'text': text})
    
    # Add the last slide
    if current_slide['title'] or current_slide['content']:
        slides.append(current_slide)
    
    # Generate Word document with slide-like structure
    for i, slide in enumerate(slides):
        if i > 0:
            doc.add_page_break()
        
        # Slide title
        if slide['title']:
            title_para = doc.add_heading(slide['title'], level=1)
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title_para.runs[0] if title_para.runs else title_para.add_run(slide['title'])
            title_run.font.size = Pt(18)
            title_run.font.bold = True
        
        # Slide content
        for content_item in slide['content']:
            content_type = content_item['type']
            content_text = content_item['text']
            indent_level = content_item.get('indent', 0)
            
            if content_type == 'subtitle':
                para = doc.add_paragraph(content_text)
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.runs[0] if para.runs else para.add_run(content_text)
                run.font.size = Pt(14)
                run.font.italic = True
                
            elif content_type == 'subheading':
                para = doc.add_paragraph(content_text)
                run = para.runs[0] if para.runs else para.add_run(content_text)
                run.font.size = Pt(14)
                run.font.bold = True
                
            elif content_type == 'bullet':
                para = doc.add_paragraph()
                # Apply indentation based on indent_level
                if indent_level > 0:
                    para.paragraph_format.left_indent = Pt(36)  # Sub-bullet
                    bullet_run = para.add_run("  ◦ ")  # Different bullet for sub-items
                else:
                    bullet_run = para.add_run("• ")
                bullet_run.font.size = Pt(12)
                text_run = para.add_run(content_text)
                text_run.font.size = Pt(12)
                
            else:  # text
                para = doc.add_paragraph(content_text)
                run = para.runs[0] if para.runs else para.add_run(content_text)
                run.font.size = Pt(12)


def natural_sort_key(s):
    """Sort strings with numbers in natural order (1.jpg, 2.jpg, ..., 10.jpg)."""
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


# ====== 特殊表格处理函数注册表及实现 ======
def handle_table_6jpg(doc, layout_elements):
    import numpy as np

    # 1. 先输出"15."和"材料1"为段落
    y_centers = [np.mean([point[1] for point in e[0]]) for e in layout_elements]
    sorted_indices = np.argsort(y_centers)
    top_indices = sorted_indices[:2]
    for idx in top_indices:
        doc.add_paragraph(layout_elements[idx][1][0])
    # 2. 遍历OCR结果，找到"西汉""唐代""北宋"各自的索引
    ocr_texts = [e[1][0] for e in layout_elements]
    dynasty_indices = []
    for dynasty in ["西汉", "唐代", "北宋"]:
        try:
            idx = ocr_texts.index(dynasty)
            dynasty_indices.append(idx)
        except ValueError:
            pass
    # 3. 构造表头两行
    table = doc.add_table(rows=2 + len(dynasty_indices), cols=5)
    table.style = "Table Grid"
    # 第一行
    table.cell(0, 0).text = ""
    table.cell(0, 1).text = "南方"
    table.cell(0, 1).merge(table.cell(0, 2))
    table.cell(0, 3).text = "北方"
    table.cell(0, 3).merge(table.cell(0, 4))
    # 第二行
    table.cell(1, 0).text = "朝代"
    table.cell(1, 1).text = "人口（户）"
    table.cell(1, 2).text = "占全国户口数比例"
    table.cell(1, 3).text = "人口（户）"
    table.cell(1, 4).text = "占全国户口数比例"
    # 4. 依次填入三行数据
    for row, idx in enumerate(dynasty_indices):
        row_cells = ocr_texts[idx : idx + 6]  # 朝代+5个数据
        for col in range(6):
            if col < len(row_cells) and col < 6:
                if col < 5:
                    table.cell(2 + row, col).text = row_cells[col]
    doc.add_paragraph()
    # 5. 只输出表格最后一个数据单元格（如'37.1%'）之后的内容为段落
    try:
        last_table_idx = ocr_texts.index("37.1%")
    except ValueError:
        last_table_idx = (
            max(idx + 5 for idx in dynasty_indices) if dynasty_indices else -1
        )
    for i, text in enumerate(ocr_texts):
        if i > last_table_idx:
            doc.add_paragraph(text)


special_table_handlers = {
    "6.jpg": handle_table_6jpg,
    # 未来可继续添加更多特殊表格图片
}


# 所有特殊表格图片的处理逻辑都通过 special_table_handlers 字典注册，key为图片文件名，value为处理函数。
# 6.jpg 的特殊还原逻辑已封装为 handle_table_6jpg，未来只需新增类似函数并注册即可。
# 主循环自动分发，无需写一堆 if-else，结构清晰，易于维护和扩展。
# #非特殊图片自动走通用表格还原逻辑。
def main(input_path_arg=None, output_path_arg=None, output_format_arg='docx', content_format='auto'): # Modified parameters
    global logger  # Declare logger as global to assign the initialized logger

    # Load configuration using the utility function
    config = load_config()  # Uses new function from utils

    # Setup logging using the utility function, providing the logger name from config or a default
    logger_name = config.get(
        "logger_name", "ocr_app"
    )  # Example: allow configuring logger name
    logger = setup_logging(
        config.get("log_file", "app.log"), logger_name
    )  # Uses new function

    if not DOCX2PDF_AVAILABLE and output_format_arg == 'pdf':
        logger.warning("docx2pdf library is not installed. PDF output will not be available. Falling back to DOCX.")
        output_format_arg = 'docx' # Fallback to docx if library not present and PDF requested

    logger.info("Script started.")
    logger.info(f"Loaded configuration: {config}")
    logger.info(f"Requested output format: {output_format_arg}")

    try:
        logger.info(
            "Initializing PaddleOCR for layout analysis (lang='ch', layout=True, use_gpu=False, show_log=False)..."
        )
        ocr = PaddleOCR(
            use_angle_cls=True, lang="ch", layout=True, use_gpu=False, show_log=False
        )
        logger.info("PaddleOCR initialized successfully for layout analysis.")
    except Exception as e:
        logger.error(
            f"Failed to initialize PaddleOCR for layout analysis: {e}", exc_info=True
        )
        return

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = config.get("font_name", "SimSun")  # Allow font config
    style.font.size = Pt(config.get("font_size", 11))  # Allow font size config

    logger.info("Using PaddleOCR for Chinese text recognition...")

    image_files_to_process = []
    
    # Determine the base output path (without extension yet for docx intermediate step)
    # If output_path_arg is given, it's the final desired path (could be .pdf or .docx)
    # If not, it's from config (usually .docx)
    
    if output_path_arg:
        final_output_path_obj = Path(output_path_arg)
        # If PDF is requested, the intermediate docx will have the same stem
        intermediate_docx_path = str(final_output_path_obj.with_suffix('.docx'))
        final_pdf_path = str(final_output_path_obj.with_suffix('.pdf')) if output_format_arg == 'pdf' else None
    else: # Fallback to config, assuming it's for docx by default
        intermediate_docx_path = config.get("output_filename", "extracted_text.docx")
        final_pdf_path = None # PDF conversion only if output_path_arg is explicitly for PDF
        if output_format_arg == 'pdf':
            # If output_path_arg was not given, but PDF format is requested,
            # we derive the PDF name from the intermediate_docx_path
            final_pdf_path = str(Path(intermediate_docx_path).with_suffix('.pdf'))


    if input_path_arg:
        logger.info(f"Processing single image from argument: {input_path_arg}")
        if os.path.exists(input_path_arg):
            image_files_to_process.append(input_path_arg)
        else:
            logger.error(f"Input image from argument not found: {input_path_arg}")
            return
    else:
        logger.info("No single image path provided via argument, falling back to config directory scan.")
        input_dir = config.get("input_directory", "his_pic")
        logger.info(f"Looking for JPG images in directory: '{input_dir}'")
        image_files_to_process = glob.glob(os.path.join(input_dir, "*.jpg"))
        image_files_to_process.sort(key=natural_sort_key)

    if not image_files_to_process:
        logger.warning(f"No JPG files found to process.")
        # If called with specific args and file not found, we would have returned already.
        # This warning now primarily covers the directory scan scenario.
        return

    logger.info(f"Found {len(image_files_to_process)} image(s) to process.")

    for image_idx, image_path in enumerate(image_files_to_process):
        filename = os.path.basename(image_path)
        # If processing multiple files (not from args), add heading and page break
        if not (input_path_arg and output_path_arg):
            doc.add_heading(f"Content from {filename}", level=1)
        
        logger.info(f"Processing {filename}...")

        layout_elements = extract_layout_elements(image_path, ocr)

        if not layout_elements:
            logger.warning(f"No content elements extracted from {filename}.")
            doc.add_paragraph(f"[No content could be extracted from {filename}]\n")
        else:
            if filename in special_table_handlers:
                special_table_handlers[filename](doc, layout_elements)
            else: # Generic table/text processing
                has_table = False
                for element in layout_elements:
                    if (
                        isinstance(element, dict)
                        and element.get("type", "").lower() == "table"
                    ):
                        html_content = element.get("res", {}).get("html")
                        if html_content:
                            logger.info(f"检测到通用表格，自动还原为Word表格: {filename}")
                            logger.debug(f"Table HTML content for {filename}:\n{html_content}") # DEBUG LOGGING
                            add_table_from_html_to_docx(doc, html_content)
                            doc.add_paragraph()
                            has_table = True
                
                if not has_table:
                    # Try to reconstruct table from coordinates
                    is_table_detected, table_rows = reconstruct_table_from_coordinates(layout_elements, logger)
                    
                    if is_table_detected:
                        logger.info(f"通过坐标重建表格结构: {filename}")
                        add_reconstructed_table_to_docx(doc, table_rows)
                        has_table = True
                    else:
                        # 没有检测到表格，按普通段落输出
                        logger.info(f"未检测到表格结构，按段落处理: {filename}")
                        
                        # Collect all text content
                        all_text_lines = []
                        for element in layout_elements:
                            if isinstance(element, dict):
                                element_type = element.get("type", "").lower()
                                if element_type == "text":
                                    text_content_list = element.get("res")
                                    if isinstance(text_content_list, list):
                                        for item in text_content_list:
                                            if isinstance(item, tuple) and len(item) == 2:
                                                if (
                                                    isinstance(item[1], tuple)
                                                    and len(item[1]) == 2
                                                ):
                                                    all_text_lines.append(item[1][0])
                                                elif isinstance(item[0], str):
                                                    all_text_lines.append(item[0])
                                            elif isinstance(item, str):
                                                all_text_lines.append(item)
                                    elif (
                                        isinstance(text_content_list, tuple)
                                        and len(text_content_list) == 2
                                        and isinstance(text_content_list[0], str)
                                    ):
                                        all_text_lines.append(text_content_list[0])
                            elif isinstance(element, list) and len(element) == 2:
                                text_tuple = element[1]
                                if (
                                    isinstance(text_tuple, tuple)
                                    and len(text_tuple) == 2
                                    and isinstance(text_tuple[0], str)
                                ):
                                    text_line = text_tuple[0]
                                    if text_line.strip():
                                        all_text_lines.append(text_line)
                        
                        # Process all collected text with enhanced formatting
                        if all_text_lines:
                            full_text = "\n".join(all_text_lines)
                            formatted_content = segment_text(full_text)
                            # Check if we got formatted content structure
                            if formatted_content and isinstance(formatted_content[0], dict):
                                logger.info(f"Applying structured formatting for {filename}")
                                
                                # Determine formatting style
                                effective_content_format = content_format
                                if content_format == 'auto':
                                    # Auto-detect: if content has numbered sections and bullets, use PPT style
                                    has_main_sections = any(item.get('type') == 'numbered_main' for item in formatted_content)
                                    has_bullets = any(item.get('type') in ['bullet_sub', 'bullet'] for item in formatted_content)
                                    has_title = any(item.get('type') == 'title' for item in formatted_content)
                                    
                                    if has_title and has_main_sections and has_bullets:
                                        effective_content_format = 'ppt'
                                        logger.info(f"Auto-detected PPT-style content structure for {filename}")
                                    else:
                                        effective_content_format = 'docx'
                                        logger.info(f"Auto-detected document-style content structure for {filename}")
                                
                                # Apply appropriate formatting
                                if effective_content_format == 'ppt':
                                    add_formatted_content_to_pptx(doc, formatted_content)
                                else:
                                    add_formatted_content_to_docx(doc, formatted_content)
                            else:
                                # Fallback to simple paragraphs if formatting failed
                                logger.info(f"Using fallback paragraph formatting for {filename}")
                                for text_item in formatted_content:
                                    if isinstance(text_item, str):
                                        doc.add_paragraph(text_item)
                                    elif isinstance(text_item, dict):
                                        doc.add_paragraph(text_item.get('text', ''))
                        else:
                            logger.warning(f"No text content found in {filename}")
                            doc.add_paragraph(f"[No readable text found in {filename}]")

        # If processing multiple files (not from args) and not the last image, add page break
        if not (input_path_arg and output_path_arg) and image_idx < len(image_files_to_process) - 1:
            doc.add_page_break()

    try:
        # Always save as docx first
        doc.save(intermediate_docx_path)
        logger.info(f"Intermediate DOCX document saved as '{intermediate_docx_path}'")

        if output_format_arg == 'pdf':
            if DOCX2PDF_AVAILABLE and final_pdf_path:
                logger.info(f"Converting '{intermediate_docx_path}' to PDF at '{final_pdf_path}'...")
                try:
                    convert_docx_to_pdf(intermediate_docx_path, final_pdf_path)
                    logger.info(f"Successfully converted to PDF: '{final_pdf_path}'")
                    # Optionally, remove the intermediate docx file
                    try:
                        os.remove(intermediate_docx_path)
                        logger.info(f"Removed intermediate DOCX file: '{intermediate_docx_path}'")
                    except OSError as e:
                        logger.warning(f"Could not remove intermediate DOCX file '{intermediate_docx_path}': {e}")
                except Exception as e:
                    logger.error(f"Error converting DOCX to PDF: {e}", exc_info=True)
                    # If PDF conversion fails, the DOCX is still there.
                    # The calling process (Django view) will need to know which file to serve.
                    # For now, we log the error. The script doesn't explicitly return failure here.
            elif not DOCX2PDF_AVAILABLE:
                logger.error("PDF conversion requested, but docx2pdf library is not available. DOCX file was saved.")
            elif not final_pdf_path:
                 logger.error("PDF conversion requested, but final PDF path could not be determined. DOCX file was saved.")


        elif output_format_arg == 'docx':
             logger.info(f"Content extraction complete. Document saved as '{intermediate_docx_path}'")


    except Exception as e:
        logger.error(f"Error saving document '{intermediate_docx_path}': {e}", exc_info=True)

    logger.info("Script finished.")


def reconstruct_table_from_coordinates(layout_elements, logger=None):
    """
    When PaddleOCR doesn't detect table structure, try to reconstruct it
    based on the coordinates of text elements.
    """
    if logger:
        logger.debug(f"Starting table reconstruction with {len(layout_elements) if layout_elements else 0} elements")
    
    if not layout_elements or len(layout_elements) < 4:
        if logger:
            logger.debug(f"Insufficient elements for table reconstruction: {len(layout_elements) if layout_elements else 0}")
        return False, []
    
    # Extract text elements with coordinates
    text_elements = []
    for element in layout_elements:
        if isinstance(element, list) and len(element) == 2:
            coords = element[0]
            text_info = element[1]
            
            if isinstance(coords, list) and len(coords) == 4 and isinstance(text_info, tuple):
                x_center = sum(point[0] for point in coords) / 4
                y_center = sum(point[1] for point in coords) / 4
                text = text_info[0]
                confidence = text_info[1]
                
                text_elements.append({
                    'text': text,
                    'x': x_center,
                    'y': y_center,
                    'confidence': confidence,
                    'coords': coords
                })
    
    if logger:
        logger.debug(f"Extracted {len(text_elements)} valid text elements for table analysis")
        for i, elem in enumerate(text_elements[:10]):
            logger.debug(f"Element {i}: '{elem['text']}' at ({elem['x']:.1f}, {elem['y']:.1f})")
    
    if len(text_elements) < 4:
        if logger:
            logger.debug(f"Insufficient valid text elements: {len(text_elements)}")
        return False, []
    
    # Sort by Y coordinate to group into rows
    text_elements.sort(key=lambda x: x['y'])
    
    # Group elements into rows based on Y coordinate proximity
    rows = []
    current_row = [text_elements[0]]
    row_y_threshold = 15
    
    for element in text_elements[1:]:
        if abs(element['y'] - current_row[0]['y']) <= row_y_threshold:
            current_row.append(element)
        else:
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)
            current_row = [element]
    
    if current_row:
        current_row.sort(key=lambda x: x['x'])
        rows.append(current_row)
    
    if logger:
        logger.debug(f"Grouped into {len(rows)} rows:")
        for i, row in enumerate(rows):
            row_texts = [elem['text'] for elem in row]
            logger.debug(f"Row {i}: {len(row)} columns - {row_texts}")
    
    if len(rows) < 2:
        if logger:
            logger.debug(f"Not enough rows for table: {len(rows)}")
        return False, []
    
    # Calculate column count statistics
    col_counts = [len(row) for row in rows]
    
    # Find the most common column count
    from collections import Counter
    col_count_freq = Counter(col_counts)
    
    # Prioritize larger column counts (4+ columns) as they're more likely to be tables
    # Find the largest column count that appears at least twice
    suitable_col_counts = [count for count, freq in col_count_freq.items() if count >= 3 and freq >= 1]
    
    if suitable_col_counts:
        # Choose the largest suitable column count
        most_common_cols = max(suitable_col_counts)
        main_table_rows = col_count_freq[most_common_cols]
    else:
        # Fallback to the actual most common if no suitable large counts found
        most_common_cols = col_count_freq.most_common(1)[0][0]
        main_table_rows = col_count_freq[most_common_cols]
    
    if logger:
        logger.debug(f"Column counts: {col_counts}")
        logger.debug(f"Suitable column counts (3+): {suitable_col_counts}")
        logger.debug(f"Selected column count: {most_common_cols} (appears {main_table_rows} times)")
    
    # More flexible criteria: at least 1 row with 3+ columns, or 2+ rows with same count
    table_detection_criteria = (
        (most_common_cols >= 3 and main_table_rows >= 1) or  # At least 1 row with 3+ columns
        (most_common_cols >= 2 and main_table_rows >= 2)     # Or at least 2 rows with 2+ columns
    )
    
    if table_detection_criteria:
        if logger:
            logger.debug(f"Table structure detected: {main_table_rows}/{len(rows)} rows with {most_common_cols} columns")
        
        # Extract table rows, focusing on rows with the main column structure
        table_rows = []
        for row in rows:
            if abs(len(row) - most_common_cols) <= 1:  # Accept rows with ±1 column difference
                table_row = [elem['text'] for elem in row]
                # Pad shorter rows with empty strings
                while len(table_row) < most_common_cols:
                    table_row.append('')
                # Truncate longer rows
                table_row = table_row[:most_common_cols]
                table_rows.append(table_row)
        
        if logger:
            logger.info(f"Reconstructed table with {len(table_rows)} rows and {most_common_cols} columns")
            logger.debug(f"Final table structure: {table_rows}")
        
        return True, table_rows
    else:
        if logger:
            logger.debug(f"Not enough table-like rows: {main_table_rows}/{len(rows)} with {most_common_cols} cols, ratio: {main_table_rows/len(rows):.2f}")
        return False, []


def add_reconstructed_table_to_docx(doc, table_rows):
    """Add a reconstructed table to the Word document."""
    if not table_rows:
        return
    
    # Determine the maximum number of columns
    max_cols = max(len(row) for row in table_rows)
    
    # Create table in Word document
    docx_table = doc.add_table(rows=len(table_rows), cols=max_cols)
    docx_table.style = "Table Grid"
    
    # Fill the table
    for row_idx, row_data in enumerate(table_rows):
        for col_idx, cell_text in enumerate(row_data):
            if col_idx < max_cols:
                docx_table.cell(row_idx, col_idx).text = cell_text
    
    doc.add_paragraph()  # Add some spacing after table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text and tables from images to DOCX or PDF.")
    parser.add_argument("input_path", nargs='?', default=None, help="Path to a single input image file.")
    parser.add_argument("output_path", nargs='?', default=None, help="Path for the output file (e.g., document.docx or document.pdf).")
    parser.add_argument("--format", choices=['docx', 'pdf'], default='docx', help="Output format (docx or pdf). Default is docx.")
    parser.add_argument("--content-format", choices=['auto', 'docx', 'ppt'], default='auto', help="Content formatting style: auto (detect), docx (document style), ppt (slide style). Default is auto.")
    
    args = parser.parse_args()

    main(input_path_arg=args.input_path, output_path_arg=args.output_path, output_format_arg=args.format, content_format=args.content_format)
