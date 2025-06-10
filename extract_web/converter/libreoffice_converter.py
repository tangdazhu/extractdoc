import subprocess
import os
import shutil  # For moving file if needed
import logging
import re  # Add re import at module level

logger = logging.getLogger("converter")


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
            logger.debug(
                f"Removed existing file before conversion: {potentially_converted_pdf_path}"
            )
        except OSError as e:
            logger.error(
                f"Error removing existing file {potentially_converted_pdf_path}: {e}"
            )
            return (
                False,
                f"Error removing existing file {potentially_converted_pdf_path}: {e}",
                None,
            )

    command = [
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        input_path,
    ]

    logger.info(f"Executing LibreOffice command: {' '.join(command)}")

    try:
        process = subprocess.run(
            command, capture_output=True, text=True, timeout=120, check=False
        )

        if process.returncode == 0:
            if os.path.exists(potentially_converted_pdf_path):
                logger.info(
                    f"LibreOffice successfully converted '{input_path}' to '{potentially_converted_pdf_path}'"
                )
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


def convert_to_pptx(input_path, output_dir, skip_default_content=False):
    """
    Converts a document to PPTX using python-pptx library (primary) or LibreOffice (fallback).

    Args:
        input_path (str): Absolute path to the input document (e.g., a DOCX file).
        output_dir (str): Absolute path to the directory where the PPTX should be saved.
        skip_default_content (bool): If True, skip adding default "文档内容" slide when no content is found.

    Returns:
        tuple: (bool_success, pptx_output_path_or_error_msg, original_pptx_filename_or_None)
               - bool_success: True if conversion was successful, False otherwise.
               - pptx_output_path_or_error_msg: Absolute path to the converted PPTX if successful,
                                               or an error message string if failed.
               - original_pptx_filename_or_None: The original filename of the PPTX as created by LibreOffice.
    """
    print(f"!!! CONVERT_TO_PPTX CALLED !!! {input_path}")  # Force visible log
    logger.error(
        f"FORCE LOG: convert_to_pptx called with {input_path}"
    )  # Force error level log

    if not os.path.exists(input_path):
        return False, f"Input file not found: {input_path}", None
    if not os.path.isdir(output_dir):
        return (
            False,
            f"Output directory not found: {output_dir}",
            None,
        )  # Try Python-based PPTX creation first (more reliable for DOCX to PPTX)
    logger.info(
        f"Attempting PPTX creation using python-pptx for: {input_path}"
    )  # Check if this is a PPT-derived file (should skip default content)
    input_filename = os.path.basename(input_path)
    filename_based_skip = (
        "ppt" in input_filename.lower()
        or "powerpoint" in input_filename.lower()
        or input_filename.lower().endswith((".ppt", ".pptx"))
    )

    # Use parameter if explicitly passed, otherwise use filename-based detection
    final_skip_default_content = skip_default_content or filename_based_skip

    logger.error(
        f"FORCE LOG: skip_default_content param = {skip_default_content}, filename_based = {filename_based_skip}, final = {final_skip_default_content} for filename {input_filename}"
    )
    print(
        f"!!! SKIP_DEFAULT_CONTENT = {final_skip_default_content} for {input_filename} !!!"
    )

    success, result, filename = create_pptx_from_docx(
        input_path, output_dir, final_skip_default_content
    )

    if success:
        return success, result, filename

    # Log the python-pptx failure but continue to LibreOffice fallback
    logger.warning(f"Python-pptx method failed: {result}")

    # LibreOffice fallback - but DOCX to PPTX conversion may not be supported
    logger.info("Attempting LibreOffice fallback for DOCX to PPTX conversion...")

    input_filename_stem = os.path.splitext(os.path.basename(input_path))[0]
    expected_pptx_filename = f"{input_filename_stem}.pptx"
    potentially_converted_pptx_path = os.path.join(output_dir, expected_pptx_filename)

    if os.path.exists(potentially_converted_pptx_path):
        try:
            os.remove(potentially_converted_pptx_path)
            logger.debug(
                f"Removed existing file before conversion: {potentially_converted_pptx_path}"
            )
        except OSError as e:
            logger.error(
                f"Error removing existing file {potentially_converted_pptx_path}: {e}"
            )
            return (
                False,
                f"Error removing existing file {potentially_converted_pptx_path}: {e}",
                None,
            )

    # Try LibreOffice conversion
    command = [
        "soffice",
        "--headless",
        "--convert-to",
        "pptx",
        "--outdir",
        output_dir,
        input_path,
    ]

    logger.info(f"LibreOffice fallback command: {' '.join(command)}")

    try:
        process = subprocess.run(
            command, capture_output=True, text=True, timeout=120, check=False
        )

        if process.returncode == 0:
            if os.path.exists(potentially_converted_pptx_path):
                logger.info(
                    f"LibreOffice successfully converted '{input_path}' to '{potentially_converted_pptx_path}'"
                )
                return True, potentially_converted_pptx_path, expected_pptx_filename
            else:
                error_message = f"LibreOffice exited successfully (code 0) but the expected output PPTX was not found: {potentially_converted_pptx_path}. stdout: {process.stdout}, stderr: {process.stderr}"
                logger.error(error_message)
                # Since both methods failed, return the more informative python-pptx error
                return (
                    False,
                    f"PPTX conversion failed. Python-pptx error: {result}. LibreOffice error: {process.stderr}",
                    None,
                )
        else:
            error_message = f"LibreOffice conversion to PPTX failed for '{input_path}'. Return code: {process.returncode}. stdout: {process.stdout}, stderr: {process.stderr}"
            logger.error(error_message)
            # Return the more informative python-pptx error since LibreOffice also failed
            return (
                False,
                f"PPTX conversion failed. Python-pptx error: {result}. LibreOffice error: {process.stderr}",
                None,
            )

    except FileNotFoundError:
        error_msg = "'soffice' command not found. Please ensure LibreOffice is installed and in your system's PATH."
        logger.error(error_msg)
        return (
            False,
            f"PPTX conversion failed. Python-pptx error: {result}. LibreOffice not found: {error_msg}",
            None,
        )
    except subprocess.TimeoutExpired:
        error_msg = f"LibreOffice conversion to PPTX timed out for '{input_path}'."
        logger.error(error_msg)
        return (
            False,
            f"PPTX conversion failed. Python-pptx error: {result}. LibreOffice timeout: {error_msg}",
            None,
        )
    except Exception as e:
        error_msg = f"An unexpected error occurred during LibreOffice conversion of '{input_path}' to PPTX: {e}"
        logger.error(error_msg, exc_info=True)
        return (
            False,
            f"PPTX conversion failed. Python-pptx error: {result}. LibreOffice error: {error_msg}",
            None,
        )


