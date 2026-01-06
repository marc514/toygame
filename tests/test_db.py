import sqlite3
from datetime import date

from toygame.db import DB
from toygame.models import Pet


def create_old_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_date DATE NOT NULL,
            gender TEXT NOT NULL,
            birth_trigger_count INTEGER NOT NULL DEFAULT 0,
            timer_trigger_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        "INSERT INTO pets (name, birth_date, gender, birth_trigger_count, timer_trigger_count) VALUES (?, ?, ?, ?, ?)",
        ("old", date.today(), "M", 1, 1),
    )
    conn.commit()
    conn.close()


def test_recreate_overwrites_old_db(tmp_path):
    dbfile = tmp_path / "old.db"
    create_old_db(str(dbfile))

    # Instantiate our DB which should DROP and CREATE the table
    db = DB(str(dbfile))

    # Now the pets table should have the new columns and not the old count columns
    cur = db.conn.cursor()
    cur.execute("PRAGMA table_info(pets)")
    cols = [r[1] for r in cur.fetchall()]
    assert "birth_trigger_times" in cols
    assert "birth_trigger_count" not in cols
    assert "timer_trigger_count" not in cols

    # Table should be empty because we dropped and recreated
    cur.execute("SELECT COUNT(*) FROM pets")
    count = cur.fetchone()[0]
    assert count == 0


def test_get_pets_by_ids(tmp_path):
    """测试通过ID列表搜索宠物"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    # 创建几个宠物
    pet1 = Pet(
        id=0, name="Pet1", birth_date=date.today().isoformat(), gender="M", mbti="INTJ"
    )
    pet2 = Pet(
        id=0, name="Pet2", birth_date=date.today().isoformat(), gender="F", mbti="ENFP"
    )
    pet3 = Pet(
        id=0, name="Pet3", birth_date=date.today().isoformat(), gender="M", mbti="ISTP"
    )

    pet1 = db.add_pet(pet1)
    pet2 = db.add_pet(pet2)
    pet3 = db.add_pet(pet3)

    # 测试搜索特定ID
    result = db.get_pets(pet_ids=[pet1.id, pet3.id])
    assert len(result) == 2
    assert result[0].id == pet1.id
    assert result[1].id == pet3.id
    assert result[0].name == "Pet1"
    assert result[1].name == "Pet3"

    # 测试搜索不存在的ID
    result = db.get_pets(pet_ids=[999])
    assert len(result) == 0

    # 测试搜索单个ID
    result = db.get_pets(pet_ids=[pet2.id])
    assert len(result) == 1
    assert result[0].id == pet2.id
    assert result[0].name == "Pet2"


def test_get_pets_by_names(tmp_path):
    """测试通过名称列表搜索宠物"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    # 创建几个宠物
    pet1 = Pet(
        id=0, name="Alice", birth_date=date.today().isoformat(), gender="F", mbti="INTJ"
    )
    pet2 = Pet(
        id=0, name="Bob", birth_date=date.today().isoformat(), gender="M", mbti="ENFP"
    )
    pet3 = Pet(
        id=0,
        name="Charlie",
        birth_date=date.today().isoformat(),
        gender="M",
        mbti="ISTP",
    )

    pet1 = db.add_pet(pet1)
    pet2 = db.add_pet(pet2)
    pet3 = db.add_pet(pet3)

    # 测试搜索特定名称
    result = db.get_pets(pet_names=["Alice", "Charlie"])
    assert len(result) == 2
    assert result[0].name == "Alice"
    assert result[1].name == "Charlie"
    assert result[0].id == pet1.id
    assert result[1].id == pet3.id

    # 测试搜索不存在的名称
    result = db.get_pets(pet_names=["NonExistent"])
    assert len(result) == 0

    # 测试搜索单个名称
    result = db.get_pets(pet_names=["Bob"])
    assert len(result) == 1
    assert result[0].name == "Bob"
    assert result[0].id == pet2.id


def test_get_pets_by_both_ids_and_names(tmp_path):
    """测试同时使用ID和名称搜索（OR条件）"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    # 创建几个宠物
    pet1 = Pet(
        id=0, name="Alice", birth_date=date.today().isoformat(), gender="F", mbti="INTJ"
    )
    pet2 = Pet(
        id=0, name="Bob", birth_date=date.today().isoformat(), gender="M", mbti="ENFP"
    )
    pet3 = Pet(
        id=0,
        name="Charlie",
        birth_date=date.today().isoformat(),
        gender="M",
        mbti="ISTP",
    )

    pet1 = db.add_pet(pet1)
    pet2 = db.add_pet(pet2)
    pet3 = db.add_pet(pet3)

    # 测试同时使用ID和名称搜索 - 找到匹配ID或名称的宠物（OR关系）
    result = db.get_pets(pet_ids=[pet1.id], pet_names=["Charlie"])
    assert len(result) == 2
    pet_ids = {p.id for p in result}
    assert pet1.id in pet_ids
    assert pet3.id in pet_ids

    # 测试找不到匹配项的情况
    result = db.get_pets(pet_ids=[999], pet_names=["NonExistent"])
    assert len(result) == 0


def test_get_pets_empty_conditions(tmp_path):
    """测试不提供任何搜索条件时的行为"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    # 创建几个宠物
    pet1 = Pet(
        id=0, name="Alice", birth_date=date.today().isoformat(), gender="F", mbti="INTJ"
    )
    pet2 = Pet(
        id=0, name="Bob", birth_date=date.today().isoformat(), gender="M", mbti="ENFP"
    )

    pet1 = db.add_pet(pet1)
    pet2 = db.add_pet(pet2)

    # 不提供任何条件，应该不返回任何宠物
    result = db.get_pets()
    assert len(result) == 0

    # 提供空列表作为条件，应该不返回任何宠物
    result = db.get_pets(pet_ids=[], pet_names=[])
    assert len(result) == 0
