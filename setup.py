# -*- coding:utf-8 -*-
##############################################################
# Created Date: Monday, December 28th 2020
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################


import setuptools
import utdf2gmns as ug

with open("Readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    # if have requirements.txt file inside the folder
    with open("requirements.txt", "r", encoding="utf-8") as f:
        modules_needed = [i.strip() for i in f.readlines()]
except Exception:
    modules_needed = []

setuptools.setup(
    name=ug.pkg_name,
    version=ug.pkg_version,
    author=ug.pkg_author,
    author_email=ug.pkg_email,
    description="This open-source package is a tool to convert utdf file to GMNS format.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/asu-trans-ai-lab/utdf2gmns",

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    install_requires=modules_needed,

    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={'': ['*.txt', '*.xls', '*.xlsx', '*.csv'],
                  "test_data": ['*.xls']},
    project_urls={
        'Homepage': 'https://github.com/xyluo25/utdf2gmns',
        'Documentation': 'https://utdf2gmns.readthedocs.io/en/latest/',
        'Bug Tracker': 'https://github.com/asu-trans-ai-lab/utdf2gmns/issues',
        # 'Source Code': '',
        # 'Download': '',
        # 'Publication': '',
        # 'Citation': '',
        # 'License': '',
        # 'Acknowledgement': '',
        # 'FAQs': '',
        # 'Contact': '',
    }
)