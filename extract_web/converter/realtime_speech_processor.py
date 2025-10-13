"""
智能文档转换工作室 - 实时语音识别处理器
========================================

【模块功能概述】
本模块负责通过阿里云 DashScope API 实现实时语音识别，支持中英文，兼容 DashScope WebSocket 流式接口，面向“智能文档转换工作室”前后端实时语音识别场景。核心目标是实现前后端流式同步，确保前端能实时显示 DashScope 返回的临时（is_final: false）和最终（is_final: true）识别结果。

【设计说明与踩坑记录】
--------------------------------------
1. DashScope WebSocket 返回的识别结果分为临时（is_final: false）和最终（is_final: true），同一句话会多次推送临时结果，最终结果只推送一次。
2. 前端需“边说边出字”，每次轮询都能拿到所有新结果，且不能重复显示。
3. 早期方案采用 session['results'] 作为 Python list，前端每次轮询后端就清空该 list。但多线程/异步环境下，list 可能出现丢失、重复、竞争等问题。
4. DashScope 的临时结果和最终结果都可能多次推送，且前端和后端轮询频率不一致，单纯靠 list.pop/clear 很难保证“每条结果只推送一次且不丢失”。
5. 解决方案：
   - 在 RealtimeSpeechRecognizer 内部维护 self.all_results，每收到一次 DashScope 消息（无论临时还是最终）都 append 进去。
   - get_all_results() 方法每次返回当前所有结果并清空，确保前端每次轮询都能拿到所有新内容。
   - 前端只需根据 is_final 字段区分渲染，无需关心去重和顺序。
   - 这样避免了多线程 list 竞争、重复消费、丢失等问题。
6. 计数挑战：
   - 不能简单用“结果条数”计数，因为同一句话的临时结果会多次覆盖，最终结果才算定稿。
   - 采用“每次收到就推送，前端自行决定如何展示”，保证体验和数据完整性。
7. 日志设计：
   - 关键流程、异常、识别结果、同步点均有详细日志，便于排查。
8. 最佳实践总结：
   - 后端只负责收集和推送所有新结果，不做去重和覆盖，避免多线程同步难题。
   - 前端根据 is_final 字段和文本内容自行决定 UI 展示。
   - 这样最大程度兼容 DashScope 推送机制和前端实时体验需求。
--------------------------------------

# 变更日志（2025-06-21）
- 新增：实时语音识别前后端流式同步，支持 DashScope 临时/最终结果实时推送，前端可区分 is_final 渲染。
- 优化：后端统一组装所有新识别结果，get_all_results() 每次返回并清空，避免多线程/异步丢失和重复。
- 增强：详细日志，便于排查同步与计数问题。
- 兼容：支持中英文，兼容 DashScope WebSocket 接口。
- 文档：补充详细设计说明与踩坑记录，便于团队维护。
"""

import asyncio
import base64
import json
import logging
import os
import threading
import time
import uuid
import websockets
from queue import Queue, Empty
from typing import Dict, Any, List, Optional, Callable

# 尝试导入 dashscope，如果失败则不影响功能
try:
    import dashscope
except ImportError:
    dashscope = None

# Configure logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s %(process)d %(thread)d %(message)s"


def _get_logger():
    logger = logging.getLogger("ocr_system")
    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT)
        file_handler = logging.FileHandler("app.log", encoding="utf-8-sig")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        logger.propagate = False

    logger.setLevel(logging.DEBUG)
    return logger


logger = _get_logger()


