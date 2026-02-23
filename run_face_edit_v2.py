#!/usr/bin/env python3
"""
FaceEditPanel v2 바로 실행
"""
import sys
import os

# MediaPipe 경고 메시지 억제
os.environ['GLOG_minloglevel'] = '3'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
    import logging
    logging.getLogger('absl').setLevel(logging.ERROR)
except ImportError:
    pass

import warnings
warnings.filterwarnings('ignore')

# 프로젝트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui.face_edit_v2 import FaceEditPanel
    panel = FaceEditPanel()
    panel.mainloop()
except Exception as e:
    print(f"FaceEditPanel v2 실행 실패: {e}")
    import traceback
    traceback.print_exc()
