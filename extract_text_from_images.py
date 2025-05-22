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
    """Segment the extracted text into paragraphs."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return [text]
    return paragraphs


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
def main(input_path_arg=None, output_path_arg=None, output_format_arg='docx'): # Modified parameters
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
                            add_table_from_html_to_docx(doc, html_content)
                            doc.add_paragraph()
                            has_table = True
                if not has_table:
                    # 没有检测到表格，按普通段落输出
                    for element in layout_elements:
                        if isinstance(element, dict):
                            element_type = element.get("type", "").lower()
                            if element_type == "text":
                                text_content_list = element.get("res")
                                extracted_lines = []
                                if isinstance(text_content_list, list):
                                    for item in text_content_list:
                                        if isinstance(item, tuple) and len(item) == 2:
                                            if (
                                                isinstance(item[1], tuple)
                                                and len(item[1]) == 2
                                            ):
                                                extracted_lines.append(item[1][0])
                                            elif isinstance(item[0], str):
                                                extracted_lines.append(item[0])
                                        elif isinstance(item, str):
                                            extracted_lines.append(item)
                                elif (
                                    isinstance(text_content_list, tuple)
                                    and len(text_content_list) == 2
                                    and isinstance(text_content_list[0], str)
                                ):
                                    extracted_lines.append(text_content_list[0])
                                if extracted_lines:
                                    full_text = "\n".join(extracted_lines)
                                    paragraphs = segment_text(full_text)
                                    for paragraph_text in paragraphs:
                                        doc.add_paragraph(paragraph_text)
                        elif isinstance(element, list) and len(element) == 2:
                            text_tuple = element[1]
                            if (
                                isinstance(text_tuple, tuple)
                                and len(text_tuple) == 2
                                and isinstance(text_tuple[0], str)
                            ):
                                text_line = text_tuple[0]
                                if text_line.strip():
                                    paragraphs = segment_text(text_line)
                                    for paragraph_text in paragraphs:
                                        doc.add_paragraph(paragraph_text)

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text and tables from images to DOCX or PDF.")
    parser.add_argument("input_path", nargs='?', default=None, help="Path to a single input image file.")
    parser.add_argument("output_path", nargs='?', default=None, help="Path for the output file (e.g., document.docx or document.pdf).")
    parser.add_argument("--format", choices=['docx', 'pdf'], default='docx', help="Output format (docx or pdf). Default is docx.")
    
    args = parser.parse_args()

    main(input_path_arg=args.input_path, output_path_arg=args.output_path, output_format_arg=args.format)
