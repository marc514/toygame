"""数据库访问层（中文注释）

本模块封装了对 SQLite 的轻量操作，用于保存和查询 `Pet` 并维护触发器的触发历史。
触发历史以 JSON 文本（ISO 时间字符串列表）保存在单独的列中（例如 `dinner_trigger_times`），
读取时会解析为 `datetime` 列表，写入时以 ISO 时间字符串追加。

设计与约定（重要）：
- `birth_date` 字段以 ISO 格式字符串（"YYYY-MM-DD"）保存在 TEXT 列；
  **强制约定**：调用方必须传入 ISO 字符串，`DB.add_pet` 在遇到非字符串会抛出 TypeError；
- 新增 `mbti` 字段用于演示随机属性（四字母代码，如 "INTJ"），在 DB 中以 TEXT 存储；
- `DB.__init__` 在初始化时会 DROP & CREATE `pets` 表以使用最新 schema（会清除旧数据）——
  这是有意的简化设计（不做自动迁移），使用时请注意数据不可恢复；
- 提供 `triggered_today` 方法以判断某宠物在某日是否已由指定触发器触发；
  `Trigger.fire` 使用此方法实现"同一宠物、同一触发器在同一天只触发一次"的规则。

说明：此模块以教学/原型为目标；生产环境请补充迁移、并发控制与更严格的错误处理。
"""

import sqlite3
from datetime import date
from typing import List, Optional, Tuple

from .models import Pet

# 解决 Python 3.12+ 对 sqlite3 默认 date adapter/converter 的弃用警告：
# 显式注册日期类型的 adapter 与 converter，避免依赖 sqlite3 的默认行为。
import datetime as _datetime


def _adapt_date(value: _datetime.date) -> bytes:
    """
    Args:
        value: 要转换的日期对象

    Returns:
        bytes: ISO 格式字符串的字节表示
    """
    return value.isoformat().encode()


def _convert_date(value: bytes) -> _datetime.date:
    """
    Args:
        value: SQLite 中存储的字节串

    Returns:
        datetime.date: 转换后的日期对象
    """
    return _datetime.date.fromisoformat(value.decode())


# 注册适配器与转换器，名称 'DATE' 对应数据库中声明的列类型
sqlite3.register_adapter(_datetime.date, _adapt_date)
sqlite3.register_converter("DATE", _convert_date)


