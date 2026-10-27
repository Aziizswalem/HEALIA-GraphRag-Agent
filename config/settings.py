"""Central Pydantic settings — load from environment and optional `.env`."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    DEMO_MODE: bool = False

    # Neo4j
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_USER: str = ""
    NEO4J_PASSWORD: str = ""

    # Remote MCP Neo4j server
    MCP_ENABLED: bool = False
    MCP_URL: str = ""
    MCP_AUTHORIZATION: str = ""
    MCP_TIMEOUT_SECONDS: float = 15.0

    # LLM
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT_SECONDS: float = 60.0
    OPENAI_MAX_RETRIES: int = 2
    EVAL_JUDGE_MODE: str = "off"
    EVAL_JUDGE_PROVIDER: str = ""
    EVAL_JUDGE_MODEL: str = ""
    EVAL_JUDGE_API_KEY: str = ""
    EVAL_JUDGE_BASE_URL: str = ""
    EVAL_JUDGE_TIMEOUT_SECONDS: float = 60.0
    EVAL_INPUT_PRICE_PER_1M_TOKENS: float = 0.0
    EVAL_OUTPUT_PRICE_PER_1M_TOKENS: float = 0.0

    # Schema cache (in-memory TTL)
    SCHEMA_CACHE_TTL_SECONDS: int = 1800
    SCHEMA_VERSION: str = "v1"
    SCHEMA_CACHE_PREFIX: str = "graphrag:schema"
    # From apoc.meta.schema: drop property keys with existence < this (0 keeps all non-zero).
    SCHEMA_PROPERTY_MIN_EXISTENCE: float = 0.0
    SCHEMA_MAX_PROPERTIES_PER_ENTITY: int = 64
    SCHEMA_MAX_PROPERTIES_IN_PATTERN: int = 20
    # JSON: {"ActeMedical": ["type"], "Patient": ["chronic_disease"]} — distinct values sampled from DB for Cypher literals
    SCHEMA_ENUM_HINTS: str = ""
    SCHEMA_ENUM_VALUE_LIMIT: int = 200

    # API / auth (placeholders)
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    DATABASE_URL: str = ""
    AUDIT_LOG_PATH: str = "logs/audit_log.jsonl"
    AUDIT_LOG_ENABLED: bool = True
    OBSERVABILITY_LOG_PATH: str = "logs/observability.jsonl"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_TRACING_ENABLED: bool = True
    API_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CAPACITY: int = 60
    RATE_LIMIT_REFILL_TOKENS_PER_SECOND: float = 1.0
    RATE_LIMIT_PREFIX: str = "graphrag:ratelimit"

    # PII filtering
    PII_FILTER_ENABLED: bool = True

    # Conversation memory (PostgreSQL via SQLAlchemy)
    CONVERSATION_MEMORY_ENABLED: bool = True
    CONVERSATION_MAX_TURNS: int = 200
    CONVERSATION_CONTEXT_TURNS: int = 20
    CONTEXT_TOKEN_BUDGET: int = 4000
    MAX_HISTORY_TURNS: int = 20

    # Session cookie
    SESSION_TTL_SECONDS: int = 86400
    SESSION_COOKIE_NAME: str = "stagee_session_id"

    # Result sanitization
    # (Removed: project returns raw DB values)

    def neo4j_auth_user(self) -> str:
        return self.NEO4J_USER or self.NEO4J_USERNAME

    def mcp_enabled(self) -> bool:
        return self.MCP_ENABLED and bool(self.MCP_URL.strip())

    def graph_access_configured(self) -> bool:
        return self.mcp_enabled() or bool(self.neo4j_auth_user())

    def langfuse_base_url(self) -> str:
        return self.LANGFUSE_BASE_URL or self.LANGFUSE_HOST or "https://cloud.langfuse.com"

    def api_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.API_CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator(
        "OPENAI_TIMEOUT_SECONDS",
        "OPENAI_MAX_RETRIES",
        "EVAL_JUDGE_TIMEOUT_SECONDS",
        "EVAL_INPUT_PRICE_PER_1M_TOKENS",
        "EVAL_OUTPUT_PRICE_PER_1M_TOKENS",
        mode="before",
    )
    @classmethod
    def _use_field_default_for_empty_numeric_env(cls, value, info):
        if value in {"", None}:
            return cls.model_fields[info.field_name].default
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
