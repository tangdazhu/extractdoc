import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches
import os
import logging # Added for detailed logging

logger = logging.getLogger(__name__) # Get a logger for this module

# Helper function to get slide dimensions
def get_slide_dimensions_in_inches(prs):
    """Returns the slide width and height as float values in Inches."""
    # EMU (English Metric Units) per inch is 914400
    slide_width_inches = prs.slide_width / 914400.0
    slide_height_inches = prs.slide_height / 914400.0
    logger.debug(f"Calculated slide dimensions: Width={slide_width_inches:.2f} in, Height={slide_height_inches:.2f} in")
    return slide_width_inches, slide_height_inches

def convert_pdf_to_ppt(pdf_path, ppt_output_path):
    """
    Converts a PDF file to a PPTX file, with each PDF page as an image on a slide.
    Requires PyMuPDF (fitz) and python-pptx.
    Run: pip install PyMuPDF python-pptx Pillow
    """
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        # Create a new PowerPoint presentation
        prs = Presentation()
        # Get slide dimensions as float values in inches
        slide_width_in, slide_height_in = get_slide_dimensions_in_inches(prs)

        temp_image_paths = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # Render page to an image (pixmap)
            # Higher DPI improves quality but increases file size
            pix = page.get_pixmap(dpi=150) 
            
            # Save the image temporarily
            temp_image_filename = f"temp_page_{page_num}.png"
            temp_image_path = os.path.join(os.path.dirname(ppt_output_path), temp_image_filename)
            logger.debug(f"Attempting to save page {page_num} image to: {temp_image_path}")
            pix.save(temp_image_path)
            temp_image_paths.append(temp_image_path)

            if not os.path.exists(temp_image_path) or os.path.getsize(temp_image_path) == 0:
                logger.error(f"Temporary image {temp_image_path} was not created or is empty for page {page_num}.")
                # Optionally, decide if this should halt the process or just skip this page
                # For now, it will likely result in an error later or a blank slide part if add_picture fails.

            logger.debug(f"Temporary image for page {page_num} saved at {temp_image_path}, size: {os.path.getsize(temp_image_path) if os.path.exists(temp_image_path) else 'N/A'}")
            
            # Add a blank slide layout (usually layout 6 is blank)
            blank_slide_layout = prs.slide_layouts[5] # Or 6, depending on default template
            slide = prs.slides.add_slide(blank_slide_layout)
            
            # --- Image placement logic ---
            img_width_px = pix.width
            img_height_px = pix.height

            # Calculate aspect ratios
            img_aspect_ratio = img_width_px / img_height_px
            slide_aspect_ratio = slide_width_in / slide_height_in # Use float values for calculation

            # Determine dimensions for the image on the slide to maintain aspect ratio
            if img_aspect_ratio > slide_aspect_ratio:
                # Image is wider or less tall than slide: fit to width
                display_width_in = slide_width_in
                display_height_in = display_width_in / img_aspect_ratio
            else:
                # Image is taller or less wide than slide: fit to height
                display_height_in = slide_height_in
                display_width_in = display_height_in * img_aspect_ratio
            
            # Center the image (calculations are with float inch values)
            left_in = (slide_width_in - display_width_in) / 2
            top_in = (slide_height_in - display_height_in) / 2

            # Add the image to the slide
            logger.debug(f"Adding picture to slide {page_num}: path={temp_image_path}, L={left_in:.2f}in, T={top_in:.2f}in, W={display_width_in:.2f}in, H={display_height_in:.2f}in")
            if display_width_in <= 0 or display_height_in <= 0:
                logger.warning(f"Calculated image dimensions for slide {page_num} are zero or negative (W:{display_width_in:.2f}, H:{display_height_in:.2f}). Skipping add_picture.")
            else:
                try:
                    slide.shapes.add_picture(temp_image_path, 
                                             Inches(left_in), Inches(top_in),
                                             width=Inches(display_width_in), height=Inches(display_height_in))
                    logger.debug(f"Successfully added picture for page {page_num} to slide.")
                except Exception as e_add_pic:
                    logger.error(f"Error adding picture for page {page_num} to slide: {e_add_pic}", exc_info=True)

        pdf_document.close()
        logger.debug(f"Attempting to save final PPTX to: {ppt_output_path}")
        prs.save(ppt_output_path)
        logger.info(f"PPTX file saved successfully to {ppt_output_path}")

        # Clean up temporary image files
        for temp_path in temp_image_paths:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return True, ppt_output_path, None
        
    except Exception as e:
        # Clean up any temp files created before the error
        if 'temp_image_paths' in locals():
            for temp_path in temp_image_paths:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass # Ignore cleanup errors if main conversion failed
        return False, None, f"Error during PDF to PPT conversion: {str(e)}"

# Example usage (for testing locally, not part of the Django view)
# if __name__ == '__main__':
#     # Create a dummy PDF for testing if you don't have one
#     # import fitz
#     # doc = fitz.open()
#     # page = doc.new_page()
#     # page.insert_text((50, 72), "Hello, PDF page 1!")
#     # page = doc.new_page()
#     # page.insert_text((50, 72), "This is page 2.")
#     # doc.save("test.pdf")
#     # doc.close()
#
#     success, output_path, error_msg = convert_pdf_to_ppt("test.pdf", "test_output.pptx")
#     if success:
#         print(f"Conversion successful: {output_path}")
#     else:
#         print(f"Conversion failed: {error_msg}") 