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
        """如果满足触发条件并且当天尚未触发过，则在数据库上记录触发时间并返回 True；否则返回 False。

        注：触发时间以 ISO 格式字符串追加到数据库中对应触发器的 JSON 列（由 `DB.record_trigger_time` 完成），
        同时使用本模块的 `datetime.now()`（便于在测试中通过 monkeypatch 控制当前时间）。"""
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
    """晚餐触发器，例如 18:00。"""

    name = "dinner"
    hour = 18
