import importlib


def test_package_imports():
    assert importlib.import_module("arctic_analytics")
    assert importlib.import_module("arctic_analytics.streamlit_app")
    assert importlib.import_module("arctic_analytics.core.security")
    assert importlib.import_module("arctic_analytics.core.data_import")
    assert importlib.import_module("arctic_analytics.core.system_messages")


def test_compatibility_imports():
    assert importlib.import_module("utils.security_helpers")
    assert importlib.import_module("utils.data_import_helpers")
    assert importlib.import_module("utils.system_messages")
    assert importlib.import_module("widgets.uploaded_data")
    assert importlib.import_module("widgets.home")


def test_new_widget_imports():
    assert importlib.import_module("arctic_analytics.streamlit.widgets.uploaded_data")
    assert importlib.import_module("arctic_analytics.streamlit.widgets.home")

