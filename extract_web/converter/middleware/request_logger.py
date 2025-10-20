# -*- coding: utf-8 -*-
"""
临时中间件：记录realtime-speech请求的详细信息
用于排查谁在发送请求
"""

import logging

logger = logging.getLogger(__name__)


class RealtimeSpeechRequestLogger:
    """
    记录所有realtime-speech相关请求的详细信息
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 检查是否是realtime-speech相关请求
        if 'realtime-speech' in request.path:
            # 记录详细信息
            logger.warning(
                f"[RealtimeSpeech请求] "
                f"路径={request.path} | "
                f"方法={request.method} | "
                f"来源IP={self.get_client_ip(request)} | "
                f"User-Agent={request.META.get('HTTP_USER_AGENT', 'Unknown')} | "
                f"Referer={request.META.get('HTTP_REFERER', 'None')} | "
                f"Session={request.session.session_key if hasattr(request, 'session') else 'None'}"
            )
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """获取客户端真实IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
