import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id         SERIAL PRIMARY KEY,
            name       TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            exp        INTEGER DEFAULT 0,
            gold       INTEGER DEFAULT 100,
            weapon_id  INTEGER DEFAULT 1,
            armor_id   INTEGER DEFAULT 1,
            wins       INTEGER DEFAULT 0,
            losses     INTEGER DEFAULT 0,
            nation_id  INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS nations (
            id         SERIAL PRIMARY KEY,
            name       TEXT UNIQUE NOT NULL,
            leader_id  INTEGER NOT NULL,
            gold       INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS battle_log (
            id          SERIAL PRIMARY KEY,
            attacker_id INTEGER NOT NULL,
            defender    TEXT NOT NULL,
            result      TEXT NOT NULL,
            exp_gain    INTEGER DEFAULT 0,
            gold_gain   INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS chat (
            id         SERIAL PRIMARY KEY,
            player_id  INTEGER NOT NULL,
            name       TEXT NOT NULL,
            message    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
