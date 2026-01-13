"""
얼굴 편집 패널 - 스타일 전송 Mixin
스타일 전송 관련 기능을 담당
"""
import os
import tkinter as tk
from tkinter import filedialog

import utils.kaodata_image as kaodata_image


class StyleManagerMixin:
    """스타일 전송 관리 기능 Mixin"""
    
    def _create_style_transfer_ui(self, parent):
        """스타일 전송 UI 생성 (탭용)"""
        # parent는 이미 탭 노트북이므로 프레임만 생성
        style_frame = tk.Frame(parent, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 10
        
        # 스타일 이미지 선택 버튼
        style_button_frame = tk.Frame(style_frame)
        style_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_select_style = tk.Button(
            style_button_frame,
            text="스타일 이미지 선택...",
            command=self.select_style_image,
            width=20
        )
        btn_select_style.pack(side=tk.LEFT, padx=(0, 5))
        
        self.style_image_label = tk.Label(style_button_frame, text="(선택 안 됨)", fg="gray", anchor="w")
        self.style_image_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=0.0):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_style_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_style_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 색상 전송 강도
        self.color_strength_label = create_slider(style_frame, "색상 강도:", self.color_strength, 0.0, 1.0, 0.01, "0%", default_value=0.0)
        
        # 텍스처 전송 강도
        self.texture_strength_label = create_slider(style_frame, "텍스처 강도:", self.texture_strength, 0.0, 1.0, 0.01, "0%", default_value=0.0)
        
        return style_frame
    
    def select_style_image(self):
        """스타일 이미지 선택"""
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            initial_dir = self.face_edit_dir
        else:
            initial_dir = kaodata_image.get_png_dir()
            if not os.path.exists(initial_dir):
                initial_dir = None
        
        file_path = filedialog.askopenfilename(
            title="스타일 이미지 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_path:
            self.style_image_path = file_path
            filename = os.path.basename(file_path)
            self.style_image_label.config(text=f"선택됨: {filename}", fg="green")
            
            # 이미지가 로드되어 있으면 스타일 적용
            if self.current_image is not None:
                self.apply_editing()
    
    def on_style_change(self, value=None):
        """스타일 전송 설정 변경 시 호출"""
        # 라벨 업데이트
        color_value = self.color_strength.get()
        self.color_strength_label.config(text=f"{int(color_value * 100)}%")
        
        texture_value = self.texture_strength.get()
        self.texture_strength_label.config(text=f"{int(texture_value * 100)}%")
        
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
