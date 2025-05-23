import subprocess
import os
import logging
from pathlib import Path

logger = logging.getLogger('converter')

def convert_pptx_to_pdf_libreoffice(input_path, output_path):
    """
    使用LibreOffice命令行工具转换PPTX到PDF
    
    Args:
        input_path: 输入的PPTX文件路径
        output_path: 期望的输出PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        # 获取输出目录
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # LibreOffice命令
        cmd = [
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            input_path
        ]
        
        logger.info(f"Running LibreOffice command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60秒超时
            check=True
        )
        
        # LibreOffice会生成与输入文件同名的PDF文件
        input_filename = os.path.basename(input_path)
        base_name = os.path.splitext(input_filename)[0]
        generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        
        if os.path.exists(generated_pdf):
            # 如果生成的文件名与期望的不同，进行重命名
            if generated_pdf != output_path:
                os.rename(generated_pdf, output_path)
                logger.info(f"Renamed {generated_pdf} to {output_path}")
            
            return True, output_path, None
        else:
            error_msg = f"LibreOffice转换完成，但未找到输出文件: {generated_pdf}"
            logger.error(error_msg)
            return False, None, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "LibreOffice转换超时（60秒）"
        logger.error(error_msg)
        return False, None, error_msg
    except subprocess.CalledProcessError as e:
        error_msg = f"LibreOffice转换失败: {e.stderr}"
        logger.error(error_msg)
        return False, None, error_msg
    except FileNotFoundError:
        error_msg = "LibreOffice未安装或未在系统PATH中"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"LibreOffice转换时发生未知错误: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def convert_pptx_to_pdf_comtypes(input_path, output_path):
    """
    使用comtypes调用PowerPoint COM对象转换PPTX到PDF（仅Windows + Office）
    
    Args:
        input_path: 输入的PPTX文件路径
        output_path: 输出的PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        import comtypes.client
        
        # 启动PowerPoint应用程序（headless模式）
        powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
        powerpoint.Visible = 0  # 设置为不可见（headless模式）
        
        # 打开PPTX文件
        presentation = powerpoint.Presentations.Open(os.path.abspath(input_path))
        
        # 导出为PDF（格式代码32代表PDF）
        presentation.SaveAs(os.path.abspath(output_path), 32)
        
        # 关闭文件和应用程序
        presentation.Close()
        powerpoint.Quit()
        
        if os.path.exists(output_path):
            logger.info(f"PowerPoint COM转换成功: {output_path}")
            return True, output_path, None
        else:
            error_msg = "PowerPoint COM转换完成，但未找到输出文件"
            logger.error(error_msg)
            return False, None, error_msg
            
    except ImportError:
        error_msg = "comtypes库未安装"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"PowerPoint COM转换失败: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg

def convert_pptx_to_pdf(input_path, output_path):
    """
    转换PPTX到PDF的主函数，按优先级尝试不同方案
    
    Args:
        input_path: 输入的PPTX文件路径
        output_path: 输出的PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    logger.info(f"开始转换PPTX到PDF: {input_path} -> {output_path}")
    
    # 方案1: LibreOffice
    success, result_path, error = convert_pptx_to_pdf_libreoffice(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"LibreOffice转换失败: {error}")
    
    # 方案2: PowerPoint COM (仅Windows + Office)
    success, result_path, error = convert_pptx_to_pdf_comtypes(input_path, output_path)
    if success:
        return success, result_path, error
    
    logger.warning(f"PowerPoint COM转换失败: {error}")
    
    # 所有方案都失败
    final_error = "所有PPTX转PDF转换方案都失败，请安装LibreOffice或Microsoft Office"
    logger.error(final_error)
    return False, None, final_error 
