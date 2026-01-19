"""
편집 단계별 처리 메서드
apply_editing의 각 단계를 분리한 메서드들
"""
import os
from PIL import Image

import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform
import utils.face_landmarks as face_landmarks


class EditingStepsMixin:
    """편집 단계별 처리 기능 Mixin"""
    
    def _prepare_editing_parameters(self, base_image):
        """파라미터 준비 및 얼굴 특징 보정 적용"""
        # 1. 얼굴 특징 보정 적용
        # 눈 편집 파라미터 결정 (항상 왼쪽/오른쪽 눈 크기 사용)
        if self.use_individual_eye_region.get():
            # 개별 적용 모드: 각각 독립적으로 조정
            left_eye_size = self.left_eye_size.get()
            right_eye_size = self.right_eye_size.get()
        else:
            # 동기화 모드: 왼쪽 눈 크기를 기준으로 오른쪽도 동일하게 (이미 슬라이더에서 동기화됨)
            left_eye_size = self.left_eye_size.get()
            right_eye_size = self.left_eye_size.get()  # 동기화되어 있지만 명시적으로 설정

        # 눈 영역 파라미터 결정 (개별 적용 여부에 따라)
        if self.use_individual_eye_region.get():
            # 개별 적용 모드: 개별 파라미터 전달
            left_eye_region_padding = self.left_eye_region_padding.get()
            right_eye_region_padding = self.right_eye_region_padding.get()
            left_eye_region_offset_x = self.left_eye_region_offset_x.get()
            left_eye_region_offset_y = self.left_eye_region_offset_y.get()
            right_eye_region_offset_x = self.right_eye_region_offset_x.get()
            right_eye_region_offset_y = self.right_eye_region_offset_y.get()
            # 기본 파라미터는 None으로 설정 (개별 파라미터 사용)
            eye_region_padding = None
            eye_region_offset_x = None
            eye_region_offset_y = None
        else:
            # 동기화 모드: 기본 파라미터만 사용 (왼쪽 눈 영역 값을 기준)
            eye_region_padding = self.left_eye_region_padding.get()
            eye_region_offset_x = self.left_eye_region_offset_x.get()
            eye_region_offset_y = self.left_eye_region_offset_y.get()
            # 개별 파라미터는 None으로 설정 (기본 파라미터 사용)
            left_eye_region_padding = None
            right_eye_region_padding = None
            left_eye_region_offset_x = None
            left_eye_region_offset_y = None
            right_eye_region_offset_x = None
            right_eye_region_offset_y = None

        # 입 편집 파라미터 전달 (3가지: 윗입술 모양, 아랫입술 모양, 입 벌림 정도)
        # 폴리곤 기반 변형이 이미 적용되지 않은 경우에만 apply_all_adjustments 사용
        result = face_morphing.apply_all_adjustments(
            base_image,
            eye_size=None,  # 항상 left_eye_size, right_eye_size 사용
            left_eye_size=left_eye_size,
            right_eye_size=right_eye_size,
            eye_spacing=self.eye_spacing.get(),  # Boolean: 눈 간격 조정 활성화 여부
            left_eye_position_y=self.left_eye_position_y.get(),
            right_eye_position_y=self.right_eye_position_y.get(),
            left_eye_position_x=self.left_eye_position_x.get(),
            right_eye_position_x=self.right_eye_position_x.get(),
            eye_region_padding=eye_region_padding,
            eye_region_offset_x=eye_region_offset_x,
            eye_region_offset_y=eye_region_offset_y,
            left_eye_region_padding=left_eye_region_padding,
            right_eye_region_padding=right_eye_region_padding,
            left_eye_region_offset_x=left_eye_region_offset_x,
            left_eye_region_offset_y=left_eye_region_offset_y,
            right_eye_region_offset_x=right_eye_region_offset_x,
            right_eye_region_offset_y=right_eye_region_offset_y,
            nose_size=self.nose_size.get(),
            upper_lip_shape=self.upper_lip_shape.get(),
            lower_lip_shape=self.lower_lip_shape.get(),
            upper_lip_width=self.upper_lip_width.get(),
            lower_lip_width=self.lower_lip_width.get(),
            upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
            lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
            use_individual_lip_region=self.use_individual_lip_region.get(),
            upper_lip_region_padding_x=self.upper_lip_region_padding_x.get(),
            upper_lip_region_padding_y=self.upper_lip_region_padding_y.get(),
            lower_lip_region_padding_x=self.lower_lip_region_padding_x.get(),
            lower_lip_region_padding_y=self.lower_lip_region_padding_y.get(),
            upper_lip_region_offset_x=self.upper_lip_region_offset_x.get(),
            upper_lip_region_offset_y=self.upper_lip_region_offset_y.get(),
            lower_lip_region_offset_x=self.lower_lip_region_offset_x.get(),
            lower_lip_region_offset_y=self.lower_lip_region_offset_y.get(),
            use_landmark_warping=self.use_landmark_warping.get(),
            jaw_adjustment=self.jaw_size.get(),
            face_width=self.face_width.get(),
            face_height=self.face_height.get()
        )
        
        return result


    def _apply_style_transfer_step(self, image):
        """스타일 전송 적용"""
        # 2. 스타일 전송 적용
        if self.style_image_path and os.path.exists(self.style_image_path):
            try:
                style_image = Image.open(self.style_image_path)
                color_strength = self.color_strength.get()
                texture_strength = self.texture_strength.get()

                if color_strength > 0.0 or texture_strength > 0.0:
                    image = style_transfer.transfer_style(
                        style_image,
                        image,
                        color_strength=color_strength,
                        texture_strength=texture_strength
                    )
            except Exception as e:
                print(f"[얼굴편집] 스타일 전송 실패: {e}")
        
        return image


    def _apply_age_transform_step(self, image):
        """나이 변환 적용"""
        # 3. 나이 변환 적용
        age_adjustment = self.age_adjustment.get()
        if abs(age_adjustment) >= 1.0:
            image = face_transform.transform_age(image, age_adjustment=int(age_adjustment))
        
        return image


    def _update_landmarks_after_editing(self):
        """변형된 랜드마크 계산 및 업데이트"""
        # 변형된 랜드마크 계산 및 업데이트 (폴리곤 표시를 위해)
        import utils.face_landmarks as face_landmarks
        import utils.face_morphing as face_morphing

        # 원본 랜드마크 가져오기 (LandmarkManager 사용)
        if not self.landmark_manager.has_original_landmarks():
            if self.current_image is not None:
                original, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if original is not None:
                    self.landmark_manager.set_original_landmarks(original)
                    self.original_landmarks = self.landmark_manager.get_original_landmarks()

        # face_landmarks가 없으면 원본 랜드마크 사용
        if self.landmark_manager.get_face_landmarks() is None:
            original = self.landmark_manager.get_original_landmarks()
            if original is not None:
                self.landmark_manager.set_face_landmarks(original)
                self.face_landmarks = self.landmark_manager.get_face_landmarks()
        else:
            self.face_landmarks = self.landmark_manager.get_face_landmarks()

        original = self.landmark_manager.get_original_landmarks()
        face = self.landmark_manager.get_face_landmarks()

        if face is not None and original is not None:
            # 눈 크기 조정으로 변형된 랜드마크 계산
            if self.use_individual_eye_region.get():
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.right_eye_size.get()
            else:
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.left_eye_size.get()

            # 사이즈 변경 기준 랜드마크 결정: 항상 원본을 기준으로 변환
            # 드래그된 포인트는 원본 위치에서 변환하고, 드래그 표시는 유지
            # 드래그된 포인트 인덱스 가져오기
            dragged_indices = self.landmark_manager.get_dragged_indices()
            # 원본을 기준으로 변환 (드래그된 포인트도 원본 위치에서 변환)
            base_landmarks = original
            
            # 눈 크기 변형 적용 (불필요한 복사본 생성 제거: 함수 내부에서 복사본 생성)
            if left_eye_size is not None or right_eye_size is not None:
                left_ratio = left_eye_size if left_eye_size is not None else 1.0
                right_ratio = right_eye_size if right_eye_size is not None else 1.0
                has_size_change = (abs(left_ratio - 1.0) >= 0.01 or abs(right_ratio - 1.0) >= 0.01)
                
                if has_size_change:
                    print(f"[얼굴편집] apply_editing - 눈 크기 변형 적용: 왼쪽={left_ratio}, 오른쪽={right_ratio}, 드래그된 포인트 {len(dragged_indices)}개")
                    # transform_points_for_eye_size는 내부에서 복사본을 생성하므로 직접 참조 전달 (불필요한 복사본 생성 제거)
                    # 원본을 기준으로 변환 (드래그된 포인트도 원본 위치에서 변환)
                    transformed_landmarks = face_morphing.transform_points_for_eye_size(
                        base_landmarks,
                        eye_size_ratio=1.0,
                        left_eye_size_ratio=left_eye_size,
                        right_eye_size_ratio=right_eye_size
                    )
                else:
                    print(f"[얼굴편집] apply_editing - 눈 크기 변형 없음 (기본값)")
                    transformed_landmarks = base_landmarks
                    has_size_change = False
            else:
                transformed_landmarks = base_landmarks
                has_size_change = False

            # 변형된 랜드마크 저장 (폴리곤 표시용)
            self.face_landmarks = transformed_landmarks

            # 이전 transformed_landmarks 가져오기 (드래그 오프셋 계산용, 업데이트 전에 가져와야 함!)
            # custom_landmarks는 이전 사이즈 변환 + 드래그가 적용된 상태이므로,
            # 드래그 오프셋을 계산하려면 이전 사이즈 변환 상태를 알아야 함
            prev_transformed = self.landmark_manager.get_transformed_landmarks()

            # LandmarkManager를 사용하여 랜드마크 상태 관리
            self.landmark_manager.set_transformed_landmarks(transformed_landmarks)

            # custom_landmarks 업데이트
            if has_size_change:
                # 사이즈 변경이 있으면 transformed_landmarks를 기준으로 설정
                # 드래그된 포인트는 custom_landmarks에서 가져와서 변환된 위치에 적용
                custom = self.landmark_manager.get_custom_landmarks()
                if custom is None or not dragged_indices:
                    # custom_landmarks가 없거나 드래그된 포인트가 없으면 전체를 변환된 랜드마크로 설정
                    # transformed_landmarks는 이미 복사본이므로 직접 참조로 저장 가능
                    self.landmark_manager.set_custom_landmarks(transformed_landmarks, reason="apply_editing_size_change")
                else:
                    # 드래그된 포인트가 있으면: transformed_landmarks를 복사하고 드래그된 포인트는 custom_landmarks에서 가져와서 변환 적용
                    new_custom = list(transformed_landmarks)
                    
                    # 이전 transformed_landmarks가 없으면 (드래그 시작 시 원본에서 시작한 경우)
                    # custom[idx]는 원본 + 드래그 상태이므로, base_landmarks를 기준으로 오프셋 계산
                    if prev_transformed is None or len(prev_transformed) != len(custom):
                        # 이전 사이즈 변환이 없었던 경우: 드래그 오프셋 = custom[idx] - base_landmarks[idx]
                        print(f"[얼굴편집] 드래그 오프셋 계산: 이전 사이즈 변환 없음, 원본 기준")
                        for idx in dragged_indices:
                            if idx < len(custom) and idx < len(new_custom) and idx < len(base_landmarks):
                                orig_x, orig_y = base_landmarks[idx]
                                dragged_x, dragged_y = custom[idx]
                                transformed_x, transformed_y = transformed_landmarks[idx]
                                # 드래그 오프셋 (원본 기준)
                                offset_x = dragged_x - orig_x
                                offset_y = dragged_y - orig_y
                                # 새로운 사이즈 변환된 위치에 드래그 오프셋 적용
                                new_custom[idx] = (transformed_x + offset_x, transformed_y + offset_y)
                                if idx < 5:  # 처음 5개만 디버깅 출력
                                    print(f"  [idx={idx}] 원본=({orig_x:.1f},{orig_y:.1f}), 드래그=({dragged_x:.1f},{dragged_y:.1f}), 변환=({transformed_x:.1f},{transformed_y:.1f}), 오프셋=({offset_x:.1f},{offset_y:.1f}), 최종=({transformed_x + offset_x:.1f},{transformed_y + offset_y:.1f})")
                    else:
                        # 이전 사이즈 변환이 있었던 경우: 드래그 오프셋 = custom[idx] - prev_transformed[idx]
                        # (순수 드래그 오프셋만 계산)
                        print(f"[얼굴편집] 드래그 오프셋 계산: 이전 사이즈 변환 있음, 이전 변환 기준")
                        for idx in dragged_indices:
                            if idx < len(custom) and idx < len(new_custom) and idx < len(prev_transformed):
                                # 이전 사이즈 변환된 위치
                                prev_transformed_x, prev_transformed_y = prev_transformed[idx]
                                # 드래그된 위치 (이전 사이즈 변환 + 드래그)
                                dragged_x, dragged_y = custom[idx]
                                # 새로운 사이즈 변환된 위치
                                transformed_x, transformed_y = transformed_landmarks[idx]
                                
                                # 순수 드래그 오프셋 (이전 사이즈 변환 기준)
                                drag_offset_x = dragged_x - prev_transformed_x
                                drag_offset_y = dragged_y - prev_transformed_y
                                
                                # 새로운 사이즈 변환된 위치에 드래그 오프셋 적용
                                new_custom[idx] = (transformed_x + drag_offset_x, transformed_y + drag_offset_y)
                                if idx < 5:  # 처음 5개만 디버깅 출력
                                    print(f"  [idx={idx}] 이전변환=({prev_transformed_x:.1f},{prev_transformed_y:.1f}), 드래그=({dragged_x:.1f},{dragged_y:.1f}), 새변환=({transformed_x:.1f},{transformed_y:.1f}), 오프셋=({drag_offset_x:.1f},{drag_offset_y:.1f}), 최종=({transformed_x + drag_offset_x:.1f},{transformed_y + drag_offset_y:.1f})")
                    
                    self.landmark_manager.set_custom_landmarks(new_custom, reason="apply_editing_size_change")
                    # 드래그 표시는 유지 (변환은 했지만 드래그로 변경된 것으로 표시 유지)
                print(f"[얼굴편집] apply_editing - 사이즈 변경 적용, 드래그 표시 유지: {len(self.landmark_manager.get_dragged_indices())}개")
            # 사이즈 변경이 없으면 기존 custom_landmarks 유지 (_apply_common_sliders_to_landmarks에서 변환한 내용)

            # 중앙 포인트 좌표 업데이트
            if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                if self.landmark_manager.has_original_landmarks():
                    img_width, img_height = base_image.size
                    left_iris_indices, right_iris_indices = self._get_iris_indices()

                    if has_size_change:
                        # 사이즈 변경이 있으면 변환된 랜드마크에서 중앙 포인트 재계산
                        print(f"[얼굴편집] apply_editing - 사이즈 변경 감지, 변환된 랜드마크에서 중앙 포인트 재계산")
                        left_center = self._calculate_iris_center(transformed_landmarks, left_iris_indices, img_width, img_height)
                        right_center = self._calculate_iris_center(transformed_landmarks, right_iris_indices, img_width, img_height)
                        self.landmark_manager.set_iris_center_coords(left_center, right_center)
                    else:
                        # 사이즈 변경이 없으면 드래그 좌표가 있으면 유지, 없으면 original_landmarks에서 계산
                        left_center = self.landmark_manager.get_left_iris_center_coord()
                        right_center = self.landmark_manager.get_right_iris_center_coord()

                        if left_center is None:
                            left_center = self._calculate_iris_center(
                                self.landmark_manager.get_original_landmarks(), 
                                left_iris_indices, img_width, img_height)
                        if right_center is None:
                            right_center = self._calculate_iris_center(
                                self.landmark_manager.get_original_landmarks(), 
                                right_iris_indices, img_width, img_height)

                        self.landmark_manager.set_iris_center_coords(left_center, right_center)

            # property가 자동으로 처리하므로 동기화 코드 불필요
            self.transformed_landmarks = self.landmark_manager.get_transformed_landmarks()
            self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
            self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()

            custom_count = len(self.custom_landmarks) if self.custom_landmarks else 0
            print(f"[얼굴편집] apply_editing - custom_landmarks 업데이트 완료: 길이={custom_count}")

            # 폴리곤 기반 변형: 변형된 랜드마크로 이미지 변형
            # apply_all_adjustments 대신 morph_face_by_polygons 사용
            original, transformed = self.landmark_manager.get_landmarks_for_morphing()
            if original is not None and transformed is not None:
                # 중앙 포인트 좌표 가져오기
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                result = face_morphing.morph_face_by_polygons(
                    base_image,  # 원본 이미지
                    original,  # 원본 랜드마크
                    transformed,  # 변형된 랜드마크 (폴리곤으로 수정된 랜드마크)
                    selected_point_indices=None,  # 모든 포인트 처리
                    left_iris_center_coord=left_center,  # 드래그로 변환된 왼쪽 중앙 포인트
                    right_iris_center_coord=right_center  # 드래그로 변환된 오른쪽 중앙 포인트
                )
            else:
                result = None

                if result is not None:
                    # 편집된 이미지 업데이트
                    self.edited_image = result
                    # 나머지 편집(코, 입 등)은 기존 이미지에 적용
                    base_image = result

        # 입 편집 파라미터 전달 (3가지: 윗입술 모양, 아랫입술 모양, 입 벌림 정도)
        # 폴리곤 기반 변형이 이미 적용된 경우에도 코, 입, 턱, 얼굴 크기 등은 apply_all_adjustments로 처리
        # 눈 크기는 이미 morph_face_by_polygons로 처리되었으므로 None으로 설정
        if 'result' not in locals() or result is None:
            result = base_image

        # 코, 입, 턱, 얼굴 크기 등 나머지 편집 적용 (눈 크기는 이미 처리됨)
        result = face_morphing.apply_all_adjustments(
            result,  # 이미 처리된 이미지 (눈 크기 조정 포함)
            eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
            left_eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
            right_eye_size=None,  # 이미 morph_face_by_polygons로 처리됨
            eye_spacing=self.eye_spacing.get(),  # Boolean: 눈 간격 조정 활성화 여부
            left_eye_position_y=self.left_eye_position_y.get(),
            right_eye_position_y=self.right_eye_position_y.get(),
            left_eye_position_x=self.left_eye_position_x.get(),
            right_eye_position_x=self.right_eye_position_x.get(),
            eye_region_padding=eye_region_padding,
            eye_region_offset_x=eye_region_offset_x,
            eye_region_offset_y=eye_region_offset_y,
            left_eye_region_padding=left_eye_region_padding,
            right_eye_region_padding=right_eye_region_padding,
            left_eye_region_offset_x=left_eye_region_offset_x,
            left_eye_region_offset_y=left_eye_region_offset_y,
            right_eye_region_offset_x=right_eye_region_offset_x,
            right_eye_region_offset_y=right_eye_region_offset_y,
            nose_size=self.nose_size.get(),
            upper_lip_shape=self.upper_lip_shape.get(),
            lower_lip_shape=self.lower_lip_shape.get(),
            upper_lip_width=self.upper_lip_width.get(),
            lower_lip_width=self.lower_lip_width.get(),
            upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
            lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
            use_individual_lip_region=self.use_individual_lip_region.get(),
            upper_lip_region_padding_x=self.upper_lip_region_padding_x.get(),
            upper_lip_region_padding_y=self.upper_lip_region_padding_y.get(),
            lower_lip_region_padding_x=self.lower_lip_region_padding_x.get(),
            lower_lip_region_padding_y=self.lower_lip_region_padding_y.get(),
            upper_lip_region_offset_x=self.upper_lip_region_offset_x.get(),
            upper_lip_region_offset_y=self.upper_lip_region_offset_y.get(),
            lower_lip_region_offset_x=self.lower_lip_region_offset_x.get(),
            lower_lip_region_offset_y=self.lower_lip_region_offset_y.get(),
            use_landmark_warping=self.use_landmark_warping.get(),
            jaw_adjustment=self.jaw_size.get(),
            face_width=self.face_width.get(),
            face_height=self.face_height.get()
        )
        # 실패 시 원본 이미지 사용
        self.edited_image = self.current_image.copy()
        self.show_edited_preview()


