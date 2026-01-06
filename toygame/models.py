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

        def _get(r, key, idx):
            try:
                return r[key]
            except Exception:
                return r[idx]

        b = _get(row, "birth_date", 2)
        if not isinstance(b, str):
            b = str(b)

        pet = Pet(
            id=_get(row, "id", 0),
            name=_get(row, "name", 1),
            birth_date=b,
            gender=_get(row, "gender", 3),
            mbti=_get(row, "mbti", 4) or "",
        )

        # 解析触发器时间列（若查询包含这些列）
        # 使用长度判断以兼容仅查询部分列的情况
        try:
            pet.birth_trigger_times = Pet._parse_iso_list(
                _get(row, "birth_trigger_times", 5)
            )
        except Exception:
            pet.birth_trigger_times = []
        try:
            pet.wakeup_trigger_times = Pet._parse_iso_list(
                _get(row, "wakeup_trigger_times", 6)
            )
        except Exception:
            pet.wakeup_trigger_times = []
        try:
            pet.bed_trigger_times = Pet._parse_iso_list(
                _get(row, "bed_trigger_times", 7)
            )
        except Exception:
            pet.bed_trigger_times = []
        try:
            pet.breakfast_trigger_times = Pet._parse_iso_list(
                _get(row, "breakfast_trigger_times", 8)
            )
        except Exception:
            pet.breakfast_trigger_times = []
        try:
            pet.lunch_trigger_times = Pet._parse_iso_list(
                _get(row, "lunch_trigger_times", 9)
            )
        except Exception:
            pet.lunch_trigger_times = []
        try:
            pet.dinner_trigger_times = Pet._parse_iso_list(
                _get(row, "dinner_trigger_times", 10)
            )
        except Exception:
            pet.dinner_trigger_times = []

        # 解析聊天历史
        try:
            chat_history_text = _get(row, "chat_history", 11)
            if chat_history_text:
                pet.chat_history = json.loads(chat_history_text)
            else:
                pet.chat_history = []
        except Exception:
            pet.chat_history = []

        return pet
