"""事件系统模块。

定义事件基类和各种具体事件实现。
"""

import asyncio
import os
import time
from abc import ABC, abstractmethod

from google import genai
from loguru import logger

from .db import DB
from .models import Pet


class Event(ABC):
    """事件基类，所有事件应继承此类"""

    @abstractmethod
    async def execute(self, trigger_name: str, pet: Pet, db: DB, **kwargs) -> bool:
        """执行事件，返回是否成功执行"""
        pass


class GeminiAPIEvent(Event):
    """Gemini API事件，用于调用Gemini API获取对话上下文"""

    def __init__(
        self,
        api_key: str,
    ):
        """
        初始化Gemini API事件

        Args:
            api_key: Gemini API密钥
        """

        try:
            from google import genai
        except ImportError:
            logger.error(
                "Google genai library not installed. Please install google-genai."
            )
            raise

        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    async def execute(self, trigger_name: str, pet: Pet, db: DB, **kwargs) -> bool:
        """
        执行Gemini API调用

        Args:
            trigger_name: 触发器名称
            pet: 触发事件的宠物
            db: 数据库实例

        Returns:
            bool: API调用是否成功
        """

        try:
            # 1. 准备 Prompt
            prompt = kwargs.get("prompt") or (
                f"Pet {pet.name} with MBTI {pet.mbti} is experiencing {trigger_name}. "
                "Provide a fun response in chinese."
            )

            # 2. 加载聊天历史
            chat_history = db.get_chat_history(pet.id) if pet.id is not None else []
            logger.debug(f"Pet {pet.name} chat history loaded.")

            # 3. 执行带重试的 API 调用
            max_retries = 3
            response = None

            for attempt in range(max_retries):
                try:
                    # 注意：aio.chats.create 是同步方法，返回 AsyncChat 对象
                    chat = self.client.aio.chats.create(
                        model="gemini-2.0-flash", history=chat_history
                    )
                    response = await chat.send_message(prompt)
                    break  # 成功则跳出循环
                except Exception as e:
                    if "54" in str(e) or "reset" in str(e).lower():
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(
                                f"Connection reset, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                    raise e

            if not response:
                return False

            logger.info(f"Gemini response for {pet.name}: {response.text}")

            # 4. 更新并保存历史记录
            context = chat.get_history()
            serializable_context = []
            for message in context:
                message_dict = {
                    "role": getattr(message, "role", "user"),
                    "parts": [],
                }
                # 获取消息内容部分
                parts = getattr(message, "parts", [])
                for part in parts:
                    # 尝试提取文本内容
                    if hasattr(part, "text"):
                        # 确保文本内容是字符串类型
                        message_dict["parts"].append({"text": str(part.text)})
                    elif hasattr(part, "to_dict"):
                        message_dict["parts"].append(part.to_dict())
                    else:
                        message_dict["parts"].append(str(part))

                serializable_context.append(message_dict)
            print(f"len(serializable_context): {len(serializable_context)}\n")

            # 将聊天历史存入数据库
            if pet.id is not None:
                db.update_chat_history(pet.id, serializable_context)

            return True

        except Exception as e:
            logger.error(f"Error calling Gemini API for pet {pet.name}: {str(e)}")
            return False
