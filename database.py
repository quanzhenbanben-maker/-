import sqlite3

conn = sqlite3.connect('nomikai_kanji.db')  #nomikai_kanji.db というDBファイルに接続する
cursor = conn.cursor() #DBに命令を送るための「窓口」を作る。以降はこの cursor を通してSQLを実行する


#shops テーブルを作る命令。
# IF NOT EXISTS : すでにテーブルがあったら上書きせずスキップしてくれる
cursor.execute('''
CREATE TABLE IF NOT EXISTS shops (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT,
    address          TEXT,
    catch          TEXT,
    desc          TEXT,
    lat              REAL,
    lng              REAL,
    google_rating    REAL,
    hotpepper_url     TEXT,
    photo_url        TEXT,
    budget_night     INTEGER,
    is_nomihodai     BOOLEAN,
    genre            TEXT,
    access           TEXT,
    has_private_room BOOLEAN,
    private_capacity INTEGER,
    is_smoking       BOOLEAN,
    is_barrier_free  BOOLEAN,
    summary         TEXT, 
    summary_vector  TEXT
)
''')

# 社内レビューを保存するテーブル。shop_id で shops テーブルと紐付いている
cursor.execute('''
CREATE TABLE IF NOT EXISTS comments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id           INTEGER NOT NULL,
    nickname          TEXT NOT NULL,
    visited_at        DATE,
    amount_per_person INTEGER NOT NULL,
    headcount         INTEGER,
    rating            INTEGER NOT NULL,
    review            TEXT NOT NULL,
    purpose           TEXT NOT NULL,
    noise_level       TEXT NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops (id)
)
''')

conn.commit()
conn.close()

print("DBを作成しました")
