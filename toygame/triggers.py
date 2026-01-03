"""触发器（Trigger）模块，带中文注释。

模块提供一个抽象基类 `Trigger`，以及多个具体实现：
- `BirthTrigger`：当天为宠物生日时触发；
- `TimerTrigger`：在指定小时触发（派生类如 `DinnerTimer`、`WakeUpTimer` 等）。

触发后会通过数据库接口将触发发生的时间点以 ISO 字符串追加到对应宠物的触发器时间历史中，
以便保留完整触发记录（而不是简单计数）。

注意：`Pet.birth_date` 在模型与数据库中以 ISO 格式的字符串表示（"YYYY-MM-DD"）；
触发器实现会对可能为 `date` 的旧值做兼容处理并统一比较。"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .models import Pet
from .db import DB


class Trigger(ABC):
    """所有触发器的基类。

    子类需要定义 `name`（用于映射到数据库列）并实现 `should_trigger`。
    """

    name: str

    @abstractmethod
    def should_trigger(self, pet: Pet) -> bool:
        """判断是否应该触发。返回 True 表示需要触发。"""

    def fire(self, pet: Pet, db: DB) -> bool:
        """如果满足触发条件并且当天尚未触发过，则在数据库上记录触发时间并返回 True；
        否则返回 False。"""
        if not self.should_trigger(pet):
            return False
        # 使用触发器模块的 datetime（便于测试时通过 monkeypatch 控制当前时间）
        today = datetime.now().date()
        # 若当日已触发过则不再触发
        if db.triggered_today(pet.id, self.name, today):
            return False
        db.record_trigger_time(pet.id, self.name, datetime.now())
        return True


class BirthTrigger(Trigger):
    """生日触发器：当日期与宠物出生日期相同时触发。

    注意：`Pet.birth_date` 在数据库与模型中约定为 ISO 格式字符串（"YYYY-MM-DD"）；
    不再考虑 `datetime.date` 的兼容，`birth_date` 必须为 ISO 字符串。"""

    name = "birth"

    def should_trigger(self, pet: Pet) -> bool:
        now_iso = datetime.now().date().isoformat()
        b = pet.birth_date
        # 假定 b 为 ISO 字符串（"YYYY-MM-DD"）
        return now_iso == b


class TimerTrigger(Trigger):
    """计时触发器基类：子类通过设置 `name` 与 `hour` 实现不同时间点的触发。"""

    name = "timer"
    hour: int = 0

    def should_trigger(self, pet: Pet) -> bool:
        now = datetime.now()
        return now.hour == self.hour


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
    """晚餐触发器，例如 18:00（6pm）。"""

    name = "dinner"
    hour = 18
