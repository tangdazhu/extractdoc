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