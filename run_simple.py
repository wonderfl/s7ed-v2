#!/usr/bin/env python3
"""
FaceEditPanel v2 - 가장 간단한 실행
부모 창 없이 바로 독립 실행
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.face_edit_v2 import FaceEditPanel

# parent=None으로 바로 독립 창 실행
panel = FaceEditPanel(parent=None)
panel.mainloop()
