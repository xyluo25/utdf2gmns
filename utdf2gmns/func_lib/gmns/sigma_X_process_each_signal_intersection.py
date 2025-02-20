'''
##############################################################
# Created Date: Thursday, February 20th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
import os
from pathlib import Path
import shutil
import xlwings as xw
import pyufunc as pf


def utdf_to_each_signal_intersection(utdf_filename: str, *, output_dir: str = "") -> bool:
    """Utilize sigma-X engine to process each signal intersection from Synchro UTDF file
    And save each signal intersection into a separate GMNS file.

    Args:
        utdf_filename (str): the path of Synchro UTDF file
        output_dir (str): the path of output directory. Defaults to "".
            If not specified, the output directory will be the same as the input directory.

    Returns:
        bool: True if success, False otherwise
    """

    # TDD Test-Driven Development
    if not isinstance(utdf_filename, (str, Path)):
        raise TypeError(f"  :utdf_filename should be str or Path, but got {type(utdf_filename)}")

    # Step1 cvt path to universal path to enable cross-platform
    utdf_filename = pf.path2linux(Path(utdf_filename).absolute())
    if not os.path.exists(utdf_filename):
        raise FileNotFoundError(f"  :{utdf_filename} does not exist")
    input_utdf_dir = pf.path2linux(Path(utdf_filename).parent)

    # Step2 crate output directory to store the results
    output_dir = pf.path2linux(Path(input_utdf_dir) / "utdf2gmns_signal_ints")
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
    with xw.App(visible=False) as app:
        try:
            wb = app.books.open(output_sigma_utdf2gmns)
            # run the macro
            wb.macro("UTDF2GMNS")()

            # save and close the workbook
            wb.save()
            wb.close()
            app.quit()
        except Exception as e:
            app.quit()
            print(f"  :Error occurred while running the macro: {e}")
    # Step6 delete the sigma-X engine from output directory
    shutil.rmtree(output_sigma_utdf2gmns)
    shutil.rmtree(output_utdf)
    print("  :Successfully processed each signal intersection from Synchro UTDF file")
    print(f"  :Please check the output directory: {output_dir}")

if __name__ == '__main__':
    path_utdf = r"C:\Users\xh8\Desktop\data_bullhead_seg4\my_utdf.csv"
    utdf_to_each_signal_intersection(path_utdf)
