from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegistrationForm, AdminUserEditForm, AdminSetPasswordForm # 更新导入
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess # For running the script
import sys # <--- ADDED IMPORT FOR SYS
import json # <--- ADDED IMPORT FOR JSON
import re # <--- ADDED IMPORT FOR RE
from django.contrib import messages # 新增导入
from django.http import JsonResponse, FileResponse, Http404, StreamingHttpResponse
from django.views.decorators.http import require_POST # To restrict to POST requests
from django.views.decorators.csrf import csrf_exempt # <<< Import csrf_exempt
import random
import string
import traceback # 新增导入 for detailed exception logging
import logging # 新增导入
from docx import Document
from docx.oxml import OxmlElement # For adding content from sub-documents
from docx.oxml.ns import qn
from pathlib import Path # 新增
from datetime import datetime # 新增 datetime
from django.urls import reverse
import shutil # Import shutil earlier as it's used in multiple places
from converter import ppt_pdf_converter # 新的导入方式
from .pic_file_converter import process_images_to_files # 导入图片转文件模块
from .excel_pdf_converter import convert_excel_to_pdf # 导入Excel转换模块
from .txt_to_pdf_converter import convert_txt_to_pdf
from .pdf_to_excel_converter import convert_pdf_to_excel
from .pdf_to_word_converter import convert_pdf_to_word, convert_and_merge_pdfs_to_docx
# Add new imports for PDF to X converters
from .pdf_to_ppt_converter import convert_pdf_to_ppt, convert_and_merge_pdfs_to_pptx
from .pdf_to_txt_converter import convert_pdf_to_txt, convert_and_merge_pdfs_to_txt
from .libreoffice_converter import convert_to_pdf as convert_to_pdf_libreoffice
from .libreoffice_converter import convert_to_pptx as convert_docx_to_pptx_libreoffice # Added import for DOCX to PPTX
from .word_to_pdf_converter import convert_word_to_pdf # ADDED: Import for the new Word to PDF converter
from django.core.exceptions import PermissionDenied # For security checks

# Import the new file handling utility
from .utils.file_handling import (
    ensure_user_directories, 
    save_uploaded_file, 
    delete_user_data_folder,
    cleanup_temp_files # Added import
)
from .utils.request_parsing import parse_conversion_request_params # Added import
from .services.response_formatters import format_json_response, format_error_response # Added import

# PDF to X Merge Converters
from .pdf_to_word_converter import convert_and_merge_pdfs_to_docx 
from .pdf_to_ppt_converter import convert_and_merge_pdfs_to_pptx 
from .pdf_to_txt_converter import convert_and_merge_pdfs_to_txt 

# Try to import docx2pdf and set a flag
DOCX2PDF_AVAILABLE_IN_VIEW = False
try:
    from docx2pdf import convert as docx_to_pdf_converter_internal
    DOCX2PDF_AVAILABLE_IN_VIEW = True
except ImportError:
    logging.warning("docx2pdf library is not installed. Word to PDF conversion will be skipped for direct docx2pdf method.")
    def docx_to_pdf_converter_internal(input_path, output_path):
        logging.error("docx2pdf is not available, cannot convert Word to PDF using this method.")
        raise NotImplementedError("docx2pdf is not installed.")

logger = logging.getLogger('converter') # 获取 logger 实例

# Attempt to import PyPDF2 for PDF merging
try:
    from PyPDF2 import PdfMerger, PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 library is not installed. Merging multiple PPT/PPTX files into a single PDF will not be available.")

# Create your views here.

def index(request):
    # 未来这里会处理表单提交和文件上传
    return render(request, "converter/index.html")

@login_required
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) 
            
            try:
                # 注册时只创建用户主目录 his_pic/<username>
                # 日期目录将在 process_images_view 中按需创建
                user_main_dir = os.path.join(settings.BASE_DIR, 'his_pic', user.username)
                os.makedirs(user_main_dir, exist_ok=True)
                logger.info(f"Created main directory for user {user.username} at {user_main_dir}")
            except OSError as e:
                logger.error(f"Error creating main directory for user {user.username}: {e}")
            
            return redirect('converter:index')  
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

# Helper to check if user is superuser
def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def admin_console_index(request):
    return render(request, 'custom_admin/admin_index.html')

@login_required
@user_passes_test(is_superuser)
def admin_user_management(request):
    # Placeholder: Add logic for user CRUD operations here
    users = User.objects.all()
    return render(request, 'custom_admin/user_management.html', {'users': users})

@login_required
@user_passes_test(is_superuser)
def admin_file_management(request):
    # Placeholder: Add logic for file management here
    return render(request, 'custom_admin/file_management.html')

@login_required
@user_passes_test(is_superuser)
def admin_delete_user(request, user_id):
    if request.method == 'POST': 
        user_to_delete = get_object_or_404(User, pk=user_id)
        if user_to_delete.is_superuser and not request.user.is_superuser: 
            messages.error(request, "您没有权限删除超级管理员用户。")
        elif user_to_delete == request.user: 
            messages.error(request, "您不能删除您自己的账户。")
        else:
            username = user_to_delete.username
            # Delete user's data folder using the utility function
            delete_success, delete_message = delete_user_data_folder(username)
            
            if delete_success:
                # It's possible the folder didn't exist, which is also a form of success for this step.
                # The message from delete_user_data_folder will be informative.
                if "成功删除" in delete_message or "does not exist" in delete_message: # Crude check, can be refined
                    messages.success(request, delete_message)
                else: # Some other non-error message from utility
                    messages.info(request, delete_message)
            else:
                messages.error(request, delete_message) # Error message from utility

            # Proceed to delete the user object regardless of folder deletion outcome, 
            # but maybe log if folder deletion failed and user was still deleted.
            if not delete_success:
                logger.warning(f"User object for '{username}' will be deleted, but their data folder deletion failed or had issues. Message: {delete_message}")
            
            user_to_delete.delete()
            messages.success(request, f"用户 '{username}' 的账户已成功删除。")
    else:
        messages.warning(request, "删除操作应通过POST请求执行。")
    
    return redirect('converter:admin_user_management')

@login_required
@user_passes_test(is_superuser)
def admin_edit_user(request, user_id):
    user_to_edit = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # 根据提交的表单类型分别处理
        if 'change_info' in request.POST:
            user_form = AdminUserEditForm(request.POST, instance=user_to_edit)
            password_form = AdminSetPasswordForm(user_to_edit) # 保持密码表单在上下文
            if user_form.is_valid():
                user_form.save()
                messages.success(request, f"用户 '{user_to_edit.username}' 的信息已更新。")
                return redirect('converter:admin_user_management')
        elif 'set_password' in request.POST:
            password_form = AdminSetPasswordForm(user_to_edit, request.POST)
            user_form = AdminUserEditForm(instance=user_to_edit) # 保持用户信息表单在上下文
            if password_form.is_valid():
                password_form.save()
                messages.success(request, f"用户 '{user_to_edit.username}' 的密码已重置。")
                return redirect('converter:admin_user_management')
        else:
            # 未知POST请求或缺少标识，可以简单地重新加载表单
            user_form = AdminUserEditForm(instance=user_to_edit)
            password_form = AdminSetPasswordForm(user_to_edit)
            messages.error(request, "无效的请求。")

    else:
        user_form = AdminUserEditForm(instance=user_to_edit)
        password_form = AdminSetPasswordForm(user_to_edit)
        
    return render(request, 'custom_admin/user_edit_form.html', {
        'user_form': user_form,
        'password_form': password_form,
        'user_to_edit': user_to_edit
    })

def append_document(source_doc, target_doc):
    """Appends content of source_doc to target_doc."""
    for element in source_doc.element.body:
        target_doc.element.body.append(element)

# --- 新的独立视图函数 ---

