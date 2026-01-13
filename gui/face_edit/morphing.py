"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 UI 및 로직을 담당
"""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform


class MorphingManagerMixin:
    """얼굴 특징 보정 관리 기능 Mixin"""
    
    def _create_face_alignment_ui(self, parent):
        """얼굴 정렬 UI 생성 (나중에 랜드마크 기능 추가 시 구현)"""
        alignment_frame = tk.LabelFrame(parent, text="얼굴 정렬", padx=5, pady=5)
        alignment_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 자동 정렬 체크박스
        auto_align_frame = tk.Frame(alignment_frame)
        auto_align_frame.pack(fill=tk.X)
        
        auto_align_check = tk.Checkbutton(
            auto_align_frame,
            text="자동 정렬 (랜드마크 기반)",
            variable=self.auto_align,
            command=self.on_alignment_change
        )
        auto_align_check.pack(side=tk.LEFT)
        
        # MediaPipe 사용 가능 여부 표시
        if face_landmarks.is_available():
            tk.Label(auto_align_frame, text="(사용 가능)", fg="green").pack(side=tk.LEFT, padx=(10, 0))
        else:
            tk.Label(auto_align_frame, text="(MediaPipe 필요)", fg="orange").pack(side=tk.LEFT, padx=(10, 0))
        
        # 눈 영역 개별 적용 체크박스 (눈 영역 표시 위에 배치)
        individual_region_frame = tk.Frame(alignment_frame)
        individual_region_frame.pack(fill=tk.X, pady=(5, 0))
        
        individual_region_check = tk.Checkbutton(
            individual_region_frame,
            text="개별 적용",
            variable=self.use_individual_eye_region,
            command=self.on_individual_eye_region_change
        )
        individual_region_check.pack(side=tk.LEFT)
        
        # 눈 영역 표시 옵션 (개별 적용 아래에 배치)
        eye_region_display_frame = tk.Frame(alignment_frame)
        eye_region_display_frame.pack(fill=tk.X, pady=(5, 0))
        
        show_region_check = tk.Checkbutton(
            eye_region_display_frame,
            text="눈 영역 표시",
            variable=self.show_eye_region,
            command=self.on_eye_region_display_change
        )
        show_region_check.pack(side=tk.LEFT)
        
        # 눈 간격 조정 체크박스 (눈 영역 표시 아래에 배치)
        eye_spacing_display_frame = tk.Frame(alignment_frame)
        eye_spacing_display_frame.pack(fill=tk.X, pady=(5, 0))
        
        eye_spacing_check = tk.Checkbutton(
            eye_spacing_display_frame,
            text="눈 간격 조정",
            variable=self.eye_spacing,
            command=self.on_eye_spacing_change
        )
        eye_spacing_check.pack(side=tk.LEFT)
    
    def _create_face_morphing_ui(self, parent):
        """얼굴 특징 보정 UI 생성 (탭 구조)"""
        # parent는 이미 탭 노트북이므로 프레임만 생성
        morphing_frame = tk.Frame(parent, padx=5, pady=5)
        
        # 초기화 버튼
        reset_button_frame = tk.Frame(morphing_frame)
        reset_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_reset = tk.Button(
            reset_button_frame,
            text="초기화",
            command=self.reset_morphing,
            width=10,
            bg="#FF9800",
            fg="white"
        )
        btn_reset.pack(side=tk.LEFT)
        
        # 서브 탭 노트북 생성 (눈, 코, 입, 윤곽)
        notebook = ttk.Notebook(morphing_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 각 탭 생성
        eye_tab = self._create_eye_tab(notebook)
        nose_tab = self._create_nose_tab(notebook)
        mouth_tab = self._create_mouth_tab(notebook)
        contour_tab = self._create_contour_tab(notebook)
        
        notebook.add(eye_tab, text="눈")
        notebook.add(nose_tab, text="코")
        notebook.add(mouth_tab, text="입")
        notebook.add(contour_tab, text="윤곽")
        
        return morphing_frame
    
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
            
            def on_eye_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈도 같이 움직임
                        self.right_eye_size.set(float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈도 같이 움직임
                        self.left_eye_size.set(float(value))
                # 일반 morphing change 호출
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
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
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
                # 일반 morphing change 호출
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
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
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
            
            def on_eye_position_y_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        # 왼쪽 눈 슬라이더를 움직이면 오른쪽 눈도 같이 움직임
                        self.right_eye_position_y.set(float(value))
                    else:
                        # 오른쪽 눈 슬라이더를 움직이면 왼쪽 눈도 같이 움직임
                        self.left_eye_position_y.set(float(value))
                # 일반 morphing change 호출
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
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
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
                # 일반 morphing change 호출
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
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 왼쪽/오른쪽 눈 크기 슬라이더
        self.left_eye_size_label = create_eye_slider(tab_frame, "왼쪽 눈 크기:", self.left_eye_size, 0.5, 2.0, 0.01, "100%", is_left=True)
        self.right_eye_size_label = create_eye_slider(tab_frame, "오른쪽 눈 크기:", self.right_eye_size, 0.5, 2.0, 0.01, "100%", is_left=False)
        
        # 눈 위치 조정 (왼쪽/오른쪽 개별)
        self.left_eye_position_y_label = create_eye_position_y_slider(tab_frame, "왼쪽 눈 수직:", self.left_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_y_label = create_eye_position_y_slider(tab_frame, "오른쪽 눈 수직:", self.right_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=False)

        self.left_eye_position_x_label = create_eye_position_x_slider(tab_frame, "왼쪽 눈 수평:", self.left_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_x_label = create_eye_position_x_slider(tab_frame, "오른쪽 눈 수평:", self.right_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=False)
        
        # 눈 영역 크기 조절 슬라이더 (개별 적용)
        self.left_eye_region_padding_label = create_eye_region_slider(tab_frame, "왼쪽 영역크기:", self.left_eye_region_padding, 0.0, 1.0, 0.01, "30%", is_left=True, is_padding=True)        
        self.left_eye_region_offset_x_label = create_eye_region_slider(tab_frame, "왼쪽 영역수평:", self.left_eye_region_offset_x, -20.0, 20.0, 1.0, "0", is_left=True, is_padding=False)
        self.left_eye_region_offset_y_label = create_eye_region_slider(tab_frame, "왼쪽 영역수직:", self.left_eye_region_offset_y, -20.0, 20.0, 1.0, "0", is_left=True, is_padding=False)

        self.right_eye_region_padding_label = create_eye_region_slider(tab_frame, "오른쪽 영역크기:", self.right_eye_region_padding, 0.0, 1.0, 0.01, "30%", is_left=False, is_padding=True)        
        self.right_eye_region_offset_x_label = create_eye_region_slider(tab_frame, "오른쪽 영역수평:", self.right_eye_region_offset_x, -20.0, 20.0, 1.0, "0", is_left=False, is_padding=False)
        self.right_eye_region_offset_y_label = create_eye_region_slider(tab_frame, "오른쪽 영역수직:", self.right_eye_region_offset_y, -20.0, 20.0, 1.0, "0", is_left=False, is_padding=False)
        
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
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_morphing_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 코 크기
        self.nose_size_label = create_slider(tab_frame, "코 크기:", self.nose_size, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        return tab_frame
    
    def _create_mouth_tab(self, notebook):
        """입 탭 UI 생성 (플레이스홀더)"""
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        # 플레이스홀더 메시지
        placeholder_label = tk.Label(
            tab_frame,
            text="입 편집 기능은 추후 추가 예정입니다.",
            fg="gray",
            font=("", 10)
        )
        placeholder_label.pack(expand=True)
        
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
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_morphing_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 0))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 턱선 조정
        self.jaw_size_label = create_slider(tab_frame, "턱선:", self.jaw_size, -50.0, 50.0, 1.0, "0", default_value=0.0)
        
        # 얼굴 너비
        self.face_width_label = create_slider(tab_frame, "얼굴 너비:", self.face_width, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        # 얼굴 높이
        self.face_height_label = create_slider(tab_frame, "얼굴 높이:", self.face_height, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        
        return tab_frame
    
    def on_alignment_change(self):
        """얼굴 정렬 설정 변경 시 호출"""
        if self.current_image is None:
            return
        
        if self.auto_align.get():
            # 정렬 활성화: 정렬 적용
            self.apply_alignment()
        else:
            # 정렬 비활성화: 정렬된 이미지 제거하고 원본 기반으로 편집
            self.aligned_image = None
            self.apply_editing()
            self.show_original_preview()
            self.show_edited_preview()
    
    def apply_alignment(self):
        """얼굴 정렬 적용"""
        if self.current_image is None:
            return
        
        if not face_landmarks.is_available():
            self.status_label.config(text="경고: MediaPipe가 설치되지 않았습니다.", fg="orange")
            # MediaPipe가 없어도 이미지는 로드
            self.aligned_image = None
            self.edited_image = self.current_image.copy()
            # 편집 적용 (정렬 없이)
            self.apply_editing()
            return
        
        try:
            # 얼굴 정렬 (원본 이미지는 변경하지 않음)
            aligned_image, angle = face_landmarks.align_face(self.current_image)
            
            # 정렬된 이미지를 별도로 저장 (편집의 기반)
            self.aligned_image = aligned_image.copy()
            
            # 편집 적용 (정렬된 이미지를 기반으로)
            self.apply_editing()
            
            # 미리보기 업데이트
            self.show_original_preview()
            self.show_edited_preview()
            
            if abs(angle) > 0.1:
                self.status_label.config(text=f"얼굴 정렬 완료 (회전: {angle:.1f}도)", fg="green")
            else:
                self.status_label.config(text="얼굴 정렬 완료 (이미 정렬됨)", fg="green")
                
        except Exception as e:
            print(f"[얼굴편집] 얼굴 정렬 실패: {e}")
            self.status_label.config(text=f"얼굴 정렬 실패: {e}", fg="red")
            # 정렬 실패 시 원본 이미지 사용
            self.aligned_image = None
            self.edited_image = self.current_image.copy()
            # 편집 적용 (정렬 없이)
            self.apply_editing()
    
    def on_individual_eye_region_change(self):
        """개별 적용 모드 변경 시 호출 (눈 크기/위치 및 눈 영역 모두 통합)"""
        if not self.use_individual_eye_region.get():
            # 개별 적용 비활성화: 왼쪽 눈 값들을 오른쪽 눈에도 동기화
            
            # 눈 크기 동기화
            current_left_eye_size = self.left_eye_size.get()
            self.right_eye_size.set(current_left_eye_size)
            
            # 눈 수직 위치 동기화
            current_left_eye_position_y = self.left_eye_position_y.get()
            self.right_eye_position_y.set(current_left_eye_position_y)
            
            # 눈 수평 위치 동기화 (눈 간격 조정이 활성화되어 있지 않을 때만)
            if not self.eye_spacing.get():
                current_left_eye_position_x = self.left_eye_position_x.get()
                self.right_eye_position_x.set(current_left_eye_position_x)
            
            # 눈 영역 값 동기화
            self.right_eye_region_padding.set(self.left_eye_region_padding.get())
            self.right_eye_region_offset_x.set(self.left_eye_region_offset_x.get())
            self.right_eye_region_offset_y.set(self.left_eye_region_offset_y.get())
        
        # 라벨 업데이트 (동기화된 값 반영)
        self.on_morphing_change()
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            self.apply_editing()
            if self.show_eye_region.get():
                self.update_eye_region_display()
    
    def on_eye_spacing_change(self):
        """눈 간격 조정 체크박스 변경 시 호출"""
        if self.eye_spacing.get():
            # 눈 간격 조정이 활성화되면 현재 왼쪽 눈 수평 값을 기준으로 오른쪽 눈을 반대로 동기화
            current_left_value = self.left_eye_position_x.get()
            self.right_eye_position_x.set(-current_left_value)
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def on_eye_region_display_change(self):
        """눈 영역 표시 옵션 변경 시 호출"""
        if self.current_image is not None:
            if self.show_eye_region.get():
                self.update_eye_region_display()
            else:
                # 눈 영역 표시 제거
                self.clear_eye_region_display()
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출"""
        # 왼쪽/오른쪽 눈 라벨 업데이트 (항상 표시)
        left_eye_value = self.left_eye_size.get()
        self.left_eye_size_label.config(text=f"{int(left_eye_value * 100)}%")
        
        right_eye_value = self.right_eye_size.get()
        self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
        
        nose_value = self.nose_size.get()
        self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        jaw_value = self.jaw_size.get()
        self.jaw_size_label.config(text=f"{int(jaw_value)}")
        
        face_width_value = self.face_width.get()
        self.face_width_label.config(text=f"{int(face_width_value * 100)}%")
        
        face_height_value = self.face_height.get()
        self.face_height_label.config(text=f"{int(face_height_value * 100)}%")
        
        # 눈 위치 라벨 업데이트 (왼쪽/오른쪽 개별)
        left_eye_position_y_value = self.left_eye_position_y.get()
        self.left_eye_position_y_label.config(text=f"{int(left_eye_position_y_value)}")
        
        right_eye_position_y_value = self.right_eye_position_y.get()
        self.right_eye_position_y_label.config(text=f"{int(right_eye_position_y_value)}")
        
        left_eye_position_x_value = self.left_eye_position_x.get()
        self.left_eye_position_x_label.config(text=f"{int(left_eye_position_x_value)}")
        
        right_eye_position_x_value = self.right_eye_position_x.get()
        self.right_eye_position_x_label.config(text=f"{int(right_eye_position_x_value)}")
        
        # 눈 영역 라벨 업데이트 (개별 적용)
        left_eye_region_padding_value = self.left_eye_region_padding.get()
        self.left_eye_region_padding_label.config(text=f"{int(left_eye_region_padding_value * 100)}%")
        
        right_eye_region_padding_value = self.right_eye_region_padding.get()
        self.right_eye_region_padding_label.config(text=f"{int(right_eye_region_padding_value * 100)}%")
        
        # 눈 영역 위치 라벨 업데이트 (개별 적용)
        left_eye_region_offset_x_value = self.left_eye_region_offset_x.get()
        self.left_eye_region_offset_x_label.config(text=f"{int(left_eye_region_offset_x_value)}")
        
        left_eye_region_offset_y_value = self.left_eye_region_offset_y.get()
        self.left_eye_region_offset_y_label.config(text=f"{int(left_eye_region_offset_y_value)}")
        
        right_eye_region_offset_x_value = self.right_eye_region_offset_x.get()
        self.right_eye_region_offset_x_label.config(text=f"{int(right_eye_region_offset_x_value)}")
        
        right_eye_region_offset_y_value = self.right_eye_region_offset_y.get()
        self.right_eye_region_offset_y_label.config(text=f"{int(right_eye_region_offset_y_value)}")
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            self.apply_editing()
            # 눈 영역 표시 업데이트
            if self.show_eye_region.get():
                self.update_eye_region_display()
    
    def reset_morphing(self):
        """얼굴 특징 보정 값들을 모두 초기화"""
        self.eye_size.set(1.0)
        self.nose_size.set(1.0)
        self.jaw_size.set(0.0)
        self.face_width.set(1.0)
        self.face_height.set(1.0)
        
        # 눈 편집 고급 설정 초기화
        self.use_individual_eye_region.set(False)
        self.left_eye_size.set(1.0)
        self.right_eye_size.set(1.0)
        self.eye_spacing.set(False)
        self.left_eye_position_y.set(0.0)
        self.right_eye_position_y.set(0.0)
        self.left_eye_position_x.set(0.0)
        self.right_eye_position_x.set(0.0)
        self.show_eye_region.set(True)  # 기본값: True
        self.eye_region_padding.set(0.3)
        self.left_eye_region_padding.set(0.3)
        self.right_eye_region_padding.set(0.3)
        self.eye_region_offset_x.set(0.0)
        self.eye_region_offset_y.set(0.0)
        self.left_eye_region_offset_x.set(0.0)
        self.left_eye_region_offset_y.set(0.0)
        self.right_eye_region_offset_x.set(0.0)
        self.right_eye_region_offset_y.set(0.0)
        
        # UI 업데이트 (개별 적용 모드 변경)
        self.on_individual_eye_region_change()
        
        # 라벨 업데이트
        self.on_morphing_change()
        
        # 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def apply_editing(self):
        """편집 적용"""
        if self.current_image is None:
            return
        
        try:
            # 처리 순서: 정렬 → 특징 보정 → 스타일 전송 → 나이 변환
            # 편집은 항상 정렬된 이미지(또는 원본)를 기반으로 처음부터 다시 적용
            # aligned_image가 있으면 정렬된 이미지 사용, 없으면 원본 이미지 사용
            base_image = self.aligned_image if self.aligned_image is not None else self.current_image
            
            # 1. 얼굴 특징 보정 적용
            # 눈 편집 파라미터 결정 (항상 왼쪽/오른쪽 눈 크기 사용)
            if self.use_individual_eye_region.get():
                # 개별 적용 모드: 각각 독립적으로 조정
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.right_eye_size.get()
            else:
                # 동기화 모드: 왼쪽 눈 크기를 기준으로 오른쪽도 동일하게 (이미 슬라이더에서 동기화됨)
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.left_eye_size.get()  # 동기화되어 있지만 명시적으로 설정
            
            # 눈 영역 파라미터 결정 (개별 적용 여부에 따라)
            if self.use_individual_eye_region.get():
                # 개별 적용 모드: 개별 파라미터 전달
                left_eye_region_padding = self.left_eye_region_padding.get()
                right_eye_region_padding = self.right_eye_region_padding.get()
                left_eye_region_offset_x = self.left_eye_region_offset_x.get()
                left_eye_region_offset_y = self.left_eye_region_offset_y.get()
                right_eye_region_offset_x = self.right_eye_region_offset_x.get()
                right_eye_region_offset_y = self.right_eye_region_offset_y.get()
                # 기본 파라미터는 None으로 설정 (개별 파라미터 사용)
                eye_region_padding = None
                eye_region_offset_x = None
                eye_region_offset_y = None
            else:
                # 동기화 모드: 기본 파라미터만 사용 (왼쪽 눈 영역 값을 기준)
                eye_region_padding = self.left_eye_region_padding.get()
                eye_region_offset_x = self.left_eye_region_offset_x.get()
                eye_region_offset_y = self.left_eye_region_offset_y.get()
                # 개별 파라미터는 None으로 설정 (기본 파라미터 사용)
                left_eye_region_padding = None
                right_eye_region_padding = None
                left_eye_region_offset_x = None
                left_eye_region_offset_y = None
                right_eye_region_offset_x = None
                right_eye_region_offset_y = None
            
            result = face_morphing.apply_all_adjustments(
                base_image,
                eye_size=None,  # 항상 left_eye_size, right_eye_size 사용
                left_eye_size=left_eye_size,
                right_eye_size=right_eye_size,
                eye_spacing=self.eye_spacing.get(),  # Boolean: 눈 간격 조정 활성화 여부
                left_eye_position_y=self.left_eye_position_y.get(),
                right_eye_position_y=self.right_eye_position_y.get(),
                left_eye_position_x=self.left_eye_position_x.get(),
                right_eye_position_x=self.right_eye_position_x.get(),
                eye_region_padding=eye_region_padding,
                eye_region_offset_x=eye_region_offset_x,
                eye_region_offset_y=eye_region_offset_y,
                left_eye_region_padding=left_eye_region_padding,
                right_eye_region_padding=right_eye_region_padding,
                left_eye_region_offset_x=left_eye_region_offset_x,
                left_eye_region_offset_y=left_eye_region_offset_y,
                right_eye_region_offset_x=right_eye_region_offset_x,
                right_eye_region_offset_y=right_eye_region_offset_y,
                nose_size=self.nose_size.get(),
                jaw_adjustment=self.jaw_size.get(),
                face_width=self.face_width.get(),
                face_height=self.face_height.get()
            )
            
            # 2. 스타일 전송 적용
            if self.style_image_path and os.path.exists(self.style_image_path):
                try:
                    style_image = Image.open(self.style_image_path)
                    color_strength = self.color_strength.get()
                    texture_strength = self.texture_strength.get()
                    
                    if color_strength > 0.0 or texture_strength > 0.0:
                        result = style_transfer.transfer_style(
                            style_image,
                            result,
                            color_strength=color_strength,
                            texture_strength=texture_strength
                        )
                except Exception as e:
                    print(f"[얼굴편집] 스타일 전송 실패: {e}")
            
            # 3. 나이 변환 적용
            age_adjustment = self.age_adjustment.get()
            if abs(age_adjustment) >= 1.0:
                result = face_transform.transform_age(result, age_adjustment=int(age_adjustment))
            
            self.edited_image = result
            
            # 미리보기 업데이트
            self.show_edited_preview()
            
            # 눈 영역 표시 업데이트 (편집된 이미지의 실제 적용 영역 표시)
            if self.show_eye_region.get():
                self.update_eye_region_display()
            
        except Exception as e:
            print(f"[얼굴편집] 편집 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self.show_edited_preview()
