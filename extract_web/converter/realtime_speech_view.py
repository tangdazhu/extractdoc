import json
import logging
import asyncio
import base64
import threading
from typing import Dict, Optional
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
import uuid
import time

# 条件导入 - 如果 channels 未安装，跳过 WebSocket 功能
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.db import database_sync_to_async

    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False
    AsyncWebsocketConsumer = object  # 占位符类

from .realtime_speech_processor import create_realtime_recognizer
from .utils.translation import translate_text, contains_chinese

logger = logging.getLogger("ocr_system")
# 全局会话存储（简单实现，生产环境建议使用Redis等）
_recognition_sessions = {}

if CHANNELS_AVAILABLE:

    class RealtimeSpeechConsumer(AsyncWebsocketConsumer):
        """
        WebSocket consumer for real-time speech recognition
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.recognizer = None
            self.is_authenticated = False
            self.user = None
            self.recognition_active = False

        async def connect(self):
            """Handle WebSocket connection"""
            try:
                # Accept the connection first
                await self.accept()

                # Check authentication
                user = self.scope.get("user")
                if not user or not user.is_authenticated:
                    await self.send_error("Authentication required")
                    await self.close()
                    return

                self.user = user
                self.is_authenticated = True

                logger.info(
                    f"Real-time speech WebSocket connected for user: {user.username}"
                )

                # Send connection success message
                await self.send_message(
                    {"type": "connection", "status": "connected", "message": "连接成功"}
                )

            except Exception as e:
                logger.error(f"Error in WebSocket connect: {e}", exc_info=True)
                await self.send_error(f"Connection error: {str(e)}")
                await self.close()

        async def disconnect(self, close_code):
            """Handle WebSocket disconnection"""
            try:
                if self.recognizer and self.recognition_active:
                    # Stop recognition in a thread to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.recognizer.stop_recognition
                    )

                logger.info(
                    f"Real-time speech WebSocket disconnected for user: {self.user.username if self.user else 'unknown'}"
                )

            except Exception as e:
                logger.error(f"Error in WebSocket disconnect: {e}", exc_info=True)

        async def receive(self, text_data):
            """Handle incoming WebSocket messages"""
            try:
                data = json.loads(text_data)
                message_type = data.get("type")

                if message_type == "start_recognition":
                    await self.handle_start_recognition(data)
                elif message_type == "stop_recognition":
                    await self.handle_stop_recognition()
                elif message_type == "audio_data":
                    await self.handle_audio_data(data)
                else:
                    await self.send_error(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                await self.send_error("Invalid JSON format")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
                await self.send_error(f"Message handling error: {str(e)}")

        async def handle_start_recognition(self, data):
            """Start real-time speech recognition"""
            try:
                if self.recognition_active:
                    await self.send_error("Recognition is already active")
                    return

                # Extract parameters
                language_hints = data.get("language_hints", ["zh", "en"])
                vocabulary_id = data.get("vocabulary_id")

                # Create result handler that sends results back via WebSocket
                def result_handler(result: dict):
                    logger.info(
                        f"[DEBUG] WebSocket result_handler called, result={result}"
                    )
                    # 对最终的识别结果进行翻译
                    if result.get("is_final") and result.get("text"):
                        original_text = result["text"]
                        # 如果包含中文字符，则翻译成英文，否则翻译成中文
                        target_lang = "en" if contains_chinese(original_text) else "zh"
                        translated_text = translate_text(original_text, target_lang)
                        result["translated_text"] = translated_text
                        logger.info(f"Translated result for WebSocket: {result}")
                    # 无论什么结果都推送到前端
                    asyncio.create_task(self.send_recognition_result(result))

                # Create and start recognizer in a thread
                success = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._create_and_start_recognizer,
                    result_handler,
                    language_hints,
                    vocabulary_id,
                )

                if success:
                    self.recognition_active = True
                    await self.send_message(
                        {
                            "type": "recognition_started",
                            "status": "success",
                            "message": "实时识别已启动",
                        }
                    )
                else:
                    await self.send_error("Failed to start recognition")

            except Exception as e:
                logger.error(f"Error starting recognition: {e}", exc_info=True)
                await self.send_error(f"Failed to start recognition: {str(e)}")

        def _create_and_start_recognizer(
            self, result_handler, language_hints, vocabulary_id
        ):
            """Create and start recognizer (run in thread)"""
            try:
                self.recognizer = create_realtime_recognizer(
                    result_handler=result_handler, language_hints=language_hints
                )
                return self.recognizer.start_recognition()
            except Exception as e:
                logger.error(
                    f"Error in _create_and_start_recognizer: {e}", exc_info=True
                )
                return False

        async def handle_stop_recognition(self):
            """Stop real-time speech recognition"""
            try:
                if not self.recognition_active:
                    await self.send_error("Recognition is not active")
                    return

                # Stop recognizer in a thread
                success = await asyncio.get_event_loop().run_in_executor(
                    None, self._stop_recognizer
                )

                if success:
                    self.recognition_active = False
                    await self.send_message(
                        {
                            "type": "recognition_stopped",
                            "status": "success",
                            "message": "实时识别已停止",
                        }
                    )
                else:
                    await self.send_error("Failed to stop recognition")

            except Exception as e:
                logger.error(f"Error stopping recognition: {e}", exc_info=True)
                await self.send_error(f"Failed to stop recognition: {str(e)}")

        def _stop_recognizer(self):
            """Stop recognizer (run in thread)"""
            try:
                if self.recognizer:
                    result = self.recognizer.stop_recognition()
                    # stop_recognition 现在返回字典，检查状态
                    return (
                        result.get("status") == "success"
                        if isinstance(result, dict)
                        else bool(result)
                    )
                return True
            except Exception as e:
                logger.error(f"Error in _stop_recognizer: {e}", exc_info=True)
                return False

        async def handle_audio_data(self, data):
            """Handle incoming audio data"""
            try:
                if not self.recognition_active or not self.recognizer:
                    await self.send_error("Recognition is not active")
                    return

                # Extract and decode audio data
                audio_data_b64 = data.get("audio_data")
                if not audio_data_b64:
                    await self.send_error("No audio data provided")
                    return

                audio_data = base64.b64decode(audio_data_b64)
                logger.info(
                    f"[DEBUG] WebSocket received audio_data, length={len(audio_data)}, hex={audio_data[:16].hex()}"
                )

                # Send audio data to recognizer in a thread
                success = await asyncio.get_event_loop().run_in_executor(
                    None, self.recognizer.send_audio_data, audio_data
                )

                if not success:
                    await self.send_error("Failed to process audio data")

            except Exception as e:
                logger.error(f"Error handling audio data: {e}", exc_info=True)
                await self.send_error(f"Audio data error: {str(e)}")

        async def send_recognition_result(self, result: dict):
            """Send recognition result to client"""
            try:
                logger.info(
                    f"Sending WebSocket recognition result: {json.dumps(result, ensure_ascii=False)}"
                )
                await self.send(text_data=json.dumps(result))
            except Exception as e:
                logger.error(f"Error sending recognition result: {e}", exc_info=True)

        async def send_message(self, message: dict):
            """Send a message to the client"""
            try:
                await self.send(text_data=json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message: {e}", exc_info=True)

        async def send_error(self, error_message: str):
            """Send an error message to the client"""
            try:
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": error_message, "status": "error"}
                    )
                )
            except Exception as e:
                logger.error(f"Error sending error message: {e}", exc_info=True)

else:

    class RealtimeSpeechConsumer:
        """
        Dummy WebSocket consumer when channels is not available
        """

        def __init__(self, *args, **kwargs):
            pass


# HTTP API Views for real-time speech recognition
@login_required
def start_realtime_recognition(request):
    """开启一个新的实时语音识别会话"""
    if request.method == "POST":
        logger.info("[TEST] start_realtime_recognition called, method=POST")
        try:
            data = json.loads(request.body)
            language_hints = data.get("language_hints", ["zh", "en"])
            session_id = str(uuid.uuid4())

            # 为每个会话创建一个结果列表
            session_results = []

            def result_handler(result: dict):
                """将中间结果和最终结果添加到会话列表中，并触发翻译"""
                # 对最终的识别结果进行翻译
                if result.get("is_final") and result.get("text"):
                    original_text = result["text"]
                    # 如果包含中文字符，则翻译成英文，否则翻译成中文
                    target_lang = "en" if contains_chinese(original_text) else "zh"
                    translated_text = translate_text(original_text, target_lang)
                    result["translated_text"] = translated_text

                session_results.append(result)

            recognizer = create_realtime_recognizer(
                result_handler=result_handler, language_hints=language_hints
            )

            if not recognizer:
                logger.error("创建识别器失败")
                return JsonResponse(
                    {"status": "error", "message": "无法创建识别器"}, status=500
                )

            # 存储识别器、结果列表和用户ID
            _recognition_sessions[session_id] = {
                "recognizer": recognizer,
                "results": session_results,
                "user_id": request.user.id,
                "creation_time": time.time(),
            }

            if recognizer.start_recognition():
                logger.info(f"实时识别启动成功, session_id: {session_id}")
                return JsonResponse(
                    {
                        "status": "success",
                        "session_id": session_id,
                        "message": "识别已启动",
                    }
                )
            else:
                logger.error(f"实时识别启动失败, session_id: {session_id}")
                # 清理失败的会话
                if session_id in _recognition_sessions:
                    del _recognition_sessions[session_id]
                return JsonResponse(
                    {"status": "error", "message": "启动识别失败"}, status=500
                )

        except Exception as e:
            logger.error(f"启动识别时发生错误: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "仅支持POST请求"}, status=405)


@csrf_exempt
@login_required
def send_audio_data(request, session_id):
    """接收前端发送的音频数据并传递给识别器"""
    if request.method == "POST":
        logger.debug(
            f"[TEST] send_audio_data view called, session_id={session_id}, method=POST"
        )
        # 新增日志，记录收到的原始音频包长度和部分内容
        logger.info(
            f"[DEBUG] HTTP received audio_data, length={len(request.body)}, hex={request.body[:16].hex()}"
        )
        session = _recognition_sessions.get(session_id)
        if not session:
            return JsonResponse(
                {"status": "error", "message": "会话未找到"}, status=404
            )

        # 增加用户ID校验
        if session.get("user_id") != request.user.id:
            return JsonResponse({"status": "error", "message": "权限不足"}, status=403)

        try:
            recognizer = session.get("recognizer")
            if recognizer and recognizer.is_recognition_active():
                # 直接从 request.body 获取原始的二进制数据
                audio_data = request.body
                if not recognizer.send_audio_data(audio_data):
                    logger.warning(f"无法将音频数据放入队列, session_id={session_id}")
                return JsonResponse({"status": "success"})
            else:
                return JsonResponse(
                    {"status": "error", "message": "识别器未激活"}, status=400
                )
        except Exception as e:
            logger.error(f"发送音频数据时出错: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "仅支持POST请求"}, status=405)


@csrf_exempt
@login_required
def get_recognition_results(request, session_id):
    """获取指定会话的当前识别结果"""
    if request.method == "GET":
        logger.info(
            f"[TEST] get_recognition_results called, session_id={session_id}, method=GET"
        )
        session = _recognition_sessions.get(session_id)
        if session:
            # 增加用户ID校验
            if session.get("user_id") != request.user.id:
                return JsonResponse(
                    {"status": "error", "message": "权限不足"}, status=403
                )
            # 返回当前所有的结果，并清空列表，避免重复发送
            current_results = session["results"]
            session["results"] = []  # 清空以避免下次重复获取
            return JsonResponse({"status": "success", "results": current_results})
        else:
            return JsonResponse(
                {"status": "error", "message": "会话未找到或已过期"}, status=404
            )
    return JsonResponse({"status": "error", "message": "仅支持GET请求"}, status=405)


@csrf_exempt
@login_required
def stop_realtime_recognition(request, session_id):
    """停止一个实时语音识别会话"""
    if request.method == "POST":
        logger.info(
            f"[TEST] stop_realtime_recognition called, session_id={session_id}, method=POST"
        )
        session = _recognition_sessions.get(session_id)
        if session and "recognizer" in session:
            # 增加用户ID校验
            if session.get("user_id") != request.user.id:
                return JsonResponse(
                    {"status": "error", "message": "权限不足"}, status=403
                )

            recognizer = session["recognizer"]
            result = recognizer.stop_recognition()  # 这个方法现在会返回最终结果

            # 清理会话
            del _recognition_sessions[session_id]

            logger.info(f"会话 {session_id} 已停止并清理")

            # 从结果中提取 final_results 并返回
            return JsonResponse(
                {
                    "status": result.get("status", "error"),
                    "message": result.get("message", "处理停止请求时出错"),
                    "final_results": result.get("final_results", []),
                }
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "会话未找到或已过期"}, status=404
            )
    return JsonResponse({"status": "error", "message": "仅支持POST请求"}, status=405)


def cleanup_old_sessions():
    """Clean up old recognition sessions"""
    try:
        current_time = time.time()
        expired_sessions = []

        for session_id, session in _recognition_sessions.items():
            if current_time - session["created_at"] > 3600:  # 1 hour timeout
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            session = _recognition_sessions.get(session_id)
            if session:
                session["recognizer"].stop_recognition()
                del _recognition_sessions[session_id]

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}", exc_info=True)
