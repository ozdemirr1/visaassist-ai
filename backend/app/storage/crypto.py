"""Envelope encryption with AES-256-GCM (ADR 0005).

Every document has its own random data key. The data key encrypts the file and its original
name; the master key from the settings encrypts ("wraps") the data key. Every encrypted value
starts with its own random 96-bit nonce. The document ID is bound as associated data, so a file
or a wrapped key copied to another record fails to decrypt.
"""

import base64
import os
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32
NONCE_BYTES = 12


class DecryptionError(Exception):
    """The value was changed, or the key or the document does not match."""


def new_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encode_key(key: bytes) -> str:
    return base64.b64encode(key).decode()


def decode_master_key(value: str | None) -> bytes:
    """The master key from its base64 setting; refuses a missing or wrong-length key."""
    if not value:
        raise ValueError("DOCUMENT_MASTER_KEY is not set; run `python -m app.storage.new_key`.")
    try:
        key = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise ValueError("DOCUMENT_MASTER_KEY is not valid base64.") from error
    if len(key) != KEY_BYTES:
        raise ValueError(f"DOCUMENT_MASTER_KEY must decode to {KEY_BYTES} bytes.")
    return key


def _aad(document_id: uuid.UUID, purpose: str) -> bytes:
    return f"{purpose}:{document_id}".encode()


def encrypt(key: bytes, plaintext: bytes, document_id: uuid.UUID, purpose: str) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, _aad(document_id, purpose))


def decrypt(key: bytes, value: bytes, document_id: uuid.UUID, purpose: str) -> bytes:
    nonce, ciphertext = value[:NONCE_BYTES], value[NONCE_BYTES:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, _aad(document_id, purpose))
    except (InvalidTag, ValueError) as error:
        raise DecryptionError("Cannot decrypt: changed data or wrong key.") from error


def wrap_key(master_key: bytes, data_key: bytes, document_id: uuid.UUID, key_id: str) -> bytes:
    return encrypt(master_key, data_key, document_id, f"key/{key_id}")


def unwrap_key(master_key: bytes, wrapped: bytes, document_id: uuid.UUID, key_id: str) -> bytes:
    return decrypt(master_key, wrapped, document_id, f"key/{key_id}")
