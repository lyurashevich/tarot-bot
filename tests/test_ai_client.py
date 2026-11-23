import httpx2 as httpx
import openai
import pytest

from bot.ai import AIClient, AIUnavailableError, Prompt
from bot.ai.client import CONFIG_ERROR_COOLDOWN_SECONDS, EmptyAnswerError, ProviderAnswer

PROMPT = Prompt(system="system", user="user")


def _response(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return httpx.Response(status, headers=headers, request=request)


def rate_limit(retry_after: str | None = None) -> openai.RateLimitError:
    headers = {"retry-after": retry_after} if retry_after else None
    return openai.RateLimitError("rate limit", response=_response(429, headers), body=None)


def bad_key() -> openai.AuthenticationError:
    return openai.AuthenticationError("bad key", response=_response(401), body=None)


def server_error() -> openai.InternalServerError:
    return openai.InternalServerError("oops", response=_response(500), body=None)


def timeout() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=httpx.Request("POST", "https://example.test"))


class FakeProvider:
    """Answers from a script: each item is either text or an exception to raise."""

    def __init__(self, name: str, *script: str | Exception) -> None:
        self.name = name
        self.model = f"{name}-model"
        self._script = list(script)
        self.calls = 0

    async def complete(self, prompt: Prompt, max_tokens: int) -> ProviderAnswer:
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return ProviderAnswer(text=item, model=self.model)

    async def close(self) -> None:
        pass


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_client(*providers: FakeProvider, clock: FakeClock | None = None) -> AIClient:
    return AIClient(
        providers,
        max_tokens=100,
        max_concurrency=2,
        rate_limit_cooldown=600,
        clock=clock or FakeClock(),
    )


async def test_uses_first_provider_when_it_answers() -> None:
    first, second = FakeProvider("a", "ответ"), FakeProvider("b", "другой")

    completion = await make_client(first, second).generate(PROMPT)

    assert (completion.text, completion.provider, completion.model) == ("ответ", "a", "a-model")
    assert second.calls == 0


@pytest.mark.parametrize(
    "error",
    [rate_limit(), server_error(), timeout(), bad_key(), EmptyAnswerError("empty")],
    ids=["rate-limit", "server-error", "timeout", "bad-key", "empty-answer"],
)
async def test_falls_back_to_next_provider(error: Exception) -> None:
    first, second = FakeProvider("a", error), FakeProvider("b", "запасной ответ")

    completion = await make_client(first, second).generate(PROMPT)

    assert completion.provider == "b"
    assert completion.text == "запасной ответ"


async def test_raises_when_no_provider_answers() -> None:
    client = make_client(FakeProvider("a", rate_limit()), FakeProvider("b", timeout()))

    with pytest.raises(AIUnavailableError):
        await client.generate(PROMPT)


async def test_raises_when_no_provider_is_configured() -> None:
    with pytest.raises(AIUnavailableError):
        await make_client().generate(PROMPT)


async def test_rate_limited_provider_is_skipped_until_cooldown_ends() -> None:
    clock = FakeClock()
    first = FakeProvider("a", rate_limit(), "снова работаю")
    second = FakeProvider("b", "b1", "b2")
    client = make_client(first, second, clock=clock)

    assert (await client.generate(PROMPT)).provider == "b"
    clock.now += 599
    assert (await client.generate(PROMPT)).provider == "b"
    assert first.calls == 1  # not asked again while cooling down

    clock.now += 2
    assert (await client.generate(PROMPT)).provider == "a"


async def test_cooldown_follows_retry_after_header() -> None:
    clock = FakeClock()
    first = FakeProvider("a", rate_limit(retry_after="30"), "снова работаю")
    client = make_client(first, FakeProvider("b", "b1"), clock=clock)

    await client.generate(PROMPT)
    clock.now += 31

    assert (await client.generate(PROMPT)).provider == "a"


async def test_misconfigured_provider_is_skipped_for_a_long_time() -> None:
    clock = FakeClock()
    first = FakeProvider("a", bad_key())
    client = make_client(first, FakeProvider("b", "b1", "b2"), clock=clock)

    await client.generate(PROMPT)
    clock.now += CONFIG_ERROR_COOLDOWN_SECONDS - 1
    await client.generate(PROMPT)

    assert first.calls == 1


async def test_server_error_does_not_skip_provider() -> None:
    first = FakeProvider("a", server_error(), "уже в порядке")
    client = make_client(first, FakeProvider("b", "b1"))

    await client.generate(PROMPT)

    assert (await client.generate(PROMPT)).provider == "a"


def test_model_setting_may_list_several_models() -> None:
    from bot.config import AISettings

    settings = AISettings(_env_file=None, openrouter_model=" a:free , b:free,")

    assert settings.models("openrouter") == ["a:free", "b:free"]
    assert settings.models("groq") == []


class ListLog:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def write(self, record: dict) -> None:
        self.records.append(record)

    def close(self) -> None:
        pass


async def test_every_attempt_is_written_to_the_request_log() -> None:
    log = ListLog()
    client = AIClient(
        [FakeProvider("a", rate_limit()), FakeProvider("b", "ответ")],
        max_tokens=100,
        max_concurrency=1,
        rate_limit_cooldown=60,
        request_log=log,
    )

    await client.generate(PROMPT)

    failed, succeeded = log.records
    assert (failed["provider"], failed["ok"], failed["answer"]) == ("a", False, None)
    assert failed["error"].startswith("RateLimitError")
    assert (succeeded["provider"], succeeded["ok"], succeeded["answer"]) == ("b", True, "ответ")
    assert succeeded["error"] is None
    assert succeeded["system"] == "system" and succeeded["user"] == "user"


def test_jsonl_request_log_writes_one_json_object_per_line(tmp_path) -> None:
    import json

    from bot.ai.request_log import JsonlRequestLog

    path = tmp_path / "logs" / "ai.jsonl"
    log = JsonlRequestLog(path)
    log.write({"user": "Что меня ждёт?", "ok": True})
    log.write({"user": "второй", "ok": False})
    log.close()

    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["user"] for line in lines] == ["Что меня ждёт?", "второй"]
    assert "Что меня ждёт?" in lines[0]  # readable Cyrillic, not \u escapes
