"""
Real-time Speech Recognition Processor using DashScope API
实时语音识别处理器，使用阿里云DashScope API
"""

import os
import json
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from queue import Queue, Empty
import dashscope

# 条件导入 websocket-client
try:
    import websocket
    import ssl

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Configure logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s %(process)d %(thread)d %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ocr_system")
logger.info("[TEST] === 这是realtime_speech_processor.py的顶层日志 ===")


class RealtimeSpeechRecognizer:
    """
    Real-time speech recognition using DashScope WebSocket API
    使用DashScope WebSocket API进行实时语音识别
    """

    def __init__(self, api_key: str, result_handler: Callable[[Dict], None] = None):
        """
        Initialize the real-time speech recognizer

        Args:
            api_key: DashScope API key
            result_handler: Callback function to handle recognition results
        """
        self.api_key = api_key
        self.result_handler = result_handler or self._default_result_handler

        # WebSocket connection
        self.ws = None
        self.ws_url = "wss://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        # Recognition state
        self._is_active = False
        self._recognition_thread = None
        self._audio_queue = Queue()

        # Configuration
        self.config = {
            "model": "paraformer-realtime-v1",
            "language_hints": ["zh", "en"],
            "audio_encoding": "pcm",
            "sample_rate": 16000,
            "enable_intermediate_result": True,
            "enable_punctuation_prediction": True,
            "enable_inverse_text_normalization": True,
        }

        logger.info(f"Recognizer created with config: {self.config}")

    def _default_result_handler(self, result: Dict[str, Any]):
        logger.info("[TEST] _default_result_handler called, result: %s", result)
        logger.info(f"Recognition result: {result}")

    def _create_websocket_connection(self):
        """Create WebSocket connection to DashScope"""
        try:
            # Note: DashScope uses HTTP API, not WebSocket for real-time recognition
            # This is a simplified implementation for demonstration
            logger.info("WebSocket connection would be established here")
            return True
        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}")
            return False

    def _recognition_worker(self):
        logger.info("[TEST] _recognition_worker started")
        while self._is_active:
            try:
                audio_data = self._audio_queue.get(timeout=1.0)
                logger.info(
                    "[TEST] _recognition_worker got audio_data, len=%d",
                    len(audio_data) if audio_data else -1,
                )

                if audio_data is None:  # Stop signal
                    break

                # Process audio data (simplified)
                result = self._process_audio_chunk(audio_data)

                if result and self.result_handler:
                    self.result_handler(result)

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in recognition worker: {e}")

    def _process_audio_chunk(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        logger.info(
            "[TEST] _process_audio_chunk called, data length: %d", len(audio_data)
        )
        try:
            # 累积音频数据长度，但不立即返回识别结果
            # 实际实现中，这里会发送音频到 DashScope API
            logger.debug(f"Audio chunk received, length: {len(audio_data)} bytes")

            # 在 mock 模式下，我们不返回结果，只有在停止录音时才返回最终结果
            return None

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return None

    def start_recognition(self, language_hints: List[str] = None) -> bool:
        logger.info(
            "[TEST] start_recognition called, language_hints: %s", language_hints
        )
        if self._is_active:
            logger.warning("Recognition is already active")
            return True

        try:
            # Update configuration
            if language_hints:
                self.config["language_hints"] = language_hints

            # Create WebSocket connection
            if not self._create_websocket_connection():
                return False

            # Start recognition thread
            self._is_active = True
            self._recognition_thread = threading.Thread(
                target=self._recognition_worker, daemon=True
            )
            self._recognition_thread.start()

            logger.info("Real-time speech recognition started")
            return True

        except Exception as e:
            logger.error(f"Failed to start recognition: {e}")
            self._is_active = False
            return False

    def stop_recognition(self) -> Dict[str, Any]:
        """停止实时语音识别"""
        logger.info("[TEST] stop_recognition called")
        try:
            self._is_active = False
            logger.info("Real-time speech recognition stopped")

            # 在停止时模拟返回一条最终识别结果
            final_result = {
                "text": "这是一条完整的语音识别结果",
                "is_final": True,
                "confidence": 0.95,
                "timestamp": time.time(),
            }

            # 调用结果处理器返回最终结果
            if self.result_handler:
                logger.info("[TEST] Calling result_handler with final result")
                self.result_handler(final_result)

            return {"status": "success", "message": "识别已停止，返回最终结果"}
        except Exception as e:
            logger.error(f"Error stopping recognition: {e}")
            return {"status": "error", "message": str(e)}

    def send_audio_data(self, audio_data: bytes) -> bool:
        logger.info("[TEST] send_audio_data called, data length: %d", len(audio_data))
        if not self._is_active:
            logger.warning("Recognition is not active")
            return False

        try:
            self._audio_queue.put(audio_data, timeout=1.0)
            return True

        except Exception as e:
            logger.error(f"Failed to queue audio data: {e}")
            return False

    def is_recognition_active(self) -> bool:
        """Check if recognition is currently active"""
        return self._is_active

    def get_configuration(self) -> Dict[str, Any]:
        """Get current recognition configuration"""
        return self.config.copy()

    def update_configuration(self, **kwargs) -> bool:
        """
        Update recognition configuration

        Args:
            **kwargs: Configuration parameters to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            for key, value in kwargs.items():
                if key in self.config:
                    self.config[key] = value
                else:
                    logger.warning(f"Unknown configuration key: {key}")

            logger.info(f"Configuration updated: {kwargs}")
            return True

        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False


def create_realtime_recognizer(
    result_handler: Callable[[Dict], None] = None, language_hints: List[str] = None
) -> Optional[RealtimeSpeechRecognizer]:
    logger.info(
        "[TEST] create_realtime_recognizer called, language_hints: %s", language_hints
    )
    try:
        # 优先用环境变量
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        # 如果环境变量没有，尝试 dashscope.api_key
        if not api_key and hasattr(dashscope, "api_key") and dashscope.api_key:
            api_key = dashscope.api_key
        if not api_key:
            logger.error(
                "DASHSCOPE_API_KEY environment variable not found and dashscope.api_key not set"
            )
            return None
        # Create recognizer
        recognizer = RealtimeSpeechRecognizer(
            api_key=api_key, result_handler=result_handler
        )
        # Set language hints if provided
        if language_hints:
            recognizer.update_configuration(language_hints=language_hints)
        logger.info("Real-time speech recognizer created successfully")
        return recognizer
    except Exception as e:
        logger.error(f"Failed to create real-time recognizer: {e}")
        return None


# Global recognizer instance for Django views
_global_recognizer: Optional[RealtimeSpeechRecognizer] = None


def get_global_recognizer() -> Optional[RealtimeSpeechRecognizer]:
    """Get the global recognizer instance"""
    return _global_recognizer


def set_global_recognizer(recognizer: RealtimeSpeechRecognizer):
    """Set the global recognizer instance"""
    global _global_recognizer
    _global_recognizer = recognizer


def cleanup_global_recognizer():
    """Clean up the global recognizer instance"""
    global _global_recognizer
    if _global_recognizer:
        _global_recognizer.stop_recognition()
        _global_recognizer = None