@login_required
@require_POST
def file_to_pdf_view(request):
    today_date_str = datetime.now().strftime("%Y%m%d")
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    logger.info(f"file_to_pdf_view: Received request. RequestID: {request_id}")

    user_upload_dir, user_converted_dir = "", ""
    try:
        user_upload_dir, user_converted_dir = ensure_user_directories(request.user.username, today_date_str)
    except Exception as e:
        logger.critical(f"file_to_pdf_view: Failed to create user directories for {request.user.username}. Error: {e}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='服务器错误：无法创建用户目录。', merge_output=merge_output_for_error, request_id=request_id)

    parsed_params = {}
    try:
        parsed_params = parse_conversion_request_params(request.POST, request_id)
    except Exception as e_parse:
        logger.error(f"file_to_pdf_view: Error parsing request parameters: {e_parse}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='请求参数错误。', merge_output=merge_output_for_error, request_id=request_id)

    sub_tab = parsed_params['sub_tab']
    merge_output = parsed_params['merge_output']
    output_format = parsed_params.get('output_format', 'pdf') # Default to pdf, relevant for this view

    # Specific check for wordToPdf if docx2pdf is unavailable
    if sub_tab == 'wordToPdf' and not DOCX2PDF_AVAILABLE_IN_VIEW:
        logger.error(f"file_to_pdf_view: wordToPdf requested, but docx2pdf is not available. RequestID: {request_id}")
        return format_error_response(
            message='Word转PDF的转换库(docx2pdf)不可用。',
            merge_output=merge_output,
            original_item_name='Conversion Library Check', # Corrected field name
            request_id=request_id
        )

    processed_files_final = []
    temp_files_to_delete_final = []

    uploaded_files_info = []
    if not request.FILES.getlist('images'): # Assuming frontend still uses 'images' field for uploads
        logger.warning(f"file_to_pdf_view: No files uploaded. RequestID: {request_id}")
        return format_error_response(message='没有上传文件。', merge_output=merge_output, request_id=request_id)

    for uploaded_file_obj in request.FILES.getlist('images'):
        temp_input_path, original_filename, safe_filename = save_uploaded_file(uploaded_file_obj, user_upload_dir, request_id)
        if temp_input_path and safe_filename:
            uploaded_files_info.append({
                'name': original_filename,
                'path': temp_input_path,
                'safe_original_filename': safe_filename,
                'status': 'uploaded'
            })
        else:
            failed_original_name = original_filename if original_filename else "未知文件"
            logger.error(f"file_to_pdf_view: Failed to save uploaded file: {failed_original_name}. RequestID: {request_id}")
            processed_files_final.append({
                'original_name': failed_original_name,
                'status': 'error',
                'message': f'文件 "{failed_original_name}" 上传保存失败。'
            })

    if not uploaded_files_info:
        logger.error(f"file_to_pdf_view: All file uploads failed or no files were valid after saving. RequestID: {request_id}")
        if not processed_files_final: # If it's empty, add a generic message
             processed_files_final.append({'original_name': 'File Upload', 'status': 'error', 'message': '所有文件上传失败或未能保存。'})
        return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

    # --- Core File to PDF conversion logic (formerly _handle_file_to_pdf) ---
    for uploaded_file_data in uploaded_files_info:
        original_name = uploaded_file_data['name']
        temp_input_path = uploaded_file_data['path']
        safe_original_filename = uploaded_file_data['safe_original_filename']

        base_name_no_ext = os.path.splitext(safe_original_filename)[0]
        unique_pdf_filename = f"{base_name_no_ext}_{request_id}.pdf"
        output_pdf_path = os.path.join(user_converted_dir, unique_pdf_filename)

        success_conv = False
        conversion_message_conv = "不支持的文件类型或转换失败。"
        actual_output_file_path_from_converter = None

        try:
            logger.info(f"file_to_pdf_view: Processing {original_name} with sub_tab: {sub_tab}. Input: {temp_input_path}, Output: {output_pdf_path}. RequestID: {request_id}")
            if sub_tab == 'wordToPdf':
                if original_name.lower().endswith(('.doc', '.docx')):\
                    success_conv, actual_output_file_path_from_converter, conversion_message_conv = convert_word_to_pdf(temp_input_path, output_pdf_path)
                else:
                    conversion_message_conv = "不是有效的Word文件 (.doc, .docx)。"
            elif sub_tab == 'excelToPdf':
                if original_name.lower().endswith(('.xls', '.xlsx')):\
                    success_conv, actual_output_file_path_from_converter, conversion_message_conv = convert_excel_to_pdf(temp_input_path, output_pdf_path)
                else:
                    conversion_message_conv = "不是有效的Excel文件 (.xls, .xlsx)。"
            elif sub_tab == 'pptToPdf':
                if original_name.lower().endswith(('.ppt', '.pptx')):\
                    success_conv, actual_output_file_path_from_converter, conversion_message_conv = ppt_pdf_converter.convert_pptx_to_pdf(temp_input_path, output_pdf_path)
                else:
                    conversion_message_conv = "不是有效的PPT文件 (.ppt, .pptx)。"
            elif sub_tab == 'txtToPdf':
                if original_name.lower().endswith('.txt'):\
                    success_conv, actual_output_file_path_from_converter, conversion_message_conv = convert_txt_to_pdf(temp_input_path, output_pdf_path)
                else:
                    conversion_message_conv = "不是有效的TXT文件 (.txt)。"
            else:
                logger.warning(f"file_to_pdf_view: Unsupported sub_tab '{sub_tab}' for {original_name}. RequestID: {request_id}")
                conversion_message_conv = f"不支持的转换类型: {sub_tab}"

            if success_conv and actual_output_file_path_from_converter and os.path.exists(actual_output_file_path_from_converter):
                final_target_path = os.path.join(user_converted_dir, unique_pdf_filename) # This is output_pdf_path
                if actual_output_file_path_from_converter != final_target_path:
                    if os.path.exists(actual_output_file_path_from_converter): # Should always be true if success_conv
                         shutil.move(actual_output_file_path_from_converter, final_target_path)
                    # else case implies converter reported success but file is missing, which is an error state
                
                # Verify file exists at final_target_path
                if os.path.exists(final_target_path):
                    processed_files_final.append({
                        'original_name': original_name,
                        'converted_name': unique_pdf_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, unique_pdf_filename]),
                        'status': 'success',
                        'message': conversion_message_conv or '转换成功'
                    })
                    logger.info(f"file_to_pdf_view/{sub_tab}: Successfully converted '{original_name}' to '{unique_pdf_filename}'. RequestID: {request_id}")
                else: # File missing after supposed success
                    success_conv = False # Update status
                    conversion_message_conv += " (处理后输出文件丢失)"
                    logger.error(f"file_to_pdf_view/{sub_tab}: File {final_target_path} missing post-success for '{original_name}'. RequestID: {request_id}")


            if not success_conv: # Handles initial failure or failure after move check or missing file
                processed_files_final.append({
                    'original_name': original_name,
                    'status': 'error',
                    'message': conversion_message_conv or "转换失败，未生成文件。"
                })
                logger.error(f"file_to_pdf_view/{sub_tab}: Failed to convert '{original_name}'. Message: {conversion_message_conv}. OutPath: {actual_output_file_path_from_converter}. RequestID: {request_id}")
                # Cleanup problematic intermediate if it exists and is not the intended final path (which would be an error case already handled)
                if actual_output_file_path_from_converter and \
                   actual_output_file_path_from_converter != output_pdf_path and \
                   os.path.exists(actual_output_file_path_from_converter):
                    temp_files_to_delete_final.append(actual_output_file_path_from_converter)

        except Exception as e_conv:
            logger.error(f"file_to_pdf_view: Exception during {sub_tab} to PDF for {original_name}: {e_conv}. RequestID: {request_id}", exc_info=True)
            processed_files_final.append({
                'original_name': original_name,
                'status': 'error',
                'message': f"转换时发生严重错误: {str(e_conv)}"
            })
            if actual_output_file_path_from_converter and os.path.exists(actual_output_file_path_from_converter):
                temp_files_to_delete_final.append(actual_output_file_path_from_converter)
        finally:
            if temp_input_path and os.path.exists(temp_input_path):
                temp_files_to_delete_final.append(temp_input_path)
    
    # Merging logic for fileToPdf
    if merge_output and any(f['status'] == 'success' for f in processed_files_final) and PYPDF2_AVAILABLE:
        successful_pdfs_paths = [os.path.join(user_converted_dir, f['converted_name']) for f in processed_files_final if f['status'] == 'success']
        if len(successful_pdfs_paths) > 1:
            merged_pdf_name = f"merged_files_{request_id}.pdf"
            merged_pdf_path = os.path.join(user_converted_dir, merged_pdf_name)
            merger = PdfMerger()
            try:
                for pdf_path_to_merge in successful_pdfs_paths:
                    if os.path.exists(pdf_path_to_merge):
                        merger.append(pdf_path_to_merge)
                merger.write(merged_pdf_path)
                merger.close()
                logger.info(f"file_to_pdf_view: Successfully merged {len(successful_pdfs_paths)} PDFs into '{merged_pdf_name}'. RequestID: {request_id}")
                
                final_merged_result_message = f"{len(successful_pdfs_paths)} 个文件成功合并为PDF。"
                # Collect original names of files that failed, if any
                failed_original_names_for_merge = [f['original_name'] for f in processed_files_final if f['status'] == 'error' and f['original_name'] != '合并操作']
                if failed_original_names_for_merge: # More specific error reporting
                     final_merged_result_message += f" 未能转换的文件: {', '.join(failed_original_names_for_merge)}."


                # Replace list with single merged result, keeping errors separate
                processed_files_final = [f for f in processed_files_final if f['status'] == 'error' and f['original_name'] != '合并操作'] 
                processed_files_final.append({ 
                    'original_name': '合并的PDF文件',
                    'converted_name': merged_pdf_name,
                    'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, merged_pdf_name]),
                    'status': 'success',
                    'message': final_merged_result_message
                })
                temp_files_to_delete_final.extend(successful_pdfs_paths) # Add individual PDFs that were merged to cleanup
            except Exception as e_merge:
                logger.error(f"file_to_pdf_view: Error merging PDFs: {e_merge}. RequestID: {request_id}", exc_info=True)
                processed_files_final.append({'original_name': '合并操作', 'status': 'error', 'message': f'PDF合并失败: {str(e_merge)}'})
                if os.path.exists(merged_pdf_path): temp_files_to_delete_final.append(merged_pdf_path)

        elif len(successful_pdfs_paths) == 1:
            logger.info(f"file_to_pdf_view: Only one successful PDF, no merging needed. RequestID: {request_id}")
    elif merge_output and not PYPDF2_AVAILABLE and any(f['status'] == 'success' for f in processed_files_final):
        logger.warning(f"file_to_pdf_view: Merge requested but PyPDF2 is not available. RequestID: {request_id}")
        # Find the first success entry to add this warning to, or add as a general message
        found_success = False
        for item in processed_files_final:
            if item['status'] == 'success':
                item['message'] += ' (警告: PDF合并库不可用，文件未合并)'
                found_success = True
                break
        if not found_success: # Or add as a general separate warning item if no successes (though condition implies one)
            processed_files_final.append({'original_name': '合并操作', 'status': 'warning', 'message': 'PDF合并库不可用，文件未合并。'})


    cleanup_temp_files(list(set(temp_files_to_delete_final)), request_id)
    return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

