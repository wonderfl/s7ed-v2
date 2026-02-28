"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
"""
import os
import time
import math
from typing import List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk
from PIL import Image

from .landmark import StateKeys
from gui.FaceForge.utils import landmarks as utilmarks
from gui.FaceForge.utils.elapsed import StopWatch
from gui.FaceForge.utils.debugs import DEBUG_WARPING_UPDATE, DEBUG_POLYGON_WARPING, DEBUG_ELAPSED_TIME
from utils.logger import debug, info, warning, error, log

class WarpingMixin:
    
    skip_refresh = False

    def _execute_warp_from_landmark_state(self):
        """landmark_state에서 워프 데이터를 가져와 실행"""
        from .landmark import StateKeys

        print("_execute_warp_from_landmark_state")
        
        try:
            # 워프 데이터 가져오기
            warp_data = self.landmark_manager.get_state_section(StateKeys.SECTION_WARP)
            # 👇 이 부분 추가
            selected_indices = warp_data[StateKeys.KEY_SELECTED_INDICES]
            if isinstance(selected_indices[0], dict):  # 딕셔너리면 변환
                flat_indices = []
                for region in selected_indices:
                    flat_indices.extend(region.get("indices", []))
                selected_indices = list(set(flat_indices))
                    
            # morph_face_by_polygons 호출
            from gui.FaceForge.utils.morphing.polygon.core import morph_face_by_polygons
            result = morph_face_by_polygons(
                self.original_image,
                warp_data[StateKeys.KEY_SOURCE_LANDMARKS],
                warp_data[StateKeys.KEY_TARGET_LANDMARKS],
                selected_point_indices=selected_indices,
            )
            
            if result is not None:
                self.current_image = result
                
        except Exception as e:
            error("on_warping_change", f"워프 실행 실패: {e}")


    def on_warping_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출 (슬라이더 드래그 종료 시 호출)"""

        if DEBUG_WARPING_UPDATE:
            print(f"{'-'*80}",f"\n[on_warping_change] :", )
        
        self._update_region_runtime_state()
        context = self.landmark_manager.get_state_section(StateKeys.SECTION_CONTEXT) or {}
        context[StateKeys.KEY_SELECTED_REGIONS] = self._get_selected_regions()
        context[StateKeys.KEY_SLIDER_PARAMS] = self.region_params
        self.landmark_manager.set_state_section(StateKeys.SECTION_CONTEXT, context)

        # 확대/축소 중이면 건너뛰기
        if hasattr(self, '_skip_warping_change') and self._skip_warping_change:
            return
        
        # landmark_state를 사용한 슬라이더 적용
        if hasattr(self, '_apply_common_sliders_to_landmarks'):
            selected_regions = self._get_selected_regions()
            slider_values, slider_conditions = self._get_common_slider_values() # 슬라이더 값들 가져오기
            
        self.update_labels_only() # 라벨 업데이트
        
        # 슬라이더 조작 시 last_selected_landmark_index 초기화
        # (눈동자 드래그 후 슬라이더 조작 시 슬라이더가 적용되도록)
        if hasattr(self, 'last_selected_landmark_index'):
            self.last_selected_landmark_index = None
        
        if DEBUG_WARPING_UPDATE:
            debug("on_warping_change", f": image={self.current_image is not None}")

        if hasattr(self, '_last_change_source'):
            last_source = getattr(self, '_last_change_source', 'none')
            if last_source in (None, 'none'):
                self._mark_change_source('slider')
        
        self._ensure_warping_guard_state()
        if self._warping_update_in_progress:
            self._warping_update_pending = True
            return
        
        self._warping_update_in_progress = True
        try:
            self._perform_warping_update()
        finally:
            self._warping_update_in_progress = False

        # 미리보기 팝업 업데이트
        if self.preview_popup is not None and self.preview_popup.winfo_exists():
            self.update_preview_canvas(self.current_image)

    def _perform_warping_update(self, forced_update=False):
        has_current_image = self.current_image is not None
        initial_signature = self._build_warping_state_signature()
        warping_signature = getattr(self, '_last_warping_state_signature', None)
        is_repeated = (initial_signature is not None and initial_signature == warping_signature)

        elapsed1 = 0
        elapsed2 = 0
        elapsed3 = 0
        
        _watch_time = StopWatch()
        _watch_time.start()
        if DEBUG_WARPING_UPDATE:
            info("_perform_warping_update", f"current={has_current_image}, need_update={not is_repeated}")

        if not has_current_image:
            return            
        if is_repeated and not forced_update:
            return
        
        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        # 하지만 공통 슬라이더는 항상 적용되어야 하므로 return하지 않음
        use_warping = getattr(self, 'use_landmark_warping', False)
        change_source = getattr(self, '_last_change_source', 'none')
        force_slider_mode = change_source in ('slider', 'drag')

        has_apply_final = hasattr(self, 'apply_polygon_warping')
        refresh = getattr(self, '_request_face_edit_refresh', self._refresh_face_edit_display)

        current_landmarks = self.landmark_manager.get_current_landmarks()
        
        is_warping = use_warping is not None and hasattr(use_warping, 'get') and use_warping.get()
        if DEBUG_WARPING_UPDATE:
            info("_perform_warping_update", 
                f"warp: {use_warping.get()}, landmarks: {len(current_landmarks) if current_landmarks is not None else None}, "
                f"apply: {has_apply_final}, slider: {force_slider_mode}, source: {change_source}, is_warping: {is_warping}")
        
        if is_warping:
            # 고급 모드가 활성화되었고 커스텀 랜드마크가 있으면 적용
            if current_landmarks is not None:                
                # apply_polygon_warping 호출하여 기존 랜드마크 변경사항 적용
                # 옵션 변경 시에는 중심점 위치를 유지하기 위해 force_slider_mode=False, 그런데 고급모드일땐 True 여야하는데
                if hasattr(self, 'apply_polygon_warping'):
                    self.apply_polygon_warping(
                        desc=f"warp:{is_warping}, _perform_warping_update",
                        force_slider_mode=force_slider_mode,
                    )
        else:        
            if hasattr(self, 'current_face_landmarks') and self.current_face_landmarks is not None:
                if hasattr(self, 'apply_polygon_warping'):
                    # 옵션 변경 시에는 중심점 위치를 유지하기 위해 force_slider_mode=False
                    self.apply_polygon_warping(desc=f"use_warping:{is_warping}, _perform_warping_update", force_slider_mode=False)

        if DEBUG_WARPING_UPDATE and DEBUG_ELAPSED_TIME:
            elapsed1 = _watch_time.stop()
            log("_perform_warping_update", f"apply_polygon_warping: {elapsed1:.6f}초")

        _watch_time.start()
        # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
        # 고급 모드 + 슬라이더 이벤트일 땐 apply_polygon_warping에서 이미 변형/갱신 처리되므로 건너뜀
        use_warping = getattr(self, 'use_landmark_warping', None)
        is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
        is_advanced_warping = (use_warping is not None and hasattr(use_warping, 'get') and use_warping.get())
        skip_polygon_update = is_advanced_warping and force_slider_mode
        is_advanced_tesselation = is_advanced_warping and is_tesselation_selected

        if not skip_polygon_update and hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'update_polygons_only') and not is_advanced_tesselation:
                self.update_polygons_only()
                if DEBUG_WARPING_UPDATE and DEBUG_ELAPSED_TIME:
                    elapsed2 = _watch_time.stop()
                    log("_perform_warping_update", f"update_polygons_only: {elapsed2:.6f}초")
        
        _watch_time.start()
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

        # 고급 모드: 공통 슬라이더를 apply_polygon_warping 후에 별도로 적용
        get_use_warping = getattr(self, 'use_landmark_warping', None)
        use_warping = get_use_warping is not None and hasattr(get_use_warping, 'get') and get_use_warping.get()

        if DEBUG_WARPING_UPDATE:
            info("_perform_warping_update", 
                f"warping={use_warping}, force_slider={force_slider_mode}, change_source={change_source}"
            )
        
        if use_warping and force_slider_mode:            
            # 원본 이미지의 랜드마크만 업데이트 (폴리곤 표시용)
            # _apply_common_sliders를 다시 호출하면 custom_landmarks가 누적되므로 주의
            # 이미 첫 번째 호출에서 custom_landmarks가 변형되었으므로, 
            # 원본 이미지는 현재 custom_landmarks를 사용하여 폴리곤만 표시하면 됨
            # (원본 이미지 자체는 변형할 필요 없음 - 폴리곤 표시만 필요)
            pass
        
        image_update_needed = not (use_warping and hasattr(self, 'apply_polygon_warping'))
        if not self.skip_refresh: 
            self._request_face_edit_refresh(
                image=True,
                polygons=True,
                pivots=True,
                guides=False,
                bbox=False,
            )
        self.skip_refresh = False

        final_signature = self._build_warping_state_signature()
        if final_signature is not None:
            self._last_warping_state_signature = final_signature    

        if DEBUG_WARPING_UPDATE and DEBUG_ELAPSED_TIME:
            elapsed3 = _watch_time.stop()

            elapsed = elapsed3+ elapsed2+ elapsed1
            # log("_perform_warping_update", 
            #     f"elapsed: {elapsed:.6f}초 ( "
            #     f"apply_polygon_warping: {elapsed1:.6f}초, "
            #     f"update_polygons_only: {elapsed2:.6f}초, "
            #     f"_request_face_edit_refresh: {elapsed3:.6f}초, "
            #     f" )"
            # )

    def _ensure_warping_guard_state(self):
        if not hasattr(self, '_warping_update_in_progress'):
            self._warping_update_in_progress = False
        if not hasattr(self, '_warping_update_pending'):
            self._warping_update_pending = False            

    def _build_warping_state_signature(self):
        """현재 모핑 관련 상태를 요약해 중복 업데이트를 피하기 위한 시그니처 생성"""
        if not hasattr(self, 'landmark_manager'):
            return None

        slider_values = (
            self._safe_get_var_value('region_size_x', 1.0),
            self._safe_get_var_value('region_size_y', 1.0),
            self._safe_get_var_value('region_position_x', 0.0),
            self._safe_get_var_value('region_position_y', 0.0),
            self._safe_get_var_value('region_pivot_x', 0.0),
            self._safe_get_var_value('region_pivot_y', 0.0),
            self._safe_get_var_value('region_expansion_level', 1.0),
            self._safe_get_var_value('show_polygon_color', self.polygon_color_ix),
        )
        use_warping_flag = False
        use_warping = getattr(self, 'use_landmark_warping', None)
        if use_warping is not None and hasattr(use_warping, 'get'):
            try:
                use_warping_flag = bool(use_warping.get())
            except Exception:
                use_warping_flag = False

        region_flags = self._get_region_selection_flags()
        last_selected = getattr(self, 'last_selected_landmark_index', None)
        return (slider_values, use_warping_flag, region_flags, last_selected)

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

    def _validate_and_prepare_polygon_apply(self, force_slider_mode):
        """폴리곤 적용 초기화 및 검증"""
        # 중복 호출 방지 체크
        self._ensure_polygon_apply_guard_state()
        apply_signature = self._build_polygon_apply_signature(force_slider_mode)
        last_signature = getattr(self, '_last_polygon_apply_signature', None)
        is_repeated = apply_signature == last_signature
        
        if DEBUG_WARPING_UPDATE:
            debug("_validate_and_prepare_polygon_apply", 
                f"need_apply={not is_repeated}, current_image={self.current_image is not None}, "
                #f"apply_signature={apply_signature} "
            )
        
        if is_repeated:
            return False
        
        # 필수 조건 검증
        if self.current_image is None:
            return False
        
        # custom_landmarks 확인
        current = self.landmark_manager.get_current_landmarks()
        left_center = self.landmark_manager.get_left_iris_center_coord()
        right_center = self.landmark_manager.get_right_iris_center_coord()
        has_iris_centers = left_center is not None or right_center is not None
        
        if current is None and not has_iris_centers:
            return False
        
        # current_landmarks가 None이면 원본으로 설정
        if current is None:
            original_face = self.landmark_manager.get_original_face_landmarks()
            if original_face is not None:
                current = list(original_face)
                self.landmark_manager.set_current_landmarks(current, reason="apply_polygon_warping: 중앙 포인트만 변경")
        
        return True

    def _prepare_landmarks_for_warping(self):
        """랜드마크 준비 및 데이터 구성"""
        try:
            # 원본 랜드마크 가져오기
            if not self.landmark_manager.has_original_face_landmarks():
                params = self._get_alignment_params()
                detected, original_landmarks = utilmarks.detect_face_landmarks(self.original_image, params)
                if original_landmarks is None:
                    print_warning("얼굴편집", "원본 랜드마크 감지 실패")
                    return None

                # 기존 set_* 호출 대신 헬퍼 사용
                if hasattr(self, "_apply_detected_landmarks"):
                    self._apply_detected_landmarks(original_landmarks, reason="warp_prepare")
                else:
                    self.landmark_manager.set_original_face_landmarks(original_landmarks)
                    original_landmarks = self.landmark_manager.get_original_face_landmarks()
            else:
                original_landmarks = self.landmark_manager.get_original_face_landmarks()

            current_landmarks = self.landmark_manager.get_current_landmarks()
            print("_prepare_landmarks_for_warping current", self.get_bbox_lips(current_landmarks))   

            # 랜드마크 데이터 구성
            landmarks_data = {
                'original_landmarks': original_landmarks,
                'current_landmarks': current_landmarks,
                'last_selected_index': getattr(self, 'last_selected_landmark_index', None),
                'dragged_indices': self.landmark_manager.get_dragged_indices(),
                'selected_regions': self._get_selected_regions(),
                'dragged_points_backup': {}
            }
            
            # 드래그된 포인트 백업
            if landmarks_data['dragged_indices']:
                 # landmark_state에서 현재 랜드마크 가져오기
                state = self.landmark_manager.get_landmark_state()
                custom_before_sliders = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_FACE_LANDMARKS]
                
                print("custom_before_sliders",  self.get_bbox_lips(custom_before_sliders))
                if custom_before_sliders is not None:
                    max_idx = 468 if len(custom_before_sliders) == 470 else len(custom_before_sliders)
                    for idx in landmarks_data['dragged_indices']:
                        if 0 <= idx < max_idx:
                            landmarks_data['dragged_points_backup'][idx] = custom_before_sliders[idx]
                    if DEBUG_WARPING_UPDATE:
                        debug("_prepare_landmarks_for_warping", f"드래그 백업: {landmarks_data['dragged_points_backup']}")
            
            # 디버깅 정보 출력
            self._debug_landmark_changes(landmarks_data)
            return landmarks_data
            
        except Exception as e:
            error("얼굴편집", f"랜드마크 준비 실패: {e}")
            return None
    
    def _debug_landmark_changes(self, landmarks_data):
        """랜드마크 변경사항 디버깅 출력"""
        original = landmarks_data['original_landmarks']
        current = landmarks_data['current_landmarks']
        last_idx = landmarks_data['last_selected_index']
        
        if isinstance(last_idx, int) and last_idx >= 0 and current:
            if last_idx < len(original) and last_idx < len(current):
                orig_pos = original[last_idx]
                current_pos = current[last_idx]
                diff = ((current_pos[0] - orig_pos[0])**2 + (current_pos[1] - orig_pos[1])**2)**0.5

                # info("_debug_landmark_changes", f"last_selected {last_idx}: ({orig_pos[0]:.1f}, {orig_pos[1]:.1f}) => ({current_pos[0]:.1f}, {current_pos[1]:.1f}), distance= {diff:.1f} pixel")

        elif isinstance(last_idx, str):
            # info("_debug_landmark_changes", f"last_selected: ({last_idx})")
            pass

    def _apply_sliders_and_restore_dragged_points(self, landmarks_data):
        """슬라이더 적용 및 드래그 포인트 복원"""

        # 슬라이더 값 가져오기
        slider_values, slider_conditions = self._get_common_slider_values()
                
        # 랜드마크에 슬라이더 값 적용
        if hasattr(self, '_apply_common_sliders_to_landmarks'):
            temp_result = self._apply_common_sliders_to_landmarks(
                selected_regions=landmarks_data.get('selected_regions', []),
                pivot_x=slider_values['pivot_x'],
                pivot_y=slider_values['pivot_y'],
                size_x=slider_values['size_x'],
                size_y=slider_values['size_y'],
                position_x=slider_values['position_x'],
                position_y=slider_values['position_y'],
                image=self.original_image
            )

            # 드래그된 포인트 복원
            if landmarks_data['dragged_points_backup']:
                # landmark_state에서 현재 랜드마크 가져오기
                state = self.landmark_manager.get_landmark_state()
                current_after_sliders = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_FACE_LANDMARKS]
                if current_after_sliders is not None:
                    max_idx = 468 if len(current_after_sliders) == 470 else len(current_after_sliders)
                    restored_count = 0
                    for idx, backup_pos in landmarks_data['dragged_points_backup'].items():
                        if 0 <= idx < max_idx:
                            current_after_sliders[idx] = backup_pos
                            restored_count += 1

                    # landmark_state 업데이트
                    self.landmark_manager.set_state_value(
                        StateKeys.SECTION_CURRENT,
                        StateKeys.KEY_FACE_LANDMARKS,
                        current_after_sliders
                    )

                    if DEBUG_WARPING_UPDATE:
                        debug("_apply_sliders_and_restore_dragged_points", f"restdragged_points_backup: {restored_count}개")
            
            # 랜드마크 데이터 업데이트
            landmarks_data['current_landmarks'] = self.landmark_manager.get_current_landmarks()
        
        return landmarks_data


    def _execute_face_morphing(self, landmarks_data, force_slider_mode):
        """얼굴 모핑 실행"""
        slider_event_only = bool(force_slider_mode)
        # if DEBUG_WARPING_UPDATE:
        #     debug("_execute_face_morphing", f"slider_event_only={slider_event_only}")

        try:

            elapsed = 0
            _timer = StopWatch()
            _timer.start()
            
            # 슬라이더 조건 확인
            size_x = self.region_size_x.get()
            size_y = self.region_size_y.get()
            pivot_x = self.region_pivot_x.get()
            pivot_y = self.region_pivot_y.get()
            position_x = self.region_position_x.get()
            position_y = self.region_position_y.get()
            
            size_x_condition = abs(size_x - 1.0) >= 0.01
            size_y_condition = abs(size_y - 1.0) >= 0.01
            size_condition = size_x_condition or size_y_condition
            pos_x_condition = abs(position_x) >= 0.1
            pos_y_condition = abs(position_y) >= 0.1
            conditions_met = size_condition or pos_x_condition or pos_y_condition
            
            # 랜드마크 변형 확인
            landmarks_changed = self._check_landmarks_changed(landmarks_data)
            elapsed1 = _timer.stop()

            # 모핑 실행 조건 확인
            should_morph = slider_event_only or conditions_met or landmarks_changed
            # if DEBUG_WARPING_UPDATE:
            #     debug("_execute_face_morphing", f"should_morph={should_morph}, landmarks_changed={landmarks_changed}, conditions_met={conditions_met}")
                                
            if not should_morph:
                # 원본 이미지 반환
                return self.current_image

            _timer.start()
            # morph_face_by_polygons 호출
            result = self._call_morph_face_by_polygons()
            elapsed2 = _timer.stop()

            # if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
            #     log("_execute_face_morphing",
            #         f"elapsed={(elapsed1+elapsed2):.6f}s, "
            #         #f"_check_landmarks_changed={elapsed1:.6f}, "
            #         f"_call_morph_face_by_polygons={elapsed2:.6f}, ")
            return result
            
        except Exception as e:
            error("얼굴편집", f"모핑 실행 실패: {e}")
            return None

    def _check_landmarks_changed(self, landmarks_data):
        """랜드마크 변형 확인"""
        original = landmarks_data['original_landmarks']
        current = landmarks_data['current_landmarks']
        
        if DEBUG_WARPING_UPDATE:
            debug("_check_landmarks_changed", f"original={original is not None}, current={current is not None}")
        
        if current is None:
            return False
        
        # 468개 랜드마크 비교
        current_length = len(current)
        compare_length = min(len(original), current_length)
        if current_length == 470:
            compare_length = 468
        
        for i in range(compare_length):
            if i < len(original) and i < len(current):
                orig = original[i]
                current_point = current[i]
                diff = ((current_point[0] - orig[0])**2 + (current_point[1] - orig[1])**2)**0.5
                if diff > 0.1:
                    return True
        
        # 중앙 포인트 확인
        if current_length == 470:
            left_center = self.landmark_manager.get_left_iris_center_coord()
            right_center = self.landmark_manager.get_right_iris_center_coord()
            if left_center is not None or right_center is not None:
                return True
        
        return False

    def _apply_region_scaling(
            self,
            landmarks: list[tuple[float, float]],
            selected_regions: list[dict],
            size_x: float,
            size_y: float,
            pivot: tuple[float, float],
            guide_axis_info: Optional[dict] = None,
        ) -> list[tuple[float, float]]:
        """선택된 영역을 가이드축 기준으로 확대/축소"""
        if abs(size_x - 1.0) < 0.01 and abs(size_y - 1.0) < 0.01:
            return landmarks

        scaled = list(landmarks)

        angle = guide_axis_info.get("angle") if guide_axis_info else None
        use_axis = angle is not None
        cos_a = math.cos(angle) if use_axis else 1.0
        sin_a = math.sin(angle) if use_axis else 0.0

        def _apply_scale(dx: float, dy: float) -> tuple[float, float]:
            if not use_axis:
                return dx * size_x, dy * size_y
            rot_x = dx * cos_a + dy * sin_a
            rot_y = -dx * sin_a + dy * cos_a
            rot_x *= size_x
            rot_y *= size_y
            new_dx = rot_x * cos_a - rot_y * sin_a
            new_dy = rot_x * sin_a + rot_y * cos_a
            return new_dx, new_dy

        for region in selected_regions or []:
            
            name = region.get("name")
            pivot = region.get("pivot") or pivot
            pivot_x, pivot_y = pivot

            print(f"region={name}, pivot=({pivot_x:.3f},{pivot_y:.3f})")

            indices = region.get("indices", [])
            for idx in indices:
                if 0 <= idx < len(landmarks):
                    x, y = landmarks[idx]
                    dx = x - pivot_x
                    dy = y - pivot_y
                    new_dx, new_dy = _apply_scale(dx, dy)
                    scaled[idx] = (
                        pivot_x + new_dx,
                        pivot_y + new_dy,
                    )

        return scaled

    def _apply_region_translation(
            self,
            landmarks: list[tuple[float, float]],
            selected_regions: list[tuple[str, list[int]]],
            offset_x: float,
            offset_y: float,
        ) -> list[tuple[float, float]]:
        """선택된 영역의 랜드마크를 offset 만큼 평행 이동"""
        if abs(offset_x) < 1e-4 and abs(offset_y) < 1e-4:
            return landmarks
    
        translated = list(landmarks)
    
        for region in selected_regions or []:            
            indices = region.get("indices", [])
            for idx in indices:
                if idx >= len(landmarks):
                    continue
                x, y = landmarks[idx]
                translated[idx] = (
                    x + offset_x,
                    y + offset_y,
                )
    
        return translated        


    def _compute_target_landmarks_from_sliders(
            self,
            original_landmarks,
            image_width,
            image_height,
            slider_values,
            slider_conditions,
            selected_regions,
        ):
        """원본 랜드마크 + 현재 슬라이더 상태로 타깃 랜드마크 계산"""
        target = list(original_landmarks)

        # 예시: region size/position 슬라이더 적용
        if slider_conditions['size_condition']:
            guide_info = self._get_guide_axis_info(original_landmarks, (image_width,image_height))
            # selected_regions에 포함된 각 랜드마크 인덱스 영역을 확대/축소
            target = self._apply_region_scaling(
                target,
                selected_regions,
                slider_values['size_x'],
                slider_values['size_y'],
                pivot=(slider_values['pivot_x'], slider_values['pivot_y']),
                guide_axis_info=guide_info,
            )

        if slider_conditions['pos_x_condition'] or slider_conditions['pos_y_condition']:
            target = self._apply_region_translation(
                target,
                selected_regions,
                slider_values['position_x'],
                slider_values['position_y'],
            )

        # 필요하면 추가 슬라이더(iris, expansion 등)도 이곳에서 반영
        return target


    def _call_morph_face_by_polygons(self):
        """morph_face_by_polygons 호출"""

        # if DEBUG_POLYGON_WARPING:
        #     debug("_call_morph_face_by_polygons", f":")

        try:

            # 파라미터 준비
            img_width, img_height = self.original_image.size
            cached_bbox = self.landmark_manager.get_original_bbox(img_width, img_height)

            # 1) 원본 랜드마크 가져오기
            original_landmarks = self.landmark_manager.get_original_face_landmarks()
            if not original_landmarks:
                error("_call_morph_face_by_polygons", f"original_landmarks is None")
                return None

            # landmark_state에서 워프 데이터 가져오기
            warp_data = self.landmark_manager.get_state_section(StateKeys.SECTION_WARP)
            target_landmarks = warp_data.get(StateKeys.KEY_TARGET_LANDMARKS)
            selected_regions = warp_data.get(StateKeys.KEY_SELECTED_INDICES) or []

            # 2) flatten된 정수 리스트는 morph 호출에만 사용
            selected_indices = sorted({
                idx
                for region in selected_regions or []
                for idx in (
                    region.get("indices", [])               # dict 형태 (warp_regions)
                    if isinstance(region, dict)
                    else [i for pair in region[1] for i in pair]  # 기존 tuple 형태
                )
                if isinstance(idx, int)
            })

            if selected_indices:
                xs = [original_landmarks[i][0] for i in selected_indices if i < len(original_landmarks)]
                ys = [original_landmarks[i][1] for i in selected_indices if i < len(original_landmarks)]
                if xs and ys:
                    min_x_sel = max(0, int(min(xs)) - 10)
                    min_y_sel = max(0, int(min(ys)) - 10)
                    max_x_sel = min(img_width, int(max(xs)) + 10)
                    max_y_sel = min(img_height, int(max(ys)) + 10)
                    selected_bbox = (min_x_sel, min_y_sel, max_x_sel, max_y_sel)
                else:
                    selected_bbox = cached_bbox  # fallback
            else:
                selected_bbox = cached_bbox

            # 3) warp 실행 (이미지는 무조건 self.original_image)
            # morph_face_by_polygons 호출
            from gui.FaceForge.utils.morphing.polygon.core import morph_face_by_polygons
            result, ctx = morph_face_by_polygons(
                self.original_image,
                original_landmarks,
                target_landmarks,
                selected_point_indices=selected_indices,
                cached_original_bbox=selected_bbox,
                blend_ratio=1.0,
                skip_pixel_warp=False,
                return_contexts=True,
            )

            # log("_call_morph_face_by_polygons", f": origin {self.get_bbox_lips(original_landmarks)}")
            # log("_call_morph_face_by_polygons", f": target {self.get_bbox_lips(target_landmarks)}")
            
            import numpy as np
            delaunay_np = np.clip(ctx["delaunay_image"], 0, 255).astype(np.uint8)
            delaunay = Image.fromarray(delaunay_np)

            warp = ctx["warp_result"]
            count = ctx["warp_count1"]  # result_count도 같이 저장해야 함
            normalized = np.divide(warp, np.maximum(count[..., None], 1e-6))
            warping = Image.fromarray(np.clip(normalized, 0, 255).astype(np.uint8))
            counting = Image.fromarray(np.clip(count, 0, 255).astype(np.uint8))
            
            pixel_mask = None
            overlap_mask = count > 1.0
            if np.any(overlap_mask):
                pixel_mask = (overlap_mask * 255).astype(np.uint8)            
                masking = Image.fromarray(pixel_mask)
                #self.show_image_popup(masking, title="WarpMask")

            mask_arr = ctx.get("transformed_mask")
            if mask_arr is not None:
                masking = Image.fromarray((mask_arr * 255).astype(np.uint8))
                #self.show_image_popup(masking, title="WarpMask")

            transformed_np = np.clip(ctx["transformed_result"], 0, 255).astype(np.uint8)
            transformed = Image.fromarray(transformed_np)

            #self.show_image_popup(transformed, title="Transformed")
            #self.show_image_popup(warping, title="WarpResult")
            #self.show_image_popup(counting, title="WarpCount")

            #self.show_image_popup(result)

        except Exception as e:
            error("_call_morph_face_by_polygons",f"{e}")
            result = None
            import traceback
            traceback.print_exc()

        # if DEBUG_POLYGON_WARPING:
        #     size_x, size_y = result.size 
        #     size_x = int(size_x/2)
        #     size_y = int(size_y/2)

        #     info("_call_morph_face_by_polygons", 
        #         f"regions={len(selected_indices)}, result={id(result)}, {result.size} "
        #         f"current={id(self.current_image)}"
        #     )

        return result

    def _handle_morphing_result(self, result, force_slider_mode):
        """모핑 결과 처리 및 화면 업데이트"""
        if DEBUG_POLYGON_WARPING:
            debug("_handle_morphing_result", 
                f"result: {result is None}, force_slider: {force_slider_mode}, "
                f"result={id(result)}, current={id(self.current_image)}"
            )
        try:
            if result is None:
                error("얼굴편집", "랜드마크 변형 결과가 None입니다")
                return
            
            # 이미지 업데이트
            self.current_image = result

            polygons_enabled = bool(getattr(self, 'show_landmark_polygons', None) and self.show_landmark_polygons.get())
            polygons_enabled = True
            pivots_enabled = bool(getattr(self, 'show_landmark_pivots', None) and self.show_landmark_pivots.get())
            guide_lines_enabled = self._compute_guide_flag()
            bbox_enabled = bool(getattr(self, 'show_bbox_frame', None) and self.show_bbox_frame.get())
            
            # 이미지 해시 계산 및 업데이트
            image_needs_refresh = self._should_refresh_display(result, force_slider_mode)
            
            # 디스플레이 업데이트
            if hasattr(self, 'update_face_edit_display'):
                self.update_face_edit_display(
                    image=True,

                    polygons=polygons_enabled,
                    pivots=pivots_enabled,
                    guides=guide_lines_enabled,
                    bbox=bbox_enabled,

                    force_original=False,
                )
                self.skip_refresh = True


            
        except Exception as e:
            error("얼굴편집", f"결과 처리 실패: {e}")

        if DEBUG_POLYGON_WARPING:
            debug("_handle_morphing_result", f"final "
                f"result={id(result)}, current={id(self.current_image)}, original={id(self.original_image)}"
            )
            size_x, size_y = result.size 
            size_x = int(size_x/2)
            size_y = int(size_y/2)
            #self.show_image_popup(result)


    def _compute_guide_flag(self):
        """가이드 라인 표시 플래그 계산"""
        if hasattr(self, '_should_update_guide_lines'):
            try:
                return self._should_update_guide_lines()
            except Exception:
                return False
        return bool(getattr(self, 'show_guide_lines', None) and self.show_guide_lines.get())

    def _should_refresh_display(self, result, force_slider_mode):
        """디스플레이 새로고침 필요 여부 확인"""
        try:
            import hashlib
            img_bytes = result.tobytes()
            current_hash = hashlib.md5(img_bytes).hexdigest()
            
            force_option_update = (force_slider_mode == False)
            previous_hash = getattr(self, '_last_current_image_hash', None)
            
            image_needs_refresh = force_option_update or current_hash != previous_hash
            self._last_current_image_hash = current_hash
            
            return image_needs_refresh
        except Exception:
            return True

    def _update_landmark_state_for_warping(self, landmarks_data):
        """워프용 landmark_state 업데이트"""
        from .landmark import StateKeys

        _warp = self.landmark_manager.get_state_section(StateKeys.SECTION_WARP) or {}
        selected_regions = landmarks_data.get('selected_regions') or []

        # 1. 워프 섹션 업데이트 (morph_face_by_polygons용 데이터)
        self.landmark_manager.set_state_section(StateKeys.SECTION_WARP, {
            StateKeys.KEY_SOURCE_LANDMARKS: landmarks_data['original_landmarks'],
            StateKeys.KEY_TARGET_LANDMARKS: landmarks_data['current_landmarks'],
            StateKeys.KEY_SELECTED_INDICES: selected_regions
        })

        # 2. 현재 섹션 업데이트 (드래그된 랜드마크 저장)
        self.landmark_manager.set_state_value(
            StateKeys.SECTION_CURRENT, 
            StateKeys.KEY_FACE_LANDMARKS, 
            landmarks_data['current_landmarks']
        )

        # 3. 드래그 인덱스 업데이트
        dragged_indices = self.landmark_manager.get_dragged_indices()
        self.landmark_manager.set_state_value(
            StateKeys.SECTION_CURRENT,
            StateKeys.KEY_DRAGGED_INDICES,
            dragged_indices
        )

    def apply_polygon_warping(self, desc="", force_slider_mode=False):
        """폴리곤 드래그 종료 시 최종 편집 적용
        
        Args:
            force_slider_mode: (사용 안 함, 하위 호환성 유지용)
        """

        if DEBUG_POLYGON_WARPING:
            debug("apply_polygon_warping", f"[{desc}], "
                f"current={id(self.current_image)}, original={id(self.original_image)}"
            )
            
        try:
            elapsed = 0

            _timer = StopWatch()
            _timer.start()

            # 1. 초기화 및 검증
            if not self._validate_and_prepare_polygon_apply(force_slider_mode):
                return

            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed1 = _timer.stop()
            
            _timer.start()
            # 2. 랜드마크 준비
            landmarks_data = self._prepare_landmarks_for_warping()
            if landmarks_data is None:
                return
            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed2 = _timer.stop()
            
            _timer.start()
            # 3. 슬라이더 적용 및 드래그 포인트 복원            
            if force_slider_mode:
                landmarks_data = self._apply_sliders_and_restore_dragged_points(landmarks_data)
            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed3 = _timer.stop()

            _timer.start()
            # 4. landmark_state 업데이트 (새로 추가!)
            self._update_landmark_state_for_warping(landmarks_data)
            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed4 = _timer.stop()
            
            _timer.start()
            # 5. 모핑 실행 (드래그 시에만)
            result = self._execute_face_morphing(landmarks_data, force_slider_mode)
            if result is None:
                return
            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed5 = _timer.stop()
                info("_execute_face_morphing", f"result={id(result)}, "
                    f"current={id(self.current_image)}, original={id(self.original_image)}"
                )
            
            _timer.start()
            # 6. 결과 처리
            self._handle_morphing_result(result, force_slider_mode)
            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed6 = _timer.stop()

            # 시그니처 업데이트
            polygon_signature = self._build_polygon_apply_signature()
            self._last_polygon_apply_signature = polygon_signature

            if DEBUG_POLYGON_WARPING and DEBUG_ELAPSED_TIME:
                elapsed7 = _timer.stop()
                elapsed = elapsed7+elapsed6+elapsed5+elapsed4+elapsed3+elapsed2+elapsed1
                # log("apply_polygon_warping", 
                #     f"elapsed={elapsed:.6f}s\n"
                #     f"_validate_and_prepare_polygon_apply={elapsed1:.6f}s, \n"
                #     f"_prepare_landmarks_for_warping={elapsed2:.6f}s, \n"
                #     f"_apply_sliders_and_restore_dragged_points={elapsed3:.6f}s, \n"
                #     f"_update_landmark_state_for_warping={elapsed4:.6f}s, \n"
                #     f"_execute_face_morphing={elapsed5:.6f}s, \n"
                #     f"_handle_morphing_result={elapsed6:.6f}s, \n"
                #     f"_build_polygon_apply_signature={elapsed7:.6f}s, \n"
                # )


        except Exception as e:
            error("얼굴편집", f"랜드마크 드래그 최종 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            self._last_polygon_apply_signature = None

    def _ensure_polygon_apply_guard_state(self):
        if not hasattr(self, '_last_polygon_apply_signature'):
            self._last_polygon_apply_signature = None

    def _get_var_value_for_signature(self, attr_name, default=0.0):
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

    def _normalize_point_for_signature(self, point):
        if not point:
            return None
        try:
            return (round(float(point[0]), 4), round(float(point[1]), 4))
        except Exception:
            return None

    def _build_polygon_apply_signature(self, force_slider_mode=False):
        landmark_manager = getattr(self, 'landmark_manager', None)
        custom_signature = None
        left_center = None
        right_center = None
        if landmark_manager is not None:
            get_sig = getattr(landmark_manager, 'get_custom_landmarks_signature', None)
            if callable(get_sig):
                try:
                    custom_signature = get_sig()
                except Exception:
                    custom_signature = None
            left_center = self._normalize_point_for_signature(
                landmark_manager.get_left_iris_center_coord())
            right_center = self._normalize_point_for_signature(
                landmark_manager.get_right_iris_center_coord())

        slider_values = (
            self._get_var_value_for_signature('region_size_x', 1.0),
            self._get_var_value_for_signature('region_size_y', 1.0),
            self._get_var_value_for_signature('region_position_x', 0.0),
            self._get_var_value_for_signature('region_position_y', 0.0),
            self._get_var_value_for_signature('region_pivot_x', 0.0),
            self._get_var_value_for_signature('region_pivot_y', 0.0),
            self._get_var_value_for_signature('region_expansion_level', 1.0),
            self._get_var_value_for_signature('show_polygon_color', self.polygon_color_ix),
        )

        use_warping = getattr(self, 'use_landmark_warping', None)
        use_warping_flag = False
        if use_warping is not None and hasattr(use_warping, 'get'):
            try:
                use_warping_flag = bool(use_warping.get())
            except Exception:
                use_warping_flag = False

        iris_mapping_method = getattr(self, 'iris_mapping_method', None)
        iris_mapping_val = None
        if iris_mapping_method is not None and hasattr(iris_mapping_method, 'get'):
            try:
                iris_mapping_val = iris_mapping_method.get()
            except Exception:
                iris_mapping_val = None

        region_flags = None
        if hasattr(self, '_get_region_selection_flags'):
            try:
                region_flags = self._get_region_selection_flags()
            except Exception:
                region_flags = None

        current_tab = getattr(self, 'current_morphing_tab', '전체')
        last_selected = getattr(self, 'last_selected_landmark_index', None)

        return (
            custom_signature,
            left_center,
            right_center,
            slider_values,
            use_warping_flag,
            iris_mapping_val,
            region_flags,
            current_tab,
            last_selected,
            bool(force_slider_mode),
        )