"""主程序与辅助函数（中文注释）。

模块职责：
- 随机创建若干个 Pet 并保存到数据库；
- 为每个 Pet 轮询触发器并在触发时记录计数与输出信息。

注：为了方便测试，`run_game` 接受一个显式的 `DB` 实例并仅负责轮询触发器；若需要创建宠物，请先调用 `create_pets`。
"""

from datetime import datetime, timedelta, date
import random

from .db import DB
from .enums import MBTI_LIST
from .models import Pet
from .triggers import (
    BirthTrigger,
    WakeUpTimer,
    BedTimer,
    BreakfastTimer,
    LunchTimer,
    DinnerTimer,
)


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
    # 使用统一定义的 MBTI 值（从 toygame.enums 导入），简化维护
    mbti = random.choice(MBTI_LIST)
    # 使用 0 作为插入前占位 id（必须提供 id）
    return Pet(
        id=0, name=f"{name_prefix}{idx}", birth_date=birth, gender=gender, mbti=mbti
    )


def create_pets(db: DB, num_pets: int = 5):
    """在数据库中创建若干随机宠物。"""
    # 创建并插入若干宠物
    pets = [random_pet("pet", i + 1) for i in range(num_pets)]
    for p in pets:
        db.add_pet(p)


def run_game(db: DB):
    """执行一次游戏循环：轮询数据库中的所有宠物并运行触发器逻辑。

    行为说明：
    - `run_game` 不负责创建宠物；若在测试或演示中需要先创建宠物，请使用 `create_pets`；
    - 函数会对数据库中所有宠物轮询触发器，触发器负责决定是否记录触发时间（并保证同一天不重复记录）。
    """

    # 要轮询的触发器列表（独立事件触发）
    triggers = [
        BirthTrigger(),
        WakeUpTimer(),
        BreakfastTimer(),
        LunchTimer(),
        DinnerTimer(),
        BedTimer(),
    ]

    # 对数据库中的每个 ID 执行触发器逻辑（todo：并行化 / 优化为时间线触发）
    for pet in db.list_pets():
        for trig in triggers:
            fired = trig.fire(pet, db)
            if fired:
                # 仅在交互运行时打印信息，测试中不依赖打印
                print(f"Triggered {trig.name} for pet {pet.name}")
    # todo: 联合事件触发，关系型数据库


def main():
    """运行游戏，使用文件数据库 'pets.db' 来持久化数据（演示用途）。"""
    db = DB("pets.db")
    create_pets(db, num_pets=5)
    run_game(db)


if __name__ == "__main__":
    main()
