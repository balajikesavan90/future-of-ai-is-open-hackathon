from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import regenerate_example_trace as regenerate


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(regenerate, "ROOT", root)
    return root


@pytest.mark.parametrize("target", [".", "..", "../outside", "src", "file", "link", "examples/sample_research_bundle"])
def test_unsafe_bundle_destinations_are_rejected_without_deletion(repo, monkeypatch, target):
    source = repo / "src"
    source.mkdir()
    sentinel = source / "keep.py"
    sentinel.write_text("keep")
    (repo / "file").write_text("keep")
    (repo / "link").symlink_to(source, target_is_directory=True)
    # A redirected examples directory must not make its target eligible for deletion.
    (repo / "examples").symlink_to(source, target_is_directory=True)
    delete = Mock()
    monkeypatch.setattr(regenerate.shutil, "rmtree", delete)

    with pytest.raises(SystemExit):
        regenerate.prepare_bundle_output(repo / target)

    delete.assert_not_called()
    assert sentinel.read_text() == "keep"


@pytest.mark.parametrize("exists", [False, True])
def test_custom_new_or_empty_destination_is_not_deleted(repo, monkeypatch, exists):
    destination = repo / "custom"
    if exists:
        destination.mkdir()
    delete = Mock()
    monkeypatch.setattr(regenerate.shutil, "rmtree", delete)

    assert regenerate.prepare_bundle_output(destination) == destination
    delete.assert_not_called()


def test_only_default_bundle_is_replaced(repo, monkeypatch):
    destination = repo / "examples" / "sample_research_bundle"
    destination.mkdir(parents=True)
    (destination / "old.json").write_text("{}")
    delete = Mock()
    monkeypatch.setattr(regenerate.shutil, "rmtree", delete)

    assert regenerate.prepare_bundle_output(destination) == destination
    delete.assert_called_once_with(destination)


def test_invalid_destination_is_rejected_before_loading_api_key(repo, monkeypatch):
    monkeypatch.setattr(regenerate, "parse_args", lambda: SimpleNamespace(trace_only=False, bundle_output=repo))
    load_key = Mock()
    monkeypatch.setattr(regenerate, "load_openai_api_key", load_key)

    with pytest.raises(SystemExit):
        regenerate.main()

    load_key.assert_not_called()
