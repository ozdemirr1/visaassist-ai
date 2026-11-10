"""Test-wide settings: a fixed document master key, so the API starts without a real one.

Set before any settings are read; a real key in `.env` is never used by the tests.
"""

import os

TEST_MASTER_KEY = "dGVzdC1vbmx5LW1hc3Rlci1rZXktMzItYnl0ZXMhISE="  # 32 bytes, tests only

os.environ["DOCUMENT_MASTER_KEY"] = TEST_MASTER_KEY
os.environ["DOCUMENT_KEY_ID"] = "test"
