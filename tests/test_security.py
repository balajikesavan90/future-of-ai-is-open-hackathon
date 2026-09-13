import pandas as pd
import pytest

import streamlit as st

from arctic_analytics.core.security import (
    SecurityError,
    execute_with_timeout,
    safely_execute_code,
    validate_code_security,
)
from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility


def test_validate_code_security_rejects_unsafe_import():
    with pytest.raises(SecurityError):
        validate_code_security("import os\nos.getcwd()")


@pytest.mark.parametrize(
    "code",
    [
        "import os as pd\npd.getcwd()",
        "import pandas as os\nos.DataFrame()",
        "import pandas as open\nopen.DataFrame()",
        "from pandas import DataFrame as open\nopen()",
    ],
)
def test_validate_code_security_rejects_misleading_alias_imports(code):
    with pytest.raises(SecurityError):
        validate_code_security(code)


@pytest.mark.parametrize(
    "code",
    [
        "open('/tmp/example.txt').read()",
        "eval('1 + 1')",
        "exec('x = 1')",
        "__import__('os').getcwd()",
        "getattr(1, '__class__')",
        "globals()",
        "locals()",
    ],
)
def test_validate_code_security_rejects_forbidden_builtins(code):
    with pytest.raises(SecurityError):
        validate_code_security(code)


@pytest.mark.parametrize(
    "code",
    [
        "().__class__",
        "int.__mro__",
        "object.__subclasses__()",
        "(lambda: 1).__globals__",
        "(lambda: 1).__code__",
    ],
)
def test_validate_code_security_rejects_attribute_escapes(code):
    with pytest.raises(SecurityError):
        validate_code_security(code)


@pytest.mark.parametrize(
    "code",
    [
        "import socket\nsocket.socket()",
        "import requests\nrequests.get('https://example.com')",
        "import urllib.request\nurllib.request.urlopen('https://example.com')",
    ],
)
def test_validate_code_security_rejects_network_attempts(code):
    with pytest.raises(SecurityError):
        validate_code_security(code)


@pytest.mark.parametrize(
    "code",
    [
        "open('/tmp/example.txt', 'w')",
        "from pathlib import Path\nPath('/tmp/example.txt').read_text()",
        "import shutil\nshutil.rmtree('/tmp/example')",
    ],
)
def test_validate_code_security_rejects_filesystem_attempts(code):
    with pytest.raises(SecurityError):
        validate_code_security(code)


def test_execute_with_timeout_reports_long_running_code():
    with pytest.raises(TimeoutError):
        execute_with_timeout("import time\ntime.sleep(0.1)", {}, None, timeout_sec=0.01)


def test_safely_execute_code_returns_dataframe():
    vetted_files = {
        "sales": {
            "dataframe": pd.DataFrame(
                {
                    "region": ["east", "east", "west"],
                    "revenue": [10, 15, 20],
                }
            )
        }
    }

    code = """
def generate_report():
    return sales.groupby("region")["revenue"].sum().reset_index()
"""
    output, stdout_output, error_message = safely_execute_code(code, vetted_files, "generate_report")

    assert error_message is None
    assert stdout_output == ""
    assert output.to_dict("records") == [
        {"region": "east", "revenue": 25},
        {"region": "west", "revenue": 20},
    ]


def test_tool_execution_preserves_oversized_text_outputs_for_display():
    st.session_state.clear()
    st.session_state["session_id"] = "test-session"
    client = OpenAIResponsesUtility()
    vetted_files = {
        "sales": {
            "dataframe": pd.DataFrame({"value": range(3000)}),
        }
    }
    code = """
def generate_report():
    return sales
"""

    result = client.run_python_code(
        python_code=code,
        reason="exercise output-size guard",
        vetted_files=vetted_files,
        report_function="generate_report",
    )

    assert result.startswith('{"0":')
    assert '"2999":{"value":2999}' in result


@pytest.mark.parametrize(
    "code",
    [
        "sales['value']",
        "{'total': 6}",
        "sales['value'].sum()",
    ],
)
def test_tool_execution_requires_dataframe_results(code):
    st.session_state.clear()
    st.session_state["session_id"] = "test-session"
    client = OpenAIResponsesUtility()
    vetted_files = {"sales": {"dataframe": pd.DataFrame({"value": [1, 2, 3]})}}

    result = client.run_python_code(
        python_code=code,
        reason="verify table-only output contract",
        vetted_files=vetted_files,
        report_function=None,
    )

    assert "must return a pandas DataFrame so it can be rendered as a table" in result
