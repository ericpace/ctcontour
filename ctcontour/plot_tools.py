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


from dataclasses import dataclass
from math import ceil
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from skimage import measure


@dataclass
class BoundingBox:
    metric: str = None
    number_format: str = '0.3f'
    color: str = 'w'


def prep_figure(contour_steps, cols=4, rows=None, figheight=14, figwidth=17):
    """
    Prepares a standard matplotlib subplots layout
    :param contour_steps: number of steps in the contour process
    :param cols: predefined number of columns
    :param rows: predefined number of rows
    :param figheight: desired figure height
    :param figwidth:  desired figure width
    :return: figure and axes objects
    """
    plt.switch_backend('Agg')

    if not rows:
        rows = ceil(len(contour_steps)/cols)

    fig, axes = plt.subplots(nrows=rows, ncols=cols)

    axs = axes.flatten()

    fig.set(figheight=figheight, figwidth=figwidth)
    fig.set_tight_layout(True)

    for ax in axs:
        ax.axis('off')
    return fig, axs


def add_labelled_boundingbox(ax, prop_df, property, number_format='0.2f', color='r'):
    """
    Overlays bounding boxes around label objects
    :param ax: input axis figure to overlay
    :param prop_df: DataFrame with property labels
    :param property: shape property label (e.g. area or eccentricity)
    :param number_format: how to format the number
    :param color: label colour
    :return: None
    """

    for index, roi in prop_df.iterrows():
        width = roi['bbox-3'] - roi['bbox-1']
        height = roi['bbox-2'] - roi['bbox-0']
        info_label = roi[property]

        boundingbox = Rectangle((roi['bbox-1'], roi['bbox-0']), width, height,
                                linewidth=0.5, edgecolor=color, facecolor='none')
        ax.add_patch(boundingbox)

        plot_size = ax.get_xlim()[1] - ax.get_xlim()[0]

        # Aligns label left or right depending on where bounding box is
        if roi['bbox-1'] <= plot_size/2:
            ax.text(roi['bbox-1'], roi['bbox-0'] - 2,
                    f"{info_label:{number_format}}", fontsize=8, color=color)
        else:
            ax.text(roi['bbox-3'], roi['bbox-0'] - 2,
                    f"{info_label:{number_format}}", fontsize=8, color=color, horizontalalignment='right')


def add_text_overlay(ax, text_str_list, color='w'):
    step = 15
    # top left alignment
    for i, text_str in enumerate(text_str_list):
        ax.text(5, 15+(i*step), text_str, fontsize=8, color=color)

    return ax


def draw_contour(ax, px, **kwargs):
    """
    Draw the contour outline
    :param ax: the Axes to plot on
    :param px: the bool mask with the contour
    :param kwargs: plotting options compatible with ax.plot(), like linewidth and color
    :return: None
    """
    contours = measure.find_contours(px)

    for contour in contours:
        ax.plot(contour[:, 1], contour[:, 0], **kwargs)