"""AI client with fallback between providers.

Providers are tried in order. One that hit its rate limit (or is misconfigured) is
skipped for a while, so requests do not keep failing on it.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import openai

from bot.ai.errors import AIUnavailableError
from bot.ai.providers import PROVIDERS
from bot.ai.request_log import JsonlRequestLog, RequestLog
from bot.config import AISettings

logger = logging.getLogger(__name__)

# A wrong key or model will not fix itself; check the logs and .env.
CONFIG_ERROR_COOLDOWN_SECONDS = 3600


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str


@dataclass(frozen=True)
class Completion:
    text: str
    provider: str
    model: str


@dataclass(frozen=True)
class ProviderAnswer:
    text: str
    # The model that actually answered: with fallback models it may differ from the first one.
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class EmptyAnswerError(Exception):
    """The provider answered, but with no text."""


class ChatProvider(Protocol):
    name: str
    model: str

    async def complete(self, prompt: Prompt, max_tokens: int) -> ProviderAnswer:
        """Raises openai.APIError subclasses or EmptyAnswerError."""
        ...

    async def close(self) -> None: ...


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        models: list[str],
        timeout: float,
        max_models: int = 1,
    ) -> None:
        self.name = name
        self.model = models[0]
        # OpenRouter can itself try the next model when one is busy ("models" parameter).
        self._fallback_models = models[:max_models] if max_models > 1 and len(models) > 1 else None
        # No retries inside the SDK: on failure we move on to the next provider instead.
        self._client = openai.AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0
        )

    async def complete(self, prompt: Prompt, max_tokens: int) -> ProviderAnswer:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            max_tokens=max_tokens,
            extra_body={"models": self._fallback_models} if self._fallback_models else None,
        )
        text = response.choices[0].message.content if response.choices else None
        if not text or not text.strip():
            raise EmptyAnswerError(f"finish_reason={response.choices[0].finish_reason}")
        usage = response.usage
        return ProviderAnswer(
            text=text.strip(),
            model=response.model or self.model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )

    async def close(self) -> None:
        await self._client.close()


class AIClient:
    def __init__(
        self,
        providers: Sequence[ChatProvider],
        *,
        max_tokens: int,
        max_concurrency: int,
        rate_limit_cooldown: float,
        request_log: RequestLog | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._providers = list(providers)
        self._request_log = request_log
        self._max_tokens = max_tokens
        self._rate_limit_cooldown = rate_limit_cooldown
        self._clock = clock
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._skip_until: dict[str, float] = {}

    async def generate(self, prompt: Prompt) -> Completion:
        async with self._semaphore:
            for provider in self._providers:
                if self._clock() < self._skip_until.get(provider.name, 0):
                    continue
                started = self._clock()
                try:
                    answer = await provider.complete(prompt, self._max_tokens)
                except (openai.APIError, EmptyAnswerError) as error:
                    self._log_request(prompt, provider, started, error=error)
                    self._handle_failure(provider, error)
                else:
                    self._log_request(prompt, provider, started, answer=answer)
                    logger.info(
                        "AI answer: provider=%s model=%s seconds=%.1f tokens=%s+%s",
                        provider.name,
                        answer.model,
                        self._clock() - started,
                        answer.prompt_tokens,
                        answer.completion_tokens,
                    )
                    return Completion(text=answer.text, provider=provider.name, model=answer.model)
        raise AIUnavailableError("no AI provider could answer")

    def _handle_failure(self, provider: ChatProvider, error: Exception) -> None:
        match error:
            case openai.RateLimitError():
                cooldown = _retry_after(error) or self._rate_limit_cooldown
                self._skip(provider, cooldown)
                logger.warning("AI %s: rate limit, skipping for %.0f s", provider.name, cooldown)
            case (
                openai.AuthenticationError()
                | openai.PermissionDeniedError()
                | openai.NotFoundError()
            ):
                self._skip(provider, CONFIG_ERROR_COOLDOWN_SECONDS)
                logger.error(
                    "AI %s: check its API key and model in .env (%s: %s)",
                    provider.name,
                    type(error).__name__,
                    error,
                )
            case _:
                logger.warning(
                    "AI %s failed, trying the next provider (%s: %s)",
                    provider.name,
                    type(error).__name__,
                    error,
                )

    def _log_request(
        self,
        prompt: Prompt,
        provider: ChatProvider,
        started: float,
        *,
        answer: ProviderAnswer | None = None,
        error: Exception | None = None,
    ) -> None:
        if self._request_log is None:
            return
        record: dict[str, Any] = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "provider": provider.name,
            "model": answer.model if answer else provider.model,
            "ok": answer is not None,
            "seconds": round(self._clock() - started, 1),
            "prompt_tokens": answer.prompt_tokens if answer else None,
            "completion_tokens": answer.completion_tokens if answer else None,
            "error": f"{type(error).__name__}: {error}" if error else None,
            "system": prompt.system,
            "user": prompt.user,
            "answer": answer.text if answer else None,
        }
        try:
            self._request_log.write(record)
        except OSError:
            # A full disk must not break answers to users.
            logger.exception("Could not write the AI request log")

    def _skip(self, provider: ChatProvider, seconds: float) -> None:
        self._skip_until[provider.name] = self._clock() + seconds

    async def close(self) -> None:
        for provider in self._providers:
            await provider.close()
        if self._request_log is not None:
            self._request_log.close()


def _retry_after(error: openai.APIStatusError) -> float | None:
    value = error.response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:  # it can also be an HTTP date; then the default cooldown is used
        return None


def build_ai_client(settings: AISettings) -> AIClient:
    providers: list[ChatProvider] = []
    for name in settings.provider_order:
        spec = PROVIDERS.get(name)
        if spec is None:
            raise ValueError(f"Unknown AI provider in AI_PROVIDERS: {name!r}")
        api_key = settings.api_key(name)
        if not api_key:
            logger.info("AI %s: no API key, skipped", name)
            continue
        models = settings.models(name) or ([spec.default_model] if spec.default_model else [])
        if not models:
            logger.warning("AI %s: set %s_MODEL in .env, skipped", name, name.upper())
            continue
        if len(models) > spec.max_models:
            logger.warning(
                "AI %s accepts at most %d model(s) in %s_MODEL; using: %s",
                name,
                spec.max_models,
                name.upper(),
                ", ".join(models[: spec.max_models]),
            )
            models = models[: spec.max_models]
        providers.append(
            OpenAICompatibleProvider(
                name=name,
                base_url=spec.base_url,
                api_key=api_key,
                models=models,
                timeout=settings.ai_timeout_seconds,
                max_models=spec.max_models,
            )
        )
    if not providers:
        logger.warning("No AI provider is configured: AI answers will not work")
    request_log = (
        JsonlRequestLog(Path(settings.ai_request_log_path))
        if settings.ai_request_log_path
        else None
    )
    return AIClient(
        providers,
        max_tokens=settings.ai_max_tokens,
        max_concurrency=settings.ai_max_concurrency,
        rate_limit_cooldown=settings.ai_rate_limit_cooldown_seconds,
        request_log=request_log,
    )
