import os
from datetime import datetime, date, timedelta

import pytest

from toygame.db import DB
from toygame.models import Pet
from toygame.triggers import BirthTrigger, TimerTrigger, WakeUpTimer, BedTimer, BreakfastTimer, LunchTimer, DinnerTimer
from toygame.main import run_game


def test_db_add_and_list(tmp_path):
    """测试：添加宠物并能通过 list_pets 读取。

    说明：`birth_date` 在当前设计中以 ISO 字符串保存，调用方应传入 ISO 字符串。
    这里我们验证返回的 Pet 实例的 `birth_date` 为字符串且能被解析为日期。
    """
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    p1 = Pet(id=None, name="a", birth_date=date.today().isoformat(), gender="M")
    p2 = Pet(id=None, name="b", birth_date=date.today().isoformat(), gender="F")
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


def test_birth_trigger_increments(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # pet with birth today
    pet = Pet(id=None, name="born_today", birth_date=date.today().isoformat(), gender="F")
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
    fired2 = b.fire(pet, db)
    assert fired2
    times = db.get_trigger_times(pet.id, 'birth')
    assert len(times) == 2


def test_birth_trigger_not_on_other_day(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    pet = Pet(id=None, name="born_other", birth_date=(date.today() - timedelta(days=1)).isoformat(), gender="M")
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
    pet = Pet(id=None, name="t", birth_date=date.today().isoformat(), gender="M")
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


def test_wakeup_timer_at_7am(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # birth_date 使用 ISO 字符串表示
    pet = Pet(id=None, name="w", birth_date=date.today().isoformat(), gender="F")
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


def test_lunch_timer_at_noon(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # birth_date 使用 ISO 字符串表示
    pet = Pet(id=None, name="l", birth_date=date.today().isoformat(), gender="M")
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


def test_run_game_creates_pets(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    run_game(db, num_pets=3)
    pets = db.list_pets()
    assert len(pets) == 3
