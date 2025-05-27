import subprocess
import os
import logging
from pathlib import Path
# Import the generic LibreOffice converter
from .libreoffice_converter import convert_to_pdf as lo_convert_to_pdf 

logger = logging.getLogger('converter')

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

def convert_pptx_to_pdf(input_path, output_pdf_path):
    """
    转换PPTX到PDF的主函数，按优先级尝试不同方案
    
    Args:
        input_path: 输入的PPTX文件路径
        output_pdf_path: 期望的输出PDF文件路径
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    logger.info(f"开始转换PPTX到PDF: {input_path} -> {output_pdf_path}")
    
    # --- 方案1: LibreOffice (using the generic converter) ---
    output_dir_for_lo = os.path.dirname(output_pdf_path)
    
    # Ensure output directory exists for LO converter
    if not os.path.isdir(output_dir_for_lo):
        try:
            os.makedirs(output_dir_for_lo, exist_ok=True)
        except OSError as e:
            logger.error(f"创建LibreOffice输出目录失败 '{output_dir_for_lo}': {e}")
            # If we can't even create the directory, LO step will fail, so we might report this early
            # or let lo_convert_to_pdf handle it (it also checks output_dir).
            # For now, let lo_convert_to_pdf handle its own dir checks.
            pass

    # Call the generic LibreOffice converter.
    # lo_convert_to_pdf expects an output_dir, not a full output_path.
    # It returns the actual path of the created PDF (e.g., input_filename.pdf in output_dir)
    lo_success, lo_actual_pdf_path_or_error, lo_original_filename = lo_convert_to_pdf(input_path, output_dir_for_lo)
    
    if lo_success:
        # If the path LibreOffice used is not the final desired output_pdf_path, move/rename it.
        if lo_actual_pdf_path_or_error != output_pdf_path:
            try:
                if os.path.exists(output_pdf_path):
                    logger.warning(f"目标PDF路径 {output_pdf_path} 已存在。将进行覆盖。")
                    os.remove(output_pdf_path)
                os.rename(lo_actual_pdf_path_or_error, output_pdf_path)
                logger.info(f"PPTX到PDF（LibreOffice）：成功将 '{lo_actual_pdf_path_or_error}' 重命名/移动到 '{output_pdf_path}'")
                return True, output_pdf_path, os.path.basename(output_pdf_path)
            except Exception as e_move:
                error_msg_move = f"PPTX到PDF（LibreOffice）转换成功，但重命名/移动文件失败 从 '{lo_actual_pdf_path_or_error}' 到 '{output_pdf_path}': {e_move}"
                logger.error(error_msg_move)
                # Return success as True because PDF was created, but provide the path where it is, and the error.
                return True, lo_actual_pdf_path_or_error, error_msg_move # Error message in the third element now
        else:
            # File is already at the desired output_pdf_path
            logger.info(f"PPTX到PDF（LibreOffice）成功，文件已在: {output_pdf_path}")
            return True, output_pdf_path, lo_original_filename # Original name from LO
    else:
        logger.warning(f"LibreOffice (通用转换器) 转换PPTX到PDF失败: {lo_actual_pdf_path_or_error}")
        # lo_actual_pdf_path_or_error contains the error message from lo_convert_to_pdf

    # --- 方案2: PowerPoint COM (仅Windows + Office) ---
    # Only try this if LibreOffice failed and the error from LO wasn't a critical setup issue like soffice not found.
    # We might want to be more specific about which LO errors should prevent COM attempt.
    # For now, if lo_success is false, we proceed to COMtypes.
    
    com_success, com_result_path, com_error = convert_pptx_to_pdf_comtypes(input_path, output_pdf_path)
    if com_success:
        return com_success, com_result_path, None # No specific original_filename from COM like LO gives
    
    logger.warning(f"PowerPoint COM转换失败: {com_error}")
    
    # 所有方案都失败
    # The error message from the last attempted method (COM, or LO if COM was skipped) is more relevant.
    final_error_detail = com_error if 'com_error' in locals() and com_error else lo_actual_pdf_path_or_error
    final_error = f"所有PPTX转PDF转换方案都失败。最后错误: {final_error_detail}"
    logger.error(final_error)
    return False, None, final_error 
