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
    def execute(self, pet: Pet, db: DB) -> bool:
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
            prompt_template: 提示模板，可以包含{name}, {mbti}, {trigger_name}等占位符
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

            chat = self.client.chats.create(model="gemini-2.0-flash")
            response = chat.send_message(prompt)
            print(f"Gemini: {response.text}\n")

            # 显示当前聊天上下文
            context = chat.get_history()
            print(f"Current chat context: {context}")
            print(f"Current chat context length: {len(context)}")

            return True

        except Exception as e:
            print(f"Error calling Gemini API for pet {pet.name}: {str(e)}")
            return False
