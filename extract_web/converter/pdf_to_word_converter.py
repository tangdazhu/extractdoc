from pdf2docx import Converter
import os
import logging

logger = logging.getLogger('converter')

def convert_pdf_to_word(input_pdf_path, output_docx_path):
    """
    Converts a PDF file to a DOCX file.

    Args:
        input_pdf_path (str): Path to the input PDF file.
        output_docx_path (str): Path to save the output DOCX file.

    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        logger.info(f"Starting PDF to Word conversion: {input_pdf_path} -> {output_docx_path}")

        if not os.path.exists(input_pdf_path):
            return False, None, "Input PDF file not found."

        # Create a Converter object
        cv = Converter(input_pdf_path)
        
        # Convert to Word (output_docx_path specifies the output file)
        # The pages argument can be used to specify a range of pages, e.g., pages=[0, 1] for first two pages.
        # None means all pages.
        cv.convert(output_docx_path, start=0, end=None)
        
        # Close the converter object
        cv.close()

        if os.path.exists(output_docx_path):
            logger.info(f"Successfully converted PDF to Word: {output_docx_path}")
            return True, output_docx_path, None
        else:
            # This case should ideally not be reached if convert() doesn't raise an error
            # but pdf2docx might have peculiarities.
            error_msg = "Conversion completed but output DOCX file not found."
            logger.error(error_msg)
            return False, None, error_msg

    except Exception as e:
        logger.error(f"Error during PDF to Word conversion for '{input_pdf_path}': {e}", exc_info=True)
        return False, None, f"PDF转Word失败: {str(e)}"

if __name__ == '__main__':
    # For standalone testing:
    # You'd need a sample.pdf in the same directory as this script.
    # success, out_path, err = convert_pdf_to_word("sample.pdf", "output.docx")
    # if success:
    #     print(f"Conversion successful: {out_path}")
    # else:
    #     print(f"Conversion failed: {err}")
    pass 