"""Encryption and the local file store (no database needed)."""

import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.storage import crypto
from app.storage import documents as docs
from app.storage.files import LocalStorage


def test_encrypt_round_trip_and_fresh_nonce() -> None:
    key, document_id = crypto.new_key(), uuid.uuid4()
    first = crypto.encrypt(key, b"passport scan", document_id, "file")
    second = crypto.encrypt(key, b"passport scan", document_id, "file")
    assert first != second  # a new nonce every time
    assert b"passport scan" not in first
    assert crypto.decrypt(key, first, document_id, "file") == b"passport scan"


def test_a_changed_byte_fails() -> None:
    key, document_id = crypto.new_key(), uuid.uuid4()
    value = bytearray(crypto.encrypt(key, b"bank statement", document_id, "file"))
    value[-1] ^= 1
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(key, bytes(value), document_id, "file")


def test_another_document_or_purpose_fails() -> None:
    key, document_id = crypto.new_key(), uuid.uuid4()
    value = crypto.encrypt(key, b"payslip", document_id, "file")
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(key, value, uuid.uuid4(), "file")
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(key, value, document_id, "name")


def test_wrapped_key_needs_the_right_master_key() -> None:
    master, data_key, document_id = crypto.new_key(), crypto.new_key(), uuid.uuid4()
    wrapped = crypto.wrap_key(master, data_key, document_id, "k1")
    assert crypto.unwrap_key(master, wrapped, document_id, "k1") == data_key
    with pytest.raises(crypto.DecryptionError):
        crypto.unwrap_key(crypto.new_key(), wrapped, document_id, "k1")
    with pytest.raises(crypto.DecryptionError):
        crypto.unwrap_key(master, wrapped, document_id, "k2")


@pytest.mark.parametrize("value", [None, "", "not base64!", crypto.encode_key(b"short")])
def test_bad_master_key_is_refused(value: str | None) -> None:
    with pytest.raises(ValueError):
        crypto.decode_master_key(value)


@pytest.mark.parametrize(
    ("data", "mime"),
    [
        (b"%PDF-1.7\n...", "application/pdf"),
        (b"\xff\xd8\xff\xe0...", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n...", "image/png"),
        (b"MZ\x90\x00", None),
        (b"<html>", None),
    ],
)
def test_type_comes_from_the_first_bytes(data: bytes, mime: str | None) -> None:
    assert docs.detect_type(data) == mime


def test_retention_is_30_days_after_the_trip() -> None:
    assert docs.delete_after(date(2027, 4, 20)).date() == date(2027, 4, 20) + timedelta(days=30)


def test_local_storage_write_read_delete(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    key = uuid.uuid4().hex
    storage.write(key, b"encrypted bytes")
    assert storage.read(key) == b"encrypted bytes"
    assert storage.keys() == {key}
    assert not list(tmp_path.rglob("*.part"))
    storage.delete(key)
    assert not storage.exists(key)


@pytest.mark.parametrize("bad", ["../etc/passwd", "ABC", "a" * 31, "g" * 32])
def test_storage_refuses_keys_that_are_not_random_hex(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).write(bad, b"x")
