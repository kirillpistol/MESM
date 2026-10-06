from email.message import Message
from io import BytesIO
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

from mesm.ingest import official_web
from mesm.ingest.official_web import _request_bytes, is_allowed_url

HOSTS = {"admsurgut.ru"}


class _Resp:
    def __init__(self, body=b"data", url="https://admsurgut.ru/a.xlsx"):
        self._body = BytesIO(body)
        self._url = url
        self.headers = Message()
        self.headers["Content-Type"] = "application/octet-stream"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return self._url

    def read(self, n=-1):
        return self._body.read(n)


def test_is_allowed_url_requires_https_and_known_host():
    assert is_allowed_url("https://admsurgut.ru/f.xlsx", HOSTS)
    assert not is_allowed_url("http://admsurgut.ru/f.xlsx", HOSTS)
    assert not is_allowed_url("file:///etc/passwd", HOSTS)
    assert not is_allowed_url("https://evil.example/f.xlsx", HOSTS)
    assert not is_allowed_url("https://sub.admsurgut.ru/f.xlsx", HOSTS)


def test_request_rejects_foreign_host_before_any_network_call():
    with mock.patch.object(official_web, "urlopen") as opened:
        with pytest.raises(ValueError):
            _request_bytes("https://evil.example/a.xlsx", allowed_hosts=HOSTS)
    opened.assert_not_called()


def test_request_retries_on_server_error_then_succeeds():
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(1)
        if len(calls) < 3:
            raise HTTPError(request.full_url, 503, "busy", Message(), None)
        return _Resp(b"ok")

    sleeps = []
    with mock.patch.object(official_web, "urlopen", fake_urlopen):
        body, _ = _request_bytes(
            "https://admsurgut.ru/a.xlsx", allowed_hosts=HOSTS, retries=3, sleep=sleeps.append
        )
    assert body == b"ok"
    assert len(calls) == 3
    assert sleeps == [2.0, 4.0]


def test_request_does_not_retry_not_found():
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(1)
        raise HTTPError(request.full_url, 404, "nf", Message(), None)

    with mock.patch.object(official_web, "urlopen", fake_urlopen):
        with pytest.raises(HTTPError):
            _request_bytes("https://admsurgut.ru/a.xlsx", allowed_hosts=HOSTS, sleep=lambda s: None)
    assert len(calls) == 1


def test_request_gives_up_after_retries_on_network_error():
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(1)
        raise URLError("down")

    with mock.patch.object(official_web, "urlopen", fake_urlopen):
        with pytest.raises(URLError):
            _request_bytes(
                "https://admsurgut.ru/a.xlsx", allowed_hosts=HOSTS, retries=3, sleep=lambda s: None
            )
    assert len(calls) == 3


def test_request_rejects_redirect_to_foreign_host():
    with mock.patch.object(
        official_web, "urlopen", lambda r, timeout=0: _Resp(url="https://evil.example/x")
    ):
        with pytest.raises(ValueError):
            _request_bytes("https://admsurgut.ru/a.xlsx", allowed_hosts=HOSTS)


def test_request_rejects_oversized_download():
    with mock.patch.object(official_web, "urlopen", lambda r, timeout=0: _Resp(b"x" * 100)):
        with pytest.raises(ValueError):
            _request_bytes("https://admsurgut.ru/a.xlsx", allowed_hosts=HOSTS, max_bytes=10)