@login_required
@require_POST
def img_to_file_view(request):
    today_date_str = datetime.now().strftime("%Y%m%d")
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    logger.info(f"img_to_file_view: Received request. RequestID: {request_id}")

    user_upload_dir, user_converted_dir = "", ""
    try:
        user_upload_dir, user_converted_dir = ensure_user_directories(request.user.username, today_date_str)
    except Exception as e:
        logger.critical(f"img_to_file_view: Failed to create user directories for {request.user.username}. Error: {e}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='服务器错误：无法创建用户目录。', merge_output=merge_output_for_error, request_id=request_id)

    parsed_params = {}
    try:
        parsed_params = parse_conversion_request_params(request.POST, request_id)
    except Exception as e_parse:
        logger.error(f"img_to_file_view: Error parsing request parameters: {e_parse}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='请求参数错误。', merge_output=merge_output_for_error, request_id=request_id)

    merge_output = parsed_params['merge_output']
    output_format = parsed_params['output_format']

    processed_files_final = []
    temp_files_to_delete_final = []

    uploaded_files_info = []
    if not request.FILES.getlist('images'):
        logger.warning(f"img_to_file_view: No files uploaded. RequestID: {request_id}")
        return format_error_response(message='没有上传文件。', merge_output=merge_output, request_id=request_id)
        
    for uploaded_file_obj in request.FILES.getlist('images'):
        temp_input_path, original_filename, safe_filename = save_uploaded_file(uploaded_file_obj, user_upload_dir, request_id)
        if temp_input_path and safe_filename:
            uploaded_files_info.append({
                'name': original_filename,
                'path': temp_input_path,
                'safe_original_filename': safe_filename,
                'status': 'uploaded'
            })
        else:
            failed_original_name = original_filename if original_filename else "未知文件"
            logger.error(f"img_to_file_view: Failed to save uploaded file: {failed_original_name}. RequestID: {request_id}")
            processed_files_final.append({
                'original_name': failed_original_name,
                'status': 'error',
                'message': f'文件 "{failed_original_name}" 上传保存失败。'
            })
    
    if not uploaded_files_info:
        logger.error(f"img_to_file_view: All file uploads failed or no files were valid after saving. RequestID: {request_id}")
        if not processed_files_final: 
             processed_files_final.append({'original_name': 'File Upload', 'status': 'error', 'message': '所有文件上传失败或未能保存。'})
        return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

    # --- Core Img to File conversion logic (formerly _handle_img_to_file) ---
    img_script_results, script_created_files = process_images_to_files(
        uploaded_files_info, 
        user_converted_dir, 
        request_id,
        output_format
    )

    for item in uploaded_files_info:
        if item.get('path') and os.path.exists(item['path']):
            temp_files_to_delete_final.append(item['path'])

    if not script_created_files and not img_script_results:
        logger.error(f"img_to_file_view: pic_file_converter script (process_images_to_files) provided no output. RequestID: {request_id}")
        if not img_script_results: # Populate errors if script returned nothing
            for up_file in uploaded_files_info:
                processed_files_final.append({
                    'original_name': up_file['name'], 'status': 'error',
                    'message': '图像处理脚本未能生成任何输出。'
                })
        else: # Script might have returned error messages within img_script_results
            processed_files_final.extend(img_script_results)
        
        cleanup_temp_files(list(set(temp_files_to_delete_final)), request_id)
        return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

    if merge_output:
        if not script_created_files:
            logger.warning(f"img_to_file_view: Merge requested, but no files from script to merge. Script results: {img_script_results}. RequestID: {request_id}")
            processed_files_final.extend(img_script_results or [{'original_name': '图像合并操作', 'status': 'error', 'message': '没有从图像生成可合并的文档。'}])
            temp_files_to_delete_final.extend([item['path'] for item in (script_created_files or []) if isinstance(item, dict) and 'path' in item])
        else:
            merged_base_name = f"merged_images_{request_id}"
            final_merged_docx_filename = f"{merged_base_name}.docx"
            final_merged_docx_path = os.path.join(user_converted_dir, final_merged_docx_filename)
            try:
                if len(script_created_files) > 0: # Ensure there are files to merge
                    master_doc = Document(script_created_files[0]['path'])
                    for doc_info in script_created_files[1:]:
                        sub_doc = Document(doc_info['path'])
                        master_doc.add_page_break()
                        append_document(sub_doc, master_doc)
                    master_doc.save(final_merged_docx_path)
                    logger.info(f"img_to_file_view: Merged {len(script_created_files)} DOCX files to {final_merged_docx_path}. RequestID: {request_id}")
                    temp_files_to_delete_final.extend([item['path'] for item in (script_created_files or []) if isinstance(item, dict) and 'path' in item])

                    if output_format == 'docx':
                        processed_files_final = [{'original_name': "合并的Word文档 (来自图像)", 'converted_name': final_merged_docx_filename, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, final_merged_docx_filename]), 'status': 'success', 'message': "图像已成功合并为Word文档。"}]
                    elif output_format == 'pdf':
                        final_merged_pdf_filename = f"{merged_base_name}.pdf"
                        final_merged_pdf_path = os.path.join(user_converted_dir, final_merged_pdf_filename)
                        pdf_success, pdf_path_or_msg, _ = convert_word_to_pdf(final_merged_docx_path, final_merged_pdf_path)
                        if pdf_success and os.path.exists(final_merged_pdf_path):
                            processed_files_final = [{'original_name': "合并的PDF文档 (来自图像)", 'converted_name': final_merged_pdf_filename, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, final_merged_pdf_filename]), 'status': 'success', 'message': "图像成功合并到Word并转换为PDF。"}]
                            temp_files_to_delete_final.append(final_merged_docx_path)
                        else:
                            processed_files_final = [{'original_name': "图像合并与PDF转换", 'status': 'error', 'message': pdf_path_or_msg or "无法将合并的Word文档转换为PDF。"}]
                            # MODIFIED: Do not delete intermediate merged DOCX if output is PPTX for debugging
                            # Temporarily disable cleanup to inspect the merged DOCX file
                            # if output_format != 'pptx':
                            #     temp_files_to_delete_final.append(final_merged_docx_path)
                    elif output_format == 'pptx': # New: Handle PPTX output for merged files
                        final_merged_pptx_filename = f"{merged_base_name}.pptx"
                        final_merged_pptx_path = os.path.join(user_converted_dir, final_merged_pptx_filename)
                        pptx_success, pptx_path_or_msg, _ = convert_docx_to_pptx_libreoffice(final_merged_docx_path, user_converted_dir)
                        
                        if pptx_success and pptx_path_or_msg and os.path.exists(pptx_path_or_msg):
                            # pptx_path_or_msg from libreoffice converter is the actual path of the created file (e.g., user_converted_dir/merged_images_requestid.pptx)
                            # We need to rename it to final_merged_pptx_path if it's different (it should be if libreoffice names it based on docx stem)
                            if pptx_path_or_msg != final_merged_pptx_path:
                                if os.path.exists(final_merged_pptx_path):
                                    os.remove(final_merged_pptx_path) # Remove if somehow exists
                                shutil.move(pptx_path_or_msg, final_merged_pptx_path)
                            
                            processed_files_final = [{'original_name': "合并的PPTX文档 (来自图像)", 'converted_name': final_merged_pptx_filename, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, final_merged_pptx_filename]), 'status': 'success', 'message': "图像成功合并到Word并转换为PPTX。"}]
                            # MODIFIED: Do not delete intermediate merged DOCX if output is PPTX for debugging
                            # Temporarily disable cleanup to inspect the merged DOCX file
                            # if output_format != 'pptx':
                            #     temp_files_to_delete_final.append(final_merged_docx_path)
                        else:
                            processed_files_final = [{'original_name': "图像合并与PPTX转换", 'status': 'error', 'message': pptx_path_or_msg or "无法将合并的Word文档转换为PPTX。"}]
                            # MODIFIED: Do not delete intermediate merged DOCX if output is PPTX for debugging, and it was an error with PPTX conversion
                            # However, if the error is about PPTX conversion, the DOCX might be useful.
                            # Let's keep it for now if output_format == 'pptx'. If it's another format, it should be deleted.
                            # if output_format != 'pptx':
                            #     temp_files_to_delete_final.append(final_merged_docx_path)
                else: 
                     processed_files_final.extend(img_script_results or [{'original_name': "图像合并操作", 'status': 'info', 'message': '请求合并，但没有生成可合并的图像文档。'}])
            except Exception as e_img_merge:
                logger.error(f"img_to_file_view: 合并DOCX文件时出错: {e_img_merge}. RequestID: {request_id}", exc_info=True)
                processed_files_final.append({'original_name': "图像合并操作", 'status': 'error', 'message': f"图像文档合并过程中出错: {str(e_img_merge)}"})
                if os.path.exists(final_merged_docx_path): temp_files_to_delete_final.append(final_merged_docx_path)
                temp_files_to_delete_final.extend([item['path'] for item in (script_created_files or []) if isinstance(item, dict) and 'path' in item])
    else: 
        temp_individual_results = []
        if not img_script_results:
            logger.warning(f"img_to_file_view: 非合并模式，但 process_images_to_files 未返回结果。RequestID: {request_id}")
            for up_file in uploaded_files_info: # Create error entries for each uploaded file
                 temp_individual_results.append({'original_name': up_file['name'], 'status': 'error', 'message': '图像处理脚本未能为此文件生成输出。'})
            temp_files_to_delete_final.extend([item['path'] for item in (script_created_files or []) if isinstance(item, dict) and 'path' in item])
        else:
            for res_info in img_script_results:
                original_img_name = res_info.get('original_name')
                intermediate_docx_name = res_info.get('converted_name')
                intermediate_docx_full_path = None
                if intermediate_docx_name: # Map to full path
                    for scf_item in script_created_files: # scf_item is a dict
                        if isinstance(scf_item, dict) and os.path.basename(scf_item.get('path', '')) == intermediate_docx_name:
                            intermediate_docx_full_path = scf_item['path']
                            break
                
                if res_info.get('status') == 'error' or not intermediate_docx_full_path or not os.path.exists(intermediate_docx_full_path):
                    temp_individual_results.append(res_info) # Pass through script's error or if file is missing
                    if intermediate_docx_full_path and os.path.exists(intermediate_docx_full_path): # Cleanup if exists but was error
                        temp_files_to_delete_final.append(intermediate_docx_full_path)
                    elif intermediate_docx_full_path and not os.path.exists(intermediate_docx_full_path):
                         logger.warning(f"img_to_file_view: 脚本为 {original_img_name} 生成的 {intermediate_docx_name} 不存在于 {intermediate_docx_full_path}. RequestID: {request_id}")
                    continue

                if output_format == 'docx':
                    res_info['download_url'] = reverse('converter:download_converted_file', args=[request.user.username, today_date_str, intermediate_docx_name])
                    temp_individual_results.append(res_info)
                elif output_format == 'pdf':
                    pdf_base = os.path.splitext(intermediate_docx_name)[0]
                    final_pdf_name = f"{pdf_base}.pdf"
                    final_pdf_full_path = os.path.join(user_converted_dir, final_pdf_name)
                    pdf_succ, pdf_msg, _ = convert_word_to_pdf(intermediate_docx_full_path, final_pdf_full_path)
                    if pdf_succ and os.path.exists(final_pdf_full_path):
                        temp_individual_results.append({'original_name': original_img_name, 'converted_name': final_pdf_name, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, final_pdf_name]), 'status': 'success', 'message': res_info.get('message', "图像已转为PDF。") + " (经Word)"})
                        temp_files_to_delete_final.append(intermediate_docx_full_path)
                    else:
                        temp_individual_results.append({'original_name': original_img_name, 'converted_name': intermediate_docx_name, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, intermediate_docx_name]), 'status': 'error', 'message': pdf_msg or "图像生成的Word转PDF失败。"})
                elif output_format == 'pptx': # New: Handle PPTX output for individual files
                    pptx_base_name_no_ext = os.path.splitext(intermediate_docx_name)[0] # original_img_name_tempScriptOutput_requestid
                    # We want the final name to be like: original_img_name_requestid.pptx
                    # The intermediate_docx_name is like: original_img_name_tempScriptOutput_requestid.docx
                    # So, pptx_base_name_no_ext is original_img_name_tempScriptOutput_requestid
                    # Let's try to reconstruct a cleaner name if possible, or use a unique one.
                    # For consistency, use original_img_name and request_id for the final pptx name
                    final_pptx_name = f"{os.path.splitext(original_img_name)[0]}_{request_id}.pptx"
                    final_pptx_full_path = os.path.join(user_converted_dir, final_pptx_name)

                    pptx_succ, actual_libre_pptx_path, pptx_msg = convert_docx_to_pptx_libreoffice(intermediate_docx_full_path, user_converted_dir)

                    if pptx_succ and actual_libre_pptx_path and os.path.exists(actual_libre_pptx_path):
                        # actual_libre_pptx_path is based on intermediate_docx_full_path's stem, e.g. user_converted_dir/original_img_name_tempScriptOutput_requestid.pptx
                        # We need to rename it to final_pptx_full_path
                        if actual_libre_pptx_path != final_pptx_full_path:
                            if os.path.exists(final_pptx_full_path):
                                os.remove(final_pptx_full_path)
                            shutil.move(actual_libre_pptx_path, final_pptx_full_path)
                        
                        temp_individual_results.append({'original_name': original_img_name, 'converted_name': final_pptx_name, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, final_pptx_name]), 'status': 'success', 'message': res_info.get('message', "图像已转为PPTX。") + " (经Word)"})
                        # MODIFIED: Do not delete intermediate merged DOCX if output is PPTX for debugging
                        # Temporarily disable cleanup to inspect the merged DOCX file
                        # if output_format != 'pptx':
                        #     temp_files_to_delete_final.append(final_merged_docx_path)
                    else:
                        temp_individual_results.append({'original_name': original_img_name, 'converted_name': intermediate_docx_name, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, intermediate_docx_name]), 'status': 'error', 'message': pptx_msg or "图像生成的Word转PPTX失败。"})
                        # MODIFIED: Do not delete intermediate DOCX if output is PPTX for debugging, and it was an error with PPTX conversion
                        # However, if the error is about PPTX conversion, the DOCX might be useful.
                        # Let's keep it for now if output_format == 'pptx'. If it's another format, it should be deleted.
                        # if output_format != 'pptx':
                        #     temp_files_to_delete_final.append(final_merged_docx_path)
                else:
                    logger.warning(f"img_to_file_view: 不支持的输出格式 '{output_format}' 用于单个图像处理. RequestID: {request_id}")
                    res_info['status'] = 'error'; res_info['message'] = f"图像转换不支持输出格式 '{output_format}'。"
                    temp_individual_results.append(res_info)
            
        processed_files_final = temp_individual_results
        final_product_names = [f.get('converted_name') for f in processed_files_final if f.get('status') == 'success']
        for scf_item in script_created_files: # General cleanup of unmerged/unused script files; scf_item is a dict
            if isinstance(scf_item, dict) and 'path' in scf_item:
                scf_path = scf_item['path']
                if os.path.basename(scf_path) not in final_product_names:
                    if scf_path not in temp_files_to_delete_final:
                        temp_files_to_delete_final.append(scf_path)
        
    cleanup_temp_files(list(set(temp_files_to_delete_final)), request_id)
    return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

