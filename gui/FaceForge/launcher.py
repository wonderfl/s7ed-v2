#!/usr/bin/env python3
"""
FaceForge - 얼굴 모핑 애플리케이션
MediaPipe + PIL + Tkinter 기반
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"    # TensorFlow INFO/Warning 숨김
os.environ["GLOG_minloglevel"] = "3"        # absl/glog INFO/Warning 숨김
os.environ["FLAGS_minloglevel"] = "3"       # 동일한 효과 (일부 플랫폼 필요)

from absl import logging
logging.set_verbosity(logging.ERROR)
logging._warn_preinit_stderr = False

from typing import Optional
import tkinter as tk
from gui.FaceForge.gui import FaceForgePanel


def show_face_forge_panel(parent: Optional[tk.Toplevel] = None):
    """얼굴 편집 패널을 생성해 표시한다."""

    panel = FaceForgePanel(parent)
    panel.transient(parent)
    return panel
