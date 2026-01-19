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
    
    def _transform_eye_center(self, orig_eye_center, center_x, center_y, size_x, size_y, position_x, position_y):
        """원본 눈 중심점을 얼굴 전체 중심점 기준으로 변형"""
        orig_rel_eye_x = orig_eye_center[0] - center_x
        orig_rel_eye_y = orig_eye_center[1] - center_y
        # 크기 조절
        if abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
            orig_rel_eye_x *= size_x
            orig_rel_eye_y *= size_y
        # 위치 이동
        orig_rel_eye_x += position_x
        orig_rel_eye_y += position_y
        # 변형된 눈 중심점
        return (center_x + orig_rel_eye_x, center_y + orig_rel_eye_y)
    
    def _calculate_and_update_iris_center(self, eye_side, orig_eye_center, trans_eye_center, 
                                         original_landmarks, img_width, img_height, 
                                         size_x, size_y, iris_indices_in_all, updated_landmarks):
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
        
        # 눈 중심점 기준으로 변형 (Tesselation과 동일한 크기/위치 비율)
        new_rel_iris_x = orig_rel_iris_x * size_x
        new_rel_iris_y = orig_rel_iris_y * size_y
        
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
                                    position_x, position_y, image):
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
            
            # 크기 조절
            if abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
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
                        orig_left_eye, center_x, center_y, size_x, size_y, position_x, position_y
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
                        orig_right_eye, center_x, center_y, size_x, size_y, position_x, position_y
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
    
    def _apply_common_sliders(self, image, base_image=None):
        """공통 슬라이더(Size, Position, Center Offset) 적용"""
        if image is None:
            return image
        
        try:
            # 고급 모드 확인
            use_warping = getattr(self, 'use_landmark_warping', None)
            is_advanced_mode = (use_warping is not None and hasattr(use_warping, 'get') and use_warping.get() and
                               hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None)
            
            # 선택된 부위 목록 가져오기
            selected_regions = []
            if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
                selected_regions.append('face_oval')
            if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
                selected_regions.append('left_eye')
            if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
                selected_regions.append('right_eye')
            if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
                selected_regions.append('left_eyebrow')
            if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
                selected_regions.append('right_eyebrow')
            if hasattr(self, 'show_nose') and self.show_nose.get():
                selected_regions.append('nose')
            if hasattr(self, 'show_lips') and self.show_lips.get():
                selected_regions.append('lips')
            if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
                selected_regions.append('left_iris')
            if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
                selected_regions.append('right_iris')
            if hasattr(self, 'show_contours') and self.show_contours.get():
                selected_regions.append('contours')
            if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
                selected_regions.append('tesselation')
            
            if not selected_regions:
                return image
            
            # 공통 슬라이더 값 가져오기
            center_offset_x = self.region_center_offset_x.get()
            center_offset_y = self.region_center_offset_y.get()
            size_x = self.region_size_x.get()
            size_y = self.region_size_y.get()
            position_x = self.region_position_x.get()
            position_y = self.region_position_y.get()
            
            print(f"[얼굴편집] 공통 슬라이더 적용: size_x={size_x:.2f}, size_y={size_y:.2f}, center_offset=({center_offset_x:.1f}, {center_offset_y:.1f}), position=({position_x:.1f}, {position_y:.1f})")
            print(f"[얼굴편집] 선택된 부위: {selected_regions}, 고급 모드: {is_advanced_mode}")
            
            # 선택된 부위가 있고 슬라이더 값이 기본값이 아니면 적용
            size_x_condition = abs(size_x - 1.0) >= 0.01
            size_y_condition = abs(size_y - 1.0) >= 0.01
            size_condition = size_x_condition or size_y_condition
            offset_x_condition = abs(center_offset_x) >= 0.1
            offset_y_condition = abs(center_offset_y) >= 0.1
            pos_x_condition = abs(position_x) >= 0.1
            pos_y_condition = abs(position_y) >= 0.1
            
            conditions_met = offset_x_condition or offset_y_condition or size_condition or pos_x_condition or pos_y_condition
            print(f"[얼굴편집] 슬라이더 조건 확인: size_x={size_x_condition}, size_y={size_y_condition}, offset_x={offset_x_condition}, offset_y={offset_y_condition}, pos_x={pos_x_condition}, pos_y={pos_y_condition}, 통과={conditions_met}")
            
            # 고급 모드: custom_landmarks의 포인트를 직접 조절
            if is_advanced_mode:
                result = self._apply_common_sliders_to_landmarks(selected_regions, center_offset_x, center_offset_y, 
                                                                   size_x, size_y, position_x, position_y, image)
                # 이미지가 변형되었으므로 미리보기 업데이트
                if result is not None and result != image:
                    self.edited_image = result
                    self.show_edited_preview()
                    if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                        self.update_face_features_display()
                return result
            
            # 일반 모드: 이미지 영역 변형
            import utils.face_landmarks as face_landmarks
            landmarks, _ = face_landmarks.detect_face_landmarks(image)
            print(f"[얼굴편집] 랜드마크 감지 결과: landmarks={'있음' if landmarks is not None else '없음'}")
            
            if landmarks is None:
                return image
            
            from utils.face_morphing.adjustments import adjust_region_size, adjust_region_position
            result = image
            
            # 각 부위에 대해 순차적으로 적용
            for region_name in selected_regions:
                # 1. 크기 조절
                if size_condition:
                    print(f"[얼굴편집] 크기 조절 적용: {region_name}, size_x={size_x:.2f}, size_y={size_y:.2f}")
                    result = adjust_region_size(result, region_name, size_x, size_y, center_offset_x, center_offset_y, landmarks)
                    if result is None:
                        print_warning("얼굴편집", f"{region_name} 크기 조절 결과가 None입니다")
                        result = image
                    else:
                        # 랜드마크 업데이트 (크기 조절 후)
                        landmarks, _ = face_landmarks.detect_face_landmarks(result)
                        image = result  # 다음 단계를 위해 업데이트
                
                # 2. 위치 이동
                if pos_x_condition or pos_y_condition:
                    result = adjust_region_position(result, region_name, position_x, position_y, 
                                                  center_offset_x, center_offset_y, landmarks)
                    if result is None:
                        print_warning("얼굴편집", f"{region_name} 위치 이동 결과가 None입니다")
                        result = image
                    else:
                        # 랜드마크 업데이트 (위치 이동 후)
                        landmarks, _ = face_landmarks.detect_face_landmarks(result)
                        image = result  # 다음 단계를 위해 업데이트
            
            return result if result is not None else image
            
        except Exception as e:
            print(f"[얼굴편집] 공통 슬라이더 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            return image
    
    def _apply_common_sliders_to_landmarks(self, selected_regions, center_offset_x, center_offset_y, 
                                          size_x, size_y, position_x, position_y, image):
        print(f"[얼굴편집] _apply_common_sliders_to_landmarks 호출: 선택된 부위={selected_regions}")
        """고급 모드: 공통 슬라이더로 custom_landmarks의 포인트를 직접 조절"""
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        if custom is None:
            return image
        
        try:
            from utils.face_morphing.region_extraction import _get_region_center
            import utils.face_landmarks as face_landmarks
            
            # 원본 랜드마크 가져오기 (LandmarkManager 사용)
            if not self.landmark_manager.has_original_face_landmarks():
                # MediaPipe로 랜드마크 감지 (478개 또는 468개)
                original_landmarks_full, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if original_landmarks_full is None:
                    return image
                
                # LandmarkManager에 저장 (자동으로 얼굴/눈동자 분리)
                self.landmark_manager.set_original_landmarks(original_landmarks_full)
                self.original_landmarks = self.landmark_manager.get_original_landmarks_full()
            
            # 얼굴 랜드마크 (468개) 가져오기
            original_face_landmarks = self.landmark_manager.get_original_face_landmarks()
            # 눈동자 랜드마크 (10개) 가져오기
            original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            # 전체 랜드마크
            original_landmarks = self.landmark_manager.get_original_landmarks_full()
            
            # custom_landmarks 초기화 (얼굴 랜드마크만, 468개)
            if self.custom_landmarks is None or len(self.custom_landmarks) != 468:
                if original_face_landmarks is not None:
                    # original_face_landmarks는 원본이므로 복사본이 필요할 수 있지만,
                    # 직접 참조로 저장 (원본은 읽기 전용이므로 안전)
                    self.custom_landmarks = original_face_landmarks
            
            # 드래그로 변경된 포인트 추적 (LandmarkManager에서 직접 가져오기)
            # 슬라이더 변형을 적용할 때 이 포인트들은 건너뛰어야 함
            dragged_indices = self.landmark_manager.get_dragged_indices()
            
            # 사이즈 변환 중복 적용 방지: 원본 랜드마크를 기준으로 변환 적용
            # 드래그된 포인트만 custom_landmarks에서 보존
            updated_landmarks = []
            img_width, img_height = image.size
            
            # 원본 랜드마크를 기준으로 초기화 (사이즈 변환 중복 방지)
            base_landmarks = original_face_landmarks if original_face_landmarks is not None else (original_landmarks[:468] if len(original_landmarks) >= 468 else original_landmarks)
            for idx in range(len(base_landmarks)):
                if isinstance(base_landmarks[idx], tuple):
                    updated_landmarks.append(base_landmarks[idx])
                else:
                    updated_landmarks.append((
                        base_landmarks[idx].x * img_width,
                        base_landmarks[idx].y * img_height
                    ))
            
            # 드래그된 포인트는 custom_landmarks에서 가져와서 보존 (사이즈 변환 포함된 상태)
            custom = self.landmark_manager.get_custom_landmarks()
            
            # custom_landmarks가 470개인 경우 마지막 2개(중앙 포인트)를 제외한 468개만 사용
            custom_for_drag = custom
            if custom is not None and len(custom) == 470:
                custom_for_drag = custom[:468]  # 마지막 2개 제외
            
            if custom_for_drag is not None and len(custom_for_drag) == 468 and dragged_indices:
                # 드래그된 포인트만 custom_landmarks에서 가져와서 보존
                for idx in dragged_indices:
                    if 0 <= idx < len(custom_for_drag) and idx < len(updated_landmarks):
                        if isinstance(custom_for_drag[idx], tuple):
                            updated_landmarks[idx] = custom_for_drag[idx]
                        else:
                            updated_landmarks[idx] = (
                                custom_for_drag[idx].x * img_width,
                                custom_for_drag[idx].y * img_height
                            )
                print_info("얼굴편집", f"드래그된 포인트 {len(dragged_indices)}개를 custom_landmarks에서 보존 (사이즈 변환 포함, custom 길이={len(custom) if custom is not None else 0})")
            
            # 확장 레벨 가져오기
            expansion_level = getattr(self, 'polygon_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'polygon_expansion_level') else 1
            print_debug("얼굴편집", f"확장 레벨: {expansion_level}, 선택된 부위: {selected_regions}")
            
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
                    if len(eyebrow_in_graph) < len(eyebrow_check_indices):
                        print(f"[얼굴편집] 경고: 눈썹 인덱스 중 {len(eyebrow_check_indices) - len(eyebrow_in_graph)}개가 그래프에 없음 (그래프 크기: {len(tesselation_graph)})")
                except ImportError:
                    pass
            
            # Tesselation 선택 시 전체 얼굴 중심점 사용
            if 'tesselation' in selected_regions and len(selected_regions) == 1:
                # Tesselation만 선택된 경우: 전체 얼굴 중심점 사용
                all_indices = set()
                for region_name in selected_regions:
                    region_indices = set(self._get_region_indices(region_name))
                    all_indices.update(region_indices)
                
                # 눈동자 인덱스 분리 (별도 처리, MediaPipe 정의 사용)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices = set(left_iris_indices + right_iris_indices)
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    iris_indices = set([469, 470, 471, 472, 474, 475, 476, 477])
                iris_indices_in_all = all_indices & iris_indices
                face_indices = all_indices - iris_indices
                
                # 확장 레벨에 따라 이웃 포인트 추가 (눈동자 제외)
                if expansion_level > 0 and tesselation_graph:
                    current_indices = face_indices.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(updated_landmarks) and neighbor not in iris_indices:
                                        next_level_indices.add(neighbor)
                        face_indices.update(next_level_indices)
                        current_indices = next_level_indices
                
                # Tesselation 변형 적용 (드래그로 변경된 포인트는 제외)
                # face_indices에서 드래그로 변경된 포인트 제거
                face_indices_for_transform = face_indices - dragged_indices
                self._apply_tesselation_transform(
                    updated_landmarks, face_indices_for_transform, iris_indices_in_all,
                    center_offset_x, center_offset_y, size_x, size_y,
                    position_x, position_y, image
                )
            else:
                # 각 선택된 부위에 대해 랜드마크 포인트 조절
                # 이미 변형된 포인트 추적 (중복 변형 방지)
                transformed_indices = set()
                
                # 먼저 모든 선택된 부위의 기본 인덱스 수집 (확장 제한용)
                all_selected_base_indices = set()
                for region_name in selected_regions:
                    base_indices = set(self._get_region_indices(region_name))
                    all_selected_base_indices.update(base_indices)
                
                # 원본 랜드마크를 기준으로 각 부위의 중심점을 미리 계산 (여러 부위 선택 시 정확성 보장)
                region_centers = {}
                for region_name in selected_regions:
                    # 부위의 랜드마크 인덱스 가져오기
                    region_indices = set(self._get_region_indices(region_name))
                    if not region_indices:
                        continue
                    
                    # 원본 랜드마크를 기준으로 중심점 계산 (오프셋 포함)
                    center = _get_region_center(region_name, original_landmarks, center_offset_x, center_offset_y)
                    if center is None:
                        continue
                    region_centers[region_name] = center
                
                for region_name in selected_regions:
                    # 부위의 랜드마크 인덱스 가져오기
                    region_indices = set(self._get_region_indices(region_name))
                    if not region_indices:
                        continue
                    
                    original_region_count = len(region_indices)
                    
                    # 확장 레벨에 따라 이웃 포인트 추가
                    if expansion_level > 0 and tesselation_graph:
                        # 디버그: 눈썹인 경우 초기 상태 확인
                        if 'eyebrow' in region_name.lower():
                            eyebrow_in_graph_count = sum(1 for idx in region_indices if idx in tesselation_graph)
                            print(f"[얼굴편집] {region_name} 확장 전: {len(region_indices)}개 포인트, 그래프에 포함된 포인트: {eyebrow_in_graph_count}개")
                        
                        current_indices = region_indices.copy()
                        for level in range(expansion_level):
                            next_level_indices = set()
                            for idx in current_indices:
                                if idx in tesselation_graph:
                                    for neighbor in tesselation_graph[idx]:
                                        if neighbor < len(updated_landmarks):
                                            next_level_indices.add(neighbor)
                            region_indices.update(next_level_indices)
                            current_indices = next_level_indices
                        
                        # 확장 결과 로그 (눈썹 포함)
                        if 'eyebrow' in region_name.lower():
                            print_debug("얼굴편집", f"{region_name} 확장 (레벨 {expansion_level}): {len(region_indices)}개 포인트 (원본 {original_region_count}개에서 확장)")
                    elif 'eyebrow' in region_name.lower():
                        print_warning("얼굴편집", f"{region_name} 확장 실패: expansion_level={expansion_level}, tesselation_graph 크기={len(tesselation_graph)}")
                    
                    # 미리 계산한 중심점 사용
                    if region_name not in region_centers:
                        continue
                    
                    center_x, center_y = region_centers[region_name]
                    
                    # 눈동자 영역인 경우 중앙 포인트로 변환
                    if region_name in ['left_iris', 'right_iris']:
                        # 눈동자 포인트들의 중앙 포인트 계산
                        iris_points_orig = []
                        for idx in region_indices:
                            if idx < len(self.original_landmarks):
                                if isinstance(self.original_landmarks[idx], tuple):
                                    iris_points_orig.append(self.original_landmarks[idx])
                                else:
                                    img_width, img_height = image.size
                                    iris_points_orig.append((
                                        self.original_landmarks[idx].x * img_width,
                                        self.original_landmarks[idx].y * img_height
                                    ))
                        
                        if iris_points_orig:
                            # 원본 눈동자 중앙 포인트
                            orig_iris_center_x = sum(p[0] for p in iris_points_orig) / len(iris_points_orig)
                            orig_iris_center_y = sum(p[1] for p in iris_points_orig) / len(iris_points_orig)
                            
                            # 중심점 기준 상대 좌표
                            rel_x = orig_iris_center_x - center_x
                            rel_y = orig_iris_center_y - center_y
                            
                            # 크기 조절
                            if abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
                                rel_x *= size_x
                                rel_y *= size_y
                            
                            # 위치 이동
                            rel_x += position_x
                            rel_y += position_y
                            
                            # 새로운 좌표 계산
                            new_iris_center_x = center_x + rel_x
                            new_iris_center_y = center_y + rel_y
                            
                            # 중앙 포인트 좌표 업데이트 (LandmarkManager 사용)
                            if region_name == 'left_iris':
                                self.landmark_manager.set_iris_center_coords(
                                    (new_iris_center_x, new_iris_center_y),
                                    self.landmark_manager.get_right_iris_center_coord()
                                )
                            elif region_name == 'right_iris':
                                self.landmark_manager.set_iris_center_coords(
                                    self.landmark_manager.get_left_iris_center_coord(),
                                    (new_iris_center_x, new_iris_center_y)
                                )
                            
                            # 모든 눈동자 포인트를 중앙 포인트로 설정
                            for idx in region_indices:
                                if idx not in transformed_indices and idx < len(updated_landmarks):
                                    updated_landmarks[idx] = (new_iris_center_x, new_iris_center_y)
                                    transformed_indices.add(idx)
                    else:
                        # 일반 부위: 각 포인트를 개별적으로 변형
                        # 부위의 랜드마크 포인트들을 중심점 기준으로 조절 (확장된 포인트 포함)
                        # 이미 변형된 포인트는 제외 (중복 변형 방지)
                        # 드래그로 변경된 포인트도 제외 (드래그 변경 보존)
                        for idx in region_indices:
                            if idx in transformed_indices:
                                continue  # 이미 다른 부위에서 변형된 포인트는 건너뛰기
                            if idx in dragged_indices:
                                continue  # 드래그로 변경된 포인트는 건너뛰기 (보존)
                            if idx >= len(updated_landmarks):
                                continue
                            
                            # 현재 포인트 좌표
                            if isinstance(updated_landmarks[idx], tuple):
                                point_x, point_y = updated_landmarks[idx]
                            else:
                                img_width, img_height = image.size
                                point_x = updated_landmarks[idx].x * img_width
                                point_y = updated_landmarks[idx].y * img_height
                            
                            # 중심점 기준 상대 좌표
                            rel_x = point_x - center_x
                            rel_y = point_y - center_y
                            
                            # 크기 조절
                            if abs(size_x - 1.0) >= 0.01 or abs(size_y - 1.0) >= 0.01:
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
                            transformed_indices.add(idx)  # 변형된 포인트 추적
            
            # 변형된 포인트 인덱스 수집 (선택한 부위만)
            transformed_point_indices = set()
            base_for_compare = original_face_landmarks if original_face_landmarks is not None else (original_landmarks[:468] if len(original_landmarks) >= 468 else original_landmarks)
            if 'tesselation' in selected_regions and len(selected_regions) == 1:
                # Tesselation만 선택된 경우: 모든 변형된 포인트 포함
                for idx in range(len(updated_landmarks)):
                    if idx < len(base_for_compare):
                        # 원본과 변형된 랜드마크 비교
                        if isinstance(base_for_compare[idx], tuple) and isinstance(updated_landmarks[idx], tuple):
                            if abs(base_for_compare[idx][0] - updated_landmarks[idx][0]) > 0.1 or \
                               abs(base_for_compare[idx][1] - updated_landmarks[idx][1]) > 0.1:
                                transformed_point_indices.add(idx)
                        else:
                            # MediaPipe 형태인 경우
                            img_width, img_height = image.size
                            orig_x = base_for_compare[idx].x * img_width if hasattr(base_for_compare[idx], 'x') else base_for_compare[idx][0]
                            orig_y = base_for_compare[idx].y * img_height if hasattr(base_for_compare[idx], 'y') else base_for_compare[idx][1]
                            trans_x = updated_landmarks[idx][0] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].x * img_width
                            trans_y = updated_landmarks[idx][1] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].y * img_height
                            if abs(orig_x - trans_x) > 0.1 or abs(orig_y - trans_y) > 0.1:
                                transformed_point_indices.add(idx)
            else:
                # 각 선택된 부위의 실제로 변형된 포인트만 수집 (원본과 비교)
                for idx in range(len(updated_landmarks)):
                    if idx < len(base_for_compare):
                        # 원본과 변형된 랜드마크 비교
                        if isinstance(base_for_compare[idx], tuple) and isinstance(updated_landmarks[idx], tuple):
                            if abs(base_for_compare[idx][0] - updated_landmarks[idx][0]) > 0.1 or \
                               abs(base_for_compare[idx][1] - updated_landmarks[idx][1]) > 0.1:
                                transformed_point_indices.add(idx)
                        else:
                            # MediaPipe 형태인 경우
                            img_width, img_height = image.size
                            orig_x = base_for_compare[idx].x * img_width if hasattr(base_for_compare[idx], 'x') else base_for_compare[idx][0]
                            orig_y = base_for_compare[idx].y * img_height if hasattr(base_for_compare[idx], 'y') else base_for_compare[idx][1]
                            trans_x = updated_landmarks[idx][0] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].x * img_width
                            trans_y = updated_landmarks[idx][1] if isinstance(updated_landmarks[idx], tuple) else updated_landmarks[idx].y * img_height
                            if abs(orig_x - trans_x) > 0.1 or abs(orig_y - trans_y) > 0.1:
                                transformed_point_indices.add(idx)
            
            # 변형되지 않은 포인트는 원본 위치로 복원 (선택하지 않은 부위는 변형되지 않도록)
            # 단, 드래그로 변경된 포인트는 보존해야 함
            final_landmarks = list(updated_landmarks)  # 468개
            base_landmarks_for_restore = original_face_landmarks if original_face_landmarks is not None else (original_landmarks[:468] if len(original_landmarks) >= 468 else original_landmarks)
            for idx in range(len(base_landmarks_for_restore)):
                # 드래그로 변경된 포인트는 원본으로 복원하지 않음 (보존)
                if idx in dragged_indices:
                    continue
                if idx not in transformed_point_indices:
                    # 변형되지 않은 포인트는 원본 위치 유지
                    if isinstance(base_landmarks_for_restore[idx], tuple):
                        final_landmarks[idx] = base_landmarks_for_restore[idx]
                    else:
                        # MediaPipe 형태인 경우 tuple로 변환
                        img_width, img_height = image.size
                        final_landmarks[idx] = (
                            base_landmarks_for_restore[idx].x * img_width,
                            base_landmarks_for_restore[idx].y * img_height
                        )
            
            # original_face_landmarks를 tuple 형태로 변환 (morph_face_by_polygons에 전달하기 위해)
            original_face_landmarks_tuple = []
            img_width, img_height = image.size
            base_for_tuple = original_face_landmarks if original_face_landmarks is not None else (original_landmarks[:468] if len(original_landmarks) >= 468 else original_landmarks)
            for idx in range(len(base_for_tuple)):
                if isinstance(base_for_tuple[idx], tuple):
                    original_face_landmarks_tuple.append(base_for_tuple[idx])
                else:
                    # MediaPipe 형태인 경우 tuple로 변환
                    original_face_landmarks_tuple.append((
                        base_for_tuple[idx].x * img_width,
                        base_for_tuple[idx].y * img_height
                    ))
            
            # Tesselation 선택 시: 중앙 포인트 추가 (눈동자 제거 불필요, 이미 468개)
            if 'tesselation' in selected_regions and len(selected_regions) == 1:
                # 중앙 포인트 좌표 가져오기 (드래그로 변환된 좌표 또는 계산)
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                
                # 중앙 포인트가 없으면 원본 눈동자에서 계산
                if left_center is None or right_center is None:
                    if original_iris_landmarks is not None:
                        try:
                            from utils.face_morphing.region_extraction import get_iris_indices
                            left_iris_indices, right_iris_indices = get_iris_indices()
                            # 왼쪽 눈동자 포인트 (contour만, 처음 4개 가정)
                            left_points = original_iris_landmarks[:4] if len(original_iris_landmarks) >= 4 else original_iris_landmarks[:len(original_iris_landmarks)//2]
                            # 오른쪽 눈동자 포인트 (나머지)
                            right_points = original_iris_landmarks[4:] if len(original_iris_landmarks) > 4 else original_iris_landmarks[len(original_iris_landmarks)//2:]
                            
                            if left_points:
                                left_center = (
                                    sum(p[0] for p in left_points) / len(left_points),
                                    sum(p[1] for p in left_points) / len(left_points)
                                )
                            if right_points:
                                right_center = (
                                    sum(p[0] for p in right_points) / len(right_points),
                                    sum(p[1] for p in right_points) / len(right_points)
                                )
                        except Exception as e:
                            print(f"[얼굴편집] 중앙 포인트 계산 실패: {e}")
                
                # 중앙 포인트 추가 (morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저, MediaPipe RIGHT_IRIS 나중)
                if left_center is not None and right_center is not None:
                    # MediaPipe LEFT_IRIS 먼저 추가 (len-2), MediaPipe RIGHT_IRIS 나중 추가 (len-1)
                    final_landmarks.append(left_center)   # MediaPipe LEFT_IRIS (사용자 왼쪽)
                    final_landmarks.append(right_center)  # MediaPipe RIGHT_IRIS (사용자 오른쪽)
                    original_face_landmarks_tuple.append(left_center)  # 원본도 동일하게 추가
                    original_face_landmarks_tuple.append(right_center)
                    
                    print(f"[얼굴편집] Tesselation: 468개 얼굴 + 중앙 포인트 2개 추가 -> 최종 {len(final_landmarks)}개")
                    
                    # custom_landmarks는 468개 + 중앙 포인트 2개 = 470개 구조로 저장
                    final_landmarks_for_custom = final_landmarks  # 470개
                    original_landmarks_for_morph = original_face_landmarks_tuple  # 470개
                    
                    # LandmarkManager에 중앙 포인트 저장
                    self.landmark_manager.set_custom_iris_centers([left_center, right_center])
                else:
                    print(f"[얼굴편집] 경고: Tesselation 선택 시 중앙 포인트 계산 실패")
                    final_landmarks_for_custom = final_landmarks  # 468개
                    original_landmarks_for_morph = original_face_landmarks_tuple  # 468개
            else:
                # Tesselation이 아닌 경우: 원래 구조 유지 (468개)
                final_landmarks_for_custom = final_landmarks  # 468개
                original_landmarks_for_morph = original_face_landmarks_tuple  # 468개
            
            # custom_landmarks가 이미 470개인 경우 (눈동자 중심점 드래그로 생성된 경우)
            # 중앙 포인트 변환 후 마지막 2개 포인트 업데이트
            existing_custom = self.landmark_manager.get_custom_landmarks()
            if existing_custom is not None and len(existing_custom) == 470:
                # 중앙 포인트 좌표 가져오기 (변환된 좌표)
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                
                if left_center is not None and right_center is not None:
                    # final_landmarks에 중앙 포인트 추가 (470개 구조로 변환)
                    final_landmarks_for_custom = list(final_landmarks)
                    final_landmarks_for_custom.append(left_center)   # MediaPipe LEFT_IRIS (사용자 왼쪽, len-2)
                    final_landmarks_for_custom.append(right_center)  # MediaPipe RIGHT_IRIS (사용자 오른쪽, len-1)
                    print_info("얼굴편집", f"기존 custom_landmarks(470개)에 중앙 포인트 업데이트: 왼쪽={left_center}, 오른쪽={right_center}")
            
            # custom_landmarks 업데이트 (LandmarkManager 사용)
            self.landmark_manager.set_custom_landmarks(final_landmarks_for_custom, reason="_apply_common_sliders_to_landmarks")
            
            # 랜드마크 변형을 이미지에 적용
            import utils.face_morphing as face_morphing
            # 중앙 포인트 좌표 가져오기 (드래그로 변환된 좌표)
            left_center = self.landmark_manager.get_left_iris_center_coord()
            right_center = self.landmark_manager.get_right_iris_center_coord()
            
            # morph_face_by_polygons 호출 시: Tesselation 선택 시에는 이미 눈동자 제거 + 중앙 포인트 추가된 구조 전달
            # LandmarkManager의 get_landmarks_for_tesselation() 사용 (원본, 변형 모두 470개 구조)
            if 'tesselation' in selected_regions and len(selected_regions) == 1:
                original_for_morph, transformed_for_morph = self.landmark_manager.get_copied_landmarks_for_tesselation_with_centers()
                if original_for_morph is None:
                    original_for_morph = original_landmarks_for_morph
                if transformed_for_morph is None:
                    transformed_for_morph = final_landmarks_for_custom
            else:
                # Tesselation이 아닌 경우: 468개 구조
                original_for_morph = original_face_landmarks_tuple
                transformed_for_morph = final_landmarks_for_custom
            
            result = face_morphing.morph_face_by_polygons(
                self.current_image,  # 원본 이미지
                original_for_morph,  # 원본 랜드마크 (Tesselation 선택 시 470개, 그 외 468개)
                transformed_for_morph,  # 변형된 랜드마크 (Tesselation 선택 시 470개, 그 외 468개)
                selected_point_indices=None,  # 모든 포인트 사용 (변형되지 않은 포인트는 원본 위치 유지)
                left_iris_center_coord=left_center,  # 드래그로 변환된 왼쪽 중앙 포인트
                right_iris_center_coord=right_center  # 드래그로 변환된 오른쪽 중앙 포인트
            )
            
            if result is None:
                print_warning("얼굴편집", "랜드마크 변형 결과가 None입니다")
                return image
            
            # 편집된 이미지 업데이트
            self.edited_image = result
            self.face_landmarks = updated_landmarks  # 현재 편집된 랜드마크 저장
            
            # 원본 이미지의 폴리곤 다시 그리기
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # 기존 폴리곤 제거
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
                            iris_centers=iris_centers_for_drawing  # 2개 또는 None
                        )
            
            # 이미지 변형 결과 반환
            return result
            
        except Exception as e:
            print(f"[얼굴편집] 랜드마크 조절 실패: {e}")
            import traceback
            traceback.print_exc()
            return image
    
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
        
        # LandmarkManager를 사용하여 초기화
        self.landmark_manager.reset(keep_original=True)
        # property가 자동으로 처리하므로 동기화 코드 불필요
        self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
        self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
        
        # Tesselation 모드일 때 _custom_iris_centers 복원
        is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
        if is_tesselation_selected and hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
            if self.current_image is not None:
                img_width, img_height = self.current_image.size
                original_landmarks = self.landmark_manager.get_original_landmarks()
                if original_landmarks is not None:
                    left_iris_indices, right_iris_indices = self._get_iris_indices()
                    left_center = self._calculate_iris_center(original_landmarks, left_iris_indices, img_width, img_height)
                    right_center = self._calculate_iris_center(original_landmarks, right_iris_indices, img_width, img_height)
                    if left_center is not None and right_center is not None:
                        self.landmark_manager.set_custom_iris_centers([left_center, right_center])
                        self._left_iris_center_coord = left_center
                        self._right_iris_center_coord = right_center
        
        custom_count = len(self.custom_landmarks) if self.custom_landmarks else 0
        print(f"[얼굴편집] reset_morphing: custom_landmarks를 original_landmarks로 복원 (길이: {custom_count})")
        
        # UI 업데이트 (개별 적용 모드 변경)
        self.on_individual_region_change()
        
        # 라벨 업데이트만 수행 (이미지 업데이트는 apply_editing에서 처리)
        self.update_labels_only()
        
        # 편집 적용 (on_morphing_change는 내부에서 apply_editing을 호출할 수 있으므로 중복 방지)
        if self.current_image is not None:
            self.apply_editing()
    
    def apply_editing(self):
        """편집 적용"""
        print(f"[얼굴편집] apply_editing 호출")
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
                print(f"[얼굴편집] 공통 슬라이더가 모두 기본값이므로 원본 이미지로 복원")
                result = base_image
            else:
                # base_image를 전달하여 슬라이더가 모두 기본값일 때 원본으로 복원할 수 있도록 함
                result = self._apply_common_sliders(result, base_image=base_image)
            
            self.edited_image = result
            
            # 5. 변형된 랜드마크 계산 및 업데이트 (폴리곤 표시를 위해)
            self._update_landmarks_after_editing()
            
        except Exception as e:
            print(f"[얼굴편집] 편집 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self.show_edited_preview()
