"""Known AI providers. All of them speak the OpenAI-compatible chat completions API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    # None: the model must be set in .env (<NAME>_MODEL), e.g. because free models change often.
    default_model: str | None
    # How many models the provider accepts in one request, trying the next one itself
    # if one is busy. 1: no such feature.
    max_models: int = 1


PROVIDERS = {
    spec.name: spec
    for spec in (
        # Only models with the ":free" suffix are free; pick at openrouter.ai/models.
        # OPENROUTER_MODEL may list up to 3, comma-separated: the first is tried first.
        ProviderSpec("openrouter", "https://openrouter.ai/api/v1", None, max_models=3),
        # Not available from Belarus.
        ProviderSpec("groq", "https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
        # Paid.
        ProviderSpec("mistral", "https://api.mistral.ai/v1", "mistral-small-latest"),
    )
}