@login_required
@require_POST
def pdf_to_file_view(request):
    today_date_str = datetime.now().strftime("%Y%m%d")
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    logger.info(f"pdf_to_file_view: Received request. RequestID: {request_id}")

    user_upload_dir, user_converted_dir = "", ""
    try:
        user_upload_dir, user_converted_dir = ensure_user_directories(request.user.username, today_date_str)
    except Exception as e:
        logger.critical(f"pdf_to_file_view: Failed to create user directories for {request.user.username}. Error: {e}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='服务器错误：无法创建用户目录。', merge_output=merge_output_for_error, request_id=request_id)

    parsed_params = {}
    try:
        parsed_params = parse_conversion_request_params(request.POST, request_id)
    except Exception as e_parse:
        logger.error(f"pdf_to_file_view: Error parsing request parameters: {e_parse}. RequestID: {request_id}", exc_info=True)
        merge_output_for_error = request.POST.get('merge_output', 'false').lower() == 'true'
        return format_error_response(message='请求参数错误。', merge_output=merge_output_for_error, request_id=request_id)

    merge_output = parsed_params['merge_output']
    sub_tab = parsed_params['sub_tab']

    processed_files_final = []
    temp_files_to_delete_final = []

    uploaded_files_info = []
    if not request.FILES.getlist('images'): 
        logger.warning(f"pdf_to_file_view: No files uploaded. RequestID: {request_id}")
        return format_error_response(message='没有上传PDF文件。', merge_output=merge_output, request_id=request_id)
        
    for uploaded_file_obj in request.FILES.getlist('images'):
        temp_input_path, original_filename, safe_filename = save_uploaded_file(uploaded_file_obj, user_upload_dir, request_id)
        if temp_input_path and safe_filename:
            uploaded_files_info.append({
                'name': original_filename,
                'path': temp_input_path,
                'safe_original_filename': safe_filename,
                'status': 'uploaded'
            })
        else:
            failed_original_name = original_filename if original_filename else "未知文件"
            logger.error(f"pdf_to_file_view: Failed to save uploaded PDF: {failed_original_name}. RequestID: {request_id}")
            processed_files_final.append({'original_name': failed_original_name, 'status': 'error', 'message': f'PDF文件 "{failed_original_name}" 上传保存失败。'})
    
    if not uploaded_files_info:
        logger.error(f"pdf_to_file_view: All PDF uploads failed. RequestID: {request_id}")
        if not processed_files_final:
            processed_files_final.append({'original_name': 'PDF File Upload', 'status': 'error', 'message': '所有PDF文件上传失败或未能保存。'})
        return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)

    # --- Core PDF to File conversion logic (formerly _handle_pdf_to_file) ---
    temp_individual_converted_outputs = []
    for up_file_info in uploaded_files_info:
        original_name = up_file_info['name']
        source_file_path = up_file_info['path']
        safe_original_filename = up_file_info['safe_original_filename']
        base_name_no_ext = os.path.splitext(safe_original_filename)[0]
        
        converted_filename = None; success_conv = False; conversion_message_conv = "不支持的转换或发生错误。"
        actual_output_path_from_converter = None; intended_final_output_path = None

        try:
            if not original_name.lower().endswith('.pdf'):
                error_message = f"文件类型不匹配: {original_name} (应为PDF)。"; logger.warning(f"pdf_to_file_view: {error_message} RID: {request_id}")
                processed_files_final.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                if source_file_path and os.path.exists(source_file_path): temp_files_to_delete_final.append(source_file_path)
                continue

            logger.info(f"pdf_to_file_view: Processing {original_name} for {sub_tab}. Input: {source_file_path}. RID: {request_id}")
            
            output_extension = ""; current_mode = None
            if sub_tab == 'pdfToWord': output_extension = ".docx"; current_mode = parsed_params['pdf_to_word_mode']
            elif sub_tab == 'pdfToExcel': output_extension = ".xlsx"; current_mode = parsed_params['pdf_to_excel_mode']
            elif sub_tab == 'pdfToPpt': output_extension = ".pptx"; current_mode = parsed_params['pdf_to_ppt_mode']
            elif sub_tab == 'pdfToTxt': output_extension = ".txt"; current_mode = parsed_params['pdf_to_txt_mode']
            
            if not output_extension:
                conversion_message_conv = f"不支持的PDF转换子类型: {sub_tab}。"; logger.warning(f"pdf_to_file_view: {conversion_message_conv} for {original_name}. RID: {request_id}")
            else:
                converted_filename = f"{base_name_no_ext}_{request_id}{output_extension}"
                intended_final_output_path = os.path.join(user_converted_dir, converted_filename)

                if sub_tab == 'pdfToWord': success_conv, actual_output_path_from_converter, conversion_message_conv = convert_pdf_to_word(source_file_path, intended_final_output_path, mode=current_mode)
                elif sub_tab == 'pdfToExcel': success_conv, actual_output_path_from_converter, conversion_message_conv = convert_pdf_to_excel(source_file_path, intended_final_output_path, mode=current_mode)
                elif sub_tab == 'pdfToPpt': 
                    # Pass user_converted_dir as the output folder, and base_name_no_ext as desired_filename_base
                    # The converter will create a file like base_name_no_ext.pptx or base_name_no_ext_converted.pptx in user_converted_dir
                    success_conv, actual_output_path_from_converter, conversion_message_conv = convert_pdf_to_ppt(
                        source_file_path, 
                        user_converted_dir, # Pass the directory here
                        mode=current_mode, 
                        desired_filename_base=base_name_no_ext # Pass the base name for the converter to use
                    )
                    # intended_final_output_path is already defined correctly with request_id
                elif sub_tab == 'pdfToTxt': success_conv, actual_output_path_from_converter, conversion_message_conv = convert_pdf_to_txt(source_file_path, intended_final_output_path, mode=current_mode)
            
            if success_conv and actual_output_path_from_converter and os.path.exists(actual_output_path_from_converter):
                # Ensure actual_output_path_from_converter is a file before proceeding
                if not os.path.isfile(actual_output_path_from_converter):
                    success_conv = False
                    conversion_message_conv = f"转换器未返回有效的文件路径: {actual_output_path_from_converter}"
                    logger.error(f"pdf_to_file_view/{sub_tab}: Converter for '{original_name}' returned a non-file path: {actual_output_path_from_converter}. RID: {request_id}")
                elif actual_output_path_from_converter != intended_final_output_path:
                    if os.path.exists(intended_final_output_path):
                        try:
                            if os.path.isdir(intended_final_output_path):
                                shutil.rmtree(intended_final_output_path) # Remove directory if it exists from previous error
                            else:
                                os.remove(intended_final_output_path) # Remove file if it exists
                        except Exception as e_remove_existing:
                            logger.warning(f"Error removing existing target {intended_final_output_path} before move: {e_remove_existing}. RID: {request_id}")
                    try:
                        shutil.move(actual_output_path_from_converter, intended_final_output_path)
                        logger.info(f"Moved converted file from {actual_output_path_from_converter} to {intended_final_output_path}. RID: {request_id}")
                    except Exception as e_move:
                        success_conv = False
                        conversion_message_conv = f"无法将转换后的文件移动到目标位置: {e_move}"
                        logger.error(f"Failed to move {actual_output_path_from_converter} to {intended_final_output_path}: {e_move}. RID: {request_id}")
                # else: actual_output_path_from_converter is already the intended_final_output_path, no move needed
                
                # Re-check success_conv because it might have been set to False during move/check
                if success_conv and os.path.exists(intended_final_output_path) and os.path.isfile(intended_final_output_path):
                    processed_files_final.append({
                        'original_name': original_name,
                        'converted_name': converted_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, converted_filename]),
                        'status': 'success',
                        'message': conversion_message_conv or '转换成功。'
                    })
                    temp_individual_converted_outputs.append(intended_final_output_path)
                else: # File missing after supposed success
                    success_conv = False; conversion_message_conv += " (处理后输出文件丢失)"
                    logger.error(f"pdf_to_file_view: File {intended_final_output_path} missing post-success for {original_name}. RID: {request_id}")


            if not success_conv:
                processed_files_final.append({
                    'original_name': original_name,
                    'status': 'error',
                    'message': conversion_message_conv or "转换失败"
                })
                logger.error(f"pdf_to_file_view/{sub_tab}: '{original_name}' failed. Msg: {conversion_message_conv}. OutPath: {actual_output_path_from_converter}. RID: {request_id}")
                if actual_output_path_from_converter and actual_output_path_from_converter != intended_final_output_path and os.path.exists(actual_output_path_from_converter):
                    temp_files_to_delete_final.append(actual_output_path_from_converter)
        except Exception as e_conv_pdf_ind:
            logger.error(f"pdf_to_file_view: {sub_tab} for {original_name} EXCEPTION: {e_conv_pdf_ind}. RID: {request_id}", exc_info=True)
            processed_files_final.append({'original_name': original_name, 'status': 'error', 'message': f"关键错误: {str(e_conv_pdf_ind)}"})
            if actual_output_path_from_converter and os.path.exists(actual_output_path_from_converter):
                temp_files_to_delete_final.append(actual_output_path_from_converter)
        finally:
            if source_file_path and os.path.exists(source_file_path):
                temp_files_to_delete_final.append(source_file_path)

    if merge_output and len(temp_individual_converted_outputs) > 1:
        first_converted_path = temp_individual_converted_outputs[0]; merge_output_ext = os.path.splitext(first_converted_path)[1].lower()
        merged_target_filename = f"merged_pdfs_to_{sub_tab.replace('pdfTo','').lower()}_{request_id}{merge_output_ext}"
        merged_target_path = os.path.join(user_converted_dir, merged_target_filename)
        merge_succ = False; merge_msg = "合并未尝试或失败。"

        successful_original_pdf_paths_for_merge = []
        success_map = {} # Map original_name to its temp_path for successfully converted files
        for pf in processed_files_final:
            if pf['status'] == 'success':
                original_file_detail = next((uf_info for uf_info in uploaded_files_info if uf_info['name'] == pf['original_name']), None)
                if original_file_detail and os.path.join(user_converted_dir, pf['converted_name']) in temp_individual_converted_outputs:
                    success_map[pf['original_name']] = original_file_detail['path']
        
        for tico_path in temp_individual_converted_outputs:
            found_original_name = next((pf_entry['original_name'] for pf_entry in processed_files_final if pf_entry.get('status') == 'success' and os.path.join(user_converted_dir, pf_entry.get('converted_name', '')) == tico_path), None)
            if found_original_name and found_original_name in success_map: successful_original_pdf_paths_for_merge.append(success_map[found_original_name])
            else: logger.warning(f"pdf_to_file_view: Cannot map temp output {tico_path} to original PDF for merge. RID: {request_id}")

        if not successful_original_pdf_paths_for_merge or len(successful_original_pdf_paths_for_merge) <=1:
            logger.warning(f"pdf_to_file_view: Merge requested, not enough original PDFs. RID: {request_id}")
        else:
            current_merge_mode = parsed_params.get(f"pdf_to_{sub_tab.replace('pdfTo','').lower()}_mode")

            try:
                if sub_tab == 'pdfToWord' and merge_output_ext == '.docx': merge_succ, merge_msg = convert_and_merge_pdfs_to_docx(successful_original_pdf_paths_for_merge, merged_target_path, request_id, mode=current_merge_mode)
                elif sub_tab == 'pdfToPpt' and merge_output_ext == '.pptx': merge_succ, merge_msg = convert_and_merge_pdfs_to_pptx(successful_original_pdf_paths_for_merge, merged_target_path, request_id, ppt_creation_mode=current_merge_mode)
                elif sub_tab == 'pdfToTxt' and merge_output_ext == '.txt': merge_succ, merge_msg = convert_and_merge_pdfs_to_txt(successful_original_pdf_paths_for_merge, merged_target_path, request_id, mode=current_merge_mode)
                else: merge_msg = f"不支持PDF合并为 {merge_output_ext}。"; logger.warning(f"pdf_to_file_view: {merge_msg} RID: {request_id}")

                if merge_succ and os.path.exists(merged_target_path):
                    final_list_after_merge = [res for res in processed_files_final if res['status'] == 'error']
                    final_list_after_merge.append({'original_name': f'合并的 {sub_tab.replace("pdfTo","")} (来自 {len(successful_original_pdf_paths_for_merge)} 个PDF)', 'converted_name': merged_target_filename, 'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, merged_target_filename]), 'status': 'success', 'message': merge_msg or f"{len(successful_original_pdf_paths_for_merge)} 个PDF成功合并。"})
                    processed_files_final = final_list_after_merge
                    temp_files_to_delete_final.extend(temp_individual_converted_outputs)
                elif not merge_succ:
                    processed_files_final.append({'original_name': '合并操作', 'status': 'error', 'message': f"PDF合并为 {sub_tab.replace('pdfTo','')} 失败: {merge_msg}"})
                    if os.path.exists(merged_target_path): temp_files_to_delete_final.append(merged_target_path)
            except Exception as e_merge_main:
                logger.error(f"pdf_to_file_view: {sub_tab} merge EXCEPTION: {e_merge_main}. RID: {request_id}", exc_info=True)
                processed_files_final.append({'original_name': '合并操作', 'status': 'error', 'message': f"PDF合并时关键错误: {str(e_merge_main)}"})
                if os.path.exists(merged_target_path): temp_files_to_delete_final.append(merged_target_path)
    
    elif merge_output and len(temp_individual_converted_outputs) == 1:
        logger.info(f"pdf_to_file_view: Merge requested, only one PDF converted. No merge performed. RID: {request_id}")

    cleanup_temp_files(list(set(temp_files_to_delete_final)), request_id)
    return format_json_response(results=processed_files_final, merge_output=merge_output, request_id=request_id)


@login_required
@require_POST
def process_images_view(request): # This view is now a deprecated placeholder
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    main_tab = request.POST.get('main_tab', None)
    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'

    logger.warning(f"process_images_view: DEPRECATED endpoint hit. main_tab: {main_tab}, RequestID: {request_id}. Client should use specific API endpoints.")
    
    error_message = "此通用转换接口已弃用。请更新客户端使用新的专用接口。"
    if main_tab == 'fileToPdf': error_message = "文件转PDF接口已更新至 /api/file-to-pdf/。请更新客户端。"
    elif main_tab == 'imgToFile': error_message = "图片转文件接口已更新至 /api/img-to-file/。请更新客户端。"
    elif main_tab == 'pdfToFile': error_message = "PDF转文件接口已更新至 /api/pdf-to-file/。请更新客户端。"

    return format_error_response(
        message=error_message,
        merge_output=merge_output, 
        original_item_name=f"Deprecated Call ({main_tab})", 
        request_id=request_id, 
        http_status=400 
    )

@login_required
def conversion_history_view(request):
    user = request.user
    user_history_base_dir = os.path.join(settings.BASE_DIR, 'his_pic', user.username)
    
    available_dates = []
    if os.path.exists(user_history_base_dir):
        for item in os.listdir(user_history_base_dir):
            if os.path.isdir(os.path.join(user_history_base_dir, item)):
                if len(item) == 8 and item.isdigit():
                    available_dates.append(item)
        available_dates.sort(reverse=True)

    selected_date_str = request.GET.get('date', None)
    converted_files_info = []

    if selected_date_str and selected_date_str in available_dates:
        date_specific_converted_dir = os.path.join(user_history_base_dir, selected_date_str, 'converted_files')
        if os.path.exists(date_specific_converted_dir):
            for filename in os.listdir(date_specific_converted_dir):
                if filename.endswith('.meta'): # Skip .meta files themselves
                    continue

                file_path = os.path.join(date_specific_converted_dir, filename)
                if os.path.isfile(file_path):
                    original_name_display = os.path.splitext(filename)[0] # Fallback
                    meta_file_path = f"{file_path}.meta"
                    if os.path.exists(meta_file_path):
                        try:
                            with open(meta_file_path, 'r', encoding='utf-8') as mf:
                                original_name_display = mf.read()
                        except Exception as e:
                            logger.error(f"Error reading .meta file {meta_file_path}: {e}")
                    
                    download_url = f"{settings.MEDIA_URL}{user.username}/{selected_date_str}/converted_files/{filename}"
                    delete_url = reverse('converter:delete_converted_file', args=[selected_date_str, filename])

                    converted_files_info.append({
                        'original_name': original_name_display,
                        'converted_name': filename,
                        'download_url': download_url,
                        'delete_url': delete_url, # Use the generated one, not from request
                        'status': '已完成'
                    })
    
    context = {
        'available_dates': available_dates,
        'selected_date': selected_date_str,
        'converted_files': converted_files_info,
        'page_title': '历史转换记录',
        'current_nav': 'history'
    }
    return render(request, 'converter/conversion_history.html', context)

@login_required
@require_POST
def delete_converted_file_view(request, date_str, filename):
    user = request.user
    file_path = os.path.join(settings.BASE_DIR, 'his_pic', user.username, date_str, 'converted_files', filename)
    meta_file_path = f"{file_path}.meta"

    file_deleted = False
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            messages.success(request, f"文件 '{filename}' 已成功删除。")
            logger.info(f"User {user.username} deleted file: {file_path}")
            file_deleted = True
            
            # Attempt to delete corresponding .meta file
            if os.path.exists(meta_file_path):
                try:
                    os.remove(meta_file_path)
                    logger.info(f"User {user.username} deleted meta file: {meta_file_path}")
                except OSError as e:
                    logger.warning(f"Error deleting meta file {meta_file_path} for user {user.username}: {e}")
            
            # Check if the converted_files directory is now empty
            converted_dir_path = os.path.dirname(file_path)
            if not os.listdir(converted_dir_path):
                try:
                    os.rmdir(converted_dir_path)
                    logger.info(f"Removed empty directory: {converted_dir_path}")
                    # Check if the parent date directory is now empty (uploads might still be there)
                    date_dir_path = os.path.dirname(converted_dir_path)
                    # We only remove the date dir if both 'uploads' and 'converted_files' are gone or empty
                    uploads_dir_path = os.path.join(date_dir_path, 'uploads')
                    can_delete_date_dir = True
                    if os.path.exists(uploads_dir_path) and os.listdir(uploads_dir_path):
                        can_delete_date_dir = False
                    
                    if not os.path.exists(converted_dir_path) and not os.path.exists(uploads_dir_path): # both gone
                         pass # can delete
                    elif not os.path.exists(converted_dir_path) and os.path.exists(uploads_dir_path) and not os.listdir(uploads_dir_path): # converted gone, uploads empty
                        os.rmdir(uploads_dir_path) # remove empty uploads
                        logger.info(f"Removed empty directory: {uploads_dir_path}")
                    elif can_delete_date_dir : # converted was removed, uploads never existed or was already removed
                        pass
                    else: # uploads still has content or converted_files was not empty
                        can_delete_date_dir = False


                    if can_delete_date_dir and not os.listdir(date_dir_path): # Check if date_dir is truly empty now
                        os.rmdir(date_dir_path)
                        logger.info(f"Removed empty date directory: {date_dir_path}")

                except OSError as e:
                    logger.error(f"Error removing directory for user {user.username} after file deletion: {e}")
                    # Don't send this specific error to user, file deletion was successful.

        except OSError as e:
            messages.error(request, f"删除文件 '{filename}' 时出错: {e}")
            logger.error(f"Error deleting file {file_path} for user {user.username}: {e}")
    else:
        messages.error(request, "文件未找到或无法删除。")
        logger.warning(f"Attempt to delete non-existent file by {user.username}: {file_path}")

    # Redirect to the history page, potentially without the date if the folder was removed
    # Or always redirect to the general history page to show the date is gone from the list
    return redirect(reverse('converter:conversion_history'))

@login_required
@require_POST # Ensure this view is only accessed via POST
def delete_all_for_date_view(request, date_str):
    user = request.user
    user_date_dir = os.path.join(settings.BASE_DIR, 'his_pic', user.username, date_str)
    
    if not os.path.exists(user_date_dir) or not os.path.isdir(user_date_dir):
        messages.error(request, f"日期 '{date_str}' 的记录不存在或无法访问。")
        return redirect(reverse('converter:conversion_history') + f'?date={date_str}')

    converted_files_dir = os.path.join(user_date_dir, 'converted_files')
    uploads_dir = os.path.join(user_date_dir, 'uploads')
    
    deleted_something = False
    try:
        # Delete files in converted_files directory
        if os.path.exists(converted_files_dir):
            for item_name in os.listdir(converted_files_dir):
                item_path = os.path.join(converted_files_dir, item_name)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                        logger.info(f"User {user.username} deleted file/link during mass delete: {item_path}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"User {user.username} deleted directory during mass delete: {item_path}")
                    deleted_something = True
                except OSError as e:
                    logger.warning(f"Error deleting item {item_path} during mass delete for user {user.username}: {e}")
                    messages.warning(request, f"删除 '{item_name}' 时出错，但会继续尝试。")
            # Attempt to remove the converted_files directory if empty
            if not os.listdir(converted_files_dir): # Should be empty if all items were deleted
                os.rmdir(converted_files_dir)
                logger.info(f"Removed empty directory: {converted_files_dir}")

        # Delete files in uploads directory
        if os.path.exists(uploads_dir):
            for item_name in os.listdir(uploads_dir):
                item_path = os.path.join(uploads_dir, item_name)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                        logger.info(f"User {user.username} deleted uploaded file/link during mass delete: {item_path}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        logger.info(f"User {user.username} deleted uploaded directory during mass delete: {item_path}")
                    deleted_something = True
                except OSError as e:
                    logger.warning(f"Error deleting uploaded file {file_path} during mass delete for user {user.username}: {e}")
                    messages.warning(request, f"删除上传文件 '{filename}' 时出错，但会继续尝试。")
            # Attempt to remove the uploads directory if empty
            if not os.listdir(uploads_dir):
                os.rmdir(uploads_dir)
                logger.info(f"Removed empty directory: {uploads_dir}")

        # Attempt to remove the date directory itself if it's now empty
        if not os.listdir(user_date_dir):
            os.rmdir(user_date_dir)
            logger.info(f"Removed empty date directory: {user_date_dir}")
            messages.success(request, f"日期 '{date_str}' 的所有记录已成功清除。")
        elif deleted_something:
            messages.success(request, f"日期 '{date_str}' 的部分或全部文件已清除。可能仍有空目录结构残留。")
        else:
            messages.info(request, f"日期 '{date_str}' 下没有找到可清除的文件。")
            
    except OSError as e:
        messages.error(request, f"清除日期 '{date_str}' 的记录时发生错误: {e}")
        logger.error(f"Error during mass delete for user {user.username}, date {date_str}: {e}", exc_info=True)
    
    # Redirect to the history page, potentially without the date if the folder was removed
    # Or always redirect to the general history page to show the date is gone from the list
    return redirect(reverse('converter:conversion_history'))

@login_required
def download_converted_file_view(request, username, date_str, filename):
    # Security check: Ensure the logged-in user matches the username in the URL
    # or the logged-in user is a superuser.
    if not (request.user.username == username or request.user.is_superuser):
        logger.warning(f"Permission denied for user {request.user.username} trying to download file for user {username}.")
        raise PermissionDenied("您没有权限下载此文件。")

    # Construct the full path to the file
    # Ensure to use settings.BASE_DIR or another secure base path for `his_pic`
    file_path = os.path.join(settings.BASE_DIR, 'his_pic', username, date_str, 'converted_files', filename)
    
    logger.debug(f"Attempting to serve file: {file_path} for user {request.user.username}")

    if os.path.exists(file_path):
        try:
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}", exc_info=True)
            raise Http404("下载文件时发生错误。")
    else:
        logger.error(f"File not found for download by {request.user.username}: {file_path}")
        raise Http404("文件未找到。")

@csrf_exempt # Ensure CSRF exemption if you test directly without a form including {% csrf_token %}
@require_POST
def process_video_extraction_view(request):
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) # Unique ID for this request
    today_date_str = datetime.now().strftime("%Y%m%d")
    logger.info(f"process_video_extraction_view: Received request. RequestID: {request_id}")

    user_upload_dir, user_converted_dir = "", ""
    try:
        user_upload_dir, user_converted_dir = ensure_user_directories(request.user.username, today_date_str)
    except Exception as e:
        logger.critical(f"process_video_extraction_view: Failed to create user directories for {request.user.username}. Error: {e}. RequestID: {request_id}", exc_info=True)
        return format_error_response(message='服务器错误：无法创建用户目录。', request_id=request_id)

    video_file_obj = request.FILES.get('videoFile') # Ensure frontend name matches
    scene_threshold_str = request.POST.get('sceneDetectionThreshold', '10.0')
    group_size_str = request.POST.get('deduplicationGroupSize', '5')

    if not video_file_obj:
        logger.warning(f"process_video_extraction_view: No video file uploaded. RequestID: {request_id}")
        return format_error_response(message='没有上传视频文件。', request_id=request_id)

    try:
        scene_threshold = float(scene_threshold_str)
        group_size = int(group_size_str)
    except ValueError:
        logger.warning(f"process_video_extraction_view: Invalid threshold or group size. T: {scene_threshold_str}, G: {group_size_str}. RequestID: {request_id}")
        return format_error_response(message='场景阈值或分组大小参数无效。', request_id=request_id)

    temp_video_path, original_video_filename, safe_video_filename = save_uploaded_file(video_file_obj, user_upload_dir, request_id)
    if not temp_video_path:
        logger.error(f"process_video_extraction_view: Failed to save uploaded video file: {original_video_filename}. RequestID: {request_id}")
        return format_error_response(message=f'视频文件 "{original_video_filename}" 上传保存失败。', request_id=request_id)

    # Path to the video extraction script
    # settings.BASE_DIR is .../extract_doc/extract_web
    # script is in .../extract_doc/
    script_original_location = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'extract_video_snapshots.py'))
    if not os.path.exists(script_original_location):
        logger.error(f"process_video_extraction_view: Snapshot script not found at {script_original_location}. RequestID: {request_id}")
        cleanup_temp_files([temp_video_path], request_id)
        return format_error_response(message='服务器配置错误：找不到视频处理脚本。', request_id=request_id)

    # Create a temporary directory for script execution to manage its outputs
    exec_temp_dir = os.path.join(user_upload_dir, f"video_exec_{request_id}")
    os.makedirs(exec_temp_dir, exist_ok=True)
    script_in_temp_dir_path = os.path.join(exec_temp_dir, os.path.basename(script_original_location))
    shutil.copy2(script_original_location, script_in_temp_dir_path)
    
    # These are the directories where the script, when run from exec_temp_dir, will output its results
    # based on its internal hardcoded relative paths like "test/test_data/video-snapshot"
    script_output_base_in_temp = os.path.join(exec_temp_dir, "test", "test_data")
    source_raw_dir_in_temp = os.path.join(script_output_base_in_temp, "video-snapshot")
    source_dedup_dir_in_temp = os.path.join(script_output_base_in_temp, "video-snapshot-duplicate")

    # These are the final target directories in the user's history
    target_raw_snapshots_dir = os.path.join(user_converted_dir, "video-snapshot")
    target_dedup_snapshots_dir = os.path.join(user_converted_dir, "video-snapshot-duplicate")
    os.makedirs(target_raw_snapshots_dir, exist_ok=True)
    os.makedirs(target_dedup_snapshots_dir, exist_ok=True)

    processed_files_final = [] # This will be populated at the end by the generator
    # temp_files_to_delete_final is managed by the generator now

    def stream_video_processing_response():
        temp_files_to_clean = [temp_video_path, exec_temp_dir]
        process_completed_successfully = False
        final_result_payload = None

        try:
            cmd = [
                sys.executable,
                script_in_temp_dir_path,
                "--video_file", temp_video_path,
                "--output_base_dir", exec_temp_dir,
                "--threshold", str(scene_threshold),
                "--group_size", str(group_size)
            ]
            logger.info(f"process_video_extraction_view (stream): Executing command: {' '.join(cmd)}. RequestID: {request_id}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', bufsize=1)

            # Yield initial message
            yield f"data: {json.dumps({'type': 'info', 'message': '视频处理脚本已启动...'})}\n\n"

            # Read stderr for progress (assuming PySceneDetect outputs progress there)
            if process.stderr:
                for line_from_stderr in iter(process.stderr.readline, ''):
                    original_line = line_from_stderr.strip() # Original line from stderr (with if initial decoding failed)
                    if not original_line: continue
                    logger.debug(f"Script STDERR line: {original_line}. RequestID: {request_id}")

                    # Clean the line for display by removing non-ASCII characters that became or were other symbols
                    # This should strip out the progress bar visual elements that are causing garbling
                    cleaned_display_line = original_line.encode('ascii', 'ignore').decode('utf-8', 'ignore')
                    # Further ensure the specific unicode replacement character is removed if it somehow persists
                    cleaned_display_line = cleaned_display_line.replace('\ufffd', '').strip()


                    progress_match = re.search(r"(\d+)/(\d+)\s*\((.*?)%\)", original_line) # Regex on original_line for robust parsing
                    if progress_match:
                        current_frame, total_frames, percent_str = progress_match.groups()
                        try:
                            percent = float(percent_str)
                            yield f"data: {json.dumps({'type': 'progress', 'percent': percent, 'text': cleaned_display_line})}\n\n"
                        except ValueError:
                            yield f"data: {json.dumps({'type': 'info', 'message': cleaned_display_line})}\n\n" # Send as info if percent parse fails
                    else:
                        yield f"data: {json.dumps({'type': 'info', 'message': cleaned_display_line})}\n\n" # Send non-progress lines as info
                    # Ensure buffer is flushed to client periodically if needed by frontend/browser
            
            stdout_data, stderr_data_remaining = process.communicate() # Get remaining stderr and all stdout
            return_code = process.returncode

            if stdout_data:
                logger.info(f"Script STDOUT (final) for {request_id}:\n{stdout_data}")
            if stderr_data_remaining: # Log any stderr not caught by the loop (e.g. if it didn't end with newline)
                logger.error(f"Script STDERR (final) for {request_id}:\n{stderr_data_remaining}")

            if return_code == 0:
                logger.info(f"Script executed successfully for {original_video_filename}. RequestID: {request_id}")
                
                # Parse counts from stdout_data early, so both messages can use them
                raw_count = 0
                dedup_count = 0
                if stdout_data:
                    raw_match = re.search(r"Raw snapshots count: (\d+)", stdout_data)
                    if raw_match:
                        try:
                            raw_count = int(raw_match.group(1))
                        except ValueError:
                            logger.warning(f"Could not parse raw_count from script output: {raw_match.group(1)}. RequestID: {request_id}")
                    dedup_match = re.search(r"Deduplicated snapshots count: (\d+)", stdout_data)
                    if dedup_match:
                        try:
                            dedup_count = int(dedup_match.group(1))
                        except ValueError:
                            logger.warning(f"Could not parse dedup_count from script output: {dedup_match.group(1)}. RequestID: {request_id}")

                source_raw_dir_in_temp = os.path.join(exec_temp_dir, "video-snapshot")
                source_dedup_dir_in_temp = os.path.join(exec_temp_dir, "video-snapshot-duplicate")

                # File copying and ZIP creation logic (moved from outer try block)
                current_results_list = [] # Temporary list for this block
                if os.path.exists(source_raw_dir_in_temp) and os.path.isdir(source_raw_dir_in_temp):
                    shutil.copytree(source_raw_dir_in_temp, target_raw_snapshots_dir, dirs_exist_ok=True)
                    logger.info(f"Copied raw snapshots to {target_raw_snapshots_dir}. RequestID: {request_id}")

                    # Create ZIP for raw snapshots
                    raw_zip_base_name = os.path.join(user_converted_dir, f"raw_frames_{safe_video_filename}_{request_id}")
                    raw_zip_file_path = shutil.make_archive(raw_zip_base_name, 'zip', target_raw_snapshots_dir)
                    raw_zip_filename = os.path.basename(raw_zip_file_path)
                    
                    # Create .meta file for raw_zip_filename
                    raw_meta_file_path = f"{raw_zip_file_path}.meta"
                    try:
                        with open(raw_meta_file_path, 'w', encoding='utf-8') as mf_raw:
                            mf_raw.write(original_video_filename)
                        logger.info(f"Created .meta file for raw ZIP: {raw_meta_file_path}. RequestID: {request_id}")
                    except Exception as e_meta_raw:
                        logger.error(f"Failed to create .meta file for raw ZIP {raw_meta_file_path}: {e_meta_raw}. RequestID: {request_id}")

                    current_results_list.append({
                        'original_name': f"{original_video_filename} (原始截图)",
                        'converted_name': raw_zip_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, raw_zip_filename]),
                        'status': 'success',
                        'message': f'包含所有原始提取的截图 ({raw_count} 张)。'
                    })
                else:
                    logger.warning(f"Raw snapshot output directory not found after script run: {source_raw_dir_in_temp}. RequestID: {request_id}")

                if os.path.exists(source_dedup_dir_in_temp) and os.path.isdir(source_dedup_dir_in_temp):
                    shutil.copytree(source_dedup_dir_in_temp, target_dedup_snapshots_dir, dirs_exist_ok=True)
                    logger.info(f"Copied deduplicated snapshots to {target_dedup_snapshots_dir}. RequestID: {request_id}")
                    
                    dedup_zip_base_name = os.path.join(user_converted_dir, f"deduplicated_frames_{safe_video_filename}_{request_id}")
                    dedup_zip_file_path = shutil.make_archive(dedup_zip_base_name, 'zip', target_dedup_snapshots_dir)
                    dedup_zip_filename = os.path.basename(dedup_zip_file_path)
                    
                    # Create .meta file for dedup_zip_filename
                    dedup_meta_file_path = f"{dedup_zip_file_path}.meta"
                    try:
                        with open(dedup_meta_file_path, 'w', encoding='utf-8') as mf_dedup:
                            mf_dedup.write(original_video_filename) # Use the same original_video_filename
                        logger.info(f"Created .meta file for deduplicated ZIP: {dedup_meta_file_path}. RequestID: {request_id}")
                    except Exception as e_meta_dedup:
                        logger.error(f"Failed to create .meta file for deduplicated ZIP {dedup_meta_file_path}: {e_meta_dedup}. RequestID: {request_id}")
                    
                    success_message_dedup = (
                        f'视频帧去重完成。'
                        f'原始截图: {raw_count} 张，去重后截图: {dedup_count} 张。'
                        f'ZIP压缩包包含去重后的截图。'
                    )

                    current_results_list.append({
                        'original_name': f"{original_video_filename} (去重截图)",
                        'converted_name': dedup_zip_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, dedup_zip_filename]),
                        'status': 'success',
                        'message': success_message_dedup
                    })
                    process_completed_successfully = True 
                else:
                    logger.warning(f"Deduplicated snapshot output directory not found: {source_dedup_dir_in_temp}. RequestID: {request_id}")
                    current_results_list.append({
                        'original_name': original_video_filename, 'status': 'error',
                        'message': '视频处理脚本执行成功，但未找到去重后的截图输出。'
                    })
                
                if not current_results_list and (not os.path.exists(source_raw_dir_in_temp) and not os.path.exists(source_dedup_dir_in_temp)):
                    current_results_list.append({
                        'original_name': original_video_filename,
                        'status': 'error',
                        'message': f'视频处理脚本运行成功，但未能找到任何截图输出目录。' # Removed STDOUT from here too
                    })
                final_result_payload = {"type": "result", "results": current_results_list, "request_id": request_id, "merge_output": False}
            else: # Script execution failed
                logger.error(f"process_video_extraction_view (stream): Script failed with code {return_code}. Input: {original_video_filename}. RequestID: {request_id}")
                error_message = f'视频处理脚本执行失败: {stderr_data_remaining[:500] if stderr_data_remaining else "(无详细错误信息)"}'
                final_result_payload = {"type": "error", "message": error_message, "request_id": request_id}

        except Exception as e_main:
            logger.error(f"process_video_extraction_view (stream): Exception during video processing for {original_video_filename}: {e_main}. RequestID: {request_id}", exc_info=True)
            final_result_payload = {"type": "error", "message": f'视频处理时发生意外服务器错误: {str(e_main)}', "request_id": request_id}
        
        finally:
            # Ensure the subprocess is terminated and waited for before cleanup
            if 'process' in locals() and process.poll() is None: # Check if process was started and is still running
                try:
                    process.terminate() # Try to terminate gracefully
                    process.wait(timeout=5) # Wait for a few seconds
                except subprocess.TimeoutExpired:
                    logger.warning(f"Subprocess did not terminate gracefully, attempting to kill. PID: {process.pid}. RequestID: {request_id}")
                    process.kill() # Force kill if terminate fails
                    process.wait() # Wait for kill
                except Exception as e_term:
                    logger.error(f"Error during subprocess termination: {e_term}. RequestID: {request_id}")
            
            cleanup_temp_files(temp_files_to_clean, request_id, remove_dirs=True)
            logger.info(f"process_video_extraction_view (stream): Cleanup of temp files executed for {exec_temp_dir}. RequestID: {request_id}")
            if final_result_payload: # Send final result or error
                 yield f"data: {json.dumps(final_result_payload)}\n\n"
            # Signal end of stream explicitly (optional, depends on client handling)
            yield f"event: stream_end\ndata: End of stream for {request_id}\n\n"

    response = StreamingHttpResponse(stream_video_processing_response(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache' # Important for SSE
    return response

# Celery task status check view (if you integrate Celery later)
@login_required
def check_task_status_view(request, task_id):
    # Placeholder implementation
    # In a real scenario, you would query your task queue (e.g., Celery) for the task status.
    logger.info(f"Checking status for task_id: {task_id}. User: {request.user.username}")
    
    # Simulate some possible states
    # This is highly dependent on how you implement tasks
    if task_id.startswith("sim_success_"):
        return JsonResponse({"task_id": task_id, "status": "SUCCESS", "result": {"message": "Task completed successfully!", "output_url": "/media/dummy_output.zip"}})
    elif task_id.startswith("sim_pending_"):
        return JsonResponse({"task_id": task_id, "status": "PENDING", "result": {"message": "Task is waiting to be processed."}})
    elif task_id.startswith("sim_processing_"):
        return JsonResponse({"task_id": task_id, "status": "PROCESSING", "result": {"message": "Task is currently being processed.", "progress": 50}})
    elif task_id.startswith("sim_failure_"):
        return JsonResponse({"task_id": task_id, "status": "FAILURE", "result": {"message": "Task failed to complete."}})
    else:
        # Default: Simulate task not found or still processing for a generic ID
        # You might want to return a 404 if the task ID is definitively not found
        logger.warning(f"Task ID {task_id} not found or status unknown (placeholder). Returning as PENDING.")
        return JsonResponse({"task_id": task_id, "status": "PENDING", "message": "Status unknown or task not found (placeholder response)."})
