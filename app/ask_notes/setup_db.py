from pathlib import Path

from app.core.db import connect

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def setup_db() -> None:
    """Create the vector extension, the tables and the indexes. Safe to run again."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(with_vectors=False) as conn:
        conn.execute(sql)  # our own trusted file, never user input


def main() -> None:
    setup_db()
    print("Database ready: tables notes and chunks.")


if __name__ == "__main__":
    main()
