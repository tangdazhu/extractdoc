import asyncio
import argparse
import edge_tts
import logging
import os
from typing import List, Dict, Any

# --- New Logging Setup ---
# Configure logger to write to app.log (like other modules) and console
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log_file_path = os.path.join(log_dir, "app.log")

logger = logging.getLogger("ocr_system")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    try:
        fh = logging.FileHandler(log_file_path, "a", "utf-8-sig")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        fallback_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        )
        fallback_handler = logging.StreamHandler()
        fallback_handler.setFormatter(fallback_formatter)
        logger.addHandler(fallback_handler)
        logger.error(
            f"Failed to set up file logger, falling back to console. Error: {e}"
        )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.propagate = False
else:
    logger.propagate = False
# --- End New Logging Setup ---

# --- Curated List of Predefined Voices ---
PREDEFINED_VOICES = [
    {
        "DisplayName": "晓晓 (默认) - 温暖、清晰的年轻女声",
        "ShortName": "zh-CN-XiaoxiaoNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "晓艺 - 活泼、甜美的少女音",
        "ShortName": "zh-CN-XiaoyiNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "云希 - 阳光、活力的少年音",
        "ShortName": "zh-CN-YunxiNeural",
        "Gender": "Male",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "云夏 - 清新、自然的青年女声",
        "ShortName": "zh-CN-YunxiaNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "云健 - 成熟、稳重的男声",
        "ShortName": "zh-CN-YunjianNeural",
        "Gender": "Male",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "晓涵 - 温柔、甜美的对话风格女声",
        "ShortName": "zh-CN-XiaohanNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "晓墨 - 自然、平和的通用女声",
        "ShortName": "zh-CN-XiaomoNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "云扬 - 成熟、稳重的磁性男声",
        "ShortName": "zh-CN-YunyangNeural",
        "Gender": "Male",
        "Locale": "zh-CN",
    },
    {
        "DisplayName": "晓辰 - 知性、优雅的青年女声",
        "ShortName": "zh-CN-XiaochenNeural",
        "Gender": "Female",
        "Locale": "zh-CN",
    },
]

# Fallback voice mapping for compatibility
# All unavailable voices will fallback to XiaoxiaoNeural (which is confirmed available)
VOICE_FALLBACK_MAP = {
    "zh-CN-XiaohanNeural": "zh-CN-XiaoxiaoNeural",  # 晓涵 -> 晓晓
    "zh-CN-XiaomoNeural": "zh-CN-XiaoxiaoNeural",  # 晓墨 -> 晓晓
    "zh-CN-YunyangNeural": "zh-CN-YunxiNeural",  # 云扬 -> 云希
    "zh-CN-XiaochenNeural": "zh-CN-XiaoyiNeural",  # 晓辰 -> 晓艺
    "zh-CN-XiaoqiuNeural": "zh-CN-XiaoxiaoNeural",  # 晓秋 -> 晓晓
}


def get_predefined_tts_voices() -> List[Dict[str, Any]]:
    """
    Returns a curated, static list of recommended TTS voices.
    This avoids network calls and provides a user-friendly selection.
    """
    logger.info("Returning predefined static list of TTS voices.")
    return PREDEFINED_VOICES


async def validate_voice(voice: str) -> bool:
    """
    Validate if a voice is available in edge-tts service.
    """
    try:
        voices_manager = await edge_tts.VoicesManager.create()
        available_voices = [v["ShortName"] for v in voices_manager.voices]
        is_available = voice in available_voices
        logger.info(
            f"Voice validation for '{voice}': {'Available' if is_available else 'Not available'}"
        )
        if not is_available:
            # Log some similar voices for debugging
            similar_voices = [
                v for v in available_voices if "zh-CN" in v and "Neural" in v
            ][:5]
            logger.info(f"Available Chinese Neural voices (first 5): {similar_voices}")
        return is_available
    except Exception as e:
        logger.error(f"Failed to validate voice '{voice}': {e}")
        return False


