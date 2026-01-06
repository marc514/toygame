"""主程序与辅助函数（中文注释）。

模块职责：
- 随机创建若干个 Pet 并保存到数据库；
- 为每个 Pet 轮询触发器并在触发时记录计数与输出信息。

注：为了方便测试，`run_game` 接受一个显式的 `DB` 实例并仅负责轮询触发器；若需要创建宠物，请先调用 `create_pets`。
"""

import random
from datetime import date, timedelta

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
    """
    Args:
        name_prefix: 宠物名字前缀
        idx: 宠物索引号

    Returns:
        Pet: 随机生成的宠物对象
    出生日期随机选择过去 30 天内的某一天，birth_date 以 ISO 字符串保存
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


def create_pets(db: DB, num_pets: int = 3):
    """
    Args:
        db: 数据库实例
        num_pets: 要创建的宠物数量，默认为3
    """
    # 创建并插入若干宠物
    pets = [random_pet("pet", i + 1) for i in range(num_pets)]
    for p in pets:
        db.add_pet(p)


def run_game(db: DB):
    """
    `run_game` 不负责创建宠物；若在测试或演示中需要先创建宠物，请使用 `create_pets`；

    Args:
        db: 数据库实例
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
