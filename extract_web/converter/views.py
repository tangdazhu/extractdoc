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
def process_images_view(request):
    today_date_str = datetime.now().strftime("%Y%m%d")
    user_base_dir = os.path.join(settings.BASE_DIR, 'his_pic', request.user.username, today_date_str)
    user_upload_dir = os.path.join(user_base_dir, 'uploads')
    user_converted_dir = os.path.join(user_base_dir, 'converted_files')
    
    os.makedirs(user_upload_dir, exist_ok=True)
    os.makedirs(user_converted_dir, exist_ok=True)
    logger.info(f"Ensured daily directories exist: Uploads='{user_upload_dir}', Converted='{user_converted_dir}'")

    merge_output = request.POST.get('merge_output', 'false').lower() == 'true'
    output_format_param = request.POST.get('output_format', '') # Original format from frontend
    main_tab = request.POST.get('main_tab', 'imgToFile')
    sub_tab = request.POST.get('sub_tab', '')

    if main_tab == 'fileToPdf':
        output_format = 'pdf'
    elif main_tab == 'imgToFile':
        output_format = output_format_param if output_format_param else 'docx'
    elif main_tab == 'pdfToFile':
        # Determine output format based on sub_tab for pdfToFile
        if sub_tab == 'pdfToWord':
            output_format = 'docx'
        elif sub_tab == 'pdfToExcel':
            output_format = 'xlsx'
        elif sub_tab == 'pdfToPpt':
            output_format = 'pptx'
        elif sub_tab == 'pdfToTxt':
            output_format = 'txt'
        else:
            # Fallback if sub_tab is unknown
            output_format = output_format_param  # Use param as a fallback
            logger.warning(f"pdfToFile: Unknown or missing sub_tab ('{sub_tab}'), or sub_tab implies an output format not directly handled. Falling back to output_format_param: '{output_format_param}'. Ensure frontend sends correct sub_tab and output_format_param if sub_tab is unusual.")
            if not output_format: # If param is also empty or not helpful
                 logger.error(f"pdfToFile: Critical - sub_tab '{sub_tab}' led to empty output_format even after fallback. Defaulting to 'docx' to prevent None. This indicates a potential configuration or request issue.")
                 output_format = 'docx' # A failsafe default, though likely an error state.
    else: 
        # Fallback for any other main_tab (e.g., if new main_tabs are added without specific logic here)
        output_format = output_format_param
        logger.warning(f"Unhandled main_tab '{main_tab}' for output_format determination, using output_format_param: '{output_format_param}' as fallback.")
        if not output_format: # If param is also empty
            logger.error(f"Fallback: Critical - main_tab '{main_tab}' led to empty output_format. Defaulting to 'docx'.")
            output_format = 'docx' # General failsafe

    logger.debug(f"Process Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, RequestedFormat='{output_format_param}', EffectiveOutputFormat='{output_format}', MainTab={main_tab}, SubTab={sub_tab}")

    if main_tab == 'fileToPdf' and output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW and sub_tab == 'wordToPdf':
        logger.error("PDF output requested for Word file, but docx2pdf is not available.")
        return JsonResponse({'results': [{'original_name': 'Conversion', 'status': 'error', 'message': 'Word转PDF的转换库(docx2pdf)不可用。'}], 'merge_output': merge_output})

    uploaded_files_info_from_frontend = []
    for uploaded_file in request.FILES.getlist('images'): 
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
    temp_files_for_final_processing = [] 

    if main_tab == 'imgToFile':
        img_processed_results, img_temp_files_list_of_dicts = process_images_to_files(uploaded_files_info_from_frontend, user_converted_dir)
        processed_results.extend(img_processed_results) 
        for item_dict in img_temp_files_list_of_dicts: 
             temp_files_for_final_processing.append(item_dict)

    elif main_tab == 'fileToPdf':
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                source_file_path = up_file_info['path']
                base_name_no_ext = os.path.splitext(original_name)[0]
                
                temp_file_ext = os.path.splitext(original_name)[1]
                temp_file_in_converted_dir_filename = f"{base_name_no_ext}_prePdf{temp_file_ext}"
                temp_file_in_converted_dir_path = os.path.join(user_converted_dir, temp_file_in_converted_dir_filename)

                try:
                    valid_type = False
                    if sub_tab == 'wordToPdf' and original_name.lower().endswith(('.doc', '.docx')):
                        valid_type = True
                    elif sub_tab == 'excelToPdf' and original_name.lower().endswith(('.xls', '.xlsx')):
                        valid_type = True
                        if os.path.exists(temp_file_in_converted_dir_path):
                            try: os.remove(temp_file_in_converted_dir_path)
                            except OSError as e_remove: logger.error(f"Failed to remove existing target for Excel: {e_remove}", exc_info=True)
                    elif sub_tab == 'pptToPdf' and original_name.lower().endswith(('.ppt', '.pptx')):
                        valid_type = True
                    elif sub_tab == 'txtToPdf' and original_name.lower().endswith('.txt'):
                        valid_type = True
                    
                    if not valid_type:
                        error_message = f"文件类型不匹配 ({sub_tab}): {original_name}"
                        logger.warning(error_message)
                        processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                        continue

                    shutil.copy(source_file_path, temp_file_in_converted_dir_path)
                    logger.info(f"Copied {original_name} to {temp_file_in_converted_dir_path} for PDF conversion process.")
                    temp_files_for_final_processing.append({
                        'path': temp_file_in_converted_dir_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext
                    })

                except PermissionError as pe:
                    logger.error(f"Permission denied during preparation of {original_name} to {temp_file_in_converted_dir_path}: {pe}", exc_info=True)
                    processed_results.append({'original_name': original_name, 'status': 'error','message': f'准备文件时权限不足: {str(pe)}'})
                except Exception as e:
                    logger.exception(f"Error preparing {original_name} for conversion (sub_tab: {sub_tab}): {e}")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': f'准备文件时出错: {str(e)}'})
            else: 
                processed_results.append(up_file_info)
    
    elif main_tab == 'pdfToFile': # New logic for pdfToFile
        for up_file_info in uploaded_files_info_from_frontend:
            if up_file_info['status'] == 'uploaded':
                original_name = up_file_info['name']
                source_file_path = up_file_info['path']
                base_name_no_ext = os.path.splitext(original_name)[0]
                
                # Determine target extension based on sub_tab
                target_ext = ''
                if sub_tab == 'pdfToWord': target_ext = '.docx'
                elif sub_tab == 'pdfToExcel': target_ext = '.xlsx' # Assuming Excel output is xlsx
                elif sub_tab == 'pdfToPpt': target_ext = '.pptx'
                elif sub_tab == 'pdfToTxt': target_ext = '.txt'
                else:
                    error_message = f"不支持的PDF转换类型: {sub_tab}"
                    logger.warning(error_message)
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                    continue

                # For pdfToFile, the 'output_format' from the request is the target format (e.g., 'docx', 'xlsx')
                # We use 'output_format' variable which should be set correctly based on output_format_param
                # If output_format is empty (which it might be if not 'imgToFile' or 'fileToPdf' explicitly sets it to 'pdf'),
                # we should derive it from sub_tab for clarity or rely on output_format_param.
                # Let's ensure output_format reflects the target format.
                if not output_format and target_ext: # If output_format wasn't set by general logic
                    current_output_format = target_ext.lstrip('.')
                    if output_format_param and output_format_param != current_output_format:
                         logger.warning(f"Mismatch between sub_tab inferred format '{current_output_format}' and output_format_param '{output_format_param}'. Using sub_tab.")
                    # The global 'output_format' variable is used later, so ensure it's what we expect for this path.
                    # This might need careful review if 'output_format' is expected to be something else globally.
                    # For now, let's assume output_format_param correctly carries 'docx', 'xlsx', etc.
                    # And the 'output_format' variable at the top is correctly assigned from output_format_param

                temp_file_in_converted_dir_filename = f"{base_name_no_ext}_preFinal{os.path.splitext(original_name)[1]}" # Keep original ext for temp
                temp_file_in_converted_dir_path = os.path.join(user_converted_dir, temp_file_in_converted_dir_filename)

                try:
                    valid_type = False
                    if original_name.lower().endswith('.pdf'): # All inputs must be PDF for this tab
                        if sub_tab in ['pdfToWord', 'pdfToExcel', 'pdfToPpt', 'pdfToTxt']:
                             valid_type = True
                    
                    if not valid_type:
                        error_message = f"文件类型不匹配 ({sub_tab}): {original_name} (应为PDF)"
                        logger.warning(error_message)
                        processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                        continue

                    shutil.copy(source_file_path, temp_file_in_converted_dir_path)
                    logger.info(f"Copied {original_name} to {temp_file_in_converted_dir_path} for {sub_tab} conversion process.")
                    temp_files_for_final_processing.append({
                        'path': temp_file_in_converted_dir_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext
                    })

                except PermissionError as pe:
                    logger.error(f"Permission denied during preparation of {original_name} to {temp_file_in_converted_dir_path}: {pe}", exc_info=True)
                    processed_results.append({'original_name': original_name, 'status': 'error','message': f'准备文件时权限不足: {str(pe)}'})
                except Exception as e:
                    logger.exception(f"Error preparing {original_name} for conversion (main_tab: {main_tab}, sub_tab: {sub_tab}): {e}")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': f'准备文件时出错: {str(e)}'})
            else: 
                processed_results.append(up_file_info)

    else: 
        if main_tab not in ['imgToFile', 'fileToPdf', 'pdfToFile'] and not any(r['status'] == 'error' for r in processed_results): 
            logger.warning(f"Unhandled main_tab '{main_tab}' or no files processed. Cannot proceed.")
            if not uploaded_files_info_from_frontend:
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件。'})
            elif not temp_files_for_final_processing and any(info['status'] == 'uploaded' for info in uploaded_files_info_from_frontend):
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '上传的文件无法按当前选择的模式处理。'})
            elif not temp_files_for_final_processing : 
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有文件可供处理。'})


    if temp_files_for_final_processing: 
        if merge_output:
            logger.debug(f"Attempting to merge {len(temp_files_for_final_processing)} files. MainTab: {main_tab}, SubTab: {sub_tab}, OutputFormat: {output_format}.")
            random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            merged_base_filename = f"{request.user.username}_{today_date_str}_{random_chars}"
            
            final_merged_filename_ext = output_format 
            final_merged_filename = f"{merged_base_filename}.{final_merged_filename_ext}"
            final_merged_path = os.path.join(user_converted_dir, final_merged_filename)

            # temp_files_for_final_processing: paths to copies of uploaded files in user_converted_dir (e.g., ..._preFinal.pdf, ..._prePdf.xlsx)
            files_to_cleanup_after_merge = [info['path'] for info in temp_files_for_final_processing]
            temp_individual_outputs_for_merging = [] # For storing paths of files converted for merging (e.g. PDF->DOCX items, or PPT->PDF items)
            
            try:
                merge_successful = False

                if main_tab == 'fileToPdf' and sub_tab in ['excelToPdf', 'pptToPdf', 'txtToPdf']:
                    if not PYPDF2_AVAILABLE:
                        raise Exception(f"无法合并到PDF (sub_tab: {sub_tab})：缺少必需的PDF处理库(PyPDF2)。")

                    conversion_func = None
                    if sub_tab == 'excelToPdf': conversion_func = convert_excel_to_pdf
                    elif sub_tab == 'pptToPdf': conversion_func = ppt_pdf_converter.convert_pptx_to_pdf
                    elif sub_tab == 'txtToPdf': conversion_func = convert_txt_to_pdf

                    all_individual_conversions_successful = True
                    for item_info in temp_files_for_final_processing: # item_info['path'] are original .xlsx, .pptx, .txt copies
                        item_path = item_info['path']
                        item_original_name = item_info['original_name']
                        # Output of individual conversion here is always PDF, for later PDF merging
                        temp_pdf_name_for_merge = f"{os.path.splitext(os.path.basename(item_path))[0]}_merged_temp.pdf"
                        temp_pdf_path_for_merge = os.path.join(user_converted_dir, temp_pdf_name_for_merge)
                        
                        logger.info(f"Converting individual {sub_tab} file '{item_original_name}' to PDF for merging: {item_path} -> {temp_pdf_path_for_merge}")
                        success, actual_pdf_output, err_msg = conversion_func(item_path, temp_pdf_path_for_merge)
                        
                        if success and actual_pdf_output and os.path.exists(actual_pdf_output):
                            temp_individual_outputs_for_merging.append(actual_pdf_output) 
                        else:
                            all_individual_conversions_successful = False
                            processed_results.append({'original_name': item_original_name, 'status': 'error', 'message': f"合并前转换为PDF失败 ({item_original_name}): {err_msg or '未知错误'}"})
                            break 
                    
                    if all_individual_conversions_successful and temp_individual_outputs_for_merging:
                        pdf_merger = PdfMerger()
                        for pdf_path in temp_individual_outputs_for_merging: pdf_merger.append(pdf_path)
                        pdf_merger.write(final_merged_path) # final_merged_path target extension is .pdf (from output_format)
                        pdf_merger.close()
                        logger.info(f"Successfully merged PDFs from {sub_tab} into: {final_merged_path}")
                        merge_successful = True
                    elif not temp_individual_outputs_for_merging and all_individual_conversions_successful:
                        if not any(r['status'] == 'error' for r in processed_results):
                            processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': '没有PDF文件可供合并，即使单个转换报告成功。'})

                elif main_tab == 'pdfToFile':
                    conversion_func_pdf_to_target = None
                    target_ext_for_individual_conversion = ''
                    perform_pdf_to_target_conversion_step = True

                    if output_format == 'docx':
                        conversion_func_pdf_to_target = convert_pdf_to_word
                        target_ext_for_individual_conversion = '.docx'
                    elif output_format == 'txt':
                        conversion_func_pdf_to_target = convert_pdf_to_txt
                        target_ext_for_individual_conversion = '.txt'
                    else: # pdfToPpt, pdfToExcel - merging not supported for single output file
                        logger.warning(f"Merging PDFs to a single {output_format.upper()} file is not supported. Each PDF will be converted individually if 'merge output' was checked, or an error will be shown if no individual processing logic follows.")
                        processed_results.append({
                            'original_name': "Merged Document", 
                            'status': 'error', 
                            'message': f"合并多个PDF到单个 {output_format.upper()} 文件暂不支持。请取消勾选“合并为一个文件”以单独转换每个PDF，或选择DOCX/TXT作为合并输出格式。"
                        })
                        merge_successful = False 
                        perform_pdf_to_target_conversion_step = False # Skip the conversion-then-merge logic

                    if perform_pdf_to_target_conversion_step:
                        all_individual_pdf_to_target_conversions_ok = True
                        for item_info in temp_files_for_final_processing: # item_info['path'] are .pdf file copies
                            item_pdf_path = item_info['path'] 
                            item_original_pdf_name = item_info['original_name']
                            temp_indv_target_filename = f"{os.path.splitext(os.path.basename(item_pdf_path))[0]}_indv_conv{target_ext_for_individual_conversion}"
                            temp_indv_target_path = os.path.join(user_converted_dir, temp_indv_target_filename)
                            
                            logger.info(f"Converting PDF '{item_original_pdf_name}' to {output_format.upper()} for potential merging: {item_pdf_path} -> {temp_indv_target_path}")
                            success, actual_converted_path, err_msg = conversion_func_pdf_to_target(item_pdf_path, temp_indv_target_path)
                            
                            if success and actual_converted_path and os.path.exists(actual_converted_path):
                                temp_individual_outputs_for_merging.append(actual_converted_path)
                            else:
                                all_individual_pdf_to_target_conversions_ok = False
                                processed_results.append({'original_name': item_original_pdf_name, 'status': 'error', 'message': f"合并前PDF转 {output_format.upper()} 失败 ({item_original_pdf_name}): {err_msg or '未知错误'}"})
                                break
                        
                        if all_individual_pdf_to_target_conversions_ok and temp_individual_outputs_for_merging:
                            if output_format == 'docx':
                                master_doc = Document(temp_individual_outputs_for_merging[0])
                                for doc_path in temp_individual_outputs_for_merging[1:]:
                                    sub_doc = Document(doc_path)
                                    master_doc.add_page_break()
                                    append_document(sub_doc, master_doc)
                                master_doc.save(final_merged_path) # final_merged_path target ext is .docx
                                logger.info(f"Successfully merged DOCX from PDFs into: {final_merged_path}")
                                merge_successful = True
                            elif output_format == 'txt':
                                all_text_content = []
                                for txt_path in temp_individual_outputs_for_merging:
                                    with open(txt_path, 'r', encoding='utf-8') as f_txt:
                                        all_text_content.append(f_txt.read())
                                with open(final_merged_path, 'w', encoding='utf-8') as merged_f: # final_merged_path target ext is .txt
                                    merged_f.write("\n\n--- New File ---\n\n".join(all_text_content))
                                logger.info(f"Successfully merged TXT from PDFs into: {final_merged_path}")
                                merge_successful = True
                        elif not temp_individual_outputs_for_merging and all_individual_pdf_to_target_conversions_ok:
                            # This means all conversions were reported as success, but no files were produced to merge.
                            if not any(r['status'] == 'error' for r in processed_results):
                                processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': f'没有 {output_format.upper()} 文件可供合并 (来自PDF转换)。'})
                
                elif main_tab == 'imgToFile' or (main_tab == 'fileToPdf' and sub_tab == 'wordToPdf'):
                    # This path assumes temp_files_for_final_processing contains .docx or .doc files
                    # (either from imgToFile conversion if output_format is docx, or original Word uploads for wordToPdf)
                    merged_docx_intermediate_path = os.path.join(user_converted_dir, f"{merged_base_filename}_intermediate.docx")
                    first_doc_path = temp_files_for_final_processing[0]['path']

                    if not first_doc_path.lower().endswith(('.doc', '.docx')):
                        logger.error(f"Merge logic error for {main_tab}/{sub_tab}: Expected DOCX-compatible file for direct merging, but got {first_doc_path}")
                        if not any(r['status'] == 'error' and r.get('original_name') == "Merged Document" for r in processed_results):
                            processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': f'内部合并错误：期望DOCX兼容文件进行合并，但实际文件类型不匹配 ({os.path.basename(first_doc_path)}).'})
                        merge_successful = False 
                    else:
                        master_doc = Document(first_doc_path)
                        if len(temp_files_for_final_processing) > 1:
                            for doc_info in temp_files_for_final_processing[1:]:
                                sub_doc = Document(doc_info['path'])
                                master_doc.add_page_break()
                                append_document(sub_doc, master_doc)
                        master_doc.save(merged_docx_intermediate_path)
                        logger.info(f"Merged DOCX (intermediate for {main_tab}/{sub_tab}) saved: {merged_docx_intermediate_path}")
                        # This intermediate DOCX is one of the files to cleanup
                        if merged_docx_intermediate_path not in files_to_cleanup_after_merge:
                             files_to_cleanup_after_merge.append(merged_docx_intermediate_path)
                        
                        if output_format == 'pdf': # This case is for wordToPdf merge to PDF
                            if DOCX2PDF_AVAILABLE_IN_VIEW:
                                convert_docx_to_pdf(merged_docx_intermediate_path, final_merged_path)
                                logger.info(f"Converted merged DOCX to PDF: {final_merged_path}")
                                # The intermediate docx can be removed if PDF conversion was successful
                                # os.remove(merged_docx_intermediate_path) # Handled by cleanup list
                                merge_successful = True
                            else:
                                final_merged_filename = f"{merged_base_filename}.docx" 
                                final_merged_path = merged_docx_intermediate_path # Serve the intermediate DOCX
                                logger.warning("DOCX to PDF failed for merged file (docx2pdf unavailable), serving DOCX.")
                                if not any(pr['original_name'] == "Merged Document (DOCX Fallback)" for pr in processed_results):
                                    processed_results.append({'original_name': "Merged Document (DOCX Fallback)", 'status': 'error', 'message': 'DOCX转PDF库不可用，已合并为DOCX。请检查文件。', 'converted_name': final_merged_filename, 'download_url': None })
                                merge_successful = True # "Successful" as a DOCX fallback
                        elif output_format == 'docx': # This case is for imgToFile merge to DOCX
                            if merged_docx_intermediate_path != final_merged_path: 
                                shutil.move(merged_docx_intermediate_path, final_merged_path)
                                # If moved, merged_docx_intermediate_path no longer exists for cleanup, final_merged_path is the one.
                                if merged_docx_intermediate_path in files_to_cleanup_after_merge:
                                     files_to_cleanup_after_merge.remove(merged_docx_intermediate_path)
                            logger.info(f"Final merged file is DOCX: {final_merged_path}")
                            merge_successful = True
                        else: # Should ideally not happen if output_format logic at the start is correct
                            logger.error(f"Unexpected output_format '{output_format}' for main_tab {main_tab}/{sub_tab} in DOCX-direct-merge path.")
                            merge_successful = False
                
                # --- Common post-merge attempt processing --- 
                if merge_successful and os.path.exists(final_merged_path):
                    meta_file_path_merged = f"{final_merged_path}.meta"
                    merged_original_names_list = [info['original_name'] for info in temp_files_for_final_processing]
                    with open(meta_file_path_merged, 'w', encoding='utf-8') as mf: mf.write(",".join(merged_original_names_list))
                    
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', os.path.basename(final_merged_path)).replace("\\\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    
                    fallback_entry = next((r for r in processed_results if r.get('original_name') == "Merged Document (DOCX Fallback)"), None)
                    if fallback_entry:
                        fallback_entry['download_url'] = download_url 
                        fallback_entry['status'] = 'success_fallback' 
                    else:
                        # If merge was successful and no fallback message, this is the primary success result.
                        # Remove any prior general "Merged Document" error if one was added before specific logic.
                        current_processed_results = [r for r in processed_results if not (r.get('original_name') == "Merged Document" and r.get('status') == 'error')]
                        processed_results = current_processed_results + [{'original_name': ",".join(merged_original_names_list), 'converted_name': os.path.basename(final_merged_path), 'download_url': download_url, 'status': 'success'}]
                
                elif merge_output and not merge_successful and not any(r.get('original_name') == "Merged Document" and r.get('status') == 'error' for r in processed_results):
                     # This is a catch-all if merge_output was true, no merge happened for supported types (or was unsupported),
                     # and no specific error for "Merged Document" was added by the logic paths above.
                     processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': '所选的合并操作不受支持或未能完成。'})

            except Exception as e_merge:
                logger.error(f"Error during merge operation (MainTab: {main_tab}, SubTab: {sub_tab}, OutputFormat: {output_format}): {e_merge}", exc_info=True)
                if not any(r.get('original_name') == "Merged Document" and r.get('status') == 'error' for r in processed_results):
                    processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': f"合并文件时发生严重错误: {str(e_merge)}"})
            finally:
                # Add all individually converted intermediate files to the main cleanup list
                for temp_f in temp_individual_outputs_for_merging:
                    if temp_f not in files_to_cleanup_after_merge:
                        files_to_cleanup_after_merge.append(temp_f)
                
                # Cleanup all accumulated files
                unique_files_to_cleanup = list(set(files_to_cleanup_after_merge)) # Ensure unique paths
                for f_path in unique_files_to_cleanup:
                    try: 
                        if os.path.exists(f_path):
                            os.remove(f_path)
                            logger.debug(f"Cleaned up temp file: {f_path}")
                    except OSError as e_clean:
                        logger.warning(f"Failed to clean up temp file {f_path}: {e_clean}")

        else: # Not merge_output: Process individual files
            for file_info in temp_files_for_final_processing:
                temp_source_for_individual_conversion = file_info['path'] 
                original_input_name = file_info['original_name']
                base_filename_no_ext = file_info['base_filename_no_ext']

                final_output_filename = f"{base_filename_no_ext}.{output_format}"
                final_output_path = os.path.join(user_converted_dir, final_output_filename)
                conversion_successful_individual = False
                actual_final_path_individual = final_output_path # Can be overridden by converters
                
                try:
                    logger.info(f"Converting individual file '{original_input_name}' to {output_format}: {temp_source_for_individual_conversion} -> {final_output_path}")
                    
                    if output_format == 'pdf':
                        success_ind = False
                        err_msg_ind = "未知转换错误"
                        current_actual_path = final_output_path # Store current target
                        
                        if main_tab == 'imgToFile' or (main_tab == 'fileToPdf' and sub_tab == 'wordToPdf'): 
                            if DOCX2PDF_AVAILABLE_IN_VIEW:
                                convert_docx_to_pdf(temp_source_for_individual_conversion, current_actual_path)
                                success_ind = True
                                actual_final_path_individual = current_actual_path
                            else: err_msg_ind = "DOCX转PDF库(docx2pdf)不可用。"
                        elif main_tab == 'fileToPdf' and sub_tab == 'excelToPdf':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_excel_to_pdf(temp_source_for_individual_conversion, current_actual_path)
                        elif main_tab == 'fileToPdf' and sub_tab == 'pptToPdf':
                            success_ind, actual_final_path_individual, err_msg_ind = ppt_pdf_converter.convert_pptx_to_pdf(temp_source_for_individual_conversion, current_actual_path)
                        elif main_tab == 'fileToPdf' and sub_tab == 'txtToPdf':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_txt_to_pdf(temp_source_for_individual_conversion, current_actual_path)
                        else:
                             err_msg_ind = f"不支持的直接转PDF类型: {main_tab}/{sub_tab}"
                        
                        if not success_ind: raise Exception(err_msg_ind)
                        # Update final_output_path and filename if converter saved to a different name
                        if actual_final_path_individual != final_output_path :
                             final_output_path = actual_final_path_individual
                             final_output_filename = os.path.basename(final_output_path)


                    elif output_format == 'docx': 
                        if main_tab == 'pdfToFile' and sub_tab == 'pdfToWord':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_pdf_to_word(temp_source_for_individual_conversion, final_output_path)
                            if not success_ind: raise Exception(err_msg_ind)
                            if actual_final_path_individual != final_output_path:
                                final_output_path = actual_final_path_individual
                                final_output_filename = os.path.basename(final_output_path)
                        elif temp_source_for_individual_conversion != final_output_path : # Default case for other docx (e.g. from imgToFile)
                            shutil.move(temp_source_for_individual_conversion, final_output_path)
                    
                    elif output_format == 'xlsx': # Assuming pdfToExcel
                        if main_tab == 'pdfToFile' and sub_tab == 'pdfToExcel':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_pdf_to_excel(temp_source_for_individual_conversion, final_output_path)
                            if not success_ind: raise Exception(err_msg_ind)
                            if actual_final_path_individual != final_output_path:
                                final_output_path = actual_final_path_individual
                                final_output_filename = os.path.basename(final_output_path)
                        else:
                            raise Exception(f"Unsupported direct conversion to XLSX for {main_tab}/{sub_tab}")

                    elif output_format == 'pptx': # Assuming pdfToPpt
                        if main_tab == 'pdfToFile' and sub_tab == 'pdfToPpt':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_pdf_to_ppt(temp_source_for_individual_conversion, final_output_path)
                            if not success_ind: raise Exception(err_msg_ind)
                            if actual_final_path_individual != final_output_path:
                                final_output_path = actual_final_path_individual
                                final_output_filename = os.path.basename(final_output_path)
                        else:
                            raise Exception(f"Unsupported direct conversion to PPTX for {main_tab}/{sub_tab}")

                    elif output_format == 'txt': # Assuming pdfToTxt
                        if main_tab == 'pdfToFile' and sub_tab == 'pdfToTxt':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_pdf_to_txt(temp_source_for_individual_conversion, final_output_path)
                            if not success_ind: raise Exception(err_msg_ind)
                            if actual_final_path_individual != final_output_path:
                                final_output_path = actual_final_path_individual
                                final_output_filename = os.path.basename(final_output_path)
                        else: # This case should also handle txt output from imgToFile if that's ever a target
                            # For now, if not pdfToFile/pdfToTxt, it's an issue.
                            raise Exception(f"Unsupported direct conversion to TXT for {main_tab}/{sub_tab}")

                    else: 
                        raise Exception(f"不支持的单独输出格式 '{output_format}' for {original_input_name}")

                    logger.info(f"Successfully processed '{original_input_name}' to '{final_output_filename}'")
                    conversion_successful_individual = True
                    if temp_source_for_individual_conversion != final_output_path :
                        try: os.remove(temp_source_for_individual_conversion); logger.debug(f"Removed temp source after individual conversion: {temp_source_for_individual_conversion}")
                        except OSError: pass
                
                except Exception as e_ind:
                    logger.error(f"Error converting individual file '{original_input_name}' to {output_format}: {e_ind}", exc_info=True)
                    file_type_for_error = sub_tab if main_tab == 'fileToPdf' else '图片' # Simplify
                    if main_tab == 'pdfToFile': # More specific error for pdfToFile
                        file_type_for_error = f"PDF ({sub_tab.replace('pdfTo', '')})"

                    message = f"{file_type_for_error}文件 {original_input_name} 转 {output_format.upper()} 失败: {str(e_ind)}"
                    
                    current_final_output_path_for_fallback = None
                    current_final_output_filename_for_fallback = original_input_name # Default to original

                    if os.path.exists(temp_source_for_individual_conversion):
                        current_final_output_path_for_fallback = temp_source_for_individual_conversion
                        current_final_output_filename_for_fallback = os.path.basename(temp_source_for_individual_conversion)
                        message += f" 保留预处理文件 ({current_final_output_filename_for_fallback})。"
                        conversion_successful_individual = True 
                        logger.warning(f"Fallback: serving {current_final_output_filename_for_fallback} for failed conversion of {original_input_name}")
                    
                    processed_results.append({
                        'original_name': original_input_name,
                        'converted_name': current_final_output_filename_for_fallback,
                        'download_url': None, 
                        'status': 'conversion_error_fallback' if current_final_output_path_for_fallback and os.path.exists(current_final_output_path_for_fallback) else 'conversion_error',
                        'message': message
                    })
                
                if conversion_successful_individual and final_output_path and os.path.exists(final_output_path):
                    meta_file_path_individual = f"{final_output_path}.meta"
                    with open(meta_file_path_individual, 'w', encoding='utf-8') as mf: mf.write(original_input_name)
                    
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_output_filename).replace("\\\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    
                    existing_entry = next((r for r in processed_results if r['original_name'] == original_input_name), None)
                    if existing_entry and existing_entry['status'] == 'conversion_error_fallback':
                        existing_entry['download_url'] = download_url
                    elif not existing_entry:
                         processed_results.append({
                            'original_name': original_input_name,
                            'converted_name': final_output_filename,
                            'download_url': download_url,
                            'status': 'success'
                        })
                elif not any(r['original_name'] == original_input_name for r in processed_results): 
                    processed_results.append({
                        'original_name': original_input_name, 'status': 'conversion_error',
                        'message': f'处理文件 {original_input_name} 后，最终文件丢失。'
                    })
    elif not temp_files_for_final_processing and not processed_results: 
        logger.warning("No files were available for Stage 2 processing, and no prior errors captured.")
        processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有文件可供处理或所有文件准备失败。'})

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
