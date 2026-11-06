"""Проверка хеширования паролей."""

from __future__ import annotations

import pytest

from app.utils.errors import AuthError
from app.utils.security import hash_password, validate_password, verify_password


def test_hash_is_not_plaintext_and_is_salted():
    password = "password123"
    first = hash_password(password)
    second = hash_password(password)
    assert password not in first
    assert first != second  # соль делает хеши разными


def test_verify_password():
    digest = hash_password("password123")
    assert verify_password("password123", digest)
    assert not verify_password("password124", digest)


def test_verify_rejects_broken_hash():
    assert not verify_password("password123", "не-хеш")


@pytest.mark.parametrize("password", ["short", "", "x" * 73])
def test_weak_password_is_rejected(password):
    with pytest.raises(AuthError):
        validate_password(password)
