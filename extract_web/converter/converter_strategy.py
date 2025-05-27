# 转换策略配置
# 定义不同转换类型的首选方法和备用方法

CONVERSION_STRATEGIES = {
    'pdf_to_txt': {
        'primary': 'pymupdf',  # 保持当前方案，效果好且稳定
        'fallback': 'libreoffice',
        'reason': 'PyMuPDF文本提取效果好，性能高'
    },
    
    'pdf_to_word': {
        'primary': 'pdf2docx',  # 保持当前方案，格式保持较好
        'fallback': 'libreoffice', 
        'reason': 'pdf2docx对格式保持较好'
    },
    
    'pdf_to_excel': {
        'primary': 'pdfplumber',  # 保持当前方案，表格提取专业
        'fallback': 'libreoffice',
        'reason': 'pdfplumber专门优化表格提取'
    },
    
    'pdf_to_ppt': {
        'primary': 'libreoffice',  # 当前只有这个选项
        'fallback': None,
        'reason': 'LibreOffice是唯一可行的方案'
    }
}

# LibreOffice过滤器配置
LIBREOFFICE_FILTERS = {
    'pdf_to_txt': {
        'infilter': 'writer_pdf_import',
        'convert_to': 'txt'
    },
    'pdf_to_word': {
        'infilter': 'writer_pdf_import', 
        'convert_to': 'docx'
    },
    'pdf_to_excel': {
        'infilter': 'calc_pdf_addstream_import',
        'convert_to': 'xlsx'
    },
    'pdf_to_ppt': {
        'infilter': 'impress_pdf_import',
        'convert_to': 'pptx'
    }
} 