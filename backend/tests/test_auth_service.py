"""Unit tests for auth_service sync helpers."""

import pytest

from app.services.auth_service import (
    create_access_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
    _create_token,
)
from datetime import timedelta


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret")
        assert hashed != "secret"

    def test_verify_correct_password(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False


class TestTokenCreation:
    def test_create_token_with_extra_claims(self):
        token = _create_token(
            subject="user-123",
            token_type="access",
            expires_delta=timedelta(minutes=30),
            extra={"role": "admin"},
        )
        assert token is not None
        user_id = get_user_id_from_token(token, expected_type="access")
        assert user_id == "user-123"

    def test_access_token_has_correct_type(self):
        token = create_access_token("abc")
        user_id = get_user_id_from_token(token, expected_type="access")
        assert user_id == "abc"


class TestGetUserIdFromToken:
    def test_wrong_token_type_raises(self):
        access_token = create_access_token("user-1")
        with pytest.raises(ValueError, match="Expected token type"):
            get_user_id_from_token(access_token, expected_type="refresh")

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid or expired token"):
            get_user_id_from_token("not.a.token", expected_type="access")

    def test_empty_subject_raises(self):
        token = _create_token(
            subject="",
            token_type="access",
            expires_delta=timedelta(minutes=30),
        )
        with pytest.raises(ValueError, match="Token missing subject"):
            get_user_id_from_token(token, expected_type="access")
