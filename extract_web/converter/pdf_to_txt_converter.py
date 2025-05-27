import fitz  # PyMuPDF
import os
import logging
import subprocess

logger = logging.getLogger(__name__)

def convert_pdf_to_txt(pdf_path, txt_output_path, mode='pymupdf'):
    """
    Converts a PDF file to a TXT file by extracting text content.
    
    Args:
        pdf_path (str): Path to input PDF file
        txt_output_path (str): Path to output TXT file  
        mode (str): Conversion mode - 'pymupdf' (default) or 'libreoffice'
    
    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
          """
    try:
        logger.info(f"Starting PDF to TXT conversion using {mode} mode: {pdf_path} -> {txt_output_path}")

        if not os.path.exists(pdf_path):
            return False, None, "Input PDF file not found."

        if mode == 'libreoffice':
            return _convert_pdf_to_txt_libreoffice(pdf_path, txt_output_path)
        else:  # Default to pymupdf mode
            return _convert_pdf_to_txt_pymupdf(pdf_path, txt_output_path)

    except Exception as e:
        logger.error(f"Error during PDF to TXT conversion for '{pdf_path}' using {mode}: {e}", exc_info=True)
        return False, None, f"PDF转TXT失败: {str(e)}"

def _convert_pdf_to_txt_pymupdf(pdf_path, txt_output_path):
    """Convert PDF to TXT using PyMuPDF."""
    try:
        pdf_document = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text("text") # Extract text as plain text
            if page_num < len(pdf_document) - 1: # Add page break if not the last page
                text += "\n\n--- Page Break ---\n\n" 
        
        pdf_document.close()

        with open(txt_output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"Successfully extracted text using PyMuPDF from {pdf_path} to {txt_output_path}")
        return True, txt_output_path, None
        
    except Exception as e:
        logger.error(f"Error during PyMuPDF PDF to TXT conversion for {pdf_path}: {e}", exc_info=True)
        return False, None, f"PyMuPDF转换失败: {str(e)}"

