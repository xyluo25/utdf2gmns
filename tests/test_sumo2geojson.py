# -*- coding:utf-8 -*-
##############################################################
# Created Date: Monday, February 3rd 2026
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
from __future__ import absolute_import

import importlib
import sys
import types
from pathlib import Path

import pytest


MODULE_PATH = "utdf2gmns.func_lib.sumo_geojson.sumo2geojson"


def import_sumo2geojson(monkeypatch):
    """Import sumo2geojson with a stub sumolib module."""
    stub = types.ModuleType("sumolib")
    monkeypatch.setitem(sys.modules, "sumolib", stub)

    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]

    module = importlib.import_module(MODULE_PATH)
    return module


def test_sumo2geojson_builds_command_and_calls_subprocess(monkeypatch, tmp_path):
    module = import_sumo2geojson(monkeypatch)

    net_file = tmp_path / "sample.net.xml"
    net_file.write_text("<net></net>")
    output_file = tmp_path / "out"

    captured = {}

    def fake_run(cmd, shell, check):
        captured["cmd"] = cmd
        captured["shell"] = shell
        captured["check"] = check
        return "EXECUTED"

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.sumo2geojson(
        str(net_file),
        str(output_file),
        lanes=True,
        junctions=True,
        internal=True,
        junction_coords=True,
        boundary=True,
        edge_data_timeline=True,
        edge_data="edge.xml",
        pt_lines="pt.xml",
    )

    assert result == "EXECUTED"
    assert captured["shell"] is True
    assert captured["check"] is True
    assert "net2geojson.py" in captured["cmd"]
    assert str(net_file) in captured["cmd"]
    assert str(output_file) + ".geojson" in captured["cmd"]
    assert " -l" in captured["cmd"]
    assert " --junctions" in captured["cmd"]
    assert " -i" in captured["cmd"]
    assert " -j" in captured["cmd"]
    assert " -b" in captured["cmd"]
    assert " --edgedata-timeline" in captured["cmd"]
    assert " -d \"edge.xml\"" in captured["cmd"]
    assert " -p \"pt.xml\"" in captured["cmd"]


def test_sumo2geojson_invalid_net_path_type(monkeypatch):
    module = import_sumo2geojson(monkeypatch)

    with pytest.raises(TypeError):
        module.sumo2geojson(123, "out.geojson")


def test_sumo2geojson_invalid_output_path_type(monkeypatch, tmp_path):
    module = import_sumo2geojson(monkeypatch)

    net_file = tmp_path / "sample.net.xml"
    net_file.write_text("<net></net>")

    with pytest.raises(TypeError):
        module.sumo2geojson(str(net_file), 456)


def test_sumo2geojson_missing_net_file(monkeypatch, tmp_path):
    module = import_sumo2geojson(monkeypatch)

    net_file = tmp_path / "missing.net.xml"

    with pytest.raises(FileNotFoundError):
        module.sumo2geojson(str(net_file), "out.geojson")


def test_sumo2geojson_invalid_extension(monkeypatch, tmp_path):
    module = import_sumo2geojson(monkeypatch)

    net_file = tmp_path / "bad.xml"
    net_file.write_text("<net></net>")

    with pytest.raises(ValueError):
        module.sumo2geojson(str(net_file), "out.geojson")
