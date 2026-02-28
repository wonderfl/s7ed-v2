#!/usr/bin/env python3
"""
FaceForge - 얼굴 모핑 애플리케이션
MediaPipe + PIL + Tkinter 기반
"""
# import tensorflow as tf
# tf.get_logger().setLevel('ERROR')

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"    # TensorFlow INFO/Warning 숨김
os.environ["GLOG_minloglevel"] = "3"        # absl/glog INFO/Warning 숨김
os.environ["FLAGS_minloglevel"] = "3"       # 동일한 효과 (일부 플랫폼 필요)

from absl import logging
logging.set_verbosity(logging.ERROR)
logging._warn_preinit_stderr = False




import tkinter as tk
from gui.__init__ import FaceForgePanel

import mediapipe as mp
def print_mesh():
    mp_face_mesh = mp.solutions.face_mesh
    for attr in dir(mp_face_mesh):
        if 'FACEMESH_' in attr:
            print(attr)

#print_mesh()

# 숨겨진 부모 창
root = tk.Tk()
root.withdraw()  # 보이지 않게

# 패널 생성
panel = FaceForgePanel(parent=root)

# 닫기 처리
def on_close():
    panel.close_popup()
    root.quit()  # quit()으로 변경
    
panel.protocol("WM_DELETE_WINDOW", on_close)



# 바로 패널만 보임
panel.mainloop()
root.destroy()  # 부모 창 정리


