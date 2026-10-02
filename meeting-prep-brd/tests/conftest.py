"""The live world the tests read: the prep database (5434, schema brd), the
mock web (:8100), Mailpit (:8025), and the seminar router for embeddings.

Set PREP_DB_URL, OPENAI_BASE_URL and OPENAI_API_KEY before running; tests
that need a service which is not there are skipped, never faked.
"""
import os
import socket

import pytest


def _up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def pytest_configure(config):
    config.addinivalue_line("markers", "live(*ports): needs these local services")


def pytest_runtest_setup(item):
    marker = item.get_closest_marker("live")
    if marker is None:
        return
    if not os.environ.get("PREP_DB_URL") or not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("PREP_DB_URL and OPENAI_API_KEY are not set")
    down = [p for p in marker.args if not _up(p)]
    if down:
        pytest.skip(f"no service on {down}")
