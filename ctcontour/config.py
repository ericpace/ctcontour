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


"""
Morph properties specific to each algorithm
"""
MORPH_PROPS_EP = dict(
    threshold=-260,
    erosion_diam=4,
    dilation_diam=4,
    small_objects_size=300,
    close_diam=2,
    eccentricity=0.99,
    areas=4
)


"""
Morph props for truncation detection
"""
TRUNCATION_PROPS = dict(
    small_objects_size=90,
    out_of_scan_tolerance=25,
    edge_tolerance=20,
    oos_color='red',
    ooe_color='orange'
)

"""
Stems are added to filenames right before the extension suffix
"""

OPTIONS = dict(
    thumbs_stem='_thumbs',
    detail_stem='_detail',
    trunk_stem='_trunk',
    contour_stem='_contour',
    plot_filetype='pdf',
    method='ep',
    contour_color='w',
    contour_linewidth=0.25
)

"""
Restrict to reading only the following DCM tags
"""

DCM_TAGS = [
    "ImageType",
    "RescaleSlope",
    "RescaleIntercept",
    "CTDIPhantomTypeCodeSequence",
    "CTDIvol",
    "PixelSpacing",
    "FloatPixelData",
    "DoubleFloatPixelData",
    "PixelData",
    "BitsAllocated",
    "Rows",
    "Columns",
    "ReconstructionDiameter",
    "PixelRepresentation",
    "SamplesPerPixel",
    "PhotometricInterpretation"
]