def create_pptx_from_docx(docx_path, output_dir, skip_default_content=False):
    """
    Creates a PPTX file from a DOCX file using python-pptx library.
    Reads tables and text from DOCX and creates slides in PPTX with improved formatting.
    Each image's content is kept on a single slide to preserve the original structure.

    Args:
        docx_path (str): Path to the input DOCX file
        output_dir (str): Directory where PPTX should be saved
        skip_default_content (bool): If True, skip adding default "文档内容" slide when no content is found

    Returns:
        tuple: (bool_success, pptx_output_path_or_error_msg, original_pptx_filename_or_None)
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.enum.text import PP_ALIGN
        from pptx.dml.color import RGBColor
        from docx import Document

        # Read DOCX content
        doc = Document(docx_path)

        # Create presentation
        prs = Presentation()

        # Get filename stem for output
        input_filename_stem = os.path.splitext(os.path.basename(docx_path))[0]
        expected_pptx_filename = f"{input_filename_stem}.pptx"
        output_path = os.path.join(output_dir, expected_pptx_filename)

        slide_count = 0

        # Process tables first (each table gets its own slide)
        for table in doc.tables:
            slide_layout = prs.slide_layouts[5]  # Blank layout
            slide = prs.slides.add_slide(slide_layout)
            slide_count += 1

            # Add title
            title_shape = slide.shapes.title
            if title_shape:
                title_shape.text = f"表格 {slide_count}"

            # Calculate table dimensions
            rows = len(table.rows)
            cols = len(table.rows[0].cells) if rows > 0 else 0

            if rows > 0 and cols > 0:
                # Add table to slide
                left = Inches(1)
                top = Inches(1.5)
                width = Inches(8)
                height = Inches(4)

                ppt_table = slide.shapes.add_table(
                    rows, cols, left, top, width, height
                ).table

                # Copy data from DOCX table to PPT table
                for row_idx, row in enumerate(table.rows):
                    for col_idx, cell in enumerate(row.cells):
                        if row_idx < len(ppt_table.rows) and col_idx < len(
                            ppt_table.rows[row_idx].cells
                        ):
                            ppt_cell = ppt_table.rows[row_idx].cells[col_idx]
                            ppt_cell.text = cell.text.strip()

                            # Format header row
                            if row_idx == 0:
                                for paragraph in ppt_cell.text_frame.paragraphs:
                                    for run in paragraph.runs:
                                        run.font.bold = True
                                        run.font.size = Pt(
                                            12
                                        )  # Collect all paragraphs (skip for PPT files when skipping default content)
        paragraphs = []
        if (
            not skip_default_content
        ):  # Only process paragraphs if not skipping default content
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)

        logger.info(
            f"skip_default_content: {skip_default_content}, found {len(paragraphs)} paragraphs"
        )

        # Create a single content slide for all text content (preserving original structure)
        if paragraphs:
            # Create one slide for all content
            slide_layout = prs.slide_layouts[1]  # Title and content layout
            slide = prs.slides.add_slide(slide_layout)

            # Set title - use first paragraph if it looks like a title, otherwise use generic title
            title_shape = slide.shapes.title
            title_text = "Content"
            content_start_idx = 0

            if title_shape:
                first_para = paragraphs[0]
                # Check if first paragraph looks like a title
                if len(first_para) <= 50 and (
                    any(
                        keyword in first_para
                        for keyword in ["目的", "Content", "Whitepaper"]
                    )
                    or re.match(r"^\d+[.、]", first_para)
                    or first_para.isupper()
                ):
                    title_text = first_para
                    content_start_idx = 1
                title_shape.text = title_text

            # Set content - put ALL remaining content on this single slide
            content_shape = slide.placeholders[1]
            if content_shape:
                text_frame = content_shape.text_frame
                text_frame.clear()

                # Add all paragraphs to the single slide
                content_paragraphs = paragraphs[content_start_idx:]

                for i, para_text in enumerate(content_paragraphs):
                    if i == 0:
                        p = text_frame.paragraphs[0]
                    else:
                        p = text_frame.add_paragraph()

                    p.text = para_text

                    # Apply formatting based on content patterns
                    if re.match(
                        r"^\d+[.、]\s*\S", para_text
                    ):  # Numbered sections (1. 2. 3.)
                        p.font.bold = True
                        p.font.size = Pt(16)
                        p.font.color.rgb = RGBColor(
                            0, 51, 102
                        )  # Dark blue for main sections
                    elif para_text.startswith(("•", "·", "-", "*")):  # Bullet points
                        p.level = 1  # Indent bullet points
                        p.font.size = Pt(12)
                    elif (
                        any(
                            keyword in para_text
                            for keyword in [
                                "开发",
                                "技术",
                                "平台",
                                "框架",
                                "选型",
                                "架构",
                                "安全",
                                "评估",
                            ]
                        )
                        and len(para_text) <= 80
                    ):
                        # Technical terms that might be headings
                        p.font.bold = True
                        p.font.size = Pt(14)
                        p.font.color.rgb = RGBColor(
                            51, 51, 153
                        )  # Medium blue for sub-headings
                    elif len(para_text) <= 30:  # Short text might be headings
                        p.font.bold = True
                        p.font.size = Pt(13)
                    else:
                        # Regular content
                        p.font.size = Pt(11)

                # Adjust text frame to fit more content
                text_frame.margin_bottom = Inches(0.1)
                text_frame.margin_top = Inches(0.1)
                text_frame.margin_left = Inches(0.1)
                text_frame.margin_right = Inches(
                    0.1
                )  # If no paragraphs and not skipping default content, create a simple slide
        elif (
            len(prs.slides) == slide_count and not skip_default_content
        ):  # Only table slides exist or no content at all
            logger.info(
                f"Adding default content slide because: slides={len(prs.slides)}, slide_count={slide_count}, skip_default_content={skip_default_content}"
            )
            slide_layout = prs.slide_layouts[1]  # Title and content layout
            slide = prs.slides.add_slide(slide_layout)

            title_shape = slide.shapes.title
            content_shape = slide.placeholders[1]

            if title_shape:
                title_shape.text = "文档内容"
            if content_shape:
                content_shape.text = "从图片中提取的文本内容"
        else:
            logger.info(
                f"Skipping default content slide because: slides={len(prs.slides)}, slide_count={slide_count}, skip_default_content={skip_default_content}"
            )

        # Save the presentation
        prs.save(output_path)
        logger.info(f"Successfully created PPTX using python-pptx: {output_path}")
        return True, output_path, expected_pptx_filename

    except ImportError as e:
        error_msg = f"Required libraries not available for PPTX creation: {e}. Please install python-pptx and python-docx."
        logger.error(error_msg)
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Error creating PPTX from DOCX '{docx_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None


if __name__ == "__main__":
    # Example usage (for testing this script directly)
    # Create dummy files and dirs for testing
    test_output_dir = "./test_output_lo"
    test_input_file = "./test_input_lo.docx"

    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    # Create a simple DOCX file for testing if it doesn't exist
    if not os.path.exists(test_input_file):
        try:
            from docx import (
                Document as DocxDocument,
            )  # Use a different alias to avoid confusion if Document is used elsewhere

            doc = DocxDocument()
            doc.add_paragraph(
                "This is a test docx for LibreOffice conversion created by script."
            )
            doc.save(test_input_file)
            logger.info(f"Created dummy test file: {test_input_file}")
        except ImportError:
            logger.warning(
                "python-docx library is not installed. Cannot create a dummy .docx file for testing. Please create it manually."
            )
            # As a very basic fallback, create a text file that soffice might still process or error out on
            with open(test_input_file, "w") as f:
                f.write("This is a test docx for LibreOffice conversion (plain text).")
        except Exception as e_create:
            logger.error(
                f"Failed to create dummy test file {test_input_file}: {e_create}"
            )

    print("Testing LibreOffice converter...")
    if os.path.exists(test_input_file):  # Only test if input file exists
        success, result_path_or_msg, _ = convert_to_pdf(
            os.path.abspath(test_input_file), os.path.abspath(test_output_dir)
        )

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
        print(
            f"Skipping test, input file {test_input_file} does not exist or could not be created."
        )
