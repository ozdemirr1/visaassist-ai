"""Delete documents past their retention date and files without a database row (ADR 0005).

Run daily, from backend/:

    uv run python -m app.storage.cleanup
"""

import sys

from sqlalchemy.orm import Session

from app.api.documents import get_storage
from app.db import get_engine
from app.storage import documents as docs


def main() -> int:
    storage = get_storage()
    with Session(get_engine()) as session:
        with session.begin():
            keys = docs.delete_documents(session, docs.expired(session))
        for key in keys:
            storage.delete(key)
        orphans = docs.remove_orphans(session, storage)
    print(f"Deleted {len(keys)} expired document(s) and {orphans} orphaned file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
