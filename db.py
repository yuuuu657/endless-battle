import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "game.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            exp        INTEGER DEFAULT 0,
            gold       INTEGER DEFAULT 100,
            weapon_id  INTEGER DEFAULT 1,
            armor_id   INTEGER DEFAULT 1,
            wins       INTEGER DEFAULT 0,
            losses     INTEGER DEFAULT 0,
            nation_id  INTEGER DEFAULT NULL,
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS nations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    UNIQUE NOT NULL,
            leader_id  INTEGER NOT NULL,
            gold       INTEGER DEFAULT 0,
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS battle_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender    TEXT    NOT NULL,
            result      TEXT    NOT NULL,
            exp_gain    INTEGER DEFAULT 0,
            gold_gain   INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS chat (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id  INTEGER NOT NULL,
            name       TEXT    NOT NULL,
            message    TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()
