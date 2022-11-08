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
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
from skimage import morphology, measure
import scipy.ndimage as ndi
import pandas as pd

from ctcontour.contours import ContourStep, Contour
from ctcontour.io_tools import load_dicom_image
from ctcontour.plot_tools import prep_figure, add_text_overlay, add_labelled_boundingbox, BoundingBox, draw_contour


class Slice:

    def __init__(self, fp):

        # Setup
        self.fp = fp
        self.ds = load_dicom_image(fp)
        self.rescaled_px = self._rescale()

        self.CTDIvol = self.ds.CTDIvol if 'CTDIvol' in self.ds else np.nan
        self.rows = self.ds.Rows if 'Rows' in self.ds else np.nan
        self.columns = self.ds.Columns if 'Columns' in self.ds else np.nan
        self.fov_mm = self.ds.ReconstructionDiameter if 'ReconstructionDiameter' in self.ds else np.nan

        self.has_contour = False
        self.contour = None
        self.ssde_mgy = np.nan
        self.phantom = np.nan

        # Truncation
        self.scan_limit_mask = np.nan

        self.out_of_scan_map = None  # map with out of scan pixels
        self.oos_px = np.nan  # count of how many px are out of scan
        self.is_out_of_scan = False  # bool whether patient in this slice is out of scan

        self.out_of_edge_map = None   # map with out of edge (l,r,t,b) pixels
        self.ooe_px = None  # tuple of (l,r,t,b) of counts of how many px are out of edge
        self.is_out_of_edge = False  # bool whether patient in this slice is out of edge

        self.is_truncated = False

        # Figures
        self.fig_detail = None
        self.fig_thumbs = None
        self.fig_truncation = None

    def _rescale(self):
        """
        Converts px data to HU, by applying rescale slope and intercept from DICOM headers
        :return: px data in Hounsfield Units
        """

        # Convert to int16 (from sometimes int16),
        # should be possible as values should always be low enough (<32k)
        try:
            px = self.ds.pixel_array.astype(np.int16)
            slope = self.ds.RescaleSlope
            intercept = self.ds.RescaleIntercept
        except AttributeError as e:
            logging.warning(f"{e}")
            return

        if slope != 1:
            px = slope * px.astype(np.float64)
            px = px.astype(np.int16)

        px += np.int16(intercept)

        return np.array(px, dtype=np.int16)

    def flag_truncation(self, small_objects_size=90, out_of_scan_tolerance=25, edge_tolerance=20, **kwargs):
        """
        There are two types of truncation:
        1. Out of scan. Patient is truncated because a portion lies beyound the reconstructed image
        2. Out of edge. Patient is truncated because a portion lies beyond either vertical or horizontal edges
        :param small_objects_size:
        :param out_of_scan_tolerance:
        :param edge_tolerance:
        :return:
        """

        # 1. Out of scan
        threshold = np.min(self.rescaled_px) + 1
        scan_limit_mask = np.where(self.rescaled_px <= threshold, True, False)
        scan_limit_mask = morphology.remove_small_objects(scan_limit_mask, small_objects_size)
        self.scan_limit_mask = morphology.dilation(scan_limit_mask, np.ones((4, 4)))

        self.out_of_scan_map = self.contour.contour & self.scan_limit_mask
        self.oos_px = np.count_nonzero(self.out_of_scan_map == True)

        if np.count_nonzero(self.out_of_scan_map == True) > out_of_scan_tolerance:
            self.is_out_of_scan = True
        else:
            self.is_out_of_scan = False

        # 2. Out of edge
        left = ((self.contour.contour[:, 0]) & (self.rescaled_px[:, 0] > threshold))
        right = ((self.contour.contour[:, -1]) & (self.rescaled_px[:, -1] > threshold))
        top = ((self.contour.contour[0]) & (self.rescaled_px[0] > threshold))
        bottom = ((self.contour.contour[-1]) & (self.rescaled_px[-1] > threshold))

        self.out_of_edge_map = np.full(self.rescaled_px.shape, False)
        self.out_of_edge_map[:, 0] = left
        self.out_of_edge_map[:, -1] = right
        self.out_of_edge_map[0] = top
        self.out_of_edge_map[-1] = bottom

        # tuple of counts of left, right, top, bottom
        self.ooe_px = (np.count_nonzero(self.out_of_edge_map[:, 0] == True),
                       np.count_nonzero(self.out_of_edge_map[:, -1] == True),
                       np.count_nonzero(self.out_of_edge_map[0] == True),
                       np.count_nonzero(self.out_of_edge_map[-1] == True))

        self.is_out_of_edge = False

        for edge in (left, right, top, bottom):
            if np.count_nonzero(edge == True) > edge_tolerance:
                self.is_out_of_edge = True

        if self.is_out_of_scan or self.is_out_of_edge:
            self.is_truncated = True

    def contour_with_ep(self, props):

        # Note on memory size:
        # Numpy uses int16 (16 bit) for pixel values
        # Numpy uses int8 (8 bit) for pixel bool values
        # For a 512x512px array:
        # 0.5MB for pixel values
        # 0.25MB for bool values
        # For this contour, approx 3.25MB of memory are needed to store all the steps

        # Initialise the contour steps
        steps = [ContourStep(f"Original", self.rescaled_px)]

        # Threshold
        px1 = self.rescaled_px > props['threshold']
        steps.append(ContourStep(f"Threshold: >{props['threshold']}HU", px1))

        # Despeckle
        px2 = morphology.remove_small_objects(px1, props['small_objects_size'])
        steps.append(ContourStep(f"Despeckle: <{props['small_objects_size']}px", px2))

        # Erode
        shape = (props['erosion_diam'], props['erosion_diam'])
        px3 = morphology.binary_erosion(px2, np.ones(shape))
        steps.append(ContourStep(f"Erode: {props['erosion_diam']}px", px3))

        # Despeckle
        px4 = morphology.remove_small_objects(px3, props['small_objects_size'])
        steps.append(ContourStep(f"Despeckle: <{props['small_objects_size']}px", px4))

        # Dilate
        shape = (props['dilation_diam'], props['dilation_diam'])
        px5 = morphology.binary_dilation(px4, np.ones(shape))
        steps.append(ContourStep(f"Dilate: {props['dilation_diam']}px", px5))

        # Eccentricity filter
        bb = BoundingBox(metric="eccentricity")  # show them before filtering
        steps.append(ContourStep(f"Contour eccentricities", px5, bb=bb))

        labels = measure.label(px5)  # Get bounding-box info for labelled regions
        selected_label_indexes = [r.label for r in measure.regionprops(labels) if r.eccentricity < props['eccentricity']]
        px6 = self._label_from_idx(labels, selected_label_indexes)
        steps.append(ContourStep(f"Filter eccentricities: >{props['eccentricity']}", px6))

        # Close
        px7 = morphology.binary_closing(px6, selem=morphology.disk(props['close_diam']))
        steps.append(ContourStep(f"Close: <{props['close_diam']}px", px7))

        # Binary filling
        px8 = ndi.binary_fill_holes(px7)
        steps.append(ContourStep(f"Fill", px8))

        #
        # Select n largest areas
        bb = BoundingBox(metric="area", number_format='0.0f')  # show them before filtering
        steps.append(ContourStep(f"Contour areas (px$^2$)", px8, bb=bb))
        #
        # get area labels
        labels = measure.label(px8)
        df = pd.DataFrame(measure.regionprops_table(labels, properties=['area']))
        df.index = np.arange(1, len(df) + 1)  # labels start from 1 (i.e. 0 == background)
        #
        # Sort and pick largest
        selected_label_indexes = list(df.sort_values('area', ascending=False).head(props['areas']).index)
        px9 = self._label_from_idx(labels, selected_label_indexes)
        steps.append(ContourStep(f"Final contour", px9))

        # Build Contour object
        self.contour = Contour(method='ep', props=props, steps=tuple(steps))
        self._build_contour_metrics(px9)

    def _label_from_idx(self, labels, selected_label_indexes):
        """
        returns a bool mask from the selected labels.
        :param selected_label_indexes: which label index (or indexes) to apply
        :param labels: labelled mask
        :return: px of same size as original, with zeros outside the mask
        """
        px_new = np.zeros_like(self.rescaled_px, dtype=np.int8)

        for lbl_idx in selected_label_indexes:
            px_new += np.where(labels == lbl_idx, 1, 0)

        px_new = np.where(px_new > 0, True, False)  # Flatten to a bool mask
        return px_new

    def _build_contour_metrics(self, px):
        """
        Use contour to perform measurements
        :param px:
        :return:
        """
        contour = measure.label(px).astype(bool)  # convert to Bool to flatten, otherwise contours won't find them all
        lbl = np.where(contour, 1, 0)
        df = pd.DataFrame(measure.regionprops_table(lbl, self.rescaled_px, properties=['area', 'mean_intensity']))

        # Add metrics
        self.contour.contour = contour
        self.contour.mpv = df.mean_intensity[0]  # Assume df has only 1 row
        self.contour.area_px2 = df.area[0]  # Assume df has only 1 row
        self.contour.area_mm2 = self._area_px_to_mm(self.contour.area_px2)
        self.contour.wed_cm2 = self.calc_wed()

        # Set flag
        self.has_contour = True

        # Calc SSDE
        self.ssde_mgy, self.phantom = self.calc_ssde()

    def calc_wed(self):
        """
        Equation for Water Equivalent Diameter
        :return: Water equivalent diameter in cm^2
        """
        return 2 * np.sqrt(
                             ((self.contour.mpv / 1000) + 1) *
                             (self.contour.area_mm2 / np.pi)
                           ) / 10  # div by 10 to convert to cm

    def calc_ssde(self):
        """
        Calculation of SSDE as per equations in AAPM220
        Requires these values to be present in DICOM tag:
        - CTDIvol
        - CTDIPhantomTypeCodeSequence
        :return: SSDE value in mGy
        """
        body, head = "IEC Body Dosimetry Phantom", "IEC Head Dosimetry Phantom"

        if 'CTDIPhantomTypeCodeSequence' in self.ds:
            code_meaning = self.ds.CTDIPhantomTypeCodeSequence[0].CodeMeaning
            if code_meaning == body:
                return self.CTDIvol * (3.704369 * np.exp(-0.03671937 * self.contour.wed_cm2)), body
            elif code_meaning == head:
                return self.CTDIvol * (1.874799 * np.exp(-0.03871313 * self.contour.wed_cm2)), head
            else:
                return np.nan, ''
        else:
            return np.nan, ''

    def _area_px_to_mm(self, area_px2):
        try:
            ps = self.ds.PixelSpacing
            return area_px2 * ps[0] * ps[1]  # Area to mm^2
        except KeyError as e:
            print(f'Key error:{e}')
            return np.nan

    def data_as_df(self):
        """
        Combine contour info as DataFrame with one row
        :return: DataFrame
        """
        return pd.DataFrame(
            dict(
                filepath=[self.fp],
                filename=[Path(self.fp).name],
                area_mm2=[self.contour.area_mm2],
                mpv_hu=[self.contour.mpv],
                wed_cm=[self.contour.wed_cm2],
                phantom=[self.phantom],
                ctdi_vol=[self.CTDIvol],
                ssde=[self.ssde_mgy],
                is_out_of_scan=self.is_out_of_scan,
                out_of_scan_px=self.oos_px,
                is_out_of_edge=self.is_out_of_edge,
                out_of_edge_px=str(self.ooe_px),
                is_truncated=self.is_truncated
            )
        )

    def draw_fig_detail(self):
        """
        Prepare a Figure to showcase all the contour steps.
        If a contour step includes a bounding box, show it.
        Final subplot will always draw the contour as an outline
        over the original pixel_array.
        :return: Figure
        """
        fig, axs = prep_figure(self.contour.steps)

        fig.suptitle(self.fp.name, fontsize=14, y=0.99)

        for step, ax in zip(self.contour.steps, axs):
            ax.imshow(step.pixel_array, cmap='gray')
            ax.set_title(step.label)

            if step.bb:  # If the contour step includes a bounding box
                labels = measure.label(step.pixel_array)
                df = pd.DataFrame(measure.regionprops_table(labels, properties=['bbox', step.bb.metric]))

                add_labelled_boundingbox(ax, df, step.bb.metric,
                                         number_format=step.bb.number_format,
                                         color=step.bb.color)

        # Show contour
        vmin = np.min(self.rescaled_px)
        vmax = np.max(self.rescaled_px)

        cutout = np.where(self.contour.contour, self.contour.steps[0].pixel_array, vmin)
        axs[-1].imshow(cutout, cmap='gray', vmin=vmin, vmax=vmax)

        self.fig_detail = fig
        return fig

    def draw_fig_thumbs(self):
        """
        Prepare a Figure showing only the original pixel array
        on the left and the contour overlay on right
        :return: Figure
        """
        # fig, axs = prep_figure(self.contour.steps, cols=2, rows=1, figheight=4, figwidth=7)
        plt.switch_backend('Agg')
        fig, axs = plt.subplots(nrows=1, ncols=2)
        fig.set(figheight=5, figwidth=9)

        for ax in axs:
            ax.axis('off')

        fig.suptitle(self.fp.name, fontsize=9, y=0.04)

        axs[0].imshow(self.contour.steps[0].pixel_array, cmap='gray')
        axs[0].set_title(self.contour.steps[0].label, fontsize=10)

        vmin = np.min(self.rescaled_px)
        vmax = np.max(self.rescaled_px)

        # cutout = np.where(self.contour.contour, self.contour.steps[0].pixel_array, vmin)
        # axs[1].imshow(cutout, cmap='gray', vmin=vmin, vmax=vmax)
        # axs[1].set_title(self.contour.steps[-1].label, fontsize=10)

        axs[1].imshow(self.rescaled_px, cmap='gray')
        draw_contour(axs[1], self.contour.contour, linewidth=1.0, color='w')

        fig.subplots_adjust(left=0.01, bottom=0, right=0.99, top=1, wspace=0.02, hspace=0)

        self.fig_thumbs = fig
        return fig

    def draw_fig_truncation(self, oos_color='red', ooe_color='orange', **kwargs):
        plt.switch_backend('Agg')

        fig, ax = plt.subplots()
        fig.set(figheight=8, figwidth=8)
        fig.set_tight_layout(True)
        ax.axis('off')

        cmap_slm = colors.ListedColormap(['orangered'])
        cmap_oos = colors.ListedColormap([oos_color])  # orange
        cmap_ooe = colors.ListedColormap([ooe_color])  # darkorange

        # Show original
        ax.imshow(self.rescaled_px, cmap='gray')
        ax.set_title(self.fp.name, fontsize=10)

        # Show scan limit
        # alpha = np.where(self.scan_limit_mask == True, 0.25, 0.)
        # ax.imshow(self.scan_limit_mask, alpha=alpha, cmap=cmap_slm)

        # Show out_of_scan_map
        alpha = np.where(self.out_of_scan_map == True, 1., 0.)
        ax.imshow(self.out_of_scan_map, alpha=alpha, cmap=cmap_oos)

        # Show out_of_edge_map
        ooe_presentation = morphology.dilation(self.out_of_edge_map, np.ones((6, 6)))
        alpha = np.where(ooe_presentation == True, 1., 0.)
        ax.imshow(ooe_presentation, alpha=alpha, cmap=cmap_ooe)

        # draw_contour(ax, self.contour.contour, linewidth=0.5, color='w')

        text_labels = [
            f"is_out_of_scan: {self.is_out_of_scan} {self.oos_px}",
            f"is_out_of_edge: {self.is_out_of_edge} l={self.ooe_px[0]}, r={self.ooe_px[1]}, t={self.ooe_px[2]}, b={self.ooe_px[3]}",
            f"is_truncated: {self.is_truncated}"
        ]
        # add_text_overlay(ax, text_labels)

        self.fig_truncation = fig

    def save_fig_thumbs(self, fp):
        self.fig_thumbs.savefig(fp)

    def save_fig_detail(self, fp):
        self.fig_detail.savefig(fp)

    def save_fig_trunk(self, fp):
        self.fig_truncation.savefig(fp)

    def save_csv(self, fp, index=False):
        df = self.data_as_df()
        df.to_csv(fp, index=index)

    def save_npz(self, fp):
        np.savez_compressed(fp, mask=self.contour.contour)

