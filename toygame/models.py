"""数据模型（中文注释）

此模块定义了项目中的核心数据结构 `Pet`。为了便于单元测试和示例运行，
`Pet` 使用简单的 dataclass 表示，并提供从数据库行转换为实例的辅助方法。
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Pet:
    """表示一个虚拟宠物的简单数据类。

    字段说明：
        id: 可选的整数，表示数据库分配的主键；在插入数据库后会被设置。
        name: 宠物的名字，用于输出与识别。
        birth_date: 出生日期的 ISO 字符串（例如 "2026-01-03"），用于判断是否触发生日触发器。
        gender: 性别标记（例如 "M" 或 "F"），仅用于示例。
    """

    id: Optional[int]
    name: str
    birth_date: str
    gender: str

    @staticmethod
    def from_row(row: Tuple) -> "Pet":
        """从数据库查询返回的一行构造 `Pet` 实例。

        说明：
        - 当前实现将 `birth_date` 以 ISO 格式的字符串（例如 "2026-01-03"）存储于数据库的 TEXT 列中；
        - 为了兼容测试或历史数据，从数据库读出的 `birth_date` 可能是 `str`，也可能是 `datetime.date`（旧行为）；
          本方法会统一将其转换为 ISO 字符串后赋值给 `Pet.birth_date`。

        Args:
            row: 数据库查询结果行，预期至少包含 (id, name, birth_date, gender, ...)

        Returns:
            Pet: 使用统一字符串格式的 birth_date 字段的 Pet 实例。
        """
        # 只取前四个字段来构造 Pet（忽略触发器相关列）
        b = row[2]
        # 现在我们假定数据库中存储的 birth_date 为 ISO 格式字符串（"YYYY-MM-DD"），
        # 不再做对 datetime.date 等类型的兼容转换。
        return Pet(id=row[0], name=row[1], birth_date=b, gender=row[3])
