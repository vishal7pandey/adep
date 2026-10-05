"""UsageMeter counts and caps OpenAI chat-completion spend, from outside the engines (ADE-31)."""

import asyncio
from types import SimpleNamespace

import pytest
from openai import AsyncOpenAI, OpenAI
from openai.resources.chat.completions import AsyncCompletions, Completions

from src.eval.usage_meter import SpendCapReached, UsageMeter


def _sync() -> Completions:
    """A real SDK resource on a client that never connects (create is faked in every test)."""
    return OpenAI(api_key="test-key", base_url="http://127.0.0.1:9").chat.completions


def _async() -> AsyncCompletions:
    return AsyncOpenAI(api_key="test-key", base_url="http://127.0.0.1:9").chat.completions


def _response(prompt: int, completion: int) -> SimpleNamespace:
    usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)
    return SimpleNamespace(usage=usage)


@pytest.fixture
def fake_create(monkeypatch):
    """Replace both create methods with fakes that record how often they were really called."""
    calls = {"sync": 0, "async": 0}

    def sync_create(self, **kwargs):
        calls["sync"] += 1
        return _response(10, 5)

    async def async_create(self, **kwargs):
        calls["async"] += 1
        return _response(20, 7)

    monkeypatch.setattr(Completions, "create", sync_create)
    monkeypatch.setattr(AsyncCompletions, "create", async_create)
    return calls


class TestCounting:
    def test_counts_sync_and_async_calls_and_tokens(self, fake_create):
        sync_client, async_client = _sync(), _async()
        with UsageMeter() as meter:
            sync_client.create(model="m", messages=[])
            asyncio.run(async_client.create(model="m", messages=[]))
        assert meter.calls == 2
        assert (meter.prompt_tokens, meter.completion_tokens) == (30, 12)
        assert meter.total_tokens == 42
        assert fake_create == {"sync": 1, "async": 1}

    def test_response_without_usage_counts_the_call_but_no_tokens(self, monkeypatch):
        monkeypatch.setattr(Completions, "create", lambda self, **kw: SimpleNamespace(usage=None))
        with UsageMeter() as meter:
            _sync().create(model="m", messages=[])
        assert (meter.calls, meter.total_tokens) == (1, 0)

    def test_snapshot_supports_per_run_deltas(self, fake_create):
        client = _sync()
        with UsageMeter() as meter:
            client.create(model="m", messages=[])
            before = meter.snapshot()
            client.create(model="m", messages=[])
            after = meter.snapshot()
        assert tuple(a - b for a, b in zip(after, before)) == (1, 10, 5)


class TestCaps:
    def test_call_cap_blocks_the_next_call_without_reaching_the_provider(self, fake_create):
        client = _sync()
        with UsageMeter(max_calls=2) as meter:
            client.create(model="m", messages=[])
            client.create(model="m", messages=[])
            with pytest.raises(SpendCapReached):
                client.create(model="m", messages=[])
        assert fake_create["sync"] == 2
        assert meter.calls == 2

    def test_token_cap_blocks_once_reached_and_applies_to_async_too(self, fake_create):
        sync_client, async_client = _sync(), _async()
        with UsageMeter(max_tokens=15) as meter:
            sync_client.create(model="m", messages=[])  # 15 tokens: now exactly at the cap
            assert meter.exhausted
            with pytest.raises(SpendCapReached):
                asyncio.run(async_client.create(model="m", messages=[]))
        assert fake_create == {"sync": 1, "async": 0}

    def test_below_the_cap_calls_go_through(self, fake_create):
        with UsageMeter(max_calls=3, max_tokens=100) as meter:
            _sync().create(model="m", messages=[])
        assert not meter.exhausted


class TestRestore:
    def test_originals_restored_even_when_the_body_raises(self, fake_create):
        before = (Completions.create, AsyncCompletions.create)
        with pytest.raises(ValueError):
            with UsageMeter():
                assert Completions.create is not before[0]
                raise ValueError("boom")
        assert (Completions.create, AsyncCompletions.create) == before

    def test_cannot_nest_the_same_meter(self, fake_create):
        meter = UsageMeter()
        with meter:
            with pytest.raises(RuntimeError, match="already active"):
                meter.__enter__()
