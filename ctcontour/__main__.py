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


import argparse
import logging.config
from pathlib import Path

from ctcontour import contour_proc
from ctcontour.config import MORPH_PROPS_EP, TRUNCATION_PROPS, OPTIONS
from ctcontour.decorator_funcs import timer

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def parse_args_contour():
    message = """
    Fully automated patient abdomino-pelvic contouring for CT images.
    https://doi.org/10.1016/j.ejmp.2022.10.027.
    """

    parser = argparse.ArgumentParser(description=message)

    parser.add_argument('src_root', type=str, metavar="Source",
                        help='Location of source dicom file or folder to contour')

    parser.add_argument('dst_root', type=str, metavar="Destination",
                        help='Destination for results. Should ideally be an empty directory. Existing files may be overwritten \n')

    parser.add_argument("--thumbs",
                        help="Save PDF showing original image at left and contoured image at right. \
                              File saved as *_thumbs.pdf",
                        action="store_true")

    parser.add_argument("--detail",
                        help="save PDF showing full morphological steps. \
                        File saved as *_detail.pdf",
                        action="store_true")

    parser.add_argument("--trunk",
                        help="save PDF showing truncation map. Red for out-of-scan and orange for out-of-edge. \
                        File saved as *_trunk.pdf",
                        action="store_true")

    parser.add_argument("--npz",
                        help="save trunk contour to compressed npz file. Uses dictionary key: 'mask': mask. \
                              File saved as *.npz",
                        action="store_true")

    parser.add_argument("--csv",
                        help="save contour metrics to csv. \
                              File saved as *.csv",
                        action="store_true")

    parser.add_argument("--single",
                        help="No multicore processing (useful for debugging)",
                        action="store_true")

    parser.add_argument("--recursive",
                        help="Also process subfolders. Generates a list of all subfolders before starting.",
                        action="store_true")

    parser.add_argument("--merge_pdf",
                        help="Merge generated PDFs. \
                              By default merges into [foldername]_[thumbs|detail|trunk].pdf",
                        action="store_true")

    parser.add_argument("--merge_csv",
                        help="Merge generated CSVs. \
                              By default merges into [foldername]_mask.csv",
                        action="store_true")

    args = parser.parse_args()

    args.src_root = Path(args.src_root)
    args.dst_root = Path(args.dst_root)

    return args


@timer
def contour():
    """
    Top level entry point for contouring and truncation detection.
    :return: None
    """
    args = parse_args_contour()

    kwargs = {**vars(args), **OPTIONS}

    logging.info(
         f"Running...\n"
         f"     Source: {kwargs['src_root']}\n"
         f"Destination: {kwargs['dst_root']}\n"
         f"  Recursive: {kwargs['recursive']}\n"
         f"Single core: {kwargs['single']}\n"
         f"   Save PDF: Thumbnails [{kwargs['thumbs']}], Details [{kwargs['detail']}], Trunk [{kwargs['trunk']}]\n"
         f"   Save CSV: {kwargs['csv']}\n"
         f"   Save NPZ: {kwargs['npz']}\n"
         f"      Merge: PDF [{kwargs['merge_pdf']}], CSV [{kwargs['merge_csv']}]\n")

    contour_proc.start(morph_props=MORPH_PROPS_EP, truncation_props=TRUNCATION_PROPS, kwargs=kwargs)


def __main__():
    contour()


if __name__ == "__main__":
    __main__()
