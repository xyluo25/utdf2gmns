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
REPO_ROOT = Path(__file__).resolve().parents[1]


def import_sumo2geojson(monkeypatch):
    """Import sumo2geojson with a stub sumolib module."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.append(str(REPO_ROOT))

    stub = types.ModuleType("sumolib")
    monkeypatch.setitem(sys.modules, "sumolib", stub)

    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]

    module = importlib.import_module(MODULE_PATH)
    return module


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
