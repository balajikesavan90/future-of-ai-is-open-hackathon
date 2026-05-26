from arctic_analytics.config import get_config_value, has_openai_api_key


class BrokenSecrets:
    def get(self, key):
        raise FileNotFoundError("missing Streamlit secrets")


def test_config_prefers_environment_values():
    assert (
        get_config_value(
            "OPENAI_API_KEY",
            secrets={"OPENAI_API_KEY": "from-secrets"},
            environ={"OPENAI_API_KEY": "from-env"},
        )
        == "from-env"
    )


def test_config_falls_back_to_streamlit_secrets():
    assert (
        get_config_value(
            "OPENAI_API_KEY",
            secrets={"OPENAI_API_KEY": "from-secrets"},
            environ={},
        )
        == "from-secrets"
    )


def test_config_handles_missing_streamlit_secrets():
    assert get_config_value("OPENAI_API_KEY", secrets=BrokenSecrets(), environ={}, default="") == ""
    assert has_openai_api_key(secrets=BrokenSecrets(), environ={}) is False
