"""Eval configuration from eval_config.yaml and agent.yaml."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Generator
import yaml


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid."""
    pass


# Request-scoped configuration using contextvars (thread-safe)
_request_config: ContextVar[Optional["EvalConfig"]] = ContextVar(
    "request_config", default=None
)


def get_eval_dir() -> Path:
    """Get the eval directory path."""
    return Path(__file__).parent.parent


def get_agent_dir() -> Path:
    """Get the agent root directory (parent of eval)."""
    return get_eval_dir().parent


def _load_agent_yaml() -> dict:
    """Load agent.yaml configuration."""
    agent_yaml = get_agent_dir() / "agent.yaml"
    if agent_yaml.exists():
        return yaml.safe_load(agent_yaml.read_text()) or {}
    return {}


@dataclass
class EvalConfig:
    """Eval framework configuration."""

    type: str = "single"  # "single" or "multi"
    default_agent: str = "main"
    agent_ids: list[str] = field(default_factory=lambda: ["main"])
    imports: dict = field(default_factory=dict)
    versions: dict = field(default_factory=dict)
    active_version: Optional[str] = None  # Production active version from agent.yaml

    # LLM defaults from agent.yaml llm section
    default_model: Optional[str] = None
    default_temperature: Optional[float] = None

    def __post_init__(self):
        """Apply default imports if not specified."""
        default_imports = {
            "userdata_module": "shared_state",
            "userdata_class": "UserData",
            "test_data_factory": "shared_state:create_test_userdata",
            "agent_classes_module": "sub_agents",
            "agent_classes_var": "AGENT_CLASSES",
            "tools_module": "tools",
            "tools_function": "get_tools_by_names",
        }
        self.imports = {**default_imports, **self.imports}

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "EvalConfig":
        """Load config from eval_config.yaml and versions from agent.yaml."""
        if path is None:
            path = get_eval_dir() / "eval_config.yaml"

        if not path.exists():
            return cls()

        data = yaml.safe_load(path.read_text()) or {}

        # Load versions from agent.yaml (single source of truth)
        agent_config = _load_agent_yaml()
        versions = agent_config.get("versions", {})
        active_version = agent_config.get("active_version")

        # Load LLM config from agent.yaml (single source of truth)
        llm_config = agent_config.get("llm", {})
        default_model = llm_config.get("model")  # No fallback - will be None if not set
        default_temperature = llm_config.get("temperature")  # No fallback

        return cls(
            type=data.get("type", "single"),
            default_agent=data.get("default_agent", "main"),
            agent_ids=data.get("agent_ids", ["main"]),
            imports=data.get("imports", {}),
            versions=versions,
            active_version=active_version,
            default_model=default_model,
            default_temperature=default_temperature,
        )

    def is_multi_agent(self) -> bool:
        """Check if this is a multi-agent configuration."""
        return self.type == "multi"

    def get_import(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an import configuration value."""
        return self.imports.get(key, default)

    def get_version_config(self, version_name: str) -> Optional[dict]:
        """Get configuration for a specific version."""
        return self.versions.get(version_name)

    def get_all_version_names(self) -> list[str]:
        """Get all defined version names."""
        return list(self.versions.keys())

    def get_version_model(self, version_name: str) -> Optional[str]:
        """Get model override for a version, if any."""
        version = self.versions.get(version_name)
        return version.get("model") if version else None

    def get_version_prompt_version(self, version_name: str, agent_id: str) -> Optional[str]:
        """Get prompt_version override for a specific agent in a version."""
        version = self.versions.get(version_name)
        if not version:
            return None
        sub_agents = version.get("sub_agents", {})
        agent_cfg = sub_agents.get(agent_id, {})
        return agent_cfg.get("prompt_version")

    def get_active_version(self) -> Optional[str]:
        """Get the active version for production use."""
        return self.active_version

    def get_effective_version(self, override: Optional[str] = None) -> Optional[str]:
        """Get effective version: CLI override > active_version > None."""
        return override or self.active_version

    def resolve_model(
        self,
        cli_override: Optional[str] = None,
        version: Optional[str] = None,
    ) -> str:
        """Resolve model with priority: CLI > version > agent.yaml llm.model.

        Raises ConfigurationError if no model is configured anywhere.
        """
        # CLI override has highest priority
        if cli_override is not None:
            return cli_override

        # Version override
        if version:
            version_model = self.get_version_model(version)
            if version_model is not None:
                return version_model

        # Agent.yaml default
        if self.default_model is not None:
            return self.default_model

        raise ConfigurationError(
            "No model configured. Set llm.model in agent.yaml or pass --model flag."
        )

    def resolve_temperature(
        self,
        cli_override: Optional[float] = None,
        version: Optional[str] = None,
    ) -> float:
        """Resolve temperature with priority: CLI > version > agent.yaml llm.temperature.

        Raises ConfigurationError if no temperature is configured anywhere.
        """
        # CLI override has highest priority
        if cli_override is not None:
            return cli_override

        # Version override
        if version:
            version_cfg = self.get_version_config(version)
            if version_cfg and "temperature" in version_cfg:
                return version_cfg["temperature"]

        # Agent.yaml default
        if self.default_temperature is not None:
            return self.default_temperature

        raise ConfigurationError(
            "No temperature configured. Set llm.temperature in agent.yaml or pass --temperature flag."
        )

    def validate_version(self, version: str) -> dict:
        """Validate that a version exists and return its config.

        Raises ConfigurationError if version not found.
        """
        version_cfg = self.get_version_config(version)
        if version_cfg is None:
            available = ", ".join(self.get_all_version_names()) or "(none)"
            raise ConfigurationError(
                f"Version '{version}' not found in agent.yaml. Available versions: {available}"
            )
        return version_cfg

    def get_all_sub_agents(self) -> list[dict]:
        """Get all sub_agents from agent.yaml."""
        agent_config = _load_agent_yaml()
        return agent_config.get("sub_agents", [])


# Singleton cache for config (global fallback)
_config_cache: Optional[EvalConfig] = None


@contextmanager
def request_scope(config: Optional[EvalConfig] = None) -> Generator[EvalConfig, None, None]:
    """Context manager for request-scoped configuration.

    Creates an isolated config scope for a single test execution.
    This avoids the need to clear global caches between tests.

    Args:
        config: Optional pre-loaded config. If None, loads fresh config.

    Yields:
        The scoped EvalConfig instance.

    Example:
        with request_scope() as config:
            # All get_config() calls within this block return this config
            runner = EvalRunner(...)
            result = runner.run_eval(test_case)
    """
    if config is None:
        config = EvalConfig.load()

    token = _request_config.set(config)
    try:
        yield config
    finally:
        _request_config.reset(token)


def get_config(reload: bool = False) -> EvalConfig:
    """Get eval configuration.

    Resolution order:
    1. Request-scoped config (if within request_scope context)
    2. Global cached config (singleton)

    Args:
        reload: Force reload from disk (only affects global cache)
    """
    # Check request-scoped config first (thread-safe via contextvars)
    request_cfg = _request_config.get()
    if request_cfg is not None:
        return request_cfg

    # Fall back to global cache
    global _config_cache
    if _config_cache is None or reload:
        _config_cache = EvalConfig.load()

    return _config_cache


def clear_config_cache() -> None:
    """Clear the global config cache.

    Note: This only clears the global cache, not request-scoped configs.
    Prefer using request_scope() for test isolation instead of clearing caches.
    """
    global _config_cache
    _config_cache = None
