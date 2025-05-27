import fitz  # PyMuPDF
import os
import logging

logger = logging.getLogger(__name__)

def convert_pdf_to_txt(pdf_path, txt_output_path):
    """
    Converts a PDF file to a TXT file by extracting text content.
    Requires PyMuPDF (fitz).
    Run: pip install PyMuPDF
    """
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
        
        logger.info(f"Successfully extracted text from {pdf_path} to {txt_output_path}")
        return True, txt_output_path, None
        
    except Exception as e:
        logger.error(f"Error during PDF to TXT conversion for {pdf_path}: {e}", exc_info=True)
        return False, None, f"Error during PDF to TXT conversion: {str(e)}"

def convert_and_merge_pdfs_to_txt(pdf_paths, merged_txt_path, request_id=""):
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

        success, actual_txt_path, error_msg = convert_pdf_to_txt(pdf_path, temp_individual_txt_path)
        
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