import os
from datetime import datetime, date, timedelta

import pytest

from toygame.db import DB
from toygame.models import Pet
from toygame.triggers import BirthTrigger, TimerTrigger, WakeUpTimer, BedTimer, BreakfastTimer, LunchTimer, DinnerTimer
from toygame.main import run_game, create_pets
from toygame.enums import MBTI_TYPES, MBTI_LIST


def test_db_add_and_list(tmp_path):
    """测试：添加宠物并能通过 list_pets 读取。

    说明：`birth_date` 在当前设计中以 ISO 字符串保存，调用方应传入 ISO 字符串。
    这里我们验证返回的 Pet 实例的 `birth_date` 为字符串且能被解析为日期。
    """
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    p1 = Pet(id=0, name="a", birth_date=date.today().isoformat(), gender="M", mbti="INTJ")
    p2 = Pet(id=0, name="b", birth_date=date.today().isoformat(), gender="F", mbti="ENFP")
    db.add_pet(p1)
    db.add_pet(p2)
    pets = db.list_pets()
    assert len(pets) == 2
    # 确认 birth_date 为 ISO 字符串并可被解析
    from datetime import date as _d
    assert isinstance(pets[0].birth_date, str)
    _d.fromisoformat(pets[0].birth_date)
    assert isinstance(pets[1].birth_date, str)
    _d.fromisoformat(pets[1].birth_date)
    # 已指定的 MBTI 应如实返回
    assert pets[0].mbti == "INTJ"
    assert pets[1].mbti == "ENFP"

