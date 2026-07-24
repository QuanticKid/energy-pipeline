import pytest
import requests

from ingestion.ingest import fetch_page, MAX_RETRIES


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeSession:
    """Returns the queued responses one by one and records how often it was called."""

    def __init__(self, responses: list[FakeResponse]):
        self._responses = responses
        self.calls = 0

    def get(self, url, params=None) -> FakeResponse:
        self.calls += 1
        return self._responses[self.calls - 1]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # The retry path sleeps 20s between attempts; the test must not wait for it.
    monkeypatch.setattr("ingestion.ingest.time.sleep", lambda seconds: None)


def test_returns_data_on_success():
    session = FakeSession([FakeResponse(200, {"data": [{"value": 1}]})])

    result = fetch_page(session, dataset_id=188, page=1)

    assert result == [{"value": 1}]
    assert session.calls == 1


def test_retries_after_rate_limit():
    session = FakeSession([
        FakeResponse(429),
        FakeResponse(200, {"data": [{"value": 2}]}),
    ])

    result = fetch_page(session, dataset_id=188, page=1)

    assert result == [{"value": 2}]
    assert session.calls == 2


def test_gives_up_after_max_retries():
    session = FakeSession([FakeResponse(429)] * MAX_RETRIES)

    with pytest.raises(RuntimeError):
        fetch_page(session, dataset_id=188, page=1)

    assert session.calls == MAX_RETRIES