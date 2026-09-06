import pytest

from arctic_analytics.config import (
    SUPPORTED_OPENAI_MODELS,
    get_config_value,
    get_openai_api_key,
    has_openai_api_key,
    load_runtime_config,
    save_openai_api_key_to_env,
    validate_openai_model,
)


class BrokenSecrets:
    def get(self, key):
        raise FileNotFoundError("missing Streamlit secrets")


@pytest.mark.parametrize("model", SUPPORTED_OPENAI_MODELS)
def test_validate_openai_model_accepts_supported_models(model):
    assert validate_openai_model(model) == model


def test_validate_openai_model_rejects_unsupported_model():
    with pytest.raises(ValueError, match="not supported"):
        validate_openai_model("unknown-model")


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


@pytest.mark.parametrize("selected_source", ["session", "dotenv", "environment", "secrets", None])
def test_openai_api_key_strips_values_and_skips_blank_sources(tmp_path, selected_source):
    sources = ["session", "dotenv", "environment", "secrets"]
    values = {source: " \t " for source in sources}
    if selected_source is not None:
        for source in sources[sources.index(selected_source):]:
            values[source] = f"  key-from-{source}  "
    env_path = tmp_path / ".env"
    env_path.write_text(f'OPENAI_API_KEY="{values["dotenv"]}"\n')
    kwargs = {
        "session_state": {"OPENAI_API_KEY": values["session"]},
        "environ": {"OPENAI_API_KEY": values["environment"]},
        "secrets": {"OPENAI_API_KEY": values["secrets"]},
        "env_path": env_path,
    }

    expected = f"key-from-{selected_source}" if selected_source else None
    assert get_openai_api_key(**kwargs) == expected
    assert has_openai_api_key(**kwargs) is (selected_source is not None)


def test_save_openai_api_key_to_env(tmp_path):
    env_path = tmp_path / ".env"

    saved_path = save_openai_api_key_to_env("sk-test", env_path=env_path)

    assert saved_path == env_path
    config = load_runtime_config(env_path)
    assert config["LLM_PROVIDER"] == "openai"
    assert config["OPENAI_API_KEY"] == "sk-test"


def test_save_openai_api_key_writes_when_chmod_is_unsupported(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"

    def unsupported_chmod(self, mode):
        raise OSError("chmod unsupported")

    monkeypatch.setattr(type(env_path), "chmod", unsupported_chmod)

    saved_path = save_openai_api_key_to_env("sk-test", env_path=env_path)

    assert saved_path == env_path
    assert load_runtime_config(env_path)["OPENAI_API_KEY"] == "sk-test"


def test_save_openai_api_key_refuses_symlink_path(tmp_path):
    target_path = tmp_path / "target.env"
    target_path.write_text("OPENAI_API_KEY=existing\n")
    env_path = tmp_path / ".env"
    try:
        env_path.symlink_to(target_path)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not supported on this filesystem")

    with pytest.raises(RuntimeError, match="Refusing to write API key to symlinked path"):
        save_openai_api_key_to_env("sk-test", env_path=env_path)

    assert target_path.read_text() == "OPENAI_API_KEY=existing\n"


def test_save_openai_api_key_rejects_empty_value(tmp_path):
    with pytest.raises(ValueError):
        save_openai_api_key_to_env(" ", env_path=tmp_path / ".env")
