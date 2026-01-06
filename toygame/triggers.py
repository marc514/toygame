"""触发器（Trigger）模块。

模块提供一个抽象基类 `Trigger`，以及多个具体实现：
- `BirthTrigger`：当天为宠物生日时触发；
- `TimerTrigger`：在指定小时触发（派生类如 `DinnerTimer`、`WakeUpTimer` 等）。

触发后会通过数据库接口将触发发生的时间点以 ISO 字符串追加到对应宠物的触发器时间历史中（JSON 列），
以便保留完整触发记录（而不是简单计数）。

行为与约定：
- `Trigger.fire` 在满足条件且该宠物在**当天尚未由同名触发器触发**的情况下才会记录触发（即一天只记录一次）；
- `Pet.birth_date` 在模型与数据库中约定为 ISO 格式字符串（"YYYY-MM-DD"），触发器不再对 date 对象做兼容转换；
- 触发时间由本模块的 `datetime.now()` 提供（方便在测试中通过 monkeypatch 替换）。
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from .db import DB
from .events import Event, GeminiAPIEvent
from .models import Pet


class Trigger(ABC):
    """所有触发器的基类。

    子类需要定义 `name`（用于映射到数据库列）并实现 `should_trigger`。
    """

    name: str
    events: List[Event]

    def __init__(self):
        self.events = []

    @abstractmethod
    def should_trigger(self, pet: Pet, db: DB = None) -> bool:
        """
        Args:
            pet: 触发事件的宠物
            db: 数据库实例，可选参数，用于频率控制等需要查询数据库的逻辑

        Returns:
            bool: 是否应该触发
        """

    def fire(self, pet: Pet, db: DB, **kwargs) -> bool:
        """
        Args:
            pet: 触发事件的宠物
            db: 数据库实例

        Returns:
            bool: 是否成功触发
        注：触发时间以 ISO 格式字符串追加到数据库中对应触发器的 JSON 列（由 `DB.record_trigger_time` 完成），
        同时使用本模块的 `datetime.now()`（便于在测试中通过 monkeypatch 控制当前时间）。
        频率控制逻辑在子类的should_trigger方法中实现。
        同时会触发注册到此触发器的事件。
        """
        if not self.should_trigger(pet, db):
            return False

        # 记录触发时间
        db.record_trigger_time(pet.id, self.name, datetime.now())

        # 触发注册的事件
        for event in self.events:
            event.execute(self.name, pet, db, **kwargs)

        return True

    def add_event(self, event: Event):
        """
        Args:
            event: 要添加的事件
        """
        self.events.append(event)

    def remove_event(self, event: Event):
        """
        Args:
            event: 要移除的事件
        """
        if event in self.events:
            self.events.remove(event)


class BirthTrigger(Trigger):
    """生日触发器：当日期与宠物出生日期相同时触发。

    注意：`Pet.birth_date` 在数据库与模型中约定为 ISO 格式字符串（"YYYY-MM-DD"）；
    不再考虑 `datetime.date` 的兼容，`birth_date` 必须为 ISO 字符串。"""

    name = "birth"

    def __init__(self):
        super().__init__()
        # 自动从环境变量获取 API Key 并注册 GeminiAPIEvent
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.add_event(GeminiAPIEvent(api_key))

    def should_trigger(self, pet: Pet, db: DB = None) -> bool:
        """
        Args:
            pet: 触发事件的宠物
            db: 数据库实例，可选参数

        Returns:
            bool: 是否为宠物生日
        """
        now = datetime.now()
        # 解析出生日期字符串为月日
        birth_parts = pet.birth_date.split("-")
        birth_month = int(birth_parts[1])
        birth_day = int(birth_parts[2])
        # 比较月日，忽略年份
        is_birthday = now.month == birth_month and now.day == birth_day

        # 检查当天是否已经触发过，生日触发器一天只触发一次
        if db and db.triggered_today(pet.id, self.name, now.date()):
            return False

        return is_birthday

    def fire(self, pet: Pet, db: DB, **kwargs) -> bool:
        """
        覆盖基类的 fire 方法，在触发时传入特定的生日 prompt。
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        prompt = f"今天是 {date_str}。宠物 {pet.name}（MBTI: {pet.mbti}）正在过生日！请用中文提供一个有趣的庆祝回复。"
        return super().fire(pet, db, prompt=prompt, **kwargs)


class TimerTrigger(Trigger):
    """计时触发器基类：子类通过设置 `name` 与 `hour` 实现不同时间点的触发。"""

    name = "timer"
    hour: int = 0

    def should_trigger(self, pet: Pet, db: DB = None) -> bool:
        """
        Args:
            pet: 触发事件的宠物
            db: 数据库实例，可选参数

        Returns:
            bool: 当前小时是否匹配
        """
        now = datetime.now()
        is_hour_match = now.hour == self.hour

        # 检查当天是否已经触发过，计时触发器一天只触发一次
        if db and db.triggered_today(pet.id, self.name, now.date()):
            return False

        return is_hour_match


class WakeUpTimer(TimerTrigger):
    """起床触发器，例如 07:00。"""

    name = "wakeup"
    hour = 7


class BedTimer(TimerTrigger):
    """上床睡觉触发器，例如 22:00。"""

    name = "bed"
    hour = 22


class BreakfastTimer(TimerTrigger):
    """早餐触发器，例如 08:00。"""

    name = "breakfast"
    hour = 8


class LunchTimer(TimerTrigger):
    """午餐触发器，例如 12:00。"""

    name = "lunch"
    hour = 12


class DinnerTimer(TimerTrigger):
    """晚餐触发器，例如 18:00。"""

    name = "dinner"
    hour = 18
