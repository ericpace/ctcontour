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


import os
import logging
from pathlib import Path

import pydicom
from PyPDF2 import PdfFileMerger, PdfFileReader
from PyPDF2 import utils as PyPDF2utils
import pandas as pd

from ctcontour.config import DCM_TAGS


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class NotAxialImageError(Error):
    """Not an Axial image (possibly a localiser or secondary image"""
    def __init__(self, image_type, message="Not an Axial image"):
        self.image_type = image_type
        self.message = f"{message}: {self.image_type}"
        super().__init__(self.message)


def load_dicom_image(fp):
    """
    Load ds from DICOM files

    :param fp: path to single DCM
    :return: Pydicom DataSet
    """

    try:
        ds = pydicom.dcmread(fp, specific_tags=DCM_TAGS)

        if 'AXIAL' not in list(ds.ImageType):
            raise NotAxialImageError(list(ds.ImageType))
        else:
            return ds

    except pydicom.errors.InvalidDicomError as e:
        logging.error(f"{fp}: {e}")
        raise
    except AttributeError as e:
        logging.error(f"{fp}: {e}")
        raise
    except NotAxialImageError as e:
        logging.error(f"{fp}: {e}")
        raise


def _delete_file(fp):
    try:
        os.remove(fp)
    except FileNotFoundError as e:
        logging.error(f"{fp} does not exist")
    except IsADirectoryError as e:
        logging.error(f"{fp} is a directory")


def target_fp(src_root, dst_root, src, stem_part, suffix):
    """
    Builds final target file path for writing
    :param src_root: top level source path
    :param dst_root: top level destination path
    :param src: fully qualified path to source dcm file
    :param stem_part: to be added at the end of the filename, like '_thumbs'
    :param suffix: the suffix, like pdf or csv
    :return: destination file path as Path object
    """

    # Convert to Paths if not done already
    src_root = Path(src_root)

    # If src_root points to a file, then program is running on a single file only
    if src_root.is_file():
        src_root = src_root.parent

    dst_root = Path(dst_root)
    src = Path(src)

    # Build target
    index = len(src_root.parts)
    dst = dst_root.joinpath(*src.parts[index:])
    dst = dst.parent / f"{dst.stem}{stem_part}.{suffix}"

    # Create folders if they don't exist
    if not dst.parent.exists():
        try:
            os.makedirs(dst.parent)
        except FileExistsError as e:
            logging.warning(f"Exists: {dst}")
    # if not dst.parent.exists():
    #
    # if dst.exists():
    #     logging.warning(f"File exists: {dst}")

    return dst


def merge_pdfs(pdf_list, fp, chunksize=500, delete_original=True):
    """
    Will merge a given list of pdf filepaths
    :param pdf_list: list of pdf filepaths
    :param fp: destination file path for merged result
    :param chunksize: Generate multiple files if list larger than chunksize
    :param delete_original: optionally remove the original list of pdf files
    :return: None
    """
    fp = Path(fp)
    chunks = [pdf_list[x:x + chunksize] for x in range(0, len(pdf_list), chunksize)]

    for chunknum, pdf_sublist in enumerate(chunks):
        merger = PdfFileMerger()
        for pdf in pdf_sublist:
            try:
                merger.append(PdfFileReader(open(pdf, 'rb')))
            except PyPDF2utils.PdfReadError as e:
                logging.warning(e)

        dst = fp.parent / f"{fp.stem}_{chunknum}{fp.suffix}"
        merger.write(str(dst))
        merger.close()

    if delete_original:
        for pdf in pdf_list:
            _delete_file(pdf)


def merge_csvs(csv_list, fp, index=False, delete_original=True):
    """
    Will merge a given list of csv filepaths
    :param csv_list: list of csv filepaths
    :param fp: destination file path for merged result
    :param index: Include Pandas index in output?
    :param delete_original: optionally remove the original list of pdf files
    :return: None
    """

    if not csv_list:
        return

    # Remove any existing target csv files otherwise we'll append old results with new ones
    try:
        if fp.exists():
            csv_list.remove(str(fp))
    except ValueError as e:
        logging.warning(f"Merging csv: {e}")

    # combine results
    df = pd.concat((pd.read_csv(f) for f in csv_list))
    df.to_csv(fp, index=index)

    # delete individual files
    if delete_original:
        for csv in csv_list:
            _delete_file(csv)
