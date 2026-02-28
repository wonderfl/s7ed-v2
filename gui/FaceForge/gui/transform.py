import math
import tkinter as tk
from tkinter import ttk

from gui.FaceForge.utils.morphing.adjustments.region import (
    adjust_region_size,
    adjust_region_position,
    adjust_region_size_with_axis,
)

# StateKeys import 추가
from .landmark import StateKeys

from gui.FaceForge.utils.elapsed import StopWatch
from gui.FaceForge.utils.morphing.region import _get_region_pivot

from utils.logger import debug, info, warn, error, log
from gui.FaceForge.utils.debugs import DEBUG_ELAPSED_TIME, DEBUG_MORPHING_UPDATE, DEBUG_APPLY_SLIDERS, DEBUG_APPLY_TRANSFORM


class TransformMixin:
    """이벤트 핸들러 기능 Mixin"""

    def get_bbox_lips(self, landmarks):
        if landmarks is None or len(landmarks) < 293:
            return "랜드마크 부족"

        _top = landmarks[13]     # 입술 중앙 상단
        _left = landmarks[61]    # 입술 왼쪽 끝
        _right = landmarks[291]  # 입술 오른쪽 끝
        _bottom = landmarks[292]   # 입술 중앙 하단
        #return f"lips[ ({_top[0]:.3f},{_top[1]:.3f}), ({_left[0]:.3f},{_left[1]:.3f}), ({_right[0]:.3f},{_right[1]:.3f}), ({_bottom[0]:.3f},{_bottom[1]:.3f}) ]"

        x_min = min(_top[0],_left[0],_right[0],_bottom[0])
        x_max = max(_top[0],_left[0],_right[0],_bottom[0])
        y_min = min(_top[1],_left[1],_right[1],_bottom[1])
        y_max = max(_top[1],_left[1],_right[1],_bottom[1])        
        return f"lip[ ({x_min:.1f}, {y_min:.1f}), ({x_max:.1f}, {y_max:.1f}) ]"

    def _apply_common_sliders_general_mode(self, image, selected_regions, slider_values, slider_conditions):
        from gui.FaceForge.utils import landmarks as utilmarks

        params = self._get_alignment_params()
        detected, _landmarks = utilmarks.detect_face_landmarks(image, params)
        if not detected:
            return image

        pivot_x = slider_values['pivot_x']
        pivot_y = slider_values['pivot_y']
        size_x = slider_values['size_x']
        size_y = slider_values['size_y']
        position_x = slider_values['position_x']
        position_y = slider_values['position_y']
        blend_ratio = slider_values['blend_ratio']

        size_condition = slider_conditions['size_condition']
        pos_x_condition = slider_conditions['pos_x_condition']
        pos_y_condition = slider_conditions['pos_y_condition']

        result = image
        use_guide_axis = self._should_use_guide_axis()
        guide_angle = None
        if use_guide_axis:
            guide_angle = self._get_guide_axis_angle(_landmarks, image.size)
            if guide_angle is None:
                if DEBUG_APPLY_TRANSFORM:
                    debug("_apply_common_sliders_general_mode", "지시선 축 각도 계산 실패 - 기본 축으로 폴백")
                use_guide_axis = False
            else:
                if DEBUG_APPLY_TRANSFORM:
                    debug( "_apply_common_sliders_general_mode",
                        f"angle={math.degrees(guide_angle):.1f}°, regions={len(selected_regions)}"
                    )

        for region_name, region_indecies in selected_regions:
            if size_condition:
                if use_guide_axis and guide_angle is not None:
                    if DEBUG_APPLY_TRANSFORM:
                        debug("_apply_common_sliders_general_mode", 
                            f"지시선 축 적용 대상: {region_name}, size=({size_x:.3f},{size_y:.3f}), "
                            f"region={region_name}, "
                        )

                    result = adjust_region_size_with_axis(
                        result,
                        region_name,
                        size_x=size_x,
                        size_y=size_y,
                        pivot_x=pivot_x,
                        pivot_y=pivot_y,
                        landmarks=_landmarks,
                        blend_ratio=blend_ratio,
                        guide_angle=guide_angle,
                    )
                else:
                    if DEBUG_APPLY_TRANSFORM:
                        debug("_apply_common_sliders_general_mode", f"기본 축 adjust_region_size 호출: region={region_name}")
                    result = adjust_region_size(
                        result,
                        region_name,
                        size_x,
                        size_y,
                        pivot_x,
                        pivot_y,
                        _landmarks,
                        blend_ratio,
                    )

                if result is None:
                    if DEBUG_APPLY_TRANSFORM:
                        warn("_apply_common_sliders_general_mode", f"{region_name} 크기 조절 결과가 None입니다")
                    result = image
                else:
                    params = self._get_alignment_params()
                    _, _landmarks = utilmarks.detect_face_landmarks(result, params)
                    if _landmarks is None:
                        if DEBUG_APPLY_TRANSFORM:
                            warn("_apply_common_sliders_general_mode", "랜드마크 재검출 실패 (지시선 축 적용)")
                        return result
                    if use_guide_axis:
                        guide_angle = self._get_guide_axis_angle(_landmarks, image.size)
                        if guide_angle is None:
                            if DEBUG_APPLY_TRANSFORM:
                                warn("_apply_common_sliders_general_mode", "지시선 축 재계산 실패 - 이후 기본 축 적용")
                            use_guide_axis = False
                    image = result

            if pos_x_condition or pos_y_condition:
                result = adjust_region_position(
                    result,
                    region_name,
                    position_x,
                    position_y,
                    pivot_x,
                    pivot_y,
                    _landmarks,
                )
                if result is None:
                    if DEBUG_APPLY_TRANSFORM:
                        warn("_apply_common_sliders_general_mode", f"{region_name} 위치 이동 결과가 None입니다")
                    result = image
                else:
                    params = self._get_alignment_params()
                    _, _landmarks = utilmarks.detect_face_landmarks(result, params)
                    image = result

        return result if result is not None else image

    def _get_guide_axis_info(self, landmarks, image_size):
        if not landmarks or not hasattr(self, 'guide_lines_manager'):
            return None
        try:
            img_width, img_height = image_size
        except Exception:
            return None

        try:
            left_center, right_center, angle = self.guide_lines_manager.get_eye_centers_and_angle(
                landmarks, img_width, img_height
            )
            if left_center is None or right_center is None or angle is None:
                # if DEBUG_APPLY_TRANSFORM:
                #     warn("_get_guide_axis_info", "지시선 축 정보를 가져오지 못했습니다")
                return None

            mid_center = (
                (left_center[0] + right_center[0]) / 2.0,
                (left_center[1] + right_center[1]) / 2.0,
            )
            guide_info = {
                'angle': angle,
                'left_center': left_center,
                'right_center': right_center,
                'mid_center': mid_center,
            }

            self.current_guide_axis_info = guide_info
            # if DEBUG_APPLY_TRANSFORM:
            #     info( "_get_guide_axis_info",
            #         f"지시선 축 정보 계산: angle={math.degrees(angle):.1f}°, left={left_center}, right={right_center}"
            #     )

            return guide_info
        except Exception as exc:
            error("_get_guide_axis_info", f"지시선 축 계산 실패: {exc}")
            import traceback
            traceback.print_exc()
            return None

    def _get_guide_axis_angle(self, landmarks, image_size):
        info = self._get_guide_axis_info(landmarks, image_size)
        return info['angle'] if info else None

    def _apply_guide_axis_transform(self, abs_x, abs_y, size_x, size_y, pos_x, pos_y, axis_info, pivot=None):
        if axis_info is None or (abs(size_x - 1.0) < 0.01 and abs(size_y - 1.0) < 0.01):
            return abs_x + pos_x, abs_y + pos_y

        #pivot_point = pivot or axis_info.get('mid_center') or axis_info.get('left_center') or axis_info.get('right_center')
        pivot_point = pivot
        if pivot_point is None:
            return abs_x + pos_x, abs_y + pos_y

        angle = axis_info.get('angle')
        if angle is None:
            return abs_x + pos_x, abs_y + pos_y

        cos_angle = axis_info.get('cos_angle') or math.cos(angle)
        sin_angle = axis_info.get('sin_angle') or math.sin(angle)

        pivot_x, pivot_y = pivot_point
        dx = abs_x - pivot_x
        dy = abs_y - pivot_y

        # 디버그 출력 (처음 3개 포인트만)
        if not hasattr(self, '_debug_rotation_count'):
            self._debug_rotation_count = 0

        if self._debug_rotation_count < 3:
            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_guide_axis_transform",
                    f"[DEBUG 전체탭] 원본: ({abs_x:.1f},{abs_y:.1f}), "
                    f"pivot=({pivot_x:.1f},{pivot_y:.1f}), dx={dx:.1f}, dy={dy:.1f}, "
                    f"angle={math.degrees(angle):.2f}°, cos={cos_angle:.3f}, sin={sin_angle:.3f}")
        self._debug_rotation_count += 1

        rotated_x = dx * cos_angle + dy * sin_angle
        rotated_y = -dx * sin_angle + dy * cos_angle

        if self._debug_rotation_count <= 3:
            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_guide_axis_transform", f"  회전후: ({rotated_x:.1f},{rotated_y:.1f})")

        rotated_x = rotated_x * size_x + pos_x
        rotated_y = rotated_y * size_y + pos_y

        if self._debug_rotation_count <= 3:
            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_guide_axis_transform", f"  스케일후: ({rotated_x:.1f},{rotated_y:.1f})")

        new_x = pivot_x + (rotated_x * cos_angle - rotated_y * sin_angle)
        new_y = pivot_y + (rotated_x * sin_angle + rotated_y * cos_angle)

        if self._debug_rotation_count <= 3:
            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_guide_axis_transform", 
                    f"  최종: ({new_x:.1f},{new_y:.1f}), "
                    f"  y변화: {abs_y:.1f} -> {new_y:.1f} (차이={new_y-abs_y:.1f})"
                )

        return new_x, new_y

    def _log_guide_axis_landmark_snapshot(self, label, landmarks, guide_axis_info):
        if DEBUG_APPLY_TRANSFORM:
            debug("_log_guide_axis_landmark_snapshot", f"{label}, info={guide_axis_info}")
        if not guide_axis_info or not landmarks:
            return
        idx = guide_axis_info.get('sample_index', 0)
        if idx < 0 or idx >= len(landmarks):
            idx = 0
        point = landmarks[idx]
        if not isinstance(point, tuple):
            try:
                img_width = getattr(self, 'preview_width', 800)
                img_height = getattr(self, 'preview_height', 1000)
                point = (point.x * img_width, point.y * img_height)
            except Exception:
                point = (0.0, 0.0)

        mid_center = guide_axis_info.get('mid_center')
        angle = guide_axis_info.get('angle')
        if mid_center is not None and angle is not None:
            dx = point[0] - mid_center[0]
            dy = point[1] - mid_center[1]
            # if DEBUG_APPLY_TRANSFORM:
            #     debug("_log_guide_axis_landmark_snapshot", 
            #         f"[{label}] sample_idx={idx}, point=({point[0]:.2f},{point[1]:.2f}), pivot=({mid_center[0]:.2f},{mid_center[1]:.2f}), vector=({dx:.2f},{dy:.2f}), angle={math.degrees(angle):.2f}°"
            #     )

    def _scale_relative(self, dx, dy, size_x, size_y, use_guide_axis, guide_axis_info, size_condition):
        if not size_condition:
            return dx, dy

        if use_guide_axis and guide_axis_info is not None:
            guide_angle = guide_axis_info.get('angle')
            if guide_angle is not None:
                cos_angle = math.cos(guide_angle)
                sin_angle = math.sin(guide_angle)
                rot_x = dx * cos_angle + dy * sin_angle
                rot_y = -dx * sin_angle + dy * cos_angle
                rot_x *= size_x
                rot_y *= size_y
                new_dx = rot_x * cos_angle - rot_y * sin_angle
                new_dy = rot_x * sin_angle + rot_y * cos_angle
                return new_dx, new_dy
        
        return dx * size_x, dy * size_y

    def _build_warp_regions(self, selected_regions, base_landmarks, expansion_level, pivot_add_x, pivot_add_y):
        warp_regions = []

        for region_name, region_pairs in selected_regions or []:
            flat_indices = sorted({idx for pair in region_pairs for idx in pair})
            if expansion_level > 0:
                region_indices = set(self._get_region_expanded( len(base_landmarks), region_pairs, expansion_level))            
                flat_indices = sorted(region_indices)
            pivot = _get_region_pivot(region_name, base_landmarks, pivot_add_x, pivot_add_y)
            warp_regions.append({
                "name": region_name,
                "indices": flat_indices,
                "pivot": pivot,
            })
        return warp_regions


    def _apply_common_sliders_to_landmarks(self, selected_regions, pivot_x, pivot_y,
                                          size_x, size_y, position_x, position_y, image):
        """고급 모드: 공통 슬라이더로 custom_landmarks의 포인트를 직접 조절"""
        try:
            from gui.FaceForge.utils.morphing.region import _get_region_pivot
            import gui.FaceForge.utils.landmarks as utilmarks

            elapsed = 0
            _timer = StopWatch()

            _timer.start()
            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_common_sliders_to_landmarks", 
                    f"regions:{len(selected_regions)}, "
                    f"pivot({pivot_x:.1f}, {pivot_y:.1f}), "
                    f"size({size_x:.1f}, {size_y:.1f}), "
                    f"pos({position_x:.1f}, {position_y:.1f})"
                )
                # for i, region in enumerate(selected_regions):
                #     print(f"  [{i}] {region[0]}, {len(region[1])}")

            # landmark_state에서 데이터 가져오기
            state = self.landmark_manager.get_landmark_state()

            context = state[StateKeys.SECTION_CONTEXT] or {}
            region_params = context.get(StateKeys.KEY_SLIDER_PARAMS, {})
            
            current_landmarks = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_FACE_LANDMARKS]
            original_face_landmarks = state[StateKeys.SECTION_ORIGINAL][StateKeys.KEY_FACE_LANDMARKS]
            if original_face_landmarks is None and current_landmarks:
                original_face_landmarks = current_landmarks[:468] if len(current_landmarks) >= 468 else current_landmarks
            original_iris_landmarks = state[StateKeys.SECTION_ORIGINAL][StateKeys.KEY_IRIS_LANDMARKS]
            
            dragged_indices = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_DRAGGED_INDICES]
            selected_indices = state[StateKeys.SECTION_WARP][StateKeys.KEY_SELECTED_INDICES]

            # 이미지 크기
            img_width, img_height = image.size

            # updated_landmarks 준비
            updated_landmarks = []

            base_landmarks = None
            if original_face_landmarks is not None:
                base_landmarks = original_face_landmarks
            elif current_landmarks is not None:
                base_landmarks = current_landmarks[:468] if len(current_landmarks) >= 468 else current_landmarks
            if base_landmarks is None:
                return image

            def _to_pixel_tuple(point):
                if isinstance(point, tuple):
                    return point
                return (point.x * img_width, point.y * img_height)
            
            base_pixels = [_to_pixel_tuple(point) for point in base_landmarks]
            original_from_state = state[StateKeys.SECTION_ORIGINAL][StateKeys.KEY_FACE_LANDMARKS]
            if original_from_state is not None:
                source = original_from_state[:468] if len(original_from_state) >= 468 else original_from_state
                base_pixels = [_to_pixel_tuple(point) for point in source]
            
            updated_landmarks = list(base_pixels)  # 얕은 복사만 수행

            # 드래그된 포인트 적용
            if current_landmarks is not None and len(current_landmarks) == 470:
                current_face_landmarks = current_landmarks[:468]
                if current_face_landmarks is not None and dragged_indices:
                    for idx in dragged_indices:
                        if 0 <= idx < len(current_face_landmarks) and idx < len(updated_landmarks):
                            if isinstance(current_face_landmarks[idx], tuple):
                                updated_landmarks[idx] = current_face_landmarks[idx]
                            else:
                                updated_landmarks[idx] = (
                                    current_face_landmarks[idx].x * img_width,
                                    current_face_landmarks[idx].y * img_height
                                )

            original_landmarks = self.landmark_manager.get_original_landmarks_full()

            size_x_condition = abs(size_x - 1.0) >= 0.01
            size_y_condition = abs(size_y - 1.0) >= 0.01
            size_condition = size_x_condition or size_y_condition

            use_guide_axis = self._should_use_guide_axis()
            guide_axis_info = self._get_guide_axis_info(updated_landmarks, image.size) if use_guide_axis else None

            elapsed1 = _timer.stop()
            if DEBUG_APPLY_TRANSFORM and guide_axis_info:
                debug("_apply_common_sliders_to_landmarks",
                      f"elapsed={elapsed1:.6}s, size({size_x:.1f},{size_y:.1f}), "
                      f"angle={math.degrees(guide_axis_info.get('angle', 0.0)):.2f}°")
            _timer.start()


            original_from_state = state[StateKeys.SECTION_ORIGINAL][StateKeys.KEY_FACE_LANDMARKS]
            if original_from_state is not None:
                base_for_reset = original_from_state[:468] if len(original_from_state) >= 468 else original_from_state
            else:
                base_for_reset = base_landmarks

            updated_landmarks = [point if isinstance(point, tuple) else (point.x * img_width, point.y * img_height) for point in base_for_reset]

            if current_landmarks is not None and len(current_landmarks) == 470 and dragged_indices:
                current_face_landmarks = current_landmarks[:468]
                for idx in dragged_indices:
                    if 0 <= idx < len(current_face_landmarks) and idx < len(updated_landmarks):
                        if isinstance(current_face_landmarks[idx], tuple):
                            updated_landmarks[idx] = current_face_landmarks[idx]
                        else:
                            updated_landmarks[idx] = (
                                current_face_landmarks[idx].x * img_width,
                                current_face_landmarks[idx].y * img_height
                            )

            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_common_sliders_to_landmarks",
                      f": {self.get_bbox_lips(updated_landmarks)} before")

            normalized_region_indices = {}
            def _flatten_indices(seq):
                for item in seq:
                    if isinstance(item, (list, tuple, set)):
                        yield from _flatten_indices(item)
                    elif isinstance(item, str):
                        if item.isdigit():
                            yield int(item)
                    elif isinstance(item, int):
                        yield item

            for region_name, entry in region_params.items():
                if not entry.get("applied"):
                    continue
            
                if region_name not in normalized_region_indices:
                    raw = entry.get("indices") or self._get_region_indices(region_name)
                    normalized_region_indices[region_name] = list(_flatten_indices(raw))
            
                region_indices = normalized_region_indices[region_name]
                if not region_indices:
                    continue
            
                sliders = entry.get("sliders")
                if not sliders:
                    continue

                log("_apply_common_sliders_to_landmarks",
                    f"region_name: {region_name}, sliders: {sliders}")

                expansion_level = sliders["expansion_level"]
                tesselation_graph = {}
                if expansion_level > 0:
                    try:
                        tesselation = self.TESSELATION

                        for idx1, idx2 in tesselation:
                            if idx1 < 468 and idx2 < 468 and idx1 < len(updated_landmarks) and idx2 < len(updated_landmarks):
                                if idx1 not in tesselation_graph:
                                    tesselation_graph[idx1] = []
                                if idx2 not in tesselation_graph:
                                    tesselation_graph[idx2] = []
                                tesselation_graph[idx1].append(idx2)
                                tesselation_graph[idx2].append(idx1)
                    except ImportError:
                        pass

                size_x = sliders["size_x"]
                size_y = sliders["size_y"]
                use_guide_axis = self._should_use_guide_axis()

                size_x_condition = abs(size_x - 1.0) >= 0.01
                size_y_condition = abs(size_y - 1.0) >= 0.01
                size_condition = size_x_condition or size_y_condition
            
                transformed = self._transform_selected_landmarks(
                    selected_regions=[(region_name, region_indices)],
                    updated_landmarks=updated_landmarks,
                    original_landmarks=original_landmarks,
                    center_offset_x=sliders["pivot_x"],
                    center_offset_y=sliders["pivot_y"],
                    position_x=sliders["position_x"],
                    position_y=sliders["position_y"],
                    image=image,
                    expansion_level=expansion_level,
                    tesselation_graph=tesselation_graph,
                    scale_relative_fn=lambda dx, dy: self._scale_relative(
                        dx, dy,
                        sliders["size_x"], sliders["size_y"],
                        use_guide_axis, guide_axis_info,
                        size_condition,
                    ),
                    dragged_indices=dragged_indices,
                    guide_axis_info=guide_axis_info,
                    size_x=sliders["size_x"],
                    size_y=sliders["size_y"],
                    use_guide_axis=use_guide_axis,
                )

            if DEBUG_APPLY_TRANSFORM:
                debug("_apply_common_sliders_to_landmarks",
                      f": {self.get_bbox_lips(updated_landmarks)}")

            self.landmark_manager.set_state_value(
                StateKeys.SECTION_TRANSFORMED,
                StateKeys.KEY_FACE_LANDMARKS,
                updated_landmarks
            )
            self.landmark_manager.set_state_value(
                StateKeys.SECTION_CURRENT,
                StateKeys.KEY_FACE_LANDMARKS,
                updated_landmarks
            )

            expansion_level = getattr(self, 'region_expansion_level', tk.IntVar(value=1)).get()
            warp_regions = self._build_warp_regions(
                selected_regions, updated_landmarks, expansion_level, pivot_x, pivot_y
            )

            self.landmark_manager.set_state_section(StateKeys.SECTION_WARP, {
                StateKeys.KEY_SOURCE_LANDMARKS: original_face_landmarks,
                StateKeys.KEY_TARGET_LANDMARKS: updated_landmarks,
                StateKeys.KEY_SELECTED_INDICES: warp_regions,
            })

            self.landmark_manager.set_current_landmarks(
                updated_landmarks,
                reason="_apply_common_sliders_to_landmarks",
            )

            elapsed2 = _timer.stop()
            elapsed = elapsed2 + elapsed1
            if DEBUG_APPLY_TRANSFORM and DEBUG_ELAPSED_TIME:
                log("_apply_common_sliders_to_landmarks", f"elapsed={elapsed:.6f}")

            return image

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._refresh_face_edit_display(
                image=True,
                polygons=self._is_polygon_display_enabled(),
                pivots=self._is_pivot_display_enabled(),
                guides=self._is_guides_display_enabled(),
                bbox=self._is_bbox_frame_display_enabled(),
                force_original=False,
            )
            return image

    
    def reset_morphing(self):
        """얼굴 특징 보정 값들을 모두 초기화"""
        
        debug("reset_morphing", f":")

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
        if hasattr(self, 'blend_ratio'):
            self.blend_ratio.set(1.0)
        
        # 눈 편집 고급 설정 초기화
        # 체크박스 설정들은 초기화하지 않음 (사용자가 선택한 상태 유지)
        # self.use_individual_eye_region.set(False)  # 눈 영역과 입술 영역 모두 통합된 변수 - 제거: 초기화 시 선택 상태 유지
        # self.use_landmark_warping.set(False)  # 랜드마크 직접 변형 모드 초기화 - 제거: 초기화 시 선택 상태 유지
        self.left_eye_size.set(1.0)
        self.right_eye_size.set(1.0)
        # self.eye_spacing.set(False)  # 제거: 초기화 시 선택 상태 유지
        self.left_eye_position_y.set(0.0)
        self.right_eye_position_y.set(0.0)
        self.left_eye_position_x.set(0.0)
        self.right_eye_position_x.set(0.0)
        # 눈 영역 표시는 초기화하지 않음 (사용자가 선택한 상태 유지)
        # self.show_eye_region.set(True)  # 기본값: True - 제거: 초기화 시 선택 상태 유지
        self.eye_region_padding.set(0.3)
        self.left_eye_region_padding.set(0.3)
        self.right_eye_region_padding.set(0.3)
        self.eye_region_offset_x.set(0.0)
        self.eye_region_offset_y.set(0.0)
        self.left_eye_region_offset_x.set(0.0)
        self.left_eye_region_offset_y.set(0.0)
        self.right_eye_region_offset_x.set(0.0)
        self.right_eye_region_offset_y.set(0.0)
        
        # 전체 탭 공통 슬라이더 초기화
        if hasattr(self, 'region_center_offset_x'):
            self.region_center_offset_x.set(0.0)
        if hasattr(self, 'region_center_offset_y'):
            self.region_center_offset_y.set(0.0)
        if hasattr(self, 'region_size_x'):
            self.region_size_x.set(1.0)
        if hasattr(self, 'region_size_y'):
            self.region_size_y.set(1.0)
        if hasattr(self, 'region_position_x'):
            self.region_position_x.set(0.0)
        if hasattr(self, 'region_position_y'):
            self.region_position_y.set(0.0)
        
        # 눈동자 중앙 포인트 좌표 초기화 (재계산을 위해)
        if hasattr(self, '_left_iris_center_coord'):
            self._left_iris_center_coord = None
        if hasattr(self, '_right_iris_center_coord'):
            self._right_iris_center_coord = None
        
        # 초기화 전에 original_iris_landmarks 확인 (디버깅용)
        original_iris_before = self.landmark_manager.get_original_iris_landmarks()
        if DEBUG_APPLY_TRANSFORM:
            debug("reset_morphing", f"reset 전 original_iris_landmarks: {original_iris_before is not None}, 길이: {len(original_iris_before) if original_iris_before else 0}")
        
        # LandmarkManager를 사용하여 초기화
        self.landmark_manager.reset(keep_original=True)

        # 👇 이 한 줄을 추가해야 함
        self.landmark_manager.reset_current_landmarks()  # 현재 랜드마크도 초기화
    

        # property가 자동으로 처리하므로 동기화 코드 불필요
        self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
        self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
        
        # 초기화 후 original_iris_landmarks 확인 (디버깅용)
        original_iris_after = self.landmark_manager.get_original_iris_landmarks()
        if DEBUG_APPLY_TRANSFORM:
            debug("reset_morphing", f"reset 후 original_iris_landmarks: {original_iris_after is not None}, 길이: {len(original_iris_after) if original_iris_after else 0}")
        
        # 초기화 후 항상 중앙 포인트 계산 및 설정 (눈동자나 tesselation 선택 시 폴리곤 그리기 위해 필요)
        # 주의: 이미지 로딩 시 original_iris_landmarks가 설정되었다면 reset(keep_original=True)로 유지되므로 재감지하지 않음
        if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
            if self.current_image is not None:
                img_width, img_height = self.current_image.size
                # original_iris_landmarks 확인 (이미지 로딩 시 설정된 값 유지)
                original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                
                # 전체 원본 랜드마크 가져오기 (478개 또는 468개)
                original_landmarks_full = self.landmark_manager.get_original_landmarks_full()
                
                # 중앙 포인트 계산
                left_center = None
                right_center = None
                
                if original_iris_landmarks is not None and len(original_iris_landmarks) == 10:
                    # 눈동자 랜드마크에서 중앙 포인트 계산
                    left_iris_points = original_iris_landmarks[:5]
                    right_iris_points = original_iris_landmarks[5:]
                    if left_iris_points:
                        left_center = (
                            sum(p[0] for p in left_iris_points) / len(left_iris_points),
                            sum(p[1] for p in left_iris_points) / len(left_iris_points)
                        )
                    if right_iris_points:
                        right_center = (
                            sum(p[0] for p in right_iris_points) / len(right_iris_points),
                            sum(p[1] for p in right_iris_points) / len(right_iris_points)
                        )
                elif original_landmarks_full is not None:
                    # 전체 랜드마크에서 직접 계산
                    left_iris_indices, right_iris_indices = self._get_iris_indices()
                    left_center = self._calculate_iris_center(original_landmarks_full, left_iris_indices, img_width, img_height)
                    right_center = self._calculate_iris_center(original_landmarks_full, right_iris_indices, img_width, img_height)
                
                if left_center is not None and right_center is not None:
                    # 항상 중앙 포인트 설정 (눈동자나 tesselation 선택 시 폴리곤 그리기 위해 필요)
                    self.landmark_manager.set_custom_iris_centers([left_center, right_center])
                    self.landmark_manager.set_iris_center_coords(left_center, right_center)
                    self._left_iris_center_coord = left_center
                    self._right_iris_center_coord = right_center
                    
                    # custom_landmarks에 중앙 포인트 추가 (470개 구조로 변환)
                    custom = self.landmark_manager.get_custom_landmarks()
                    if custom is not None and len(custom) == 468:
                        # 468개에 중앙 포인트 2개 추가하여 470개로 변환
                        custom_with_centers = list(custom) + [left_center, right_center]
                        self.landmark_manager.set_custom_landmarks(custom_with_centers, reason="reset_morphing: 중앙 포인트 추가")
        
        # UI 업데이트 (개별 적용 모드 변경)
        self.on_individual_region_change()
        
        # 라벨 업데이트만 수행 (이미지 업데이트는 apply_editing에서 처리)
        self.update_labels_only()
        
        # 편집 적용 (on_morphing_change는 내부에서 apply_editing을 호출할 수 있으므로 중복 방지)
        if self.current_image is not None:
            self.apply_editing()
            
            # 초기화 후 폴리곤 다시 그리기 (눈동자나 tesselation 선택 시 보이도록)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
                
    def _handle_tesselation_transform_mode(
        self,
        selected_regions,
        dragged_indices,
        updated_landmarks,
        center_offset_x,
        center_offset_y,
        size_x,
        size_y,
        position_x,
        position_y,
        image,
        expansion_level,
        tesselation_graph,
        scale_relative_fn,
    ):
        if 'tesselation' not in selected_regions or len(selected_regions) != 1:
            return False

        all_indices = set()
        for region_name in selected_regions:
            result = self._get_region_indices(region_name)
            if not result:
                continue
            all_indices.update(set(result[1]))

        try:
            from utils.face_morphing.region_extraction import get_iris_indices

            left_iris_indices, right_iris_indices = get_iris_indices()
            iris_indices = set(left_iris_indices + right_iris_indices)
        except ImportError:
            iris_indices = {469, 470, 471, 472, 474, 475, 476, 477}

        iris_indices_in_all = all_indices & iris_indices
        face_indices = all_indices - iris_indices

        if expansion_level > 0 and tesselation_graph:
            current_indices = face_indices.copy()
            for _ in range(expansion_level):
                next_level_indices = set()
                for idx in current_indices:
                    if idx in tesselation_graph:
                        for neighbor in tesselation_graph[idx]:
                            if neighbor < len(updated_landmarks) and neighbor not in iris_indices:
                                next_level_indices.add(neighbor)
                face_indices.update(next_level_indices)
                current_indices = next_level_indices

        face_indices_for_transform = face_indices - dragged_indices
        self._apply_tesselation_transform(
            updated_landmarks,
            face_indices_for_transform,
            iris_indices_in_all,
            center_offset_x,
            center_offset_y,
            size_x,
            size_y,
            position_x,
            position_y,
            image,
            scale_relative_fn=scale_relative_fn,
        )
        return True

    def _transform_selected_landmarks(
        self,
        selected_regions,
        updated_landmarks,
        original_landmarks,
        center_offset_x,
        center_offset_y,
        position_x,
        position_y,
        image,
        expansion_level,
        tesselation_graph,
        scale_relative_fn,
        dragged_indices,
        guide_axis_info=None,
        size_x=1.0,
        size_y=1.0,
        use_guide_axis=False,
    ):
        from gui.FaceForge.utils.morphing.region import _get_region_pivot
        transformed_indices = set()

        region_centers = {}
        for _name, _indices in selected_regions:
            if not self._has_region_name(_name):
                continue
            center = _get_region_pivot(_name, original_landmarks, center_offset_x, center_offset_y)
            if center is None:
                continue
            region_centers[_name] = center

        axis_pivot = None
        if guide_axis_info is not None and guide_axis_info.get('mid_center'):
            pivot_x, pivot_y = guide_axis_info['mid_center']
            axis_pivot = (
                pivot_x + center_offset_x,
                pivot_y + center_offset_y,
            )

        print("region_centers", region_centers)

        for _name, _indices in selected_regions:
            if not self._has_region_name(_name):
                continue

            print("_transform_selected_landmarks",f"{_name}")

            region_indices = set()
            if all(isinstance(item, int) for item in _indices):
                region_indices.update(_indices)
            else:
                for pair in _indices:
                    if isinstance(pair, (list, tuple)):
                        region_indices.update(pair)
                    else:
                        region_indices.add(pair)

            if expansion_level > 0:
                region_indices = set(self._get_region_expanded( len(original_landmarks),list( region_indices), expansion_level))
            elif 'eyebrow' in _name.lower():
                if DEBUG_APPLY_TRANSFORM:
                    warn( "_transform_selected_landmarks",
                        f"{region_name} 확장 실패: expansion_level={expansion_level}, tesselation_graph 크기={len(tesselation_graph)}",
                    )

            center_x, center_y = region_centers[_name]
            
            #pivot_for_region = axis_pivot if axis_pivot is not None else (center_x, center_y)
            pivot_for_region = (center_x, center_y)

            use_face_axis = (
                use_guide_axis
                and guide_axis_info is not None
                and (abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01)
            )

            if DEBUG_APPLY_TRANSFORM:
                info( "_transform_selected_landmarks",
                    f"{_name}: indices={len(_indices)}, pivot=({pivot_for_region[0]:.1f}, {pivot_for_region[1]:.1f}), "
                    f"size({size_x:.1f},{size_y:.1f}), pos({position_x:.1f},{position_y:.1f})"
                )

            sample_check_done = False

            for idx in region_indices:
                if idx in transformed_indices or idx in dragged_indices or idx >= len(updated_landmarks):
                    continue

                if isinstance(updated_landmarks[idx], tuple):
                    point_x, point_y = updated_landmarks[idx]
                else:
                    img_width, img_height = image.size
                    point_x = updated_landmarks[idx].x * img_width
                    point_y = updated_landmarks[idx].y * img_height

                rel_x = point_x - center_x
                rel_y = point_y - center_y
                rel_x, rel_y = scale_relative_fn(rel_x, rel_y)
                rel_x += position_x
                rel_y += position_y
                new_point = (center_x + rel_x, center_y + rel_y)

                denom = point_x - center_x
                if not sample_check_done and abs(rel_x) > 1e-3 and abs(denom) > 1e-6:
                    actual_scale = rel_x / denom
                    #print(f"[scale-check] idx={idx}, slider={size_x:.2f}, actual={actual_scale:.2f}")
                    sample_check_done = True

                updated_landmarks[idx] = new_point
                transformed_indices.add(idx)

        return transformed_indices