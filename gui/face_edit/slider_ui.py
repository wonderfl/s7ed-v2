"""
얼굴 편집 패널 - 슬라이더 UI 생성 Mixin
슬라이더 UI 생성 및 탭별 UI 구성을 담당
"""
import tkinter as tk


class SliderUIMixin:
    """슬라이더 UI 생성 기능 Mixin"""
    
    def _create_eye_tab(self, notebook):
        """눈 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수 (눈 크기 전용 - 동기화 처리를 위해)
        def create_eye_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 1.0  # 눈 크기 기본값
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_size.set(default_value)
                    else:
                        self.left_eye_size.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_eye_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈도 같이 움직임
                        self.right_eye_size.set(float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈도 같이 움직임
                        self.left_eye_size.set(float(value))
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                    # update_labels_only가 없으면 라벨만 업데이트
                    value_label.config(text=f"{int(float(value) * 100)}%")
            
            def on_eye_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_slider_release)
            
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수평 전용 - 반대 동기화 처리를 위해)
        def create_eye_position_x_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0  # 눈 위치 기본값
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                # 눈 간격 조정이 활성화되어 있으면 반대쪽 눈도 반대로 동기화
                if self.eye_spacing.get():
                    if is_left:
                        self.right_eye_position_x.set(-default_value)
                    else:
                        self.left_eye_position_x.set(-default_value)
                # 개별 조정 모드가 아니면 동기화
                elif not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_x.set(default_value)
                    else:
                        self.left_eye_position_x.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_eye_position_x_slider_change(value):
                # 눈 간격 조정이 활성화되어 있으면 반대쪽 눈도 반대로 동기화
                if self.eye_spacing.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈은 반대로
                        self.right_eye_position_x.set(-float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈은 반대로
                        self.left_eye_position_x.set(-float(value))
                # 개별 조정 모드가 아니면 동기화
                elif not self.use_individual_eye_region.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈도 같이 움직임
                        self.right_eye_position_x.set(float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈도 같이 움직임
                        self.left_eye_position_x.set(float(value))
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    value_label.config(text=f"{int(float(value))}")
            
            def on_eye_position_x_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_x_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_position_x_slider_release)
            
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수직 전용 - 동기화 처리를 위해)
        def create_eye_position_y_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0  # 눈 위치 기본값
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_y.set(default_value)
                    else:
                        self.left_eye_position_y.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_eye_position_y_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈도 같이 움직임
                        self.right_eye_position_y.set(float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈도 같이 움직임
                        self.left_eye_position_y.set(float(value))
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    value_label.config(text=f"{int(float(value))}")
            
            def on_eye_position_y_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_y_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_position_y_slider_release)
            
            return value_label
        
        # 눈 영역 크기 조절 슬라이더 생성 헬퍼 함수
        def create_eye_region_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=4, is_left=True, is_padding=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # 기본값 설정
            default_value = 0.3 if is_padding else 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        if is_padding:
                            self.right_eye_region_padding.set(default_value)
                        else:
                            # offset_x인지 offset_y인지 확인 필요
                            if variable == self.left_eye_region_offset_x:
                                self.right_eye_region_offset_x.set(default_value)
                            else:
                                self.right_eye_region_offset_y.set(default_value)
                    else:
                        if is_padding:
                            self.left_eye_region_padding.set(default_value)
                        else:
                            if variable == self.right_eye_region_offset_x:
                                self.left_eye_region_offset_x.set(default_value)
                            else:
                                self.left_eye_region_offset_y.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_eye_region_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        if is_padding:
                            self.right_eye_region_padding.set(float(value))
                        else:
                            # offset_x인지 offset_y인지 확인 필요
                            if variable == self.left_eye_region_offset_x:
                                self.right_eye_region_offset_x.set(float(value))
                            else:
                                self.right_eye_region_offset_y.set(float(value))
                    else:
                        if is_padding:
                            self.left_eye_region_padding.set(float(value))
                        else:
                            if variable == self.right_eye_region_offset_x:
                                self.left_eye_region_offset_x.set(float(value))
                            else:
                                self.left_eye_region_offset_y.set(float(value))
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_eye_region_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_region_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_region_slider_release)
            
            return value_label
        
        # ==============================
        # 1. 눈 영역 / 오프셋 조정 영역
        # ==============================
        eye_region_frame = tk.LabelFrame(tab_frame, text="눈 영역 / 오프셋", padx=5, pady=5)
        eye_region_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))
        
        # 눈 영역 크기 조절 슬라이더 (개별 적용)
        self.left_eye_region_padding_label = create_eye_region_slider(eye_region_frame, "왼쪽 영역크기:", self.left_eye_region_padding, 0.0, 1.0, 0.01, "30%", is_left=True, is_padding=True)        
        self.left_eye_region_offset_x_label = create_eye_region_slider(eye_region_frame, "왼쪽 영역수평:", self.left_eye_region_offset_x, -20.0, 20.0, 1.0, "0", is_left=True, is_padding=False)
        self.left_eye_region_offset_y_label = create_eye_region_slider(eye_region_frame, "왼쪽 영역수직:", self.left_eye_region_offset_y, -20.0, 20.0, 1.0, "0", is_left=True, is_padding=False)

        self.right_eye_region_padding_label = create_eye_region_slider(eye_region_frame, "오른쪽 영역크기:", self.right_eye_region_padding, 0.0, 1.0, 0.01, "30%", is_left=False, is_padding=True)        
        self.right_eye_region_offset_x_label = create_eye_region_slider(eye_region_frame, "오른쪽 영역수평:", self.right_eye_region_offset_x, -20.0, 20.0, 1.0, "0", is_left=False, is_padding=False)
        self.right_eye_region_offset_y_label = create_eye_region_slider(eye_region_frame, "오른쪽 영역수직:", self.right_eye_region_offset_y, -20.0, 20.0, 1.0, "0", is_left=False, is_padding=False)
        
        # ==============================
        # 2. 눈 모양 / 이동 조정 영역
        # ==============================
        eye_shape_frame = tk.LabelFrame(tab_frame, text="눈 모양 / 이동", padx=5, pady=5)
        eye_shape_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 0))
        
        # 왼쪽/오른쪽 눈 크기 슬라이더
        self.left_eye_size_label = create_eye_slider(eye_shape_frame, "왼쪽 눈 크기:", self.left_eye_size, 0.5, 2.0, 0.01, "100%", is_left=True)
        self.right_eye_size_label = create_eye_slider(eye_shape_frame, "오른쪽 눈 크기:", self.right_eye_size, 0.5, 2.0, 0.01, "100%", is_left=False)
        
        # 눈 위치 조정 (왼쪽/오른쪽 개별)
        self.left_eye_position_y_label = create_eye_position_y_slider(eye_shape_frame, "왼쪽 눈 수직:", self.left_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_y_label = create_eye_position_y_slider(eye_shape_frame, "오른쪽 눈 수직:", self.right_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=False)

        self.left_eye_position_x_label = create_eye_position_x_slider(eye_shape_frame, "왼쪽 눈 수평:", self.left_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_x_label = create_eye_position_x_slider(eye_shape_frame, "오른쪽 눈 수평:", self.right_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=False)
        
        return tab_frame

    def _create_nose_tab(self, notebook):
        """코 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        # 코 크기
        self.nose_size_label = create_slider(tab_frame, "코 크기:", self.nose_size, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        return tab_frame

    def _create_mouth_tab(self, notebook):
        """입 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=1.0):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        # ==============================
        # 1. 입술 영역 / 오프셋 조정 영역
        # ==============================
        lip_region_frame = tk.LabelFrame(tab_frame, text="입술 영역 / 오프셋", padx=5, pady=5)
        lip_region_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))

        # 입술 영역 슬라이더 생성 헬퍼 함수
        def create_lip_region_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=4, is_upper=True, is_padding_x=False, is_padding_y=False, is_offset=False):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            if is_padding_x or is_padding_y:
                default_value = 0.2 if is_padding_x else 0.3
            else:
                default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                if not self.use_individual_eye_region.get():  # 통합된 개별 적용 변수 사용
                    if is_upper:
                        if is_padding_x:
                            self.lower_lip_region_padding_x.set(default_value)
                        elif is_padding_y:
                            self.lower_lip_region_padding_y.set(default_value)
                        elif is_offset:
                            if variable == self.upper_lip_region_offset_x:
                                self.lower_lip_region_offset_x.set(default_value)
                            else:
                                self.lower_lip_region_offset_y.set(default_value)
                    else:
                        if is_padding_x:
                            self.upper_lip_region_padding_x.set(default_value)
                        elif is_padding_y:
                            self.upper_lip_region_padding_y.set(default_value)
                        elif is_offset:
                            if variable == self.lower_lip_region_offset_x:
                                self.upper_lip_region_offset_x.set(default_value)
                            else:
                                self.upper_lip_region_offset_y.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_lip_region_slider_change(value):
                if not self.use_individual_eye_region.get():  # 통합된 개별 적용 변수 사용
                    if is_upper:
                        if is_padding_x:
                            self.lower_lip_region_padding_x.set(float(value))
                        elif is_padding_y:
                            self.lower_lip_region_padding_y.set(float(value))
                        elif is_offset:
                            if variable == self.upper_lip_region_offset_x:
                                self.lower_lip_region_offset_x.set(float(value))
                            else:
                                self.lower_lip_region_offset_y.set(float(value))
                    else:
                        if is_padding_x:
                            self.upper_lip_region_padding_x.set(float(value))
                        elif is_padding_y:
                            self.upper_lip_region_padding_y.set(float(value))
                        elif is_offset:
                            if variable == self.lower_lip_region_offset_x:
                                self.upper_lip_region_offset_x.set(float(value))
                            else:
                                self.upper_lip_region_offset_y.set(float(value))
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_lip_region_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_lip_region_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_lip_region_slider_release)
            
            return value_label
        
        # 윗입술 영역 조정 슬라이더
        self.upper_lip_region_padding_x_label = create_lip_region_slider(lip_region_frame, "윗입술 영역가로:", self.upper_lip_region_padding_x, -1.0, 2.0, 0.01, "20%", is_upper=True, is_padding_x=True)
        self.upper_lip_region_padding_y_label = create_lip_region_slider(lip_region_frame, "윗입술 영역세로:", self.upper_lip_region_padding_y, -1.0, 2.0, 0.01, "30%", is_upper=True, is_padding_y=True)
        self.upper_lip_region_offset_x_label = create_lip_region_slider(lip_region_frame, "윗입술 영역수평:", self.upper_lip_region_offset_x, -50.0, 50.0, 1.0, "0", is_upper=True, is_offset=True)
        self.upper_lip_region_offset_y_label = create_lip_region_slider(lip_region_frame, "윗입술 영역수직:", self.upper_lip_region_offset_y, -50.0, 50.0, 1.0, "0", is_upper=True, is_offset=True)
        
        # 아래입술 영역 조정 슬라이더
        self.lower_lip_region_padding_x_label = create_lip_region_slider(lip_region_frame, "아래입술 영역가로:", self.lower_lip_region_padding_x, -1.0, 2.0, 0.01, "20%", is_upper=False, is_padding_x=True)
        self.lower_lip_region_padding_y_label = create_lip_region_slider(lip_region_frame, "아래입술 영역세로:", self.lower_lip_region_padding_y, -1.0, 2.0, 0.01, "30%", is_upper=False, is_padding_y=True)
        self.lower_lip_region_offset_x_label = create_lip_region_slider(lip_region_frame, "아래입술 영역수평:", self.lower_lip_region_offset_x, -50.0, 50.0, 1.0, "0", is_upper=False, is_offset=True)
        self.lower_lip_region_offset_y_label = create_lip_region_slider(lip_region_frame, "아래입술 영역수직:", self.lower_lip_region_offset_y, -50.0, 50.0, 1.0, "0", is_upper=False, is_offset=True)
        
        # ==============================
        # 2. 입술 모양 / 이동 조정 영역
        # ==============================
        lip_shape_frame = tk.LabelFrame(tab_frame, text="입술 모양 / 이동", padx=5, pady=5)
        lip_shape_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 0))

        # 입술 모양 조정 슬라이더 (6가지)
        # 1. 윗입술 모양 (두께)
        self.upper_lip_shape_label = create_slider(lip_shape_frame, "윗입술 모양:", self.upper_lip_shape, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        
        # 2. 아랫입술 모양 (두께)
        self.lower_lip_shape_label = create_slider(lip_shape_frame, "아랫입술 모양:", self.lower_lip_shape, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        
        # 3. 윗입술 너비
        self.upper_lip_width_label = create_slider(lip_shape_frame, "윗입술 너비:", self.upper_lip_width, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        
        # 4. 아랫입술 너비
        self.lower_lip_width_label = create_slider(lip_shape_frame, "아랫입술 너비:", self.lower_lip_width, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        
        # 5. 윗입술 수직 이동
        self.upper_lip_vertical_move_label = create_slider(lip_shape_frame, "윗입술 수직 이동:", self.upper_lip_vertical_move, -50.0, 50.0, 1.0, "0", default_value=0.0)
        
        # 6. 아랫입술 수직 이동
        self.lower_lip_vertical_move_label = create_slider(lip_shape_frame, "아랫입술 수직 이동:", self.lower_lip_vertical_move, -50.0, 50.0, 1.0, "0", default_value=0.0)
        
        return tab_frame

    def _create_contour_tab(self, notebook):
        """윤곽 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        return tab_frame

    def _create_face_tab(self, notebook):
        """전체 얼굴 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        # 얼굴 너비
        self.face_width_label = create_slider(tab_frame, "얼굴 너비:", self.face_width, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        # 얼굴 높이
        self.face_height_label = create_slider(tab_frame, "얼굴 높이:", self.face_height, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        return tab_frame

    def _create_eyebrow_tab(self, notebook):
        """눈썹 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        # 플레이스홀더 메시지 (향후 기능 추가 예정)
        placeholder_label = tk.Label(
            tab_frame,
            text="눈썹 편집 기능은 추후 추가 예정입니다.",
            fg="gray",
            font=("", 10)
        )
        placeholder_label.pack(pady=20)
        
        return tab_frame

    def _create_jaw_tab(self, notebook):
        """턱선 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                # 라벨 및 폴리곤 업데이트 (드래그 중 - 이미지 편집 적용 안 함)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 업데이트
                    val = float(value)
                    if default_label.endswith("%"):
                        value_label.config(text=f"{int(val * 100)}%")
                    else:
                        value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            
            return value_label
        
        # 턱선 조정
        self.jaw_size_label = create_slider(tab_frame, "턱선:", self.jaw_size, -50.0, 50.0, 1.0, "0", default_value=0.0)
        
        return tab_frame

