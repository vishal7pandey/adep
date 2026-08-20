"""Type-safe configuration via Pydantic Settings [CM].

Provider selection is config-driven; the ocr/vlm tool interfaces are identical
regardless of backend, so swapping is a one-line change [§9]. Cycle caps enforce
the give-up threshold [§2.6]. All secrets come from environment variables, never
hardcoded [AKM].
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file.

    All fields have sensible defaults for local development. Override via
    environment variables (e.g. ADE_OCR_PROVIDER=tesseract) or a .env file.

    Attributes:
        ocr_provider: Which OCR backend to use ("paddle" or "tesseract").
        vlm_provider: Which VLM backend to use ("azure").
        azure_api_key: API key for Azure OpenAI (loaded from env, never hardcoded).
        azure_chat_endpoint: Azure OpenAI chat endpoint URL.
        azure_chat_deployment: Azure OpenAI chat deployment name (e.g. gpt-5.4).
        azure_embedding_endpoint: Azure OpenAI embedding endpoint URL.
        azure_embedding_deployment: Azure OpenAI embedding deployment name.
        default_confidence_threshold: Minimum confidence for a field to be
            considered satisfied [§4.1].
        max_cycles_per_field: Hard cap on ReAct attempts per field [§2.6].
        max_cycles_per_document: Hard cap on total ReAct attempts per run [§2.6].
        trace_window_size: Max trace entries kept in the active rolling
            window [§12.3]. Full trace persists in the LangGraph checkpoint.
        log_level: Logging level (DEBUG / INFO / WARNING / ERROR).
    """

    model_config = SettingsConfigDict(
        env_prefix="ADE_",
        env_file=".env",
        env_file_encoding="latin-1",
        extra="ignore",
    )

    # Provider selection [§9]
    ocr_provider: str = "paddle"
    vlm_provider: str = "azure"

    # Azure OpenAI — primary LLM + VLM (GPT-5.4) [AKM]
    azure_api_key: str = Field(default="", alias="AZURE_API_KEY")
    azure_chat_endpoint: str = Field(default="", alias="AZURE_CHAT_ENDPOINT")
    azure_chat_deployment: str = Field(default="gpt-5.4", alias="AZURE_CHAT_DEPLOYMENT")
    azure_embedding_endpoint: str = Field(default="", alias="AZURE_EMBEDDING_ENDPOINT")
    azure_embedding_deployment: str = Field(default="text-embedding-3-large", alias="AZURE_EMBEDDING_DEPLOYMENT")

    # Validation thresholds [§4.1]
    default_confidence_threshold: float = 0.8

    # Give-up caps [§2.6]
    max_cycles_per_field: int = 5
    max_cycles_per_document: int = 30

    # Trace compaction [§12.3]
    trace_window_size: int = 10

    # Context compaction [§12.4]
    compaction_enabled: bool = True
    compaction_threshold: int = 15

    # Observability [LS, BLK-130]
    log_level: str = "INFO"
    log_format: str = "console"  # "json" or "console"
    otel_endpoint: str = ""  # OTLP endpoint; empty = tracing disabled

    # Token pricing per 1K tokens [BLK-050, §15]
    llm_pricing_input_per_1k: float = 0.005
    llm_pricing_output_per_1k: float = 0.015
    vlm_pricing_input_per_1k: float = 0.01
    vlm_pricing_output_per_1k: float = 0.03

    # Budget limits [BLK-051, §15]
    budget_per_run_tokens: int = 100_000
    budget_per_run_cost_usd: float = 1.0
    budget_per_definition_daily_tokens: int = 1_000_000
    budget_per_definition_daily_cost_usd: float = 10.0
    budget_global_daily_tokens: int = 10_000_000
    budget_global_daily_cost_usd: float = 100.0
    budget_warning_threshold: float = 0.8

    # Authentication [BLK-122, BLK-153] — secure by default
    auth_enabled: bool = True

    # Document classification [BLK-127]
    auto_route_threshold: float = 0.75

    # Tool result caching [BLK-124]
    cache_enabled: bool = True
    cache_ttl_seconds: int = 2_592_000  # 30 days
    cache_max_size_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    cache_memory_entries: int = 256  # LRU in-memory bound
    cache_version: str = "v1"

    # Async run execution [BLK-129]
    max_concurrent_runs: int = 3

    # Definition store backend [BLK-036]
    store_backend: str = "file"  # "file" or "sqlite"
    store_db_path: str = ".adep/store.db"  # SQLite DB path (relative to cwd)

    # Rate limiting [BLK-123] — enabled by default (secure for production) [SCRUM-63]
    rate_limit_enabled: bool = True  # set ADE_RATE_LIMIT_ENABLED=false for local dev
    rate_limit_post_runs_per_min: int = 10
    rate_limit_post_documents_per_min: int = 20
    rate_limit_mutating_per_min: int = 60
    rate_limit_get_per_min: int = 300
    rate_limit_sse_concurrent_per_key: int = 5
    rate_limit_eviction_interval_seconds: int = 300  # 5 minutes

    def validate_provider_config(self) -> None:
        """Fail fast on empty or partially configured provider credentials [BLK-173].

        Detects:
          - API key set but endpoint missing (or vice versa) — partial config
            that would silently produce zero-output runs.
          - Both key and endpoint missing — no LLM provider at all.

        Raises:
            ValueError: If provider credentials are partially or fully missing
                and no PDF fallback is available.
        """
        azure_fields = {
            "AZURE_API_KEY": self.azure_api_key,
            "AZURE_CHAT_ENDPOINT": self.azure_chat_endpoint,
        }
        set_fields = {k: v for k, v in azure_fields.items() if v.strip()}
        unset_fields = [k for k, v in azure_fields.items() if not v.strip()]

        if unset_fields and set_fields:
            # Partial configuration — some fields set, some empty
            raise ValueError(
                f"Partial Azure OpenAI configuration detected [BLK-173]. "
                f"Set: {list(set_fields.keys())}, Missing: {unset_fields}. "
                f"Either provide ALL required Azure credentials "
                f"(AZURE_API_KEY, AZURE_CHAT_ENDPOINT) or leave ALL empty "
                f"to use PDF fallback. Partial config causes silent zero-output runs."
            )

    def is_llm_configured(self) -> bool:
        """Return True if all required Azure OpenAI credentials are set [BLK-173]."""
        return bool(self.azure_api_key.strip() and self.azure_chat_endpoint.strip())


# Module-level singleton — import as `from src.config import settings`.
settings = Settings()

# BLK-173: Validate provider config at startup — fail fast on partial credentials
settings.validate_provider_config()

# BLK-153: Warn when auth is disabled
if not settings.auth_enabled:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "ADE_AUTH_ENABLED is false — all endpoints are unauthenticated. "
        "This is NOT recommended for production. Set ADE_AUTH_ENABLED=true."
    )

# SCRUM-63: Warn when rate limiting is disabled
if not settings.rate_limit_enabled:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "ADE_RATE_LIMIT_ENABLED is false — rate limiting is inactive. "
        "This is NOT recommended for production. Set ADE_RATE_LIMIT_ENABLED=true."
    )
