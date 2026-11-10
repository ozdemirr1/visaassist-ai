"""Print a new random master key for DOCUMENT_MASTER_KEY (ADR 0005).

    uv run python -m app.storage.new_key

Put the printed line into the repository-root `.env`. Keep it out of the repository; losing it
makes every stored document unreadable.
"""

from app.storage.crypto import encode_key, new_key

if __name__ == "__main__":
    print(f"DOCUMENT_MASTER_KEY={encode_key(new_key())}")
