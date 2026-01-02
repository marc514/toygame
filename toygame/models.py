"""数据模型（中文注释）

此模块定义了项目中的核心数据结构 `Pet`。为了便于单元测试和示例运行，
`Pet` 使用简单的 dataclass 表示，并提供从数据库行转换为实例的辅助方法。
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple


@dataclass
class Pet:
    """表示一个虚拟宠物的简单数据类。

    字段说明：
        id: 可选的整数，表示数据库分配的主键；在插入数据库后会被设置。
        name: 宠物的名字，用于输出与识别。
        birth_date: 出生日期（datetime.date），用于判断是否触发生日触发器。
        gender: 性别标记（例如 "M" 或 "F"），仅用于示例。
    """

    id: Optional[int]
    name: str
    birth_date: date
    gender: str

    @staticmethod
    def from_row(row: Tuple) -> "Pet":
        """从数据库查询返回的一行构造 `Pet` 实例。

        数据库查询通常会返回类似 (id, name, birth_date, gender, birth_trigger_count, timer_trigger_count)
        的行；本方法只关注前 4 个字段并忽略计数列，从而创建 Pet 对象。
        """
        # 只取前四个字段来构造 Pet（忽略触发器计数列）
        return Pet(id=row[0], name=row[1], birth_date=row[2], gender=row[3])
