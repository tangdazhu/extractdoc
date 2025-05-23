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
import shutil # Import shutil earlier as it's used in multiple places
from .ppt_pdf_converter import convert_pptx_to_pdf # 导入PPT转换模块
from .pic_file_converter import process_images_to_files # 导入图片转文件模块

logger = logging.getLogger('converter') # 获取 logger 实例

# Attempt to import PyPDF2 for PDF merging
try:
    from PyPDF2 import PdfMerger, PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 library is not installed. Merging multiple PPT/PPTX files into a single PDF will not be available.")

# 尝试导入 docx2pdf，如果失败则记录错误，但脚本仍可生成docx
try:
    from docx2pdf import convert as convert_docx_to_pdf
    DOCX2PDF_AVAILABLE_IN_VIEW = True
except ImportError:
    DOCX2PDF_AVAILABLE_IN_VIEW = False

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

    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    output_format = request.POST.get('output_format', 'docx').lower()
    main_tab = request.POST.get('main_tab', 'imgToFile') # Get main_tab
    sub_tab = request.POST.get('sub_tab', '') # Get sub_tab

    logger.debug(f"Process Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, Format={output_format}, MainTab={main_tab}, SubTab={sub_tab}")

    if output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW and main_tab != 'imgToFile': # PDF for non-image relies on this
        logger.error("PDF output requested for non-image file, but docx2pdf is not available in the Django view environment.")
        return JsonResponse({'results': [{'original_name': 'Conversion', 'status': 'error', 'message': 'PDF转换库不可用，无法处理此请求。'}], 'merge_output': merge_output})

    uploaded_files_info_from_frontend = []
    for uploaded_file in request.FILES.getlist('images'): # 'images' is the key from FormData
        original_filename = uploaded_file.name
        uploaded_file_path = os.path.join(user_upload_dir, original_filename)
        try:
            with open(uploaded_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_files_info_from_frontend.append({'name': original_filename, 'status': 'uploaded', 'path': uploaded_file_path})
        except Exception as e:
            logger.error(f"Error uploading file {original_filename} to {user_upload_dir}: {e}")
            uploaded_files_info_from_frontend.append({'name': original_filename, 'status': 'upload_error', 'message': str(e)})
    
    processed_results = []
    temp_files_for_final_processing = [] # Will store paths of files ready for final conversion/merge (docx or original non-image files)

    if main_tab == 'imgToFile':
        # 使用新的图片转文件处理模块
        img_processed_results, img_temp_files = process_images_to_files(uploaded_files_info_from_frontend, user_converted_dir)
        processed_results.extend(img_processed_results)
        temp_files_for_final_processing.extend(img_temp_files)
    
    elif main_tab == 'fileToPdf' and sub_tab == 'wordToPdf':
        logger.info(f"Processing via fileToPdf/wordToPdf (direct DOCX to PDF)")
        # 直接使用上传的Word文档进行后续处理
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                # For Word to PDF, the uploaded file itself is the source for conversion or merge.
                # We need to copy it to user_converted_dir if we intend to merge or convert from there,
                # or use its path from user_upload_dir directly if not merging before conversion.
                # For consistency with the merge logic, let's copy to converted_dir first.
                
                # Ensure it is a doc/docx file (though frontend should filter)
                if not (original_name.lower().endswith('.doc') or original_name.lower().endswith('.docx')):
                    logger.warning(f"Skipping non-Word file {original_name} in wordToPdf mode.")
                    processed_results.append({
                        'original_name': original_name, 'status': 'error',
                        'message': '文件类型不是 Word (.doc/.docx)。'
                    })
                    continue

                # Path of the uploaded file in 'uploads' directory
                source_word_path = up_file_info['path'] 
                
                # Define a temporary path in 'converted_files' for this Word file before final PDF conversion
                # This path will be used by the merging logic or direct conversion logic below.
                # If not merging, this file will be directly converted to PDF.
                # If merging, these files will be merged into another DOCX, then that to PDF.
                temp_word_in_converted_dir_filename = f"{os.path.splitext(original_name)[0]}_prePdf.docx" # Ensure it's .docx for our merge logic
                temp_word_in_converted_dir_path = os.path.join(user_converted_dir, temp_word_in_converted_dir_filename)
                
                try:
                    # If the source is .doc, we might need to convert to .docx first if merging relies on python-docx strictly for .docx
                    # For now, assume python-docx can handle .doc for reading, or direct docx2pdf can handle .doc
                    # Copy the file to the converted_files directory before processing
                    import shutil
                    shutil.copy(source_word_path, temp_word_in_converted_dir_path)
                    logger.info(f"Copied Word file {original_name} to {temp_word_in_converted_dir_path} for PDF conversion process.")
                    
                    temp_files_for_final_processing.append({
                        'path': temp_word_in_converted_dir_path, # This is the path to the .docx (or copied .doc as .docx)
                        'original_name': original_name,
                        'base_filename_no_ext': os.path.splitext(original_name)[0]
                    })
                except Exception as e:
                    logger.exception(f"Error preparing Word file {original_name} for conversion: {e}")
                    processed_results.append({
                        'original_name': original_name, 'status': 'error',
                        'message': f'准备Word文件时出错: {str(e)}'
                    })
            else:
                processed_results.append(up_file_info)
    elif main_tab == 'fileToPdf' and sub_tab == 'pptToPdf':
        logger.info(f"Processing via fileToPdf/pptToPdf (direct PPT/PPTX to PDF)")
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                if not (original_name.lower().endswith('.ppt') or original_name.lower().endswith('.pptx')):
                    logger.warning(f"Skipping non-PPT file {original_name} in pptToPdf mode.")
                    processed_results.append({
                        'original_name': original_name, 'status': 'error',
                        'message': '文件类型不是 PowerPoint (.ppt/.pptx)。'
                    })
                    continue

                source_ppt_path = up_file_info['path']
                # Determine a temporary name, try to keep original extension for docx2pdf if it matters
                # However, our merge logic might expect .docx. For direct conversion, original ext is fine.
                # For consistency, let's assume we might merge ppt/pptx into a docx-compatible format first if such a tool existed,
                # or more realistically, we convert each ppt to pdf individually or merge pdfs later.
                # For now, copy with a _prePdf marker, keeping original extension for direct conversion by docx2pdf.
                temp_ppt_in_converted_dir_filename = f"{os.path.splitext(original_name)[0]}_prePdf{os.path.splitext(original_name)[1]}"
                temp_ppt_in_converted_dir_path = os.path.join(user_converted_dir, temp_ppt_in_converted_dir_filename)
                
                try:
                    import shutil
                    shutil.copy(source_ppt_path, temp_ppt_in_converted_dir_path)
                    logger.info(f"Copied PPT/PPTX file {original_name} to {temp_ppt_in_converted_dir_path} for PDF conversion process.")
                    
                    temp_files_for_final_processing.append({
                        'path': temp_ppt_in_converted_dir_path, 
                        'original_name': original_name,
                        'base_filename_no_ext': os.path.splitext(original_name)[0]
                    })
                except Exception as e:
                    logger.exception(f"Error preparing PPT/PPTX file {original_name} for conversion: {e}")
                    processed_results.append({
                        'original_name': original_name, 'status': 'error',
                        'message': f'准备PPT文件时出错: {str(e)}'
                    })
            else:
                processed_results.append(up_file_info)
    else:
        logger.warning(f"Unhandled main_tab '{main_tab}' or sub_tab '{sub_tab}'. Cannot process files.")
        return JsonResponse({'results': [{'original_name': '-', 'status': 'error', 'message': '未实现的处理类型。'}], 'merge_output': merge_output})

    # 第二阶段：处理和合并 (现在 temp_files_for_final_processing 包含了需要处理的文件路径)
    # This section is largely the same, but operates on temp_files_for_final_processing
    # which contains paths to .docx files (either from script OCR or copied Word files)
    
    if merge_output and temp_files_for_final_processing:
        logger.debug(f"Attempting to merge {len(temp_files_for_final_processing)} files for date {today_date_str} (MainTab: {main_tab}, SubTab: {sub_tab}).")
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        merged_base_filename = f"{request.user.username}_{today_date_str}_{random_chars}"
        
        # Default final output to be PDF if the sub_tab implies it, or if original output_format was PDF
        # For pptToPdf, the final merged output should be PDF.
        if main_tab == 'fileToPdf' and sub_tab == 'pptToPdf':
            final_target_format_for_merge = 'pdf'
        else: # For imgToFile or wordToPdf, the existing output_format (which could be docx or pdf) is the target.
            final_target_format_for_merge = output_format

        final_merged_filename = f"{merged_base_filename}.{final_target_format_for_merge}"
        final_merged_path = os.path.join(user_converted_dir, final_merged_filename)

        if not temp_files_for_final_processing:
            logger.error("Merge requested but no files available in temp_files_for_final_processing.")
            return JsonResponse({'results': [{'original_name': 'Merge Error', 'status': 'error', 'message': '没有可合并的文件。'}], 'merge_output': merge_output})

        if main_tab == 'fileToPdf' and sub_tab == 'pptToPdf':
            if not PYPDF2_AVAILABLE:
                logger.error("Cannot merge PPTs to PDF: PyPDF2 library is not available.")
                processed_results = [{'original_name': "Merged Document", 'status': 'error', 'message': '无法合并PPT到PDF：缺少必需的PDF处理库(PyPDF2)。请先将各PPT单独转换为PDF。'}]
                # Fallback: attempt to convert each PPT to PDF individually instead of merging
                # This part would need to be refactored to call the individual processing logic.
                # For now, just error out for merge. User can uncheck "merge".
                # OR, we could try to produce individual PDFs and message the user.
                # Let's just error for now, it's cleaner than partial success with confusing output.
            else:
                logger.info("Merging PPTs to a single PDF using PyPDF2.")
                temp_individual_pdfs = []
                conversion_all_individual_ppt_to_pdf_successful = True
                
                for ppt_info in temp_files_for_final_processing:
                    individual_ppt_path = ppt_info['path']
                    individual_pdf_temp_name = f"{os.path.splitext(os.path.basename(individual_ppt_path))[0]}_temp.pdf"
                    individual_pdf_temp_path = os.path.join(user_converted_dir, individual_pdf_temp_name)
                    
                    try:
                        logger.info(f"Converting individual PPT '{individual_ppt_path}' to temporary PDF '{individual_pdf_temp_path}'")
                        # 使用新的PPT转换函数替代docx2pdf
                        success, actual_pdf_path, error_msg = convert_pptx_to_pdf(individual_ppt_path, individual_pdf_temp_path)
                        if success and actual_pdf_path:
                            temp_individual_pdfs.append(actual_pdf_path)
                            logger.info(f"Successfully converted '{individual_ppt_path}' to '{actual_pdf_path}'")
                        else:
                            raise Exception(error_msg or "PPT转换失败，未知原因")
                    except Exception as e_ind_pdf:
                        logger.error(f"Error converting individual PPT '{individual_ppt_path}' to PDF: {e_ind_pdf}", exc_info=True)
                        original_filename_str = ppt_info["original_name"]
                        exception_str = str(e_ind_pdf)
                        message = f"转换PPT '{original_filename_str}' 到PDF失败: {exception_str}"
                        processed_results.append({'original_name': ppt_info['original_name'], 
                                                  'status': 'error', 
                                                  'message': message})
                        conversion_all_individual_ppt_to_pdf_successful = False
                        break # Stop if one fails
                
                if conversion_all_individual_ppt_to_pdf_successful and temp_individual_pdfs:
                    pdf_merger = PdfMerger()
                    try:
                        for pdf_path in temp_individual_pdfs:
                            pdf_merger.append(pdf_path)
                        pdf_merger.write(final_merged_path)
                        pdf_merger.close()
                        logger.info(f"Successfully merged temporary PDFs into: {final_merged_path}")

                        # Meta file for merged PDF
                        meta_file_path_merged = f"{final_merged_path}.meta"
                        merged_original_names_list = [info['original_name'] for info in temp_files_for_final_processing]
                        try:
                            with open(meta_file_path_merged, 'w', encoding='utf-8') as mf:
                                mf.write(",".join(merged_original_names_list))
                        except Exception as e_meta: logger.error(f"Error saving .meta file {meta_file_path_merged}: {e_meta}")

                        relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_merged_filename).replace("\\", "/")
                        download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                        processed_results = [{'original_name': ",".join(merged_original_names_list), 'converted_name': final_merged_filename, 'download_url': download_url, 'status': 'success'}]
                    except Exception as e_merge_pdf:
                        logger.error(f"Error merging PDFs: {e_merge_pdf}", exc_info=True)
                        original_names_str = ",".join([info['original_name'] for info in temp_files_for_final_processing]) # Fallback original name
                        exception_str = str(e_merge_pdf)
                        message = f"合并PDF时出错 ({original_names_str}): {exception_str}"
                        processed_results.append({'original_name': "Merged Document", 
                                              'status': 'error', 
                                              'message': message})
                elif not temp_individual_pdfs and conversion_all_individual_ppt_to_pdf_successful : # Should not happen if list was populated
                     processed_results.append({'original_name': "Merged Document", 
                                           'status': 'error', 
                                           'message': '没有PDF文件可供合并。'})


                # Cleanup temporary individual PDFs and original PPTs from converted_files
                for temp_pdf in temp_individual_pdfs:
                    try: os.remove(temp_pdf); logger.debug(f"Cleaned up temp PDF: {temp_pdf}")
                    except OSError: pass
                for ppt_info in temp_files_for_final_processing: # These are the copied PPTs
                    try: os.remove(ppt_info['path']); logger.debug(f"Cleaned up temp PPT source: {ppt_info['path']}")
                    except OSError: pass
        
        else: # Existing merge logic for DOCX based sources (imgToFile, wordToPdf)
            merged_docx_path = os.path.join(user_converted_dir, f"{merged_base_filename}.docx") # DOCX is always the intermediate for these
            logger.debug(f"Merged DOCX (intermediate for non-PPT merge) filename will be: {merged_docx_path}")
            first_doc_path = temp_files_for_final_processing[0]['path']
            try:
                master_doc = Document(first_doc_path) 
                if len(temp_files_for_final_processing) > 1:
                    for doc_info in temp_files_for_final_processing[1:]:
                        sub_doc = Document(doc_info['path'])
                        master_doc.add_page_break()
                        append_document(sub_doc, master_doc)
                master_doc.save(merged_docx_path)
                logger.info(f"Merged DOCX (intermediate) saved successfully: {merged_docx_path}")

                for doc_info in temp_files_for_final_processing: # remove individual docx files
                    try: os.remove(doc_info['path']); logger.debug(f"Cleaned up temp file after DOCX merge: {doc_info['path']}")
                    except OSError as e: logger.warning(f"Could not clean up temp file {doc_info['path']} after DOCX merge: {e}")

                # Now, if final_target_format_for_merge is 'pdf', convert merged_docx_path to final_merged_path
                if final_target_format_for_merge == 'pdf':
                    if DOCX2PDF_AVAILABLE_IN_VIEW:
                        try:
                            logger.info(f"Converting merged DOCX '{merged_docx_path}' to PDF '{final_merged_path}'")
                            convert_docx_to_pdf(merged_docx_path, final_merged_path)
                            logger.info(f"Successfully converted merged DOCX to PDF: {final_merged_path}")
                            try: os.remove(merged_docx_path); logger.debug(f"Removed intermediate merged DOCX: {merged_docx_path}")
                            except OSError as e: logger.warning(f"Could not remove intermediate merged DOCX {merged_docx_path}: {e}")
                        except Exception as e_conv_pdf:
                            logger.error(f"Error converting merged DOCX to PDF: {e_conv_pdf}", exc_info=True)
                            # Fallback to the DOCX file
                            final_merged_filename = f"{merged_base_filename}.docx" # Update filename to .docx
                            final_merged_path = merged_docx_path # Path is already the docx path
                            messages.warning(request, "合并文件PDF转换失败，已生成DOCX文件。")
                    else:
                        logger.error("PDF conversion for merged DOCX requested, but docx2pdf is not available. Serving DOCX.")
                        final_merged_filename = f"{merged_base_filename}.docx"
                        final_merged_path = merged_docx_path
                        messages.warning(request, "PDF转换库不可用，已为合并文件生成DOCX文件。")
                elif final_target_format_for_merge == 'docx': # merged_docx_path is already final_merged_path essentially if no renaming
                    if merged_docx_path != final_merged_path: # Should be the case if final_merged_filename was already .docx
                         shutil.move(merged_docx_path, final_merged_path) # Ensure it's at final_merged_path
                    logger.info(f"Final merged file is DOCX: {final_merged_path}")


                if os.path.exists(final_merged_path):
                    meta_file_path_merged = f"{final_merged_path}.meta"
                    merged_original_names_list = [info['original_name'] for info in temp_files_for_final_processing]
                    try:
                        with open(meta_file_path_merged, 'w', encoding='utf-8') as mf:
                            mf.write(",".join(merged_original_names_list))
                    except Exception as e_meta: logger.error(f"Error saving .meta file {meta_file_path_merged}: {e_meta}")
                    
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_merged_filename).replace("\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    processed_results = [{'original_name': ",".join(merged_original_names_list), 'converted_name': final_merged_filename, 'download_url': download_url, 'status': 'success'}]
                else:
                     logger.error(f"Final merged file (from DOCX path) {final_merged_path} not found after processing.")
                     processed_results = [{'original_name': "Merged Document", 'status': 'error', 'message': '合并后的最终文件未找到 (DOCX path)。'}]
            except Exception as e_merge_docx:
                logger.exception("Error during DOCX-based merging or final conversion of merged document")
                if os.path.exists(merged_docx_path):
                    try: os.remove(merged_docx_path)
                    except OSError: pass
                for doc_info in temp_files_for_final_processing:
                    if os.path.exists(doc_info['path']): 
                        try: os.remove(doc_info['path'])
                        except OSError: pass
                
                original_names_str = ",".join([info['original_name'] for info in temp_files_for_final_processing]) # Fallback original name
                exception_str = str(e_merge_docx)
                message = f"DOCX合并或转换时出错 ({original_names_str}): {exception_str}"
                processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': message})

    elif not merge_output and temp_files_for_final_processing: # Process individual files
        for file_info in temp_files_for_final_processing:
            # file_info['path'] is the path to the .docx file (from OCR or copied Word file)
            # file_info['original_name'] is the original uploaded name
            temp_docx_for_individual_conversion = file_info['path']
            original_input_name = file_info['original_name']
            base_filename_no_ext = file_info['base_filename_no_ext']

            final_output_filename = f"{base_filename_no_ext}.{output_format}" # output_format from frontend, should be 'pdf' for wordToPdf
            final_output_path = os.path.join(user_converted_dir, final_output_filename)
            conversion_successful = False

            if output_format == 'pdf':
                if DOCX2PDF_AVAILABLE_IN_VIEW:
                    try:
                        logger.info(f"Converting individual file '{temp_docx_for_individual_conversion}' to PDF '{final_output_path}'")
                        
                        # 根据文件类型选择转换方法
                        if original_input_name.lower().endswith(('.ppt', '.pptx')):
                            # PPT文件使用专门的转换函数
                            success, actual_pdf_path, error_msg = convert_pptx_to_pdf(temp_docx_for_individual_conversion, final_output_path)
                            if not success:
                                raise Exception(error_msg or "PPT转换失败，未知原因")
                            if actual_pdf_path != final_output_path:
                                final_output_path = actual_pdf_path
                                final_output_filename = os.path.basename(actual_pdf_path)
                        else:
                            # Word文件使用docx2pdf
                            convert_docx_to_pdf(temp_docx_for_individual_conversion, final_output_path)
                        
                        logger.info(f"Successfully converted '{temp_docx_for_individual_conversion}' to PDF: {final_output_path}")
                        try: os.remove(temp_docx_for_individual_conversion); logger.debug(f"Removed temp source after PDF: {temp_docx_for_individual_conversion}")
                        except OSError as e: logger.warning(f"Could not remove temp source {temp_docx_for_individual_conversion}: {e}")
                        conversion_successful = True
                    except Exception as e:
                        logger.error(f"Error converting individual file '{temp_docx_for_individual_conversion}' to PDF: {e}", exc_info=True)
                        # Fallback: keep the source file if PDF fails
                        final_output_filename = os.path.basename(temp_docx_for_individual_conversion) # use its name
                        final_output_path = temp_docx_for_individual_conversion # use its path
                        
                        exception_str = str(e)
                        file_type = "PPT" if original_input_name.lower().endswith(('.ppt', '.pptx')) else "Word"
                        message = f"文件 {original_input_name} 的PDF转换失败，保留原始{file_type}文件。错误: {exception_str}"
                        messages.warning(request, message) # Inform user via Django messages as well

                        processed_results.append({ # Add to results so frontend knows about this file
                            'original_name': original_input_name,
                            'converted_name': final_output_filename, # The original/fallback filename
                            'download_url': None, # No download URL if it's a fallback and not in media yet, or construct carefully
                            'status': 'conversion_error_fallback',
                            'message': message
                        })
                        # Instead of directly setting conversion_successful = True for fallback,
                        # we handle it via the append above and subsequent logic.
                        # The key is that final_output_path points to the fallback file.
                        # We will still try to create a meta file for this fallback.
                        conversion_successful = True # Mark as successful for the meta file logic to run for the fallback file
                else: # docx2pdf not available
                    logger.error(f"PDF conversion for {original_input_name} requested, but docx2pdf not available. Serving original format.")
                    final_output_filename = os.path.basename(temp_docx_for_individual_conversion) # use its name
                    final_output_path = temp_docx_for_individual_conversion # use its path
                    file_type = "PPT" if original_input_name.lower().endswith(('.ppt', '.pptx')) else "Word"
                    messages.warning(request, f"文件 {original_input_name} 的PDF转换库不可用，已保留原始{file_type}格式文件。")
                    conversion_successful = True 
            elif output_format == 'docx': # This case is mostly for imgToFile where output_format can be docx
                # The file is already in docx (temp_docx_for_individual_conversion), rename/move it if necessary
                if temp_docx_for_individual_conversion != final_output_path:
                    try:
                        os.rename(temp_docx_for_individual_conversion, final_output_path)
                        logger.info(f"Moved/Renamed DOCX from {temp_docx_for_individual_conversion} to {final_output_path}")
                        conversion_successful = True
                    except OSError as e:
                        logger.error(f"Error moving/renaming {temp_docx_for_individual_conversion} to {final_output_path}: {e}")
                        final_output_path = temp_docx_for_individual_conversion 
                        final_output_filename = os.path.basename(temp_docx_for_individual_conversion)
                        conversion_successful = True 
                else: 
                    conversion_successful = True
            
            if conversion_successful and os.path.exists(final_output_path):
                meta_file_path_individual = f"{final_output_path}.meta"
                try:
                    with open(meta_file_path_individual, 'w', encoding='utf-8') as mf:
                        mf.write(original_input_name)
                    logger.info(f"Saved meta file for individual output: {meta_file_path_individual}")
                except Exception as e: logger.error(f"Error saving .meta file {meta_file_path_individual}: {e}")

                relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_output_filename).replace("\\", "/")
                download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                processed_results.append({
                    'original_name': original_input_name,
                    'converted_name': final_output_filename,
                    'download_url': download_url,
                    'status': 'success'
                })
            elif os.path.exists(temp_docx_for_individual_conversion): # Fallback if final path doesn't exist but temp source does
                 # ... (fallback logic as before)
                 logger.warning(f"Final path {final_output_path} not found, but temp source {temp_docx_for_individual_conversion} exists. Serving temp source.")
                 final_output_filename = os.path.basename(temp_docx_for_individual_conversion)
                 relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_output_filename).replace("\\", "/")
                 download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                 processed_results.append({
                    'original_name': original_input_name,
                    'converted_name': final_output_filename,
                    'download_url': download_url,
                    'status': 'success' # Or appropriate status
                })
            else:
                # ... (error handling as before) ...
                logger.error(f"Neither final output '{final_output_path}' nor temp source '{temp_docx_for_individual_conversion}' found for {original_input_name}.")
                if not any(pr['original_name'] == original_input_name for pr in processed_results):
                    processed_results.append({
                        'original_name': original_input_name,
                        'status': 'conversion_error',
                        'message': '处理后的文件丢失。'
                    })

    elif not temp_files_for_final_processing and any(r['status'] == 'uploaded' for r in uploaded_files_info_from_frontend):
        logger.warning("No files were successfully prepared for final processing (merge or individual conversion).")
        # If processed_results already contains specific errors from upload or prep, don't add a generic one.
        if not processed_results or all(p.get('status') == 'uploaded' for p in processed_results):
            processed_results.append({
                'original_name': "Conversion Attempt",
                'status': 'conversion_error',
                'message': '没有文件成功准备好进行最终处理。'
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
