from types import SimpleNamespace

from dip_coater.app import toggled_textual_theme


def test_toggled_textual_theme_uses_current_theme_dark_flag():
    assert toggled_textual_theme(SimpleNamespace(dark=True)) == "textual-light"
    assert toggled_textual_theme(SimpleNamespace(dark=False)) == "textual-dark"
