import subprocess
import os
import logging
from pathlib import Path
import tempfile
import shutil

logger = logging.getLogger('converter')

def convert_excel_to_pdf_libreoffice(input_path, output_path):
    """
    使用LibreOffice命令行工具转换Excel到PDF，优化大表显示
    
    Args:
        input_path: 输入的Excel文件路径(.xls/.xlsx)
        output_path: 期望的输出PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    temp_profile_dir = tempfile.mkdtemp(prefix='libreoffice_profile_')
    user_install_path = f"file:///{temp_profile_dir.replace(os.sep, '/')}"
    
    soffice_input_copy = ""

    try:
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        base_name_orig, ext_orig = os.path.splitext(os.path.basename(input_path))
        input_dir_orig = os.path.dirname(input_path)
        with tempfile.NamedTemporaryFile(dir=input_dir_orig, prefix=f"{base_name_orig}_soffice_in_", suffix=ext_orig, delete=False) as tmp_file_obj:
            soffice_input_copy = tmp_file_obj.name
        
        shutil.copy2(input_path, soffice_input_copy)
        logger.info(f"Created temporary copy for soffice input: {soffice_input_copy} from {input_path}")

        cmd = [
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            f'-env:UserInstallation={user_install_path}',
            soffice_input_copy
        ]
        
        logger.info(f"Running LibreOffice command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=True
        )
        
        actual_soffice_output_pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(soffice_input_copy))[0] + ".pdf")
        
        if os.path.exists(actual_soffice_output_pdf):
            if actual_soffice_output_pdf != output_path:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        logger.info(f"Removed existing file at final output path: {output_path}")
                    except OSError as e_rm_target:
                        logger.warning(f"Could not remove existing file at final output path {output_path}: {e_rm_target}. Rename might fail.")
                try:
                    os.rename(actual_soffice_output_pdf, output_path)
                    logger.info(f"Renamed soffice output {actual_soffice_output_pdf} to {output_path}")
                except OSError as e_rename:
                    error_msg = f"LibreOffice produced PDF {actual_soffice_output_pdf}, but failed to rename it to {output_path}: {e_rename}"
                    logger.error(error_msg)
                    return False, None, error_msg
            
            return True, output_path, None
        else:
            error_msg = f"LibreOffice转换完成，但未找到期望的输出文件: {actual_soffice_output_pdf} (based on soffice input {soffice_input_copy})"
            logger.error(error_msg)
            return False, None, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "LibreOffice转换超时（180秒）"
        logger.error(error_msg)
        return False, None, error_msg
    except subprocess.CalledProcessError as e:
        error_output = e.stderr if e.stderr else (e.stdout if e.stdout else "No output from soffice")
        error_msg = f"LibreOffice转换失败 (exit code {e.returncode}): {error_output.strip()}"
        logger.error(error_msg)
        return False, None, error_msg
    except FileNotFoundError:
        error_msg = "LibreOffice (soffice) 未安装或未在系统PATH中"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"LibreOffice转换时发生未知错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg
    finally:
        if soffice_input_copy and os.path.exists(soffice_input_copy):
            try:
                os.remove(soffice_input_copy)
                logger.info(f"Successfully removed temporary soffice input copy: {soffice_input_copy}")
            except Exception as e_rm_copy:
                logger.warning(f"Failed to remove temporary soffice input copy {soffice_input_copy}: {e_rm_copy}")
        
        if os.path.exists(temp_profile_dir):
            try:
                shutil.rmtree(temp_profile_dir)
                logger.info(f"Successfully removed temporary LibreOffice profile directory: {temp_profile_dir}")
            except Exception as e_rm_profile:
                logger.warning(f"Failed to remove temporary LibreOffice profile directory {temp_profile_dir}: {e_rm_profile}")

def register_chinese_fonts():
    """注册中文字体以支持中文显示"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.fonts import addMapping
        
        # 尝试注册常见的中文字体
        font_paths = [
            'C:/Windows/Fonts/simsun.ttc',  # 宋体
            'C:/Windows/Fonts/simhei.ttf',  # 黑体
            'C:/Windows/Fonts/simkai.ttf',  # 楷体
            'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
            # For Linux, common paths could be:
            # '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            # '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        ]
        
        # 为Linux环境调整字体名称和添加映射的逻辑可能需要更通用
        # 例如，不仅仅基于文件名后缀，可能需要检查字体元数据或使用更标准的名称

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_name_map = {
                        'simsun.ttc': ('SimSun', 0),
                        'simhei.ttf': ('SimHei', None),
                        'simkai.ttf': ('SimKai', None),
                        'msyh.ttc': ('Microsoft-YaHei', 0),
                        'wqy-microhei.ttc': ('WenQuanYiMicroHei', None), # Example for Linux
                        'NotoSansCJK-Regular.ttc': ('NotoSansCJK', None) # Example for Linux
                    }
                    
                    base_font_file = os.path.basename(font_path)
                    if base_font_file in font_name_map:
                        font_register_name, subfont_idx = font_name_map[base_font_file]
                        if subfont_idx is not None:
                            pdfmetrics.registerFont(TTFont(font_register_name, font_path, subfontIndex=subfont_idx))
                        else:
                            pdfmetrics.registerFont(TTFont(font_register_name, font_path))
                        
                        # Basic mapping, might need refinement for bold/italic if separate font files are not used
                        addMapping(font_register_name, 0, 0, font_register_name) # normal
                        addMapping(font_register_name, 1, 0, font_register_name) # bold (map to normal if no bold variant registered)
                        addMapping(font_register_name, 0, 1, font_register_name) # italic (map to normal)
                        addMapping(font_register_name, 1, 1, font_register_name) # bold-italic (map to normal)

                        logger.info(f"Successfully registered font: {font_register_name} from {font_path}")
                        return font_register_name # Return the first successfully registered font
                except Exception as e:
                    logger.warning(f"Failed to register font {font_path}: {e}")
                    continue
        
        logger.warning("No suitable Chinese/CJK fonts found or registered from predefined paths, using default Helvetica.")
        return 'Helvetica'
        
    except ImportError:
        logger.warning("ReportLab not available for font registration, using default Helvetica.")
        return 'Helvetica'

def convert_excel_to_pdf_openpyxl(input_path, output_path):
    """
    使用openpyxl和reportlab创建带工作表标题的优化PDF，支持中文和超宽表格
    
    Args:
        input_path: 输入的Excel文件路径(.xls/.xlsx)
        output_path: 输出的PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        from openpyxl import load_workbook
        from reportlab.lib.pagesizes import A4, A3, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        
        chinese_font = register_chinese_fonts()
        
        wb = load_workbook(input_path, data_only=True)
        page_size = landscape(A3)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=0.3*cm,
            leftMargin=0.3*cm,
            topMargin=0.5*cm,
            bottomMargin=0.3*cm
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.darkblue
        )
        story = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            title = Paragraph(f"<b>{sheet_name}</b>", title_style)
            story.append(title)
            story.append(Spacer(1, 10))
            data = []
            max_col = 0
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    row_data = [str(cell).strip() if cell is not None else '' for cell in row]
                    data.append(row_data)
                    max_col = max(max_col, len(row_data))
            if data:
                for row in data:
                    while len(row) < max_col:
                        row.append('')
                available_width = page_size[0] - doc.leftMargin - doc.rightMargin
                col_width = available_width / max_col if max_col > 0 else available_width / 10
                min_col_width = 0.8*cm
                max_col_width = 4*cm
                col_width = max(min_col_width, min(col_width, max_col_width))
                table = Table(data, colWidths=[col_width] * max_col)
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), chinese_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('FONTNAME', (0, 1), (-1, -1), chinese_font),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ])
                table.setStyle(table_style)
                story.append(table)
                story.append(Spacer(1, 20))
                logger.info(f"Processed worksheet '{sheet_name}' with {len(data)} rows and {max_col} columns, col_width: {col_width}")
        doc.build(story)
        if os.path.exists(output_path):
            logger.info(f"OpenPyXL转换成功: {output_path}")
            return True, output_path, None
        else:
            error_msg = "OpenPyXL转换完成，但未找到输出文件"
            logger.error(error_msg)
            return False, None, error_msg
    except ImportError as e:
        error_msg = f"所需库未安装 (openpyxl/reportlab): {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"OpenPyXL转换失败: {str(e)}"
        logger.error(error_msg, exc_info=True) # Added exc_info=True for better debugging
        return False, None, error_msg

def convert_excel_to_pdf(input_path, output_path):
    """
    转换Excel到PDF的主函数，按优先级尝试不同方案
    
    Args:
        input_path: 输入的Excel文件路径(.xls/.xlsx)
        output_path: 输出的PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    logger.info(f"开始转换Excel到PDF: {input_path} -> {output_path}")
    
    # 方案1: LibreOffice - 跨平台，中文支持良好
    # LibreOffice 应该作为首选，因为它对复杂格式和功能的兼容性通常优于纯Python方案
    success, result_path, error = convert_excel_to_pdf_libreoffice(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"LibreOffice转换失败: {error}. Falling back to OpenPyXL+ReportLab.")
    
    # 方案2: OpenPyXL + ReportLab - 自定义方案，现在支持中文字体
    success, result_path, error = convert_excel_to_pdf_openpyxl(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"OpenPyXL+ReportLab转换也失败: {error}")
    
    # 所有方案都失败
    final_error = "所有Excel转PDF转换方案(LibreOffice, OpenPyXL+ReportLab)都失败。请检查LibreOffice是否正确安装和配置，或检查文件内容。"
    logger.error(final_error)
    return False, None, final_error 