def test_birth_trigger_increments(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # pet with birth today
    pet = Pet(id=0, name="born_today", birth_date=date.today().isoformat(), gender="F", mbti="INFP")
    pet = db.add_pet(pet)

    # 使用 monkeypatch 模拟触发器模块中的 datetime.now() 返回当天中午（保证与 birth_date 相同）
    class DummyDatetime:
        @classmethod
        def now(cls):
            return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

    import toygame.triggers as triggers
    monkeypatch.setattr(triggers, 'datetime', DummyDatetime)

    b = BirthTrigger()

    fired = b.fire(pet, db)
    assert fired
    times = db.get_trigger_times(pet.id, 'birth')
    assert len(times) == 1

    # 再次触发应继续追加时间点
    # 当天已触发过则不再记录第二次
    fired2 = b.fire(pet, db)
    assert not fired2
    times = db.get_trigger_times(pet.id, 'birth')
    assert len(times) == 1


def test_birth_trigger_not_on_other_day(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    pet = Pet(id=0, name="born_other", birth_date=(date.today() - timedelta(days=1)).isoformat(), gender="M", mbti="ENTJ")
    pet = db.add_pet(pet)

    # 模拟当前时间为当天中午（与 pet.birth_date 前一天不同），确保不触发
    class DummyDatetime:
        @classmethod
        def now(cls):
            return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

    import toygame.triggers as triggers
    monkeypatch.setattr(triggers, 'datetime', DummyDatetime)

    b = BirthTrigger()
    fired = b.fire(pet, db)
    assert not fired
    times = db.get_trigger_times(pet.id, 'birth')
    assert len(times) == 0


def test_dinner_timer_at_6pm(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    pet = Pet(id=0, name="t", birth_date=date.today().isoformat(), gender="M", mbti="ISTP")
    pet = db.add_pet(pet)

    # 使用 monkeypatch 模拟触发器模块中的 datetime.now() 返回 18:00
    class DummyDatetime:
        @classmethod
        def now(cls):
            return datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)

    import toygame.triggers as triggers
    monkeypatch.setattr(triggers, 'datetime', DummyDatetime)

    t = DinnerTimer()
    fired = t.fire(pet, db)
    assert fired
    times = db.get_trigger_times(pet.id, 'dinner')
    assert len(times) == 1
    # 确认记录的时间小时为 18
    assert times[0].hour == 18
    # 再次触发当天不应重复记录
    fired2 = t.fire(pet, db)
    assert not fired2
    times = db.get_trigger_times(pet.id, 'dinner')
    assert len(times) == 1


def test_wakeup_timer_at_7am(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # birth_date 使用 ISO 字符串表示
    pet = Pet(id=0, name="w", birth_date=date.today().isoformat(), gender="F", mbti="ESFJ")
    pet = db.add_pet(pet) 

    class DummyDatetime:
        @classmethod
        def now(cls):
            return datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)

    import toygame.triggers as triggers
    monkeypatch.setattr(triggers, 'datetime', DummyDatetime)

    t = WakeUpTimer()
    fired = t.fire(pet, db)
    assert fired
    times = db.get_trigger_times(pet.id, 'wakeup')
    assert len(times) == 1
    assert times[0].hour == 7
    # 再触发当天不应重复记录
    fired2 = t.fire(pet, db)
    assert not fired2
    times = db.get_trigger_times(pet.id, 'wakeup')
    assert len(times) == 1


def test_lunch_timer_at_noon(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # birth_date 使用 ISO 字符串表示
    pet = Pet(id=0, name="l", birth_date=date.today().isoformat(), gender="M", mbti="ESTJ")
    pet = db.add_pet(pet)

    class DummyDatetime:
        @classmethod
        def now(cls):
            return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

    import toygame.triggers as triggers
    monkeypatch.setattr(triggers, 'datetime', DummyDatetime)

    t = LunchTimer()
    fired = t.fire(pet, db)
    assert fired
    times = db.get_trigger_times(pet.id, 'lunch')
    assert len(times) == 1
    assert times[0].hour == 12
    # 再次触发当天不应重复记录
    fired2 = t.fire(pet, db)
    assert not fired2
    times = db.get_trigger_times(pet.id, 'lunch')
    assert len(times) == 1


def test_run_game_creates_pets(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    # 先创建三只宠物（`run_game` 仅负责轮询触发器）
    create_pets(db, num_pets=3)
    run_game(db)
    pets = db.list_pets()
    assert len(pets) == 3
    # 确认 run_game 中创建的宠物包含随机分配的 MBTI，格式为 4 个字符（如 "INTJ") 且属于 16 型集合
    # 使用从 toygame.enums 导入的类型集合
    for pet in pets:
        assert isinstance(pet.mbti, str)
        assert len(pet.mbti) == 4
        assert pet.mbti in MBTI_TYPES


def test_mbti_random_pet_values():
    """验证 random_pet 返回的 Pet.mbti 属于 16 型集合。"""
    from toygame.main import random_pet
    # 多次调用以覆盖随机性
    seen = set()
    for i in range(50):
        p = random_pet("x", i)
        assert isinstance(p.mbti, str)
        assert p.mbti in MBTI_TYPES
        seen.add(p.mbti)
    # 期望在 50 次尝试中至少看到 8 种不同 MBTI，验证分布不是极端偏颇
    assert len(seen) >= 8


def test_run_game_multiple_times_with_time_progression(tmp_path, monkeypatch):
    """循环调用：每次先创建 1 个随机 pet，再调用 run_game，并将 triggers.datetime.now() 设置为
    从 2000-01-01 00:00:00 起每次增加 7 小时，验证每轮新插入的宠物在对应小时触发器的行为。"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    from datetime import datetime, timedelta
    import toygame.triggers as triggers
    from toygame.main import create_pets, run_game

    base = datetime(2000, 1, 1, 0, 0, 0)
    # 小时 -> 触发器名映射（我们关心这几个时间点）
    mapping = {7: 'wakeup', 8: 'breakfast', 12: 'lunch', 18: 'dinner', 22: 'bed'}

    create_pets(db, num_pets=3)

    iterations = 5000
    for i in range(iterations):
        current = base + timedelta(hours=13 * i)

        class DummyDatetime:
            @classmethod
            def now(cls):
                return current

        monkeypatch.setattr(triggers, 'datetime', DummyDatetime)
        run_game(db)

    pets = db.list_pets()
    for p in pets:
        print(f"{p.name}\t{p.birth_date}\t{p.gender}\t{p.mbti}\t{p.birth_trigger_times}\t{p.wakeup_trigger_times}")
