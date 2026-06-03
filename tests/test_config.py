import pytest

from arctic_analytics.config import (
    get_config_value,
    get_openai_api_key,
    has_openai_api_key,
    load_runtime_config,
    save_openai_api_key_to_env,
)


class BrokenSecrets:
    def get(self, key):
        raise FileNotFoundError("missing Streamlit secrets")


def test_config_prefers_environment_values():
    assert (
        get_config_value(
            "OPENAI_API_KEY",
            secrets={"OPENAI_API_KEY": "from-secrets"},
            environ={"OPENAI_API_KEY": "from-env"},
            env_path="missing.env",
        )
        == "from-env"
    )


def test_config_falls_back_to_streamlit_secrets():
    assert (
        get_config_value(
            "OPENAI_API_KEY",
            secrets={"OPENAI_API_KEY": "from-secrets"},
            environ={},
            env_path="missing.env",
        )
        == "from-secrets"
    )


def test_config_handles_missing_streamlit_secrets():
    assert get_config_value("OPENAI_API_KEY", secrets=BrokenSecrets(), environ={}, env_path="missing.env", default="") == ""
    assert has_openai_api_key(secrets=BrokenSecrets(), environ={}, env_path="missing.env") is False


def test_config_loads_dotenv_before_environment(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=from-dotenv\n")

    assert load_runtime_config(env_path)["OPENAI_API_KEY"] == "from-dotenv"
    assert (
        get_config_value(
            "OPENAI_API_KEY",
            environ={"OPENAI_API_KEY": "from-env"},
            env_path=env_path,
        )
        == "from-dotenv"
    )


def test_openai_api_key_prefers_session_state():
    assert (
        get_openai_api_key(
            secrets={"OPENAI_API_KEY": "from-secrets"},
            environ={"OPENAI_API_KEY": "from-env"},
            session_state={"OPENAI_API_KEY": "from-session"},
            env_path="missing.env",
        )
        == "from-session"
    )


def test_save_openai_api_key_to_env(tmp_path):
    env_path = tmp_path / ".env"

    saved_path = save_openai_api_key_to_env("sk-test", env_path=env_path)

    assert saved_path == env_path
    config = load_runtime_config(env_path)
    assert config["LLM_PROVIDER"] == "openai"
    assert config["OPENAI_API_KEY"] == "sk-test"


def test_save_openai_api_key_rejects_empty_value(tmp_path):
    with pytest.raises(ValueError):
        save_openai_api_key_to_env(" ", env_path=tmp_path / ".env")
