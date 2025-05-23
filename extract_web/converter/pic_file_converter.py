import os
import subprocess
import logging
from django.conf import settings

logger = logging.getLogger('converter')

def process_images_to_files(uploaded_files_info, user_converted_dir):
    """
    处理图片转文件功能
    
    Args:
        uploaded_files_info: 上传文件信息列表，每个元素包含 {'name': str, 'status': str, 'path': str}
        user_converted_dir: 用户转换文件目录路径
    
    Returns:
        tuple: (processed_results, temp_files_for_final_processing)
            - processed_results: 处理结果列表
            - temp_files_for_final_processing: 准备用于最终处理的文件列表
    """
    logger.info("Processing via imgToFile (script-based OCR to DOCX first)")
    
    processed_results = []
    temp_files_for_final_processing = []
    
    # 调用脚本为每个图片生成单独的 .docx 文件
    script_path = os.path.join(settings.BASE_DIR.parent, 'extract_text_from_images.py')
    
    for up_file_info in uploaded_files_info:
        if up_file_info['status'] == 'uploaded':
            original_name = up_file_info['name']
            input_image_path = up_file_info['path']
            temp_script_output_docx_filename = f"{os.path.splitext(original_name)[0]}_tempScriptOutput.docx"
            temp_script_output_docx_path = os.path.join(user_converted_dir, temp_script_output_docx_filename)
            
            try:
                python_executable = 'python' 
                command = [python_executable, script_path, input_image_path, temp_script_output_docx_path, '--format', 'docx']
                logger.debug(f"Executing script command: {' '.join(command)}")
                
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    check=False, 
                    encoding='utf-8', 
                    errors='replace'
                )
                
                if result.returncode == 0 and os.path.exists(temp_script_output_docx_path):
                    logger.info(f"Script successfully created DOCX: {temp_script_output_docx_path} for {original_name}")
                    temp_files_for_final_processing.append({
                        'path': temp_script_output_docx_path, 
                        'original_name': original_name,
                        'base_filename_no_ext': os.path.splitext(original_name)[0]
                    })
                else: 
                    error_message = result.stderr or result.stdout or "Script execution failed."
                    if not os.path.exists(temp_script_output_docx_path):
                         error_message += " Script output DOCX file not found."
                    logger.error(f"Error converting {original_name} by script: {error_message}")
                    processed_results.append({ 
                        'original_name': original_name,
                        'converted_name': '',
                        'download_url': '',
                        'status': 'conversion_error',
                        'message': error_message
                    })
            except Exception as e:
                logger.exception(f"Exception during script execution for {original_name}")
                processed_results.append({
                    'original_name': original_name, 
                    'status': 'conversion_error',
                    'message': f'服务器内部错误: {str(e)}'
                })
        else: 
            processed_results.append(up_file_info)
    
    return processed_results, temp_files_for_final_processing 