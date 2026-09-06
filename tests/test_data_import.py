import io

from arctic_analytics.core.data_import import dataframe_name_from_filename
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


def test_is_valid_csv_accepts_plain_csv():
    valid, error = is_valid_csv(Upload(b"a,b\n1,2\n"))

    assert valid is True
    assert error == ""


def test_is_valid_csv_rejects_suspicious_content():
    valid, error = is_valid_csv(Upload(b"name,formula\nx,=cmd|calc\n"))

    assert valid is False
    assert "Suspicious content" in error
