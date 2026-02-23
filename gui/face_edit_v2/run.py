import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tkinter as tk
from gui.face_edit_v2 import FaceEditPanel

# 숨겨진 부모 창
root = tk.Tk()
root.withdraw()  # 보이지 않게

# 패널 생성
panel = FaceEditPanel(parent=root)

# 닫기 처리
def on_close():
    panel.destroy()
    root.quit()  # quit()으로 변경
    
panel.protocol("WM_DELETE_WINDOW", on_close)

# 바로 패널만 보임
panel.mainloop()
root.destroy()  # 부모 창 정리
