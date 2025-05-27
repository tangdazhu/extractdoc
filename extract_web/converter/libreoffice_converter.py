import subprocess
import os
import shutil # For moving file if needed
import logging

logger = logging.getLogger('converter')

def convert_to_pdf(input_path, output_dir):
    """
    Converts a document to PDF using LibreOffice (soffice).

    Args:
        input_path (str): Absolute path to the input document.
        output_dir (str): Absolute path to the directory where the PDF should be saved.

    Returns:
        tuple: (bool_success, pdf_output_path_or_error_msg, original_pdf_filename_or_None)
               - bool_success: True if conversion was successful, False otherwise.
               - pdf_output_path_or_error_msg: Absolute path to the converted PDF if successful,
                                               or an error message string if failed.
               - original_pdf_filename_or_None: The original filename of the PDF as created by LibreOffice.
    """
    if not os.path.exists(input_path):
        return False, f"Input file not found: {input_path}", None
    if not os.path.isdir(output_dir):
        return False, f"Output directory not found: {output_dir}", None

    input_filename_stem = os.path.splitext(os.path.basename(input_path))[0]
    expected_pdf_filename = f"{input_filename_stem}.pdf"
    potentially_converted_pdf_path = os.path.join(output_dir, expected_pdf_filename)

    if os.path.exists(potentially_converted_pdf_path):
        try:
            os.remove(potentially_converted_pdf_path)
            logger.debug(f"Removed existing file before conversion: {potentially_converted_pdf_path}")
        except OSError as e:
            logger.error(f"Error removing existing file {potentially_converted_pdf_path}: {e}")
            return False, f"Error removing existing file {potentially_converted_pdf_path}: {e}", None
            
    command = [
        'soffice',
        '--headless',
        '--convert-to', 'pdf',
        '--outdir', output_dir,
        input_path
    ]
    
    logger.info(f"Executing LibreOffice command: {' '.join(command)}")
    
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)

        if process.returncode == 0:
            if os.path.exists(potentially_converted_pdf_path):
                logger.info(f"LibreOffice successfully converted '{input_path}' to '{potentially_converted_pdf_path}'")
                return True, potentially_converted_pdf_path, expected_pdf_filename
            else:
                error_message = f"LibreOffice exited successfully (code 0) but the expected output PDF was not found: {potentially_converted_pdf_path}. stdout: {process.stdout}, stderr: {process.stderr}"
                logger.error(error_message)
                return False, error_message, None
        else:
            error_message = f"LibreOffice conversion failed for '{input_path}'. Return code: {process.returncode}. stdout: {process.stdout}, stderr: {process.stderr}"
            logger.error(error_message)
            return False, error_message, None
            
    except FileNotFoundError:
        error_msg = "'soffice' command not found. Please ensure LibreOffice is installed and in your system's PATH."
        logger.error(error_msg)
        return False, error_msg, None
    except subprocess.TimeoutExpired:
        error_msg = f"LibreOffice conversion timed out for '{input_path}'."
        logger.error(error_msg)
        return False, error_msg, None
    except Exception as e:
        error_msg = f"An unexpected error occurred during LibreOffice conversion of '{input_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

if __name__ == '__main__':
    # Example usage (for testing this script directly)
    # Create dummy files and dirs for testing
    test_output_dir = './test_output_lo'
    test_input_file = './test_input_lo.docx'

    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)
    
    # Create a simple DOCX file for testing if it doesn't exist
    if not os.path.exists(test_input_file):
        try:
            from docx import Document as DocxDocument # Use a different alias to avoid confusion if Document is used elsewhere
            doc = DocxDocument()
            doc.add_paragraph("This is a test docx for LibreOffice conversion created by script.")
            doc.save(test_input_file)
            logger.info(f"Created dummy test file: {test_input_file}")
        except ImportError:
            logger.warning("python-docx library is not installed. Cannot create a dummy .docx file for testing. Please create it manually.")
            # As a very basic fallback, create a text file that soffice might still process or error out on
            with open(test_input_file, 'w') as f:
                f.write("This is a test docx for LibreOffice conversion (plain text).")
        except Exception as e_create:
            logger.error(f"Failed to create dummy test file {test_input_file}: {e_create}")

    print("Testing LibreOffice converter...")
    if os.path.exists(test_input_file): # Only test if input file exists
        success, result_path_or_msg, _ = convert_to_pdf(os.path.abspath(test_input_file), os.path.abspath(test_output_dir))
        
        if success:
            print(f"Conversion successful. PDF at: {result_path_or_msg}")
            # Optional: Clean up test files by uncommenting below
            # print(f"To cleanup, manually remove: {test_input_file}, {result_path_or_msg}, and directory {test_output_dir}")
            # os.remove(test_input_file)
            # os.remove(result_path_or_msg)
            # shutil.rmtree(test_output_dir)
        else:
            print(f"Conversion failed. Error: {result_path_or_msg}")
    else:
        print(f"Skipping test, input file {test_input_file} does not exist or could not be created.") 