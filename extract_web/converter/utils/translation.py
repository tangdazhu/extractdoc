import logging
import os
import re
import dashscope
from utils.config_manager import config

logger = logging.getLogger("ocr_system")


def translate_text(text: str, target_language: str = "en") -> str:
    """
    使用 DashScope 模型翻译文本。

    :param text: 需要翻译的文本。
    :param target_language: 目标语言代码 ('en' for English, 'zh' for Chinese).
    :return: 翻译后的文本。
    """
    # 从环境变量获取 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")

    # 从配置加载模型
    model = config.get("ai_document_analysis.model", "qwen-max")

    # 构建翻译提示
    if target_language == "en":
        prompt = f"请将以下中文文本翻译成英文：\n\n{text}"
    elif target_language == "zh":
        prompt = f"请将以下英文文本翻译成中文：\n\n{text}"
    else:
        raise ValueError(f"不支持的目标语言: {target_language}")

    try:
        # 调用 DashScope 的生成 API
        response = dashscope.Generation.call(
            model=model,
            prompt=prompt,
            api_key=api_key,
            temperature=0.2,  # 使用较低的温度以获得更稳定、一致的翻译结果
        )

        if response.status_code == 200:
            translated_text = response.output.text.strip()
            # 按照您的要求，在日志中打印原文和译文
            logger.info(f"翻译API调用成功 -> 原文: '{text}', 译文: '{translated_text}'")
            return translated_text
        else:
            error_msg = (
                f"DashScope 翻译 API 出错。状态码: {response.status_code}, "
                f"错误代码: {response.code}, 错误信息: {response.message}"
            )
            logger.error(error_msg)
            return f"翻译错误: {response.message}"

    except Exception as e:
        logger.error(f"翻译过程中发生异常: {e}", exc_info=True)
        return f"翻译异常: {e}"


def contains_chinese(text: str) -> bool:
    """
    检查字符串是否包含中文字符。
    """
    return bool(re.search("[\u4e00-\u9fa5]", text))
