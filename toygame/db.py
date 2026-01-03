"""数据库访问层（中文注释）

本模块封装了对 SQLite 的最小操作集合，用于保存和查询 Pet 以及
对触发器触发时间的历史记录（每种触发器保存为 JSON 列的时间字符串列表）。

设计说明（重要）：
- `birth_date` 字段在当前设计中以 ISO 格式的字符串（"YYYY-MM-DD"）保存于表的 TEXT 列；
  - 本模块**不再尝试**兼容 `date` 类型；调用方必须提供 ISO 字符串作为 `birth_date`。
- 每个触发器的触发历史以 JSON 文本（ISO 时间字符串列表）保存，例如 `dinner_trigger_times`；
- 初始化时会重建（DROP & CREATE）`pets` 表以使用最新 schema（按你的要求，不做旧表兼容）。

此模块力求简单且可测，适合用作教学或原型示例；在生产中可换为带迁移支持的持久层实现。
"""

import sqlite3
from datetime import date
from typing import List, Optional, Tuple

from .models import Pet

# 解决 Python 3.12+ 对 sqlite3 默认 date adapter/converter 的弃用警告：
# 显式注册日期类型的 adapter 与 converter，避免依赖 sqlite3 的默认行为。
import datetime as _datetime

def _adapt_date(value: _datetime.date) -> bytes:
    """将 datetime.date 转换为 bytes（ISO 格式字符串）以存储到 SQLite。"""
    return value.isoformat().encode()

def _convert_date(value: bytes) -> _datetime.date:
    """将 SQLite 字节串（ISO 格式）转换回 datetime.date。"""
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
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
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
        """向数据库插入一条 pet 记录并返回带有 id 的 Pet 实例。

        该方法会修改传入的 pet 对象，设置 pet.id 为数据库分配的主键。
        """
        cur = self.conn.cursor()
        # 要求 birth_date 为 ISO 字符串（存储于 TEXT 列），不再支持 date 类型的自动转换
        b = pet.birth_date
        # 强制要求调用方传入 ISO 格式字符串，若类型不对则抛出错误以便及早发现问题
        if not isinstance(b, str):
            raise TypeError("pet.birth_date must be an ISO format string 'YYYY-MM-DD'")
        cur.execute(
            "INSERT INTO pets (name, birth_date, gender) VALUES (?, ?, ?)",
            (pet.name, b, pet.gender),
        )
        pet.id = cur.lastrowid
        self.conn.commit()
        return pet

    def _read_json_list(self, text: str):
        """解析数据库中 JSON 列，并返回 Python 列表。"""
        import json
        try:
            return json.loads(text) if text else []
        except Exception:
            return []

    def _write_json_list(self, lst) -> str:
        """将 Python 列表序列化为 JSON 文本用于存储。"""
        import json
        return json.dumps(lst)

    def list_pets(self) -> List[Pet]:
        """返回数据库中所有 pet 的列表（每项为 Pet 实例）。"""
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, birth_date, gender FROM pets")
        rows = cur.fetchall()
        # 将每一行转换为 Pet（忽略触发器时间列）
        return [Pet.from_row((r[0], r[1], r[2], r[3], None, None)) for r in rows]

    def get_trigger_times(self, pet_id: int, trigger_name: str):
        """返回指定 pet 的某个触发器触发时间列表（datetime 列表），若不存在返回 None。"""
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

    def record_trigger_time(self, pet_id: int, trigger_name: str, when_dt):
        """在对应触发器的时间列表中追加一个时间点（when_dt 为 datetime 实例）。"""
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
