"""
얼굴 편집 패널 - 전체 탭 전용 슬라이더 UI Mixin
전체 탭과 고급 모드에 집중한 단순화된 구조
"""
import tkinter as tk


class SliderUIMixin:
    """전체 탭 전용 슬라이더 UI 생성 기능 Mixin"""

    def _handle_slider_drag(self, event, scale, variable, label_text, value_label, default_label):
        """슬라이더 드래그 직접 처리"""
        try:
            slider_width = scale.winfo_width()
            click_x = event.x
            relative_x = max(0, min(click_x, slider_width))

            from_val = scale.cget("from")
            to_val = scale.cget("to")
            val = from_val + (to_val - from_val) * (relative_x / slider_width)

            variable.set(val)
            scale.set(val)

            if default_label.endswith("%"):
                value_label.config(text=f"{int(val * 100)}%")
            else:
                value_label.config(text=f"{int(val)}")

        except Exception:
            pass

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
            
            # value_label을 먼저 생성 (콜백 함수에서 사용하기 위해)
            value_label = tk.Label(frame, text=default_label, width=width)
            
            def on_slider_change(value):
                # 드래그 중에는 라벨만 업데이트 (성능 최적화)
                val = float(value)
                
                if default_label.endswith("%"):
                    value_label.config(text=f"{int(val * 100)}%")
                else:
                    value_label.config(text=f"{int(val)}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                print("on_slider_release called..")
                try:
                    print("Calling on_morphing_change...")
                    self.on_morphing_change()
                    print("on_morphing_change completed")
                except Exception as e:
                    print(f"on_morphing_change error: {e}")
                    import traceback
                    traceback.print_exc()
            
            def reset_slider(event):
                variable.set(default_value)
                # value_label도 직접 업데이트
                if default_label.endswith("%"):
                    value_label.config(text=f"{int(default_value * 100)}%")
                else:
                    value_label.config(text=f"{int(default_value)}")
                print("reset_slider called..")
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                length=scaled_length,
                showvalue=False,
                takefocus=1,
                state=tk.NORMAL,
                cursor="hand2"
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            # 슬라이더 상태 확인
            scale.config(state=tk.NORMAL)
            scale.update()
            
            # command 콜백 직접 설정
            scale.config(command=on_slider_change)
            
            # 드래그 이벤트 바인딩
            scale.bind("<B1-Motion>", lambda e: self._handle_slider_drag(e, scale, variable, label_text, value_label, default_label))
            scale.bind("<ButtonRelease-1>", on_slider_release)
            scale.bind("<ButtonRelease-3>", on_slider_release)
            
            value_label.pack(side=tk.LEFT)
            
            # Scale 위젯을 value_label에 속성으로 저장
            value_label.scale_widget = scale
            
            return value_label
        
        # 부위 선택 섹션
        region_frame = tk.LabelFrame(tab_frame, text="Region Selection", padx=5, pady=5)
        region_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        
        # MediaPipe 사용 가능 여부 확인
        try:
            import utils.face_landmarks as face_landmarks
            mediapipe_available = face_landmarks.is_available()
        except Exception:
            mediapipe_available = False
        
        # 체크박스 그리드 배치
        checkbox_frame = tk.Frame(region_frame)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 부위 선택 체크박스 생성
        def create_region_checkbox(parent, text, variable, row, col):
            check = tk.Checkbutton(parent, text=text, variable=variable)
            check.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            return check
        
        # 주요 부위 체크박스들 (전체 탭용) - 3줄 배치
        self.face_oval_check = create_region_checkbox(checkbox_frame, "Face Oval", self.show_face_oval, 0, 0)
        self.left_eye_check = create_region_checkbox(checkbox_frame, "Left Eye", self.show_left_eye, 0, 1)
        self.right_eye_check = create_region_checkbox(checkbox_frame, "Right Eye", self.show_right_eye, 0, 2)
        self.left_eyebrow_check = create_region_checkbox(checkbox_frame, "Left Eyebrow", self.show_left_eyebrow, 1, 0)
        self.right_eyebrow_check = create_region_checkbox(checkbox_frame, "Right Eyebrow", self.show_right_eyebrow, 1, 1)
        self.nose_check = create_region_checkbox(checkbox_frame, "Nose", self.show_nose, 1, 2)
        self.lips_check = create_region_checkbox(checkbox_frame, "Lips", self.show_lips, 2, 0)
        self.contours_check = create_region_checkbox(checkbox_frame, "Contours", self.show_contours, 2, 1)
        self.tesselation_check = create_region_checkbox(checkbox_frame, "Tesselation", self.show_tesselation, 2, 2)
        
        # Tesselation 상호 배타적 처리
        def handle_tesselation_exclusive():
            if self.show_tesselation.get():
                # Tesselation 선택 시 다른 부위 비활성화
                for check in [self.face_oval_check, self.left_eye_check, self.right_eye_check,
                             self.left_eyebrow_check, self.right_eyebrow_check, self.nose_check,
                             self.lips_check, self.contours_check]:
                    if check:
                        check.config(state=tk.DISABLED)
            else:
                # Tesselation 해제 시 다른 부위 활성화
                if mediapipe_available:
                    for check in [self.face_oval_check, self.left_eye_check, self.right_eye_check,
                                 self.left_eyebrow_check, self.right_eyebrow_check, self.nose_check,
                                 self.lips_check, self.contours_check]:
                        if check:
                            check.config(state=tk.NORMAL)
        
        def handle_individual_region_exclusive():
            has_individual_selected = (self.show_face_oval.get() or self.show_left_eye.get() or
                                      self.show_right_eye.get() or self.show_left_eyebrow.get() or
                                      self.show_right_eyebrow.get() or self.show_nose.get() or
                                      self.show_lips.get() or self.show_contours.get())
            
            if has_individual_selected:
                if self.tesselation_check:
                    self.tesselation_check.config(state=tk.DISABLED)
                    if self.show_tesselation.get():
                        self.show_tesselation.set(False)
            else:
                if self.tesselation_check and mediapipe_available:
                    self.tesselation_check.config(state=tk.NORMAL)
            for slider in [self.center_offset_x_label, self.center_offset_y_label, 
                          self.size_x_label, self.size_y_label, 
                          self.position_x_label, self.position_y_label,
                          self.polygon_expansion_label]:
                if slider and hasattr(slider, 'scale_widget'):
                    # 저장된 Scale 위젯에 state 설정
                    slider.scale_widget.config(state=tk.NORMAL if has_individual_selected else tk.DISABLED)
        
        # 개별 부위 체크박스에 이벤트 바인딩
        for check in [self.face_oval_check, self.left_eye_check, self.right_eye_check,
                     self.left_eyebrow_check, self.right_eyebrow_check, self.nose_check,
                     self.lips_check, self.contours_check]:
            if check:
                check.config(command=handle_tesselation_exclusive)
                check.config(command=handle_individual_region_exclusive)
        
        # MediaPipe가 없을 때 안내 메시지
        if not mediapipe_available:
            warning_label = tk.Label(checkbox_frame, text="MediaPipe not available - limited regions", fg="red")
            warning_label.grid(row=3, column=0, columnspan=3, pady=5)
        
        # 슬라이더 섹션
        slider_frame = tk.LabelFrame(tab_frame, text="Common Sliders", padx=5, pady=5)
        slider_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 공통 슬라이더들
        self.center_offset_x_label = create_slider(slider_frame, "Center Offset X", self.region_center_offset_x, -50, 50, 1, "0", 6, 0)
        self.center_offset_y_label = create_slider(slider_frame, "Center Offset Y", self.region_center_offset_y, -50, 50, 1, "0", 6, 0)
        self.size_x_label = create_slider(slider_frame, "Size X", self.region_size_x, 0.5, 2.0, 0.01, "100%", 6, 1.0)
        self.size_y_label = create_slider(slider_frame, "Size Y", self.region_size_y, 0.5, 2.0, 0.01, "100%", 6, 1.0)
        self.position_x_label = create_slider(slider_frame, "Position X", self.region_position_x, -50, 50, 1, "0", 6, 0)
        self.position_y_label = create_slider(slider_frame, "Position Y", self.region_position_y, -50, 50, 1, "0", 6, 0)
        
        # 폴리곤 확장 슬라이더
        self.polygon_expansion_label = create_slider(slider_frame, "Polygon Expansion", self.polygon_expansion_level, 0, 5, 1, "1", 6, 1)
        
        # 폴리곤 확장 슬라이더 변경 시 폴리곤 다시 그리기
        def on_polygon_expansion_change(value):
            # 폴리곤 다시 그리기
            if self.current_image is not None:
                self.update_face_features_display()
        
        # 폴리곤 확장 슬라이더에 이벤트 바인딩 (ButtonRelease-1 이벤트 사용)
        if hasattr(self.polygon_expansion_label, 'scale_widget'):
            # 기존 command는 그대로 두고, ButtonRelease-1 이벤트로 폴리곤 업데이트
            self.polygon_expansion_label.scale_widget.bind("<ButtonRelease-1>", lambda e: on_polygon_expansion_change(None))
            self.polygon_expansion_label.scale_widget.bind("<ButtonRelease-3>", lambda e: on_polygon_expansion_change(None))
        
        return tab_frame
