"""事件系统模块。

定义事件基类和各种具体事件实现。
"""

from google import genai
import os
from abc import ABC, abstractmethod
from typing import Any

from .models import Pet
from .db import DB


class Event(ABC):
    """事件基类，所有事件应继承此类"""

    @abstractmethod
    def execute(self, trigger_name: str, pet: Pet, db: DB) -> bool:
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
            print("Google genai library not installed. Please install google-genai.")
            raise

        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    def execute(self, trigger_name: str, pet: Pet, db: DB) -> bool:
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
            prompt_template: str = (
                "Pet {name} with MBTI {mbti} is experiencing {trigger_name}. Provide a fun response in chinese."
            )
            prompt = prompt_template.format(
                name=pet.name,
                mbti=pet.mbti,
                trigger_name=trigger_name,
            )

            # 从数据库加载聊天历史
            chat_history = db.get_chat_history(pet.id) if pet.id is not None else []
            print(f"chat_history: {chat_history}\n")

            # 创建带有历史记录的chat
            chat = self.client.chats.create(
                model="gemini-2.0-flash", history=chat_history
            )

            response = chat.send_message(prompt)
            print(f"Gemini: {response.text}\n")

            # 获取当前聊天上下文
            context = chat.get_history()
            print(f"Current chat context length: {len(context)}")

            # 将聊天历史转换为可序列化的格式
            serializable_context = []
            for message in context:
                # 将消息对象转换为字典格式
                message_dict = {
                    "role": getattr(message, "role", "unknown"),
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

            # 将聊天历史存入数据库
            if pet.id is not None:
                db.update_chat_history(pet.id, serializable_context)

            return True

        except Exception as e:
            print(f"Error calling Gemini API for pet {pet.name}: {str(e)}")
            return False
