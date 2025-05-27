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
from converter import ppt_pdf_converter # 新的导入方式
from .pic_file_converter import process_images_to_files # 导入图片转文件模块
from .excel_pdf_converter import convert_excel_to_pdf # 导入Excel转换模块
from .txt_to_pdf_converter import convert_txt_to_pdf
from .pdf_to_excel_converter import convert_pdf_to_excel
from .pdf_to_word_converter import convert_pdf_to_word
# Add new imports for PDF to X converters
from .pdf_to_ppt_converter import convert_pdf_to_ppt
from .pdf_to_txt_converter import convert_pdf_to_txt
from .libreoffice_converter import convert_to_pdf as convert_to_pdf_libreoffice # Import LO converter
from .word_to_pdf_converter import convert_word_to_pdf # ADDED: Import for the new Word to PDF converter

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
    # Optionally define a fallback or placeholder function if needed, or just rely on the flag
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
def process_images_view(request):
    today_date_str = datetime.now().strftime("%Y%m%d")
    request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    logger.debug(f"Generated unique request_id: {request_id} for this conversion process.")

    user_base_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, today_date_str)
    user_upload_dir = os.path.join(user_base_dir, 'uploads')
    user_converted_dir = os.path.join(user_base_dir, 'converted_files')
    
    os.makedirs(user_upload_dir, exist_ok=True)
    os.makedirs(user_converted_dir, exist_ok=True)
    logger.info(f"Ensured daily directories exist: Uploads='{user_upload_dir}', Converted='{user_converted_dir}', RequestID: {request_id}")

    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    output_format_param = request.POST.get('output_format', '')
    main_tab = request.POST.get('main_tab', 'imgToFile')
    sub_tab = request.POST.get('sub_tab', '')
    output_format = ''
    pdf_to_ppt_mode = 'screenshot' # Default for all cases, will be overridden if applicable

    if main_tab == 'fileToPdf':
        output_format = 'pdf'
    elif main_tab == 'imgToFile':
        output_format = output_format_param if output_format_param else 'docx'
    elif main_tab == 'pdfToFile':
        if sub_tab == 'pdfToWord': output_format = 'docx'
        elif sub_tab == 'pdfToExcel': output_format = 'xlsx'
        elif sub_tab == 'pdfToPpt': 
            output_format = 'pptx'
            pdf_to_ppt_mode = request.POST.get('pdf_to_ppt_mode', 'screenshot') # Get the mode from POST
            logger.info(f"[process_images_view] PDF to PPT mode explicitly set to: {pdf_to_ppt_mode} for RequestID: {request_id}")
        elif sub_tab == 'pdfToTxt': output_format = 'txt'
        else:
            output_format = output_format_param
            logger.warning(f"pdfToFile: Unknown sub_tab ('{sub_tab}'), fallback to param: '{output_format_param}', RequestID: {request_id}")
            if not output_format: output_format = 'docx'; logger.error(f"pdfToFile: Critical fallback to docx for unknown sub_tab, RequestID: {request_id}")
    else: 
        output_format = output_format_param
        logger.warning(f"Unhandled main_tab '{main_tab}', fallback to param: '{output_format_param}', RequestID: {request_id}")
        if not output_format: output_format = 'docx'; logger.error(f"Fallback: Critical fallback to docx for unhandled main_tab, RequestID: {request_id}")

    logger.debug(f"Process Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, RequestedFormat='{output_format_param}', EffectiveOutputFormat='{output_format}', MainTab={main_tab}, SubTab={sub_tab}, PDFtoPPTMode={pdf_to_ppt_mode}, RequestID: {request_id}")

    if main_tab == 'fileToPdf' and output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW and sub_tab == 'wordToPdf':
        logger.error(f"PDF output requested for Word file, but docx2pdf is not available. RequestID: {request_id}")
        return JsonResponse({'results': [{'original_name': 'Conversion', 'status': 'error', 'message': 'Word转PDF的转换库(docx2pdf)不可用。'}], 'merge_output': merge_output})

    uploaded_files_info_from_frontend = []
    for uploaded_file in request.FILES.getlist('images'): 
        original_filename = uploaded_file.name
        safe_original_filename = Path(original_filename).name
        uploaded_file_path = os.path.join(user_upload_dir, safe_original_filename)
        try:
            with open(uploaded_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_files_info_from_frontend.append({'name': safe_original_filename, 'status': 'uploaded', 'path': uploaded_file_path})
        except Exception as e:
            logger.error(f"Error uploading file {safe_original_filename} to {user_upload_dir} (RequestID: {request_id}): {e}")
            uploaded_files_info_from_frontend.append({'name': safe_original_filename, 'status': 'upload_error', 'message': str(e)})
    
    processed_results = []
    temp_files_for_final_processing = [] 

    if main_tab == 'imgToFile':
        img_processed_results, img_temp_files_list_of_dicts = process_images_to_files(
            uploaded_files_info_from_frontend, 
            user_converted_dir,
            request_id 
        )
        processed_results.extend(img_processed_results) 
        temp_files_for_final_processing.extend(img_temp_files_list_of_dicts)

    elif main_tab == 'fileToPdf':
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                source_file_path = up_file_info['path']
                base_name_no_ext = os.path.splitext(original_name)[0]
                temp_file_ext = os.path.splitext(original_name)[1]
                temp_file_in_converted_dir_filename = f"{base_name_no_ext}_prePdf_{request_id}{temp_file_ext}"
                temp_file_in_converted_dir_path = os.path.join(user_converted_dir, temp_file_in_converted_dir_filename)
                try:
                    valid_type = False
                    if sub_tab == 'wordToPdf' and original_name.lower().endswith(('.doc', '.docx')): valid_type = True
                    elif sub_tab == 'excelToPdf' and original_name.lower().endswith(('.xls', '.xlsx')):
                        valid_type = True
                        if os.path.exists(temp_file_in_converted_dir_path):
                            try: os.remove(temp_file_in_converted_dir_path) # Remove if exists from a retry of same request_id
                            except OSError as e_remove: logger.error(f"Failed to remove existing target for Excel prePdf (RequestID: {request_id}): {e_remove}", exc_info=True)
                    elif sub_tab == 'pptToPdf' and original_name.lower().endswith(('.ppt', '.pptx')): valid_type = True
                    elif sub_tab == 'txtToPdf' and original_name.lower().endswith('.txt'): valid_type = True
                    
                    if not valid_type:
                        error_message = f"文件类型不匹配 ({sub_tab}): {original_name}"
                        logger.warning(f"{error_message} (RequestID: {request_id})")
                        processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                        continue
                    shutil.copy(source_file_path, temp_file_in_converted_dir_path)
                    logger.info(f"Copied {original_name} to {temp_file_in_converted_dir_path} for PDF conversion (RequestID: {request_id}).")
                    temp_files_for_final_processing.append({
                        'path': temp_file_in_converted_dir_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext
                    })
                except PermissionError as pe:
                    logger.error(f"Permission denied for {original_name} to {temp_file_in_converted_dir_path} (RequestID: {request_id}): {pe}", exc_info=True)
                    processed_results.append({'original_name': original_name, 'status': 'error','message': f'准备文件时权限不足: {str(pe)}'})
                except Exception as e:
                    logger.exception(f"Error preparing {original_name} for fileToPdf (RequestID: {request_id}): {e}")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': f'准备文件时出错: {str(e)}'})
            else: 
                processed_results.append(up_file_info)
    
    elif main_tab == 'pdfToFile':
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                source_file_path = up_file_info['path']
                base_name_no_ext = os.path.splitext(original_name)[0]
                
                # For pdfToFile, the temp files are just copies of the original PDFs, 
                # as the conversion happens during the final merge or individual processing step.
                temp_file_in_converted_dir_filename = f"{base_name_no_ext}_preFinal_{request_id}{os.path.splitext(original_name)[1]}"
                temp_file_in_converted_dir_path = os.path.join(user_converted_dir, temp_file_in_converted_dir_filename)
                try:
                    if not original_name.lower().endswith('.pdf'):
                        error_message = f"文件类型不匹配 ({sub_tab}): {original_name} (应为PDF)"
                        logger.warning(f"{error_message} (RequestID: {request_id})")
                        processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                        continue # Skip this file for temp_files_for_final_processing
                    
                    shutil.copy(source_file_path, temp_file_in_converted_dir_path)
                    logger.info(f"Copied {original_name} to {temp_file_in_converted_dir_path} for {main_tab}/{sub_tab} (RequestID: {request_id}).")
                    temp_files_for_final_processing.append({
                        'path': temp_file_in_converted_dir_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext,
                        'status': 'success' # Mark as success for this stage
                    })
                except PermissionError as pe:
                    logger.error(f"Permission denied for {original_name} to {temp_file_in_converted_dir_path} (RequestID: {request_id}): {pe}", exc_info=True)
                    processed_results.append({'original_name': original_name, 'status': 'error','message': f'准备文件时权限不足: {str(pe)}'})
                except Exception as e:
                    logger.exception(f"Error preparing {original_name} for pdfToFile (RequestID: {request_id}): {e}")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': f'准备文件时出错: {str(e)}'})
            else: 
                processed_results.append(up_file_info) # Carry over upload errors

    else: 
        if main_tab not in ['imgToFile', 'fileToPdf', 'pdfToFile'] and not any(r['status'] == 'error' for r in processed_results): 
            logger.warning(f"Unhandled main_tab '{main_tab}' or no files processed. RequestID: {request_id}")
            if not uploaded_files_info_from_frontend:
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件。'})
            elif not temp_files_for_final_processing and any(info['status'] == 'uploaded' for info in uploaded_files_info_from_frontend):
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '上传的文件无法按当前选择的模式处理。'})
            elif not temp_files_for_final_processing : 
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有文件可供处理。'})

    # Filter out files that failed initial processing for merge/individual conversion stages
    valid_temp_files_for_processing = [f for f in temp_files_for_final_processing if f.get('status') == 'success']

    if valid_temp_files_for_processing:
        if merge_output:
            logger.debug(f"Attempting to merge {len(valid_temp_files_for_processing)} files. MainTab: {main_tab}, SubTab: {sub_tab}, OutputFormat: {output_format}, RequestID: {request_id}.")
            # Use a consistent merged base name for all merged files
            merged_base_name_for_file = f"merged_{request_id}"
            final_merged_filename = f"{merged_base_name_for_file}.{output_format}"
            final_merged_path = os.path.join(user_converted_dir, final_merged_filename)
            
            original_names_for_meta = [item['original_name'] for item in valid_temp_files_for_processing]
            if not original_names_for_meta: original_names_for_meta = ["Unknown original files"]

            current_merge_op_success = False
            current_merge_op_message = ""
            paths_of_temp_sources_for_merge = [item['path'] for item in valid_temp_files_for_processing]

            try:
                if main_tab == 'imgToFile': # Merging for imgToFile (always to DOCX, then optionally to PDF)
                    # This implies intermediate DOCX files were created by process_images_to_files
                    # and are in paths_of_temp_sources_for_merge
                    temp_merged_docx_path = os.path.join(user_converted_dir, f"{merged_base_name_for_file}_intermediate.docx")
                    
                    master_doc = Document(paths_of_temp_sources_for_merge[0])
                    for doc_path in paths_of_temp_sources_for_merge[1:]:
                        sub_doc = Document(doc_path)
                        master_doc.add_page_break()
                        append_document(sub_doc, master_doc)
                    master_doc.save(temp_merged_docx_path)
                    logger.info(f"imgToFile: Merged intermediate DOCX saved to {temp_merged_docx_path}. RequestID: {request_id}")

                    if output_format == 'docx':
                        if temp_merged_docx_path != final_merged_path:
                             shutil.move(temp_merged_docx_path, final_merged_path)
                        current_merge_op_success = True
                        current_merge_op_message = "图片已合并为Word文档。"
                    elif output_format == 'pdf':
                        # Convert the merged DOCX to PDF
                        pdf_success, pdf_path_or_msg, _ = convert_word_to_pdf(temp_merged_docx_path, final_merged_path), # final_merged_path has .pdf ext
                        if pdf_success and os.path.exists(final_merged_path):
                            current_merge_op_success = True
                            current_merge_op_message = "图片已合并并转换为PDF。"
                        else:
                            current_merge_op_message = pdf_path_or_msg or "图片合并为Word后，转换为PDF失败。"
                        if os.path.exists(temp_merged_docx_path): # Clean up intermediate merged DOCX
                            os.remove(temp_merged_docx_path)
                    else:
                        current_merge_op_message = f"imgToFile merge: Unexpected output format '{output_format}'"
                        if os.path.exists(temp_merged_docx_path): os.remove(temp_merged_docx_path) # cleanup
                
                elif main_tab == 'fileToPdf': # Merging for fileToPdf (various file types to a single PDF)
                    if not PYPDF2_AVAILABLE:
                        current_merge_op_message = "PDF合并库 (PyPDF2) 不可用，无法合并输出。"
                    else:
                        intermediate_pdfs_for_merging = []
                        all_individual_to_pdf_ok = True
                        conversion_map = {
                            'wordToPdf': convert_word_to_pdf,
                            'excelToPdf': convert_excel_to_pdf,
                            'pptToPdf': ppt_pdf_converter.convert_pptx_to_pdf, # Assuming this takes (source, target_pdf_path)
                            'txtToPdf': convert_txt_to_pdf
                        }
                        selected_conversion_func = conversion_map.get(sub_tab)

                        if not selected_conversion_func:
                            current_merge_op_message = f"未知的子类型 {sub_tab} 用于 fileToPdf 合并。"
                            all_individual_to_pdf_ok = False
                        else:
                            for item in valid_temp_files_for_processing: # These are _prePdf_ copies
                                temp_pdf_for_merge_name = f"{item['base_filename_no_ext']}_tempMerge_{request_id}.pdf"
                                temp_pdf_for_merge_path = os.path.join(user_converted_dir, temp_pdf_for_merge_name)
                                
                                ind_success, ind_path_or_msg, _ = selected_conversion_func(item['path'], temp_pdf_for_merge_path)
                                if ind_success and os.path.exists(temp_pdf_for_merge_path):
                                    intermediate_pdfs_for_merging.append(temp_pdf_for_merge_path)
                                else:
                                    current_merge_op_message = f"将 {item['original_name']} 转换为PDF以进行合并时失败: {ind_path_or_msg or '未知错误'}"
                                    all_individual_to_pdf_ok = False
                                    break
                        
                        if all_individual_to_pdf_ok and intermediate_pdfs_for_merging:
                            pdf_merger = PdfMerger()
                            for pdf_path in intermediate_pdfs_for_merging:
                                pdf_merger.append(pdf_path)
                            pdf_merger.write(final_merged_path) # final_merged_path has .pdf ext
                            pdf_merger.close()
                            current_merge_op_success = True
                            current_merge_op_message = "文件已合并并转换为PDF。"
                        elif all_individual_to_pdf_ok and not intermediate_pdfs_for_merging : # All reported success but no files
                             current_merge_op_message = "所有文件单独转换为PDF均报告成功，但未生成可合并的PDF文件。"
                        
                        # Cleanup intermediate PDFs created for merging
                        for temp_pdf in intermediate_pdfs_for_merging:
                            if os.path.exists(temp_pdf): os.remove(temp_pdf)

                elif main_tab == 'pdfToFile': # Merging for pdfToFile (PDFs to various formats)
                    # paths_of_temp_sources_for_merge contains paths to _preFinal_ PDF copies
                    if output_format == 'docx':
                        current_merge_op_success, current_merge_op_message = convert_and_merge_pdfs_to_docx(paths_of_temp_sources_for_merge, final_merged_path, request_id)
                    elif output_format == 'pptx':
                        # pdf_to_ppt_mode is available from earlier in the function
                        if pdf_to_ppt_mode == 'libreoffice':
                            if not PYPDF2_AVAILABLE:
                                current_merge_op_message = "PDF合并库 (PyPDF2) 不可用，无法使用LibreOffice模式合并PDF到PPTX。"
                            else:
                                temp_merged_pdf_for_lo_ppt_path = os.path.join(user_converted_dir, f"temp_lo_merged_pdf_{request_id}.pdf")
                                try:
                                    pdf_merger = PdfMerger()
                                    for pdf_path in paths_of_temp_sources_for_merge:
                                        pdf_merger.append(pdf_path)
                                    
                                    if not pdf_merger.inputs:
                                        logger.warning(f"No valid PDFs were appended to PdfMerger. Cannot create merged PDF. RequestID: {request_id}")
                                        current_merge_op_message = "没有有效的PDF文件可供合并。"
                                        current_merge_op_success = False # Ensure this path is marked as failure
                                    else:
                                        pdf_merger.write(temp_merged_pdf_for_lo_ppt_path)
                                        pdf_merger.close()
                                        logger.info(f"pdfToFile/PPT-LO: Merged source PDFs to {temp_merged_pdf_for_lo_ppt_path}. RequestID: {request_id}")

                                        if not os.path.exists(temp_merged_pdf_for_lo_ppt_path):
                                            logger.error(f"CRITICAL FAILURE: PyPDF2 claimed to write {temp_merged_pdf_for_lo_ppt_path} but it does NOT exist. RequestID: {request_id}")
                                            current_merge_op_message = "PDF合并失败：未能创建合并后的文件。"
                                            current_merge_op_success = False # Mark as failure
                                            # Do not proceed to call convert_pdf_to_ppt
                                        else:
                                            # File exists, proceed with LibreOffice conversion
                                            logger.info(f"Merged PDF {temp_merged_pdf_for_lo_ppt_path} confirmed to exist. Proceeding with LibreOffice. RequestID: {request_id}")
                                            lo_conv_success, lo_conv_actual_path, lo_conv_msg = convert_pdf_to_ppt(
                                                temp_merged_pdf_for_lo_ppt_path, 
                                                user_converted_dir, 
                                                mode='libreoffice', 
                                                desired_filename_base=merged_base_name_for_file
                                            )
                                            if lo_conv_success and lo_conv_actual_path and os.path.exists(lo_conv_actual_path):
                                                if lo_conv_actual_path != final_merged_path: # Ensure final name
                                                    if os.path.exists(final_merged_path): os.remove(final_merged_path)
                                                    os.rename(lo_conv_actual_path, final_merged_path)
                                                current_merge_op_success = True
                                                current_merge_op_message = lo_conv_msg or "PDF已合并并通过LibreOffice转换为PPTX。"
                                            else:
                                                current_merge_op_message = lo_conv_msg or "LibreOffice转换合并后的PDF为PPTX时失败。"
                                                current_merge_op_success = False # Mark as failure

                                except Exception as e_lo_ppt_merge:
                                    current_merge_op_message = f"PDF合并或LibreOffice转换预处理过程中出错: {str(e_lo_ppt_merge)}"
                                    logger.error(f"{current_merge_op_message}. RequestID: {request_id}", exc_info=True)
                                    current_merge_op_success = False # Mark as failure
                                finally:
                                    # Cleanup the merged PDF (temp_lo_merged_pdf_for_lo_ppt_path) only if it exists
                                    # This cleanup happens regardless of soffice success, as it's an intermediate for this specific path.
                                    if os.path.exists(temp_merged_pdf_for_lo_ppt_path):
                                        try:
                                            os.remove(temp_merged_pdf_for_lo_ppt_path)
                                            logger.info(f"Cleaned up temporary merged PDF for LO: {temp_merged_pdf_for_lo_ppt_path}. RequestID: {request_id}")
                                        except Exception as e_clean_merged_lo:
                                            logger.warning(f"Failed to clean up temporary merged PDF for LO {temp_merged_pdf_for_lo_ppt_path}: {e_clean_merged_lo}. RequestID: {request_id}")
                        
                        else: # Screenshot mode for PDF to PPT merge
                            current_merge_op_success, current_merge_op_message = convert_and_merge_pdfs_to_pptx(paths_of_temp_sources_for_merge, final_merged_path, request_id, ppt_creation_mode='screenshot')
                    elif output_format == 'txt':
                        current_merge_op_success, current_merge_op_message = convert_and_merge_pdfs_to_txt(paths_of_temp_sources_for_merge, final_merged_path, request_id)
                    elif output_format == 'xlsx':
                        current_merge_op_message = "不支持将多个PDF直接合并为一个Excel文件。请取消勾选合并选项。"
                        # current_merge_op_success remains False
                    else:
                        current_merge_op_message = f"pdfToFile合并: 未知的输出格式 '{output_format}'"

                else: # Should not be reached if main_tab is validated
                    current_merge_op_message = f"合并操作: 未知的主选项卡 '{main_tab}'"

                # Cleanup _prePdf_ or _preFinal_ temp files after merge attempt
                for f_info in valid_temp_files_for_processing:
                    if os.path.exists(f_info['path']): 
                        try: os.remove(f_info['path'])
                        except Exception as e_clean_pre: logger.warning(f"Failed to cleanup temp source {f_info['path']} after merge: {e_clean_pre}")
                
                # Add result for merge operation to processed_results
                if current_merge_op_success and os.path.exists(final_merged_path):
                    meta_file_path_merged = f"{final_merged_path}.meta"
                    with open(meta_file_path_merged, 'w', encoding='utf-8') as mf: mf.write(",".join(original_names_for_meta))
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_merged_filename).replace("\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    processed_results = [{
                        'original_name': ",".join(original_names_for_meta),
                        'converted_name': final_merged_filename, 
                        'download_url': download_url, 
                        'status': 'success',
                        'message': current_merge_op_message or "合并成功"
                    }]
                elif merge_output: # If merge was checked but failed
                    processed_results = [{
                        'original_name': "合并操作", 
                        'status': 'error', 
                        'message': current_merge_op_message or f'合并到 {output_format.upper()} 失败或不受支持。'
                    }]
            except Exception as e_merge_main:
                logger.error(f"Error during main merge operation block (RequestID: {request_id}): {e_merge_main}", exc_info=True)
                if merge_output: # Ensure an error is reported if merge was intended
                    processed_results = [{'original_name': "合并操作", 'status': 'error', 'message': f"合并文件时发生严重错误: {str(e_merge_main)}"}]

        else: # Not merge_output: Process individual files
            for file_info in valid_temp_files_for_processing:
                temp_source_for_individual_conversion = file_info['path'] # This is the _prePdf_ or _preFinal_ or _tempScriptOutput_ file
                original_input_name = file_info['original_name']
                base_filename_no_ext_for_indiv = file_info['base_filename_no_ext']

                random_chars_final_indv = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                final_output_base_indiv = f"{base_filename_no_ext_for_indiv}_{random_chars_final_indv}" 
                final_output_filename_indiv = f"{final_output_base_indiv}.{output_format}"
                final_output_path_indiv = os.path.join(user_converted_dir, final_output_filename_indiv)
                
                conversion_successful_individual = False
                actual_final_path_for_individual = final_output_path_indiv 
                err_msg_for_individual = None

                try:
                    logger.info(f"Converting individual file '{original_input_name}' to {output_format} (RequestID: {request_id}): {temp_source_for_individual_conversion} -> {final_output_path_indiv}")
                    
                    # Determine the correct conversion function based on main_tab, sub_tab, and output_format
                    if main_tab == 'imgToFile':
                        # temp_source_for_individual_conversion is already the DOCX from OCR script (e.g., ..._tempScriptOutput_XYZ.docx)
                        if output_format == 'docx':
                            shutil.move(temp_source_for_individual_conversion, final_output_path_indiv)
                            conversion_successful_individual = True
                        elif output_format == 'pdf':
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_word_to_pdf(temp_source_for_individual_conversion, final_output_path_indiv)
                        else:
                            err_msg_for_individual = f"imgToFile: 不支持的独立输出格式 '{output_format}'"

                    elif main_tab == 'fileToPdf':
                        # temp_source_for_individual_conversion is a _prePdf_ copy of the original file
                        conversion_map_file_to_pdf = {
                            'wordToPdf': convert_word_to_pdf,
                            'excelToPdf': convert_excel_to_pdf,
                            'pptToPdf': ppt_pdf_converter.convert_pptx_to_pdf,
                            'txtToPdf': convert_txt_to_pdf
                        }
                        selected_conv_func = conversion_map_file_to_pdf.get(sub_tab)
                        if selected_conv_func:
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = selected_conv_func(temp_source_for_individual_conversion, final_output_path_indiv)
                        else:
                            err_msg_for_individual = f"fileToPdf: 未知的子类型 '{sub_tab}' 用于独立转换。"

                    elif main_tab == 'pdfToFile':
                        # temp_source_for_individual_conversion is a _preFinal_ copy of the original PDF
                        if output_format == 'docx':
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_word(temp_source_for_individual_conversion, final_output_path_indiv)
                        elif output_format == 'pptx':
                            # Use pdf_to_ppt_mode retrieved earlier
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_ppt(temp_source_for_individual_conversion, final_output_path_indiv, mode=pdf_to_ppt_mode, desired_filename_base=final_output_base_indiv)
                        elif output_format == 'xlsx':
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_excel(temp_source_for_individual_conversion, final_output_path_indiv)
                        elif output_format == 'txt':
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_txt(temp_source_for_individual_conversion, final_output_path_indiv)
                        else:
                            err_msg_for_individual = f"pdfToFile: 不支持的独立输出格式 '{output_format}'"
                    else:
                        err_msg_for_individual = f"未知的主选项卡 '{main_tab}' 用于独立文件处理。"

                    # Common result handling for individual conversion
                    if conversion_successful_individual and os.path.exists(actual_final_path_for_individual):
                        logger.info(f"Successfully processed '{original_input_name}' to '{os.path.basename(actual_final_path_for_individual)}' (RequestID: {request_id})")
                        status_for_frontend = 'success'
                        message_for_frontend = err_msg_for_individual or '转换成功' # Some converters might put success msg in err_msg_for_individual
                        if err_msg_for_individual and "Conversion OK, but move to final path failed" in str(err_msg_for_individual):
                             status_for_frontend = 'success_fallback' # Or a more specific status
                             message_for_frontend = str(err_msg_for_individual) # Pass detailed error

                        relative_media_path_indiv = os.path.join(request.user.username, today_date_str, 'converted_files', os.path.basename(actual_final_path_for_individual)).replace("\\", "/")
                        download_url_indiv = f"{settings.MEDIA_URL}{relative_media_path_indiv}"
                        processed_results.append({
                            'original_name': original_input_name,
                            'converted_name': os.path.basename(actual_final_path_for_individual),
                            'download_url': download_url_indiv,
                            'status': status_for_frontend,
                            'message': message_for_frontend
                        })
                        meta_file_path_indiv = f"{actual_final_path_for_individual}.meta"
                        with open(meta_file_path_indiv, 'w', encoding='utf-8') as mf: mf.write(original_input_name)
                        
                        # Cleanup the temp source if it's different from final output and was a _prePpdf/_preFinal_ etc.
                        if temp_source_for_individual_conversion != actual_final_path_for_individual and \
                           os.path.exists(temp_source_for_individual_conversion) and \
                           any(temp_marker in os.path.basename(temp_source_for_individual_conversion) for temp_marker in [f"_prePdf_{request_id}", f"_preFinal_{request_id}", f"_tempScriptOutput_{request_id}"]):
                            try: 
                                os.remove(temp_source_for_individual_conversion)
                                logger.info(f"Cleaned up temp source {temp_source_for_individual_conversion} after individual conversion. RequestID: {request_id}")
                            except OSError as e_clean_ind_src: logger.warning(f"Failed to clean up temp source {temp_source_for_individual_conversion}: {e_clean_ind_src}")

                    else: # Individual conversion failed
                        logger.error(f"Conversion failed for '{original_input_name}' to {output_format}. Error: {err_msg_for_individual} (RequestID: {request_id})")
                        processed_results.append({
                            'original_name': original_input_name, 
                            'status': 'error', 
                            'message': str(err_msg_for_individual or '转换失败，未返回具体错误信息。')
                        })
                except Exception as e_ind_main:
                    logger.error(f"Error converting individual file '{original_input_name}' (RequestID: {request_id}): {e_ind_main}", exc_info=True)
                    processed_results.append({'original_name': original_input_name, 'status': 'error', 'message': f'处理单个文件转换时发生意外错误: {str(e_ind_main)}'})
    
    elif not uploaded_files_info_from_frontend : # No files were uploaded at all
        processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件，无法开始转换。'})
    # If temp_files_for_final_processing is empty but uploaded_files_info_from_frontend is not,
    # it means all initial file preparations failed and errors are already in processed_results.
    
    logger.info(f"Final processed results to be sent to client (RequestID: {request_id}): {processed_results}")
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
            for filename in os.listdir(converted_files_dir):
                file_path = os.path.join(converted_files_dir, filename)
                try:
                    os.remove(file_path)
                    logger.info(f"User {user.username} deleted file during mass delete: {file_path}")
                    deleted_something = True
                except OSError as e:
                    logger.warning(f"Error deleting file {file_path} during mass delete for user {user.username}: {e}")
                    messages.warning(request, f"删除文件 '{filename}' 时出错，但会继续尝试。")
            # Attempt to remove the converted_files directory if empty
            if not os.listdir(converted_files_dir):
                os.rmdir(converted_files_dir)
                logger.info(f"Removed empty directory: {converted_files_dir}")

        # Delete files in uploads directory
        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                file_path = os.path.join(uploads_dir, filename)
                try:
                    os.remove(file_path)
                    logger.info(f"User {user.username} deleted uploaded file during mass delete: {file_path}")
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
