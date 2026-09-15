import tempfile
from pathlib import Path
import unittest

from database import delete_project, migrate, seed_project, task_count


class DatabaseTests(unittest.TestCase):
    def test_delete_project_cascades_to_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "app.db")
            migrate(path)
            seed_project(path)
            delete_project(path)

            self.assertEqual(
                task_count(path),
                0,
                "deleting a project must not leave orphan tasks",
            )


if __name__ == "__main__":
    unittest.main()
