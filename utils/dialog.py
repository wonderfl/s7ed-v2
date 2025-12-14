"""
위치를 기억하는 커스텀 다이얼로그 유틸리티
messagebox를 대체하여 창 위치를 기억할 수 있음
"""
import tkinter as tk
from tkinter import ttk
import globals as gl
import utils.config as config

# 다이얼로그 위치 저장 딕셔너리
_dialog_positions = {}

def _get_dialog_position(dialog_id):
    """다이얼로그 위치를 가져옵니다."""
    key = f"dialog_{dialog_id}_x"
    y_key = f"dialog_{dialog_id}_y"
    
    x = getattr(gl, key, None) if hasattr(gl, key) else None
    y = getattr(gl, y_key, None) if hasattr(gl, y_key) else None
    
    return x, y

def _save_dialog_position(dialog_id, x, y):
    """다이얼로그 위치를 저장합니다."""
    key_x = f"dialog_{dialog_id}_x"
    key_y = f"dialog_{dialog_id}_y"
    
    setattr(gl, key_x, x)
    setattr(gl, key_y, y)
    config.save_config()

def askyesno(title, message, dialog_id="default", parent=None):
    """
    messagebox.askyesno()와 동일한 기능이지만 위치를 기억하는 커스텀 다이얼로그
    
    Args:
        title: 다이얼로그 제목
        message: 표시할 메시지
        dialog_id: 다이얼로그 식별자 (위치를 별도로 저장하기 위함)
        parent: 부모 창 (None이면 기본 루트 창 사용)
    
    Returns:
        bool: True(예) 또는 False(아니오)
    """
    if parent is None:
        # gui 모듈에서 _root 가져오기
        try:
            from gui.gui import _root
            parent = _root
        except ImportError:
            parent = tk.Tk()
    
    # 이미 같은 다이얼로그가 열려있으면 무시
    if hasattr(askyesno, '_active_dialogs'):
        if dialog_id in askyesno._active_dialogs:
            dialog = askyesno._active_dialogs[dialog_id]
            if dialog.winfo_exists():
                dialog.lift()
                return None
    else:
        askyesno._active_dialogs = {}
    
    # 결과 저장 변수
    result = [None]
    
    # 다이얼로그 창 생성
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.attributes('-toolwindow', True)
    
    # 활성 다이얼로그 목록에 추가
    askyesno._active_dialogs[dialog_id] = dialog
    
    # 창 크기 설정
    dialog_width = 400
    dialog_height = 150
    
    # 창 위치 설정 (이전 위치가 있으면 사용, 없으면 부모 창 중앙)
    x, y = _get_dialog_position(dialog_id)
    if x is not None and y is not None:
        pass  # 저장된 위치 사용
    else:
        # 부모 창 중앙에 표시
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - dialog_width) // 2
        y = py + (ph - dialog_height) // 2
    
    dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    # 창 이동 시 위치 저장
    def on_move(event=None):
        if dialog.winfo_exists():
            _save_dialog_position(dialog_id, dialog.winfo_x(), dialog.winfo_y())
    
    dialog.bind('<Configure>', on_move)
    
    # 메시지 표시
    msg_frame = tk.Frame(dialog, padx=20, pady=20)
    msg_frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(
        msg_frame,
        text=message,
        justify=tk.LEFT,
        wraplength=360
    ).pack(anchor=tk.W, pady=(0, 20))
    
    # 버튼 프레임
    btn_frame = tk.Frame(msg_frame)
    btn_frame.pack(fill=tk.X)
    
    def on_yes():
        result[0] = True
        if dialog_id in askyesno._active_dialogs:
            del askyesno._active_dialogs[dialog_id]
        dialog.destroy()
    
    def on_no():
        result[0] = False
        if dialog_id in askyesno._active_dialogs:
            del askyesno._active_dialogs[dialog_id]
        dialog.destroy()
    
    btn_yes = tk.Button(btn_frame, text="예", command=on_yes, width=10)
    btn_yes.pack(side=tk.LEFT, padx=(0, 10))
    
    btn_no = tk.Button(btn_frame, text="아니오", command=on_no, width=10)
    btn_no.pack(side=tk.LEFT)
    
    # ESC 키로 닫기 (아니오로 처리)
    dialog.bind('<Escape>', lambda e: on_no())
    dialog.focus_set()
    
    # 모달 대화상자로 만들기
    dialog.transient(parent)
    dialog.grab_set()
    
    # 창이 닫힐 때까지 대기
    dialog.wait_window()
    
    return result[0]

