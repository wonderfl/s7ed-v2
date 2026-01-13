"""
얼굴 편집 패널 - 나이 변환 Mixin
나이 변환 관련 기능을 담당
"""
import tkinter as tk


class AgeManagerMixin:
    """나이 변환 관리 기능 Mixin"""
    
    def _create_age_transform_ui(self, parent):
        """나이 변환 UI 생성 (탭용)"""
        # parent는 이미 탭 노트북이므로 프레임만 생성
        age_frame = tk.Frame(parent, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 10
        
        # 초기화 버튼
        reset_button_frame = tk.Frame(age_frame)
        reset_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_reset = tk.Button(
            reset_button_frame,
            text="초기화",
            command=self.reset_age,
            width=10,
            bg="#FF9800",
            fg="white"
        )
        btn_reset.pack(side=tk.LEFT)
        
        # 나이 조정 슬라이더
        frame = tk.Frame(age_frame)
        frame.pack(fill=tk.X)
        
        default_age_value = 0.0
        
        title_label = tk.Label(frame, text="나이 조정:", width=label_width, anchor="e", cursor="hand2")
        title_label.pack(side=tk.LEFT, padx=(0, 5))
        
        def reset_age_slider(event):
            self.age_adjustment.set(default_age_value)
            self.on_age_change()
        
        title_label.bind("<Button-1>", reset_age_slider)
        
        age_scale = tk.Scale(
            frame,
            from_=-50.0,
            to=50.0,
            resolution=1.0,
            orient=tk.HORIZONTAL,
            variable=self.age_adjustment,
            command=self.on_age_change,
            length=scaled_length,
            showvalue=False
        )
        age_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.age_label = tk.Label(frame, text="0세", width=8)
        self.age_label.pack(side=tk.LEFT)
        
        # 설명 라벨
        tk.Label(age_frame, text="(음수=어리게, 양수=늙게)", fg="gray", font=("", 8)).pack()
        
        return age_frame
    
    def on_age_change(self, value=None):
        """나이 변환 설정 변경 시 호출"""
        # 라벨 업데이트
        age_value = self.age_adjustment.get()
        if age_value < 0:
            self.age_label.config(text=f"{int(age_value)}세", fg="blue")
        elif age_value > 0:
            self.age_label.config(text=f"+{int(age_value)}세", fg="red")
        else:
            self.age_label.config(text="0세", fg="black")
        
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def reset_age(self):
        """나이 변환 값 초기화"""
        self.age_adjustment.set(0.0)
        self.on_age_change()
        
        # 편집 적용
        if self.current_image is not None:
            self.apply_editing()
