import os
import logging
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

logger = logging.getLogger(__name__) # Use __name__ for logger

DEFAULT_FONT = 'Helvetica'

def register_fonts_for_reportlab():
    """
    Registers common Chinese and a general-purpose font for ReportLab.
    Returns the name of a successfully registered font for CJK, or a default.
    """
    font_paths_to_try = {
        'SimSun': [
            'C:/Windows/Fonts/simsun.ttc', 
            '/usr/share/fonts/truetype/windows/simsun.ttc', 
            '/System/Library/Fonts/Supplemental/Songti.ttc' 
        ],
        'DejaVuSans': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
    }

    registered_cjk_font = None

    for font_name, paths in font_paths_to_try.items():
        for font_path in paths:
            if os.path.exists(font_path):
                try:
                    if font_name == 'SimSun' and font_path.endswith('.ttc'):
                        pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                    
                    addMapping(font_name, 0, 0, font_name)
                    addMapping(font_name, 1, 0, font_name)
                    addMapping(font_name, 0, 1, font_name)
                    addMapping(font_name, 1, 1, font_name)
                    logger.info(f"Successfully registered font '{font_name}' from '{font_path}' with ReportLab.")
                    if font_name == 'SimSun': 
                        registered_cjk_font = font_name
                    elif font_name == 'DejaVuSans' and not registered_cjk_font: 
                         registered_cjk_font = font_name
                    break 
                except Exception as e:
                    logger.warning(f"Could not register font '{font_name}' from '{font_path}': {e}")
        if registered_cjk_font and font_name == 'SimSun': 
            break

    return registered_cjk_font if registered_cjk_font else DEFAULT_FONT


def convert_txt_to_pdf(input_txt_path, output_pdf_path, font_name=None):
    """
    Converts a TXT file to a PDF file using ReportLab.

    Args:
        input_txt_path (str): The path to the input TXT file.
        output_pdf_path (str): The path to save the output PDF file.
        font_name (str, optional): The name of the font to use. Defaults to None.

    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    logger.info(f"Attempting to convert TXT '{input_txt_path}' to PDF '{output_pdf_path}'")
    
    try:
        requested_font = font_name
        font_name_to_use = None
        if requested_font:
            try:
                pdfmetrics.getFont(requested_font)
                font_name_to_use = requested_font
                logger.info(
                    f"Using requested font '{requested_font}' for PDF generation."
                )
            except KeyError:
                logger.warning(
                    f"Requested font '{requested_font}' not registered yet. Will attempt registration or fall back."
                )

        if not font_name_to_use:
            font_name_to_use = register_fonts_for_reportlab()

        logger.info(f"Using font '{font_name_to_use}' for PDF generation.")
        
        try:
            with open(input_txt_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decoding failed for {input_txt_path}. Trying with 'gbk'.")
            try:
                with open(input_txt_path, 'r', encoding='gbk') as f:
                    text_content = f.read()
            except Exception as e_gbk:
                logger.error(f"Failed to read {input_txt_path} with UTF-8 and GBK: {e_gbk}")
                return False, None, f"无法读取文件内容 (尝试了UTF-8和GBK编码): {e_gbk}"
        except Exception as e_read:
            logger.error(f"Error reading TXT file {input_txt_path}: {e_read}", exc_info=True)
            return False, None, f"读取TXT文件失败: {e_read}"

        doc = SimpleDocTemplate(output_pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontName=font_name_to_use,
            fontSize=10,
            leading=14, 
            alignment=TA_LEFT,
            wordWrap = 'CJK',
        )

        story = []
        paragraphs = text_content.replace('\t', '    ').splitlines()
        
        for para_text in paragraphs:
            if not para_text.strip(): 
                story.append(Spacer(1, body_style.leading / 2))
            else:
                p = Paragraph(para_text, body_style)
                story.append(p)

        doc.build(story)

        if os.path.exists(output_pdf_path):
            logger.info(f"Successfully converted TXT '{input_txt_path}' to PDF '{output_pdf_path}'")
            return True, output_pdf_path, None
        else:
            logger.error(f"Conversion appeared successful but output PDF file not found: {output_pdf_path}")
            return False, None, "转换TXT到PDF后未找到输出文件"

    except Exception as e:
        logger.error(f"Failed to convert TXT '{input_txt_path}' to PDF: {e}", exc_info=True)
        return False, None, f"TXT转PDF失败: {str(e)}"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    test_txt_content_chinese = """你好，世界！
这是一个包含中文内容的TXT文件。
Hello, World!
This is a test TXT file with Chinese content.

空行测试。

    Tabulator \t 字符测试。
长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长字符串。
"""
    with open("chinese_test.txt", "w", encoding="utf-8") as f:
        f.write(test_txt_content_chinese)

    test_txt_content_english = """Hello, World!
This is a simple test TXT file.
It contains multiple lines.

And an empty line.
    And a line with leading spaces and a tab \t character.
Looooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong string.
"""
    with open("english_test.txt", "w", encoding="utf-8") as f:
        f.write(test_txt_content_english)

    success_ch, pdf_path_ch, error_ch = convert_txt_to_pdf("chinese_test.txt", "chinese_test_output.pdf")
    if success_ch:
        logger.info(f"Chinese TXT to PDF conversion successful: {pdf_path_ch}")
    else:
        logger.error(f"Chinese TXT to PDF conversion failed: {error_ch}")

    success_en, pdf_path_en, error_en = convert_txt_to_pdf("english_test.txt", "english_test_output.pdf")
    if success_en:
        logger.info(f"English TXT to PDF conversion successful: {pdf_path_en}")
    else:
        logger.error(f"English TXT to PDF conversion failed: {error_en}")
        
    # Clean up test files (optional)
    # os.remove("chinese_test.txt")
    # os.remove("english_test.txt")
    # os.remove("chinese_test_output.pdf")
    # os.remove("english_test_output.pdf")
   