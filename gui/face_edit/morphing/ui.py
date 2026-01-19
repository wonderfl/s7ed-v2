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



class UIMixin:
    """UI 생성 기능 Mixin"""
    
    def _create_face_alignment_ui(self, parent):
        """얼굴 정렬 UI 생성 (나중에 랜드마크 기능 추가 시 구현)"""
        alignment_frame = tk.LabelFrame(parent, text="얼굴 정렬", padx=5, pady=5)
        alignment_frame.pack(fill=tk.X, pady=(0, 5))
        
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
            to=15,
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

        eye_spacing_check = tk.Checkbutton(
            checkbox_row2,
            text="눈 간격 조정",
            variable=self.eye_spacing,
            command=self.on_eye_spacing_change
        )
        eye_spacing_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

        individual_region_check = tk.Checkbutton(
            checkbox_row2,
            text="개별 적용",
            variable=self.use_individual_eye_region,  # 눈 영역 변수를 메인으로 사용
            command=self.on_individual_region_change
        )
        individual_region_check.pack(side=tk.LEFT, anchor=tk.W)        
        

        
        # 세 번째 줄
        checkbox_row3 = tk.Frame(alignment_frame)
        checkbox_row3.pack(fill=tk.X, pady=(5, 0))

        show_indices_check = tk.Checkbutton(
            checkbox_row3,
            text="인덱스 표시",
            variable=self.show_landmark_indices,
            command=self.on_landmarks_display_change
        )
        show_indices_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        show_center_check = tk.Checkbutton(
            checkbox_row3,
            text="센터 표시",
            variable=self.show_region_centers,
            command=self.on_landmarks_display_change
        )
        show_center_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))        
        
        # 고급 모드 (랜드마크 직접 변형)
        use_landmark_warping_check = tk.Checkbutton(
            checkbox_row3,
            text="폴리곤 맵핑",
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
        
        # 서브 탭 노트북 생성 (전체, 눈, 눈동자, 눈썹, 코, 입, 윤곽)
        notebook = ttk.Notebook(morphing_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 각 탭 생성
        face_tab = self._create_face_tab(notebook)
        eye_tab = self._create_eye_tab(notebook)
        iris_tab = self._create_iris_tab(notebook)
        eyebrow_tab = self._create_eyebrow_tab(notebook)
        nose_tab = self._create_nose_tab(notebook)
        mouth_tab = self._create_mouth_tab(notebook)
        contour_tab = self._create_contour_tab(notebook)
        
        notebook.add(face_tab, text="전체")
        notebook.add(eye_tab, text="눈")
        notebook.add(iris_tab, text="눈동자")
        notebook.add(eyebrow_tab, text="눈썹")
        notebook.add(nose_tab, text="코")
        notebook.add(mouth_tab, text="입")
        notebook.add(contour_tab, text="윤곽")
        
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
    
    
