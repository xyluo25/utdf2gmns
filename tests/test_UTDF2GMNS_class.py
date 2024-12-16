'''
##############################################################
# Created Date: Sunday, December 15th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
from __future__ import absolute_import

import pytest
from pathlib import Path

try:
    from utdf2gmns._utdf2gmns import UTDF2GMNS
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utdf2gmns._utdf2gmns import UTDF2GMNS


# TODO test the UTDF2GMNS class
class TestUTDF2GMNSClass:
    """Test the UTDF2GMNS class including raises, warnings, and exceptions."""

    def setup_class(self):
        # define the test data directory
        self.dir_datasets = Path(__file__).resolve().parents[1] / "datasets"

    def test_invalid_utdf_file(self):
        with pytest.raises(Exception) as exc_info:
            net = UTDF2GMNS(utdf_filename="invalid_utdf_file.utdf")
        assert str(exc_info.value) == "UTDF file invalid_utdf_file.utdf not found!"

    def test_valid_utdf_file(self):

        net = UTDF2GMNS(utdf_filename=self.dir_datasets / "data_Tempe_network" / "UTDF.csv")
        assert net is not None