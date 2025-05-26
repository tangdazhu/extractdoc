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

def convert_excel_to_pdf_comtypes(input_path, output_path):
    """
    使用comtypes调用Excel COM对象转换Excel到PDF，支持多工作表和大表优化
    
    Args:
        input_path: 输入的Excel文件路径(.xls/.xlsx)
        output_path: 输出的PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    excel = None
    workbook = None
    try:
        import comtypes.client
        
        # 启动Excel应用程序（headless模式）
        excel = comtypes.client.CreateObject("Excel.Application")
        excel.Visible = False  # 设置为不可见（headless模式）
        excel.DisplayAlerts = False  # 禁用警告对话框
        
        # 打开Excel文件
        workbook = excel.Workbooks.Open(os.path.abspath(input_path))
        
        # 优化每个工作表的页面设置
        for worksheet in workbook.Worksheets:
            # 设置页面布局为横向（适合宽表格）
            worksheet.PageSetup.Orientation = 2  # xlLandscape = 2
            # 设置缩放以适应页面宽度
            worksheet.PageSetup.Zoom = False
            worksheet.PageSetup.FitToPagesWide = 1
            worksheet.PageSetup.FitToPagesTall = False  # 允许多页高度
            # 设置页边距（最小化以获得更多空间）
            worksheet.PageSetup.LeftMargin = excel.Application.InchesToPoints(0.1)
            worksheet.PageSetup.RightMargin = excel.Application.InchesToPoints(0.1)
            worksheet.PageSetup.TopMargin = excel.Application.InchesToPoints(0.3)
            worksheet.PageSetup.BottomMargin = excel.Application.InchesToPoints(0.3)
            # 设置页眉和页脚边距
            worksheet.PageSetup.HeaderMargin = excel.Application.InchesToPoints(0.2)
            worksheet.PageSetup.FooterMargin = excel.Application.InchesToPoints(0.2)
            
            # 添加工作表名称作为页眉（使用粗体和较大字号）
            worksheet.PageSetup.CenterHeader = f"&B&18{worksheet.Name}"
            
            # 设置打印质量和网格线
            worksheet.PageSetup.PrintQuality = 600  # 高质量打印
            worksheet.PageSetup.PrintGridlines = True  # 显示网格线
            
            logger.info(f"Optimized page setup for worksheet: {worksheet.Name}")
        
        # 导出为PDF，包含所有工作表
        workbook.ExportAsFixedFormat(
            Type=0,  # xlTypePDF
            Filename=os.path.abspath(output_path),
            Quality=0,  # xlQualityStandard = 0, xlQualityMinimum = 1
            IncludeDocProps=True,
            IgnorePrintAreas=False,
            OpenAfterPublish=False
        )
        
        # workbook.Close() # Not strictly necessary before Quit if not saving changes
        # excel.Quit()     # Moved to finally block
        
        if os.path.exists(output_path):
            logger.info(f"Excel COM转换成功: {output_path}")
            return True, output_path, None
        else:
            error_msg = "Excel COM转换完成，但未找到输出文件"
            logger.error(error_msg)
            # Attempt to quit even if output not found, before returning
            # This path might indicate an issue with ExportAsFixedFormat not completing as expected
            return False, None, error_msg
            
    except ImportError:
        error_msg = "comtypes库未安装"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Excel COM转换失败: {str(e)}"
        logger.error(error_msg, exc_info=True) # Added exc_info=True
        return False, None, error_msg
    finally:
        if workbook is not None:
            try:
                workbook.Close(SaveChanges=False) # False ensures no prompts if there were accidental changes
                logger.info("Excel workbook closed via COM in finally block.")
            except Exception as e_close:
                logger.warning(f"Error closing Excel workbook via COM in finally block: {e_close}", exc_info=True)
        if excel is not None:
            try:
                excel.Quit()
                logger.info("Excel application quit via COM in finally block.")
            except Exception as e_quit:
                logger.warning(f"Error quitting Excel application via COM in finally block: {e_quit}", exc_info=True)
        # Optional: Force garbage collection to help release COM objects, though not always guaranteed effective immediately.
        # import gc
        # del workbook
        # del excel
        # gc.collect()

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
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    if font_path.endswith('simsun.ttc'):
                        pdfmetrics.registerFont(TTFont('SimSun', font_path, subfontIndex=0))
                        addMapping('SimSun', 0, 0, 'SimSun')  # normal
                        addMapping('SimSun', 1, 0, 'SimSun')  # bold
                        logger.info("Successfully registered SimSun font")
                        return 'SimSun'
                    elif font_path.endswith('simhei.ttf'):
                        pdfmetrics.registerFont(TTFont('SimHei', font_path))
                        addMapping('SimHei', 0, 0, 'SimHei')
                        addMapping('SimHei', 1, 0, 'SimHei')
                        logger.info("Successfully registered SimHei font")
                        return 'SimHei'
                    elif font_path.endswith('msyh.ttc'):
                        pdfmetrics.registerFont(TTFont('Microsoft-YaHei', font_path, subfontIndex=0))
                        addMapping('Microsoft-YaHei', 0, 0, 'Microsoft-YaHei')
                        addMapping('Microsoft-YaHei', 1, 0, 'Microsoft-YaHei')
                        logger.info("Successfully registered Microsoft YaHei font")
                        return 'Microsoft-YaHei'
                except Exception as e:
                    logger.warning(f"Failed to register font {font_path}: {e}")
                    continue
        
        # 如果都失败了，使用默认字体
        logger.warning("No Chinese fonts found, using default font")
        return 'Helvetica'
        
    except ImportError:
        logger.warning("ReportLab not available for font registration")
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
        
        # 注册中文字体
        chinese_font = register_chinese_fonts()
        
        # 加载Excel工作簿
        wb = load_workbook(input_path, data_only=True)
        
        # 根据表格宽度选择页面大小（A3横向以支持更宽的表格）
        page_size = landscape(A3)  # 使用A3横向，提供更大的宽度
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=0.3*cm,  # 进一步减小页边距
            leftMargin=0.3*cm,
            topMargin=0.5*cm,
            bottomMargin=0.3*cm
        )
        
        # 样式设置
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=18,
            spaceAfter=20,
            alignment=1,  # 居中
            textColor=colors.darkblue
        )
        
        story = []
        
        # 处理每个工作表
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            
            # 添加工作表标题
            title = Paragraph(f"<b>{sheet_name}</b>", title_style)
            story.append(title)
            story.append(Spacer(1, 10))
            
            # 获取工作表数据
            data = []
            max_col = 0
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):  # 跳过空行
                    # 转换None为空字符串，确保中文正确显示
                    row_data = [str(cell).strip() if cell is not None else '' for cell in row]
                    data.append(row_data)
                    max_col = max(max_col, len(row_data))
            
            if data:
                # 确保所有行有相同的列数
                for row in data:
                    while len(row) < max_col:
                        row.append('')
                
                # 计算列宽：根据页面宽度和列数动态调整
                available_width = page_size[0] - doc.leftMargin - doc.rightMargin
                col_width = available_width / max_col if max_col > 0 else available_width / 10
                
                # 设置最小和最大列宽
                min_col_width = 0.8*cm
                max_col_width = 4*cm
                col_width = max(min_col_width, min(col_width, max_col_width))
                
                # 创建表格
                table = Table(data, colWidths=[col_width] * max_col)
                
                # 设置表格样式
                table_style = TableStyle([
                    # 表头样式
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), chinese_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    
                    # 数据行样式
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('FONTNAME', (0, 1), (-1, -1), chinese_font),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    
                    # 交替行颜色
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ])
                table.setStyle(table_style)
                
                story.append(table)
                story.append(Spacer(1, 20))
                
                logger.info(f"Processed worksheet '{sheet_name}' with {len(data)} rows and {max_col} columns, col_width: {col_width}")
        
        # 生成PDF
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
        logger.error(error_msg)
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
    
    # 方案1: Excel COM (Windows + Office) - 优先，因为支持完整的Excel功能和最佳的中文显示
    success, result_path, error = convert_excel_to_pdf_comtypes(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"Excel COM转换失败: {error}")
    
    # 方案2: LibreOffice - 跨平台，中文支持良好
    success, result_path, error = convert_excel_to_pdf_libreoffice(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"LibreOffice转换失败: {error}")
    
    # 方案3: OpenPyXL + ReportLab - 自定义方案，现在支持中文字体
    success, result_path, error = convert_excel_to_pdf_openpyxl(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"OpenPyXL转换失败: {error}")
    
    # 所有方案都失败
    final_error = "所有Excel转PDF转换方案都失败，请安装Microsoft Office或LibreOffice"
    logger.error(final_error)
    return False, None, final_error 