class RealtimeSpeechRecognizer:
    """阿里云 DashScope Paraformer 实时语音识别器"""

    def __init__(self, api_key: str, result_handler: Callable[[Dict], None] = None):
        self.api_key = api_key
        self.result_handler = result_handler or self._default_result_handler
        self.websocket = None
        self.task_id = None
        self.is_active = False
        self.audio_queue = Queue()
        self.send_thread = None
        self.receive_thread = None
        self.final_results = []

        # 新增：存储所有识别结果（临时+最终）
        self.all_results = []

        # WebSocket URL and headers
        self.ws_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
        self.headers = {
            "Authorization": f"bearer {self.api_key}",
            "X-DashScope-DataInspection": "enable",
        }

        # Recognition configuration
        self.config = {
            "model": "paraformer-realtime-v2",
            "format": "pcm",
            "sample_rate": 16000,
            "language_hints": ["zh", "en"],
            "disfluency_removal_enabled": False,
            "punctuation_prediction_enabled": True,
            "inverse_text_normalization_enabled": True,
        }

        logger.info("实时语音识别器初始化完成")

    def _default_result_handler(self, result: Dict[str, Any]):
        """默认结果处理器"""
        logger.info(f"识别结果: {result}")

    async def _connect_websocket(self):
        """建立 WebSocket 连接"""
        try:
            logger.info("正在连接到 DashScope WebSocket 服务...")

            # 将 self.headers 作为 extra_headers 参数传递
            self.websocket = await websockets.connect(
                self.ws_url, extra_headers=self.headers
            )
            logger.info("WebSocket 连接建立成功")
            return True

        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            return False

    async def _send_run_task_command(self):
        """发送 run-task 指令"""
        self.task_id = str(uuid.uuid4())

        run_task_cmd = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.config["model"],
                "parameters": {
                    "format": self.config["format"],
                    "sample_rate": self.config["sample_rate"],
                    "language_hints": self.config["language_hints"],
                    "disfluency_removal_enabled": self.config[
                        "disfluency_removal_enabled"
                    ],
                    "punctuation_prediction_enabled": self.config[
                        "punctuation_prediction_enabled"
                    ],
                    "inverse_text_normalization_enabled": self.config[
                        "inverse_text_normalization_enabled"
                    ],
                },
                "input": {},
            },
        }

        await self.websocket.send(json.dumps(run_task_cmd))
        logger.info(f"已发送 run-task 指令，task_id: {self.task_id}")

    async def _send_finish_task_command(self):
        """发送 finish-task 指令"""
        if not self.task_id:
            return

        finish_task_cmd = {
            "header": {
                "action": "finish-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {"input": {}},
        }

        await self.websocket.send(json.dumps(finish_task_cmd))
        logger.info("已发送 finish-task 指令")

    async def _handle_websocket_message(self, message):
        """处理 WebSocket 消息"""
        try:
            logger.debug(f"[DEBUG] Raw WebSocket message: {message}")
            data = json.loads(message)
            event = data.get("header", {}).get("event")
            logger.debug(f"[DEBUG] WebSocket event type: {event}")

            if event == "task-started":
                logger.info("任务已启动，可以开始发送音频数据")
                self.is_active = True

            elif event == "result-generated":
                # 处理识别结果
                sentence = data.get("payload", {}).get("output", {}).get("sentence", {})
                logger.debug(f"[DEBUG] result-generated payload: {sentence}")
                if sentence:
                    result = {
                        "text": sentence.get("text", ""),
                        "is_final": sentence.get("end_time") is not None,
                        "begin_time": sentence.get("begin_time"),
                        "end_time": sentence.get("end_time"),
                        "confidence": 0.95,  # DashScope 不返回置信度，设置默认值
                        "timestamp": time.time(),
                    }
                    if result["text"].strip():
                        logger.info(
                            f"收到识别结果: {result['text']} (final: {result['is_final']})"
                        )
                        # 新增：所有结果都存储
                        self.all_results.append(result)
                        if result["is_final"]:
                            self.final_results.append(result)
                        if self.result_handler:
                            logger.debug(
                                f"[DEBUG] Calling result_handler with: {result}"
                            )
                            self.result_handler(result)

            elif event == "task-finished":
                logger.info("任务已完成")
                self.is_active = False

            elif event == "task-failed":
                error_code = data.get("header", {}).get("error_code")
                error_message = data.get("header", {}).get("error_message")
                logger.error(f"任务失败: {error_code} - {error_message}")
                self.is_active = False
            else:
                logger.warning(
                    f"[DEBUG] Unhandled WebSocket event: {event}, data: {data}"
                )

        except Exception as e:
            logger.error(f"处理 WebSocket 消消息时出错: {e}, message: {message}")

    async def _receive_messages(self):
        """接收 WebSocket 消息的协程"""
        try:
            async for message in self.websocket:
                await self._handle_websocket_message(message)
                if not self.is_active:
                    break
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket 连接已关闭: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"接收消息时出错: {e}")
        finally:
            logger.info("消息接收循环结束")
            self.is_active = False  # 确保接收端关闭也停止整个任务

    async def _send_audio_data_async(self):
        """发送音频数据的协程"""
        logger.info("音频发送循环启动")
        # 修复：等待 is_active 变为 True 再进入主循环
        while not self.is_active:
            await asyncio.sleep(0.01)
        try:
            while self.is_active:
                try:
                    # 使用非阻塞的 get_nowait()
                    audio_data = self.audio_queue.get_nowait()
                    if audio_data is None:  # 停止信号
                        logger.info("收到音频发送停止信号")
                        break

                    # 发送音频数据
                    await self.websocket.send(audio_data)
                    logger.debug(f"已发送音频数据: {len(audio_data)} 字节")

                except Empty:
                    # 当队列为空时，短暂休眠并让出控制权，以允许其他协程运行
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    logger.error(f"发送音频数据时出错: {e}")
                    self.is_active = False  # 发送出错时也停止任务
                    break
        finally:
            logger.info("音频发送循环结束")

    def start_recognition(self, language_hints: List[str] = None) -> bool:
        """启动实时语音识别"""
        logger.info(
            f"[TEST] start_recognition called, language_hints: {language_hints}"
        )

        if self.is_active:
            logger.warning("识别已经在运行中")
            return True

        try:
            # 更新语言配置
            if language_hints:
                self.config["language_hints"] = language_hints
                logger.info(f"配置已更新: {{'language_hints': {language_hints}}}")

            # 在新线程中运行异步识别
            self.recognition_thread = threading.Thread(
                target=self._run_recognition_async, daemon=True
            )
            self.recognition_thread.start()

            # 等待连接建立
            max_wait = 10  # 最多等待10秒
            wait_time = 0
            while not self.is_active and wait_time < max_wait:
                time.sleep(0.1)
                wait_time += 0.1

            if self.is_active:
                logger.info("实时语音识别启动成功")
                return True
            else:
                logger.error("实时语音识别启动超时")
                return False

        except Exception as e:
            logger.error(f"启动实时语音识别失败: {e}")
            return False

    def _run_recognition_async(self):
        """在新线程中运行异步识别逻辑"""
        try:
            asyncio.run(self._async_recognition_loop())
        except Exception as e:
            logger.error(f"异步识别循环出错: {e}")

    async def _async_recognition_loop(self):
        """异步识别主循环"""
        try:
            # 建立 WebSocket 连接
            if not await self._connect_websocket():
                return

            # 发送 run-task 指令
            await self._send_run_task_command()

            # 启动接收消息和发送音频的协程
            receive_task = asyncio.create_task(self._receive_messages())
            send_task = asyncio.create_task(self._send_audio_data_async())

            # 等待任务完成
            await asyncio.gather(receive_task, send_task)

        except Exception as e:
            logger.error(f"异步识别循环出错: {e}")
        finally:
            # 确保在循环结束后，无论成功或失败，都尝试优雅关闭
            logger.info("异步识别循环结束，正在进行清理...")
            if self.websocket and self.websocket.open:
                try:
                    await self._send_finish_task_command()
                    # 等待服务器响应 task-finished，或者超时关闭
                    await asyncio.wait_for(self.websocket.close(), timeout=5.0)
                    logger.info("WebSocket 连接已成功关闭")
                except Exception as close_e:
                    logger.error(f"关闭 WebSocket 时出错: {close_e}")
            self.is_active = False

    def send_audio_data(self, audio_data: bytes) -> bool:
        """发送音频数据"""
        logger.debug(f"[TEST] send_audio_data called, data length: {len(audio_data)}")

        if not self.is_active:
            logger.warning("识别服务未激活")
            return False

        try:
            self.audio_queue.put(audio_data, timeout=1.0)
            return True
        except Exception as e:
            logger.error(f"音频数据入队失败: {e}")
            return False

    def stop_recognition(self) -> Dict[str, Any]:
        """停止实时语音识别"""
        logger.info("[TEST] stop_recognition called")

        if not self.is_active:
            logger.warning("识别服务已经不在运行状态")
            return {"status": "success", "message": "识别已停止"}

        try:
            # 发送停止信号到音频队列，让发送循环优雅退出
            self.audio_queue.put(None)
            # 等待识别线程结束
            if self.recognition_thread and self.recognition_thread.is_alive():
                self.recognition_thread.join(timeout=10.0)  # 增加超时时间

            logger.info("实时语音识别已停止")
            return {
                "status": "success",
                "message": "识别已停止",
                "final_results": self.final_results,
            }

        except Exception as e:
            logger.error(f"停止识别时出错: {e}")
            return {"status": "error", "message": str(e)}

    def is_recognition_active(self) -> bool:
        """检查识别是否处于激活状态"""
        return self.is_active

    def get_configuration(self) -> Dict[str, Any]:
        """获取当前识别配置"""
        return self.config.copy()

    def update_configuration(self, **kwargs) -> bool:
        """更新识别配置"""
        try:
            for key, value in kwargs.items():
                if key in self.config:
                    self.config[key] = value
                else:
                    logger.warning(f"未知的配置参数: {key}")

            logger.info(f"配置已更新: {kwargs}")
            return True

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

    def get_all_results(self) -> List[Dict]:
        """获取所有识别结果（临时+最终），并清空缓存（一次性返回给前端）"""
        results = self.all_results.copy()
        self.all_results.clear()
        return results


