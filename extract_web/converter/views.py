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
from datetime import datetime # 新增 datetime
from django.urls import reverse

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
            # 删除整个 his_pic/<username> 目录，包括所有日期子目录
            user_folder_path = os.path.join(settings.BASE_DIR, 'his_pic', username)
            if os.path.exists(user_folder_path):
                try:
                    import shutil
                    shutil.rmtree(user_folder_path)
                    messages.success(request, f"用户 '{username}' 的所有数据文件夹已成功删除。")
                    logger.info(f"Deleted entire user data folder for {username} at {user_folder_path}")
                except OSError as e:
                    messages.error(request, f"删除用户 '{username}' 的数据文件夹时出错: {e}")
                    logger.error(f"Error deleting user data folder for {username}: {e}")
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
    today_date_str = datetime.now().strftime("%Y%m%d")
    user_base_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, today_date_str)

    user_upload_dir = os.path.join(user_base_dir, 'uploads')
    user_converted_dir = os.path.join(user_base_dir, 'converted_files')
    
    os.makedirs(user_upload_dir, exist_ok=True)
    os.makedirs(user_converted_dir, exist_ok=True)
    logger.info(f"Ensured daily directories exist: Uploads='{user_upload_dir}', Converted='{user_converted_dir}'")

    script_path = os.path.join(settings.BASE_DIR.parent, 'extract_text_from_images.py')
    
    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    output_format = request.POST.get('output_format', 'docx').lower() # 新增：获取输出格式

    logger.debug(f"Process Images Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, Format={output_format}")

    if output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW:
        logger.error("PDF output requested by view, but docx2pdf is not available in the Django view environment.")
        # 可以考虑返回一个特定的错误信息给前端，告知用户PDF转换不可用
        # For now, let it proceed, script will also check and might fallback or error.

    uploaded_files_raw_info = []
    for uploaded_file in request.FILES.getlist('images'):
        original_filename = uploaded_file.name
        # 保存上传文件到当天的日期目录下
        uploaded_file_path = os.path.join(user_upload_dir, original_filename)
        try:
            with open(uploaded_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_files_raw_info.append({'name': original_filename, 'status': 'uploaded', 'path': uploaded_file_path})
        except Exception as e:
            logger.error(f"Error uploading file {original_filename} to {user_upload_dir}: {e}")
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
        logger.debug(f"Attempting to merge {len(temp_files_for_script_processing)} DOCX files for date {today_date_str}.")
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        merged_base_filename = f"{request.user.username}_{today_date_str}_{random_chars}"
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
                # Save original names to a .meta file for the merged output
                meta_file_path_merged = f"{final_merged_path}.meta"
                merged_original_names_list = [info['original_name'] for info in temp_files_for_script_processing]
                try:
                    with open(meta_file_path_merged, 'w', encoding='utf-8') as mf:
                        mf.write(",".join(merged_original_names_list))
                    logger.info(f"Saved meta file for merged output: {meta_file_path_merged}")
                except Exception as e:
                    logger.error(f"Error saving .meta file {meta_file_path_merged}: {e}")

                relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_merged_filename).replace("\\", "/")
                download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                processed_results = [{
                    'original_name': ",".join(merged_original_names_list), # Display actual original filenames for merged result on main page
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
                        # messages.warning(request, f"文件 {original_image_name} 的PDF转换失败，已生成DOCX。") # Message already in process_images_view
                        # conversion_successful = True # Already set in process_images_view

                        # For individual files, save original name to a .meta file
                        meta_file_path = f"{final_output_path}.meta"
                        try:
                            with open(meta_file_path, 'w', encoding='utf-8') as mf:
                                mf.write(original_image_name)
                            logger.info(f"Saved meta file for individual conversion: {meta_file_path}")
                        except Exception as e:
                            logger.error(f"Error saving .meta file {meta_file_path}: {e}")
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
                # Save original name to a .meta file for the individual output
                meta_file_path_individual = f"{final_output_path}.meta"
                try:
                    with open(meta_file_path_individual, 'w', encoding='utf-8') as mf:
                        mf.write(original_image_name)
                    logger.info(f"Saved meta file for individual conversion: {meta_file_path_individual}")
                except Exception as e:
                    logger.error(f"Error saving .meta file {meta_file_path_individual}: {e}")

                relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_output_filename).replace("\\", "/")
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
                 relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_output_filename).replace("\\", "/")
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
    logger.info(f"Final processed results to be sent to client: {processed_results}")
    return JsonResponse({'results': processed_results, 'merge_output': merge_output})

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

    # Redirect to the history page, maintaining the selected date if possible
    redirect_url = reverse('converter:conversion_history')
    if date_str:
        redirect_url += f'?date={date_str}'
    return redirect(redirect_url)
