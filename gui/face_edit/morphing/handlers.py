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



class HandlersMixin:
    """이벤트 핸들러 기능 Mixin"""
    
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
    
    def on_region_selection_change(self):
        """부위 선택 변경 시 호출"""
        # 슬라이더 상태 업데이트
        if hasattr(self, 'update_region_slider_state'):
            self.update_region_slider_state()
        
        # 전체 탭일 때만 부위 선택이 적용됨
        if self.current_morphing_tab == "전체":
            # 랜드마크 표시 업데이트
            if self.current_image is not None:
                self.update_face_features_display()
    
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
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출 (슬라이더 드래그 종료 시 호출)"""
        # 라벨 업데이트
        self.update_labels_only()
        
        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        # 하지만 공통 슬라이더는 항상 적용되어야 하므로 return하지 않음
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
                        # return 제거: 공통 슬라이더도 적용하기 위해 계속 진행
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
            # 고급 모드에서 Tesselation 선택 시에는 update_polygons_only를 호출하지 않음
            # (공통 슬라이더로 직접 변형하므로 중복 변형 방지)
            use_warping = getattr(self, 'use_landmark_warping', None)
            is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
            is_advanced_tesselation = (use_warping is not None and hasattr(use_warping, 'get') and use_warping.get() and is_tesselation_selected)
            
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                if hasattr(self, 'update_polygons_only') and not is_advanced_tesselation:
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
            
            # 고급 모드가 아닐 때만 apply_editing 호출 (고급 모드는 이미 apply_polygon_drag_final에서 처리됨)
            use_warping = getattr(self, 'use_landmark_warping', None)
            if use_warping is None or not (hasattr(use_warping, 'get') and use_warping.get() and 
                                           hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None):
                # 일반 모드: apply_editing 호출 (공통 슬라이더 포함)
                self.apply_editing()
            else:
                # 고급 모드: apply_polygon_drag_final에서 랜드마크 변형 적용 후, 스타일 전송/나이 변환/공통 슬라이더도 적용
                if hasattr(self, 'edited_image') and self.edited_image is not None:
                    result = self.edited_image
                    
                    # 스타일 전송 적용
                    import utils.style_transfer as style_transfer
                    import os
                    if hasattr(self, 'style_image_path') and self.style_image_path and os.path.exists(self.style_image_path):
                        try:
                            from PIL import Image
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
                    
                    # 나이 변환 적용
                    import utils.face_transform as face_transform
                    age_adjustment = self.age_adjustment.get()
                    if abs(age_adjustment) >= 1.0:
                        result = face_transform.transform_age(result, age_adjustment=int(age_adjustment))
                    
                    # 공통 슬라이더 적용
                    print(f"[얼굴편집] 고급 모드: 공통 슬라이더 적용 시작")
                    # base_image를 전달하여 슬라이더가 모두 기본값일 때 원본으로 복원할 수 있도록 함
                    base_image = self.aligned_image if hasattr(self, 'aligned_image') and self.aligned_image is not None else self.current_image
                    result = self._apply_common_sliders(result, base_image=base_image)
                    
                    if result is not None:
                        self.edited_image = result
                        self.show_edited_preview()
                    else:
                        print(f"[얼굴편집] 경고: 공통 슬라이더 적용 후 edited_image가 None입니다")
            
            # 고급 모드에서 폴리곤 표시가 활성화되어 있으면 눈/입술 영역 표시는 하지 않음 (폴리곤으로 대체)
            show_polygons = hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()
            if not show_polygons:
                # 눈 영역 표시 업데이트
                if self.show_eye_region.get():
                    self.update_eye_region_display()
                # 입술 영역 표시 업데이트
                if self.show_lip_region.get():
                    self.update_lip_region_display()
            else:
                # 폴리곤이 활성화되면 기존 타원형 영역 제거
                if hasattr(self, 'clear_eye_region_display'):
                    self.clear_eye_region_display()
                if hasattr(self, 'clear_lip_region_display'):
                    self.clear_lip_region_display()
            # 폴리곤 표시 업데이트 (custom_landmarks가 이미 update_polygons_only에서 업데이트되었으므로)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # custom_landmarks가 있으면 폴리곤만 다시 그리기
                if self.custom_landmarks is not None:
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items['original'].clear()
                    self.polygon_point_map_original.clear()
                    
                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        # custom_landmarks 가져오기 (LandmarkManager 사용)
                        custom = self.landmark_manager.get_custom_landmarks()
                        
                        if custom is not None:
                            self._draw_landmark_polygons(
                                self.canvas_original,
                                self.current_image,
                                custom,
                                self.canvas_original_pos_x,
                                self.canvas_original_pos_y,
                                self.landmark_polygon_items['original'],
                                "green",
                                current_tab,
                                force_use_custom=True  # custom_landmarks를 명시적으로 전달했으므로 강제 사용
                            )
                else:
                    # custom_landmarks가 없으면 전체 업데이트
                    self.update_face_features_display()
    
