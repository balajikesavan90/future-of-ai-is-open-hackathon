import importlib


def test_package_imports():
    assert importlib.import_module("arctic_analytics")
    assert importlib.import_module("arctic_analytics.streamlit_app")
    assert importlib.import_module("arctic_analytics.core.security")
    assert importlib.import_module("arctic_analytics.core.data_import")
    assert importlib.import_module("arctic_analytics.core.system_messages")


def test_new_widget_imports():
    assert importlib.import_module("arctic_analytics.streamlit.widgets.uploaded_data")
    assert importlib.import_module("arctic_analytics.streamlit.widgets.home")
