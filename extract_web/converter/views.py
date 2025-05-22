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
            # 修改：用户文件夹路径与 register 和 process_image_to_word_view 统一
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
def process_image_to_word_view(request):
    uploaded_files_raw_info = []
    # 修改：路径基于 settings.BASE_DIR (extract_web)
    user_upload_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, 'uploads')
    user_converted_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, 'converted_files')
    
    logger.debug(f"Ensuring user_upload_dir exists: {user_upload_dir}")
    os.makedirs(user_upload_dir, exist_ok=True)
    logger.debug(f"Ensuring user_converted_dir exists: {user_converted_dir}")
    os.makedirs(user_converted_dir, exist_ok=True)

    # script_path 仍然是相对于项目根目录 (extract_doc)
    script_path = os.path.join(settings.BASE_DIR.parent, 'extract_text_from_images.py')
    logger.debug(f"Calculated script_path: {script_path}")
    logger.debug(f"settings.BASE_DIR: {settings.BASE_DIR}") # Should be extract_web

    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    logger.debug(f"Merge output: {merge_output}")

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
    temp_docx_files = [] 

    for up_file_info in uploaded_files_raw_info:
        if up_file_info['status'] == 'uploaded':
            original_name = up_file_info['name']
            input_image_path = up_file_info['path']
            temp_output_filename = f"{os.path.splitext(original_name)[0]}.docx"
            temp_output_docx_path = os.path.join(user_converted_dir, temp_output_filename) # This now uses the corrected user_converted_dir

            try:
                python_executable = 'python' 
                command = [
                    python_executable, 
                    script_path, 
                    input_image_path, 
                    temp_output_docx_path 
                ]
                
                result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')

                if result.returncode == 0 and os.path.exists(temp_output_docx_path):
                    if merge_output:
                        temp_docx_files.append({'path': temp_output_docx_path, 'original_name': original_name})
                    else: 
                        relative_media_path = os.path.join(request.user.username, 'converted_files', temp_output_filename).replace("\\\\", "/")
                        download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                        processed_results.append({
                            'original_name': original_name,
                            'converted_name': temp_output_filename,
                            'download_url': download_url, 
                            'status': 'success'
                        })
                else: 
                    error_message = result.stderr or result.stdout or "Script execution failed."
                    if not os.path.exists(temp_output_docx_path):
                         error_message += " Output file not found."
                    logger.error(f"Error converting {original_name}: {error_message}")
                    processed_results.append({ 
                        'original_name': original_name,
                        'converted_name': '',
                        'download_url': '',
                        'status': 'conversion_error',
                        'message': error_message
                    })
            except Exception as e:
                logger.exception(f"Exception during conversion of {original_name}")
                processed_results.append({
                    'original_name': original_name,
                    'converted_name': '',
                    'download_url': '',
                    'status': 'conversion_error',
                    'message': f'服务器内部错误: {str(e)}'
                })
        else: 
            processed_results.append(up_file_info)

    if merge_output and temp_docx_files:
        logger.debug(f"Attempting to merge {len(temp_docx_files)} files.")
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        merged_filename = f"{request.user.username}_{random_chars}.docx"
        merged_docx_path = os.path.join(user_converted_dir, merged_filename) # This now uses the corrected user_converted_dir
        logger.debug(f"Merged filename will be: {merged_docx_path}")
        logger.debug(f"Target directory for merged file ({user_converted_dir}) exists: {os.path.exists(user_converted_dir)}")
        
        master_doc = Document()
        
        try:
            logger.debug("Starting loop to append documents for merging.")
            for i, doc_info in enumerate(temp_docx_files):
                logger.debug(f"Merging document: {doc_info['path']}")
                sub_doc = Document(doc_info['path'])
                if i > 0: 
                    logger.debug("Adding page break.")
                    master_doc.add_page_break()
                append_document(sub_doc, master_doc)
                logger.debug(f"Appended {doc_info['original_name']} to master document.")
            
            logger.debug(f"Attempting to save merged document to: {merged_docx_path}")
            master_doc.save(merged_docx_path)
            if os.path.exists(merged_docx_path):
                logger.debug(f"SUCCESS: Merged document confirmed to exist at {merged_docx_path} after save.")
            else:
                logger.error(f"FAILURE: Merged document NOT FOUND at {merged_docx_path} immediately after save call.")
            
            logger.debug("Cleaning up temporary files.")
            for doc_info in temp_docx_files:
                try:
                    if os.path.exists(doc_info['path']): 
                        os.remove(doc_info['path'])
                        logger.debug(f"Removed temporary file: {doc_info['path']}")
                    else:
                        logger.warning(f"Temporary file not found for deletion: {doc_info['path']}")
                except OSError as e:
                    logger.error(f"Error deleting temporary file {doc_info['path']}: {e}")

            relative_media_path = os.path.join(request.user.username, 'converted_files', merged_filename).replace("\\\\", "/")
            download_url = f"{settings.MEDIA_URL}{relative_media_path}"
            
            merged_original_names = ", ".join([info['original_name'] for info in temp_docx_files])
            if os.path.exists(merged_docx_path):
                processed_results = [{ 
                    'original_name': f"Merged: {merged_original_names}",
                    'converted_name': merged_filename,
                    'download_url': download_url, 
                    'status': 'success'
                }]
                logger.debug("Merge process successful, result prepared.")
            else:
                logger.error("Merge process reported success, but merged file is missing. Reporting error.")
                processed_results.append({
                    'original_name': f"Merged: {merged_original_names}",
                    'converted_name': merged_filename,
                    'download_url': '',
                    'status': 'conversion_error',
                    'message': '合并后的文件未能正确保存，请联系管理员。'
                })

        except Exception as e:
            logger.exception("Error during merging documents")
            processed_results.append({
                'original_name': "Merged Document",
                'converted_name': '',
                'download_url': '',
                'status': 'conversion_error',
                'message': f'合并文件时出错: {str(e)}'
            })

    elif merge_output and not temp_docx_files and any(r['status'] == 'uploaded' for r in uploaded_files_raw_info):
        logger.debug("Merge requested, but no files were successfully converted to merge.")
        if not any(r['status'] == 'success' for r in processed_results):
             processed_results.append({
                'original_name': "Merge Attempt",
                'converted_name': '',
                'download_url': '',
                'status': 'conversion_error',
                'message': '没有文件成功转换以进行合并。请检查单个文件错误。'
            })

    logger.debug(f"Final processed_results before JsonResponse: {processed_results}")
    return JsonResponse({'results': processed_results})
