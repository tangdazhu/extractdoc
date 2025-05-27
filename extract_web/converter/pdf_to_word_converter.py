from pdf2docx import Converter
import os
import logging
import subprocess
import tempfile
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

logger = logging.getLogger('converter')

def convert_pdf_to_word(input_pdf_path, output_docx_path, mode='pdf2docx'):
    """
    Converts a PDF file to a DOCX file.

    Args:
        input_pdf_path (str): Path to the input PDF file.
        output_docx_path (str): Path to save the output DOCX file.
        mode (str): Conversion mode - 'pdf2docx' (default) or 'libreoffice'

    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        logger.info(f"Starting PDF to Word conversion using {mode} mode: {input_pdf_path} -> {output_docx_path}")

        if not os.path.exists(input_pdf_path):
            return False, None, "Input PDF file not found."

        if mode == 'libreoffice':
            return _convert_pdf_to_word_libreoffice(input_pdf_path, output_docx_path)
        else:  # Default to pdf2docx mode
            return _convert_pdf_to_word_pdf2docx(input_pdf_path, output_docx_path)

    except Exception as e:
        logger.error(f"Error during PDF to Word conversion for '{input_pdf_path}' using {mode}: {e}", exc_info=True)
        return False, None, f"PDF转Word失败: {str(e)}"

def _convert_pdf_to_word_pdf2docx(input_pdf_path, output_docx_path):
    """Convert PDF to Word using pdf2docx library."""
    try:
        # Create a Converter object
        cv = Converter(input_pdf_path)
        
        # Convert to Word (output_docx_path specifies the output file)
        cv.convert(output_docx_path, start=0, end=None)
        
        # Close the converter object
        cv.close()

        if os.path.exists(output_docx_path):
            logger.info(f"Successfully converted PDF to Word using pdf2docx: {output_docx_path}")
            return True, output_docx_path, None
        else:
            error_msg = "pdf2docx conversion completed but output DOCX file not found."
            logger.error(error_msg)
            return False, None, error_msg

    except Exception as e:
        logger.error(f"Error during pdf2docx conversion: {e}", exc_info=True)
        return False, None, f"pdf2docx转换失败: {str(e)}"

def _convert_pdf_to_word_libreoffice(input_pdf_path, output_docx_path):
    """Convert PDF to Word using LibreOffice."""
    try:
        output_dir = os.path.dirname(output_docx_path)
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Using LibreOffice to convert {input_pdf_path} to {output_docx_path}")
        
        cmd = [
            'soffice', 
            '--headless',
            '--infilter=writer_pdf_import',
            '--convert-to', 'docx',
            '--outdir', output_dir,
            input_pdf_path
        ]
        
        logger.info(f"Executing LibreOffice command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # LibreOffice creates output with the same base name as input but different extension
            input_basename = os.path.splitext(os.path.basename(input_pdf_path))[0]
            expected_output = os.path.join(output_dir, f"{input_basename}.docx")
            
            if os.path.exists(expected_output):
                # Rename to desired output path if different
                if expected_output != output_docx_path:
                    if os.path.exists(output_docx_path):
                        os.remove(output_docx_path)
                    os.rename(expected_output, output_docx_path)
                
                logger.info(f"LibreOffice conversion successful: {output_docx_path}")
                return True, output_docx_path, "LibreOffice转换成功"
            else:
                error_msg = f"LibreOffice conversion error: Expected output {expected_output} not found. Stdout: {result.stdout}, stderr: {result.stderr}"
                logger.error(error_msg)
                return False, None, error_msg
        else:
            error_msg = f"LibreOffice process failed with return code {result.returncode}. Stdout: {result.stdout}, stderr: {result.stderr}"
            logger.error(error_msg)
            return False, None, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "LibreOffice conversion timed out after 60 seconds"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"LibreOffice conversion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg

def _append_document(source_doc, target_doc):
    """Appends the content of source_doc to target_doc."""
    for element in source_doc.element.body:
        target_doc.element.body.append(element)
    # Add a page break after appending, if desired
    # target_doc.add_page_break()

def convert_and_merge_pdfs_to_docx(pdf_paths, merged_docx_path, request_id="", mode='pdf2docx'):
    """Converts multiple PDFs to DOCX and merges them into a single DOCX file."""
    logger.info(f"Starting convert_and_merge_pdfs_to_docx for {len(pdf_paths)} files. Output: {merged_docx_path}. RequestID: {request_id}")
    
    temp_docx_files = []
    any_conversion_failed = False
    conversion_errors = []
    
    output_folder = os.path.dirname(merged_docx_path)
    os.makedirs(output_folder, exist_ok=True)

    for i, pdf_path in enumerate(pdf_paths):
        temp_docx_filename = f"temp_merge_{request_id}_{i}.docx"
        temp_docx_path = os.path.join(output_folder, temp_docx_filename)
        
        success, actual_output_path, error_msg = convert_pdf_to_word(pdf_path, temp_docx_path, mode=mode)
        
        if success and actual_output_path and os.path.exists(actual_output_path):
            temp_docx_files.append(actual_output_path)
            logger.info(f"Successfully converted {pdf_path} to {actual_output_path} for merging. RequestID: {request_id}")
        else:
            any_conversion_failed = True
            conversion_errors.append(error_msg or f"Failed to convert {os.path.basename(pdf_path)}")
            logger.error(f"Failed to convert {pdf_path} to DOCX for merging. Error: {error_msg}. RequestID: {request_id}")

    if not temp_docx_files:
        logger.error(f"No PDF could be converted to DOCX for merging. Errors: {"; ".join(conversion_errors)}. RequestID: {request_id}")
        return False, ("; ".join(conversion_errors) if conversion_errors else "No PDF files could be converted to DOCX.")

    # Start merging
    try:
        if not temp_docx_files:
            return False, "No successful DOCX conversions to merge."

        # Use the first converted docx as the base for the merged document
        merged_doc = Document(temp_docx_files[0])
        
        # Append subsequent documents
        for i in range(1, len(temp_docx_files)):
            # Add a section break before appending the next document to better preserve formatting/layout
            # merged_doc.add_section() # This might add too much separation, page break might be better if sections are not distinct.
            # Or, just a simple page break if preferred for less distinct separation:
            if i > 0 : # Add page break before appending new content, but not before the very first doc.
                merged_doc.add_page_break()
            
            sub_doc = Document(temp_docx_files[i])
            _append_document(sub_doc, merged_doc) # Using the local helper for merging
            logger.info(f"Appended {temp_docx_files[i]} to merged document. RequestID: {request_id}")

        merged_doc.save(merged_docx_path)
        logger.info(f"Successfully merged {len(temp_docx_files)} DOCX files into {merged_docx_path}. RequestID: {request_id}")
        
        final_message = f"Successfully merged {len(temp_docx_files)} PDF(s) into a DOCX file."
        if any_conversion_failed:
            final_message += f" However, {len(conversion_errors)} PDF(s) failed to convert: {"; ".join(conversion_errors)}"
        return True, final_message

    except Exception as e_merge:
        logger.error(f"Error during DOCX merge process for {merged_docx_path}: {e_merge}. RequestID: {request_id}", exc_info=True)
        return False, f"Error merging DOCX files: {str(e_merge)}"
    finally:
        # Clean up temporary DOCX files
        for temp_file in temp_docx_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}. RequestID: {request_id}")
                except Exception as e_clean:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {e_clean}. RequestID: {request_id}")

if __name__ == '__main__':
    # For standalone testing:
    # You'd need a sample.pdf in the same directory as this script.
    # success, out_path, err = convert_pdf_to_word("sample.pdf", "output.docx")
    # if success:
    #     print(f"Conversion successful: {out_path}")
    # else:
    #     print(f"Conversion failed: {err}")
    pass 