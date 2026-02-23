"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
모든 Mixin을 통합
"""
from .ui import UIMixin
from .handlers import HandlersMixin
from .logic import LogicMixin
from .utils import UtilsMixin


class MorphingManagerMixin(
    UIMixin,
    HandlersMixin,
    LogicMixin,
    UtilsMixin
):
    """얼굴 특징 보정 관리 기능 Mixin"""
    pass
