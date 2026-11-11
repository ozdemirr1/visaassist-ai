"""Test-wide settings, set before any settings are read, so the tests do not depend on `.env`.

A fixed document master key lets the API start without a real one, and a real key in `.env` is
never used. The session cookie is Secure as in production, even when the developer's `.env` turns
that off for a browser on http://localhost.
"""

import os

TEST_MASTER_KEY = "dGVzdC1vbmx5LW1hc3Rlci1rZXktMzItYnl0ZXMhISE="  # 32 bytes, tests only

os.environ["DOCUMENT_MASTER_KEY"] = TEST_MASTER_KEY
os.environ["DOCUMENT_KEY_ID"] = "test"
os.environ["COOKIE_SECURE"] = "true"
