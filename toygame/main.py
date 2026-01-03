"""主程序与辅助函数（中文注释）。

模块职责：
- 随机创建若干个 Pet 并保存到数据库；
- 为每个 Pet 轮询触发器并在触发时记录计数与输出信息。

注：为了方便测试，`run_game` 接受一个显式的 `DB` 实例和 `num_pets` 参数，
测试可传入临时数据库来断言行为。
"""
from datetime import datetime, timedelta, date
import random

from .db import DB
from .models import Pet
from .triggers import BirthTrigger, WakeUpTimer, BedTimer, BreakfastTimer, LunchTimer, DinnerTimer


def random_pet(name_prefix: str, idx: int) -> Pet:
    """生成一个具有随机出生日期和随机性别的 Pet 实例。

    出生日期随机选择过去 30 天内的某一天，从而在示例运行中能
    同时触发或不触发生日触发器，增加演示效果。birth_date 以 ISO 字符串保存。
    """
    # 在过去 0 到 30 天之间随机选择一个天数作为出生日期的偏移
    days_ago = random.randint(0, 30)
    birth = (date.today() - timedelta(days=days_ago)).isoformat()
    # 使用简单的性别表示（仅用于示例）
    gender = random.choice(["M", "F"])  # simple gender choices
    return Pet(id=None, name=f"{name_prefix}{idx}", birth_date=birth, gender=gender)


def run_game(db: DB, num_pets: int = 5):
    """执行一次游戏循环：创建宠物并轮询触发器。

    Args:
        db: DB 实例，用于持久化 Pet 和更新触发计数。
        num_pets: 本次运行要创建的宠物数量。
    """
    # 创建并插入若干宠物
    pets = [random_pet("pet", i + 1) for i in range(num_pets)]
    for p in pets:
        db.add_pet(p)

    # 要轮询的触发器列表；可扩展以添加更多触发逻辑
    triggers = [
        BirthTrigger(),
        WakeUpTimer(),
        BreakfastTimer(),
        LunchTimer(),
        DinnerTimer(),
        BedTimer(),
    ]

    # 对数据库中的每只宠物执行触发器逻辑
    for pet in db.list_pets():
        for trig in triggers:
            fired = trig.fire(pet, db)
            if fired:
                # 仅在交互运行时打印信息，测试中不依赖打印
                print(f"Triggered {trig.name} for pet {pet.name}")


def main():
    """运行游戏，使用文件数据库 'pets.db' 来持久化数据（演示用途）。"""
    db = DB("pets.db")
    run_game(db)


if __name__ == "__main__":
    main()
