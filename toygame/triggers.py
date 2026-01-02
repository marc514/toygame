"""触发器（Trigger）模块，带中文注释。

模块提供一个抽象基类 `Trigger`，以及两个具体实现：
- `BirthTrigger`：当天为宠物生日时触发；
- `TimerTrigger`：当当前时间为 18 点（6pm）时触发。

触发后使用数据库接口将对应宠物的计数加 1。
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
    def should_trigger(self, pet: Pet, now: datetime) -> bool:
        """判断是否应该触发。返回 True 表示需要触发。

        传入 `now` 参数是为了让测试变得可控（测试中可以传入任意时间）。
        """

    def fire(self, pet: Pet, db: DB, now: datetime) -> bool:
        """如果满足触发条件，则在数据库上增加对应计数并返回 True，否则返回 False。"""
        if self.should_trigger(pet, now):
            # 使用 DB 的方法来累加计数，以保持状态的一致性。
            db.increment_trigger(pet.id, self.name)
            return True
        return False


class BirthTrigger(Trigger):
    """生日触发器：当日期与宠物出生日期相同时触发。"""

    name = "birth"

    def should_trigger(self, pet: Pet, now: datetime) -> bool:
        # 比较日期（不比较时间部分），当天生日就触发
        return now.date() == pet.birth_date


class TimerTrigger(Trigger):
    """计时触发器：当小时为 18（6pm）时触发。"""

    name = "timer"

    def should_trigger(self, pet: Pet, now: datetime) -> bool:
        # 仅检查小时数是否等于 18，方便在测试中模拟时间
        return now.hour == 18
