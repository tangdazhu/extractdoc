import logging
from typing import Dict, Any

logger = logging.getLogger('converter')

def parse_conversion_request_params(post_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Parses conversion-related parameters from the request.POST data.

    Args:
        post_data: The request.POST QueryDict (or a regular dict for testing).
        request_id: The unique request ID for logging context.

    Returns:
        A dictionary containing parsed and default parameters:
        'main_tab', 'sub_tab', 'merge_output', 'output_format',
        'pdf_to_word_mode', 'pdf_to_excel_mode', 'pdf_to_ppt_mode', 'pdf_to_txt_mode'.
    """
    params = {}

    params['merge_output'] = post_data.get('merge_output', 'false').lower() == 'true'
    output_format_param = post_data.get('output_format', '') # Raw from request
    params['main_tab'] = post_data.get('main_tab', 'imgToFile')
    params['sub_tab'] = post_data.get('sub_tab', '')
    
    # Determine effective output_format based on main_tab and sub_tab
    effective_output_format = ''
    if params['main_tab'] == 'fileToPdf':
        effective_output_format = 'pdf'
    elif params['main_tab'] == 'imgToFile':
        effective_output_format = output_format_param if output_format_param else 'docx' 
    elif params['main_tab'] == 'pdfToFile':
        if params['sub_tab'] == 'pdfToWord': 
            effective_output_format = 'docx'
        elif params['sub_tab'] == 'pdfToExcel': 
            effective_output_format = 'xlsx'
        elif params['sub_tab'] == 'pdfToPpt': 
            effective_output_format = 'pptx'
        elif params['sub_tab'] == 'pdfToTxt': 
            effective_output_format = 'txt'
        else:
            effective_output_format = output_format_param
            logger.warning(f"RequestParsing: pdfToFile: Unknown sub_tab ('{params['sub_tab']}'), fallback to param: '{output_format_param}', RequestID: {request_id}")
            if not effective_output_format: 
                effective_output_format = 'docx' # Critical fallback
                logger.error(f"RequestParsing: pdfToFile: Critical fallback to docx for unknown sub_tab, RequestID: {request_id}")
    else: 
        effective_output_format = output_format_param
        logger.warning(f"RequestParsing: Unhandled main_tab '{params['main_tab']}', fallback to param: '{output_format_param}', RequestID: {request_id}")
        if not effective_output_format: 
            effective_output_format = 'docx' # Critical fallback
            logger.error(f"RequestParsing: Fallback: Critical fallback to docx for unhandled main_tab, RequestID: {request_id}")
    
    params['output_format'] = effective_output_format
    params['output_format_param'] = output_format_param # Keep original param for logging if needed

    # Get conversion mode parameters for all PDF conversion types
    params['pdf_to_word_mode'] = post_data.get('pdf_to_word_mode', 'pdf2docx')
    params['pdf_to_excel_mode'] = post_data.get('pdf_to_excel_mode', 'pdfplumber')
    params['pdf_to_ppt_mode'] = post_data.get('pdf_to_ppt_mode', 'screenshot')
    params['pdf_to_txt_mode'] = post_data.get('pdf_to_txt_mode', 'pymupdf')

    logger.debug(
        f"RequestParamsParsed (RequestID: {request_id}): "
        f"MainTab={params['main_tab']}, SubTab={params['sub_tab']}, Merge={params['merge_output']}, "
        f"ReqFormat='{params['output_format_param']}', EffFormat='{params['output_format']}', "
        f"PDFtoWordMode={params['pdf_to_word_mode']}, PDFtoExcelMode={params['pdf_to_excel_mode']}, "
        f"PDFtoPPTMode={params['pdf_to_ppt_mode']}, PDFtoTXTMode={params['pdf_to_txt_mode']}"
    )
    
    return params 