# -*- coding: utf-8 -*-
"""
文本格式解析器

解析AI返回的Markdown格式文本，转换为PPT格式
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger("converter")


class TextFormatter:
    """文本格式解析器"""
    
    @staticmethod
    def parse_markdown_text(text: str) -> List[Tuple[str, int, bool]]:
        """
        解析Markdown格式文本
        
        Args:
            text: 原始文本（可能包含**加粗**和缩进）
            
        Returns:
            列表，每个元素为(文本内容, 缩进级别, 是否加粗)
        """
        if not text or not text.strip():
            return []
        
        lines = text.split('\n')
        parsed_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            
            # 1. 检测缩进级别
            indent_level = TextFormatter._detect_indent_level(line)
            
            # 2. 移除Markdown标记并检测加粗
            clean_text, is_bold = TextFormatter._remove_markdown_markers(line.strip())
            
            if clean_text:
                parsed_lines.append((clean_text, indent_level, is_bold))
        
        return parsed_lines
    
    @staticmethod
    def _detect_indent_level(line: str) -> int:
        """
        检测缩进级别
        
        规则：
        - 无缩进或以•/-开头：级别0
        - 2-4个空格或1个tab：级别1
        - 4+个空格或2+个tab：级别2
        """
        # 移除行首的列表标记
        stripped = line.lstrip()
        
        # 计算前导空白
        leading_spaces = len(line) - len(stripped)
        
        # 如果以列表标记开头，检查标记前的空白
        if stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*'):
            # 移除标记后再检查
            after_marker = stripped[1:].lstrip()
            marker_spaces = len(stripped) - 1 - len(after_marker)
            
            # 如果标记前有空白，说明是子级
            if leading_spaces >= 4:
                return 2
            elif leading_spaces >= 2:
                return 1
            else:
                return 0
        
        # 普通文本的缩进
        if leading_spaces >= 4:
            return 2
        elif leading_spaces >= 2:
            return 1
        else:
            return 0
    
    @staticmethod
    def _remove_markdown_markers(text: str) -> Tuple[str, bool]:
        """
        移除Markdown标记并检测是否加粗
        
        Args:
            text: 原始文本
            
        Returns:
            (清理后的文本, 是否加粗)
        """
        # 移除行首的列表标记
        text = re.sub(r'^[•\-\*]\s*', '', text)
        
        # 检测并移除加粗标记 **文本**
        is_bold = False
        if '**' in text:
            # 检查是否整行加粗
            bold_pattern = r'^\*\*(.+?)\*\*$'
            match = re.match(bold_pattern, text.strip())
            if match:
                text = match.group(1)
                is_bold = True
            else:
                # 移除所有加粗标记（部分加粗）
                text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
                is_bold = True  # 只要包含加粗标记就认为重要
        
        return text.strip(), is_bold
    
    @staticmethod
    def format_for_ppt(text: str) -> str:
        """
        快速格式化文本用于PPT显示
        
        只移除Markdown标记，不解析结构
        
        Args:
            text: 原始文本
            
        Returns:
            格式化后的文本
        """
        if not text:
            return ""
        
        # 移除加粗标记
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        
        # 移除列表标记（保留缩进）
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 保留前导空格
            leading_spaces = len(line) - len(line.lstrip())
            stripped = line.lstrip()
            
            # 移除列表标记
            if stripped.startswith('• ') or stripped.startswith('- ') or stripped.startswith('* '):
                stripped = stripped[2:]
            
            # 重新添加缩进
            formatted_line = ' ' * leading_spaces + stripped
            formatted_lines.append(formatted_line)
        
        return '\n'.join(formatted_lines)
