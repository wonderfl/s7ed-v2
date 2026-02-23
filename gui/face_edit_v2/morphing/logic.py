"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
"""
import math
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform

from .editing_steps import EditingStepsMixin
from utils.logger import print_info, print_debug, print_error, print_warning



class LogicMixin(EditingStepsMixin):
    """편집 적용 및 보정 로직 기능 Mixin"""
    
    def _convert_landmarks_to_tuples(self, landmarks, img_width, img_height):
        """랜드마크를 tuple 리스트로 변환"""
        result = []
        for landmark in landmarks:
            if isinstance(landmark, tuple):
                result.append(landmark)
            else:
                result.append((landmark.x * img_width, landmark.y * img_height))
        return result
    
    def _transform_eye_center(
        self,
        orig_eye_center,
        center_x,
        center_y,
        size_x,
        size_y,
        position_x,
        position_y,
        scale_relative_fn=None,
    ):
        """원본 눈 중심점을 얼굴 전체 중심점 기준으로 변형"""
        rel_x = orig_eye_center[0] - center_x
        rel_y = orig_eye_center[1] - center_y

        size_condition = abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01
        if scale_relative_fn is not None:
            rel_x, rel_y = scale_relative_fn(rel_x, rel_y)
        elif size_condition:
            rel_x *= size_x
            rel_y *= size_y

        # 위치 이동
        rel_x += position_x
        rel_y += position_y

        return center_x + rel_x, center_y + rel_y
    
    def _calculate_and_update_iris_center(self, eye_side, orig_eye_center, trans_eye_center, 
                                         original_landmarks, img_width, img_height, 
                                         size_x, size_y, iris_indices_in_all, updated_landmarks, scale_relative_fn=None):
        """눈동자 중심점 계산 및 업데이트
        
        Args:
            eye_side: 'left' 또는 'right'
            orig_eye_center: 원본 눈 중심점 (x, y)
            trans_eye_center: 변형된 눈 중심점 (x, y)
            original_landmarks: 원본 랜드마크
            img_width, img_height: 이미지 크기
            size_x, size_y: 크기 비율
            iris_indices_in_all: 적용할 눈동자 인덱스 집합
            updated_landmarks: 업데이트할 랜드마크 리스트
        """
        try:
            from utils.face_morphing.region_extraction import get_iris_indices
            left_iris_indices, right_iris_indices = get_iris_indices()
            iris_indices = left_iris_indices if eye_side == 'left' else right_iris_indices
        except ImportError:
            # 폴백: 하드코딩된 인덱스 사용
            if eye_side == 'left':
                iris_indices = [474, 475, 476, 477]  # LEFT_IRIS
            else:
                iris_indices = [469, 470, 471, 472]  # RIGHT_IRIS
        
        # 눈동자 포인트 추출
        iris_points_orig = []
        for idx in iris_indices:
            if idx < len(original_landmarks):
                if isinstance(original_landmarks[idx], tuple):
                    iris_points_orig.append(original_landmarks[idx])
                else:
                    iris_points_orig.append((
                        original_landmarks[idx].x * img_width,
                        original_landmarks[idx].y * img_height
                    ))
        
        if not iris_points_orig:
            return
        
        # 원본 눈동자 중앙 포인트
        orig_iris_center_x = sum(p[0] for p in iris_points_orig) / len(iris_points_orig)
        orig_iris_center_y = sum(p[1] for p in iris_points_orig) / len(iris_points_orig)
        
        # 원본 눈 중심점 기준 상대 좌표
        orig_rel_iris_x = orig_iris_center_x - orig_eye_center[0]
        orig_rel_iris_y = orig_iris_center_y - orig_eye_center[1]
        
        # 눈 중심점 기준으로 변형 (가이드 축 스케일 사용 가능)
        size_condition = abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01
        if scale_relative_fn is not None:
            new_rel_iris_x, new_rel_iris_y = scale_relative_fn(orig_rel_iris_x, orig_rel_iris_y)
        elif size_condition:
            new_rel_iris_x = orig_rel_iris_x * size_x
            new_rel_iris_y = orig_rel_iris_y * size_y
        else:
            new_rel_iris_x = orig_rel_iris_x
            new_rel_iris_y = orig_rel_iris_y
        
        # 변형된 눈 중심점 기준 새로운 좌표
        new_iris_center_x = trans_eye_center[0] + new_rel_iris_x
        new_iris_center_y = trans_eye_center[1] + new_rel_iris_y
        
        # 중앙 포인트 좌표 업데이트 (LandmarkManager 사용)
        if eye_side == 'left':
            self.landmark_manager.set_iris_center_coords(
                (new_iris_center_x, new_iris_center_y),
                self.landmark_manager.get_right_iris_center_coord()
            )
        else:
            self.landmark_manager.set_iris_center_coords(
                self.landmark_manager.get_left_iris_center_coord(),
                (new_iris_center_x, new_iris_center_y)
            )
        
        # 하위 호환성
        if eye_side == 'left':
            if hasattr(self, '_left_iris_center_coord'):
                self._left_iris_center_coord = (new_iris_center_x, new_iris_center_y)
        else:
            if hasattr(self, '_right_iris_center_coord'):
                self._right_iris_center_coord = (new_iris_center_x, new_iris_center_y)
        
        # Tesselation 선택 시에는 눈동자 포인트를 제거하고 중앙 포인트를 추가하는 방식으로 처리
        # 따라서 여기서는 updated_landmarks를 직접 수정하지 않음
        # (final_landmarks 생성 시 눈동자 포인트 제거 및 중앙 포인트 추가)
    
    def _apply_tesselation_transform(self, updated_landmarks, face_indices, iris_indices_in_all,
                                    center_offset_x, center_offset_y, size_x, size_y,
                                    position_x, position_y, image, scale_relative_fn=None):
        """Tesselation 선택 시 전체 얼굴 변형 적용"""
        # 전체 얼굴 중심점 계산 (눈동자 제외)
        if not face_indices:
            return
        
        x_coords = []
        y_coords = []
        img_width, img_height = image.size
        
        for idx in face_indices:
            if idx < len(updated_landmarks):
                point = updated_landmarks[idx]
                if isinstance(point, tuple):
                    x_coords.append(point[0])
                    y_coords.append(point[1])
                else:
                    x_coords.append(point.x * img_width)
                    y_coords.append(point.y * img_height)
        
        if not x_coords or not y_coords:
            return
        
        center_x = sum(x_coords) / len(x_coords) + center_offset_x
        center_y = sum(y_coords) / len(y_coords) + center_offset_y
        
        # 얼굴 포인트를 전체 중심점으로 변형
        for idx in face_indices:
            if idx >= len(updated_landmarks):
                continue
            
            # 현재 포인트 좌표
            if isinstance(updated_landmarks[idx], tuple):
                point_x, point_y = updated_landmarks[idx]
            else:
                point_x = updated_landmarks[idx].x * img_width
                point_y = updated_landmarks[idx].y * img_height
            
            # 중심점 기준 상대 좌표
            rel_x = point_x - center_x
            rel_y = point_y - center_y
            
            # 크기 조절 (가이드 축 스케일 사용 가능)
            if scale_relative_fn is not None:
                rel_x, rel_y = scale_relative_fn(rel_x, rel_y)
            elif abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
                rel_x *= size_x
                rel_y *= size_y
            
            # 위치 이동
            rel_x += position_x
            rel_y += position_y
            
            # 새로운 좌표 계산
            new_x = center_x + rel_x
            new_y = center_y + rel_y
            
            # 업데이트
            updated_landmarks[idx] = (new_x, new_y)
        
        # 눈동자는 눈 영역의 변형을 따라야 함
        if iris_indices_in_all and hasattr(self, 'original_landmarks') and self.original_landmarks is not None:
            from utils.face_landmarks import get_key_landmarks
            
            # 원본 랜드마크에서 눈 중심점 계산
            original_landmarks_for_key = self._convert_landmarks_to_tuples(
                self.original_landmarks, img_width, img_height
            )
            original_key_landmarks = get_key_landmarks(original_landmarks_for_key)
            
            if original_key_landmarks:
                # 왼쪽 눈 처리
                if original_key_landmarks.get('left_eye'):
                    orig_left_eye = original_key_landmarks['left_eye']
                    trans_left_eye = self._transform_eye_center(
                        orig_left_eye, center_x, center_y, size_x, size_y, position_x, position_y,
                        scale_relative_fn=scale_relative_fn
                    )
                    self._calculate_and_update_iris_center(
                        'left', orig_left_eye, trans_left_eye,
                        self.original_landmarks, img_width, img_height,
                        size_x, size_y, iris_indices_in_all, updated_landmarks
                    )
                
                # 오른쪽 눈 처리
                if original_key_landmarks.get('right_eye'):
                    orig_right_eye = original_key_landmarks['right_eye']
                    trans_right_eye = self._transform_eye_center(
                        orig_right_eye, center_x, center_y, size_x, size_y, position_x, position_y,
                        scale_relative_fn=scale_relative_fn
                    )
                    self._calculate_and_update_iris_center(
                        'right', orig_right_eye, trans_right_eye,
                        self.original_landmarks, img_width, img_height,
                        size_x, size_y, iris_indices_in_all, updated_landmarks
                    )
    
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
            self._refresh_face_edit_display(
                image=True,
                landmarks=True,
                overlays=True,
                guide_lines=True,
                force_original=True,
            )
            
            if abs(angle) > 0.1:
                self.status_label.config(text=f"얼굴 정렬 완료 (회전: {angle:.1f}도)", fg="green")
            else:
                self.status_label.config(text="얼굴 정렬 완료 (이미 정렬됨)", fg="green")
                
        except Exception as e:
            self.status_label.config(text=f"얼굴 정렬 실패: {e}", fg="red")
            # 정렬 실패 시 원본 이미지 사용
            self.aligned_image = None
            self.edited_image = self.current_image.copy()
            # 편집 적용 (정렬 없이)
            self.apply_editing()
    
    def _apply_common_sliders(self, image, base_image=None):
        """공통 슬라이더(Size, Position, Center Offset) 적용"""
        
        print_debug("_apply_common_sliders",f"_apply_common_sliders: called..")
        if image is None:
            return image
        
        try:
            is_advanced_mode = self._is_advanced_mode()
            selected_regions = self._get_selected_regions()
            slider_values, slider_conditions = self._get_common_slider_values()
        except Exception as e:
            print(f"[DEBUG] 고급모드 확인 실패: {e}")
            return image
        
        print(f"[DEBUG] 고급모드: {is_advanced_mode}, 선택된 부위: {selected_regions}")
        print(f"[DEBUG] use_landmark_warping: {getattr(self, 'use_landmark_warping', None)}")
        print(f"[DEBUG] custom_landmarks: {hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None}")
        
        if not selected_regions:
            return image

        if is_advanced_mode:
            return self._handle_advanced_mode(selected_regions, slider_values, image)

        if getattr(self, 'debug_guide_axis', False):
            size_x = slider_values.get('size_x')
            size_y = slider_values.get('size_y')
            center_offset_x = slider_values.get('center_offset_x')
            center_offset_y = slider_values.get('center_offset_y')
            print(
                f"[GuideAxis] sliders size_x={size_x} size_y={size_y} "
                f"center_offset=({center_offset_x},{center_offset_y})"
            )

        return self._apply_common_sliders_general_mode(
            image=image,
            selected_regions=selected_regions,
            slider_values=slider_values,
            slider_conditions=slider_conditions,
        )

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
            region_indices = set(self._get_region_indices(region_name))
            all_indices.update(region_indices)

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
        from utils.face_morphing.region_extraction import _get_region_center

        print_debug("얼굴편집", f"_transform_selected_landmarks 호출: selected_regions={selected_regions}")
        print(f"[DEBUG] size_x={size_x}, size_y={size_y}, center_offset_x={center_offset_x}, center_offset_y={center_offset_y}")

        transformed_indices = set()

        region_centers = {}
        for region_name in selected_regions:
            region_indices = set(self._get_region_indices(region_name))
            if not region_indices:
                continue

            center = _get_region_center(region_name, original_landmarks, center_offset_x, center_offset_y)
            if center is None:
                continue
            region_centers[region_name] = center

        axis_pivot = None
        if guide_axis_info is not None and guide_axis_info.get('mid_center'):
            pivot_x, pivot_y = guide_axis_info['mid_center']
            axis_pivot = (
                pivot_x + center_offset_x,
                pivot_y + center_offset_y,
            )

        for region_name in selected_regions:
            region_indices = set(self._get_region_indices(region_name))
            if not region_indices or region_name not in region_centers:
                continue

            if expansion_level > 0 and tesselation_graph:
                current_indices = region_indices.copy()
                for _ in range(expansion_level):
                    next_level_indices = set()
                    for idx in current_indices:
                        if idx in tesselation_graph:
                            for neighbor in tesselation_graph[idx]:
                                if neighbor < len(updated_landmarks):
                                    next_level_indices.add(neighbor)
                    region_indices.update(next_level_indices)
                    current_indices = next_level_indices
            elif 'eyebrow' in region_name.lower():
                print_warning(
                    "얼굴편집",
                    f"{region_name} 확장 실패: expansion_level={expansion_level}, tesselation_graph 크기={len(tesselation_graph)}",
                )

            center_x, center_y = region_centers[region_name]

            use_global_axis = (
                use_guide_axis
                and guide_axis_info is not None
                and (abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01)
            )

            #pivot_for_region = axis_pivot if axis_pivot is not None else (center_x, center_y)
            pivot_for_region = (center_x, center_y)
            print_debug(
                "얼굴편집",
                f"가이드축 사용: {use_guide_axis}, " + \
                f"region={region_name}, pivot={pivot_for_region}\n" + \
                f"use_global_axis={use_global_axis}, " + \
                f"size_x={size_x}, size_y={size_y}, " + \
                f"position_x={position_x}, position_y={position_y}"
            )

            if region_name in ['left_iris', 'right_iris']:
                iris_points_orig = []
                for idx in region_indices:
                    if idx < len(self.original_landmarks):
                        if isinstance(self.original_landmarks[idx], tuple):
                            iris_points_orig.append(self.original_landmarks[idx])
                        else:
                            img_width, img_height = image.size
                            iris_points_orig.append(
                                (
                                    self.original_landmarks[idx].x * img_width,
                                    self.original_landmarks[idx].y * img_height,
                                )
                            )

                if iris_points_orig:
                    orig_iris_center_x = sum(p[0] for p in iris_points_orig) / len(iris_points_orig)
                    orig_iris_center_y = sum(p[1] for p in iris_points_orig) / len(iris_points_orig)

                    rel_x = orig_iris_center_x - center_x
                    rel_y = orig_iris_center_y - center_y

                    before_rel_x, before_rel_y = rel_x, rel_y
                    rel_x, rel_y = scale_relative_fn(rel_x, rel_y)
                    if (before_rel_x, before_rel_y) != (rel_x, rel_y):
                        print(
                            "얼굴편집",
                            f"랜드마크 변형: before=({before_rel_x:.3f},{before_rel_y:.3f}), after=({rel_x:.3f},{rel_y:.3f})",
                        )

                    rel_x += position_x
                    rel_y += position_y

                    new_iris_center_x = center_x + rel_x
                    new_iris_center_y = center_y + rel_y

                    if region_name == 'left_iris':
                        self.landmark_manager.set_iris_center_coords(
                            (new_iris_center_x, new_iris_center_y),
                            self.landmark_manager.get_right_iris_center_coord(),
                        )
                    else:
                        self.landmark_manager.set_iris_center_coords(
                            self.landmark_manager.get_left_iris_center_coord(),
                            (new_iris_center_x, new_iris_center_y),
                        )

                    for idx in region_indices:
                        if idx not in transformed_indices and idx < len(updated_landmarks):
                            updated_landmarks[idx] = (new_iris_center_x, new_iris_center_y)
                            transformed_indices.add(idx)
            else:
                print_debug("얼굴편집", f"region={region_name}, region_indices 개수={len(region_indices)}, use_guide_axis={use_guide_axis}")
                for idx in region_indices:
                    if idx in transformed_indices or idx in dragged_indices or idx >= len(updated_landmarks):
                        continue

                    if isinstance(updated_landmarks[idx], tuple):
                        point_x, point_y = updated_landmarks[idx]
                    else:
                        img_width, img_height = image.size
                        point_x = updated_landmarks[idx].x * img_width
                        point_y = updated_landmarks[idx].y * img_height

                    print_debug(
                        "얼굴편집",
                        f"포인트 변환: idx={idx}, point=({point_x:.1f},{point_y:.1f}), center=({center_x:.1f},{center_y:.1f})"
                    )

                    rel_x = point_x - center_x
                    rel_y = point_y - center_y
                    rel_x, rel_y = scale_relative_fn(rel_x, rel_y)
                    rel_x += position_x
                    rel_y += position_y
                    new_point = (center_x + rel_x, center_y + rel_y)                        

                    updated_landmarks[idx] = new_point
                    transformed_indices.add(idx)

        return transformed_indices

    def _is_advanced_mode(self):
        use_warping = getattr(self, 'use_landmark_warping', None)
        has_custom_landmarks = hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None
        result = (
            use_warping is not None and
            hasattr(use_warping, 'get') and
            use_warping.get() and
            has_custom_landmarks
        )
        print_debug("얼굴편집", f"_is_advanced_mode: use_warping={use_warping}, use_warping.get()={use_warping.get() if use_warping and hasattr(use_warping, 'get') else 'N/A'}, has_custom_landmarks={has_custom_landmarks}, result={result}")
        return result

    def _should_use_guide_axis(self):
        return (
            hasattr(self, 'use_guide_line_scaling') and
            hasattr(self.use_guide_line_scaling, 'get') and
            self.use_guide_line_scaling.get() and
            hasattr(self, 'guide_lines_manager')
        )

    def _get_selected_regions(self):
        regions = []
        attr_pairs = [
            ('show_face_oval', 'face_oval'),
            ('show_left_eye', 'left_eye'),
            ('show_right_eye', 'right_eye'),
            ('show_left_eyebrow', 'left_eyebrow'),
            ('show_right_eyebrow', 'right_eyebrow'),
            ('show_nose', 'nose'),
            ('show_lips', 'lips'),
            ('show_left_iris', 'left_iris'),
            ('show_right_iris', 'right_iris'),
            ('show_contours', 'contours'),
            ('show_tesselation', 'tesselation'),
        ]
        for attr_name, region_name in attr_pairs:
            var = getattr(self, attr_name, None)
            if var is not None and hasattr(var, 'get') and var.get():
                regions.append(region_name)
        return regions

    def _get_common_slider_values(self):
        values = {
            'center_offset_x': self.region_center_offset_x.get(),
            'center_offset_y': self.region_center_offset_y.get(),
            'size_x': self.region_size_x.get(),
            'size_y': self.region_size_y.get(),
            'position_x': self.region_position_x.get(),
            'position_y': self.region_position_y.get(),
            'blend_ratio': self.blend_ratio.get() if hasattr(self, 'blend_ratio') else 1.0,
        }
        conditions = {
            'size_x_condition': abs(values['size_x'] - 1.0) >= 0.01,
            'size_y_condition': abs(values['size_y'] - 1.0) >= 0.01,
            'offset_x_condition': abs(values['center_offset_x']) >= 0.1,
            'offset_y_condition': abs(values['center_offset_y']) >= 0.1,
            'pos_x_condition': abs(values['position_x']) >= 0.1,
            'pos_y_condition': abs(values['position_y']) >= 0.1,
        }
        conditions['size_condition'] = conditions['size_x_condition'] or conditions['size_y_condition']
        return values, conditions

    def _log_polygon_debug_info(self, face_landmarks, transformed_indices, original_face_landmarks_tuple, has_iris_centers):
        try:
            transformed_count = len(transformed_indices) if transformed_indices else 0
            total_points = len(face_landmarks) if face_landmarks is not None else 0
            original_count = len(original_face_landmarks_tuple) if original_face_landmarks_tuple is not None else 0
            print(
                "얼굴편집",
                f"폴리곤 디버그: transformed={transformed_count}, face_points={total_points}, original_tuple={original_count}, iris_centers={has_iris_centers}",
            )
        except Exception as exc:  # pylint: disable=broad-except
            print("얼굴편집", f"폴리곤 디버그 로그 실패: {exc}")

    def _handle_advanced_mode(self, selected_regions, slider_values, image):
        center_offset_x = slider_values['center_offset_x']
        center_offset_y = slider_values['center_offset_y']
        size_x = slider_values['size_x']
        size_y = slider_values['size_y']
        position_x = slider_values['position_x']
        position_y = slider_values['position_y']

        print(f"_handle_advanced_mode: called.. {selected_regions}")

        # NOTE: 전체 탭 size X/Y는 custom_landmarks를 직접 변형하며, 현재는 회전 정보 없이 수평/수직 스케일만 적용된다.
        #       가이드축 연동 시점은 이 호출 이후 `_collect_landmark_transform_context` → `_transform_selected_landmarks` 흐름이다.
        result = self._apply_common_sliders_to_landmarks(
            selected_regions,
            center_offset_x,
            center_offset_y,
            size_x,
            size_y,
            position_x,
            position_y,
            image,
        )

        if result is not None and result != image:
            self.edited_image = result
            self._refresh_face_edit_display(
                image=True,
                landmarks=True,
                overlays=True,
                guide_lines=True,
                force_original=False,
            )

        return result

    def _apply_common_sliders_general_mode(self, image, selected_regions, slider_values, slider_conditions):
        import utils.face_landmarks as face_landmarks

        landmarks, _ = face_landmarks.detect_face_landmarks(image)
        if landmarks is None:
            return image

        from utils.face_morphing.adjustments import (
            adjust_region_size,
            adjust_region_position,
            adjust_region_size_with_axis,
        )

        center_offset_x = slider_values['center_offset_x']
        center_offset_y = slider_values['center_offset_y']
        size_x = slider_values['size_x']
        size_y = slider_values['size_y']
        position_x = slider_values['position_x']
        position_y = slider_values['position_y']
        blend_ratio = slider_values['blend_ratio']

        size_condition = slider_conditions['size_condition']
        pos_x_condition = slider_conditions['pos_x_condition']
        pos_y_condition = slider_conditions['pos_y_condition']

        result = image
        use_guide_axis = size_condition and self._should_use_guide_axis()
        guide_angle = None
        if use_guide_axis:
            guide_angle = self._get_guide_axis_angle(landmarks, image.size)
            if guide_angle is None:
                print("얼굴편집", "지시선 축 각도 계산 실패 - 기본 축으로 폴백")
                use_guide_axis = False
            else:
                print(
                    "얼굴편집",
                    f"전체탭 축 스케일 시작: angle={math.degrees(guide_angle):.1f}°, regions={len(selected_regions)}"
                )

        for region_name in selected_regions:
            if size_condition:
                if use_guide_axis and guide_angle is not None:
                    print("얼굴편집", f"지시선 축 적용 대상: {region_name}, size=({size_x:.3f},{size_y:.3f})")
                    print("얼굴편집", f"adjust_region_size_with_axis 호출: region={region_name}")
                    result = adjust_region_size_with_axis(
                        result,
                        region_name,
                        size_x=size_x,
                        size_y=size_y,
                        center_offset_x=center_offset_x,
                        center_offset_y=center_offset_y,
                        landmarks=landmarks,
                        blend_ratio=blend_ratio,
                        guide_angle=guide_angle,
                    )
                else:
                    print("얼굴편집", f"기본 축 adjust_region_size 호출: region={region_name}")
                    result = adjust_region_size(
                        result,
                        region_name,
                        size_x,
                        size_y,
                        center_offset_x,
                        center_offset_y,
                        landmarks,
                        blend_ratio,
                    )

                if result is None:
                    print_warning("얼굴편집", f"{region_name} 크기 조절 결과가 None입니다")
                    result = image
                else:
                    landmarks, _ = face_landmarks.detect_face_landmarks(result)
                    if landmarks is None:
                        print_warning("얼굴편집", "랜드마크 재검출 실패 (지시선 축 적용)")
                        return result
                    if use_guide_axis:
                        guide_angle = self._get_guide_axis_angle(landmarks, image.size)
                        if guide_angle is None:
                            print("얼굴편집", "지시선 축 재계산 실패 - 이후 기본 축 적용")
                            use_guide_axis = False
                    image = result

            if pos_x_condition or pos_y_condition:
                result = adjust_region_position(
                    result,
                    region_name,
                    position_x,
                    position_y,
                    center_offset_x,
                    center_offset_y,
                    landmarks,
                )
                if result is None:
                    print_warning("얼굴편집", f"{region_name} 위치 이동 결과가 None입니다")
                    result = image
                else:
                    landmarks, _ = face_landmarks.detect_face_landmarks(result)
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
                print("얼굴편집", "지시선 축 정보를 가져오지 못했습니다")
                return None

            mid_center = (
                (left_center[0] + right_center[0]) / 2.0,
                (left_center[1] + right_center[1]) / 2.0,
            )
            info = {
                'angle': angle,
                'left_center': left_center,
                'right_center': right_center,
                'mid_center': mid_center,
            }
            self.current_guide_axis_info = info
            print(
                "얼굴편집",
                f"지시선 축 정보 계산: angle={math.degrees(angle):.1f}°, left={left_center}, right={right_center}"
            )
            return info
        except Exception as exc:
            print("얼굴편집", f"지시선 축 계산 실패: {exc}")
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
            print(f"[DEBUG 전체탭] 원본: ({abs_x:.1f},{abs_y:.1f})")
            print(f"  pivot=({pivot_x:.1f},{pivot_y:.1f}), dx={dx:.1f}, dy={dy:.1f}")
            print(f"  angle={math.degrees(angle):.2f}°, cos={cos_angle:.3f}, sin={sin_angle:.3f}")
        self._debug_rotation_count += 1

        rotated_x = dx * cos_angle + dy * sin_angle
        rotated_y = -dx * sin_angle + dy * cos_angle

        if self._debug_rotation_count <= 3:
            print(f"  회전후: ({rotated_x:.1f},{rotated_y:.1f})")

        rotated_x = rotated_x * size_x + pos_x
        rotated_y = rotated_y * size_y + pos_y

        if self._debug_rotation_count <= 3:
            print(f"  스케일후: ({rotated_x:.1f},{rotated_y:.1f})")

        new_x = pivot_x + (rotated_x * cos_angle - rotated_y * sin_angle)
        new_y = pivot_y + (rotated_x * sin_angle + rotated_y * cos_angle)

        if self._debug_rotation_count <= 3:
            print(f"  최종: ({new_x:.1f},{new_y:.1f})")
            print(f"  y변화: {abs_y:.1f} -> {new_y:.1f} (차이={new_y-abs_y:.1f})")
            print("---")

        return new_x, new_y

    def _log_guide_axis_landmark_snapshot(self, label, landmarks, guide_axis_info):
        print("_log_guide_axis_landmark_snapshot: called")
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
            #print(
            print(
                "얼굴편집",
                f"[{label}] sample_idx={idx}, point=({point[0]:.2f},{point[1]:.2f}), pivot=({mid_center[0]:.2f},{mid_center[1]:.2f}), vector=({dx:.2f},{dy:.2f}), angle={math.degrees(angle):.2f}°"
            )
    
    def _apply_common_sliders_to_landmarks(self, selected_regions, center_offset_x, center_offset_y, 
                                          size_x, size_y, position_x, position_y, image):
        """고급 모드: 공통 슬라이더로 custom_landmarks의 포인트를 직접 조절"""
        try:
            from utils.face_morphing.region_extraction import _get_region_center
            import utils.face_landmarks as face_landmarks
            print_debug("_apply_common_sliders_to_landmarks","_apply_common_sliders_to_landmarks: called..")

            context = self._collect_landmark_transform_context(
                image=image,
                size_x=size_x,
                size_y=size_y,
                face_landmarks_module=face_landmarks,
            )
            if context is None:
                return image

            size_x_condition = context['size_x_condition']
            size_y_condition = context['size_y_condition']
            size_condition = context['size_condition']
            scale_relative_fn = context['scale_relative_fn']
            dragged_indices = context['dragged_indices']
            updated_landmarks = context['updated_landmarks']
            original_face_landmarks = context['original_face_landmarks']
            original_iris_landmarks = context['original_iris_landmarks']
            original_landmarks = context['original_landmarks']
            base_landmarks = context['base_landmarks']
            img_width, img_height = context['image_size']
            use_guide_axis = context['use_guide_axis']

            # 확장 레벨 가져오기
            expansion_level = getattr(self, 'polygon_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'polygon_expansion_level') else 1
            
            # TESSELATION 그래프 구성 (확장된 포인트 찾기용)
            tesselation_graph = {}
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    
                    for idx1, idx2 in tesselation:
                        # 468 미만의 인덱스만 포함 (눈동자 제외)
                        if idx1 < 468 and idx2 < 468 and idx1 < len(updated_landmarks) and idx2 < len(updated_landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    
                    # 디버그: 눈썹 인덱스가 그래프에 포함되는지 확인
                    eyebrow_check_indices = [46, 52, 53, 55, 63, 65, 66, 70, 105, 107, 276, 282, 283, 285, 293, 295, 296, 300, 334, 336]
                    eyebrow_in_graph = [idx for idx in eyebrow_check_indices if idx in tesselation_graph]
                except ImportError:
                    pass
            
            handled_tesselation = self._handle_tesselation_transform_mode(
                selected_regions=selected_regions,
                dragged_indices=dragged_indices,
                updated_landmarks=updated_landmarks,
                center_offset_x=center_offset_x,
                center_offset_y=center_offset_y,
                size_x=size_x,
                size_y=size_y,
                position_x=position_x,
                position_y=position_y,
                image=image,
                expansion_level=expansion_level,
                tesselation_graph=tesselation_graph,
                scale_relative_fn=scale_relative_fn if size_condition else None,
            )

            if handled_tesselation:
                transformed_indices = set()
            else:
                transformed_indices = self._transform_selected_landmarks(
                    selected_regions=selected_regions,
                    updated_landmarks=updated_landmarks,
                    original_landmarks=original_landmarks,
                    center_offset_x=center_offset_x,
                    center_offset_y=center_offset_y,
                    position_x=position_x,
                    position_y=position_y,
                    image=image,
                    expansion_level=expansion_level,
                    tesselation_graph=tesselation_graph,
                    scale_relative_fn=scale_relative_fn,
                    dragged_indices=dragged_indices,
                    guide_axis_info=context.get('guide_axis_info'),
                    size_x=size_x,
                    size_y=size_y,
                    use_guide_axis=context.get('use_guide_axis', False),
                )
            
            finalized = self._finalize_landmark_transforms(
                selected_regions=selected_regions,
                updated_landmarks=updated_landmarks,
                original_face_landmarks=original_face_landmarks,
                original_iris_landmarks=original_iris_landmarks,
                original_landmarks=original_landmarks,
                dragged_indices=dragged_indices,
                transformed_indices=transformed_indices,
                image=image,
                use_guide_axis=use_guide_axis,
            )

            guide_info_for_log = context.get('guide_axis_info')
            if guide_info_for_log:
                print_debug(
                    "guide_axis",
                    f"pivot(mid)={guide_info_for_log.get('mid_center')}, "
                    f"left={guide_info_for_log.get('left_center')}, right={guide_info_for_log.get('right_center')}, "
                    f"angle={math.degrees(guide_info_for_log.get('angle', 0.0)):.2f}°",
                )

            print("얼굴편집", f"guide_axis_info {guide_info_for_log}")
            self._log_guide_axis_landmark_snapshot("before_set_custom", finalized['final_landmarks_for_custom'], guide_info_for_log)
            self.landmark_manager.set_custom_landmarks(
                finalized['final_landmarks_for_custom'],
                reason="_apply_common_sliders_to_landmarks",
            )
            self._log_guide_axis_landmark_snapshot("after_set_custom", self.landmark_manager.get_custom_landmarks(), guide_info_for_log)

            polygon_inputs = self._prepare_polygon_inputs(
                selected_regions=selected_regions,
                finalized_landmarks=finalized,
                transformed_point_indices=finalized['transformed_point_indices'],
                image=image,
            )

            original_for_morph = polygon_inputs['original_for_morph']
            transformed_for_morph = polygon_inputs['transformed_for_morph']
            transformed_point_indices = finalized['transformed_point_indices']

            if original_for_morph and transformed_for_morph:
                sample_indices = (
                    list(transformed_point_indices)[:5]
                    if transformed_point_indices
                    else list(range(min(5, len(transformed_for_morph))))
                )
                for idx in sample_indices:
                    if idx >= len(transformed_for_morph) or idx >= len(original_for_morph):
                        continue
                    o = original_for_morph[idx]
                    t = transformed_for_morph[idx]
                    print(
                        "얼굴편집",
                        f"Delaunay 직전 좌표: idx={idx}, orig=({o[0]:.2f},{o[1]:.2f}), trans=({t[0]:.2f},{t[1]:.2f})"
                    )

            import utils.face_morphing as face_morphing
            from utils.face_morphing.adjustments.region_adjustments import adjust_region_size_with_axis

            # 가이드축 정보 전달
            guide_axis_info = context.get('guide_axis_info')
            guide_angle = guide_axis_info.get('angle') if guide_axis_info else None
            
            # 먼저 기본 폴리곤 변형 적용
            result = face_morphing.morph_face_by_polygons(
                self.current_image,
                original_for_morph,
                transformed_for_morph,
                selected_point_indices=polygon_inputs['selected_indices_for_morph'],
                left_iris_center_coord=polygon_inputs['left_center'],
                right_iris_center_coord=polygon_inputs['right_center'],
                left_iris_center_orig=polygon_inputs['left_center_orig'],
                right_iris_center_orig=polygon_inputs['right_center_orig'],
                cached_original_bbox=polygon_inputs['cached_bbox'],
                blend_ratio=polygon_inputs['blend_ratio'],
            )
            
            # 가이드축이 있고 변형이 필요한 경우 추가 적용
            if guide_angle is not None and result is not None:
                # 전체 이미지에 가이드축 기반 크기 조절 적용
                size_x = context.get('size_x', 1.0)
                size_y = context.get('size_y', 1.0)
                center_offset_x = context.get('center_offset_x', 0.0)
                center_offset_y = context.get('center_offset_y', 0.0)
                
                print(f"[DEBUG] 가이드축 추가 적용: guide_angle={guide_angle}, size_x={size_x}, size_y={size_y}")
                
                if abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
                    # 직접 가이드축 기반 이미지 변형 구현
                    print(f"[DEBUG] 직접 가이드축 변형 시작: guide_angle={guide_angle}, size_x={size_x}, size_y={size_y}")
                    
                    try:
                        import numpy as np
                        import cv2
                        from PIL import Image
                        
                        # PIL 이미지를 numpy 배열로 변환
                        img_array = np.array(result)
                        
                        # 이미지 중심점 계산
                        h, w = img_array.shape[:2]
                        center_x, center_y = w // 2, h // 2
                        
                        # 가이드축 각도로 회전 행렬 생성 (역방향으로 먼저 회전)
                        cos_a = np.cos(guide_angle)
                        sin_a = np.sin(guide_angle)
                        
                        # 회전 행렬 (시계 반대 방향)
                        rotation_matrix = np.array([
                            [cos_a, -sin_a, center_x * (1 - cos_a) + center_y * sin_a],
                            [sin_a, cos_a, center_y * (1 - cos_a) - center_x * sin_a]
                        ], dtype=np.float32)
                        
                        # 이미지 회전 (가이드축 정렬)
                        rotated = cv2.warpAffine(img_array, rotation_matrix, (w, h))
                        
                        # 스케일링 적용 (회전된 상태에서)
                        scale_x, scale_y = size_x, size_y
                        scaled_w, scaled_h = int(w * scale_x), int(h * scale_y)
                        
                        if scale_x != 1.0 or scale_y != 1.0:
                            scaled = cv2.resize(rotated, (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
                            
                            # 다시 원래 크기로 리사이즈 (중심 기준)
                            final_rotated = cv2.resize(scaled, (w, h), interpolation=cv2.INTER_LANCZOS4)
                        else:
                            final_rotated = rotated
                        
                        # 원래 각도로 역회전
                        inverse_rotation_matrix = np.array([
                            [cos_a, sin_a, center_x * (1 - cos_a) - center_y * sin_a],
                            [-sin_a, cos_a, center_y * (1 - cos_a) + center_x * sin_a]
                        ], dtype=np.float32)
                        
                        final_array = cv2.warpAffine(final_rotated, inverse_rotation_matrix, (w, h))
                        
                        # PIL 이미지로 변환
                        result = Image.fromarray(final_array)
                        print(f"[DEBUG] 직접 가이드축 변형 완료")
                        
                    except Exception as e:
                        print(f"[DEBUG] 직접 가이드축 변형 실패: {e}")
                        # 실패하면 기존 결과 유지
            
            if result is None:
                print_warning("얼굴편집", "랜드마크 변형 결과가 None입니다")
                return image
            
            # 편집된 이미지 업데이트
            self.edited_image = result
            # self.face_landmarks = updated_landmarks  # 주석 처리: 원본 좌표로 덮어쓰기 방지
            
            # 변형된 랜드마크 업데이트 확인
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                # custom_landmarks를 직접 변형된 좌표로 업데이트
                for i in range(len(updated_landmarks)):
                    if i < len(self.custom_landmarks):
                        self.custom_landmarks[i] = updated_landmarks[i]
                
                self.transformed_landmarks = self.custom_landmarks.copy()
                print(f"[DEBUG] custom_landmarks 직접 업데이트: len={len(self.custom_landmarks)}")
                if len(self.transformed_landmarks) > 384:
                    sample_point = self.transformed_landmarks[384]
                    print(f"[DEBUG] transformed_landmarks[384]: ({sample_point[0]:.2f},{sample_point[1]:.2f})")
                    
                # face_landmarks도 변형된 좌표로 업데이트 (폴리곤 그리기용)
                self.face_landmarks = self.transformed_landmarks.copy()
                print(f"[DEBUG] face_landmarks를 transformed_landmarks로 업데이트")
                
                # custom_landmarks 덮어쓰기 방지를 위한 백업
                self._last_transformed_custom_landmarks = self.custom_landmarks.copy()
                print(f"[DEBUG] custom_landmarks 백업 완료")
            
            # 원본 이미지의 폴리곤 다시 그리기
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # 기존 폴리곤 제거
                print("얼굴편집", "폴리곤 다시 그리기 시작 (고급모드)")
                if hasattr(self, 'landmark_polygon_items') and 'original' in self.landmark_polygon_items:
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items['original'].clear()
                    self.polygon_point_map_original.clear()
                    
                    # 폴리곤 다시 그리기 (전체 탭으로 강제하여 선택된 모든 부위의 폴리곤 그리기)
                    if hasattr(self, '_draw_landmark_polygons'):
                        # 파라미터 분리: face_landmarks, iris_landmarks, iris_centers
                        face_landmarks_for_drawing = updated_landmarks  # 468개
                        iris_landmarks_for_drawing = None
                        iris_centers_for_drawing = None
                        
                        transformed_point_indices = finalized['transformed_point_indices']
                        final_landmarks_for_custom = finalized['final_landmarks_for_custom']
                        original_face_landmarks_tuple = finalized['original_face_landmarks_tuple']

                        if 'tesselation' in selected_regions and len(selected_regions) == 1:
                            # Tesselation 선택 시: iris_centers 사용 (470개 구조)
                            iris_centers_for_drawing = self.landmark_manager.get_custom_iris_centers()
                            if iris_centers_for_drawing is None and len(final_landmarks_for_custom) == 470:
                                # final_landmarks_for_custom에서 중앙 포인트 추출
                                iris_centers_for_drawing = final_landmarks_for_custom[-2:]
                                face_landmarks_for_drawing = final_landmarks_for_custom[:-2]  # 468개
                        else:
                            # Tesselation이 아닌 경우: iris_landmarks 사용 (478개 구조)
                            iris_landmarks_for_drawing = self.landmark_manager.get_original_iris_landmarks()

                        self._draw_landmark_polygons(
                            self.canvas_original,
                            self.current_image,
                            face_landmarks_for_drawing,  # 468개
                            self.canvas_original_pos_x,
                            self.canvas_original_pos_y,
                            self.landmark_polygon_items['original'],
                            "green",
                            '전체',  # 전체 탭으로 강제하여 선택된 모든 부위의 폴리곤 그리기
                            iris_landmarks=iris_landmarks_for_drawing,  # 10개 또는 None
                            iris_centers=iris_centers_for_drawing,  # 2개 또는 None
                            force_use_custom=True,  # custom_landmarks를 명시적으로 전달했으므로 강제 사용
                            highlight_indices=sorted(transformed_point_indices) if transformed_point_indices else None
                        )
                        self._log_polygon_debug_info(
                            face_landmarks_for_drawing,
                            transformed_point_indices,
                            original_face_landmarks_tuple,
                            iris_centers_for_drawing is not None,
                        )
            
            # 이미지 변형 결과 반환
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self._refresh_face_edit_display(
                image=True,
                landmarks=True,
                overlays=True,
                guide_lines=True,
                force_original=False,
            )
    
    def _collect_landmark_transform_context(self, image, size_x, size_y, face_landmarks_module):
        custom = self.landmark_manager.get_custom_landmarks()
        print(f"_collect_landmark_transform_context: called {custom is not None}")
        if custom is None:
            return None

        size_x_condition = abs(size_x - 1.0) >= 0.01
        size_y_condition = abs(size_y - 1.0) >= 0.01
        size_condition = size_x_condition or size_y_condition
        use_guide_axis = size_condition and self._should_use_guide_axis()
        guide_angle = None
        cos_angle = None
        sin_angle = None

        if not self.landmark_manager.has_original_face_landmarks():
            original_landmarks_full, _ = face_landmarks_module.detect_face_landmarks(self.current_image)
            if original_landmarks_full is None:
                return None
            img_width, img_height = image.size
            self.landmark_manager.set_original_landmarks(original_landmarks_full, img_width, img_height)
            self.original_landmarks = self.landmark_manager.get_original_landmarks_full()

        original_face_landmarks = self.landmark_manager.get_original_face_landmarks()
        original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
        original_landmarks = self.landmark_manager.get_original_landmarks_full()

        if self.custom_landmarks is None or len(self.custom_landmarks) != 468:
            if original_face_landmarks is not None:
                self.landmark_manager.set_custom_landmarks(
                    list(original_face_landmarks),
                    reason="collect_landmark_transform_context: init",
                )

        dragged_indices = self.landmark_manager.get_dragged_indices()
        updated_landmarks = []
        img_width, img_height = image.size

        base_landmarks = (
            original_face_landmarks
            if original_face_landmarks is not None
            else (original_landmarks[:468] if len(original_landmarks) >= 468 else original_landmarks)
        )
        for idx in range(len(base_landmarks)):
            if isinstance(base_landmarks[idx], tuple):
                updated_landmarks.append(base_landmarks[idx])
            else:
                updated_landmarks.append((
                    base_landmarks[idx].x * img_width,
                    base_landmarks[idx].y * img_height
                ))

        guide_axis_centers = None
        if use_guide_axis:
            angle_landmarks = base_landmarks if base_landmarks is not None else updated_landmarks
            guide_info = self._get_guide_axis_info(angle_landmarks, image.size)
            if guide_info is None:
                use_guide_axis = False
                print(
                    "얼굴편집",
                    "고급모드 가이드축 비활성화: guide_info 계산 실패"
                )
            else:
                guide_angle = guide_info['angle']
                cos_angle = math.cos(guide_angle)
                sin_angle = math.sin(guide_angle)
                guide_axis_centers = dict(guide_info)
                guide_axis_centers['cos_angle'] = cos_angle
                guide_axis_centers['sin_angle'] = sin_angle
                guide_axis_centers.setdefault('sample_index', 0)
                print(
                    "얼굴편집",
                    f"고급모드 축 스케일 적용 준비: angle={math.degrees(guide_angle):.1f}°, pivot={guide_axis_centers.get('mid_center')}"
                )
        else:
            if not size_condition:
                print("얼굴편집", "고급모드 가이드축 비활성화: size_condition 미충족")
            else:
                print("얼굴편집", "고급모드 가이드축 비활성화: use_guide_line_scaling 꺼짐")

        def _scale_relative(dx, dy):
            # size_condition 체크 제거 - 항상 스케일링 적용
            print(f"[DEBUG] _scale_relative: use_guide_axis={use_guide_axis}, guide_angle={guide_angle}, size_x={size_x}, size_y={size_y}")
            if use_guide_axis and guide_angle is not None:
                rot_x = dx * cos_angle + dy * sin_angle
                rot_y = -dx * sin_angle + dy * cos_angle
                rot_x *= size_x
                rot_y *= size_y
                new_dx = rot_x * cos_angle - rot_y * sin_angle
                new_dy = rot_x * sin_angle + rot_y * cos_angle
                print(f"[DEBUG] _scale_relative (가이드축): in=({dx:.3f},{dy:.3f}) -> out=({new_dx:.3f},{new_dy:.3f})")
                return new_dx, new_dy

            print(f"[DEBUG] _scale_relative (기본축): in=({dx:.3f},{dy:.3f}) -> out=({dx*size_x:.3f},{dy*size_y:.3f})")
            return dx * size_x, dy * size_y

        custom_for_drag = custom
        if custom is not None and len(custom) == 470:
            custom_for_drag = custom[:468]

        if custom_for_drag is not None and len(custom_for_drag) == 468 and dragged_indices:
            for idx in dragged_indices:
                if 0 <= idx < len(custom_for_drag) and idx < len(updated_landmarks):
                    if isinstance(custom_for_drag[idx], tuple):
                        updated_landmarks[idx] = custom_for_drag[idx]
                    else:
                        updated_landmarks[idx] = (
                            custom_for_drag[idx].x * img_width,
                            custom_for_drag[idx].y * img_height
                        )

        return {
            'size_x_condition': size_x_condition,
            'size_y_condition': size_y_condition,
            'size_condition': size_condition,
            'scale_relative_fn': _scale_relative,
            'dragged_indices': dragged_indices,
            'updated_landmarks': updated_landmarks,
            'original_face_landmarks': original_face_landmarks,
            'original_iris_landmarks': original_iris_landmarks,
            'original_landmarks': original_landmarks,
            'base_landmarks': base_landmarks,
            'image_size': (img_width, img_height),
            'use_guide_axis': use_guide_axis,
            'guide_axis_info': guide_axis_centers,
            'size_x': size_x,
            'size_y': size_y,
            'use_guide_axis': use_guide_axis,
        }

    def _finalize_landmark_transforms(
        self,
        *,
        selected_regions,
        updated_landmarks,
        original_face_landmarks,
        original_iris_landmarks,
        original_landmarks,
        dragged_indices,
        transformed_indices,
        image,
        use_guide_axis,
    ):
        transformed_point_indices = set()
        base_for_compare = (
            original_face_landmarks
            if original_face_landmarks is not None
            else (original_landmarks[:468] if original_landmarks and len(original_landmarks) >= 468 else original_landmarks)
        )

        if 'tesselation' in selected_regions and len(selected_regions) == 1:
            if base_for_compare is not None:
                img_width, img_height = image.size
                for idx in range(len(updated_landmarks)):
                    if idx >= len(base_for_compare):
                        continue
                    base_point = base_for_compare[idx]
                    if isinstance(base_point, tuple) and isinstance(updated_landmarks[idx], tuple):
                        if (
                            abs(base_point[0] - updated_landmarks[idx][0]) > 0.1 or
                            abs(base_point[1] - updated_landmarks[idx][1]) > 0.1
                        ):
                            transformed_point_indices.add(idx)
                    else:
                        orig_x = base_point.x * img_width if hasattr(base_point, 'x') else base_point[0]
                        orig_y = base_point.y * img_height if hasattr(base_point, 'y') else base_point[1]
                        trans_x = updated_landmarks[idx][0] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].x * img_width
                        trans_y = updated_landmarks[idx][1] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].y * img_height
                        if abs(orig_x - trans_x) > 0.1 or abs(orig_y - trans_y) > 0.1:
                            transformed_point_indices.add(idx)
        else:
            transformed_point_indices = set(transformed_indices)

        if base_for_compare is not None and transformed_point_indices:
            img_width, img_height = image.size
            max_diff = 0.0
            max_y_diff = 0.0
            sample_count = 0
            for idx in transformed_point_indices:
                if idx >= len(updated_landmarks) or idx >= len(base_for_compare):
                    continue
                if isinstance(base_for_compare[idx], tuple):
                    orig_x, orig_y = base_for_compare[idx]
                else:
                    orig_x = base_for_compare[idx].x * img_width
                    orig_y = base_for_compare[idx].y * img_height
                trans_x, trans_y = updated_landmarks[idx]
                diff = ((trans_x - orig_x) ** 2 + (trans_y - orig_y) ** 2) ** 0.5
                y_diff = abs(trans_y - orig_y)
                max_diff = max(max_diff, diff)
                max_y_diff = max(max_y_diff, y_diff)
                sample_count += 1
            print_debug(
                "얼굴편집",
                f"고급모드 축스케일 비교: guide_axis={use_guide_axis}, transformed={sample_count}개, max_diff={max_diff:.3f}, max_y_diff={max_y_diff:.3f}"
            )

        restore_unselected = not (use_guide_axis and selected_regions and 'tesselation' not in selected_regions)
        final_landmarks = list(updated_landmarks)
        if restore_unselected and base_for_compare is not None:
            img_width, img_height = image.size
            restored_count = 0
            restored_samples = []
            for idx in range(len(base_for_compare)):
                if idx in dragged_indices or idx in transformed_point_indices:
                    continue
                base_point = base_for_compare[idx]
                if isinstance(base_point, tuple):
                    final_landmarks[idx] = base_point
                else:
                    final_landmarks[idx] = (
                        base_point.x * img_width,
                        base_point.y * img_height,
                    )
                restored_count += 1
                if len(restored_samples) < 5:
                    restored_samples.append((idx, final_landmarks[idx]))
            if restored_count:
                print_debug(
                    "얼굴편집",
                    f"고급모드 복원: restored={restored_count}개, sample={restored_samples}"
                )
        elif not restore_unselected:
            print_debug("얼굴편집", "고급모드 복원 비활성화: 선택 부위만 유지")

        img_width, img_height = image.size
        base_for_tuple = base_for_compare
        original_face_landmarks_tuple = []
        if base_for_tuple is not None:
            for idx in range(len(base_for_tuple)):
                base_point = base_for_tuple[idx]
                if isinstance(base_point, tuple):
                    original_face_landmarks_tuple.append(base_point)
                else:
                    original_face_landmarks_tuple.append((
                        base_point.x * img_width,
                        base_point.y * img_height,
                    ))

        final_landmarks_for_custom = final_landmarks
        original_landmarks_for_morph = original_face_landmarks_tuple

        if 'tesselation' in selected_regions and len(selected_regions) == 1:
            left_center = self.landmark_manager.get_left_iris_center_coord()
            right_center = self.landmark_manager.get_right_iris_center_coord()

            if (left_center is None or right_center is None) and original_iris_landmarks is not None:
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices  # noqa: F401 (for side effects)
                except ImportError:
                    get_iris_indices = None

                left_points = original_iris_landmarks[:4] if len(original_iris_landmarks) >= 4 else original_iris_landmarks[:len(original_iris_landmarks)//2]
                right_points = original_iris_landmarks[4:] if len(original_iris_landmarks) > 4 else original_iris_landmarks[len(original_iris_landmarks)//2:]

                if left_points and left_center is None:
                    left_center = (
                        sum(p[0] for p in left_points) / len(left_points),
                        sum(p[1] for p in left_points) / len(left_points),
                    )
                if right_points and right_center is None:
                    right_center = (
                        sum(p[0] for p in right_points) / len(right_points),
                        sum(p[1] for p in right_points) / len(right_points),
                    )

            if left_center is not None and right_center is not None:
                final_landmarks_for_custom = list(final_landmarks)
                final_landmarks_for_custom.append(left_center)
                final_landmarks_for_custom.append(right_center)
                original_landmarks_for_morph = list(original_face_landmarks_tuple)
                original_landmarks_for_morph.append(left_center)
                original_landmarks_for_morph.append(right_center)
                self.landmark_manager.set_custom_iris_centers([left_center, right_center])

        existing_custom = self.landmark_manager.get_custom_landmarks()
        if existing_custom is not None and len(existing_custom) == 470:
            left_center = self.landmark_manager.get_left_iris_center_coord()
            right_center = self.landmark_manager.get_right_iris_center_coord()
            if left_center is not None and right_center is not None:
                temp_landmarks = list(final_landmarks)
                temp_landmarks.append(left_center)
                temp_landmarks.append(right_center)
                final_landmarks_for_custom = temp_landmarks
                print_info(
                    "얼굴편집",
                    f"기존 custom_landmarks(470개)에 중앙 포인트 업데이트: 왼쪽={left_center}, 오른쪽={right_center}"
                )

        return {
            'final_landmarks': final_landmarks,
            'final_landmarks_for_custom': final_landmarks_for_custom,
            'original_face_landmarks_tuple': original_face_landmarks_tuple,
            'original_landmarks_for_morph': original_landmarks_for_morph,
            'transformed_point_indices': transformed_point_indices,
        }

    def _prepare_polygon_inputs(
        self,
        *,
        selected_regions,
        finalized_landmarks,
        transformed_point_indices,
        image,
    ):
        final_landmarks_for_custom = finalized_landmarks['final_landmarks_for_custom']
        original_face_landmarks_tuple = finalized_landmarks['original_face_landmarks_tuple']
        original_landmarks_for_morph = finalized_landmarks['original_landmarks_for_morph']

        if 'tesselation' in selected_regions and len(selected_regions) == 1:
            original_for_morph, transformed_for_morph = self.landmark_manager.get_copied_landmarks_for_tesselation_with_centers()
            if original_for_morph is None:
                original_for_morph = original_landmarks_for_morph
            if transformed_for_morph is None:
                transformed_for_morph = final_landmarks_for_custom
        else:
            original_for_morph = original_face_landmarks_tuple
            transformed_for_morph = final_landmarks_for_custom

        left_center = self.landmark_manager.get_left_iris_center_coord()
        right_center = self.landmark_manager.get_right_iris_center_coord()
        left_center_orig = self.landmark_manager.get_original_left_iris_center_coord()
        right_center_orig = self.landmark_manager.get_original_right_iris_center_coord()

        if left_center_orig is None or right_center_orig is None:
            original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            if original_iris_landmarks is not None and len(original_iris_landmarks) == 10:
                left_iris_points = original_iris_landmarks[:5]
                right_iris_points = original_iris_landmarks[5:]

                if left_iris_points and left_center_orig is None:
                    left_center_orig = (
                        sum(p[0] for p in left_iris_points) / len(left_iris_points),
                        sum(p[1] for p in left_iris_points) / len(left_iris_points),
                    )
                    self.landmark_manager.set_iris_center_coords(
                        left_center_orig,
                        self.landmark_manager.get_original_right_iris_center_coord(),
                        is_original=True,
                    )
                if right_iris_points and right_center_orig is None:
                    right_center_orig = (
                        sum(p[0] for p in right_iris_points) / len(right_iris_points),
                        sum(p[1] for p in right_iris_points) / len(right_iris_points),
                    )
                    self.landmark_manager.set_iris_center_coords(
                        self.landmark_manager.get_original_left_iris_center_coord(),
                        right_center_orig,
                        is_original=True,
                    )

        img_width, img_height = self.current_image.size
        cached_bbox = self.landmark_manager.get_original_bbox(img_width, img_height)
        blend_ratio = self.blend_ratio.get() if hasattr(self, 'blend_ratio') else 1.0

        selected_indices_for_morph = None
        if getattr(self, 'use_landmark_warping', None) and self.use_landmark_warping.get():
            if 'tesselation' in selected_regions and len(selected_regions) == 1:
                if transformed_for_morph:
                    selected_indices_for_morph = list(range(len(transformed_for_morph)))
            else:
                if transformed_point_indices:
                    selected_indices_for_morph = sorted(transformed_point_indices)

        return {
            'original_for_morph': original_for_morph,
            'transformed_for_morph': transformed_for_morph,
            'selected_indices_for_morph': selected_indices_for_morph,
            'left_center': left_center,
            'right_center': right_center,
            'left_center_orig': left_center_orig,
            'right_center_orig': right_center_orig,
            'cached_bbox': cached_bbox,
            'blend_ratio': blend_ratio,
        }
    
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
        print(f"[초기화] reset 전 original_iris_landmarks: {original_iris_before is not None}, 길이: {len(original_iris_before) if original_iris_before else 0}")
        
        # LandmarkManager를 사용하여 초기화
        self.landmark_manager.reset(keep_original=True)
        # property가 자동으로 처리하므로 동기화 코드 불필요
        self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
        self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
        
        # 초기화 후 original_iris_landmarks 확인 (디버깅용)
        original_iris_after = self.landmark_manager.get_original_iris_landmarks()
        print(f"[초기화] reset 후 original_iris_landmarks: {original_iris_after is not None}, 길이: {len(original_iris_after) if original_iris_after else 0}")
        
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
    
    def apply_editing(self ):
        """편집 적용"""
        print_debug("logic", "apply_editing: called")        
        if self.current_image is None:
            return

        try:
            # 처리 순서: 정렬 → 특징 보정 → 스타일 전송 → 나이 변환
            # 편집은 항상 정렬된 이미지(또는 원본)를 기반으로 처음부터 다시 적용
            # aligned_image가 있으면 정렬된 이미지 사용, 없으면 원본 이미지 사용
            base_image = self.aligned_image if self.aligned_image is not None else self.current_image
            
            # 1. 얼굴 특징 보정 적용
            result = self._prepare_editing_parameters(base_image)
            
            # 2. 스타일 전송 적용
            result = self._apply_style_transfer_step(result)
            
            # 3. 나이 변환 적용
            result = self._apply_age_transform_step(result)
            
            # 4. 공통 슬라이더 적용 (선택된 부위에 대해)
            # 슬라이더가 모두 기본값인지 먼저 확인
            size_x = self.region_size_x.get()
            size_y = self.region_size_y.get()
            center_offset_x = self.region_center_offset_x.get()
            center_offset_y = self.region_center_offset_y.get()
            position_x = self.region_position_x.get()
            position_y = self.region_position_y.get()
            
            size_x_condition = abs(size_x - 1.0) >= 0.01
            size_y_condition = abs(size_y - 1.0) >= 0.01
            size_condition = size_x_condition or size_y_condition
            offset_x_condition = abs(center_offset_x) >= 0.1
            offset_y_condition = abs(center_offset_y) >= 0.1
            pos_x_condition = abs(position_x) >= 0.1
            pos_y_condition = abs(position_y) >= 0.1
            conditions_met = offset_x_condition or offset_y_condition or size_condition or pos_x_condition or pos_y_condition
            
            if not conditions_met:
                # 슬라이더가 모두 기본값이면 원본 이미지로 복원 (앞 단계의 변형도 건너뜀)
                result = base_image
            else:
                # base_image를 전달하여 슬라이더가 모두 기본값일 때 원본으로 복원할 수 있도록 함
                result = self._apply_common_sliders(result, base_image=base_image)
            
            self.edited_image = result
            
            # 5. 변형된 랜드마크 계산 및 업데이트 (폴리곤 표시를 위해)
            self._update_landmarks_after_editing()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self._refresh_face_edit_display(
                image=True,
                landmarks=True,
                overlays=True,
                guide_lines=True,
                force_original=False,
            )