# The function that performs the actual conversion remains, as it still needs to contact the service.
async def text_to_speech_edge_tts_async(text: str, voice: str, output_path: str):
    """
    Asynchronously converts text to speech and saves it to a file.
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    original_voice = voice

    try:
        logger.info(
            f"Starting TTS conversion with voice '{voice}'. Using proxy: {proxy}"
            if proxy
            else f"Starting TTS conversion with voice '{voice}'. No proxy."
        )

        # Validate voice before attempting conversion
        is_voice_valid = await validate_voice(voice)
        if not is_voice_valid:
            # Try fallback voice if available
            if voice in VOICE_FALLBACK_MAP:
                fallback_voice = VOICE_FALLBACK_MAP[voice]
                logger.warning(
                    f"Voice '{voice}' not available, trying fallback voice '{fallback_voice}'"
                )
                is_fallback_valid = await validate_voice(fallback_voice)
                if is_fallback_valid:
                    voice = fallback_voice
                    logger.info(f"Using fallback voice '{voice}' for conversion")
                else:
                    logger.error(
                        f"Both original voice '{original_voice}' and fallback voice '{fallback_voice}' are not available"
                    )
                    raise ValueError(
                        f"Voice '{original_voice}' and its fallback are not available."
                    )
            else:
                logger.error(
                    f"Voice '{voice}' is not available and no fallback defined"
                )
                raise ValueError(
                    f"Voice '{voice}' is not available. Please check the voice name."
                )

        communicate = edge_tts.Communicate(text, voice, proxy=proxy)
        await communicate.save(output_path)
        logger.info(f"Successfully saved TTS audio to: {output_path}")
    except Exception as e:
        logger.error(
            f"An error occurred during TTS conversion to '{output_path}': {e}",
            exc_info=True,
        )
        raise


def text_to_speech_edge_tts(text: str, voice: str, output_path: str):
    """
    Synchronous wrapper for text_to_speech_edge_tts_async.
    """
    try:
        asyncio.run(text_to_speech_edge_tts_async(text, voice, output_path))
    except Exception as e:
        logger.error(f"Sync wrapper failed for TTS conversion for voice '{voice}': {e}")
        raise


async def main():
    """
    Main function to handle text-to-speech conversion using Edge TTS.
    """
    parser = argparse.ArgumentParser(
        description="Convert text to speech using Microsoft Edge TTS."
    )
    parser.add_argument(
        "--text_file_path", required=True, type=str, help="Path to the input text file."
    )
    parser.add_argument(
        "--voice",
        required=True,
        type=str,
        help="The voice to use for the conversion (e.g., 'zh-CN-XiaoxiaoNeural').",
    )
    parser.add_argument(
        "--output_file",
        required=True,
        type=str,
        help="The path to save the output audio file.",
    )

    args = parser.parse_args()

    try:
        with open(args.text_file_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            logger.warning("Input text file is empty. Nothing to convert.")
            return

        voice = args.voice
        original_voice = voice
        logger.info(f"Starting TTS conversion with voice: {voice}")

        # Validate voice before attempting conversion
        is_voice_valid = await validate_voice(voice)
        if not is_voice_valid:
            # Try fallback voice if available
            if voice in VOICE_FALLBACK_MAP:
                fallback_voice = VOICE_FALLBACK_MAP[voice]
                logger.warning(
                    f"Voice '{voice}' not available, trying fallback voice '{fallback_voice}'"
                )
                is_fallback_valid = await validate_voice(fallback_voice)
                if is_fallback_valid:
                    voice = fallback_voice
                    logger.info(f"Using fallback voice '{voice}' for conversion")
                else:
                    logger.error(
                        f"Both original voice '{original_voice}' and fallback voice '{fallback_voice}' are not available"
                    )
                    raise ValueError(
                        f"Voice '{original_voice}' and its fallback are not available."
                    )
            else:
                logger.error(
                    f"Voice '{voice}' is not available and no fallback defined"
                )
                raise ValueError(
                    f"Voice '{voice}' is not available. Please check the voice name."
                )

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(args.output_file)
        logger.info(f"Successfully saved TTS audio to: {args.output_file}")
    except FileNotFoundError:
        logger.error(f"Input text file not found at: {args.text_file_path}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during TTS conversion: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