def create_realtime_recognizer(
    result_handler: Callable[[Dict], None] = None, language_hints: List[str] = None
) -> Optional[RealtimeSpeechRecognizer]:
    """创建实时语音识别器"""
    logger.info(
        f"[TEST] create_realtime_recognizer called, language_hints: {language_hints}"
    )

    try:
        # 获取 API Key
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key and hasattr(dashscope, "api_key") and dashscope.api_key:
            api_key = dashscope.api_key

        if not api_key:
            logger.error("未找到 DASHSCOPE_API_KEY 环境变量或 dashscope.api_key 配置")
            return None

        # 创建识别器
        recognizer = RealtimeSpeechRecognizer(
            api_key=api_key, result_handler=result_handler
        )

        # 设置语言提示
        if language_hints:
            recognizer.update_configuration(language_hints=language_hints)

        logger.info("实时语音识别器创建成功")
        return recognizer

    except Exception as e:
        logger.error(f"创建实时语音识别器失败: {e}")
        return None


# 全局识别器实例管理
_global_recognizer: Optional[RealtimeSpeechRecognizer] = None


def get_global_recognizer() -> Optional[RealtimeSpeechRecognizer]:
    """获取全局识别器实例"""
    return _global_recognizer


def set_global_recognizer(recognizer: RealtimeSpeechRecognizer):
    """设置全局识别器实例"""
    global _global_recognizer
    _global_recognizer = recognizer


def cleanup_global_recognizer():
    """清理全局识别器实例"""
    global _global_recognizer
    if _global_recognizer:
        _global_recognizer.stop_recognition()
        _global_recognizer = None
