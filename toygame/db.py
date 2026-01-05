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

import json
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
        """初始化 pets 表，如果表结构不匹配则重建（会删除旧表并重建），
        如果表结构已匹配则保留数据。"""
        cur = self.conn.cursor()

        # 检查表是否存在
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pets';"
        )
        table_exists = cur.fetchone() is not None

        if not table_exists:
            # 如果表不存在，直接创建新表
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
                    dinner_trigger_times TEXT NOT NULL DEFAULT '[]',
                    -- 存储聊天历史的 JSON 列
                    chat_history TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            self.conn.commit()
            return

        # 如果表存在，检查表结构是否匹配
        cur.execute("PRAGMA table_info(pets)")
        existing_columns = cur.fetchall()

        # 定义期望的列结构 - 注意：这里需要与实际创建表的列完全匹配
        expected_columns = [
            ("id", "INTEGER", 0, None, 1),
            ("name", "TEXT", 1, None, 1),
            ("birth_date", "TEXT", 1, None, 0),
            ("gender", "TEXT", 1, None, 0),
            ("mbti", "TEXT", 1, "", 0),
            ("birth_trigger_times", "TEXT", 1, "[]", 0),
            ("wakeup_trigger_times", "TEXT", 1, "[]", 0),
            ("bed_trigger_times", "TEXT", 1, "[]", 0),
            ("breakfast_trigger_times", "TEXT", 1, "[]", 0),
            ("lunch_trigger_times", "TEXT", 1, "[]", 0),
            ("dinner_trigger_times", "TEXT", 1, "[]", 0),
            ("chat_history", "TEXT", 1, "[]", 0),
        ]

        # 检查列数量是否匹配
        if len(existing_columns) != len(expected_columns):
            # 列数量不匹配，需要重建表
            print("Table structure mismatch: column count differs. Rebuilding table...")
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
                    dinner_trigger_times TEXT NOT NULL DEFAULT '[]',
                    -- 存储聊天历史的 JSON 列
                    chat_history TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            self.conn.commit()
            return

        # 检查每一列的定义是否匹配
        structure_matches = True
        for i, expected_col in enumerate(expected_columns):
            if i >= len(existing_columns):
                structure_matches = False
                break

            existing_col = existing_columns[i]
            # 比较列名、类型
            # existing_col格式: (cid, name, type, notnull, dflt_value, pk)
            # expected_col格式: (name, type, notnull, dflt_value, pk)
            if (
                existing_col[1] != expected_col[0]  # name
                or existing_col[2] != expected_col[1]
            ):  # type
                structure_matches = False
                break

        if not structure_matches:
            # 表结构不匹配，备份数据后重建表
            print("Table structure mismatch. Rebuilding table...")
            # 为了保留现有数据，我们先备份现有数据
            cur.execute("SELECT * FROM pets")
            existing_data = cur.fetchall()

            # 获取列名
            cur.execute("PRAGMA table_info(pets)")
            col_info = cur.fetchall()
            col_names = [col[1] for col in col_info]

            # 重建表
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
                    dinner_trigger_times TEXT NOT NULL DEFAULT '[]',
                    -- 存储聊天历史的 JSON 列
                    chat_history TEXT NOT NULL DEFAULT '[]'
                )
                """
            )

            # 尝试插入备份的数据
            if existing_data:
                # 确定可以插入的列
                target_cols = ["name", "birth_date", "gender", "mbti"]
                # 确保源数据中的列在目标表中也存在
                for row in existing_data:
                    # 构建插入语句，只插入存在的列
                    if len(row) >= 4:  # 确保有足够的列
                        cur.execute(
                            "INSERT INTO pets (name, birth_date, gender, mbti) VALUES (?, ?, ?, ?)",
                            (
                                row[1] if len(row) > 1 else "",
                                row[2] if len(row) > 2 else "",
                                row[3] if len(row) > 3 else "",
                                row[4] if len(row) > 4 else "",
                            ),
                        )

            self.conn.commit()
        else:
            print("Table structure matches. No need to rebuild.")
            # 检查是否有chat_history列，如果没有则添加
            has_chat_history = any(col[1] == "chat_history" for col in existing_columns)
            if not has_chat_history:
                print("Adding chat_history column...")
                cur.execute(
                    "ALTER TABLE pets ADD COLUMN chat_history TEXT NOT NULL DEFAULT '[]'"
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
            List[Pet]: 数据库中所有 pet 的列表（每项为 Pet 实例），包含触发器时间历史。
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, birth_date, gender, mbti, birth_trigger_times, wakeup_trigger_times, bed_trigger_times, breakfast_trigger_times, lunch_trigger_times, dinner_trigger_times, chat_history FROM pets"
        )
        rows = cur.fetchall()
        # 将每一行（sqlite3.Row）传给 Pet.from_row，由其解析触发器时间列
        return [Pet.from_row(r) for r in rows]

    def get_pets(
        self, pet_ids: List[int] = None, pet_names: List[str] = None
    ) -> List[Pet]:
        """根据可选的ID列表或名称列表搜索宠物

        Args:
            pet_ids: 可选的宠物ID列表，如果提供则搜索指定ID的宠物
            pet_names: 可选的宠物名称列表，如果提供则搜索指定名称的宠物

        Returns:
            List[Pet]: 匹配搜索条件的宠物列表
        """
        cur = self.conn.cursor()

        # 如果没有提供任何搜索条件，返回空列表
        if not pet_ids and not pet_names:
            return []

        # 构建查询语句和参数
        query = "SELECT id, name, birth_date, gender, mbti, birth_trigger_times, wakeup_trigger_times, bed_trigger_times, breakfast_trigger_times, lunch_trigger_times, dinner_trigger_times, chat_history FROM pets"
        params = []
        conditions = []

        if pet_ids:
            # 添加ID条件
            id_placeholders = ",".join(["?" for _ in pet_ids])
            conditions.append(f"id IN ({id_placeholders})")
            params.extend(pet_ids)

        if pet_names:
            # 添加名称条件
            name_placeholders = ",".join(["?" for _ in pet_names])
            conditions.append(f"name IN ({name_placeholders})")
            params.extend(pet_names)

        if conditions:
            # 使用OR连接条件（而不是AND）
            query += " WHERE " + " OR ".join(conditions)

        cur.execute(query, params)
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

    def get_chat_history(self, pet_id: int):
        """
        获取宠物的聊天历史
        Args:
            pet_id: 宠物ID

        Returns:
            list: 聊天历史列表，如果不存在则返回空列表
        """
        import json

        try:
            cur = self.conn.cursor()
            cur.execute("SELECT chat_history FROM pets WHERE id = ?", (pet_id,))
            result = cur.fetchone()
            if result and result[0]:
                return json.loads(result[0])
            return []
        except Exception as e:
            print(f"Error getting chat history for pet {pet_id}: {str(e)}")
            return []

    def update_chat_history(self, pet_id: int, chat_history):
        """
        更新宠物的聊天历史
        Args:
            pet_id: 宠物ID
            chat_history: 聊天历史列表

        Returns:
            bool: 更新是否成功
        """
        try:
            cur = self.conn.cursor()
            history_json = json.dumps(chat_history)
            cur.execute(
                "UPDATE pets SET chat_history = ? WHERE id = ?", (history_json, pet_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating chat history for pet {pet_id}: {str(e)}")
            return False
