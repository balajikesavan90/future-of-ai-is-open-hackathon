import pandas as pd
import pytest

from arctic_analytics.core.security import SecurityError, safely_execute_code, validate_code_security


def test_validate_code_security_rejects_unsafe_import():
    with pytest.raises(SecurityError):
        validate_code_security("import os\nos.getcwd()")


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
