import sqlite3

def create_table():
    """
    データベースとテーブル（shops, comments）を作成・確認する関数
    """
    conn = sqlite3.connect('nomikai_kanji.db')
    cursor = conn.cursor()

    # 1. shopsテーブルの作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shops (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        name             TEXT,
        address          TEXT,
        catch            TEXT,
        desc             TEXT,
        lat              REAL,
        lng              REAL,
        google_rating    REAL DEFAULT 0,
        hotpepper_url    TEXT UNIQUE,
        photo_url        TEXT,
        budget_night     TEXT, 
        is_nomihodai     INTEGER, 
        genre            TEXT,
        access           TEXT,
        has_private_room INTEGER,
        private_capacity INTEGER,
        is_smoking       INTEGER,
        is_barrier_free  INTEGER,
        summary          TEXT, 
        summary_vector   TEXT
    )
    ''')

    # 2. commentsテーブルの作成
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
    print("DBのテーブル作成・確認が完了しました")

# ファイルが直接実行された時だけ動くようにする（app.pyから呼ぶときは動かない）
if __name__ == "__main__":
    create_table()