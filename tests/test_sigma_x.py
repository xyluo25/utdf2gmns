import sys

import utdf2gmns._utdf2gmns as utdf_module
from utdf2gmns import UTDF2GMNS
from utdf2gmns.func_lib.gmns.sigma_x_process_signal_intersection import (
    cvt_utdf_to_signal_intersection,
)


def test_sigma_x_skips_unsupported_platform(tmp_path, monkeypatch, capsys):
    """Do not launch xlwings interactive mode on Linux."""
    utdf_file = tmp_path / "UTDF.csv"
    utdf_file.write_text("[Network]\n", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "xlwings", None)

    assert cvt_utdf_to_signal_intersection(utdf_file) is False
    assert "supported only on Windows and macOS" in capsys.readouterr().out
    assert not (tmp_path / "utdf_to_gmns_signal_ints").exists()


def test_utdf_to_gmns_signal_ints_returns_converter_status(monkeypatch):
    """Expose a skipped or failed Sigma-X conversion to API callers."""
    monkeypatch.setattr(
        utdf_module,
        "cvt_utdf_to_signal_intersection",
        lambda *args, **kwargs: False,
    )
    net = UTDF2GMNS.__new__(UTDF2GMNS)
    net._utdf_filename = "UTDF.csv"
    net._verbose = False
    net.network_int_ids_signalized = ["1"]

    assert net.utdf_to_gmns_signal_ints() is False
