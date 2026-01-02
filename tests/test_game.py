import os
from datetime import datetime, date, timedelta

import pytest

from toygame.db import DB
from toygame.models import Pet
from toygame.triggers import BirthTrigger, TimerTrigger
from toygame.main import run_game


def test_db_add_and_list(tmp_path):
    """测试：添加宠物并能通过 list_pets 读取。"""
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    p1 = Pet(id=None, name="a", birth_date=date.today(), gender="M")
    p2 = Pet(id=None, name="b", birth_date=date.today(), gender="F")
    db.add_pet(p1)
    db.add_pet(p2)
    pets = db.list_pets()
    assert len(pets) == 2


def test_birth_trigger_increments(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    # pet with birth today
    pet = Pet(id=None, name="born_today", birth_date=date.today(), gender="F")
    pet = db.add_pet(pet)

    now = datetime.now()
    b = BirthTrigger()

    fired = b.fire(pet, db, now)
    assert fired
    counts = db.get_trigger_counts(pet.id)
    assert counts[0] == 1

    # firing again should increment further
    fired2 = b.fire(pet, db, now)
    assert fired2
    counts = db.get_trigger_counts(pet.id)
    assert counts[0] == 2


def test_birth_trigger_not_on_other_day(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    pet = Pet(id=None, name="born_other", birth_date=date.today() - timedelta(days=1), gender="M")
    pet = db.add_pet(pet)

    now = datetime.now()
    b = BirthTrigger()
    fired = b.fire(pet, db, now)
    assert not fired
    counts = db.get_trigger_counts(pet.id)
    assert counts[0] == 0


def test_timer_trigger_at_6pm(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))
    pet = Pet(id=None, name="t", birth_date=date.today(), gender="M")
    pet = db.add_pet(pet)

    # simulate 6pm
    now = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    t = TimerTrigger()
    fired = t.fire(pet, db, now)
    assert fired
    counts = db.get_trigger_counts(pet.id)
    assert counts[1] == 1


def test_run_game_creates_pets(tmp_path):
    dbfile = tmp_path / "test.db"
    db = DB(str(dbfile))

    run_game(db, num_pets=3)
    pets = db.list_pets()
    assert len(pets) == 3
