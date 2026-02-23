"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
"""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

from utils.logger import print_debug

# 디버그 출력 제어
DEBUG_MORPHING = False

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform



class HandlersMixin:
    """이벤트 핸들러 기능 Mixin"""

    def _mark_change_source(self, source):
        if hasattr(self, '_set_change_source'):
            try:
                self._set_change_source(source)
            except Exception:
                pass
    
    def on_alignment_change(self):
        """얼굴 정렬 설정 변경 시 호출"""
        if self.current_image is None:
            return
        self._mark_change_source('option')
        
        if self.auto_align.get():
            # 정렬 활성화: 정렬 적용
            self.apply_alignment()
        else:
            # 정렬 비활성화: 정렬된 이미지 제거하고 원본 기반으로 편집
            self.aligned_image = None
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
    
    def on_eye_spacing_change(self):
        """눈 간격 조정 체크박스 변경 시 호출"""
        self._mark_change_source('option')
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
    
    def on_eye_region_display_change(self):
        """눈 영역 표시 옵션 변경 시 호출"""
        self._mark_change_source('option')
        if self.current_image is not None:
            if hasattr(self, '_request_face_edit_refresh'):
                self._request_face_edit_refresh(
                    image=False,
                    landmarks=True,
                    overlays=True,
                    guide_lines=False,
                )
            else:
                self._refresh_face_edit_display(
                    image=False,
                    landmarks=True,
                    overlays=True,
                    guide_lines=False,
                )
    
    def on_lip_region_display_change(self):
        """입술 영역 표시 옵션 변경 시 호출"""
        self._mark_change_source('option')
        if self.current_image is not None:
            if hasattr(self, '_request_face_edit_refresh'):
                self._request_face_edit_refresh(
                    image=False,
                    landmarks=True,
                    overlays=True,
                    guide_lines=False,
                )
            else:
                self._refresh_face_edit_display(
                    image=False,
                    landmarks=True,
                    overlays=True,
                    guide_lines=False,
                )
    
    def on_region_selection_change(self):
        """부위 선택 변경 시 호출"""
        self._mark_change_source('option')
        # 슬라이더 상태 업데이트
        if hasattr(self, 'update_region_slider_state'):
            self.update_region_slider_state()
        
        # 전체 탭일 때만 부위 선택이 적용됨
        if self.current_morphing_tab == "전체":
            # 랜드마크 표시 업데이트
            if self.current_image is not None:
                if hasattr(self, '_request_face_edit_refresh'):
                    self._request_face_edit_refresh(
                        image=False,
                        landmarks=True,
                        overlays=True,
                        guide_lines=False,
                    )
                else:
                    self._refresh_face_edit_display(
                        image=False,
                        landmarks=True,
                        overlays=True,
                        guide_lines=False,
                    )
    
    def on_landmarks_display_change(self):
        """랜드마크 표시 옵션 변경 시 호출"""
        self._mark_change_source('option')
        if self.current_image is not None:
            refresh = getattr(self, '_request_face_edit_refresh', self._refresh_face_edit_display)
            refresh(
                image=False,
                landmarks=True,
                overlays=True,
                guide_lines=False,
            )
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출 (슬라이더 드래그 종료 시 호출)"""

        print("on_morphing_change called..")

        # 확대/축소 중이면 건너뛰기
        if hasattr(self, '_skip_morphing_change') and self._skip_morphing_change:
            # 50ms 후에 플래그 해제 (더 빠른 해제)
            if hasattr(self, '_zoom_timer') and self._zoom_timer:
                self.after_cancel(self._zoom_timer)
            self._zoom_timer = self.after(50, lambda: setattr(self, '_skip_morphing_change', False))
            return
        
        # 라벨 업데이트
        self.update_labels_only()
        
        # 슬라이더 조작 시 last_selected_landmark_index 초기화
        # (눈동자 드래그 후 슬라이더 조작 시 슬라이더가 적용되도록)
        if hasattr(self, 'last_selected_landmark_index'):
            self.last_selected_landmark_index = None
        
        print_debug("handler", f"on_morphing_change: {self.current_image}")
        if hasattr(self, '_last_change_source'):
            last_source = getattr(self, '_last_change_source', 'none')
            if last_source in (None, 'none'):
                self._mark_change_source('slider')
        
        self._ensure_morphing_guard_state()
        if self._morphing_update_in_progress:
            self._morphing_update_pending = True
            return
        
        self._morphing_update_in_progress = True
        try:
            self._perform_morphing_update()
        finally:
            self._morphing_update_in_progress = False

    def _perform_morphing_update(self):
        if self.current_image is None:
            return

        print_debug("handler", "_perform_morphing_update: called..")
        initial_signature = self._build_morphing_state_signature()
        if (initial_signature is not None and
                initial_signature == getattr(self, '_last_morphing_state_signature', None)):
            print_debug("handler", "[모핑] 상태 시그니처 동일 - 업데이트 스킵")
            return
        
        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        # 하지만 공통 슬라이더는 항상 적용되어야 하므로 return하지 않음
        use_warping = getattr(self, 'use_landmark_warping', None)
        change_source = getattr(self, '_last_change_source', 'none')
        force_slider_mode = change_source in ('slider', 'drag')
        refresh = getattr(self, '_request_face_edit_refresh', self._refresh_face_edit_display)

        print_debug("handler", f"use_warping: {use_warping}, {use_warping.get()}, {len(self.custom_landmarks)}, \
            slider:{force_slider_mode}, change_source:{change_source}")

        if use_warping is not None and hasattr(use_warping, 'get') and use_warping.get():
            # 고급 모드가 활성화되었고 커스텀 랜드마크가 있으면 적용
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                # 슬라이더 이벤트일 때: 먼저 공통 슬라이더로 랜드마크 변환, 그 다음 apply_polygon_drag_final로 이미지 변형
                if force_slider_mode and hasattr(self, '_apply_common_sliders'):
                    base_image = self.aligned_image if hasattr(self, 'aligned_image') and self.aligned_image is not None else self.current_image
                    self._apply_common_sliders(self.current_image, base_image=base_image)
                
                # apply_polygon_drag_final을 호출하여 기존 랜드마크 변경사항 적용
                # 옵션 변경 시에는 중심점 위치를 유지하기 위해 force_slider_mode=False, 그런데 고급모드일땐 True 여야하는데
                if hasattr(self, 'apply_polygon_drag_final'):
                    self.apply_polygon_drag_final(
                        desc=f"use_warping:{use_warping.get()}, _perform_morphing_update",
                        force_slider_mode=force_slider_mode,
                    )
                    if not force_slider_mode:
                        refresh(
                            image=False,
                            landmarks=True,
                            overlays=True,
                            guide_lines=False,
                        )
                    # 슬라이더 이벤트일 때는 공통 슬라이더를 별도로 적용하기 위해 return하지 않음
                    # (위 코드에서 이미 _apply_common_sliders 호출됨)
        else:
            # 고급 모드가 아닐 때도 눈동자 맵핑 방법 변경은 적용되어야 함
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                if hasattr(self, 'apply_polygon_drag_final'):
                    # 옵션 변경 시에는 중심점 위치를 유지하기 위해 force_slider_mode=False
                    self.apply_polygon_drag_final(desc=f"use_warping:{use_warping}, _perform_morphing_update", force_slider_mode=False)

        # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
        # 고급 모드 + 슬라이더 이벤트일 땐 apply_polygon_drag_final에서 이미 변형/갱신 처리되므로 건너뜀
        use_warping = getattr(self, 'use_landmark_warping', None)
        is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
        is_advanced_warping = (use_warping is not None and hasattr(use_warping, 'get') and use_warping.get())
        skip_polygon_update = is_advanced_warping and force_slider_mode
        is_advanced_tesselation = is_advanced_warping and is_tesselation_selected

        if not skip_polygon_update and hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
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
                pass

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
                pass

        # 고급 모드: 공통 슬라이더를 apply_polygon_drag_final 후에 별도로 적용
        use_warping = getattr(self, 'use_landmark_warping', None)
        is_advanced_mode = (use_warping is not None and hasattr(use_warping, 'get') and use_warping.get() and 
                           hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None)
        
        print_debug("handler", f"_perform_morphing_update 슬라이더 적용: is_advanced_mode={is_advanced_mode}, force_slider_mode={force_slider_mode}")
        
        if is_advanced_mode and force_slider_mode:
            # 고급 모드 + 슬라이더 이벤트: apply_polygon_drag_final에서 슬라이더가 적용되지 않았으므로 여기서 적용
            print_debug("handler", "_apply_common_sliders 호출 시작")
            if hasattr(self, '_apply_common_sliders'):
                base_image = self.aligned_image if hasattr(self, 'aligned_image') and self.aligned_image is not None else self.current_image
                self._apply_common_sliders(self.current_image, base_image=base_image)
                print_debug("handler", "_apply_common_sliders 호출 완료")
            else:
                print_debug("handler", "_apply_common_sliders 메서드 없음")
            
            # 원본 이미지의 랜드마크만 업데이트 (폴리곤 표시용)
            # _apply_common_sliders를 다시 호출하면 custom_landmarks가 누적되므로 주의
            # 이미 첫 번째 호출에서 custom_landmarks가 변형되었으므로, 
            # 원본 이미지는 현재 custom_landmarks를 사용하여 폴리곤만 표시하면 됨
            # (원본 이미지 자체는 변형할 필요 없음 - 폴리곤 표시만 필요)
        else:
            # 일반 모드: apply_editing 호출
            self.apply_editing()
        
        final_signature = self._build_morphing_state_signature()
        if final_signature is not None:
            self._last_morphing_state_signature = final_signature
    
    def _ensure_morphing_guard_state(self):
        if not hasattr(self, '_morphing_update_in_progress'):
            self._morphing_update_in_progress = False
        if not hasattr(self, '_morphing_update_pending'):
            self._morphing_update_pending = False

    def _build_morphing_state_signature(self):
        """현재 모핑 관련 상태를 요약해 중복 업데이트를 피하기 위한 시그니처 생성"""
        if not hasattr(self, 'landmark_manager'):
            return None
        slider_values = (
            self._safe_get_var_value('region_size_x', 1.0),
            self._safe_get_var_value('region_size_y', 1.0),
            self._safe_get_var_value('region_position_x', 0.0),
            self._safe_get_var_value('region_position_y', 0.0),
            self._safe_get_var_value('region_center_offset_x', 0.0),
            self._safe_get_var_value('region_center_offset_y', 0.0),
            self._safe_get_var_value('blend_ratio', 1.0),
        )
        use_warping_flag = False
        use_warping = getattr(self, 'use_landmark_warping', None)
        if use_warping is not None and hasattr(use_warping, 'get'):
            try:
                use_warping_flag = bool(use_warping.get())
            except Exception:
                use_warping_flag = False
        current_tab = getattr(self, 'current_morphing_tab', '전체')
        region_flags = self._get_region_selection_flags()
        last_selected = getattr(self, 'last_selected_landmark_index', None)
        return (slider_values, use_warping_flag, current_tab, region_flags, last_selected)

    def _safe_get_var_value(self, attr_name, default=0.0):
        var = getattr(self, attr_name, None)
        if var is None:
            return round(default, 4)
        if hasattr(var, 'get'):
            try:
                return round(float(var.get()), 4)
            except Exception:
                return round(default, 4)
        try:
            return round(float(var), 4)
        except Exception:
            return round(default, 4)

    def _get_region_selection_flags(self):
        attrs = [
            'show_face_oval', 'show_left_eye', 'show_right_eye',
            'show_left_eyebrow', 'show_right_eyebrow', 'show_nose',
            'show_lips', 'show_upper_lips', 'show_lower_lips',
            'show_left_iris', 'show_right_iris', 'show_contours',
            'show_tesselation'
        ]
        flags = []
        for attr in attrs:
            var = getattr(self, attr, None)
            if var is None:
                flags.append(False)
            elif hasattr(var, 'get'):
                try:
                    flags.append(bool(var.get()))
                except Exception:
                    flags.append(False)
            else:
                flags.append(bool(var))
        return tuple(flags)


