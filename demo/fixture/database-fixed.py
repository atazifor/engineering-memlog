import sqlite3


def connect(path: str) -> sqlite3.Connection:
    database = sqlite3.connect(path)
    database.execute("PRAGMA foreign_keys = ON")
    return database


def migrate(path: str) -> None:
    with connect(path) as database:
        database.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY)")
        database.execute(
            "CREATE TABLE tasks ("
            "id INTEGER PRIMARY KEY, "
            "project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE"
            ")"
        )


def seed_project(path: str) -> None:
    with connect(path) as database:
        database.execute("INSERT INTO projects (id) VALUES (1)")
        database.execute("INSERT INTO tasks (id, project_id) VALUES (1, 1)")


def delete_project(path: str) -> None:
    with connect(path) as database:
        database.execute("DELETE FROM projects WHERE id = 1")


def task_count(path: str) -> int:
    with connect(path) as database:
        return database.execute("SELECT count(*) FROM tasks").fetchone()[0]
