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

    if main_tab == 'fileToPdf':
        output_format = 'pdf'
    elif main_tab == 'imgToFile':
        output_format = output_format_param if output_format_param else 'docx'
    elif main_tab == 'pdfToFile':
        if sub_tab == 'pdfToWord': output_format = 'docx'
        elif sub_tab == 'pdfToExcel': output_format = 'xlsx'
        elif sub_tab == 'pdfToPpt': output_format = 'pptx'
        elif sub_tab == 'pdfToTxt': output_format = 'txt'
        else:
            output_format = output_format_param
            logger.warning(f"pdfToFile: Unknown sub_tab ('{sub_tab}'), fallback to param: '{output_format_param}', RequestID: {request_id}")
            if not output_format: output_format = 'docx'; logger.error(f"pdfToFile: Critical fallback to docx for unknown sub_tab, RequestID: {request_id}")
    else: 
        output_format = output_format_param
        logger.warning(f"Unhandled main_tab '{main_tab}', fallback to param: '{output_format_param}', RequestID: {request_id}")
        if not output_format: output_format = 'docx'; logger.error(f"Fallback: Critical fallback to docx for unhandled main_tab, RequestID: {request_id}")

    logger.debug(f"Process Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, RequestedFormat='{output_format_param}', EffectiveOutputFormat='{output_format}', MainTab={main_tab}, SubTab={sub_tab}, RequestID: {request_id}")

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
                target_ext = ''
                if sub_tab == 'pdfToWord': target_ext = '.docx'
                elif sub_tab == 'pdfToExcel': target_ext = '.xlsx'
                elif sub_tab == 'pdfToPpt': target_ext = '.pptx'
                elif sub_tab == 'pdfToTxt': target_ext = '.txt'
                else:
                    error_message = f"不支持的PDF转换类型: {sub_tab}"
                    logger.warning(f"{error_message} (RequestID: {request_id})")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                    continue

                temp_file_in_converted_dir_filename = f"{base_name_no_ext}_preFinal_{request_id}{os.path.splitext(original_name)[1]}"
                temp_file_in_converted_dir_path = os.path.join(user_converted_dir, temp_file_in_converted_dir_filename)
                try:
                    valid_type = False
                    if original_name.lower().endswith('.pdf') and sub_tab in ['pdfToWord', 'pdfToExcel', 'pdfToPpt', 'pdfToTxt']:
                        valid_type = True
                    if not valid_type:
                        error_message = f"文件类型不匹配 ({sub_tab}): {original_name} (应为PDF)"
                        logger.warning(f"{error_message} (RequestID: {request_id})")
                        processed_results.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                        continue
                    shutil.copy(source_file_path, temp_file_in_converted_dir_path)
                    logger.info(f"Copied {original_name} to {temp_file_in_converted_dir_path} for {sub_tab} (RequestID: {request_id}).")
                    temp_files_for_final_processing.append({
                        'path': temp_file_in_converted_dir_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext
                    })
                except PermissionError as pe:
                    logger.error(f"Permission denied for {original_name} to {temp_file_in_converted_dir_path} (RequestID: {request_id}): {pe}", exc_info=True)
                    processed_results.append({'original_name': original_name, 'status': 'error','message': f'准备文件时权限不足: {str(pe)}'})
                except Exception as e:
                    logger.exception(f"Error preparing {original_name} for pdfToFile (RequestID: {request_id}): {e}")
                    processed_results.append({'original_name': original_name, 'status': 'error', 'message': f'准备文件时出错: {str(e)}'})
            else: 
                processed_results.append(up_file_info)
    else: 
        if main_tab not in ['imgToFile', 'fileToPdf', 'pdfToFile'] and not any(r['status'] == 'error' for r in processed_results): 
            logger.warning(f"Unhandled main_tab '{main_tab}' or no files processed. RequestID: {request_id}")
            if not uploaded_files_info_from_frontend:
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件。'})
            elif not temp_files_for_final_processing and any(info['status'] == 'uploaded' for info in uploaded_files_info_from_frontend):
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '上传的文件无法按当前选择的模式处理。'})
            elif not temp_files_for_final_processing : 
                 processed_results.append({'original_name': '-', 'status': 'error', 'message': '没有文件可供处理。'})

    if temp_files_for_final_processing: 
        if merge_output:
            logger.debug(f"Attempting to merge {len(temp_files_for_final_processing)} files. MainTab: {main_tab}, SubTab: {sub_tab}, OutputFormat: {output_format}, RequestID: {request_id}.")
            random_chars_final_merge = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            merged_base_filename = f"{request.user.username}_{today_date_str}_{random_chars_final_merge}" # Final merged file name base
            final_merged_filename = f"{merged_base_filename}.{output_format}"
            final_merged_path = os.path.join(user_converted_dir, final_merged_filename)

            files_to_cleanup_after_merge = [info['path'] for info in temp_files_for_final_processing] # These should have request_id from earlier steps
            temp_individual_outputs_for_merging = []
            
            try:
                merge_successful = False
                if main_tab == 'fileToPdf' and sub_tab in ['excelToPdf', 'pptToPdf', 'txtToPdf']:
                    conversion_func = None
                    if sub_tab == 'excelToPdf': conversion_func = convert_excel_to_pdf
                    elif sub_tab == 'pptToPdf': conversion_func = ppt_pdf_converter.convert_pptx_to_pdf
                    elif sub_tab == 'txtToPdf': conversion_func = convert_txt_to_pdf

                    all_individual_conversions_successful = True
                    for item_info in temp_files_for_final_processing:
                        item_path = item_info['path']
                        item_original_name = item_info['original_name']
                        base_for_temp_pdf = os.path.splitext(os.path.basename(item_path))[0].replace(f"_prePdf_{request_id}", "") # Get original base before _prePdf_requestId
                        temp_pdf_name_for_merge = f"{base_for_temp_pdf}_merged_temp_{request_id}.pdf" # Add request_id
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
                            'message': f"合并多个PDF到单个 {output_format.upper()} 文件暂不支持。请取消勾选'合并为一个文件'以单独转换每个PDF，或选择DOCX/TXT作为合并输出格式。"
                        })
                        merge_successful = False 
                        perform_pdf_to_target_conversion_step = False # Skip the conversion-then-merge logic

                    if perform_pdf_to_target_conversion_step:
                        all_individual_pdf_to_target_conversions_ok = True
                        for item_info in temp_files_for_final_processing: # item_info['path'] are .pdf file copies
                            item_pdf_path = item_info['path'] 
                            item_original_pdf_name = item_info['original_name']
                            base_for_temp_conv = os.path.splitext(os.path.basename(item_pdf_path))[0].replace(f"_preFinal_{request_id}", "")
                            temp_indv_target_filename = f"{base_for_temp_conv}_indv_conv_{request_id}{target_ext_for_individual_conversion}" # Add request_id
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
                
                # --- imgToFile (to DOCX) or wordToPdf (original Word uploads to PDF merge) ---
                elif main_tab == 'imgToFile' or (main_tab == 'fileToPdf' and sub_tab == 'wordToPdf'):
                    merged_docx_intermediate_path = os.path.join(user_converted_dir, f"{merged_base_filename}_intermediate_{request_id}.docx")
                    first_doc_path = temp_files_for_final_processing[0]['path']
                    is_from_imgToFile = first_doc_path.endswith(f"_tempScriptOutput_{request_id}.docx")
                    is_from_wordToPdf_prePdf = sub_tab == 'wordToPdf' and f"_prePdf_{request_id}" in first_doc_path and first_doc_path.lower().endswith(('.doc', '.docx'))

                    if not (is_from_imgToFile or is_from_wordToPdf_prePdf):
                        logger.error(f"Merge logic error for {main_tab}/{sub_tab} (RequestID: {request_id}): Expected temp DOCX with request_id, but got {first_doc_path}")
                        processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': f'内部合并错误：期望处理的文件类型不匹配 ({os.path.basename(first_doc_path)}).'})
                        merge_successful = False 
                    else:
                        master_doc = Document(first_doc_path)
                        for doc_info in temp_files_for_final_processing[1:]:
                            sub_doc = Document(doc_info['path'])
                            master_doc.add_page_break()
                            append_document(sub_doc, master_doc)
                        master_doc.save(merged_docx_intermediate_path)
                        logger.info(f"Merged DOCX (intermediate for {main_tab}/{sub_tab}, RequestID: {request_id}) saved: {merged_docx_intermediate_path}")
                        if merged_docx_intermediate_path not in files_to_cleanup_after_merge:
                             files_to_cleanup_after_merge.append(merged_docx_intermediate_path)
                        
                        if output_format == 'pdf': # This case is for wordToPdf merge to PDF
                            if DOCX2PDF_AVAILABLE_IN_VIEW:
                                convert_docx_to_pdf(merged_docx_intermediate_path, final_merged_path)
                                logger.info(f"Converted merged DOCX to PDF: {final_merged_path} (RequestID: {request_id})")
                                merge_successful = True
                            else:
                                # Serve the intermediate DOCX as fallback if PDF conversion fails
                                final_merged_filename = os.path.basename(merged_docx_intermediate_path) 
                                final_merged_path = merged_docx_intermediate_path # Update final_merged_path to the .docx
                                logger.warning(f"DOCX to PDF failed for merged file (docx2pdf unavailable), serving DOCX: {final_merged_path}. (RequestID: {request_id})")
                                # Add specific fallback message to processed_results, this will be updated if file exists
                                processed_results.append({
                                    'original_name': "Merged Document (DOCX Fallback)", 
                                    'status': 'error', # Initially error, will be updated
                                    'message': 'DOCX转PDF库不可用，已合并为DOCX。请检查文件。', 
                                    'converted_name': final_merged_filename, 
                                    'download_url': None
                                })
                                merge_successful = True # Still true as DOCX is served
                        elif output_format == 'docx': # This case is for imgToFile merge to DOCX
                            if merged_docx_intermediate_path != final_merged_path: 
                                try:
                                    shutil.move(merged_docx_intermediate_path, final_merged_path)
                                    logger.info(f"Moved intermediate DOCX to final path: {final_merged_path} (RequestID: {request_id})")
                                    # If moved, merged_docx_intermediate_path might be in cleanup list, ensure no double removal attempts if it was renamed
                                    if merged_docx_intermediate_path in files_to_cleanup_after_merge:
                                         files_to_cleanup_after_merge.remove(merged_docx_intermediate_path) # It no longer exists at old path
                                except Exception as e_move:
                                    logger.error(f"Failed to move intermediate DOCX {merged_docx_intermediate_path} to {final_merged_path} (RequestID: {request_id}): {e_move}")
                                    # If move fails, the final_merged_path won't exist. We should signal this.
                                    merge_successful = False # Override to false if move fails
                                    processed_results.append({
                                        'original_name': "Merged Document", 
                                        'status': 'error', 
                                        'message': f'移动合并后的DOCX文件失败: {str(e_move)}'
                                    })
                            else: # Intermediate is already the final path (should not happen with current naming)
                                logger.info(f"Intermediate DOCX is already the final DOCX: {final_merged_path} (RequestID: {request_id})")
                            
                            if os.path.exists(final_merged_path): # Only set successful if final file exists
                                merge_successful = True
                            # else merge_successful remains as per move operation or initial False if path doesn't exist

                        else: 
                            logger.error(f"Unexpected output_format '{output_format}' for main_tab {main_tab}/{sub_tab} in DOCX-direct-merge path. (RequestID: {request_id})")
                            merge_successful = False
                
                # --- Common post-merge attempt processing --- 
                if merge_successful and os.path.exists(final_merged_path):
                    meta_file_path_merged = f"{final_merged_path}.meta"
                    # Ensure merged_original_names_list is correctly populated
                    merged_original_names_list = [info['original_name'] for info in temp_files_for_final_processing if isinstance(info, dict) and 'original_name' in info]
                    if not merged_original_names_list: # Fallback if something went wrong with temp_files_for_final_processing structure
                        merged_original_names_list = ["Unknown Original Files"] 
                        logger.warning(f"Could not determine original filenames for merged output (RequestID: {request_id}). Using placeholder.")

                    with open(meta_file_path_merged, 'w', encoding='utf-8') as mf: mf.write(",".join(merged_original_names_list))
                    
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', os.path.basename(final_merged_path)).replace("\\\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    
                    # Check if it was a DOCX fallback case that now has a valid file
                    fallback_entry_idx = -1
                    for i, r_item in enumerate(processed_results):
                        if r_item.get('original_name') == "Merged Document (DOCX Fallback)":
                            fallback_entry_idx = i
                            break
                    
                    if fallback_entry_idx != -1:
                        processed_results[fallback_entry_idx]['download_url'] = download_url 
                        processed_results[fallback_entry_idx]['status'] = 'success_fallback' 
                        # Ensure this is the only result if it was a fallback success
                        processed_results = [processed_results[fallback_entry_idx]]
                    else:
                        # Standard success: Clear previous errors and set the success message.
                        processed_results = [{
                            'original_name': ",".join(merged_original_names_list), 
                            'converted_name': os.path.basename(final_merged_path), 
                            'download_url': download_url, 
                            'status': 'success'
                        }]
                
                elif merge_output and not merge_successful:
                    # If already has a specific error for "Merged Document", don't add another generic one.
                    if not any(r.get('original_name') == "Merged Document" and r.get('status') == 'error' for r in processed_results):
                         processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': '所选的合并操作不受支持或未能完成。'})
                # If merge_output is false, individual results are already in processed_results

            except Exception as e_merge:
                logger.error(f"Error during merge operation (MainTab: {main_tab}, SubTab: {sub_tab}, OutputFormat: {output_format}, RequestID: {request_id}): {e_merge}", exc_info=True)
                if not any(r.get('original_name') == "Merged Document" and r.get('status') == 'error' for r in processed_results):
                    processed_results.append({'original_name': "Merged Document", 'status': 'error', 'message': f"合并文件时发生严重错误: {str(e_merge)}"})
            finally:
                logger.debug(f"Starting cleanup for RequestID: {request_id}. Files initially marked for cleanup: {files_to_cleanup_after_merge}")
                logger.debug(f"Intermediate files from conversions for merging (also to cleanup for RequestID: {request_id}): {temp_individual_outputs_for_merging}")
                
                # Add all individually converted intermediate files to the main cleanup list *before* making it unique
                for temp_f in temp_individual_outputs_for_merging:
                    if temp_f not in files_to_cleanup_after_merge:
                        files_to_cleanup_after_merge.append(temp_f)
                
                unique_files_to_cleanup = list(set(files_to_cleanup_after_merge))
                logger.debug(f"Unique files to attempt cleanup for RequestID: {request_id}: {unique_files_to_cleanup}")

                for f_path in unique_files_to_cleanup:
                    try: 
                        if os.path.exists(f_path):
                            # More robust check: ensure the file is truly a temporary file related to *this* request_id
                            # or a general temp file type that doesn't use request_id in its name pattern.
                            filename_only = os.path.basename(f_path)
                            is_this_request_specific_temp = f"_{request_id}.docx" in filename_only or \
                                                          f"_{request_id}.pdf" in filename_only or \
                                                          f"_{request_id}{os.path.splitext(filename_only)[1]}" in filename_only # for _prePdf_id.ext, _preFinal_id.ext, _indv_conv_id.ext
                            
                            is_general_known_temp_pattern = "_prePdf" in filename_only or \
                                                            "_preFinal" in filename_only or \
                                                            "_merged_temp.pdf" in filename_only or \
                                                            "_indv_conv" in filename_only or \
                                                            "_tempScriptOutput" in filename_only or \
                                                            "_intermediate" in filename_only

                            # If it's a request-specific temp, the request_id must match.
                            # If it's a general temp pattern AND doesn't have another request's ID, it might be from this request before ID was added everywhere.
                            # The most reliable way is if all temp files that should be request-specific *do* contain the request_id.
                            
                            can_delete = False
                            if f"_{request_id}" in filename_only: # Primary check for request-specific files
                                can_delete = True
                            elif is_general_known_temp_pattern:
                                # Check if it might belong to *another* request by trying to find any 6-char alphanumeric ID pattern
                                import re
                                other_request_id_pattern = r'_([a-z0-9]{6})\.(docx|pdf|txt|xlsx|pptx|doc|xls|ppt|jpeg|jpg|png|bmp)$'
                                match_other_id = re.search(other_request_id_pattern, filename_only)
                                if match_other_id and match_other_id.group(1) != request_id:
                                    logger.debug(f"Skipping cleanup of general temp pattern file {f_path} as it seems to belong to another request ID {match_other_id.group(1)} (Current RequestID: {request_id})")
                                else: # No other ID found, or it matches current, safe to assume it's from this request or an older non-ID'd temp
                                    can_delete = True 
                            
                            if can_delete:
                                os.remove(f_path)
                                logger.info(f"Cleaned up temp file (RequestID: {request_id}): {f_path}")
                            elif not is_general_known_temp_pattern and f"_{request_id}" not in filename_only:
                                logger.warning(f"Skipped cleanup of non-temp-pattern file {f_path} without current RequestID {request_id}. This might be an issue or an unrelated file.")
                                
                        else:
                            logger.debug(f"Temp file already removed or does not exist (RequestID: {request_id}): {f_path}")
                    except OSError as e_clean:
                        logger.warning(f"Failed to clean up temp file {f_path} (RequestID: {request_id}): {e_clean}")

        else: # Not merge_output: Process individual files
            for file_info in temp_files_for_final_processing:
                temp_source_for_individual_conversion = file_info['path'] 
                original_input_name = file_info['original_name']
                base_filename_no_ext = file_info['base_filename_no_ext']

                # Final output filename should NOT contain the request_id, but be unique
                random_chars_final_indv = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                final_output_base = f"{base_filename_no_ext}_{random_chars_final_indv}" 
                final_output_filename = f"{final_output_base}.{output_format}"
                final_output_path = os.path.join(user_converted_dir, final_output_filename)
                
                conversion_successful_individual = False
                actual_final_path_individual = final_output_path 
                
                try:
                    logger.info(f"Converting individual file '{original_input_name}' to {output_format} (RequestID: {request_id}): {temp_source_for_individual_conversion} -> {final_output_path}")
                    # ... (logic for individual conversions: if/elif for output_format)
                    # Example for one path:
                    if output_format == 'docx': 
                        if main_tab == 'pdfToFile' and sub_tab == 'pdfToWord':
                            success_ind, actual_final_path_individual, err_msg_ind = convert_pdf_to_word(temp_source_for_individual_conversion, final_output_path)
                            # ...
                        elif temp_source_for_individual_conversion.endswith(f"_tempScriptOutput_{request_id}.docx"): # From imgToFile
                            shutil.move(temp_source_for_individual_conversion, final_output_path)
                            actual_final_path_individual = final_output_path # Update actual path after move
                            # temp_source_for_individual_conversion is now gone or points to final_output_path if it was a rename
                        # else: logic for other docx cases
                    # ... (other output_format cases) ...

                    # After successful conversion (where actual_final_path_individual is the final file path)
                    if os.path.exists(actual_final_path_individual) and conversion_successful_individual: # Ensure conversion_successful_individual is set correctly in each branch
                        logger.info(f"Successfully processed '{original_input_name}' to '{os.path.basename(actual_final_path_individual)}' (RequestID: {request_id})")
                        # Clean up the temp_source_for_individual_conversion if it's different from final and contains request_id
                        if temp_source_for_individual_conversion != actual_final_path_individual and \
                           os.path.exists(temp_source_for_individual_conversion) and \
                           f"_{request_id}" in os.path.basename(temp_source_for_individual_conversion):
                            try:
                                os.remove(temp_source_for_individual_conversion)
                                logger.info(f"Removed temp source after individual conversion (RequestID: {request_id}): {temp_source_for_individual_conversion}")
                            except OSError as e_clean_indiv:
                                logger.warning(f"Failed to remove temp source {temp_source_for_individual_conversion} after individual conversion (RequestID: {request_id}): {e_clean_indiv}")
                    # ...
                except Exception as e_ind:
                    logger.error(f"Error converting individual file '{original_input_name}' to {output_format} (RequestID: {request_id}): {e_ind}", exc_info=True)
                    # ... (error reporting for individual conversion)

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
