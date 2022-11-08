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


import logging
from glob import glob
from multiprocessing import Pool
from matplotlib import pyplot as plt
import pydicom

from ctcontour.io_tools import target_fp, merge_pdfs, merge_csvs, NotAxialImageError
from ctcontour.slice import Slice


def single_run(fp, morph_props, truncation_props, kwargs):
    """
    Portion of the overall contouring process that we may parallelise
    :param fp: file path to single DCM file
    :param morph_props: morph props to apply
    :param truncation_props: morph props for truncation detection
    :param kwargs: other options
    :return: None
    """

    # Load the file
    try:
        logging.info(f"Reading: {fp}")
        s = Slice(fp)
    except pydicom.errors.InvalidDicomError as e:
        return
    except NotAxialImageError as e:
        return

    # Contour
    if kwargs['method'] == "ep":
        s.contour_with_ep(morph_props)
        s.flag_truncation(**truncation_props)

    # Output
    if kwargs['detail']:
        s.draw_fig_detail()
        dst_fp = target_fp(kwargs['src_root'], kwargs['dst_root'], fp, kwargs['detail_stem'], kwargs['plot_filetype'])
        logging.info(f"Writing: {dst_fp}")
        s.save_fig_detail(dst_fp)
        plt.close(s.fig_detail)

    if kwargs['thumbs']:
        s.draw_fig_thumbs()
        dst_fp = target_fp(kwargs['src_root'], kwargs['dst_root'], fp, kwargs['thumbs_stem'], kwargs['plot_filetype'])
        logging.info(f"Writing: {dst_fp}")
        s.save_fig_thumbs(dst_fp)
        plt.close(s.fig_thumbs)

    if kwargs['trunk']:
        s.draw_fig_truncation(**truncation_props)
        dst_fp = target_fp(kwargs['src_root'], kwargs['dst_root'], fp, kwargs['trunk_stem'], kwargs['plot_filetype'])
        logging.info(f"Writing: {dst_fp}")
        s.save_fig_trunk(dst_fp)

    if kwargs['csv']:
        dst_fp = target_fp(kwargs['src_root'], kwargs['dst_root'], fp, '', 'csv')
        logging.info(f"Writing: {dst_fp}")
        s.save_csv(dst_fp)

    if kwargs['npz']:
        dst_fp = target_fp(kwargs['src_root'], kwargs['dst_root'], fp, '', 'npz')
        logging.info(f"Writing: {dst_fp}")
        s.save_npz(dst_fp)


def starmap_run(fp, morph_props, truncation_props, kwargs):
    """
    Unravel processing on all available cores
    :param fp: file path to single DCM file
    :param morph_props: morph props to apply
    :param kwargs: other options
    :return: None
    """
    single_run(fp, morph_props, truncation_props, kwargs)


def merge_files(kwargs):
    """
    Outside merge function to prepare list of files for merging.
    This is needed to iterate through the multiple nested dirs
    :param kwargs: Dict with opts defined in config.py
    :return: None
    """
    dst_dirs = [kwargs['dst_root']] + [fp for fp in kwargs['dst_root'].rglob('*') if fp.is_dir()]

    if kwargs['merge_pdf']:
        for dst_dir in dst_dirs:

            def _merge_pdf(suffix):
                logging.info(f"Merging [{kwargs[suffix]}] PDFs in {dst_dir}")
                merge_pdfs(
                    sorted([f for f in glob(str(dst_dir) + f"/*{kwargs[suffix]}.pdf")]),
                    dst_dir / f"{dst_dir.name}{kwargs[suffix]}.pdf"
                )

            if kwargs['thumbs']:
                _merge_pdf('thumbs_stem')

            if kwargs['detail']:
                _merge_pdf('detail_stem')

            if kwargs['trunk']:
                _merge_pdf('trunk_stem')

    if kwargs['merge_csv']:
        for dst_dir in dst_dirs:
            logging.info(f"Merging CSVs in {dst_dir}")
            merge_csvs(
                sorted([f for f in glob(str(dst_dir) + f"/*.csv")]),
                dst_dir / f"{dst_dir.name}.csv"
            )


def start(morph_props=None, truncation_props=None, kwargs=None):
    """
    This is the overall contouring process. Here we perform:
    - Build list of directories
    - Contour all valid files in each directory
    - Merge PDF and CSV results
    :param morph_props: Dict with props. Must match contour_method in kwargs
    :param truncation_props: morph props for truncation detection
    :param kwargs: Dict with options defined in config.py
    :return: None
    """

    # If it's a single file, process and return
    if kwargs['src_root'].is_file():
        single_run(kwargs['src_root'], morph_props, truncation_props, kwargs)
        return

    # if it's a folder, check for recursion
    if kwargs['recursive']:
        files = sorted([fp for fp in kwargs['src_root'].rglob('*') if fp.is_file() and fp.suffix == '.dcm'])
        dirs = [kwargs['src_root']] + [fp for fp in kwargs['src_root'].rglob('*') if fp.is_dir()]
        logging.info(f"Found {len(files)} files in {len(dirs)} folders")
    else:
        files = sorted([fp for fp in kwargs['src_root'].glob('*') if fp.is_file() and fp.suffix == '.dcm'])
        logging.info(f"Found {len(files)} files")

    # Process the files
    if kwargs['single']:
        for fp in files:
            single_run(fp, morph_props, truncation_props, kwargs)
    else:
        pool_kwargs = [(fp, morph_props, truncation_props, kwargs) for fp in files]
        pool = Pool()
        pool.starmap(starmap_run, pool_kwargs)

    # Merging
    merge_files(kwargs)
