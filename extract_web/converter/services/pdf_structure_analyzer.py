"""PDF结构分析工具。

用于诊断pdfplumber提取失败的原因。
"""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("converter")

try:
    import pdfplumber
    import fitz  # PyMuPDF
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    logger.warning("pdfplumber或PyMuPDF未安装")


def analyze_pdf_structure(pdf_path: Path, page_num: int = 2) -> Dict:
    """
    分析PDF页面的内部结构
    
    Args:
        pdf_path: PDF文件路径
        page_num: 页码(从1开始)
        
    Returns:
        结构分析结果
    """
    if not AVAILABLE:
        return {}
    
    result = {
        "page_num": page_num,
        "text_blocks": [],
        "lines": [],
        "rects": [],
        "chars": []
    }
    
    # 1. 使用pdfplumber分析
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_num - 1]
        
        # 获取所有文字对象
        chars = page.chars
        logger.info(f"页面{page_num}共有{len(chars)}个字符对象")
        
        # 按Y坐标分组,查看文字布局
        y_groups = {}
        for char in chars:
            y = round(char['y0'], 1)  # 四舍五入到0.1
            if y not in y_groups:
                y_groups[y] = []
            y_groups[y].append({
                'text': char['text'],
                'x': char['x0'],
                'font': char.get('fontname', ''),
                'size': char.get('size', 0)
            })
        
        # 输出每行的文字
        logger.info(f"页面{page_num}文字布局:")
        for y in sorted(y_groups.keys()):
            chars_in_line = sorted(y_groups[y], key=lambda x: x['x'])
            text = ''.join([c['text'] for c in chars_in_line])
            logger.info(f"  Y={y}: {text[:100]}")
        
        # 获取表格线
        lines = page.lines
        logger.info(f"页面{page_num}共有{len(lines)}条线")
        
        # 获取矩形(表格单元格边框)
        rects = page.rects
        logger.info(f"页面{page_num}共有{len(rects)}个矩形")
        
        # 尝试不同的表格提取策略
        logger.info("尝试不同的表格提取策略:")
        
        # 策略1: lines
        tables_lines = page.extract_tables(table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        })
        logger.info(f"  lines策略: {len(tables_lines)}个表格")
        if tables_lines:
            logger.info(f"    第一个表格: {len(tables_lines[0])}行x{len(tables_lines[0][0])}列")
        
        # 策略2: text
        tables_text = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        })
        logger.info(f"  text策略: {len(tables_text)}个表格")
        if tables_text:
            logger.info(f"    第一个表格: {len(tables_text[0])}行x{len(tables_text[0][0])}列")
        
        # 策略3: explicit (显式指定表格区域)
        # 获取页面中最大的矩形区域(可能是表格)
        if rects:
            # 按面积排序
            sorted_rects = sorted(rects, key=lambda r: (r['width'] * r['height']), reverse=True)
            largest_rect = sorted_rects[0]
            logger.info(f"  最大矩形: x0={largest_rect['x0']}, y0={largest_rect['y0']}, "
                       f"x1={largest_rect['x1']}, y1={largest_rect['y1']}")
    
    # 2. 使用PyMuPDF分析
    pdf_doc = fitz.open(str(pdf_path))
    page = pdf_doc[page_num - 1]
    
    # 获取文本块
    text_blocks = page.get_text("blocks")
    logger.info(f"PyMuPDF检测到{len(text_blocks)}个文本块")
    for i, block in enumerate(text_blocks[:10]):  # 只显示前10个
        x0, y0, x1, y1, text, block_no, block_type = block
        logger.info(f"  块{i}: ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) = {text[:50]}")
    
    return result


def diagnose_table_extraction(pdf_path: Path, page_num: int = 2):
    """
    诊断表格提取问题
    
    Args:
        pdf_path: PDF文件路径
        page_num: 页码
    """
    logger.info("="*60)
    logger.info(f"开始诊断PDF表格提取问题: {pdf_path.name}, 页面{page_num}")
    logger.info("="*60)
    
    analyze_pdf_structure(pdf_path, page_num)
    
    logger.info("="*60)
    logger.info("诊断完成")
    logger.info("="*60)
