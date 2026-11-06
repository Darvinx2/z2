"""Проверка ограничения файловых операций каталогом-песочницей."""

from __future__ import annotations

import pytest

from app.utils.errors import SecurityError
from app.utils.paths import STORAGE_ROOT, resolve_user_path, to_relative


def test_relative_path_resolves_inside_storage():
    path = resolve_user_path("notes/hello.txt")
    assert path.parent.parent == STORAGE_ROOT.resolve()
    assert to_relative(path) == "notes/hello.txt"


@pytest.mark.parametrize(
    "bad_path",
    ["../secret.txt", "notes/../../secret.txt", "/etc/passwd", "..\\..\\secret.txt", "  "],
)
def test_path_traversal_is_rejected(bad_path):
    with pytest.raises(SecurityError):
        resolve_user_path(bad_path)


def test_missing_path_with_must_exist_is_rejected():
    with pytest.raises(SecurityError):
        resolve_user_path("no-such-file.txt", must_exist=True)
