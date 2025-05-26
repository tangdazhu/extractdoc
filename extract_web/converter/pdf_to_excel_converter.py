import pdfplumber
import openpyxl
import os
import logging

logger = logging.getLogger('converter')

def convert_pdf_to_excel(input_pdf_path, output_excel_path):
    """
    Converts tables from a PDF file to an Excel file.
    Each table in the PDF will be a sheet in the Excel file.

    Args:
        input_pdf_path (str): Path to the input PDF file.
        output_excel_path (str): Path to save the output Excel file.

    Returns:
        tuple: (success: bool, actual_output_path: str or None, error_message: str or None)
    """
    try:
        logger.info(f"Starting PDF to Excel conversion: {input_pdf_path} -> {output_excel_path}")

        if not os.path.exists(input_pdf_path):
            return False, None, "Input PDF file not found."

        workbook = openpyxl.Workbook()
        # Remove default sheet created by openpyxl
        if "Sheet" in workbook.sheetnames:
            default_sheet = workbook["Sheet"]
            workbook.remove(default_sheet)
        
        has_tables = False
        with pdfplumber.open(input_pdf_path) as pdf:
            if not pdf.pages:
                return False, None, "PDF has no pages."

            for i, page in enumerate(pdf.pages):
                # Extract tables from the current page
                # page.extract_tables() returns a list of tables,
                # where each table is a list of lists (rows and cells)
                tables_on_page = page.extract_tables()
                
                if tables_on_page:
                    has_tables = True
                    for table_idx, table_data in enumerate(tables_on_page):
                        # Create a new sheet for each table
                        # Sheet names have a max length and restricted characters, be careful
                        sheet_title = f"Page{i+1}_Table{table_idx+1}"
                        # Truncate sheet title if too long (Excel limit is 31 chars)
                        if len(sheet_title) > 31:
                            sheet_title = sheet_title[:31]
                        
                        # Ensure sheet title is unique if truncated or many tables
                        original_sheet_title = sheet_title
                        counter = 1
                        while sheet_title in workbook.sheetnames:
                            suffix = f"_{counter}"
                            if len(original_sheet_title) + len(suffix) > 31:
                                sheet_title = original_sheet_title[:31-len(suffix)] + suffix
                            else:
                                sheet_title = original_sheet_title + suffix
                            counter += 1
                            if counter > 100: # Safety break
                                return False, None, "Too many tables with similar names, cannot create unique sheet names."


                        sheet = workbook.create_sheet(title=sheet_title)
                        
                        for row_data in table_data:
                            # pdfplumber might return None for cells if they are merged or empty in a complex way
                            # Replace None with empty string for openpyxl
                            cleaned_row = [str(cell) if cell is not None else "" for cell in row_data]
                            sheet.append(cleaned_row)
                        logger.info(f"Added table to sheet: {sheet_title}")
                else:
                    logger.info(f"No tables found on page {i+1}")

        if not has_tables:
            logger.warning(f"No tables found in the PDF: {input_pdf_path}")
            # Decide if this is an error or just an empty Excel file outcome
            # For now, let's create an empty Excel file and return success, but with a message.
            # Or, return False, None, "No tables found in the PDF to convert." - User might expect tables.
            # Let's return an error as this converter is specifically for table extraction.
            return False, None, "未在PDF中找到可供转换的表格。"

        workbook.save(output_excel_path)
        logger.info(f"Successfully converted PDF to Excel: {output_excel_path}")
        return True, output_excel_path, None

    except Exception as e:
        logger.error(f"Error during PDF to Excel conversion for '{input_pdf_path}': {e}", exc_info=True)
        return False, None, f"PDF转Excel失败: {str(e)}"

if __name__ == '__main__':
    # Create dummy PDF and test (requires reportlab for dummy creation)
    # This part is for standalone testing and might require additional setup/libraries
    # For now, just provide a simple test call structure

    # To test this, you'd need a sample PDF file.
    # Example:
    # success, out_path, err = convert_pdf_to_excel("sample.pdf", "output.xlsx")
    # if success:
    #     print(f"Conversion successful: {out_path}")
    # else:
    #     print(f"Conversion failed: {err}")
    pass 