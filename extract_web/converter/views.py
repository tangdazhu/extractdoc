from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegistrationForm, AdminUserEditForm, AdminSetPasswordForm # 更新导入
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess # For running the script
from django.contrib import messages # 新增导入
from django.http import JsonResponse # For AJAX responses
from django.views.decorators.http import require_POST # To restrict to POST requests
import random
import string
import traceback # 新增导入 for detailed exception logging
import logging # 新增导入
from docx import Document
from docx.oxml import OxmlElement # For adding content from sub-documents
from docx.oxml.ns import qn
from pathlib import Path # 新增

# 尝试导入 docx2pdf，如果失败则记录错误，但脚本仍可生成docx
try:
    from docx2pdf import convert as convert_docx_to_pdf
    DOCX2PDF_AVAILABLE_IN_VIEW = True
except ImportError:
    DOCX2PDF_AVAILABLE_IN_VIEW = False

logger = logging.getLogger('converter') # 获取 logger 实例

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
                # 修改：用户文件夹也应该在 MEDIA_ROOT 下，即 BASE_DIR / 'his_pic' / username
                user_dir = os.path.join(settings.BASE_DIR, 'his_pic', user.username)
                os.makedirs(user_dir, exist_ok=True)
                # 创建 uploads 和 converted_files 子目录
                os.makedirs(os.path.join(user_dir, 'uploads'), exist_ok=True)
                os.makedirs(os.path.join(user_dir, 'converted_files'), exist_ok=True)
                logger.info(f"Created directory structure for user {user.username} at {user_dir}")
            except OSError as e:
                logger.error(f"Error creating directory for user {user.username}: {e}")
            
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
            # 修改：用户文件夹路径与 register 和 process_images_view 统一
            user_folder_path = os.path.join(settings.BASE_DIR, 'his_pic', username)
            if os.path.exists(user_folder_path):
                try:
                    import shutil
                    shutil.rmtree(user_folder_path)
                    messages.success(request, f"用户 '{username}' 的文件夹已成功删除。")
                    logger.info(f"Deleted user folder for {username} at {user_folder_path}")
                except OSError as e:
                    messages.error(request, f"删除用户 '{username}' 的文件夹时出错: {e}")
                    logger.error(f"Error deleting user folder for {username}: {e}")
            
            user_to_delete.delete()
            messages.success(request, f"用户 '{username}' 已成功删除。")
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

