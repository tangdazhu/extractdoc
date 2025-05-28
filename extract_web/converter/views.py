from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegistrationForm, AdminUserEditForm, AdminSetPasswordForm # 更新导入
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess # For running the script
from django.contrib import messages # 新增导入
from django.http import JsonResponse, FileResponse, Http404
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
from .pdf_to_word_converter import convert_pdf_to_word, convert_and_merge_pdfs_to_docx
# Add new imports for PDF to X converters
from .pdf_to_ppt_converter import convert_pdf_to_ppt, convert_and_merge_pdfs_to_pptx
from .pdf_to_txt_converter import convert_pdf_to_txt, convert_and_merge_pdfs_to_txt
from .libreoffice_converter import convert_to_pdf as convert_to_pdf_libreoffice # Import LO converter
from .word_to_pdf_converter import convert_word_to_pdf # ADDED: Import for the new Word to PDF converter
from django.core.exceptions import PermissionDenied # For security checks

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
    
    # Get conversion mode parameters for all PDF conversion types
    pdf_to_ppt_mode = 'screenshot' # Default for all cases, will be overridden if applicable
    pdf_to_word_mode = 'pdf2docx' # Default mode for PDF to Word
    pdf_to_excel_mode = 'pdfplumber' # Default mode for PDF to Excel
    pdf_to_txt_mode = 'pymupdf' # Default mode for PDF to TXT

    if main_tab == 'fileToPdf':
        output_format = 'pdf'
    elif main_tab == 'imgToFile':
        output_format = output_format_param if output_format_param else 'docx'
    elif main_tab == 'pdfToFile':
        if sub_tab == 'pdfToWord': 
            output_format = 'docx'
            pdf_to_word_mode = request.POST.get('pdf_to_word_mode', 'pdf2docx')
            logger.info(f"[process_images_view] PDF to Word mode explicitly set to: {pdf_to_word_mode} for RequestID: {request_id}")
        elif sub_tab == 'pdfToExcel': 
            output_format = 'xlsx'
            pdf_to_excel_mode = request.POST.get('pdf_to_excel_mode', 'pdfplumber')
            logger.info(f"[process_images_view] PDF to Excel mode explicitly set to: {pdf_to_excel_mode} for RequestID: {request_id}")
        elif sub_tab == 'pdfToPpt': 
            output_format = 'pptx'
            pdf_to_ppt_mode = request.POST.get('pdf_to_ppt_mode', 'screenshot')
            logger.info(f"[process_images_view] PDF to PPT mode explicitly set to: {pdf_to_ppt_mode} for RequestID: {request_id}")
        elif sub_tab == 'pdfToTxt': 
            output_format = 'txt'
            pdf_to_txt_mode = request.POST.get('pdf_to_txt_mode', 'pymupdf')
            logger.info(f"[process_images_view] PDF to TXT mode explicitly set to: {pdf_to_txt_mode} for RequestID: {request_id}")
        else:
            output_format = output_format_param
            logger.warning(f"pdfToFile: Unknown sub_tab ('{sub_tab}'), fallback to param: '{output_format_param}', RequestID: {request_id}")
            if not output_format: output_format = 'docx'; logger.error(f"pdfToFile: Critical fallback to docx for unknown sub_tab, RequestID: {request_id}")
    else: 
        output_format = output_format_param
        logger.warning(f"Unhandled main_tab '{main_tab}', fallback to param: '{output_format_param}', RequestID: {request_id}")
        if not output_format: output_format = 'docx'; logger.error(f"Fallback: Critical fallback to docx for unhandled main_tab, RequestID: {request_id}")

    logger.debug(f"Process Request: User={request.user.username}, Date={today_date_str}, Merge={merge_output}, RequestedFormat='{output_format_param}', EffectiveOutputFormat='{output_format}', MainTab={main_tab}, SubTab={sub_tab}, PDFtoWordMode={pdf_to_word_mode}, PDFtoExcelMode={pdf_to_excel_mode}, PDFtoPPTMode={pdf_to_ppt_mode}, PDFtoTXTMode={pdf_to_txt_mode}, RequestID: {request_id}")

    if main_tab == 'fileToPdf' and output_format == 'pdf' and not DOCX2PDF_AVAILABLE_IN_VIEW and sub_tab == 'wordToPdf':
        logger.error(f"PDF output requested for Word file, but docx2pdf is not available. RequestID: {request_id}")
        return JsonResponse({'results': [{'original_name': 'Conversion', 'status': 'error', 'message': 'Word转PDF的转换库(docx2pdf)不可用。'}], 'merge_output': merge_output})

    processed_files = []
    temp_files_to_delete = [] # Keep track of temporary files for cleanup

    if not request.FILES.getlist('images'):
        logger.error(f"No files uploaded for conversion. RequestID: {request_id}")
        return JsonResponse({'results': [{'original_name': 'File Upload', 'status': 'error', 'message': '没有上传文件或文件列表为空。'}], 'merge_output': merge_output})

    # Create a list of uploaded file information (original_name, temp_path)
    # This is done *before* the main processing loop to ensure all files are saved first.
    uploaded_files_info_from_frontend = []
    for uploaded_file in request.FILES.getlist('images'): 
        original_filename = uploaded_file.name
        # Sanitize filename to prevent directory traversal or other issues
        safe_original_filename = Path(original_filename).name 
        
        # Create a unique name for the temporary input file to avoid collisions before conversion
        temp_input_base, temp_input_ext = os.path.splitext(safe_original_filename)
        temp_input_filename = f"{temp_input_base}_{request_id}_input{temp_input_ext}"
        temp_input_path = os.path.join(user_upload_dir, temp_input_filename) # Save to uploads, then move to converted

        with open(temp_input_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        uploaded_files_info_from_frontend.append({
            'original_name': original_filename, # Keep original for display
            'temp_path': temp_input_path,
            'safe_original_filename': safe_original_filename # Use for constructing output names
        })
        logger.info(f"Uploaded and saved temporary input file: {temp_input_path} for original: {original_filename}. RequestID: {request_id}")

    # Main processing logic starts here
    if main_tab == 'fileToPdf':
        for uploaded_file_data in uploaded_files_info_from_frontend:
            original_name = uploaded_file_data['original_name']
            temp_input_path = uploaded_file_data['temp_path']
            safe_original_filename = uploaded_file_data['safe_original_filename']

            base_name_no_ext = os.path.splitext(safe_original_filename)[0]
            unique_pdf_filename = f"{base_name_no_ext}_{request_id}.pdf" # Simpler unique name for output
            output_pdf_path = os.path.join(user_converted_dir, unique_pdf_filename)

            success = False
            conversion_message = "不支持的文件类型或转换失败。"
            actual_output_file_path_from_converter = None # To store the actual path returned by converter

            try:
                logger.info(f"fileToPdf: Processing {original_name} with sub_tab: {sub_tab}. Input: {temp_input_path}, Output: {output_pdf_path}. RequestID: {request_id}")
                if sub_tab == 'wordToPdf':
                    if original_name.lower().endswith(('.doc', '.docx')):
                        success, actual_output_file_path_from_converter, conversion_message = convert_word_to_pdf(temp_input_path, output_pdf_path)
                    else:
                        conversion_message = "不是有效的Word文件 (.doc, .docx)。"
                elif sub_tab == 'excelToPdf':
                    if original_name.lower().endswith(('.xls', '.xlsx')):
                        success, actual_output_file_path_from_converter, conversion_message = convert_excel_to_pdf(temp_input_path, output_pdf_path)
                    else:
                        conversion_message = "不是有效的Excel文件 (.xls, .xlsx)。"
                elif sub_tab == 'pptToPdf':
                    if original_name.lower().endswith(('.ppt', '.pptx')):
                        success, actual_output_file_path_from_converter, conversion_message = ppt_pdf_converter.convert_pptx_to_pdf(temp_input_path, output_pdf_path)
                    else:
                        conversion_message = "不是有效的PPT文件 (.ppt, .pptx)。"
                elif sub_tab == 'txtToPdf':
                    if original_name.lower().endswith('.txt'):
                        success, actual_output_file_path_from_converter, conversion_message = convert_txt_to_pdf(temp_input_path, output_pdf_path)
                    else:
                        conversion_message = "不是有效的TXT文件 (.txt)。"
                # ADD OTHER sub_tab conditions for fileToPdf HERE (e.g., imageToPdf if that's a sub_tab)
                else:
                    logger.warning(f"fileToPdf: Unsupported sub_tab '{sub_tab}' for {original_name}. RequestID: {request_id}")
                    conversion_message = f"不支持的转换类型: {sub_tab}"

                if success and actual_output_file_path_from_converter and os.path.exists(actual_output_file_path_from_converter):
                    # If converter returns a different path (e.g. due to its own naming logic), use it.
                    # Also, ensure the final file is named as `unique_pdf_filename` in `user_converted_dir`.
                    final_target_path = os.path.join(user_converted_dir, unique_pdf_filename)
                    if actual_output_file_path_from_converter != final_target_path:
                        shutil.move(actual_output_file_path_from_converter, final_target_path)
                        logger.info(f"Moved converted file from {actual_output_file_path_from_converter} to {final_target_path}. RequestID: {request_id}")
                    
                    processed_files.append({
                        'original_name': original_name,
                        'converted_name': unique_pdf_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, unique_pdf_filename]),
                        'status': 'success',
                        'message': conversion_message or '转换成功'
                    })
                    logger.info(f"fileToPdf/{sub_tab}: Successfully converted '{original_name}' to '{unique_pdf_filename}'. RequestID: {request_id}")
                else:
                    processed_files.append({
                        'original_name': original_name,
                        'status': 'error',
                        'message': conversion_message or "转换失败，未生成文件。"
                    })
                    logger.error(f"fileToPdf/{sub_tab}: Failed to convert '{original_name}'. Message: {conversion_message}. RequestID: {request_id}")

            except Exception as e_conv:
                logger.error(f"Exception during {sub_tab} to PDF conversion for {original_name}: {e_conv}. RequestID: {request_id}", exc_info=True)
                processed_files.append({
                    'original_name': original_name,
                    'status': 'error',
                    'message': f"转换时发生严重错误: {str(e_conv)}"
                })
            finally:
                # Clean up the unique temporary input file from user_upload_dir
                if os.path.exists(temp_input_path):
                    try:
                        os.remove(temp_input_path)
                        logger.debug(f"Cleaned up temp input file: {temp_input_path}. RequestID: {request_id}")
                    except Exception as e_del_temp_input:
                        logger.warning(f"Failed to delete temp input file {temp_input_path}: {e_del_temp_input}. RequestID: {request_id}")
        
        # Merging logic for fileToPdf (if applicable and successful PDFs exist)
        if merge_output and any(f['status'] == 'success' for f in processed_files) and PYPDF2_AVAILABLE:
            successful_pdfs = [os.path.join(user_converted_dir, f['converted_name']) for f in processed_files if f['status'] == 'success']
            if len(successful_pdfs) > 1:
                merged_pdf_name = f"merged_files_{request_id}.pdf"
                merged_pdf_path = os.path.join(user_converted_dir, merged_pdf_name)
                merger = PdfMerger()
                try:
                    for pdf_path_to_merge in successful_pdfs:
                        if os.path.exists(pdf_path_to_merge):
                            merger.append(pdf_path_to_merge)
                    merger.write(merged_pdf_path)
                    merger.close()
                    logger.info(f"fileToPdf: Successfully merged {len(successful_pdfs)} PDFs into '{merged_pdf_name}'. RequestID: {request_id}")
                    
                    final_merged_result_message = f"{len(successful_pdfs)} 个文件成功合并为PDF。"
                    # Add errors from individual conversions to the merged message if any
                    error_messages_for_merge = [f['message'] for f in processed_files if f['status'] == 'error' and f['original_name'] != '合并操作']
                    if error_messages_for_merge:
                        final_merged_result_message += " 未能转换的文件: " + "; ".join(error_messages_for_merge)

                    processed_files = [{
                        'original_name': '合并的PDF文件',
                        'converted_name': merged_pdf_name,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, merged_pdf_name]),
                        'status': 'success',
                        'message': final_merged_result_message
                    }]
                    
                    for pdf_to_delete in successful_pdfs:
                        if os.path.exists(pdf_to_delete):
                            try:
                                os.remove(pdf_to_delete)
                            except Exception as e_del_merged_src:
                                logger.warning(f"Failed to delete merged source PDF {pdf_to_delete}: {e_del_merged_src}. RequestID: {request_id}")
                except Exception as e_merge:
                    logger.error(f"Error merging PDFs in fileToPdf: {e_merge}. RequestID: {request_id}", exc_info=True)
                    processed_files.append({'original_name': '合并操作', 'status': 'error', 'message': f'PDF合并失败: {str(e_merge)}'})
            elif len(successful_pdfs) == 1:
                 logger.info(f"fileToPdf: Only one successful PDF ('{processed_files[0]['converted_name']}'), no merging needed. RequestID: {request_id}")
                 # If only one successful PDF and merge_output is true, we should still present it as the primary result.
                 # The current structure of appending to processed_files already handles this, so just logging.

        elif merge_output and not PYPDF2_AVAILABLE and any(f['status'] == 'success' for f in processed_files):
            logger.warning(f"fileToPdf: Merge requested but PyPDF2 is not available. RequestID: {request_id}")
            processed_files.append({'original_name': '合并操作', 'status': 'warning', 'message': 'PDF合并库不可用，文件未合并。'})

    elif main_tab == 'imgToFile':
        img_processed_results, img_temp_files_list_of_dicts = process_images_to_files(
            uploaded_files_info_from_frontend, 
            user_converted_dir,
            request_id 
        )
        processed_files.extend(img_processed_results) 
        temp_files_to_delete.extend(img_temp_files_list_of_dicts)

    elif main_tab == 'pdfToFile':
        # uploaded_files_info_from_frontend contains dicts with:
        # {'original_name': ..., 'temp_path': ..., 'safe_original_filename': ...}
        # The error occurs because we check for 'status', 'name', 'path' which don't exist here.
        # We should use the available keys. If it's in this list, it's effectively 'uploaded'.

        for up_file_info in uploaded_files_info_from_frontend:
            # All files in uploaded_files_info_from_frontend are considered successfully uploaded at this stage.
            # The original error was due to checking up_file_info['status'] which wasn't set
            # when uploaded_files_info_from_frontend was initially populated.
            # We will use 'original_name' and 'temp_path' from up_file_info.
            
            original_name = up_file_info['original_name']
            source_file_path = up_file_info['temp_path'] # This is the path to the uploaded file in user_upload_dir
            safe_original_filename = up_file_info['safe_original_filename']
            base_name_no_ext = os.path.splitext(safe_original_filename)[0]

            output_file_path = None # Will be set by the specific converter
            converted_filename = None
            success = False
            conversion_message = "未进行转换或不支持的子类型。"
            
            try:
                if not original_name.lower().endswith('.pdf'):
                    error_message = f"文件类型不匹配 ({sub_tab}): {original_name} (应为PDF)"
                    logger.warning(f"{error_message} (RequestID: {request_id})")
                    processed_files.append({'original_name': original_name, 'status': 'error', 'message': error_message})
                    temp_files_to_delete.append({
                        'path': source_file_path,
                        'original_name': original_name,
                        'base_filename_no_ext': base_name_no_ext,
                        'status': 'success' # Indicates the file is ready for further processing by Block D
                    })
                    continue

                logger.info(f"pdfToFile: Processing {original_name} with sub_tab: {sub_tab}. Input: {source_file_path}. RequestID: {request_id}")

                if sub_tab == 'pdfToWord':
                    output_filename_docx = f"{base_name_no_ext}_{request_id}.docx"
                    output_file_path = os.path.join(user_converted_dir, output_filename_docx)
                    success, actual_output_path, conversion_message = convert_pdf_to_word(
                        source_file_path, 
                        output_file_path, 
                        mode=pdf_to_word_mode # This should be passed from frontend or have a default
                    )
                    if success and actual_output_path:
                        converted_filename = os.path.basename(actual_output_path)
                
                elif sub_tab == 'pdfToExcel':
                    output_filename_excel = f"{base_name_no_ext}_{request_id}.xlsx"
                    output_file_path = os.path.join(user_converted_dir, output_filename_excel)
                    success, actual_output_path, conversion_message = convert_pdf_to_excel(
                        source_file_path, 
                        output_file_path,
                        mode=pdf_to_excel_mode # Pass the mode to the converter
                    )
                    if success and actual_output_path:
                        converted_filename = os.path.basename(actual_output_path)

                elif sub_tab == 'pdfToPpt':
                    output_filename_pptx = f"{base_name_no_ext}_{request_id}.pptx"
                    output_file_path = os.path.join(user_converted_dir, output_filename_pptx)
                    success, actual_output_path, conversion_message = convert_pdf_to_ppt(
                        source_file_path, 
                        output_file_path,
                        mode=pdf_to_ppt_mode # Pass the mode
                    )
                    if success and actual_output_path:
                        converted_filename = os.path.basename(actual_output_path)
                
                elif sub_tab == 'pdfToTxt':
                    output_filename_txt = f"{base_name_no_ext}_{request_id}.txt"
                    output_file_path = os.path.join(user_converted_dir, output_filename_txt)
                    success, actual_output_path, conversion_message = convert_pdf_to_txt(
                        source_file_path, 
                        output_file_path,
                        mode=pdf_to_txt_mode # Pass the mode
                    )
                    if success and actual_output_path:
                        converted_filename = os.path.basename(actual_output_path)
                
                else:
                    logger.warning(f"pdfToFile: Unsupported sub_tab '{sub_tab}' for {original_name}. RequestID: {request_id}")
                    conversion_message = f"不支持的转换类型: {sub_tab}"

                if success and converted_filename and os.path.exists(os.path.join(user_converted_dir, converted_filename)):
                    final_output_path_in_converted_dir = os.path.join(user_converted_dir, converted_filename)
                    # Ensure actual_output_path (if different) is moved to final_output_path_in_converted_dir
                    if actual_output_path and actual_output_path != final_output_path_in_converted_dir:
                        if os.path.exists(final_output_path_in_converted_dir):
                            os.remove(final_output_path_in_converted_dir) # Remove if exists to avoid error on move
                        shutil.move(actual_output_path, final_output_path_in_converted_dir)
                        logger.info(f"Moved converted file from {actual_output_path} to {final_output_path_in_converted_dir}. RequestID: {request_id}")

                    processed_files.append({
                        'original_name': original_name,
                        'converted_name': converted_filename,
                        'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, converted_filename]),
                        'status': 'success',
                        'message': conversion_message or '转换成功'
                    })
                    logger.info(f"pdfToFile/{sub_tab}: Successfully converted '{original_name}' to '{converted_filename}'. RequestID: {request_id}")
                else:
                    processed_files.append({
                        'original_name': original_name,
                        'status': 'error',
                        'message': conversion_message or "转换失败，未生成文件。"
                    })
                    logger.error(f"pdfToFile/{sub_tab}: Failed to convert '{original_name}'. Message: {conversion_message}. RequestID: {request_id}")

            except Exception as e_conv:
                logger.error(f"Exception during {sub_tab} conversion for {original_name}: {e_conv}. RequestID: {request_id}", exc_info=True)
                processed_files.append({
                    'original_name': original_name,
                    'status': 'error',
                    'message': f"转换时发生严重错误: {str(e_conv)}"
                })
            finally:
                # The source_file_path is the temporary input file in user_upload_dir.
                # It should be cleaned up by the later general processing block (Block D).
                # Add it as a dictionary to be compatible with Block D.
                temp_files_to_delete.append({
                    'path': source_file_path,
                    'original_name': original_name,
                    'base_filename_no_ext': base_name_no_ext,
                    'status': 'success' # Indicates the file is ready for further processing by Block D
                })
        
        # Merging logic for pdfToFile (if merge_output is true)
        # This tab converts multiple PDFs to a target format. If merge_output is selected,
        # the individual converted files (e.g., multiple DOCX files) should be merged.
        if merge_output and any(f['status'] == 'success' for f in processed_files):
            successful_conversions = [f for f in processed_files if f['status'] == 'success']
            if len(successful_conversions) > 1:
                files_to_merge_paths = [os.path.join(user_converted_dir, f['converted_name']) for f in successful_conversions]
                first_file_ext = os.path.splitext(files_to_merge_paths[0])[1].lower()
                merged_filename = f"merged_files_{request_id}{first_file_ext}"
                merged_output_path = os.path.join(user_converted_dir, merged_filename)
                merge_success = False
                merge_message = ""

                try:
                    if sub_tab == 'pdfToWord' and first_file_ext == '.docx':
                        original_pdf_sources = [f['path'] for f in uploaded_files_info_from_frontend if f.get('path') and os.path.splitext(f['name'])[1].lower() == '.pdf']
                        if original_pdf_sources and hasattr(settings, 'CONVERSION_MODES'): # Check if pdf_to_word_mode would be available
                            merge_success, merge_message = convert_and_merge_pdfs_to_docx(original_pdf_sources, merged_output_path, request_id, mode=pdf_to_word_mode)
                        elif not original_pdf_sources:
                            merge_success = False
                            merge_message = "Could not find original PDF files to merge for DOCX output."
                        else:
                            merge_success = False
                            merge_message = "PDF to Word conversion mode not available for merging."

                    elif sub_tab == 'pdfToPpt' and first_file_ext == '.pptx':
                        original_pdf_sources = [f['path'] for f in uploaded_files_info_from_frontend if f.get('path') and os.path.splitext(f['name'])[1].lower() == '.pdf']
                        if original_pdf_sources and hasattr(settings, 'CONVERSION_MODES'): # Check if pdf_to_ppt_mode would be available
                            merge_success, merge_message = convert_and_merge_pdfs_to_pptx(original_pdf_sources, merged_output_path, request_id, ppt_creation_mode=pdf_to_ppt_mode)
                        elif not original_pdf_sources:
                            merge_success = False
                            merge_message = "Could not find original PDF files to merge for PPTX output."
                        else:
                            merge_success = False
                            merge_message = "PDF to PPT conversion mode not available for merging."

                    elif sub_tab == 'pdfToTxt' and first_file_ext == '.txt':
                        original_pdf_sources = [f['path'] for f in uploaded_files_info_from_frontend if f.get('path') and os.path.splitext(f['name'])[1].lower() == '.pdf']
                        if original_pdf_sources and hasattr(settings, 'CONVERSION_MODES'): # Check if pdf_to_txt_mode would be available
                             merge_success, merge_message = convert_and_merge_pdfs_to_txt(original_pdf_sources, merged_output_path, request_id, mode=pdf_to_txt_mode)
                        elif not original_pdf_sources:
                            merge_success = False
                            merge_message = "Could not find original PDF files to merge for TXT output."
                        else:
                            merge_success = False
                            merge_message = "PDF to TXT conversion mode not available for merging."
                    else:
                        logger.info(f"Merge requested for {sub_tab}, but merging for {first_file_ext} is not supported or only one file. Skipping merge. RequestID: {request_id}")
                        # Not an error, just don't merge. The individual files are still available.
                        # To prevent issues, ensure merge_success is False if no merge action is taken.
                        merge_success = False 
                        merge_message = f"Merging for {first_file_ext} from {sub_tab} is not implemented in this block."

                    if merge_success:
                        logger.info(f"pdfToFile/{sub_tab}: Successfully merged {len(files_to_merge_paths)} files into '{merged_filename}'. RequestID: {request_id}")
                        final_merged_result_message = f"{len(files_to_merge_paths)} 个文件成功转换为 {sub_tab.replace('pdfTo','')} 并合并。"
                        
                        # Update processed_files to show only the merged file
                        processed_files = [{
                            'original_name': f'合并的 {sub_tab.replace("pdfTo","")} 文件',
                            'converted_name': merged_filename,
                            'download_url': reverse('converter:download_converted_file', args=[request.user.username, today_date_str, merged_filename]),
                            'status': 'success',
                            'message': merge_message or final_merged_result_message
                        }]
                        # Clean up individual files that were merged
                        for old_file_path in files_to_merge_paths:
                            if os.path.exists(old_file_path):
                                try:
                                    os.remove(old_file_path)
                                except Exception as e_del_merged_src:
                                    logger.warning(f"Failed to delete merged source file {old_file_path}: {e_del_merged_src}. RequestID: {request_id}")
                    elif merge_message: # Merge attempted but failed
                        # Keep individual files, add a warning about merge failure
                        processed_files.append({'original_name': '合并操作', 'status': 'error', 'message': f'{sub_tab.replace("pdfTo","")} 文件合并失败: {merge_message}'})
                        logger.error(f"Failed to merge files for {sub_tab}: {merge_message}. RequestID: {request_id}")

                except Exception as e_merge_sub_tab:
                    logger.error(f"Error during merging for {sub_tab}: {e_merge_sub_tab}. RequestID: {request_id}", exc_info=True)
                    processed_files.append({'original_name': '合并操作', 'status': 'error', 'message': f'{sub_tab.replace("pdfTo","")} 文件合并时发生严重错误: {str(e_merge_sub_tab)}'})
            
            elif len(successful_conversions) == 1 and merge_output:
                logger.info(f"pdfToFile/{sub_tab}: Merge output selected, but only one successful conversion. No merge needed. File: {successful_conversions[0]['converted_name']}. RequestID: {request_id}")
                # No action needed, individual file is already in processed_files.

    else: 
        if main_tab not in ['imgToFile', 'fileToPdf', 'pdfToFile'] and not any(r['status'] == 'error' for r in processed_files): 
            logger.warning(f"Unhandled main_tab '{main_tab}' or no files processed. RequestID: {request_id}")
            if not uploaded_files_info_from_frontend:
                 processed_files.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件。'})
            elif not temp_files_to_delete and any(info['status'] == 'uploaded' for info in uploaded_files_info_from_frontend):
                 processed_files.append({'original_name': '-', 'status': 'error', 'message': '上传的文件无法按当前选择的模式处理。'})
            elif not temp_files_to_delete : 
                 processed_files.append({'original_name': '-', 'status': 'error', 'message': '没有文件可供处理。'})

    # Filter out files that failed initial processing for merge/individual conversion stages
    valid_temp_files_for_processing = [f for f in temp_files_to_delete if f.get('status') == 'success']

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
                        pdf_success, pdf_path_or_msg, _ = convert_word_to_pdf(temp_merged_docx_path, final_merged_path)
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
                        # Pass the mode parameter to the conversion function
                        current_merge_op_success, current_merge_op_message = convert_and_merge_pdfs_to_docx(paths_of_temp_sources_for_merge, final_merged_path, request_id, mode=pdf_to_word_mode)
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
                        # Pass the mode parameter to the conversion function
                        current_merge_op_success, current_merge_op_message = convert_and_merge_pdfs_to_txt(paths_of_temp_sources_for_merge, final_merged_path, request_id, mode=pdf_to_txt_mode)
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
                
                # Add result for merge operation to processed_files
                if current_merge_op_success and os.path.exists(final_merged_path):
                    meta_file_path_merged = f"{final_merged_path}.meta"
                    with open(meta_file_path_merged, 'w', encoding='utf-8') as mf: mf.write(",".join(original_names_for_meta))
                    relative_media_path = os.path.join(request.user.username, today_date_str, 'converted_files', final_merged_filename).replace("\\", "/")
                    download_url = f"{settings.MEDIA_URL}{relative_media_path}"
                    processed_files = [{
                        'original_name': ",".join(original_names_for_meta),
                        'converted_name': final_merged_filename, 
                        'download_url': download_url, 
                        'status': 'success',
                        'message': current_merge_op_message or "合并成功"
                    }]
                elif merge_output: # If merge was checked but failed
                    processed_files = [{
                        'original_name': "合并操作", 
                        'status': 'error', 
                        'message': current_merge_op_message or f'合并到 {output_format.upper()} 失败或不受支持。'
                    }]
            except Exception as e_merge_main:
                logger.error(f"Error during main merge operation block (RequestID: {request_id}): {e_merge_main}", exc_info=True)
                if merge_output: # Ensure an error is reported if merge was intended
                    processed_files = [{'original_name': "合并操作", 'status': 'error', 'message': f"合并文件时发生严重错误: {str(e_merge_main)}"}]

        else: # Not merge_output: Process individual files
            for file_info in valid_temp_files_for_processing:
                temp_source_for_individual_conversion = file_info['path']
                original_input_name = file_info['original_name']
                base_filename_no_ext_for_indiv = file_info['base_filename_no_ext']

                # If main_tab is 'fileToPdf' or 'pdfToFile' and not merging,
                # Loop A already created the final file and added it to processed_files.
                # The temp_source_for_individual_conversion here is the original uploaded file
                # which just needs to be cleaned up.
                if main_tab in ['fileToPdf', 'pdfToFile']:
                    logger.info(f"Block E: '{original_input_name}' (main_tab: {main_tab}, no-merge) already processed by Loop A. Skipping re-conversion in Block E. RequestID: {request_id}")
                    # Ensure the original uploaded file is cleaned up
                    if os.path.exists(temp_source_for_individual_conversion) and \
                       Path(temp_source_for_individual_conversion).parent.samefile(Path(user_upload_dir)): # Safety check for upload dir
                        try:
                            os.remove(temp_source_for_individual_conversion)
                            logger.info(f"Block E: Cleaned up original upload {temp_source_for_individual_conversion} for skipped item. RequestID: {request_id}")
                        except OSError as e_clean_skipped_in_E:
                            logger.warning(f"Block E: Failed to clean up original upload {temp_source_for_individual_conversion} for skipped item: {e_clean_skipped_in_E}. RequestID: {request_id}")
                    continue # Skip to the next file in valid_temp_files_for_processing

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
                            # Pass the mode parameter to the conversion function
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_word(temp_source_for_individual_conversion, final_output_path_indiv, mode=pdf_to_word_mode)
                        elif output_format == 'pptx':
                            # Use pdf_to_ppt_mode retrieved earlier
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_ppt(temp_source_for_individual_conversion, final_output_path_indiv, mode=pdf_to_ppt_mode, desired_filename_base=final_output_base_indiv)
                        elif output_format == 'xlsx':
                            # Pass the mode parameter to the conversion function
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_excel(temp_source_for_individual_conversion, final_output_path_indiv, mode=pdf_to_excel_mode)
                        elif output_format == 'txt':
                            # Pass the mode parameter to the conversion function
                            conversion_successful_individual, actual_final_path_for_individual, err_msg_for_individual = convert_pdf_to_txt(temp_source_for_individual_conversion, final_output_path_indiv, mode=pdf_to_txt_mode)
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
                        processed_files.append({
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
                        processed_files.append({
                            'original_name': original_input_name, 
                            'status': 'error', 
                            'message': str(err_msg_for_individual or '转换失败，未返回具体错误信息。')
                        })
                except Exception as e_ind_main:
                    logger.error(f"Error converting individual file '{original_input_name}' (RequestID: {request_id}): {e_ind_main}", exc_info=True)
                    processed_files.append({'original_name': original_input_name, 'status': 'error', 'message': f'处理单个文件转换时发生意外错误: {str(e_ind_main)}'})
    
    elif not uploaded_files_info_from_frontend : # No files were uploaded at all
        processed_files.append({'original_name': '-', 'status': 'error', 'message': '没有上传文件，无法开始转换。'})
    # If temp_files_to_delete is empty but uploaded_files_info_from_frontend is not,
    # it means all initial file preparations failed and errors are already in processed_files.
    
    logger.info(f"Final processed results to be sent to client (RequestID: {request_id}): {processed_files}")
    return JsonResponse({'results': processed_files, 'merge_output': merge_output})

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

@login_required
def download_converted_file_view(request, username, date_str, filename):
    # Security check: Ensure the logged-in user matches the username in the URL
    # or the logged-in user is a superuser.
    if not (request.user.username == username or request.user.is_superuser):
        raise PermissionDenied("您没有权限下载此文件。")

    # Construct the full path to the file
    # Ensure to use settings.BASE_DIR or another secure base path for `his_pic`
    file_path = os.path.join(settings.BASE_DIR, 'his_pic', username, date_str, 'converted_files', filename)
    
    logger.debug(f"Download request for user {request.user.username} (URL username: {username}): {file_path}")

    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        except Exception as e:
            logger.error(f"Error serving file {file_path} for download: {e}", exc_info=True)
            raise Http404("下载文件时发生错误。")
    else:
        logger.error(f"File not found for download by {request.user.username}: {file_path}")
        raise Http404("文件未找到。")
