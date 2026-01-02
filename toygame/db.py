"""数据库访问层（中文注释）

本模块封装了对 SQLite 的最小操作集合，用于保存和查询 Pet 以及
对触发器计数进行累加。设计目标是简单可测，方便测试用例使用
临时数据库（':memory:' 或 tmp 文件）。
"""

import sqlite3
from datetime import date
from typing import List, Optional, Tuple

from .models import Pet


class DB:
    """用于操作 pets 表的轻量封装类。

    注：在本练习中我们使用 sqlite3 的 detect_types 功能来尽量让
    DATE 字段在读取时自动转换回 datetime.date，这简化了测试代码。
    """

    def __init__(self, db_path: str = ":memory:"):
        """打开数据库连接并确保表结构存在。

        Args:
            db_path: SQLite 文件路径；使用 ':memory:' 时将创建内存数据库，
                     适合测试场景。
        """
        # detect_types 用于尝试自动解析 DATE 类型为 datetime.date
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        # 使用 Row 类型可以通过下标访问字段，也可用于调试输出
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """创建 pets 表（如果尚未存在）。"""
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date DATE NOT NULL,
                gender TEXT NOT NULL,
                birth_trigger_count INTEGER NOT NULL DEFAULT 0,
                timer_trigger_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.commit()

    def add_pet(self, pet: Pet) -> Pet:
        """向数据库插入一条 pet 记录并返回带有 id 的 Pet 实例。

        该方法会修改传入的 pet 对象，设置 pet.id 为数据库分配的主键。
        """
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO pets (name, birth_date, gender) VALUES (?, ?, ?)",
            (pet.name, pet.birth_date, pet.gender),
        )
        pet.id = cur.lastrowid
        self.conn.commit()
        return pet

    def list_pets(self) -> List[Pet]:
        """返回数据库中所有 pet 的列表（每项为 Pet 实例）。"""
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, birth_date, gender, birth_trigger_count, timer_trigger_count FROM pets")
        rows = cur.fetchall()
        # 将每一行转换为 Pet（忽略计数列）
        return [Pet.from_row((r[0], r[1], r[2], r[3], r[4], r[5])) for r in rows]

    def get_trigger_counts(self, pet_id: int) -> Optional[Tuple[int, int]]:
        """返回指定 pet 的触发器计数 (birth_count, timer_count)，若不存在则返回 None。"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT birth_trigger_count, timer_trigger_count FROM pets WHERE id = ?",
            (pet_id,),
        )
        r = cur.fetchone()
        if r:
            return r[0], r[1]
        return None

    def increment_trigger(self, pet_id: int, trigger_name: str):
        """根据触发器名称将对应计数加 1。

        支持的 trigger_name 为 'birth' 或 'timer'，否则抛出 ValueError。
        """
        cur = self.conn.cursor()
        if trigger_name == "birth":
            cur.execute(
                "UPDATE pets SET birth_trigger_count = birth_trigger_count + 1 WHERE id = ?",
                (pet_id,),
            )
        elif trigger_name == "timer":
            cur.execute(
                "UPDATE pets SET timer_trigger_count = timer_trigger_count + 1 WHERE id = ?",
                (pet_id,),
            )
        else:
            # 避免意外传入错误的触发器名
            raise ValueError(f"Unknown trigger: {trigger_name}")
        self.conn.commit()
