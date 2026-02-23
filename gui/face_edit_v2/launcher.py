"""Launcher helpers for FaceEditPanel."""
from __future__ import annotations

from typing import Optional
import tkinter as tk


def show_face_edit_panel(parent: Optional[tk.Toplevel] = None):
    """얼굴 편집 패널을 생성해 표시한다."""
    from . import FaceEditPanel  # 지연 임포트로 순환 의존 방지

    panel = FaceEditPanel(parent)
    panel.transient(parent)
    return panel
