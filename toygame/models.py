"""数据模型（中文注释）

此模块定义了项目中的核心数据结构 `Pet`。为了便于单元测试和示例运行，
`Pet` 使用简单的 dataclass 表示，并提供从数据库行转换为实例的辅助方法。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class Pet:
    """表示一个虚拟宠物的简单数据类。

    字段说明：
        id: 可选的整数，表示数据库分配的主键；在插入数据库后会被设置。
        name: 宠物的名字，用于输出与识别。
        birth_date: 出生日期的 ISO 字符串（例如 "2026-01-03"）。
        gender: 性别标记（例如 "M" 或 "F"）。
        mbti: MBTI 性格代码（如 "INTJ"）。
        *_trigger_times: 各类触发器的触发时间列表（datetime 列表），由数据库中的 JSON 列解析而来。
        chat_history: 存储与宠物的聊天历史
    """

    id: Optional[int]
    name: str
    birth_date: str
    gender: str
    mbti: str = ""

    birth_trigger_times: Optional[List[datetime]] = None
    wakeup_trigger_times: Optional[List[datetime]] = None
    bed_trigger_times: Optional[List[datetime]] = None
    breakfast_trigger_times: Optional[List[datetime]] = None
    lunch_trigger_times: Optional[List[datetime]] = None
    dinner_trigger_times: Optional[List[datetime]] = None
    chat_history: Optional[List[Any]] = None

    @staticmethod
    def _parse_iso_list(text: Any):
        """
        Args:
            text: JSON文本或列表

        Returns:
            list: 解析后的datetime列表
        """
        import json

        if not text:
            return []
        if isinstance(text, list):
            lst = text
        else:
            try:
                lst = json.loads(text)
            except Exception:
                return []
        out = []
        for s in lst:
            try:
                out.append(datetime.fromisoformat(s))
            except Exception:
                continue
        return out

    @staticmethod
    def from_row(row: Any) -> "Pet":
        """
        Args:
            row: 数据库查询返回的一行数据`Pet` 实例

        Returns:
            Pet: 构造的宠物对象
        """
        # 优先使用列名访问，提高代码健壮性
        pet = Pet(
            id=row["id"],
            name=row["name"],
            birth_date=str(row["birth_date"]),
            gender=row["gender"],
            mbti=row["mbti"] if "mbti" in row.keys() else "",
        )

        # 动态解析所有触发器时间列
        trigger_fields = [
            "birth_trigger_times",
            "wakeup_trigger_times",
            "bed_trigger_times",
            "breakfast_trigger_times",
            "lunch_trigger_times",
            "dinner_trigger_times",
        ]
        for field in trigger_fields:
            if field in row.keys():
                setattr(pet, field, Pet._parse_iso_list(row[field]))
            else:
                setattr(pet, field, [])

        # 解析聊天历史
        try:
            if "chat_history" in row.keys():
                text = row["chat_history"]
                pet.chat_history = json.loads(text) if text else []
            else:
                pet.chat_history = []
        except Exception:
            pet.chat_history = []

        return pet
