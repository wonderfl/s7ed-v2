"""
눈동자 맵핑 방법 선택 UI
"""

import tkinter as tk
from tkinter import ttk


class IrisUI:
    """눈동자 관련 UI를 관리하는 클래스"""
    
    def __init__(self, parent):
        """
        초기화
        
        Args:
            parent: 부모 클래스 인스턴스 (FaceEditPanel 등)
        """
        self.parent = parent
    
    def create_iris_mapping_frame(self, parent_frame):
        """
        눈동자 맵핑 방법 선택 프레임 생성
        
        Args:
            parent_frame: 부모 프레임
            
        Returns:
            ttk.Frame: 생성된 프레임
        """
        # 프레임 생성
        mapping_frame = ttk.LabelFrame(parent_frame, text="눈동자 맵핑 방법", padding=10)
        
        # 변수가 없거나 타입이 맞지 않으면 다시 생성
        if not hasattr(self.parent, 'iris_mapping_method') or not isinstance(self.parent.iris_mapping_method, tk.StringVar):
            self.parent.iris_mapping_method = tk.StringVar(value="iris_outline")
        
        # 라디오 버튼 생성 - 수동 상호 배제 구현
        self.radio_var = self.parent.iris_mapping_method
        
        def select_iris_outline():
            self.radio_var.set("iris_outline")
            self.on_mapping_method_change()
            # 다른 라디오 버튼 상태 업데이트
            if hasattr(self, 'radio2'):
                self.radio2.deselect()
        
        def select_eye_landmarks():
            self.radio_var.set("eye_landmarks")
            self.on_mapping_method_change()
            # 다른 라디오 버튼 상태 업데이트
            if hasattr(self, 'radio1'):
                self.radio1.deselect()
        
        self.radio1 = tk.Radiobutton(
            mapping_frame, 
            text="눈동자 외곽선 맵핑", 
            variable=self.radio_var, 
            value="iris_outline",
            command=select_iris_outline
        )
        self.radio1.pack(anchor=tk.W, pady=2)
        
        self.radio2 = tk.Radiobutton(
            mapping_frame, 
            text="눈 랜드마크 맵핑", 
            variable=self.radio_var, 
            value="eye_landmarks",
            command=select_eye_landmarks
        )
        self.radio2.pack(anchor=tk.W, pady=2)
        
        # 초기 상태 설정
        if self.radio_var.get() == "iris_outline":
            self.radio2.deselect()
        else:
            self.radio1.deselect()
        
        # 디버그 출력
        print(f"[DEBUG] Created radio buttons with variable: {self.radio_var}")
        print(f"[DEBUG] Initial value: {self.radio_var.get()}")
        
        return mapping_frame
    
    def on_mapping_method_change(self):
        """맵핑 방법 변경 시 호출되는 콜백"""
        method = self.parent.iris_mapping_method.get()
        print(f"[DEBUG] Iris mapping method changed to: {method}")
        
        # 캔버스 다시 그리기
        if hasattr(self.parent, 'refresh_canvas'):
            self.parent.refresh_canvas()
        elif hasattr(self.parent, 'on_canvas_refresh'):
            self.parent.on_canvas_refresh()
