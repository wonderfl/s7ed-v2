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



class UtilsMixin:
    """유틸리티 기능 Mixin"""
    
    def update_labels_only(self):
        """라벨만 업데이트 (슬라이더 드래그 중 호출)"""
        # 왼쪽/오른쪽 눈 라벨 업데이트 (라벨이 존재하는 경우에만)
        if hasattr(self, 'left_eye_size_label') and self.left_eye_size_label is not None:
            left_eye_value = self.left_eye_size.get()
            self.left_eye_size_label.config(text=f"{int(left_eye_value * 100)}%")
        
        if hasattr(self, 'right_eye_size_label') and self.right_eye_size_label is not None:
            right_eye_value = self.right_eye_size.get()
            self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
        
        if hasattr(self, 'nose_size_label') and self.nose_size_label is not None:
            nose_value = self.nose_size.get()
            self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        # 입 편집 라벨 업데이트 (라벨이 존재하는 경우에만)
        if hasattr(self, 'upper_lip_shape_label') and self.upper_lip_shape_label is not None:
            upper_lip_shape_value = self.upper_lip_shape.get()
            self.upper_lip_shape_label.config(text=f"{int(upper_lip_shape_value * 100)}%")
        
        if hasattr(self, 'lower_lip_shape_label') and self.lower_lip_shape_label is not None:
            lower_lip_shape_value = self.lower_lip_shape.get()
            self.lower_lip_shape_label.config(text=f"{int(lower_lip_shape_value * 100)}%")
        
        if hasattr(self, 'upper_lip_width_label') and self.upper_lip_width_label is not None:
            upper_lip_width_value = self.upper_lip_width.get()
            self.upper_lip_width_label.config(text=f"{int(upper_lip_width_value * 100)}%")
        
        if hasattr(self, 'lower_lip_width_label') and self.lower_lip_width_label is not None:
            lower_lip_width_value = self.lower_lip_width.get()
            self.lower_lip_width_label.config(text=f"{int(lower_lip_width_value * 100)}%")
        
        if hasattr(self, 'upper_lip_vertical_move_label') and self.upper_lip_vertical_move_label is not None:
            upper_lip_vertical_move_value = self.upper_lip_vertical_move.get()
            self.upper_lip_vertical_move_label.config(text=f"{int(upper_lip_vertical_move_value)}")
        
        if hasattr(self, 'lower_lip_vertical_move_label') and self.lower_lip_vertical_move_label is not None:
            lower_lip_vertical_move_value = self.lower_lip_vertical_move.get()
            self.lower_lip_vertical_move_label.config(text=f"{int(lower_lip_vertical_move_value)}")
        
        # 입술 영역 라벨 업데이트 (라벨이 존재하는 경우에만)
        if hasattr(self, 'upper_lip_region_padding_x_label') and self.upper_lip_region_padding_x_label is not None:
            upper_lip_region_padding_x_value = self.upper_lip_region_padding_x.get()
            self.upper_lip_region_padding_x_label.config(text=f"{int(upper_lip_region_padding_x_value * 100)}%")
        
        if hasattr(self, 'upper_lip_region_padding_y_label') and self.upper_lip_region_padding_y_label is not None:
            upper_lip_region_padding_y_value = self.upper_lip_region_padding_y.get()
            self.upper_lip_region_padding_y_label.config(text=f"{int(upper_lip_region_padding_y_value * 100)}%")
        
        if hasattr(self, 'upper_lip_region_offset_x_label') and self.upper_lip_region_offset_x_label is not None:
            upper_lip_region_offset_x_value = self.upper_lip_region_offset_x.get()
            self.upper_lip_region_offset_x_label.config(text=f"{int(upper_lip_region_offset_x_value)}")
        
        if hasattr(self, 'upper_lip_region_offset_y_label') and self.upper_lip_region_offset_y_label is not None:
            upper_lip_region_offset_y_value = self.upper_lip_region_offset_y.get()
            self.upper_lip_region_offset_y_label.config(text=f"{int(upper_lip_region_offset_y_value)}")
        
        if hasattr(self, 'lower_lip_region_padding_x_label') and self.lower_lip_region_padding_x_label is not None:
            lower_lip_region_padding_x_value = self.lower_lip_region_padding_x.get()
            self.lower_lip_region_padding_x_label.config(text=f"{int(lower_lip_region_padding_x_value * 100)}%")
        
        if hasattr(self, 'lower_lip_region_padding_y_label') and self.lower_lip_region_padding_y_label is not None:
            lower_lip_region_padding_y_value = self.lower_lip_region_padding_y.get()
            self.lower_lip_region_padding_y_label.config(text=f"{int(lower_lip_region_padding_y_value * 100)}%")
        
        if hasattr(self, 'lower_lip_region_offset_x_label') and self.lower_lip_region_offset_x_label is not None:
            lower_lip_region_offset_x_value = self.lower_lip_region_offset_x.get()
            self.lower_lip_region_offset_x_label.config(text=f"{int(lower_lip_region_offset_x_value)}")
        
        if hasattr(self, 'lower_lip_region_offset_y_label') and self.lower_lip_region_offset_y_label is not None:
            lower_lip_region_offset_y_value = self.lower_lip_region_offset_y.get()
            self.lower_lip_region_offset_y_label.config(text=f"{int(lower_lip_region_offset_y_value)}")
        
        # 턱선 라벨 업데이트 (라벨이 존재하는 경우에만)
        if hasattr(self, 'jaw_size_label') and self.jaw_size_label is not None:
            jaw_value = self.jaw_size.get()
            self.jaw_size_label.config(text=f"{int(jaw_value)}")
        
        # 얼굴 크기 라벨 업데이트 (라벨이 존재하는 경우에만)
        if hasattr(self, 'face_width_label') and self.face_width_label is not None:
            face_width_value = self.face_width.get()
            self.face_width_label.config(text=f"{int(face_width_value * 100)}%")
        
        if hasattr(self, 'face_height_label') and self.face_height_label is not None:
            face_height_value = self.face_height.get()
            self.face_height_label.config(text=f"{int(face_height_value * 100)}%")
        
        # 눈 위치 라벨 업데이트 (왼쪽/오른쪽 개별, 라벨이 존재하는 경우에만)
        if hasattr(self, 'left_eye_position_y_label') and self.left_eye_position_y_label is not None:
            left_eye_position_y_value = self.left_eye_position_y.get()
            self.left_eye_position_y_label.config(text=f"{int(left_eye_position_y_value)}")
        
        if hasattr(self, 'right_eye_position_y_label') and self.right_eye_position_y_label is not None:
            right_eye_position_y_value = self.right_eye_position_y.get()
            self.right_eye_position_y_label.config(text=f"{int(right_eye_position_y_value)}")
        
        if hasattr(self, 'left_eye_position_x_label') and self.left_eye_position_x_label is not None:
            left_eye_position_x_value = self.left_eye_position_x.get()
            self.left_eye_position_x_label.config(text=f"{int(left_eye_position_x_value)}")
        
        if hasattr(self, 'right_eye_position_x_label') and self.right_eye_position_x_label is not None:
            right_eye_position_x_value = self.right_eye_position_x.get()
            self.right_eye_position_x_label.config(text=f"{int(right_eye_position_x_value)}")
        
        # 눈 영역 라벨 업데이트 (개별 적용, 라벨이 존재하는 경우에만)
        if hasattr(self, 'left_eye_region_padding_label') and self.left_eye_region_padding_label is not None:
            left_eye_region_padding_value = self.left_eye_region_padding.get()
            self.left_eye_region_padding_label.config(text=f"{int(left_eye_region_padding_value * 100)}%")
        
        if hasattr(self, 'right_eye_region_padding_label') and self.right_eye_region_padding_label is not None:
            right_eye_region_padding_value = self.right_eye_region_padding.get()
            self.right_eye_region_padding_label.config(text=f"{int(right_eye_region_padding_value * 100)}%")
        
        # 눈 영역 위치 라벨 업데이트 (개별 적용, 라벨이 존재하는 경우에만)
        if hasattr(self, 'left_eye_region_offset_x_label') and self.left_eye_region_offset_x_label is not None:
            left_eye_region_offset_x_value = self.left_eye_region_offset_x.get()
            self.left_eye_region_offset_x_label.config(text=f"{int(left_eye_region_offset_x_value)}")
        
        if hasattr(self, 'left_eye_region_offset_y_label') and self.left_eye_region_offset_y_label is not None:
            left_eye_region_offset_y_value = self.left_eye_region_offset_y.get()
            self.left_eye_region_offset_y_label.config(text=f"{int(left_eye_region_offset_y_value)}")
        
        if hasattr(self, 'right_eye_region_offset_x_label') and self.right_eye_region_offset_x_label is not None:
            right_eye_region_offset_x_value = self.right_eye_region_offset_x.get()
            self.right_eye_region_offset_x_label.config(text=f"{int(right_eye_region_offset_x_value)}")
        
        if hasattr(self, 'right_eye_region_offset_y_label') and self.right_eye_region_offset_y_label is not None:
            right_eye_region_offset_y_value = self.right_eye_region_offset_y.get()
            self.right_eye_region_offset_y_label.config(text=f"{int(right_eye_region_offset_y_value)}")
        
        # 공통 슬라이더 라벨 업데이트 (Region Adjustment)
        if hasattr(self, 'region_center_offset_x_label') and self.region_center_offset_x_label is not None:
            region_center_offset_x_value = self.region_center_offset_x.get()
            self.region_center_offset_x_label.config(text=f"{int(region_center_offset_x_value)}")
        
        if hasattr(self, 'region_center_offset_y_label') and self.region_center_offset_y_label is not None:
            region_center_offset_y_value = self.region_center_offset_y.get()
            self.region_center_offset_y_label.config(text=f"{int(region_center_offset_y_value)}")
        
        if hasattr(self, 'region_size_x_label') and self.region_size_x_label is not None:
            region_size_x_value = self.region_size_x.get()
            self.region_size_x_label.config(text=f"{int(region_size_x_value * 100)}%")
        
        if hasattr(self, 'region_size_y_label') and self.region_size_y_label is not None:
            region_size_y_value = self.region_size_y.get()
            self.region_size_y_label.config(text=f"{int(region_size_y_value * 100)}%")
        
        if hasattr(self, 'region_position_x_label') and self.region_position_x_label is not None:
            region_position_x_value = self.region_position_x.get()
            self.region_position_x_label.config(text=f"{int(region_position_x_value)}")
        
        if hasattr(self, 'region_position_y_label') and self.region_position_y_label is not None:
            region_position_y_value = self.region_position_y.get()
            self.region_position_y_label.config(text=f"{int(region_position_y_value)}")
        
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
            if not self.landmark_manager.has_original_landmarks():
                # original_landmarks가 없으면 face_landmarks 사용 (없으면 감지)
                if self.landmark_manager.get_face_landmarks() is None:
                    detected, _ = face_landmarks.detect_face_landmarks(base_image)
                    if detected is not None:
                        self.landmark_manager.set_original_landmarks(detected)
                        self.landmark_manager.set_face_landmarks(detected)
                        self.original_landmarks = self.landmark_manager.get_original_landmarks()
                        self.face_landmarks = self.landmark_manager.get_face_landmarks()
            base_landmarks = self.landmark_manager.get_original_landmarks()
            if base_landmarks is None:
                base_landmarks = self.landmark_manager.get_face_landmarks()
            
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
                
                # custom_landmarks 업데이트 (드래그된 포인트 보존)
                # 드래그된 포인트 인덱스 가져오기
                dragged_indices = self.landmark_manager.get_dragged_indices()
                custom = self.landmark_manager.get_custom_landmarks()
                
                # 이전 transformed_landmarks 가져오기 (드래그 오프셋 계산용)
                prev_transformed = self.landmark_manager.get_transformed_landmarks()
                
                # transformed_landmarks 업데이트
                self.landmark_manager.set_transformed_landmarks(transformed)
                
                if custom is None or not dragged_indices:
                    # custom_landmarks가 없거나 드래그된 포인트가 없으면 전체를 변환된 랜드마크로 설정
                    self.landmark_manager.set_custom_landmarks(transformed, reason="update_polygons_only")
                else:
                    # 드래그된 포인트가 있으면: transformed를 복사하고 드래그된 포인트는 custom_landmarks에서 가져와서 변환 적용
                    new_custom = list(transformed)
                    
                    # 이전 transformed_landmarks가 없으면 (드래그 시작 시 원본에서 시작한 경우)
                    if prev_transformed is None or len(prev_transformed) != len(custom):
                        # 이전 사이즈 변환이 없었던 경우: 드래그 오프셋 = custom[idx] - base_landmarks[idx]
                        print(f"[얼굴편집] update_polygons_only - 드래그 오프셋 계산: 이전 사이즈 변환 없음, 원본 기준")
                        for idx in dragged_indices:
                            if idx < len(custom) and idx < len(new_custom) and idx < len(base_landmarks):
                                orig_x, orig_y = base_landmarks[idx]
                                dragged_x, dragged_y = custom[idx]
                                transformed_x, transformed_y = transformed[idx]
                                # 드래그 오프셋 (원본 기준)
                                offset_x = dragged_x - orig_x
                                offset_y = dragged_y - orig_y
                                # 새로운 사이즈 변환된 위치에 드래그 오프셋 적용
                                new_custom[idx] = (transformed_x + offset_x, transformed_y + offset_y)
                    else:
                        # 이전 사이즈 변환이 있었던 경우: 드래그 오프셋 = custom[idx] - prev_transformed[idx]
                        print(f"[얼굴편집] update_polygons_only - 드래그 오프셋 계산: 이전 사이즈 변환 있음, 이전 변환 기준")
                        for idx in dragged_indices:
                            if idx < len(custom) and idx < len(new_custom) and idx < len(prev_transformed):
                                # 이전 사이즈 변환된 위치
                                prev_transformed_x, prev_transformed_y = prev_transformed[idx]
                                # 드래그된 위치 (이전 사이즈 변환 + 드래그)
                                dragged_x, dragged_y = custom[idx]
                                # 새로운 사이즈 변환된 위치
                                transformed_x, transformed_y = transformed[idx]
                                
                                # 순수 드래그 오프셋 (이전 사이즈 변환 기준)
                                drag_offset_x = dragged_x - prev_transformed_x
                                drag_offset_y = dragged_y - prev_transformed_y
                                
                                # 새로운 사이즈 변환된 위치에 드래그 오프셋 적용
                                new_custom[idx] = (transformed_x + drag_offset_x, transformed_y + drag_offset_y)
                    
                    self.landmark_manager.set_custom_landmarks(new_custom, reason="update_polygons_only")
                # 중앙 포인트 좌표 초기화 (original_landmarks에서 계산)
                if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                    if hasattr(self, 'original_landmarks') and self.original_landmarks is not None:
                        img_width, img_height = base_image.size
                        left_iris_indices, right_iris_indices = self._get_iris_indices()
                        # 드래그 좌표가 없으면 original_landmarks에서 계산
                        if not (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None):
                            left_center = self._calculate_iris_center(self.original_landmarks, left_iris_indices, img_width, img_height)
                            if left_center is not None:
                                self._left_iris_center_coord = left_center
                        if not (hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None):
                            right_center = self._calculate_iris_center(self.original_landmarks, right_iris_indices, img_width, img_height)
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
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_region_indices(self, region_name):
        """부위 이름에 해당하는 랜드마크 인덱스 목록 반환"""
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            indices = set()
            
            if region_name == 'face_oval':
                FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
                for conn in FACE_OVAL:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'left_eye':
                LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
                for conn in LEFT_EYE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'right_eye':
                RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
                for conn in RIGHT_EYE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'left_eyebrow':
                LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
                for conn in LEFT_EYEBROW:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'right_eyebrow':
                RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
                for conn in RIGHT_EYEBROW:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'nose':
                NOSE = list(mp_face_mesh.FACEMESH_NOSE)
                for conn in NOSE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'lips':
                LIPS = list(mp_face_mesh.FACEMESH_LIPS)
                for conn in LIPS:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'left_iris':
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, _ = get_iris_indices()
                    indices.update(left_iris_indices)
                except (ImportError, AttributeError):
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477])
                    indices.update([474, 475, 476, 477])
            elif region_name == 'right_iris':
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    _, right_iris_indices = get_iris_indices()
                    indices.update(right_iris_indices)
                except (ImportError, AttributeError):
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: RIGHT_IRIS=[469,470,471,472])
                    indices.update([469, 470, 471, 472])
            elif region_name == 'contours':
                CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
                for conn in CONTOURS:
                    indices.add(conn[0])
                    indices.add(conn[1])
            elif region_name == 'tesselation':
                TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
                for conn in TESSELATION:
                    indices.add(conn[0])
                    indices.add(conn[1])
                # Tesselation 선택 시 눈동자도 포함
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    indices.update(left_iris_indices)
                    indices.update(right_iris_indices)
                except (ImportError, AttributeError):
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    indices.update([474, 475, 476, 477])
                    indices.update([469, 470, 471, 472])
            
            return list(indices)
            
        except Exception as e:
            print(f"[얼굴편집] 부위 인덱스 가져오기 실패 ({region_name}): {e}")
            return []
    
