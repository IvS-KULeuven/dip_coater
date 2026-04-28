import sys

import pytest

from dip_coater import __version__
from dip_coater.app import main


def test_cli_version_prints_package_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dip-coater", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"{__version__}\n"
