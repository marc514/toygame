import sqlite3
from datetime import date

from toygame.db import DB


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
    cur.execute("INSERT INTO pets (name, birth_date, gender, birth_trigger_count, timer_trigger_count) VALUES (?, ?, ?, ?, ?)",
                ("old", date.today(), "M", 1, 1))
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
