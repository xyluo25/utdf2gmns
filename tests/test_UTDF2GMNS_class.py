'''
##############################################################
# Created Date: Sunday, December 15th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
from __future__ import absolute_import

import subprocess

import pytest
from pathlib import Path

try:
    import utdf2gmns._utdf2gmns as utdf_module
    from utdf2gmns import UTDF2GMNS
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    import utdf2gmns._utdf2gmns as utdf_module
    from utdf2gmns import UTDF2GMNS


# TODO test the UTDF2GMNS class
class TestUTDF2GMNS:
    """Test the UTDF2GMNS class including raises, warnings, and exceptions."""

    def setup_class(self):
        # define the test data directory
        self.dir_datasets = Path(__file__).resolve().parents[1] / "datasets"

    def test_invalid_utdf_file(self):
        with pytest.raises(Exception) as exc_info:
            net = UTDF2GMNS(utdf_filename="invalid_utdf_file.utdf")
        assert "invalid_utdf_file.utdf not found!" in str(exc_info.value)

    def test_valid_utdf_file(self):

        net = UTDF2GMNS(utdf_filename=self.dir_datasets / "data_Tempe_network" / "UTDF.csv")
        assert net is not None

    def test_utdf_to_sumo_can_skip_loop_detectors(self, tmp_path, monkeypatch):
        """remove_loop_detectors should skip detector files and config references."""
        net = UTDF2GMNS.__new__(UTDF2GMNS)
        net._utdf_filename = str(tmp_path / "UTDF.csv")
        net._utdf_dict = {}
        net._verbose = False
        net.network_nodes = {"1": {"x_coord": 0.0, "y_coord": 0.0}}
        net.network_links = {}
        net.network_settings = {}
        net.network_unit = "feet, mph"

        detector_call_count = {"count": 0}

        def count_detector_generation(*args, **kwargs):
            detector_call_count["count"] += 1
            return True

        completed_process = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        monkeypatch.setattr(utdf_module, "generate_sumo_nod_xml", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module, "generate_sumo_edg_xml", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module, "generate_sumo_connection_xml", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module, "generate_sumo_loop_detector_add_xml", count_detector_generation)
        monkeypatch.setattr(utdf_module, "update_sumo_signal_from_utdf", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module, "generate_sumo_flow_xml", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module, "remove_sumo_U_turn", lambda *args, **kwargs: True)
        monkeypatch.setattr(utdf_module.shutil, "which", lambda executable_name: executable_name)
        monkeypatch.setattr(utdf_module.subprocess, "run", lambda *args, **kwargs: completed_process)

        output_dir = tmp_path / "sumo"
        assert net.utdf_to_sumo(
            output_dir=str(output_dir),
            sim_name="skip_detectors",
            remove_U_turn=False,
            remove_loop_detectors=True,
            flow_mode="intersection",
        )

        sumo_cfg = output_dir / "skip_detectors.sumocfg"
        assert detector_call_count["count"] == 0
        assert "<additional-files" not in sumo_cfg.read_text()
