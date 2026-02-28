"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
"""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

from utils.logger import debug, info, warn, error, log
from gui.FaceForge.utils.debugs import DEBUG_MORPHING_UPDATE, DEBUG_APPLY_SLIDERS

from gui.FaceForge.utils import landmarks as utilmarks
from gui.FaceForge.utils import morphing as utilmorph

class HandlersMixin:
    """이벤트 핸들러 기능 Mixin"""

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

    def update_labels_only(self):
        """라벨만 업데이트 (슬라이더 드래그 중 호출)"""

        # # 왼쪽/오른쪽 눈 라벨 업데이트 (라벨이 존재하는 경우에만)
        # if hasattr(self, 'left_eye_size_label') and self.left_eye_size_label is not None:
        #     left_eye_value = self.left_eye_size.get()
        #     self.left_eye_size_label.config(text=f"{int(left_eye_value * 100)}%")
        
        # if hasattr(self, 'right_eye_size_label') and self.right_eye_size_label is not None:
        #     right_eye_value = self.right_eye_size.get()
        #     self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
        
        # if hasattr(self, 'nose_size_label') and self.nose_size_label is not None:
        #     nose_value = self.nose_size.get()
        #     self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        # # 입 편집 라벨 업데이트 (라벨이 존재하는 경우에만)
        # if hasattr(self, 'upper_lip_shape_label') and self.upper_lip_shape_label is not None:
        #     upper_lip_shape_value = self.upper_lip_shape.get()
        #     self.upper_lip_shape_label.config(text=f"{int(upper_lip_shape_value * 100)}%")
        
        # if hasattr(self, 'lower_lip_shape_label') and self.lower_lip_shape_label is not None:
        #     lower_lip_shape_value = self.lower_lip_shape.get()
        #     self.lower_lip_shape_label.config(text=f"{int(lower_lip_shape_value * 100)}%")
        
        # if hasattr(self, 'upper_lip_width_label') and self.upper_lip_width_label is not None:
        #     upper_lip_width_value = self.upper_lip_width.get()
        #     self.upper_lip_width_label.config(text=f"{int(upper_lip_width_value * 100)}%")
        
        # if hasattr(self, 'lower_lip_width_label') and self.lower_lip_width_label is not None:
        #     lower_lip_width_value = self.lower_lip_width.get()
        #     self.lower_lip_width_label.config(text=f"{int(lower_lip_width_value * 100)}%")
        
        # if hasattr(self, 'upper_lip_vertical_move_label') and self.upper_lip_vertical_move_label is not None:
        #     upper_lip_vertical_move_value = self.upper_lip_vertical_move.get()
        #     self.upper_lip_vertical_move_label.config(text=f"{int(upper_lip_vertical_move_value)}")
        
        # if hasattr(self, 'lower_lip_vertical_move_label') and self.lower_lip_vertical_move_label is not None:
        #     lower_lip_vertical_move_value = self.lower_lip_vertical_move.get()
        #     self.lower_lip_vertical_move_label.config(text=f"{int(lower_lip_vertical_move_value)}")
        
        # # 입술 영역 라벨 업데이트 (라벨이 존재하는 경우에만)
        # if hasattr(self, 'upper_lip_region_padding_x_label') and self.upper_lip_region_padding_x_label is not None:
        #     upper_lip_region_padding_x_value = self.upper_lip_region_padding_x.get()
        #     self.upper_lip_region_padding_x_label.config(text=f"{int(upper_lip_region_padding_x_value * 100)}%")
        
        # if hasattr(self, 'upper_lip_region_padding_y_label') and self.upper_lip_region_padding_y_label is not None:
        #     upper_lip_region_padding_y_value = self.upper_lip_region_padding_y.get()
        #     self.upper_lip_region_padding_y_label.config(text=f"{int(upper_lip_region_padding_y_value * 100)}%")
        
        # if hasattr(self, 'upper_lip_region_offset_x_label') and self.upper_lip_region_offset_x_label is not None:
        #     upper_lip_region_offset_x_value = self.upper_lip_region_offset_x.get()
        #     self.upper_lip_region_offset_x_label.config(text=f"{int(upper_lip_region_offset_x_value)}")
        
        # if hasattr(self, 'upper_lip_region_offset_y_label') and self.upper_lip_region_offset_y_label is not None:
        #     upper_lip_region_offset_y_value = self.upper_lip_region_offset_y.get()
        #     self.upper_lip_region_offset_y_label.config(text=f"{int(upper_lip_region_offset_y_value)}")
        
        # if hasattr(self, 'lower_lip_region_padding_x_label') and self.lower_lip_region_padding_x_label is not None:
        #     lower_lip_region_padding_x_value = self.lower_lip_region_padding_x.get()
        #     self.lower_lip_region_padding_x_label.config(text=f"{int(lower_lip_region_padding_x_value * 100)}%")
        
        # if hasattr(self, 'lower_lip_region_padding_y_label') and self.lower_lip_region_padding_y_label is not None:
        #     lower_lip_region_padding_y_value = self.lower_lip_region_padding_y.get()
        #     self.lower_lip_region_padding_y_label.config(text=f"{int(lower_lip_region_padding_y_value * 100)}%")
        
        # if hasattr(self, 'lower_lip_region_offset_x_label') and self.lower_lip_region_offset_x_label is not None:
        #     lower_lip_region_offset_x_value = self.lower_lip_region_offset_x.get()
        #     self.lower_lip_region_offset_x_label.config(text=f"{int(lower_lip_region_offset_x_value)}")
        
        # if hasattr(self, 'lower_lip_region_offset_y_label') and self.lower_lip_region_offset_y_label is not None:
        #     lower_lip_region_offset_y_value = self.lower_lip_region_offset_y.get()
        #     self.lower_lip_region_offset_y_label.config(text=f"{int(lower_lip_region_offset_y_value)}")
        
        # # 턱선 라벨 업데이트 (라벨이 존재하는 경우에만)
        # if hasattr(self, 'jaw_size_label') and self.jaw_size_label is not None:
        #     jaw_value = self.jaw_size.get()
        #     self.jaw_size_label.config(text=f"{int(jaw_value)}")
        
        # # 얼굴 크기 라벨 업데이트 (라벨이 존재하는 경우에만)
        # if hasattr(self, 'face_width_label') and self.face_width_label is not None:
        #     face_width_value = self.face_width.get()
        #     self.face_width_label.config(text=f"{int(face_width_value * 100)}%")
        
        # if hasattr(self, 'face_height_label') and self.face_height_label is not None:
        #     face_height_value = self.face_height.get()
        #     self.face_height_label.config(text=f"{int(face_height_value * 100)}%")
        
        # # 눈 위치 라벨 업데이트 (왼쪽/오른쪽 개별, 라벨이 존재하는 경우에만)
        # if hasattr(self, 'left_eye_position_y_label') and self.left_eye_position_y_label is not None:
        #     left_eye_position_y_value = self.left_eye_position_y.get()
        #     self.left_eye_position_y_label.config(text=f"{int(left_eye_position_y_value)}")
        
        # if hasattr(self, 'right_eye_position_y_label') and self.right_eye_position_y_label is not None:
        #     right_eye_position_y_value = self.right_eye_position_y.get()
        #     self.right_eye_position_y_label.config(text=f"{int(right_eye_position_y_value)}")
        
        # if hasattr(self, 'left_eye_position_x_label') and self.left_eye_position_x_label is not None:
        #     left_eye_position_x_value = self.left_eye_position_x.get()
        #     self.left_eye_position_x_label.config(text=f"{int(left_eye_position_x_value)}")
        
        # if hasattr(self, 'right_eye_position_x_label') and self.right_eye_position_x_label is not None:
        #     right_eye_position_x_value = self.right_eye_position_x.get()
        #     self.right_eye_position_x_label.config(text=f"{int(right_eye_position_x_value)}")
        
        # # 눈 영역 라벨 업데이트 (개별 적용, 라벨이 존재하는 경우에만)
        # if hasattr(self, 'left_eye_region_padding_label') and self.left_eye_region_padding_label is not None:
        #     left_eye_region_padding_value = self.left_eye_region_padding.get()
        #     self.left_eye_region_padding_label.config(text=f"{int(left_eye_region_padding_value * 100)}%")
        
        # if hasattr(self, 'right_eye_region_padding_label') and self.right_eye_region_padding_label is not None:
        #     right_eye_region_padding_value = self.right_eye_region_padding.get()
        #     self.right_eye_region_padding_label.config(text=f"{int(right_eye_region_padding_value * 100)}%")
        
        # # 눈 영역 위치 라벨 업데이트 (개별 적용, 라벨이 존재하는 경우에만)
        # if hasattr(self, 'left_eye_region_offset_x_label') and self.left_eye_region_offset_x_label is not None:
        #     left_eye_region_offset_x_value = self.left_eye_region_offset_x.get()
        #     self.left_eye_region_offset_x_label.config(text=f"{int(left_eye_region_offset_x_value)}")
        
        # if hasattr(self, 'left_eye_region_offset_y_label') and self.left_eye_region_offset_y_label is not None:
        #     left_eye_region_offset_y_value = self.left_eye_region_offset_y.get()
        #     self.left_eye_region_offset_y_label.config(text=f"{int(left_eye_region_offset_y_value)}")
        
        # if hasattr(self, 'right_eye_region_offset_x_label') and self.right_eye_region_offset_x_label is not None:
        #     right_eye_region_offset_x_value = self.right_eye_region_offset_x.get()
        #     self.right_eye_region_offset_x_label.config(text=f"{int(right_eye_region_offset_x_value)}")
        
        # if hasattr(self, 'right_eye_region_offset_y_label') and self.right_eye_region_offset_y_label is not None:
        #     right_eye_region_offset_y_value = self.right_eye_region_offset_y.get()
        #     self.right_eye_region_offset_y_label.config(text=f"{int(right_eye_region_offset_y_value)}")

        # # 공통 슬라이더 라벨 업데이트 (Region Adjustment)
        # if hasattr(self, 'region_size_x_label') and self.region_size_x_label is not None:
        #     region_size_x_value = self.region_size_x.get()
        #     self.region_size_x_label.config(text=f"{(region_size_x_value * 100):.1f}%")
        
        # if hasattr(self, 'region_size_y_label') and self.region_size_y_label is not None:
        #     region_size_y_value = self.region_size_y.get()
        #     self.region_size_y_label.config(text=f"{(region_size_y_value * 100):.1f}%")

        # if hasattr(self, 'region_pivot_x_label') and self.region_pivot_x_label is not None:
        #     region_pivot_x_value = self.region_pivot_x.get()
        #     self.region_pivot_x_label.config(text=f"{region_pivot_x_value:.2f}")
        
        # if hasattr(self, 'region_pivot_y_label') and self.region_pivot_y_label is not None:
        #     region_pivot_y_value = self.region_pivot_y.get()
        #     self.region_pivot_y_label.config(text=f"{region_pivot_y_value:.2f}")
        
        # if hasattr(self, 'region_position_x_label') and self.region_position_x_label is not None:
        #     region_position_x_value = self.region_position_x.get()
        #     self.region_position_x_label.config(text=f"{region_position_x_value:.2f}")
        
        # if hasattr(self, 'region_position_y_label') and self.region_position_y_label is not None:
        #     region_position_y_value = self.region_position_y.get()
        #     self.region_position_y_label.config(text=f"{region_position_y_value:.2f}")
        
        # 슬라이더 드래그 중 폴리곤 업데이트 (이미지 편집 없이 랜드마크만 계산)
        if self.current_image is not None:
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                self.update_polygons_only()            

    def update_polygons_only(self):
        """폴리곤만 업데이트 (슬라이더 드래그 중 호출, 이미지 편집 없이 랜드마크만 계산)"""
        if DEBUG_MORPHING_UPDATE:
            print("[update_polygons_only]", f": called.. this time just return")

        if self.current_image is None:
            return

        try:
            import gui.FaceForge.utils.morphing as utilmorph
            import gui.FaceForge.utils.landmarks as utilmarks
            
            # 변형된 랜드마크 계산 (이미지 편집 없이)
            base_image = self.current_image
            
            # left_eye_size = self.left_eye_size.get()
            # right_eye_size = self.left_eye_size.get()
            
            # 원본 랜드마크 가져오기 (항상 원본을 기준으로 변형)
            base_landmarks = self.landmark_manager.get_current_landmarks()
            if base_landmarks is not None:
                # 지시선 기반 스케일링 선택 여부 확인
                if hasattr(self, 'use_guide_line_scaling') and self.use_guide_line_scaling.get() and hasattr(self, 'guide_lines_manager'):
                    # 지시선 기반 스케일링
                    try:
                        # 지시선 정보 가져오기
                        img_width = getattr(self, 'preview_width', 800)
                        img_height = getattr(self, 'preview_height', 1000)
                        left_center, right_center, angle = self.guide_lines_manager.get_eye_centers_and_angle(
                            base_landmarks, img_width, img_height
                        )
                        
                        
                    except Exception as e:
                        error("update_polygons_only",f"지시선 기반 스케일링 오류: {e}")
                        
                else:
                    pass                

                # 중앙 포인트 좌표 초기화 (original_face_landmarks에서 계산)
                if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                    img_width, img_height = base_image.size
                    left_iris_indices, right_iris_indices = self._get_iris_indices()
                    # 드래그 좌표가 없으면 original_face_landmarks에서 계산
                    if not (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None):
                        left_center = self._calculate_iris_center(self._original_face_landmarks, left_iris_indices, img_width, img_height)
                        if left_center is not None:
                            self._left_iris_center_coord = left_center
                    if not (hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None):
                        right_center = self._calculate_iris_center(self._original_face_landmarks, right_iris_indices, img_width, img_height)
                        if right_center is not None:
                            self._right_iris_center_coord = right_center
                
                # 폴리곤만 다시 그리기 (전체 업데이트 대신)
                if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items['original'].clear()
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
                         # current_landmarks 가져오기 (슬라이더 적용된 랜드마크)
                        current = self.landmark_manager.get_current_landmarks()
                        if current is not None:
                            # Tesselation 모드 확인
                            is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
                            
                            # Tesselation 모드일 때 iris_centers 전달
                            iris_centers_for_drawing = None
                            face_landmarks_for_drawing = current
                            
                            if is_tesselation_selected:
                                # Tesselation 모드: iris_centers 사용
                                iris_centers_for_drawing = self.landmark_manager.get_custom_iris_centers()
                                if iris_centers_for_drawing is None and len(current) == 470:
                                    # custom_landmarks에서 중앙 포인트 추출 (마지막 2개)
                                    iris_centers_for_drawing = current[-2:]
                                    face_landmarks_for_drawing = current[:-2]  # 468개
                            
                            self._draw_landmark_polygons(
                                self.canvas_original,
                                self.current_image,
                                face_landmarks_for_drawing,  # 468개 또는 470개
                                self.canvas_original_pos_x,
                                self.canvas_original_pos_y,
                                self.landmark_polygon_items['original'],
                                "green",
                                current_tab,
                                iris_centers=iris_centers_for_drawing,  # Tesselation 모드일 때만 전달
                                force_use_custom=True  # custom_landmarks를 명시적으로 전달했으므로 강제 사용
                            )
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _log_polygon_debug_info(self, face_landmarks, transformed_indices, original_face_landmarks_tuple, has_iris_centers):
        try:
            transformed_count = len(transformed_indices) if transformed_indices else 0
            total_points = len(face_landmarks) if face_landmarks is not None else 0
            original_count = len(original_face_landmarks_tuple) if original_face_landmarks_tuple is not None else 0
            if DEBUG_APPLY_SLIDERS:
                debug( "_log_polygon_debug_info",
                    f"폴리곤 디버그: transformed={transformed_count}, face_points={total_points}, original_tuple={original_count}, iris_centers={has_iris_centers}",
                )
        except Exception as exc:  # pylint: disable=broad-except
            error("_log_polygon_debug_info", f"폴리곤 디버그 로그 실패: {exc}")            

    def _handle_advanced_mode(self, selected_regions, slider_values, image):
        pivot_x = slider_values['pivot_x']
        pivot_y = slider_values['pivot_y']
        size_x = slider_values['size_x']
        size_y = slider_values['size_y']
        position_x = slider_values['position_x']
        position_y = slider_values['position_y']

        if DEBUG_APPLY_SLIDERS:
            debug("_handle_advanced_mode",f"regions: {len(selected_regions)}, sliders: {len(slider_values)}")

        # NOTE: 전체 탭 size X/Y는 custom_landmarks를 직접 변형하며, 현재는 회전 정보 없이 수평/수직 스케일만 적용된다.
        #       가이드축 연동 시점은 이 호출 이후 `_collect_landmark_transform_context` → `_transform_selected_landmarks` 흐름이다.
        result = self._apply_common_sliders_to_landmarks(
            selected_regions,
            pivot_x,
            pivot_y,
            size_x,
            size_y,
            position_x,
            position_y,
            image,
        )

        return result

    def _is_advanced_mode(self):
        use_warping = getattr(self, 'use_landmark_warping', None)
        has_current_landmarks = hasattr(self, 'current_face_landmarks') and self.current_face_landmarks is not None
        result = (
            use_warping is not None and
            hasattr(use_warping, 'get') and
            use_warping.get() and
            has_current_landmarks
        )
        # if DEBUG_APPLY_SLIDERS:
        #     debug("_is_advanced_mode", f"use_warping={use_warping}, use_warping.get()={use_warping.get() if use_warping and hasattr(use_warping, 'get') else 'N/A'}, has_custom_landmarks={has_current_landmarks}, result={result}")
        return result

    def _should_use_guide_axis(self):
        return True
        # return (
        #     hasattr(self, 'use_guide_line_scaling') and
        #     hasattr(self.use_guide_line_scaling, 'get') and
        #     self.use_guide_line_scaling.get() and
        #     hasattr(self, 'guide_lines_manager')
        # )       


    def _apply_common_sliders(self, image, base_image=None):
        """공통 슬라이더(Size, Position, Center Offset) 적용"""

        is_advanced_mode = self._is_advanced_mode()
        selected_regions = self._get_selected_regions()
        
        if DEBUG_APPLY_SLIDERS:
            print(f"{'_' * 80}")
            debug("_apply_common_sliders",
                f"image={image is not None}, "
                f"고급모드: {is_advanced_mode}, "
                f"선택된 부위: {len(selected_regions)} ")

        if image is None:
            return image

        if not selected_regions:
            return image
        
        try:

            slider_values, slider_conditions = self._get_common_slider_values()
            if DEBUG_APPLY_SLIDERS:
                debug("_apply_common_sliders",
                    f"size_condition={slider_conditions['size_condition']}, "
                    f"pos_x_condition={slider_conditions['pos_x_condition']}, "
                    f"pos_y_condition={slider_conditions['pos_y_condition']}, "
                    f"size=({slider_values['size_x']:.3f}, {slider_values['size_y']:.3f}), "
                    f"pos=({slider_values['position_x']:.3f}, {slider_values['position_y']:.3f})")            

            # if getattr(self, 'debug_guide_axis', False):
            #     size_x = slider_values.get('size_x')
            #     size_y = slider_values.get('size_y')
            #     center_offset_x = slider_values.get('center_offset_x')
            #     center_offset_y = slider_values.get('center_offset_y')
            #     print(
            #         f"[GuideAxis] sliders size_x={size_x} size_y={size_y} "
            #         f"center_offset=({center_offset_x},{center_offset_y})"
            #     )

            # if is_advanced_mode:
            #     return self._handle_advanced_mode(selected_regions, slider_values, image)
            
            return self._apply_common_sliders_general_mode(
                image=image,
                selected_regions=selected_regions,
                slider_values=slider_values,
                slider_conditions=slider_conditions,
            )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return image            