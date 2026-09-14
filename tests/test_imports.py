import importlib


def test_package_imports():
    assert importlib.import_module("python_data_analysis_agent")
    assert importlib.import_module("python_data_analysis_agent.streamlit_app")
    assert importlib.import_module("python_data_analysis_agent.core.security")
    assert importlib.import_module("python_data_analysis_agent.core.data_import")
    assert importlib.import_module("python_data_analysis_agent.core.system_messages")


def test_new_widget_imports():
    assert importlib.import_module("python_data_analysis_agent.streamlit.widgets.uploaded_data")
    assert importlib.import_module("python_data_analysis_agent.streamlit.widgets.home")