class DB:
    """用于操作 pets 表的轻量封装类。

    注：在本练习中我们使用 sqlite3 的 detect_types 功能来尽量让
    DATE 字段在读取时自动转换回 datetime.date，这简化了测试代码。
    我们显式注册了 adapter/converter 以消除 Python 3.12 的弃用警告。
    """

    def __init__(self, db_path: str = ":memory:"):
        """打开数据库连接并确保表结构存在。

        Args:
            db_path: SQLite 文件路径；使用 ':memory:' 时将创建内存数据库，
                     适合测试场景。
        """
        # 使用明确的 detect_types 标志让 sqlite3 在解析列时使用我们注册的转换器
        self.conn = sqlite3.connect(
            db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        # 使用 Row 类型可以通过下标访问字段，也可用于调试输出
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """彻底重建 pets 表到最新定义（会删除旧表并重建）。

        注意：此行为会**清除**表中已有数据。按用户要求，不再尝试兼容旧数据库，
        每次初始化使用最新表结构。"""
        cur = self.conn.cursor()
        # 删除旧表（如果存在），然后创建全新的表结构
        cur.execute("DROP TABLE IF EXISTS pets")
        cur.execute(
            """
            CREATE TABLE pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                gender TEXT NOT NULL,
                mbti TEXT NOT NULL DEFAULT '',
                -- 为每种触发器存储触发时间的 JSON 列（ISO 格式字符串列表）
                birth_trigger_times TEXT NOT NULL DEFAULT '[]',
                wakeup_trigger_times TEXT NOT NULL DEFAULT '[]',
                bed_trigger_times TEXT NOT NULL DEFAULT '[]',
                breakfast_trigger_times TEXT NOT NULL DEFAULT '[]',
                lunch_trigger_times TEXT NOT NULL DEFAULT '[]',
                dinner_trigger_times TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        self.conn.commit()

    def add_pet(self, pet: Pet) -> Pet:
        """
        向数据库插入一条 pet 记录并返回带有 id 的 Pet 实例。
        Args:
            pet: 要添加的宠物对象
            `pet.birth_date` 必须为 ISO 格式字符串（'YYYY-MM-DD'），否则抛出 TypeError；

        Returns:
            Pet: 添加了ID的宠物对象
        """
        cur = self.conn.cursor()
        # 要求 birth_date 为 ISO 字符串（存储于 TEXT 列），不再支持 date 类型的自动转换
        b = pet.birth_date
        # 强制要求调用方传入 ISO 格式字符串，若类型不对则抛出错误以便及早发现问题
        if not isinstance(b, str):
            raise TypeError("pet.birth_date must be an ISO format string 'YYYY-MM-DD'")
        cur.execute(
            "INSERT INTO pets (name, birth_date, gender, mbti) VALUES (?, ?, ?, ?)",
            (pet.name, b, pet.gender, pet.mbti or ""),
        )
        pet.id = cur.lastrowid
        self.conn.commit()
        return pet

    def _read_json_list(self, text: str):
        """
        Args:
            text: JSON格式的字符串

        Returns:
            list: 解析后的Python列表
        """
        import json

        try:
            return json.loads(text) if text else []
        except Exception:
            return []

    def _write_json_list(self, lst) -> str:
        """
        Args:
            lst: 要序列化的 Python 列表

        Returns:
            str: JSON格式的字符串
        """
        import json

        return json.dumps(lst)

    def list_pets(self) -> List[Pet]:
        """
        Returns:
            List[Pet]: 数据库中所有宠物的列表
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, birth_date, gender, mbti, birth_trigger_times, wakeup_trigger_times, bed_trigger_times, breakfast_trigger_times, lunch_trigger_times, dinner_trigger_times FROM pets"
        )
        rows = cur.fetchall()
        # 将每一行（sqlite3.Row）传给 Pet.from_row，由其解析触发器时间列
        return [Pet.from_row(r) for r in rows]

    def get_trigger_times(self, pet_id: int, trigger_name: str):
        """
        Args:
            pet_id: 宠物ID
            trigger_name: 触发器名称

        Returns:
            list: 触发时间的datetime列表，若不存在返回None
        """
        # 在数据库中我们使用 JSON 文本保存时间字符串（ISO 格式），
        # 这里根据 trigger_name 选择相应的列并解析为 datetime 对象列表。
        col = None
        mapping = {
            "birth": "birth_trigger_times",
            "wakeup": "wakeup_trigger_times",
            "bed": "bed_trigger_times",
            "breakfast": "breakfast_trigger_times",
            "lunch": "lunch_trigger_times",
            "dinner": "dinner_trigger_times",
        }
        if trigger_name not in mapping:
            raise ValueError(f"Unknown trigger: {trigger_name}")
        col = mapping[trigger_name]

        cur = self.conn.cursor()
        cur.execute(f"SELECT {col} FROM pets WHERE id = ?", (pet_id,))
        r = cur.fetchone()
        if not r:
            return None
        text = r[0]
        times = self._read_json_list(text)
        # 将 ISO 字符串转换为 datetime
        from datetime import datetime as _dt

        return [_dt.fromisoformat(s) for s in times]

    def triggered_today(self, pet_id: int, trigger_name: str, today_date=None) -> bool:
        """
        Args:
            pet_id: 宠物ID
            trigger_name: 触发器名称
            today_date: 可选的日期或 datetime 对象，默认为今天（便于测试时注入特定日期）

        Returns:
            bool: 如果当日已有触发记录则返回True，否则返回False
        """
        if today_date is None:
            from datetime import date as _date

            today_date = _date.today()
        # 支持传入 datetime 对象或 date 对象
        try:
            d = today_date.date()
        except Exception:
            d = today_date

        times = self.get_trigger_times(pet_id, trigger_name)
        if not times:
            return False
        for t in times:
            if t.date() == d:
                return True
        return False

    def record_trigger_time(self, pet_id: int, trigger_name: str, when_dt):
        """
        在对应触发器的时间列表中追加一个时间点（when_dt 为 datetime 实例）。
        Args:
            pet_id: 宠物ID
            trigger_name: 触发器名称
            when_dt: 触发时间的datetime对象

        Returns:
            bool: 记录是否成功
        """
        mapping = {
            "birth": "birth_trigger_times",
            "wakeup": "wakeup_trigger_times",
            "bed": "bed_trigger_times",
            "breakfast": "breakfast_trigger_times",
            "lunch": "lunch_trigger_times",
            "dinner": "dinner_trigger_times",
        }
        if trigger_name not in mapping:
            raise ValueError(f"Unknown trigger: {trigger_name}")
        col = mapping[trigger_name]

        cur = self.conn.cursor()
        cur.execute(f"SELECT {col} FROM pets WHERE id = ?", (pet_id,))
        r = cur.fetchone()
        if not r:
            raise ValueError(f"Pet id {pet_id} not found")
        current = self._read_json_list(r[0])
        # 记录 ISO 格式字符串
        current.append(when_dt.isoformat())
        new_text = self._write_json_list(current)
        cur.execute(f"UPDATE pets SET {col} = ? WHERE id = ?", (new_text, pet_id))
        self.conn.commit()
