import importlib


def test_get_version_prefers_installed_package_metadata(monkeypatch):
    module = importlib.import_module("dip_coater")

    monkeypatch.setattr(module, "package_version", lambda _: "9.9.9")

    assert module.get_version() == "9.9.9"
