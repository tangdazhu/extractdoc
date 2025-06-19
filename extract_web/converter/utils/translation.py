import logging
import os
import re
import dashscope

logger = logging.getLogger("ocr_system")


def translate_text(text: str, target_language: str = "en") -> str:
    """
    使用 DashScope Qwen-Long 模型翻译文本。

    :param text: 需要翻译的文本。
    :param target_language: 目标语言代码 ('en' for English, 'zh' for Chinese).
    :return: 翻译后的文本。
    """
    # 确保我们有可用的 API key
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("未在环境变量中找到 DASHSCOPE_API_KEY")
        return "翻译错误：未配置 API key。"

    # 根据目标语言代码确定提示中使用的语言名称
    lang_map = {"en": "English", "zh": "中文"}
    target_lang_name = lang_map.get(target_language, "English")

    # 构建简洁、明确的提示
    prompt = f'Translate the following text to {target_lang_name}. Return only the translated text, without any explanations or additional content.\n\nText to translate: "{text}"'

    try:
        # 调用 DashScope 的生成 API
        response = dashscope.Generation.call(
            model="qwen-long",
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
