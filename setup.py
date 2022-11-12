"""
Author: Eric Pace
This file is part of CTContour.

CTContour is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation version 3.

CTContour is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Patient CT Contour.
If not, see <https://www.gnu.org/licenses/>.
"""

import setuptools

""" CTcontour setup """


with open('README.md') as f:
    README = f.read()

setuptools.setup(
    author="Eric Pace",
    author_email="ericpace@pm.me",
    name='ctcontour',
    license="GNU GPLv3",
    description='Fully automated patient abdomino-pelvic contouring for CT images. https://doi.org/10.1016/j.ejmp.2022.10.027.',
    version='v1.0',
    long_description='Fully automated patient abdomino-pelvic contouring for CT images. https://doi.org/10.1016/j.ejmp.2022.10.027.',
    url='https://github.com/ericpace/ct_contour',
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ctc=ctcontour.__main__:contour',
        ]
    },
    python_requires=">=3.8",
    # Enable install requires when publishing on the normal PyPi
    install_requires=[
        'pydicom>=2.1.2',
        'numba>=0.52.0',
        'scipy>=1.4.1',
        'scikit-image>=0.18.2',
        'pandas>=1.2.1',
        'matplotlib>=3.3.4',
        'seaborn>=0.11.1',
        'PyPDF2>=1.26.0'
    ],
    classifiers=[
        'Programming Language :: Python'
    ],
)
