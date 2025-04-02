'''
##############################################################
# Created Date: Thursday, February 20th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
import os
from pathlib import Path
from typing import TYPE_CHECKING
import shutil

import pyufunc as pf

if TYPE_CHECKING:
    import xlwings as xw


@pf.requires("xlwings", verbose=False)
def cvt_utdf_to_signal_intersection(utdf_filename: str, *, output_dir: str = "", verbose: bool = False) -> bool:
    """Utilize sigma-X engine to process each signal intersection from Synchro UTDF file
    And save each signal intersection into a separate GMNS file.

    Args:
        utdf_filename (str): the path of Synchro UTDF file
        output_dir (str): the path of output directory. Defaults to "".
            If not specified, the output directory will be the same as the input directory.

    Example:
        >>> import utdf2gmns as ug
        >>> utdf_filename = "your utdf file, in csv format"
        >>> ug.cvt_utdf_to_signal_intersection(utdf_filename, output_dir="")

    Location:
        utdf2gmns/func_lib/gmns/sigma_X_process_each_signal_intersection.cvt_utdf_to_signal_intersection

    Raises:
        TypeError: If the input file is not a string or Path
        FileNotFoundError: If the input file does not exist

    Returns:
        bool: True if success, False otherwise
    """
    pf.import_package("xlwings", verbose=False)  # ensure xlwings is imported
    import xlwings as xw  # ensure xlwings is imported

    # TDD Test-Driven Development
    if not isinstance(utdf_filename, (str, Path)):
        raise TypeError(f"  :utdf_filename should be str or Path, but got {type(utdf_filename)}")

    # Step1 cvt path to universal path to enable cross-platform
    utdf_filename = pf.path2linux(Path(utdf_filename).absolute())
    if not os.path.exists(utdf_filename):
        raise FileNotFoundError(f"  :{utdf_filename} does not exist")
    input_utdf_dir = pf.path2linux(Path(utdf_filename).parent)

    # Step2 crate output directory to store the results
    output_dir = pf.path2linux(Path(input_utdf_dir) / "utdf_to_gmns_signal_ints")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Step3 Copy sigma-X engine to result directory
    dir_sigma_x = pf.path2uniform(Path(__file__).parent.parent.parent / "engine" / "sigma_x")
    if not os.path.exists(dir_sigma_x):
        raise FileNotFoundError(f"  :{dir_sigma_x} does not exist")
    path_sigma_x_utdf2gmns = pf.path2uniform(Path(dir_sigma_x) / "UTDF2GMNS.xlsm")
    path_sigma_x_utdf_control = pf.path2uniform(Path(dir_sigma_x) / "Sigma-X_UTDF.xlsm")
    shutil.copy(path_sigma_x_utdf2gmns, output_dir)
    shutil.copy(path_sigma_x_utdf_control, output_dir)

    # Step4 copy input UTDF file to output directory
    output_utdf = pf.path2linux(Path(output_dir) / "UTDF8.csv")
    shutil.copy(utdf_filename, output_utdf)

    # Step5 Run the sigma-X engine
    output_sigma_utdf2gmns = pf.path2linux(Path(output_dir) / "UTDF2GMNS.xlsm")
    output_sigma = pf.path2linux(Path(output_dir) / "Sigma-X_UTDF.xlsm")

    # Close all existing open Excel instances
    for app in xw.apps:
        app.quit()

    try:
        print("  :Running Sigma-X engine to generate each signal intersection...")
        with xw.App(visible=False) as app:
            wb = app.books.open(output_sigma_utdf2gmns)
            # run the macro
            wb.macro("UTDF2GMNS")()
    except Exception as e:
        if verbose:
            print(f"  :Failed to run the macro: {e}")

    # Close all existing open Excel instances
    os.remove(output_sigma_utdf2gmns)
    os.remove(output_utdf)
    os.remove(output_sigma)

    # Step6 delete the sigma-X engine from output directory
    print("  :Successfully processed each signal intersection from Synchro UTDF file")
    print(f"  :Please check the output directory: {output_dir}")
