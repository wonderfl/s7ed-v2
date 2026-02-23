"""
얼굴 편집 패널 v2 - 전체 탭 전용 UI Mixin
전체 탭과 고급 모드에 집중한 단순화된 UI 구조
"""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


class UIMixin:
    """전체 탭 전용 UI 생성 기능 Mixin"""
    
    def _create_face_alignment_ui(self, parent):
        """얼굴 정렬 UI 생성"""
        alignment_frame = tk.LabelFrame(parent, text="얼굴 정렬", padx=5, pady=5)
        alignment_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 체크박스 2x2 그리드로 배치
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
        
        # 두 번째 줄
        checkbox_row2 = tk.Frame(alignment_frame)
        checkbox_row2.pack(fill=tk.X, pady=(5, 0))
        
        show_indices_check = tk.Checkbutton(
            checkbox_row2,
            text="인덱스",
            variable=self.show_landmark_indices,
            command=self.on_landmarks_display_change
        )
        show_indices_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        show_centers_check = tk.Checkbutton(
            checkbox_row2,
            text="중심점",
            variable=self.show_region_centers,
            command=self.on_landmarks_display_change
        )
        show_centers_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        # 고급 모드 옵션
        warping_check = tk.Checkbutton(
            checkbox_row2,
            text="고급 모드",
            variable=self.use_landmark_warping,
            command=self.on_landmarks_display_change
        )
        warping_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        guide_lines_check = tk.Checkbutton(
            checkbox_row2,
            text="가이드축",
            variable=self.use_guide_line_scaling,
            command=self.on_landmarks_display_change
        )
        guide_lines_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))
        
        return alignment_frame
    
    def _create_morphing_ui(self, parent):
        """얼굴 특징 보정 UI 생성 (전체 탭만)"""
        morphing_frame = tk.LabelFrame(parent, text="얼굴 특징 보정", padx=5, pady=5)
        morphing_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
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
        
        # 전체 탭만 있는 노트북 생성
        notebook = ttk.Notebook(morphing_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 전체 탭만 생성
        face_tab = self._create_face_tab(notebook)
        notebook.add(face_tab, text="전체")
        
        # 탭 변경 이벤트 (전체 탭만 있으므로 실제로는 발생하지 않음)
        def on_tab_changed(event):
            selected_tab = event.widget.tab('current')['text']
            self.current_morphing_tab = selected_tab
            if self.current_image is not None:
                self.update_face_features_display()
        
        notebook.bind('<<NotebookTabChanged>>', on_tab_changed)
        
        return morphing_frame
    
    def _create_face_features_ui(self, parent):
        """얼굴 특징 보정 UI 생성 (메서드 이름 호환성 유지)"""
        return self._create_morphing_ui(parent)
    
    def on_landmarks_display_change(self):
        """랜드마크 표시 변경 시 처리"""
        if self.current_image is not None:
            self.update_face_features_display()
    
    def reset_morphing(self):
        """얼굴 특징 보정 초기화"""
        try:
            # 모든 슬라이더를 기본값으로 리셋
            self.region_center_offset_x.set(0.0)
            self.region_center_offset_y.set(0.0)
            self.region_size_x.set(1.0)
            self.region_size_y.set(1.0)
            self.region_position_x.set(0.0)
            self.region_position_y.set(0.0)
            
            # 랜드마크 초기화
            if hasattr(self, 'landmark_manager'):
                self.landmark_manager.reset_custom_landmarks()
            
            # 편집된 이미지 초기화
            self.edited_image = None
            
            # 화면 갱신
            if self.current_image is not None:
                self.update_face_features_display()
            
            print("얼굴 편집 초기화 완료")
            
        except Exception as e:
            print(f"얼굴 편집 초기화 실패: {e}")
    
    def update_face_features_display(self):
        """얼굴 특징 보정 디스플레이 업데이트"""
        try:
            if self.current_image is None:
                return
            
            # 편집 적용
            self.on_morphing_change()
            
        except Exception as e:
            print(f"얼굴 특징 보정 디스플레이 업데이트 실패: {e}")
    
    def on_morphing_change(self):
        """얼굴 특징 보정 변경 시 처리"""
        print("UIMixin on_morphing_change called..")
        try:
            if self.current_image is None:
                return
            
            # 공통 슬라이더 직접 적용
            if hasattr(self, '_apply_common_sliders'):
                print("Calling _apply_common_sliders...")
                result = self._apply_common_sliders(self.current_image)
                if result is not None and result != self.current_image:
                    self.edited_image = result
                print("_apply_common_sliders completed")
            
            # 미리보기 업데이트
            self._refresh_face_edit_display(
                image=True,
                landmarks=True,
                overlays=True,
                guide_lines=True,
                force_original=False,
            )
            
        except Exception as e:
            print(f"얼굴 특징 보정 변경 처리 실패: {e}")
