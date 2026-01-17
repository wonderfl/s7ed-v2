"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
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
        
        # 자동 정렬 체크박스 (숨김)
        # auto_align_frame = tk.Frame(alignment_frame)
        # auto_align_frame.pack(fill=tk.X)
        # 
        # auto_align_check = tk.Checkbutton(
        #     auto_align_frame,
        #     text="자동 정렬 (랜드마크 기반)",
        #     variable=self.auto_align,
        #     command=self.on_alignment_change
        # )
        # auto_align_check.pack(side=tk.LEFT)
        # 
        # # MediaPipe 사용 가능 여부 표시
        # if face_landmarks.is_available():
        #     tk.Label(auto_align_frame, text="(사용 가능)", fg="green").pack(side=tk.LEFT, padx=(10, 0))
        # else:
        #     tk.Label(auto_align_frame, text="(MediaPipe 필요)", fg="orange").pack(side=tk.LEFT, padx=(10, 0))
        
        # 체크박스 2x2 그리드로 배치 (줄 맞춤)
        # 첫 번째 줄
        checkbox_row1 = tk.Frame(alignment_frame)
        checkbox_row1.pack(fill=tk.X, pady=(5, 0))
        
        show_landmarks_check = tk.Checkbutton(
            checkbox_row1,
            text="랜드마크",
            variable=self.show_landmark_points,
            command=self.on_landmarks_display_change
        )
        show_landmarks_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        show_lines_check = tk.Checkbutton(
            checkbox_row1,
            text="연결선",
            variable=self.show_landmark_lines,
            command=self.on_landmarks_display_change
        )
        show_lines_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        show_polygons_check = tk.Checkbutton(
            checkbox_row1,
            text="폴리곤",
            variable=self.show_landmark_polygons,
            command=self.on_landmarks_display_change
        )
        show_polygons_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

        # 폴리곤 확장 레벨 선택
        expansion_frame = tk.Frame(checkbox_row1)
        expansion_frame.pack(side=tk.LEFT, anchor=tk.W)
        tk.Label(expansion_frame, text="확장:").pack(side=tk.LEFT, padx=(0, 5))
        expansion_spinbox = tk.Spinbox(
            expansion_frame,
            from_=0,
            to=5,
            width=3,
            textvariable=self.polygon_expansion_level,
            command=self.on_landmarks_display_change
        )
        expansion_spinbox.pack(side=tk.LEFT)        

       
        # 두 번째 줄
        checkbox_row2 = tk.Frame(alignment_frame)
        checkbox_row2.pack(fill=tk.X, pady=(5, 0))
        
        show_region_check = tk.Checkbutton(
            checkbox_row2,
            text="눈 영역",
            variable=self.show_eye_region,
            command=self.on_eye_region_display_change
        )
        show_region_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        show_lip_region_check = tk.Checkbutton(
            checkbox_row2,
            text="입술 영역",
            variable=self.show_lip_region,
            command=self.on_lip_region_display_change
        )
        show_lip_region_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

        individual_region_check = tk.Checkbutton(
            checkbox_row2,
            text="개별 적용",
            variable=self.use_individual_eye_region,  # 눈 영역 변수를 메인으로 사용
            command=self.on_individual_region_change
        )
        individual_region_check.pack(side=tk.LEFT, anchor=tk.W)        
        

        
        # 세 번째 줄 (눈 간격 조정)
        checkbox_row3 = tk.Frame(alignment_frame)
        checkbox_row3.pack(fill=tk.X, pady=(5, 0))
        
        eye_spacing_check = tk.Checkbutton(
            checkbox_row3,
            text="눈 간격 조정",
            variable=self.eye_spacing,
            command=self.on_eye_spacing_change
        )
        eye_spacing_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

        show_indices_check = tk.Checkbutton(
            checkbox_row3,
            text="인덱스 표시",
            variable=self.show_landmark_indices,
            command=self.on_landmarks_display_change
        )
        show_indices_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))        
        
        # 고급 모드 (랜드마크 직접 변형)
        use_landmark_warping_check = tk.Checkbutton(
            checkbox_row3,
            text="폴리곤 수정",
            variable=self.use_landmark_warping,
            command=self.on_morphing_change
        )
        use_landmark_warping_check.pack(side=tk.LEFT, anchor=tk.W)

        # scipy 사용 가능 여부 표시
        try:
            from scipy.spatial import Delaunay
            if face_landmarks.is_available():
                tk.Label(checkbox_row3, text="(사용 가능)", fg="green", font=("", 8)).pack(side=tk.LEFT, padx=(10, 0))
            else:
                tk.Label(checkbox_row3, text="(MediaPipe 필요)", fg="orange", font=("", 8)).pack(side=tk.LEFT, padx=(10, 0))
        except ImportError:
            tk.Label(checkbox_row3, text="(scipy 필요)", fg="orange", font=("", 8)).pack(side=tk.LEFT, padx=(10, 0))
    
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
        
        # 서브 탭 노트북 생성 (전체, 눈, 눈썹, 코, 입, 턱선, 윤곽)
        notebook = ttk.Notebook(morphing_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 각 탭 생성
        face_tab = self._create_face_tab(notebook)
        eye_tab = self._create_eye_tab(notebook)
        eyebrow_tab = self._create_eyebrow_tab(notebook)
        nose_tab = self._create_nose_tab(notebook)
        mouth_tab = self._create_mouth_tab(notebook)
        jaw_tab = self._create_jaw_tab(notebook)
        contour_tab = self._create_contour_tab(notebook)
        
        notebook.add(eye_tab, text="눈")
        notebook.add(eyebrow_tab, text="눈썹")
        notebook.add(nose_tab, text="코")
        notebook.add(mouth_tab, text="입")
        notebook.add(jaw_tab, text="턱선")
        notebook.add(contour_tab, text="윤곽")
        notebook.add(face_tab, text="전체")
        
        # 탭 변경 이벤트 핸들러 추가
        def on_tab_changed(event):
            selected_tab = event.widget.tab('current')['text']
            self.current_morphing_tab = selected_tab
            # 탭 변경 시 화면 갱신 (랜드마크, 연결선, 폴리곤 모두)
            if self.current_image is not None:
                # 이전 탭의 표시 내용을 지우고 새 탭의 내용으로 갱신
                self.update_face_features_display()
        
        notebook.bind('<<NotebookTabChanged>>', on_tab_changed)
        
        return morphing_frame
    
    
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
    
    def on_individual_region_change(self):
        """개별 적용 체크박스 변경 시 호출 (눈 영역 + 입술 영역 통합)"""
        # 눈 영역과 입술 영역을 동시에 동기화
        is_individual = self.use_individual_eye_region.get()
        self.use_individual_lip_region.set(is_individual)
        
        if not is_individual:
            # 개별 적용 비활성화: 왼쪽/윗입술 값들을 오른쪽/아래입술에도 동기화
            
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
            
            # 입술 영역 값 동기화
            self.lower_lip_region_padding_x.set(self.upper_lip_region_padding_x.get())
            self.lower_lip_region_padding_y.set(self.upper_lip_region_padding_y.get())
            self.lower_lip_region_offset_x.set(self.upper_lip_region_offset_x.get())
            self.lower_lip_region_offset_y.set(self.upper_lip_region_offset_y.get())
        
        # 라벨 업데이트 (동기화된 값 반영)
        self.on_morphing_change()
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            self.apply_editing()
            if self.show_eye_region.get():
                self.update_eye_region_display()
            if self.show_lip_region.get():
                self.update_lip_region_display()
    
    def on_eye_spacing_change(self):
        """눈 간격 조정 체크박스 변경 시 호출"""
        if self.eye_spacing.get():
            # 눈 간격 조정이 활성화되면 현재 왼쪽 눈 수평 값을 기준으로 오른쪽 눈을 반대로 동기화
            current_left_value = self.left_eye_position_x.get()
            self.right_eye_position_x.set(-current_left_value)
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def on_individual_region_change(self):
        """개별 적용 체크박스 변경 시 호출 (눈 영역 + 입술 영역 통합)"""
        # 눈 영역과 입술 영역을 동시에 동기화
        is_individual = self.use_individual_eye_region.get()
        self.use_individual_lip_region.set(is_individual)
        
        # 눈 영역 개별 적용 처리
        if not is_individual:
            # 동기화 모드: 왼쪽 눈 값을 오른쪽 눈에 복사
            self.right_eye_region_padding.set(self.left_eye_region_padding.get())
            self.right_eye_region_offset_x.set(self.left_eye_region_offset_x.get())
            self.right_eye_region_offset_y.set(self.left_eye_region_offset_y.get())
        
        # 입술 영역 개별 적용 처리
        if not is_individual:
            # 동기화 모드: 윗입술 값을 아래입술에 복사
            self.lower_lip_region_padding_x.set(self.upper_lip_region_padding_x.get())
            self.lower_lip_region_padding_y.set(self.upper_lip_region_padding_y.get())
            self.lower_lip_region_offset_x.set(self.upper_lip_region_offset_x.get())
            self.lower_lip_region_offset_y.set(self.upper_lip_region_offset_y.get())
        
        self.on_morphing_change()
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            self.apply_editing()
            if self.show_eye_region.get():
                self.update_eye_region_display()
            if self.show_lip_region.get():
                self.update_lip_region_display()
    
    def on_eye_region_display_change(self):
        """눈 영역 표시 옵션 변경 시 호출"""
        if self.current_image is not None:
            if self.show_eye_region.get():
                self.update_eye_region_display()
            else:
                # 눈 영역 표시 제거
                self.clear_eye_region_display()
    
    def on_lip_region_display_change(self):
        """입술 영역 표시 옵션 변경 시 호출"""
        if self.current_image is not None:
            if self.show_lip_region.get():
                self.update_lip_region_display()
            else:
                # 입술 영역 표시 제거
                self.clear_lip_region_display()
    
    def on_landmarks_display_change(self):
        """랜드마크 표시 옵션 변경 시 호출"""
        print(f"[얼굴편집] 랜드마크 표시 옵션 변경: 랜드마크={self.show_landmark_points.get() if hasattr(self, 'show_landmark_points') else False}, 연결선={self.show_landmark_lines.get() if hasattr(self, 'show_landmark_lines') else False}, 폴리곤={self.show_landmark_polygons.get() if hasattr(self, 'show_landmark_polygons') else False}")
        if self.current_image is not None:
            show_landmarks = self.show_landmark_points.get() if hasattr(self, 'show_landmark_points') else False
            show_lines = self.show_landmark_lines.get() if hasattr(self, 'show_landmark_lines') else False
            show_polygons = self.show_landmark_polygons.get() if hasattr(self, 'show_landmark_polygons') else False
            
            if show_landmarks or show_lines or show_polygons:
                # 랜드마크, 연결선, 또는 폴리곤이 표시되어야 하면 업데이트
                print(f"[얼굴편집] 랜드마크 표시 업데이트 호출")
                self.update_face_features_display()
            else:
                # 모두 체크 해제되어 있으면 랜드마크 표시 제거
                print(f"[얼굴편집] 랜드마크 표시 제거")
                self.clear_landmarks_display()
    
    def update_labels_only(self):
        """라벨만 업데이트 (슬라이더 드래그 중 호출)"""
        # 왼쪽/오른쪽 눈 라벨 업데이트 (항상 표시)
        left_eye_value = self.left_eye_size.get()
        self.left_eye_size_label.config(text=f"{int(left_eye_value * 100)}%")
        
        right_eye_value = self.right_eye_size.get()
        self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
        
        nose_value = self.nose_size.get()
        self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        # 입 편집 라벨 업데이트
        upper_lip_shape_value = self.upper_lip_shape.get()
        self.upper_lip_shape_label.config(text=f"{int(upper_lip_shape_value * 100)}%")
        
        lower_lip_shape_value = self.lower_lip_shape.get()
        self.lower_lip_shape_label.config(text=f"{int(lower_lip_shape_value * 100)}%")
        
        upper_lip_width_value = self.upper_lip_width.get()
        self.upper_lip_width_label.config(text=f"{int(upper_lip_width_value * 100)}%")
        
        lower_lip_width_value = self.lower_lip_width.get()
        self.lower_lip_width_label.config(text=f"{int(lower_lip_width_value * 100)}%")
        
        upper_lip_vertical_move_value = self.upper_lip_vertical_move.get()
        self.upper_lip_vertical_move_label.config(text=f"{int(upper_lip_vertical_move_value)}")
        
        lower_lip_vertical_move_value = self.lower_lip_vertical_move.get()
        self.lower_lip_vertical_move_label.config(text=f"{int(lower_lip_vertical_move_value)}")
        
        # 입술 영역 라벨 업데이트
        upper_lip_region_padding_x_value = self.upper_lip_region_padding_x.get()
        self.upper_lip_region_padding_x_label.config(text=f"{int(upper_lip_region_padding_x_value * 100)}%")
        
        upper_lip_region_padding_y_value = self.upper_lip_region_padding_y.get()
        self.upper_lip_region_padding_y_label.config(text=f"{int(upper_lip_region_padding_y_value * 100)}%")
        
        upper_lip_region_offset_x_value = self.upper_lip_region_offset_x.get()
        self.upper_lip_region_offset_x_label.config(text=f"{int(upper_lip_region_offset_x_value)}")
        
        upper_lip_region_offset_y_value = self.upper_lip_region_offset_y.get()
        self.upper_lip_region_offset_y_label.config(text=f"{int(upper_lip_region_offset_y_value)}")
        
        lower_lip_region_padding_x_value = self.lower_lip_region_padding_x.get()
        self.lower_lip_region_padding_x_label.config(text=f"{int(lower_lip_region_padding_x_value * 100)}%")
        
        lower_lip_region_padding_y_value = self.lower_lip_region_padding_y.get()
        self.lower_lip_region_padding_y_label.config(text=f"{int(lower_lip_region_padding_y_value * 100)}%")
        
        lower_lip_region_offset_x_value = self.lower_lip_region_offset_x.get()
        self.lower_lip_region_offset_x_label.config(text=f"{int(lower_lip_region_offset_x_value)}")
        
        lower_lip_region_offset_y_value = self.lower_lip_region_offset_y.get()
        self.lower_lip_region_offset_y_label.config(text=f"{int(lower_lip_region_offset_y_value)}")
        
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
        
        # 슬라이더 드래그 중 폴리곤 업데이트 (이미지 편집 없이 랜드마크만 계산)
        if self.current_image is not None:
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                self.update_polygons_only()
    
    def update_polygons_only(self):
        """폴리곤만 업데이트 (슬라이더 드래그 중 호출, 이미지 편집 없이 랜드마크만 계산)"""
        if self.current_image is None:
            return
        
        try:
            import utils.face_morphing as face_morphing
            import utils.face_landmarks as face_landmarks
            
            # 변형된 랜드마크 계산 (이미지 편집 없이)
            base_image = self.aligned_image if self.aligned_image is not None else self.current_image
            
            # 눈 편집 파라미터 결정
            if self.use_individual_eye_region.get():
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.right_eye_size.get()
            else:
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.left_eye_size.get()
            
            # 원본 랜드마크 가져오기 (항상 원본을 기준으로 변형)
            base_landmarks = None
            if hasattr(self, 'original_landmarks') and self.original_landmarks is not None:
                base_landmarks = self.original_landmarks
            else:
                # original_landmarks가 없으면 face_landmarks 사용 (없으면 감지)
                if self.face_landmarks is None:
                    self.face_landmarks, _ = face_landmarks.detect_face_landmarks(base_image)
                    # 원본 랜드마크 저장
                    if self.face_landmarks is not None:
                        self.original_landmarks = list(self.face_landmarks)
                base_landmarks = self.face_landmarks
            
            if base_landmarks is not None:
                # 변형된 랜드마크 계산 (항상 원본을 기준으로)
                transformed = face_morphing.transform_points_for_eye_size(
                    base_landmarks,
                    eye_size_ratio=1.0,
                    left_eye_size_ratio=left_eye_size,
                    right_eye_size_ratio=right_eye_size
                )
                
                # 눈 위치 변형
                transformed = face_morphing.transform_points_for_eye_position(
                    transformed,
                    left_eye_position_x=self.left_eye_position_x.get(),
                    right_eye_position_x=self.right_eye_position_x.get(),
                    left_eye_position_y=self.left_eye_position_y.get(),
                    right_eye_position_y=self.right_eye_position_y.get()
                )
                
                # 코 크기 변형
                transformed = face_morphing.transform_points_for_nose_size(
                    transformed,
                    nose_size_ratio=self.nose_size.get()
                )
                
                # 입술 변형
                transformed = face_morphing.transform_points_for_lip_shape(
                    transformed,
                    upper_lip_shape=self.upper_lip_shape.get(),
                    lower_lip_shape=self.lower_lip_shape.get()
                )
                transformed = face_morphing.transform_points_for_lip_width(
                    transformed,
                    upper_lip_width=self.upper_lip_width.get(),
                    lower_lip_width=self.lower_lip_width.get()
                )
                
                # custom_landmarks 업데이트 (폴리곤 표시용)
                self.custom_landmarks = transformed
                
                # 폴리곤만 다시 그리기 (전체 업데이트 대신)
                if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items_original):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items_original.clear()
                    if hasattr(self, 'polygon_point_map_original'):
                        self.polygon_point_map_original.clear()
                    
                    # 기존 랜드마크 포인트도 제거 (이전 크기의 포인트가 남아있을 수 있음)
                    if hasattr(self, 'landmarks_items_original'):
                        for item_id in list(self.landmarks_items_original):
                            try:
                                self.canvas_original.delete(item_id)
                            except:
                                pass
                        self.landmarks_items_original.clear()
                    
                    # 태그로도 제거 시도 (혹시 모를 경우 대비)
                    try:
                        for item_id in self.canvas_original.find_withtag("landmarks"):
                            try:
                                self.canvas_original.delete(item_id)
                            except:
                                pass
                    except:
                        pass
                    
                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        self._draw_landmark_polygons(
                            self.canvas_original,
                            self.current_image,
                            self.custom_landmarks,
                            self.canvas_original_pos_x,
                            self.canvas_original_pos_y,
                            self.landmark_polygon_items_original,
                            "green",
                            current_tab
                        )
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출 (슬라이더 드래그 종료 시 호출)"""
        # 라벨 업데이트
        self.update_labels_only()
        
        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        if self.current_image is not None:
            use_warping = getattr(self, 'use_landmark_warping', None)
            if use_warping is not None and hasattr(use_warping, 'get') and use_warping.get():
                # 고급 모드가 활성화되었고 커스텀 랜드마크가 있으면 적용
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    print(f"[얼굴편집] 고급 모드 활성화: 기존 랜드마크 변경사항 적용")
                    # apply_polygon_drag_final을 호출하여 기존 랜드마크 변경사항 적용
                    if hasattr(self, 'apply_polygon_drag_final'):
                        self.apply_polygon_drag_final()
                        # 이미지 업데이트 후 랜드마크 표시도 업데이트
                        if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                            self.update_face_features_display()
                        return  # 이미지 업데이트 완료
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()
            # 편집 적용 전에 현재 위치를 명시적으로 저장 (위치 유지)
            # 원본 이미지 위치를 먼저 확인
            if self.image_created_original is not None:
                try:
                    original_coords = self.canvas_original.coords(self.image_created_original)
                    if original_coords and len(original_coords) >= 2:
                        self.canvas_original_pos_x = original_coords[0]
                        self.canvas_original_pos_y = original_coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 원본 위치 저장 실패: {e}")
            
            # 편집된 이미지 위치도 저장 (원본과 동기화)
            if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                self.canvas_edited_pos_x = self.canvas_original_pos_x
                self.canvas_edited_pos_y = self.canvas_original_pos_y
            elif self.image_created_edited is not None:
                # 원본 위치가 없으면 편집된 이미지의 현재 위치를 유지
                try:
                    edited_coords = self.canvas_edited.coords(self.image_created_edited)
                    if edited_coords and len(edited_coords) >= 2:
                        self.canvas_edited_pos_x = edited_coords[0]
                        self.canvas_edited_pos_y = edited_coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 편집 위치 저장 실패: {e}")
            
            self.apply_editing()
            # 눈 영역 표시 업데이트
            if self.show_eye_region.get():
                self.update_eye_region_display()
            # 입술 영역 표시 업데이트
            if self.show_lip_region.get():
                self.update_lip_region_display()
            # 폴리곤 표시 업데이트 (custom_landmarks가 이미 update_polygons_only에서 업데이트되었으므로)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # custom_landmarks가 있으면 폴리곤만 다시 그리기
                if self.custom_landmarks is not None:
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items_original):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items_original.clear()
                    self.polygon_point_map_original.clear()
                    
                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        self._draw_landmark_polygons(
                            self.canvas_original,
                            self.current_image,
                            self.custom_landmarks,
                            self.canvas_original_pos_x,
                            self.canvas_original_pos_y,
                            self.landmark_polygon_items_original,
                            "green",
                            current_tab
                        )
                else:
                    # custom_landmarks가 없으면 전체 업데이트
                    self.update_face_features_display()
    
    def reset_morphing(self):
        """얼굴 특징 보정 값들을 모두 초기화"""
        self.eye_size.set(1.0)
        self.nose_size.set(1.0)
        self.upper_lip_shape.set(1.0)
        self.lower_lip_shape.set(1.0)
        self.upper_lip_width.set(1.0)
        self.lower_lip_width.set(1.0)
        self.upper_lip_vertical_move.set(0.0)
        self.lower_lip_vertical_move.set(0.0)
        
        # 입술 영역 조정 초기화
        self.upper_lip_region_padding_x.set(0.2)
        self.upper_lip_region_padding_y.set(0.3)
        self.lower_lip_region_padding_x.set(0.2)
        self.lower_lip_region_padding_y.set(0.3)
        self.upper_lip_region_offset_x.set(0.0)
        self.upper_lip_region_offset_y.set(0.0)
        self.lower_lip_region_offset_x.set(0.0)
        self.lower_lip_region_offset_y.set(0.0)
        self.jaw_size.set(0.0)
        self.face_width.set(1.0)
        self.face_height.set(1.0)
        
        # 눈 편집 고급 설정 초기화
        self.use_individual_eye_region.set(False)  # 눈 영역과 입술 영역 모두 통합된 변수
        self.use_landmark_warping.set(False)  # 랜드마크 직접 변형 모드 초기화
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
        self.on_individual_region_change()
        
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
            
            # 입 편집 파라미터 전달 (3가지: 윗입술 모양, 아랫입술 모양, 입 벌림 정도)
            # 폴리곤 기반 변형이 이미 적용되지 않은 경우에만 apply_all_adjustments 사용
            if 'result' not in locals() or result is None:
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
                upper_lip_shape=self.upper_lip_shape.get(),
                lower_lip_shape=self.lower_lip_shape.get(),
                upper_lip_width=self.upper_lip_width.get(),
                lower_lip_width=self.lower_lip_width.get(),
                upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
                lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
                use_individual_lip_region=self.use_individual_lip_region.get(),
                upper_lip_region_padding_x=self.upper_lip_region_padding_x.get(),
                upper_lip_region_padding_y=self.upper_lip_region_padding_y.get(),
                lower_lip_region_padding_x=self.lower_lip_region_padding_x.get(),
                lower_lip_region_padding_y=self.lower_lip_region_padding_y.get(),
                upper_lip_region_offset_x=self.upper_lip_region_offset_x.get(),
                upper_lip_region_offset_y=self.upper_lip_region_offset_y.get(),
                lower_lip_region_offset_x=self.lower_lip_region_offset_x.get(),
                lower_lip_region_offset_y=self.lower_lip_region_offset_y.get(),
                use_landmark_warping=self.use_landmark_warping.get(),
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
            
            # 변형된 랜드마크 계산 및 업데이트 (폴리곤 표시를 위해)
            import utils.face_landmarks as face_landmarks
            import utils.face_morphing as face_morphing
            
            # 원본 랜드마크 가져오기 (없으면 감지)
            if not hasattr(self, 'original_landmarks') or self.original_landmarks is None:
                if self.current_image is not None:
                    self.original_landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
            
            # face_landmarks가 없으면 원본 랜드마크 사용
            if self.face_landmarks is None:
                self.face_landmarks = list(self.original_landmarks) if self.original_landmarks else None
            
            if self.face_landmarks is not None and self.original_landmarks is not None:
                # 눈 크기 조정으로 변형된 랜드마크 계산
                if self.use_individual_eye_region.get():
                    left_eye_size = self.left_eye_size.get()
                    right_eye_size = self.right_eye_size.get()
                else:
                    left_eye_size = self.left_eye_size.get()
                    right_eye_size = self.left_eye_size.get()
                
                # 원본 랜드마크를 기준으로 변형된 랜드마크 계산
                transformed_landmarks = list(self.original_landmarks)
                if left_eye_size is not None or right_eye_size is not None:
                    left_ratio = left_eye_size if left_eye_size is not None else 1.0
                    right_ratio = right_eye_size if right_eye_size is not None else 1.0
                    if abs(left_ratio - 1.0) >= 0.01 or abs(right_ratio - 1.0) >= 0.01:
                        transformed_landmarks = face_morphing.transform_points_for_eye_size(
                            transformed_landmarks,
                            eye_size_ratio=1.0,
                            left_eye_size_ratio=left_eye_size,
                            right_eye_size_ratio=right_eye_size
                        )
                
                # 변형된 랜드마크 저장 (폴리곤 표시용)
                self.face_landmarks = transformed_landmarks
                # custom_landmarks도 업데이트 (슬라이더 변형을 우선 적용)
                # 슬라이더로 변형된 랜드마크를 custom_landmarks에 반영
                # 눈 크기 조정 등으로 변형된 랜드마크를 우선적으로 적용
                self.custom_landmarks = list(transformed_landmarks)
                
                # transformed_landmarks도 업데이트 (고급 모드 표시용)
                self.transformed_landmarks = transformed_landmarks
                
                # 폴리곤 기반 변형: 변형된 랜드마크로 이미지 변형
                # apply_all_adjustments 대신 morph_face_by_polygons 사용
                if self.original_landmarks is not None and self.custom_landmarks is not None:
                    result = face_morphing.morph_face_by_polygons(
                        base_image,  # 원본 이미지
                        self.original_landmarks,  # 원본 랜드마크
                        self.custom_landmarks,  # 변형된 랜드마크 (폴리곤으로 수정된 랜드마크)
                        selected_point_indices=None  # 모든 포인트 처리
                    )
                    
                    if result is not None:
                        # 편집된 이미지 업데이트
                        self.edited_image = result
                        # 나머지 편집(코, 입 등)은 기존 이미지에 적용
                        base_image = result
            
            # 입 편집 파라미터 전달 (3가지: 윗입술 모양, 아랫입술 모양, 입 벌림 정도)
            # 폴리곤 기반 변형이 이미 적용된 경우에도 코, 입, 턱, 얼굴 크기 등은 apply_all_adjustments로 처리
            # 눈 크기는 이미 morph_face_by_polygons로 처리되었으므로 None으로 설정
            if 'result' not in locals() or result is None:
                result = base_image
            
            # 코, 입, 턱, 얼굴 크기 등 나머지 편집 적용 (눈 크기는 이미 처리됨)
            result = face_morphing.apply_all_adjustments(
                result,  # 이미 처리된 이미지 (눈 크기 조정 포함)
                eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
                left_eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
                right_eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
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
                upper_lip_shape=self.upper_lip_shape.get(),
                lower_lip_shape=self.lower_lip_shape.get(),
                upper_lip_width=self.upper_lip_width.get(),
                lower_lip_width=self.lower_lip_width.get(),
                upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
                lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
                use_individual_lip_region=self.use_individual_lip_region.get(),
                upper_lip_region_padding_x=self.upper_lip_region_padding_x.get(),
                upper_lip_region_padding_y=self.upper_lip_region_padding_y.get(),
                lower_lip_region_padding_x=self.lower_lip_region_padding_x.get(),
                lower_lip_region_padding_y=self.lower_lip_region_padding_y.get(),
                upper_lip_region_offset_x=self.upper_lip_region_offset_x.get(),
                upper_lip_region_offset_y=self.upper_lip_region_offset_y.get(),
                lower_lip_region_offset_x=self.lower_lip_region_offset_x.get(),
                lower_lip_region_offset_y=self.lower_lip_region_offset_y.get(),
                use_landmark_warping=self.use_landmark_warping.get(),
                jaw_adjustment=self.jaw_size.get(),
                face_width=self.face_width.get(),
                face_height=self.face_height.get()
            )
            
        except Exception as e:
            print(f"[얼굴편집] 편집 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self.show_edited_preview()
