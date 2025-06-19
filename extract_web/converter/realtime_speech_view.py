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
                    # Schedule the coroutine to send the message
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
@csrf_exempt
@login_required
def start_realtime_recognition(request):
    logger.info("[TEST] start_realtime_recognition called, method=%s", request.method)
    """Start a real-time speech recognition session"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
        language_hints = data.get("language_hints", ["zh", "en"])

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create result handler
        results = []

        def result_handler(result: dict):
            results.append(
                {
                    "text": result.get("text", ""),
                    "is_final": result.get("is_final", False),
                    "confidence": result.get("confidence", 0.0),
                    "timestamp": time.time(),
                }
            )

        # Create recognizer
        recognizer = create_realtime_recognizer(
            result_handler=result_handler, language_hints=language_hints
        )

        if not recognizer:
            return JsonResponse({"error": "Failed to create recognizer"}, status=500)

        # Start recognition
        if recognizer.start_recognition():
            # Store session
            _recognition_sessions[session_id] = {
                "recognizer": recognizer,
                "results": results,
                "user_id": request.user.id,
                "created_at": time.time(),
            }

            return JsonResponse(
                {
                    "status": "success",
                    "session_id": session_id,
                    "message": "实时识别会话已启动",
                }
            )
        else:
            return JsonResponse({"error": "Failed to start recognition"}, status=500)

    except Exception as e:
        logger.error(f"Error starting realtime recognition: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def send_audio_data(request, session_id):
    logger.info(
        "[TEST] send_audio_data view called, session_id=%s, method=%s",
        session_id,
        request.method,
    )
    """Send audio data to recognition session"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        session = _recognition_sessions.get(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        if session["user_id"] != request.user.id:
            return JsonResponse({"error": "Access denied"}, status=403)

        # Get audio data
        if request.content_type == "application/json":
            data = json.loads(request.body)
            audio_data_b64 = data.get("audio_data")
            if not audio_data_b64:
                return JsonResponse({"error": "No audio data provided"}, status=400)
            audio_data = base64.b64decode(audio_data_b64)
        else:
            audio_data = request.body

        # Send to recognizer
        recognizer = session["recognizer"]
        if recognizer.send_audio_data(audio_data):
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"error": "Failed to process audio data"}, status=500)

    except Exception as e:
        logger.error(f"Error sending audio data: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def get_recognition_results(request, session_id):
    logger.info(
        "[TEST] get_recognition_results called, session_id=%s, method=%s",
        session_id,
        request.method,
    )
    """Get recognition results from session"""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET method allowed"}, status=405)

    try:
        session = _recognition_sessions.get(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        if session["user_id"] != request.user.id:
            return JsonResponse({"error": "Access denied"}, status=403)

        results = session["results"]
        return JsonResponse(
            {"status": "success", "results": results, "session_id": session_id}
        )

    except Exception as e:
        logger.error(f"Error getting recognition results: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def stop_realtime_recognition(request, session_id):
    logger.info(
        "[TEST] stop_realtime_recognition called, session_id=%s, method=%s",
        session_id,
        request.method,
    )
    """Stop a real-time speech recognition session"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        session = _recognition_sessions.get(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        if session["user_id"] != request.user.id:
            return JsonResponse({"error": "Access denied"}, status=403)

        # Stop recognizer - 这会触发最终结果的生成
        recognizer = session["recognizer"]
        stop_result = recognizer.stop_recognition()

        # Get final results (包含停止时生成的最终结果)
        final_results = session["results"]

        # Clean up session
        del _recognition_sessions[session_id]

        return JsonResponse(
            {
                "status": "success",
                "final_results": final_results,
                "message": "实时识别会话已结束",
            }
        )

    except Exception as e:
        logger.error(f"Error stopping realtime recognition: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


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
