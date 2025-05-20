import os
import glob
import re
# import yaml # No longer needed here
# import logging # No longer needed here, managed by utils
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np # Added
from paddleocr import PaddleOCR
from docx import Document
from docx.shared import Pt
from bs4 import BeautifulSoup # Added

# Import utility functions
from utils import load_config, setup_logging # Added

# Global logger instance, will be initialized in main
logger = None # Added

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
    soup = BeautifulSoup(html_content, 'html.parser')
    table_tag = soup.find('table')

    if not table_tag:
        if logger: logger.warning("No <table> tag found in the HTML content provided for table extraction.")
        doc.add_paragraph("[Warning: Could not find table structure in provided HTML]")
        return

    html_rows = table_tag.find_all('tr')

    max_cols = 0
    for hr in html_rows:
        cols_in_row = 0
        for cell in hr.find_all(['td', 'th']):
            cols_in_row += int(cell.get('colspan', 1))
        if cols_in_row > max_cols:
            max_cols = cols_in_row
    
    if max_cols == 0 and not html_rows:
        if logger: logger.info("HTML table has no rows or columns.")
        doc.add_paragraph("[Empty Table]")
        return
    if max_cols == 0 and html_rows:
        if logger: logger.warning("HTML table has rows but no discernible columns. Adding as simple list.")
        for r_idx, hr in enumerate(html_rows):
            row_text_parts = [cell.get_text(separator=' ', strip=True) for cell in hr.find_all(['td', 'th'])]
            doc.add_paragraph(f"Row {r_idx+1}: {', '.join(row_text_parts)}")
        return

    grid = [[None for _ in range(max_cols)] for _ in range(len(html_rows))]
    temp_rows_for_docx = []

    for r_idx, hr in enumerate(html_rows):
        current_row_for_docx = []
        c_idx_grid = 0
        for cell in hr.find_all(['td', 'th']):
            while c_idx_grid < max_cols and grid[r_idx][c_idx_grid] is not None:
                c_idx_grid +=1
            
            if c_idx_grid >= max_cols: continue

            text = cell.get_text(separator='\n', strip=True)
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            current_row_for_docx.append({'text': text, 'colspan': colspan, 'rowspan': rowspan})

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
        if logger: logger.info("No data extracted from HTML table for docx table creation.")
        if html_rows:
             doc.add_paragraph("[Warning: Could not parse cells from HTML table rows]")
        return
    
    if not html_rows:
        return
        
    docx_table = doc.add_table(rows=len(html_rows), cols=max_cols)
    docx_table.style = 'Table Grid'

    for r_idx, row_content in enumerate(temp_rows_for_docx):
        c_idx_docx = 0
        for cell_info in row_content:
            if c_idx_docx >= max_cols: break

            text = cell_info['text']
            colspan = cell_info['colspan']
            rowspan = cell_info['rowspan']
            
            current_docx_cell = docx_table.cell(r_idx, c_idx_docx)
            current_docx_cell.text = text

            if colspan > 1 or rowspan > 1:
                br_r = r_idx + rowspan - 1
                br_c = c_idx_docx + colspan - 1
                if br_r < len(html_rows) and br_c < max_cols:
                    try:
                        current_docx_cell.merge(docx_table.cell(br_r, br_c))
                    except Exception as e:
                         if logger: logger.warning(f"Could not merge cells for ({r_idx},{c_idx_docx}) to ({br_r},{br_c}): {e}")
                else:
                    if logger: logger.warning(f"Merge region ({r_idx},{c_idx_docx}) to ({br_r},{br_c}) out of bounds for table ({len(html_rows)},{max_cols}).")
            
            c_idx_docx += colspan

def extract_layout_elements(image_path, ocr_instance):
    """Extract layout elements (text, tables, figures) from an image."""
    global logger
    try:
        # Pass the original image path directly to PaddleOCR
        result = ocr_instance.ocr(image_path, cls=True) 
        
        if logger:
            # Log a snippet of the raw result to understand its structure
            logger.debug(f"Raw OCR result for {image_path} (layout=True mode, no preprocessing): {str(result)[:1500]}")

        if not result: 
            if logger: logger.warning(f"OCR returned empty result for {image_path}.")
            return []

        if isinstance(result, list) and len(result) > 0:
            page_elements = result[0]
            
            if isinstance(page_elements, list):
                if logger and page_elements:
                    first_elem_type = type(page_elements[0]) if page_elements else "empty list (page_elements was empty)"
                    element_count = len(page_elements)
                    logger.debug(f"Extracted page_elements for {image_path}. Count: {element_count}. Type of first element: {first_elem_type}. Content (first 1000 chars): {str(page_elements)[:1000]}")
                elif logger and not page_elements: 
                     logger.debug(f"Extracted page_elements for {image_path} is an empty list.")
                return page_elements 
            else:
                if logger: logger.warning(f"Expected result[0] to be a list of elements for {image_path}, but got {type(page_elements)}. Content: {str(page_elements)[:500]}")
                return []
        else:
            if logger: logger.warning(f"OCR result for {image_path} is not in the expected list format or is empty. Result: {str(result)[:500]}")
            return []

    except Exception as e:
        if logger: logger.error(f"Error during layout extraction from {image_path}: {e}", exc_info=True)
        return []

