"""Tests for src/check_updates.py. They never contact the website."""
from src.check_updates import file_urls, file_version, fingerprint


def test_checks_the_same_files_as_download():
    assert file_urls("https://x", "2627") == [
        "https://x/mmz4281/2627/E0.csv",
        "https://x/mmz4281/2627/E1.csv",
        "https://x/fixtures.csv",
    ]


def test_version_prefers_etag():
    headers = {"ETag": '"abc"', "Last-Modified": "Fri, 13 Nov 2026 14:16:25 GMT"}
    assert file_version(headers) == 'etag "abc"'


def test_version_falls_back_to_last_modified_and_size():
    headers = {"Last-Modified": "Fri, 13 Nov 2026 14:16:25 GMT", "Content-Length": "15125"}
    assert file_version(headers) == "modified Fri, 13 Nov 2026 14:16:25 GMT size 15125"


def test_version_unknown_without_either_header():
    assert file_version({"Content-Length": "15125"}) is None


def test_same_versions_give_same_fingerprint_in_any_order():
    a = {"u1": "etag 1", "u2": "etag 2"}
    b = {"u2": "etag 2", "u1": "etag 1"}
    assert fingerprint(a) == fingerprint(b)


def test_any_changed_file_changes_the_fingerprint():
    before = {"u1": "etag 1", "u2": "etag 2", "u3": "missing"}
    for url, new in [("u1", "etag 9"), ("u2", "etag 9"), ("u3", "etag 1")]:
        assert fingerprint({**before, url: new}) != fingerprint(before)


def test_unknown_version_gives_no_fingerprint():
    assert fingerprint({"u1": "etag 1", "u2": None}) is None
