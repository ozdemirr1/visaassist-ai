"""Password hashing and input checks of the auth service (no database needed)."""

import pytest

from app.auth import service


def test_password_hash_is_argon2id_and_verifies() -> None:
    password_hash = service.hash_password("correct horse battery")
    assert password_hash.startswith("$argon2id$")
    assert service.verify_password(password_hash, "correct horse battery")
    assert not service.verify_password(password_hash, "correct horse batterz")


def test_same_password_gives_different_hashes() -> None:
    assert service.hash_password("same password") != service.hash_password("same password")


def test_a_broken_hash_does_not_verify() -> None:
    assert not service.verify_password("not a hash", "whatever")


@pytest.mark.parametrize(
    ("raw", "normalised"),
    [("Ayse@Example.COM", "ayse@example.com"), ("  ali@example.com.tr ", "ali@example.com.tr")],
)
def test_email_is_normalised(raw: str, normalised: str) -> None:
    assert service.normalise_email(raw) == normalised


@pytest.mark.parametrize(
    "bad", ["", "no-at-sign", "@example.com", "a@nodot", "a@.com", "a b@x.com"]
)
def test_invalid_email_is_refused(bad: str) -> None:
    with pytest.raises(service.InvalidEmail):
        service.normalise_email(bad)


def test_short_and_overlong_passwords_are_refused() -> None:
    with pytest.raises(service.WeakPassword):
        service.check_password_strength("short")
    with pytest.raises(service.WeakPassword):
        service.check_password_strength("x" * (service.MAX_PASSWORD_LENGTH + 1))
    service.check_password_strength("x" * service.MIN_PASSWORD_LENGTH)
