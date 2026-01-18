"""
얼굴 편집 패널 - 폴리곤 렌더링 Mixin
폴리곤 그리기 관련 기능을 담당
"""
import math
import tkinter as tk
import numpy as np

# scipy와 cv2 import 확인
try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False
    Delaunay = None

from .drawing import DrawingMixin
from .polygon_builder import PolygonBuilderMixin
from .interaction import InteractionMixin
from .utils import UtilsMixin


class PolygonRendererMixin(
    DrawingMixin,
    PolygonBuilderMixin,
    InteractionMixin,
    UtilsMixin
):
    """폴리곤 렌더링 기능 Mixin"""
    pass
