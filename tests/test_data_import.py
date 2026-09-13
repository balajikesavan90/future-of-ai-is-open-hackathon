import io
from types import SimpleNamespace

import pandas as pd
import pytest

from arctic_analytics.core import data_import
from arctic_analytics.core.data_import import (
    check_datatypes,
    build_vetted_files_from_uploads,
    dataframe_name_from_filename,
    gather_metadata,
    unique_dataframe_name,
)
from arctic_analytics.streamlit.widgets.uploader import is_valid_csv, sanitize_filename


class Upload(io.BytesIO):
    def __init__(self, content, name="sample.csv"):
        super().__init__(content)
        self.name = name
        self.size = len(content)


def test_sanitize_filename_strips_paths():
    assert sanitize_filename("../../sales.csv") == "sales.csv"


def test_dataframe_name_from_filename_normalizes_for_python():
    assert dataframe_name_from_filename("15) 16 Oct -VS DYN.csv") == "df_15_16_oct_vs_dyn"
    assert dataframe_name_from_filename("Sales Report 2026.csv") == "sales_report_2026"


def test_dataframe_name_from_filename_handles_python_keywords():
    assert dataframe_name_from_filename("class.csv") == "df_class"


@pytest.mark.parametrize("filename", ["pd.csv", "st.csv", "get_dataframe_names.csv"])
def test_dataframe_name_from_filename_avoids_reserved_execution_globals(filename):
    assert dataframe_name_from_filename(filename).startswith("df_")


def test_unique_dataframe_name_adds_numeric_suffix_for_collisions():
    existing_names = {"sales_2026", "sales_2026_2"}

    assert unique_dataframe_name("sales_2026", existing_names) == "sales_2026_3"


def test_gather_metadata_sets_description_and_preserves_colliding_uploads(monkeypatch):
    uploads = [
        Upload(b"value\n1\n", name="Sales 2026.csv"),
        Upload(b"value\n2\n", name="sales-2026.csv"),
    ]
    session_state = {
        "session_id": "test-session",
        "source": "uploader",
        "uploaded_files": uploads,
    }
    monkeypatch.setattr(data_import, "st", SimpleNamespace(session_state=session_state))

    gather_metadata()

    vetted_files = session_state["vetted_files"]
    assert list(vetted_files) == ["sales_2026", "sales_2026_2"]
    assert vetted_files["sales_2026"]["dataset_description"] == ""
    assert vetted_files["sales_2026_2"]["dataframe"]["value"].iloc[0] == 2


def test_build_vetted_files_from_uploads_strips_path_from_source_filename():
    vetted_files = build_vetted_files_from_uploads([Upload(b"value\n1\n", name="../../sales.csv")])

    assert list(vetted_files) == ["sales"]
    assert vetted_files["sales"]["source_filename"] == "sales.csv"


def test_check_datatypes_uses_column_name_index_from_data_editor(monkeypatch):
    session_state = {"session_id": "test-session"}
    monkeypatch.setattr(data_import, "st", SimpleNamespace(session_state=session_state))
    data_dictionary = pd.DataFrame(
        {
            "Primary Key": [False],
            "Column Name": ["name"],
            "Data Type": ["object"],
            "Description": ["Customer name"],
        }
    ).set_index("Column Name", drop=False)
    vetted_files = {
        "customers": {
            "data_dictionary": data_dictionary,
            "dataframe": pd.DataFrame({"name": ["Ada"]}),
        }
    }

    result = check_datatypes(vetted_files)

    assert result["customers"]["data_dictionary"].index.tolist() == ["name"]
    assert str(result["customers"]["dataframe"]["name"].dtype) == "string"


@pytest.mark.parametrize(
    ("selected_dtype", "values", "expected_dtype"),
    [
        ("Int64", ["1", "2"], "Int64"),
        ("Float64", ["1.5", "2.5"], "Float64"),
        ("string", [1, 2], "string"),
    ],
)
def test_check_datatypes_applies_data_editor_dtype_labels(
    monkeypatch, selected_dtype, values, expected_dtype
):
    session_state = {"session_id": "test-session"}
    monkeypatch.setattr(data_import, "st", SimpleNamespace(session_state=session_state))
    data_dictionary = pd.DataFrame(
        {
            "Primary Key": [False],
            "Column Name": ["value"],
            "Data Type": [selected_dtype],
            "Description": ["A value"],
        }
    ).set_index("Column Name", drop=False)
    vetted_files = {
        "values": {
            "data_dictionary": data_dictionary,
            "dataframe": pd.DataFrame({"value": values}),
        }
    }

    result = check_datatypes(vetted_files)

    assert str(result["values"]["dataframe"]["value"].dtype) == expected_dtype


def test_is_valid_csv_accepts_plain_csv():
    valid, error = is_valid_csv(Upload(b"a,b\n1,2\n"))

    assert valid is True
    assert error == ""


def test_is_valid_csv_accepts_blank_cells_in_text_columns():
    valid, error = is_valid_csv(Upload(b"station,weather_code\n01001099999,\n"))

    assert valid is True
    assert error == ""


def test_is_valid_csv_rejects_suspicious_content():
    valid, error = is_valid_csv(Upload(b"name,formula\nx,=cmd|calc\n"))

    assert valid is False
    assert "Suspicious content" in error
