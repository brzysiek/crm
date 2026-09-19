"""Testy walidacji hierarchii projektów w narzędziach zadań MCP.

Model zadań jest zamockowany (słownik w pamięci), więc testy nie dotykają bazy.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import mcp_server


def _task(id, is_project=0, parent_id=None, deleted_at=None):
    return {"id": id, "title": f"t{id}", "status": "next", "is_project": is_project,
            "parent_id": parent_id, "deleted_at": deleted_at, "context_name": "bp"}


class TaskHierarchyValidationTest(unittest.TestCase):
    def setUp(self):
        self.tasks = {
            1: _task(1, is_project=1),               # projekt
            2: _task(2, parent_id=1),                # zadanie w projekcie 1
            3: _task(3),                             # samodzielne zadanie
            4: _task(4, is_project=1, parent_id=5),  # (błędne dane) projekt z rodzicem
            5: _task(5, is_project=1, parent_id=4),
        }
        patches = [
            mock.patch.object(mcp_server.task_model, "get_task", side_effect=self.tasks.get),
            mock.patch.object(mcp_server.task_model, "get_project_subtasks",
                              side_effect=lambda pid: [t for t in self.tasks.values() if t["parent_id"] == pid]),
            mock.patch.object(mcp_server.task_model, "create_task", return_value=3),
            mock.patch.object(mcp_server.task_model, "update_task"),
            mock.patch.object(mcp_server.task_model, "convert_to_project"),
            mock.patch.object(mcp_server.task_model, "flatten_project"),
            mock.patch.object(mcp_server.gtd_context, "get_context",
                              side_effect=lambda cid: {"id": cid} if cid == 2 else None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.model = mcp_server.task_model

    def assertRejected(self, fn, message_part, **kwargs):
        with self.assertRaises(ValueError) as ctx:
            fn(**kwargs)
        self.assertIn(message_part, str(ctx.exception))
        self.model.create_task.assert_not_called()
        self.model.update_task.assert_not_called()
        self.model.convert_to_project.assert_not_called()
        self.model.flatten_project.assert_not_called()

    # create_task

    def test_create_with_nonexistent_parent(self):
        self.assertRejected(mcp_server.create_task, "Nie znaleziono projektu o id=999",
                            title="x", parent_id=999)

    def test_create_with_parent_that_is_not_project(self):
        self.assertRejected(mcp_server.create_task, "nie jest projektem", title="x", parent_id=3)

    def test_create_with_deleted_parent(self):
        self.tasks[1]["deleted_at"] = "2026-09-01"
        self.assertRejected(mcp_server.create_task, "Nie znaleziono projektu", title="x", parent_id=1)

    def test_create_project_with_parent(self):
        self.assertRejected(mcp_server.create_task, "nie może mieć parent_id",
                            title="x", parent_id=1, is_project=True)

    def test_create_with_unknown_context(self):
        self.assertRejected(mcp_server.create_task, "kontekstu o id=99", title="x", context_id=99)

    def test_create_valid_subtask_returns_compact(self):
        result = mcp_server.create_task(title="x", parent_id=1, context_id=2)
        self.model.create_task.assert_called_once()
        self.assertEqual(set(result), {"id", "title", "status", "parent_id", "is_project", "context_name"})

    # update_task

    def test_update_with_nonexistent_parent(self):
        self.assertRejected(mcp_server.update_task, "Nie znaleziono projektu o id=999",
                            task_id=3, parent_id=999)

    def test_update_with_parent_that_is_not_project(self):
        self.assertRejected(mcp_server.update_task, "nie jest projektem", task_id=3, parent_id=2)

    def test_update_self_as_parent(self):
        self.assertRejected(mcp_server.update_task, "własnym przodkiem", task_id=1, parent_id=1,
                            is_project=False)

    def test_update_cycle_through_ancestors(self):
        # 4 -> 5 -> 4: podpięcie 5 pod 4 tworzy cykl (niezależnie od reguły o projektach).
        self.assertRejected(mcp_server.update_task, "własnym przodkiem", task_id=5, parent_id=4,
                            is_project=False)

    def test_update_attach_existing_project_to_project(self):
        self.tasks[6] = _task(6, is_project=1)
        self.assertRejected(mcp_server.update_task, "nie może mieć parent_id", task_id=6, parent_id=1)

    def test_update_is_project_and_parent_at_once(self):
        self.assertRejected(mcp_server.update_task, "nie może mieć parent_id",
                            task_id=3, parent_id=1, is_project=True)

    def test_make_project_from_task_with_parent(self):
        self.assertRejected(mcp_server.update_task, "jest podpięte pod projekt", task_id=2, is_project=True)

    def test_make_project_from_task_with_parent_when_detaching(self):
        mcp_server.update_task(task_id=2, is_project=True, parent_id=0)
        self.model.update_task.assert_called_once_with(2, {"parent_id": 0})
        self.model.convert_to_project.assert_called_once_with(2)

    def test_unproject_with_subtasks(self):
        self.assertRejected(mcp_server.update_task, "ma 1 zadań", task_id=1, is_project=False)

    def test_detach_from_project(self):
        mcp_server.update_task(task_id=2, parent_id=0)
        self.model.update_task.assert_called_once_with(2, {"parent_id": 0})


if __name__ == "__main__":
    unittest.main()