def _convert_pdf_to_txt_libreoffice(pdf_path, txt_output_path):
    """Convert PDF to TXT using LibreOffice."""
    try:
        output_dir = os.path.dirname(txt_output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Using LibreOffice to convert {pdf_path} to {txt_output_path}")
        
        # Try method 1: Force Writer import with UTF8 text export
        cmd = [
            'soffice', 
            '--headless',
            '--infilter=writer_pdf_import',
            '--convert-to', 'txt:Text (encoded):UTF8',
            '--outdir', output_dir,
            pdf_path
        ]
        
        logger.info(f"Executing LibreOffice command (method 1): {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # LibreOffice creates output with the same base name as input but different extension
        input_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        expected_output = os.path.join(output_dir, f"{input_basename}.txt")
        
        if result.returncode == 0 and os.path.exists(expected_output):
            # Check if the output file has content
            try:
                with open(expected_output, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                file_size = os.path.getsize(expected_output)
                logger.info(f"Method 1 output file size: {file_size} bytes, content length: {len(content)} chars")
                
                # Debug: show the actual content and bytes
                with open(expected_output, 'rb') as fb:
                    raw_bytes = fb.read()
                logger.info(f"Method 1 raw bytes: {raw_bytes[:100]}")  # First 100 bytes
                logger.info(f"Method 1 content preview: {repr(content[:100])}")  # First 100 chars
                
                # Check if content is meaningful (not just BOM and whitespace)
                meaningful_content = content.replace('\ufeff', '').strip()  # Remove BOM and whitespace
                
                if len(meaningful_content) == 0:
                    logger.warning(f"Method 1 produced only BOM/whitespace (meaningful content length: 0), will try method 2")
                    # Don't return success yet, let it fall through to method 2
                else:
                    # Success with method 1 and has content
                    if expected_output != txt_output_path:
                        if os.path.exists(txt_output_path):
                            os.remove(txt_output_path)
                        os.rename(expected_output, txt_output_path)
                    
                    logger.info(f"LibreOffice conversion successful (method 1): {txt_output_path}")
                    return True, txt_output_path, "LibreOffice转换成功"
            except Exception as e:
                logger.warning(f"Error checking method 1 output content: {e}")
                # Fall through to method 2
        
        # Method 1 failed, try method 2: Simple txt conversion without specific filter
        logger.warning(f"Method 1 failed (returncode: {result.returncode}), trying method 2. Stdout: {result.stdout}, stderr: {result.stderr}")
        
        # Clean up any partial output from method 1
        if os.path.exists(expected_output):
            os.remove(expected_output)
        
        cmd2 = [
            'soffice', 
            '--headless',
            '--infilter=writer_pdf_import',
            '--convert-to', 'txt',
            '--outdir', output_dir,
            pdf_path
        ]
        
        logger.info(f"Executing LibreOffice command (method 2): {' '.join(cmd2)}")
        
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        
        if result2.returncode == 0 and os.path.exists(expected_output):
            # Check if method 2 output has content
            try:
                with open(expected_output, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                file_size = os.path.getsize(expected_output)
                logger.info(f"Method 2 output file size: {file_size} bytes, content length: {len(content)} chars")
                
                # Check if content is meaningful (not just BOM and whitespace)
                meaningful_content = content.replace('\ufeff', '').strip()  # Remove BOM and whitespace
                
                if len(meaningful_content) == 0:
                    logger.warning(f"Method 2 also produced only BOM/whitespace (meaningful content length: 0), will try method 3")
                    # Fall through to method 3
                else:
                    # Success with method 2 and has content
                    if expected_output != txt_output_path:
                        if os.path.exists(txt_output_path):
                            os.remove(txt_output_path)
                        os.rename(expected_output, txt_output_path)
                    
                    logger.info(f"LibreOffice conversion successful (method 2): {txt_output_path}")
                    return True, txt_output_path, "LibreOffice转换成功"
            except Exception as e:
                logger.warning(f"Error checking method 2 output content: {e}")
                # Fall through to method 3
        
        # Clean up any partial output from method 2
        if os.path.exists(expected_output):
            os.remove(expected_output)
        
        # Method 3: Try with calc_pdf_import (sometimes different modules handle PDF text better)
        cmd3 = [
            'soffice', 
            '--headless',
            '--infilter=calc_pdf_import',
            '--convert-to', 'txt:Text (encoded):UTF8',
            '--outdir', output_dir,
            pdf_path
        ]
        
        logger.info(f"Executing LibreOffice command (method 3): {' '.join(cmd3)}")
        
        result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=60)
        
        if result3.returncode == 0 and os.path.exists(expected_output):
            # Check if method 3 output has content
            try:
                with open(expected_output, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                file_size = os.path.getsize(expected_output)
                logger.info(f"Method 3 output file size: {file_size} bytes, content length: {len(content)} chars")
                
                # Check if content is meaningful (not just BOM and whitespace)
                meaningful_content = content.replace('\ufeff', '').strip()  # Remove BOM and whitespace
                
                if len(meaningful_content) > 0:
                    # Success with method 3 and has content
                    if expected_output != txt_output_path:
                        if os.path.exists(txt_output_path):
                            os.remove(txt_output_path)
                        os.rename(expected_output, txt_output_path)
                    
                    logger.info(f"LibreOffice conversion successful (method 3): {txt_output_path}")
                    return True, txt_output_path, "LibreOffice转换成功"
                else:
                    logger.warning(f"Method 3 also produced only BOM/whitespace (meaningful content length: 0)")
            except Exception as e:
                logger.warning(f"Error checking method 3 output content: {e}")
        
        # Clean up any partial output from method 3
        if os.path.exists(expected_output):
            os.remove(expected_output)
        
        # Method 4: Try two-step conversion - PDF to ODT first, then ODT to TXT
        # This might bypass the text frame issue
        expected_odt_path = os.path.join(output_dir, f"{input_basename}.odt")
        
        # Step 1: Convert PDF to ODT
        cmd4a = [
            'soffice', 
            '--headless',
            '--infilter=writer_pdf_import',
            '--convert-to', 'odt',
            '--outdir', output_dir,
            pdf_path
        ]
        
        logger.info(f"Executing LibreOffice command (method 4a - PDF to ODT): {' '.join(cmd4a)}")
        
        result4a = subprocess.run(cmd4a, capture_output=True, text=True, timeout=60)
        
        logger.info(f"Method 4a result - returncode: {result4a.returncode}, expected ODT at: {expected_odt_path}, exists: {os.path.exists(expected_odt_path)}")
        
        if result4a.returncode == 0 and os.path.exists(expected_odt_path):
            # Step 2: Convert ODT to TXT
            cmd4b = [
                'soffice', 
                '--headless',
                '--convert-to', 'txt:Text (encoded):UTF8',
                '--outdir', output_dir,
                expected_odt_path
            ]
            
            logger.info(f"Executing LibreOffice command (method 4b - ODT to TXT): {' '.join(cmd4b)}")
            
            result4b = subprocess.run(cmd4b, capture_output=True, text=True, timeout=60)
            
            if result4b.returncode == 0 and os.path.exists(expected_output):
                # Check if method 4 output has content
                try:
                    with open(expected_output, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    file_size = os.path.getsize(expected_output)
                    logger.info(f"Method 4 output file size: {file_size} bytes, content length: {len(content)} chars")
                    
                    # Check if content is meaningful (not just BOM and whitespace)
                    meaningful_content = content.replace('\ufeff', '').strip()  # Remove BOM and whitespace
                    
                    if len(meaningful_content) > 0:
                        # Success with method 4 and has content
                        if expected_output != txt_output_path:
                            if os.path.exists(txt_output_path):
                                os.remove(txt_output_path)
                            os.rename(expected_output, txt_output_path)
                        
                        # Clean up temp ODT file
                        if os.path.exists(expected_odt_path):
                            os.remove(expected_odt_path)
                        
                        logger.info(f"LibreOffice conversion successful (method 4 - two-step): {txt_output_path}")
                        return True, txt_output_path, "LibreOffice转换成功"
                    else:
                        logger.warning(f"Method 4 also produced only BOM/whitespace (meaningful content length: 0)")
                except Exception as e:
                    logger.warning(f"Error checking method 4 output content: {e}")
            
            # Clean up temp ODT file
            if os.path.exists(expected_odt_path):
                os.remove(expected_odt_path)
        
        # All LibreOffice methods failed to extract meaningful content
        # This is a known limitation: LibreOffice imports PDF text into text frames,
        # which are not exported when converting to TXT format
        error_msg = "LibreOffice无法从此PDF提取文本内容。这可能是因为：1) PDF是扫描版（图片型）；2) PDF文本被导入到文本框中，无法导出为纯文本。建议使用PyMuPDF方法。"
        logger.error(f"LibreOffice conversion failed with all methods: {error_msg}")
        logger.debug(f"Detailed errors - Method 1: Code {result.returncode}, Stdout: {result.stdout}, Stderr: {result.stderr}. Method 2: Code {result2.returncode}, Stdout: {result2.stdout}, Stderr: {result2.stderr}. Method 3: Code {result3.returncode}, Stdout: {result3.stdout}, Stderr: {result3.stderr}. Method 4a: Code {result4a.returncode}, Stdout: {result4a.stdout}, Stderr: {result4a.stderr}")
        return False, None, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "LibreOffice conversion timed out after 60 seconds"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"LibreOffice conversion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg

def convert_and_merge_pdfs_to_txt(pdf_paths, merged_txt_path, request_id="", mode='pymupdf'):
    """Converts multiple PDFs to text and merges them into a single TXT file."""
    logger.info(f"Starting convert_and_merge_pdfs_to_txt for {len(pdf_paths)} files. Output: {merged_txt_path}. RequestID: {request_id}")
    
    all_text_content = []
    any_conversion_failed = False
    error_messages = []

    output_folder = os.path.dirname(merged_txt_path)
    os.makedirs(output_folder, exist_ok=True) # Ensure output directory exists

    for i, pdf_path in enumerate(pdf_paths):
        # Create a temporary path for individual txt file to avoid direct write conflicts if convert_pdf_to_txt expects a file path
        # However, convert_pdf_to_txt already writes to a file, so we can read from it, or modify it to return text directly.
        # For simplicity, let's assume convert_pdf_to_txt writes to a temp file, then we read it.
        # A better approach would be for convert_pdf_to_txt to optionally return text content.
        # Given current convert_pdf_to_txt, it writes to txt_output_path. Let's use that.
        
        temp_individual_txt_filename = f"temp_merge_{request_id}_{i}.txt"
        temp_individual_txt_path = os.path.join(output_folder, temp_individual_txt_filename)

        success, actual_txt_path, error_msg = convert_pdf_to_txt(pdf_path, temp_individual_txt_path, mode=mode)
        
        if success and actual_txt_path and os.path.exists(actual_txt_path):
            try:
                with open(actual_txt_path, 'r', encoding='utf-8') as f_temp_txt:
                    all_text_content.append(f_temp_txt.read())
                logger.info(f"Successfully extracted text from {pdf_path} for merging. RequestID: {request_id}")
            except Exception as e_read:
                logger.error(f"Failed to read temporary TXT file {actual_txt_path}: {e_read}. RequestID: {request_id}")
                any_conversion_failed = True
                error_messages.append(f"Error reading text from {os.path.basename(pdf_path)}: {str(e_read)}")
            finally:
                if os.path.exists(actual_txt_path):
                    try: os.remove(actual_txt_path)
                    except Exception as e_del_temp:
                         logger.warning(f"Failed to delete temporary TXT {actual_txt_path}: {e_del_temp}")
        else:
            any_conversion_failed = True
            error_messages.append(error_msg or f"Failed to convert {os.path.basename(pdf_path)} to TXT.")
            logger.error(f"Failed to convert {pdf_path} to TXT for merging. Error: {error_msg}. RequestID: {request_id}")

    if any_conversion_failed and not all_text_content: # All failed, nothing to merge
        full_error_message = "; ".join(error_messages) if error_messages else "One or more PDFs failed to convert to TXT."
        logger.error(f"All PDF to TXT conversions failed for merge. Errors: {full_error_message}. RequestID: {request_id}")
        return False, full_error_message
    
    if any_conversion_failed and all_text_content: # Some failed, but we have some content
        logger.warning(f"Some PDF to TXT conversions failed during merge, but proceeding with available content. Errors: {'; '.join(error_messages)}. RequestID: {request_id}")
        # We will still merge the successful ones.

    if not all_text_content:
        logger.warning(f"No text content extracted from any PDF for merging. RequestID: {request_id}")
        return False, "No text content could be extracted from the provided PDFs."

    try:
        with open(merged_txt_path, 'w', encoding='utf-8') as merged_f:
            merged_f.write("\n\n--- Next File ---\n\n".join(all_text_content)) # Separator between content from different files
        logger.info(f"Successfully merged text from {len(all_text_content)} PDF(s) into {merged_txt_path}. RequestID: {request_id}")
        final_message = "Text successfully merged."
        if any_conversion_failed:
            final_message += " However, some files could not be converted: " + "; ".join(error_messages)
        return True, final_message
    except Exception as e_write_merge:
        logger.error(f"Error writing merged TXT file {merged_txt_path}: {e_write_merge}. RequestID: {request_id}", exc_info=True)
        return False, f"Error writing merged TXT file: {str(e_write_merge)}"

# Example usage (for testing locally)
# if __name__ == '__main__':
#     # Create a dummy PDF for testing
#     # doc = fitz.open() 
#     # page = doc.new_page()
#     # page.insert_text((50, 72), "Hello, PDF page 1 for TXT!\nAnd another line.")
#     # page2 = doc.new_page()
#     # page2.insert_text((50, 72), "This is the second page for TXT extraction.")
#     # doc.save("test_for_txt.pdf")
#     # doc.close()
# 
#     # success, output_file, error_msg = convert_pdf_to_txt("test_for_txt.pdf", "output_from_pdf.txt")
#     # if success:
#     #     print(f"TXT conversion successful: {output_file}")
#     #     with open(output_file, 'r', encoding='utf-8') as f_read:
#     #         print("--- Content ---")
#     #         print(f_read.read())
#     # else:
#     #     print(f"TXT conversion failed: {error_msg}") 