@login_required
@require_POST
def process_images_view(request): # 重命名视图函数
    uploaded_files_raw_info = []
    user_upload_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, 'uploads')
    user_converted_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, 'converted_files')
    
    os.makedirs(user_upload_dir, exist_ok=True)
    os.makedirs(user_converted_dir, exist_ok=True)

    script_path = os.path.join(settings.BASE_DIR.parent, 'extract_text_from_images.py')
    
    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    output_format = request.POST.get('output_format', 'docx').lower() # 新增：获取输出格式

    logger.debug(f"Process Images Request: User={request.user.username}, Merge={merge_output}, Format={output_format}")

    if output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW:
        logger.error("PDF output requested by view, but docx2pdf is not available in the Django view environment.")
        # 可以考虑返回一个特定的错误信息给前端，告知用户PDF转换不可用
        # For now, let it proceed, script will also check and might fallback or error.

    for uploaded_file in request.FILES.getlist('images'):
        original_filename = uploaded_file.name
        uploaded_file_path = os.path.join(user_upload_dir, original_filename)
        try:
            with open(uploaded_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_files_raw_info.append({'name': original_filename, 'status': 'uploaded', 'path': uploaded_file_path})
        except Exception as e:
            logger.error(f"Error uploading file {original_filename}: {e}")
            uploaded_files_raw_info.append({'name': original_filename, 'status': 'upload_error', 'message': str(e)})
    
    processed_results = []
    temp_files_for_script_processing = [] # Stores paths for script to generate initial docx

    # 第一阶段：调用脚本为每个图片生成单独的 .docx 文件 (即使最终目标是PDF)
    for up_file_info in uploaded_files_raw_info:
        if up_file_info['status'] == 'uploaded':
            original_name = up_file_info['name']
            input_image_path = up_file_info['path']
            # 脚本总是先输出 .docx，即使目标是 pdf
            # 这个 .docx 文件名是临时的，如果合并，它们会被合并到另一个 .docx，然后可能转PDF
            # 如果不合并且目标是PDF，这个 .docx 会被转成PDF
            temp_script_output_docx_filename = f"{os.path.splitext(original_name)[0]}_tempScriptOutput.docx"
            temp_script_output_docx_path = os.path.join(user_converted_dir, temp_script_output_docx_filename)

            try:
                python_executable = 'python' 
                command = [
                    python_executable, 
                    script_path, 
                    input_image_path, 
                    temp_script_output_docx_path, # output_path for script
                    '--format', 'docx' # Script always generates docx initially in this view's flow
                ]
                logger.debug(f"Executing script command: {' '.join(command)}")
                result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

                if result.returncode == 0 and os.path.exists(temp_script_output_docx_path):
                    logger.info(f"Script successfully created DOCX: {temp_script_output_docx_path} for {original_name}")
                    temp_files_for_script_processing.append({
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
                    'original_name': original_name, 'status': 'conversion_error',
                    'message': f'服务器内部错误: {str(e)}'
                })
        else: 
            processed_results.append(up_file_info)

    # 第二阶段：处理和合并 (如果需要)
    if merge_output and temp_files_for_script_processing:
        logger.debug(f"Attempting to merge {len(temp_files_for_script_processing)} DOCX files.")
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # 合并后的文件名基础部分 (无扩展名)
        merged_base_filename = f"{request.user.username}_{random_chars}"
        # 合并后的 .docx 路径 (总是先合并为 .docx)
        merged_docx_path = os.path.join(user_converted_dir, f"{merged_base_filename}.docx")
        logger.debug(f"Merged DOCX filename will be: {merged_docx_path}")

        first_doc_path = temp_files_for_script_processing[0]['path']
        master_doc = Document(first_doc_path)
        
        try:
            if len(temp_files_for_script_processing) > 1:
                for doc_info in temp_files_for_script_processing[1:]:
                    sub_doc = Document(doc_info['path'])
                    master_doc.add_page_break()
                    append_document(sub_doc, master_doc)
            
            master_doc.save(merged_docx_path)
            logger.info(f"Merged DOCX saved successfully: {merged_docx_path}")

            # 清理单个图片生成的临时 DOCX 文件 (合并场景下)
            for doc_info in temp_files_for_script_processing:
                try: os.remove(doc_info['path']); logger.debug(f"Cleaned up temp script output: {doc_info['path']}")
                except OSError as e: logger.warning(f"Could not clean up temp docx {doc_info['path']}: {e}")

            final_merged_filename = f"{merged_base_filename}.{output_format}"
            final_merged_path = os.path.join(user_converted_dir, final_merged_filename)

            if output_format == 'pdf':
                if DOCX2PDF_AVAILABLE_IN_VIEW:
                    try:
                        logger.info(f"Converting merged DOCX '{merged_docx_path}' to PDF '{final_merged_path}'")
                        convert_docx_to_pdf(merged_docx_path, final_merged_path)
                        logger.info(f"Successfully converted merged DOCX to PDF: {final_merged_path}")
                        try: os.remove(merged_docx_path); logger.debug(f"Removed merged DOCX after PDF conversion: {merged_docx_path}")
                        except OSError as e: logger.warning(f"Could not remove merged DOCX {merged_docx_path}: {e}")
                    except Exception as e:
                        logger.error(f"Error converting merged DOCX to PDF: {e}", exc_info=True)
                        # PDF转换失败，但合并的DOCX仍然存在，将其作为结果
                        output_format = 'docx' # Fallback to docx
                        final_merged_filename = f"{merged_base_filename}.docx"
                        final_merged_path = merged_docx_path
                        messages.warning(request, "PDF转换失败，已生成DOCX文件。") # Inform user via messages
                else:
                    logger.error("PDF conversion for merged file requested, but docx2pdf is not available. Serving DOCX.")
                    output_format = 'docx' # Fallback to docx
                    final_merged_filename = f"{merged_base_filename}.docx"
                    final_merged_path = merged_docx_path
                    messages.warning(request, "PDF转换库不可用，已生成DOCX文件。")
            
            if os.path.exists(final_merged_path):
                relative_media_path = os.path.join(request.user.username, 'converted_files', final_merged_filename).replace("\\\\", "/")
                download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                merged_original_names = ", ".join([info['original_name'] for info in temp_files_for_script_processing])
                processed_results = [{
                    'original_name': f"Merged: {merged_original_names}",
                    'converted_name': final_merged_filename,
                    'download_url': download_url,
                    'status': 'success'
                }]
            else:
                 logger.error(f"Final merged file {final_merged_path} not found after processing.")
                 processed_results.append({'original_name': "Merged Document", 'status': 'conversion_error', 'message': '合并后的最终文件未找到。'})

        except Exception as e:
            logger.exception("Error during merging or final conversion of merged document")
            # Cleanup any intermediate merged docx if it exists and an error occurred
            if os.path.exists(merged_docx_path):
                try: os.remove(merged_docx_path); logger.debug(f"Cleaned up partially merged DOCX due to error: {merged_docx_path}")
                except OSError: pass
            # Cleanup individual temp files as well
            for doc_info in temp_files_for_script_processing:
                if os.path.exists(doc_info['path']): 
                    try: os.remove(doc_info['path']); logger.debug(f"Cleaned up temp script output due to merge error: {doc_info['path']}")
                    except OSError: pass
            processed_results.append({'original_name': "Merged Document", 'status': 'conversion_error', 'message': f'合并或转换时出错: {str(e)}'})
    
    elif not merge_output and temp_files_for_script_processing: # Process individual files
        for file_info in temp_files_for_script_processing:
            temp_docx_for_individual_conversion = file_info['path']
            original_image_name = file_info['original_name']
            base_filename_no_ext = file_info['base_filename_no_ext']

            final_output_filename = f"{base_filename_no_ext}.{output_format}"
            final_output_path = os.path.join(user_converted_dir, final_output_filename)

            conversion_successful = False
            if output_format == 'pdf':
                if DOCX2PDF_AVAILABLE_IN_VIEW:
                    try:
                        logger.info(f"Converting individual DOCX '{temp_docx_for_individual_conversion}' to PDF '{final_output_path}'")
                        convert_docx_to_pdf(temp_docx_for_individual_conversion, final_output_path)
                        logger.info(f"Successfully converted '{temp_docx_for_individual_conversion}' to PDF: {final_output_path}")
                        try: os.remove(temp_docx_for_individual_conversion); logger.debug(f"Removed temp DOCX for PDF: {temp_docx_for_individual_conversion}")
                        except OSError as e: logger.warning(f"Could not remove temp DOCX {temp_docx_for_individual_conversion}: {e}")
                        conversion_successful = True
                    except Exception as e:
                        logger.error(f"Error converting individual DOCX '{temp_docx_for_individual_conversion}' to PDF: {e}", exc_info=True)
                        # Fallback: keep the docx and serve that if PDF fails
                        final_output_filename = f"{base_filename_no_ext}.docx"
                        final_output_path = temp_docx_for_individual_conversion # The original docx path
                        messages.warning(request, f"文件 {original_image_name} 的PDF转换失败，已生成DOCX。")
                        conversion_successful = True # Still successful as docx
                else:
                    logger.error("PDF conversion for individual file requested, but docx2pdf not available. Serving DOCX.")
                    final_output_filename = f"{base_filename_no_ext}.docx"
                    final_output_path = temp_docx_for_individual_conversion
                    messages.warning(request, f"文件 {original_image_name} 的PDF转换库不可用，已生成DOCX。")
                    conversion_successful = True # Still successful as docx
            elif output_format == 'docx':
                # The file is already in docx (temp_docx_for_individual_conversion), rename/move it to final_output_path
                if temp_docx_for_individual_conversion != final_output_path:
                    try:
                        os.rename(temp_docx_for_individual_conversion, final_output_path)
                        logger.info(f"Moved/Renamed DOCX from {temp_docx_for_individual_conversion} to {final_output_path}")
                        conversion_successful = True
                    except OSError as e:
                        logger.error(f"Error moving/renaming {temp_docx_for_individual_conversion} to {final_output_path}: {e}")
                        # If rename fails, the original temp docx is still there, try to use it
                        final_output_path = temp_docx_for_individual_conversion 
                        final_output_filename = os.path.basename(temp_docx_for_individual_conversion)
                        conversion_successful = True # count as success if original temp file exists
                else: # Source and dest are the same, already correct
                    conversion_successful = True
            
            if conversion_successful and os.path.exists(final_output_path):
                relative_media_path = os.path.join(request.user.username, 'converted_files', final_output_filename).replace("\\\\", "/")
                download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                processed_results.append({
                    'original_name': original_image_name,
                    'converted_name': final_output_filename,
                    'download_url': download_url,
                    'status': 'success'
                })
            elif os.path.exists(temp_docx_for_individual_conversion): # Fallback if final path doesn't exist but temp docx does
                 logger.warning(f"Final path {final_output_path} not found, but temp docx {temp_docx_for_individual_conversion} exists. Serving temp docx.")
                 final_output_filename = os.path.basename(temp_docx_for_individual_conversion)
                 relative_media_path = os.path.join(request.user.username, 'converted_files', final_output_filename).replace("\\\\", "/")
                 download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                 processed_results.append({
                    'original_name': original_image_name,
                    'converted_name': final_output_filename,
                    'download_url': download_url,
                    'status': 'success'
                })
            else:
                # This case should ideally be caught by script execution check earlier
                logger.error(f"Neither final output '{final_output_path}' nor temp DOCX '{temp_docx_for_individual_conversion}' found for {original_image_name}.")
                if not any(pr['original_name'] == original_image_name for pr in processed_results): # Avoid duplicate error
                    processed_results.append({
                        'original_name': original_image_name,
                        'status': 'conversion_error',
                        'message': '处理后的文件丢失。'
                    })

    elif not temp_files_for_script_processing and any(r['status'] == 'uploaded' for r in uploaded_files_raw_info):
        logger.warning("No files were successfully processed by the script to either merge or convert individually.")
        # Check if there are already specific errors from script run for these files
        has_script_errors = any(pr.get('status') == 'conversion_error' and pr.get('original_name') in [uf['name'] for uf in uploaded_files_raw_info if uf['status']=='uploaded'] for pr in processed_results)
        if not has_script_errors:
             processed_results.append({
                'original_name': "Conversion Attempt",
                'status': 'conversion_error',
                'message': '没有文件成功通过初始脚本处理。'
            })

    logger.debug(f"Final processed_results before JsonResponse: {processed_results}")
    return JsonResponse({'results': processed_results})