def extract_text_from_image(image_path, ocr_instance):
    """Extract text from an image using PaddleOCR."""
    global logger # Ensure we are using the global logger
    try:
        # Perform OCR on the image
        result = ocr_instance.ocr(image_path, cls=True)
        
        text_lines = []
        if result and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                if line and len(line) > 1 and line[1] and len(line[1]) > 0:
                    text_lines.append(line[1][0])
        
        if not text_lines:
            if logger: # Check if logger is initialized
                logger.warning(f"No text detected in {image_path}")
            else: # Fallback if logger somehow not set, though it should be
                print(f"Warning: No text detected in {image_path}")
            return "No text detected in this image."
        
        text = '\n'.join(text_lines)
        return text
    except Exception as e:
        if logger: # Check if logger is initialized
            logger.error(f"Error processing {image_path}: {e}", exc_info=True)
        else:
            print(f"Error processing {image_path}: {e}")
        return f"Error processing image: {str(e)}"

def segment_text(text):
    """Segment the extracted text into paragraphs."""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return [text]
    return paragraphs

def natural_sort_key(s):
    """Sort strings with numbers in natural order (1.jpg, 2.jpg, ..., 10.jpg)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def main():
    global logger # Declare logger as global to assign the initialized logger

    # Load configuration using the utility function
    config = load_config() # Uses new function from utils
    
    # Setup logging using the utility function, providing the logger name from config or a default
    # The logger name in utils.py defaults to 'app_logger', which is fine.
    logger_name = config.get('logger_name', 'ocr_app') # Example: allow configuring logger name
    logger = setup_logging(config.get('log_file', 'app.log'), logger_name) # Uses new function
    
    logger.info("Script started.")
    logger.info(f"Loaded configuration: {config}")

    try:
        logger.info("Initializing PaddleOCR for layout analysis (lang='ch', layout=True, use_gpu=False, show_log=False)...")
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', layout=True, use_gpu=False, show_log=False)
        logger.info("PaddleOCR initialized successfully for layout analysis.")
    except Exception as e:
        logger.error(f"Failed to initialize PaddleOCR for layout analysis: {e}", exc_info=True)
        return

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = config.get('font_name', 'SimSun') # Allow font config
    style.font.size = Pt(config.get('font_size', 11))   # Allow font size config
    
    logger.info("Using PaddleOCR for Chinese text recognition...")
    
    input_dir = config.get('input_directory', 'his_pic')
    logger.info(f"Looking for JPG images in directory: '{input_dir}'")

    image_files = glob.glob(os.path.join(input_dir, '*.jpg'))
    image_files.sort(key=natural_sort_key)
    
    if not image_files:
        logger.warning(f"No JPG files found in the '{input_dir}' directory.")
        return
    
    logger.info(f"Found {len(image_files)} image(s) to process.")

    table_image_filenames = {"6.jpg"}  # 只对这些图片自动还原为表格
    for image_idx, image_path in enumerate(image_files):
        filename = os.path.basename(image_path)
        doc.add_heading(f"Content from {filename}", level=1)
        logger.info(f"Processing {filename}...")

        layout_elements = extract_layout_elements(image_path, ocr)

        if not layout_elements:
            logger.warning(f"No content elements extracted from {filename}.")
            doc.add_paragraph(f"[No content could be extracted from {filename}]\n")
        else:
            # 只对白名单里的图片自动还原为带边框表格
            if filename in table_image_filenames:
                import numpy as np
                def group_boxes_by_lines(elements, y_threshold=20):
                    lines = []
                    for elem in elements:
                        bbox, (text, score) = elem
                        y_center = np.mean([point[1] for point in bbox])
                        placed = False
                        for line in lines:
                            if abs(line[0]['y_center'] - y_center) < y_threshold:
                                line.append({'bbox': bbox, 'text': text, 'y_center': y_center})
                                placed = True
                                break
                        if not placed:
                            lines.append([{'bbox': bbox, 'text': text, 'y_center': y_center}])
                    lines = sorted(lines, key=lambda l: l[0]['y_center'])
                    for line in lines:
                        line.sort(key=lambda cell: np.mean([point[0] for point in cell['bbox']]))
                    return lines
                lines = group_boxes_by_lines(layout_elements)
                table = doc.add_table(rows=len(lines), cols=max(len(line) for line in lines))
                table.style = 'Table Grid'
                for r, line in enumerate(lines):
                    for c, cell in enumerate(line):
                        table.cell(r, c).text = cell['text']
                doc.add_paragraph()
                continue  # 跳过后续所有文本处理
            # 其余情况全部用段落输出
            for element in layout_elements:
                # Check if the element is in the expected dictionary format for layout analysis
                if isinstance(element, dict):
                    element_type = element.get('type', '').lower()
                    # logger.debug(f"Layout Element (dict): {element}")

                    if element_type == 'table':
                        html_content = element.get('res', {}).get('html')
                        if html_content:
                            logger.info(f"Found table in {filename}. Attempting to add to document.")
                            try:
                                add_table_from_html_to_docx(doc, html_content)
                                doc.add_paragraph() 
                            except Exception as e:
                                logger.error(f"Failed to add table from HTML for {filename}: {e}", exc_info=True)
                                doc.add_paragraph(f"[Error processing table from {filename}. Falling back to text extraction.]")
                                raw_text_from_table = []
                                if isinstance(element.get('res'), dict) and 'cells' in element.get('res', {}):
                                    for cell_data in element.get('res', {}).get('cells', []):
                                        if isinstance(cell_data, dict) and 'text' in cell_data:
                                            # Ensure cell_data['text'] is a list of strings, or a single string
                                            cell_text_content = cell_data['text']
                                            if isinstance(cell_text_content, list):
                                                raw_text_from_table.extend(cell_text_content)
                                            elif isinstance(cell_text_content, str):
                                                raw_text_from_table.append(cell_text_content)
                                if raw_text_from_table:
                                    text_to_add = '\n'.join(raw_text_from_table)
                                    paragraphs = segment_text(text_to_add)
                                    for p_text in paragraphs: doc.add_paragraph(p_text)
                                else:
                                    doc.add_paragraph("[Could not extract fallback text from table structure]")
                        else:
                            logger.warning(f"Table element found in {filename} but no HTML content. Treating as text.")
                            text_content_list = element.get('res')
                            extracted_lines = []
                            if isinstance(text_content_list, list):
                                for item in text_content_list:
                                    if isinstance(item, tuple) and len(item) == 2:
                                        if isinstance(item[1], tuple) and len(item[1]) == 2: extracted_lines.append(item[1][0])
                                        elif isinstance(item[0], str): extracted_lines.append(item[0])
                                    elif isinstance(item, str): extracted_lines.append(item)
                            elif isinstance(text_content_list, tuple) and len(text_content_list) == 2 and isinstance(text_content_list[0], str):
                                extracted_lines.append(text_content_list[0])
                            
                            if extracted_lines:
                                full_text = '\n'.join(extracted_lines)
                                paragraphs = segment_text(full_text)
                                for paragraph_text in paragraphs: doc.add_paragraph(paragraph_text)
                            else:
                                doc.add_paragraph(f"[Table detected in {filename}, but no parsable content found.]")

                    elif element_type == 'text':
                        text_content_list = element.get('res')
                        extracted_lines = []
                        if isinstance(text_content_list, list):
                            for item in text_content_list:
                                if isinstance(item, tuple) and len(item) == 2:
                                    if isinstance(item[1], tuple) and len(item[1]) == 2:
                                        extracted_lines.append(item[1][0])
                                    elif isinstance(item[0], str):
                                         extracted_lines.append(item[0])
                                elif isinstance(item, str):
                                    extracted_lines.append(item)
                        elif isinstance(text_content_list, tuple) and len(text_content_list) == 2 and isinstance(text_content_list[0], str):
                             extracted_lines.append(text_content_list[0])
                        # else: logger.warning(f"Text element in {filename} has unexpected 'res' format: {type(text_content_list)}")
                        
                        if extracted_lines:
                            full_text = '\n'.join(extracted_lines)
                            paragraphs = segment_text(full_text)
                            for paragraph_text in paragraphs: doc.add_paragraph(paragraph_text)

                    elif element_type == 'figure':
                        logger.info(f"Figure detected in {filename}, placeholder added.")
                        doc.add_paragraph(f"[Figure detected in {filename} - content not extracted]")
                    # else: logger.info(f"Unhandled layout element type '{element_type}' in {filename}.")
                
                # Handle case where element is a list (e.g., [bbox, (text, score)]) from non-layout or failed layout OCR
                elif isinstance(element, list) and len(element) == 2:
                    # Assuming it matches [bbox, (text, score)] structure
                    # logger.debug(f"Layout Element (list - likely text line): {element}")
                    text_tuple = element[1]
                    if isinstance(text_tuple, tuple) and len(text_tuple) == 2 and isinstance(text_tuple[0], str):
                        text_line = text_tuple[0]
                        if text_line.strip(): # Add if there is actual text
                            # Here, we treat each such list as a single line of text.
                            # For multiple lines, they should appear as separate elements in layout_elements.
                            paragraphs = segment_text(text_line) # segment_text expects a block of text
                            for paragraph_text in paragraphs:
                                doc.add_paragraph(paragraph_text)
                    # else: logger.warning(f"Skipping list element in layout_elements, unexpected structure: {str(element)[:100]}")
                
                # else:
                    # if logger:
                        # logger.warning(f"Skipping element of unexpected type in layout_elements: {type(element)} - {str(element)[:100]}")

        if image_idx < len(image_files) - 1: # Add page break if not the last image
            doc.add_page_break()
    
    output_file = config.get('output_filename', 'extracted_text.docx')
    try:
        doc.save(output_file)
        logger.info(f"Content extraction complete. Document saved as '{output_file}'")
    except Exception as e:
        logger.error(f"Error saving document '{output_file}': {e}", exc_info=True)

    logger.info("Script finished.")

if __name__ == "__main__":
    main() 