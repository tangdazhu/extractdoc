import asyncio
import argparse
import edge_tts
import logging
import os

# --- New Logging Setup ---
# Configure logger to write to app.log (like other modules) and console
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log_file_path = os.path.join(log_dir, "app.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Prevent adding handlers multiple times
if not logger.handlers:
    # File handler
    try:
        fh = logging.FileHandler(log_file_path, "a", "utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(fh)
    except Exception as e:
        # Fallback to console if file logging fails
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
        )
        logger.error(
            f"Failed to set up file logger, falling back to console. Error: {e}"
        )

    # Console handler (for direct script execution feedback)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)
# --- End New Logging Setup ---


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

        logger.info(f"Starting TTS conversion with voice: {args.voice}")
        communicate = edge_tts.Communicate(text, args.voice)
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
