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
import numpy as np
import pandas as pd

from ctcontour.plot_tools import BoundingBox


@dataclass
class ContourStep:
    label: str
    pixel_array: np.ndarray
    bb: BoundingBox = None


@dataclass
class Contour:
    method: str
    props: dict
    steps: tuple = None
    contour: np.ndarray = None
    area_px2: float = np.nan
    area_mm2: float = np.nan
    mpv: float = np.nan
    wed_cm2: float = np.nan

    def get_metrics(self, as_type=None):
        data = {
            "contour_method": [self.method],
            "area_px2": [self.area_px2],
            "area_mm2": [self.area_mm2],
            "mpv": [self.mpv],
            "wed_cm2": [self.wed_cm2]
        }
        if as_type == 'dict':
            return data
        else:
            return pd.DataFrame(data=data)
