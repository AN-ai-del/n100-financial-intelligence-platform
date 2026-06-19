from pathlib import Path
import sqlite3


DB_PATH = Path("db/nifty100.db")
SCHEMA_PATH = Path("db/schema.sql")


def create_database():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    DB_PATH.parent.mkdir(exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
            schema_sql = file.read()

        conn.executescript(schema_sql)
        conn.commit()

    print(f"Database created successfully at: {DB_PATH}")


if __name__ == "__main__":
    create_database()