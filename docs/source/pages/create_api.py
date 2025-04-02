'''
##############################################################
# Created Date: Monday, March 24th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from __future__ import absolute_import
from pathlib import Path
import sys
import os

root = Path(__file__).resolve().parents[3]
sys.path = [str(root)] + sys.path

import utdf2gmns
import utdf2gmns.func_lib
import utdf2gmns.util_lib
from utdf2gmns import UTDF2GMNS

collected_functions = {
    "utdf2gmns": ["UTDF2GMNS"],
    "utdf2gmns.util_lib": utdf2gmns.util_lib.__all__,
    "utdf2gmns.func_lib": utdf2gmns.func_lib.__all__,
}


# remove all documents in the api folder
api_folder = "api"
for file in os.listdir(api_folder):
    if file.endswith(".rst"):
        os.remove(os.path.join(api_folder, file))

# Create the API documentation
total_functions = sum(len(module_list) for module_list in collected_functions.values())
for relative_path, module_list in collected_functions.items():

    # SKIP the UTDF2GMNS class (manually created)
    if relative_path == "utdf2gmns":
        continue

    if not module_list:
        continue

    for module in module_list:
        file_name = f"api/{relative_path}.{module}.rst"

        heading_message = f"{relative_path}.{module}"

        with open(file_name, "w", encoding="utf-8") as f:

            heading_message_new = heading_message.replace("_", "\\_")
            heading_dashes = "=" * len(heading_message_new)

            f.write(heading_message_new + "\n")
            f.write(heading_dashes + "\n\n")

            f.write(f".. automodule:: {relative_path}\n")
            f.write("   :members:\n")
            f.write("   :undoc-members:\n")
            f.write("   :show-inheritance:\n\n")
            f.write(f".. autofunction:: {module}" + "\n\n")
            f.write(f".. autoclass:: {module}" + "\n\n")

            f.close()

print(f"Successfully updated {total_functions} API documentations!")
