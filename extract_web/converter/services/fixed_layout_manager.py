# -*- coding: utf-8 -*-
"""
固定布局管理器
使用固定的布局区域,不进行复杂的高度计算
"""

from pptx.util import Inches


class FixedLayoutManager:
    """
    固定布局管理器
    
    核心理念:
    1. 每种布局类型有固定的区域定义
    2. 不计算高度,使用PowerPoint的auto-fit功能
    3. 简单可靠,不会溢出
    """
    
    # 标准PPT尺寸(16:9)
    SLIDE_WIDTH = 10.0  # 英寸
    SLIDE_HEIGHT = 7.5  # 英寸
    
    # 标准边距
    MARGIN_LEFT = 0.5
    MARGIN_RIGHT = 0.5
    MARGIN_TOP = 1.5  # 标题后
    MARGIN_BOTTOM = 0.5
    
    # 内容区域
    CONTENT_LEFT = MARGIN_LEFT
    CONTENT_WIDTH = SLIDE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    CONTENT_TOP = MARGIN_TOP
    CONTENT_HEIGHT = SLIDE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    
    # 布局定义: 每种布局类型的固定区域
    LAYOUTS = {
        # 标题+表格布局
        'title_and_table': [
            {
                'type': 'table',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH,
                'height': CONTENT_HEIGHT,  # 使用全部可用高度
            },
        ],
        
        # 标题+图片布局
        'title_and_image': [
            {
                'type': 'image',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH,
                'height': 2.8,  # 图片缩小到2.8英寸高(从3.5减小)
            },
            {
                'type': 'text',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP + 3.0,  # 图片后0.2英寸间距
                'width': CONTENT_WIDTH,
                'height': 2.5,  # 文本增大到2.5英寸高(从1.8增大)
            },
        ],
        
        # 标题+文本布局
        'title_and_text': [
            {
                'type': 'text',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH,
                'height': CONTENT_HEIGHT,  # 文本占满全部
            },
        ],
        
        # 标题+文本+图片布局
        'title_text_and_image': [
            {
                'type': 'text',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH,
                'height': 2.0,  # 文本2英寸
            },
            {
                'type': 'image',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP + 2.2,  # 文本后0.2英寸间距
                'width': CONTENT_WIDTH,
                'height': 3.3,  # 图片3.3英寸
            },
        ],
        
        # 两列布局
        'two_column': [
            {
                'type': 'any',
                'left': CONTENT_LEFT,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH / 2 - 0.1,
                'height': CONTENT_HEIGHT,
            },
            {
                'type': 'any',
                'left': CONTENT_LEFT + CONTENT_WIDTH / 2 + 0.1,
                'top': CONTENT_TOP,
                'width': CONTENT_WIDTH / 2 - 0.1,
                'height': CONTENT_HEIGHT,
            },
        ],
    }
    
    @classmethod
    def get_zones(cls, layout_type: str) -> list:
        """
        获取布局区域
        
        Args:
            layout_type: 布局类型
            
        Returns:
            区域列表,每个区域包含 type, left, top, width, height
        """
        return cls.LAYOUTS.get(layout_type, cls.LAYOUTS['title_and_text'])
    
    @classmethod
    def get_zone_by_type(cls, layout_type: str, element_type: str) -> dict:
        """
        根据元素类型获取对应的区域
        
        Args:
            layout_type: 布局类型
            element_type: 元素类型 (table, image, text)
            
        Returns:
            区域字典,如果没有找到返回None
        """
        zones = cls.get_zones(layout_type)
        
        for zone in zones:
            if zone['type'] == element_type or zone['type'] == 'any':
                return zone
        
        return None
    
    @classmethod
    def to_inches(cls, zone: dict) -> dict:
        """
        将区域转换为Inches对象
        
        Args:
            zone: 区域字典
            
        Returns:
            包含Inches对象的字典
        """
        return {
            'left': Inches(zone['left']),
            'top': Inches(zone['top']),
            'width': Inches(zone['width']),
            'height': Inches(zone['height']),
        }
