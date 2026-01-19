"""
얼굴 편집 패널 - 폴리곤 드래그 처리 Mixin
폴리곤 포인트 드래그 이벤트 처리를 담당
"""
import math

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


class PolygonDragHandlerMixin:
    """폴리곤 드래그 처리 기능 Mixin"""
    
    def on_polygon_drag_start(self, event, landmark_index, canvas_obj):
        """폴리곤에서 포인트를 찾아서 드래그 시작"""
        # 고급 모드가 아니어도 드래그 가능
        # 드래그 종료 시 자동으로 고급 모드로 변형 적용
        
        # 폴리곤에서 포인트를 찾았을 때 바로 드래그 모드로 진입
        self.dragging_polygon = True
        self.dragged_polygon_index = landmark_index
        self.dragged_polygon_canvas = canvas_obj
        
        # 드래그 시작 위치 저장
        self.polygon_drag_start_x = event.x
        self.polygon_drag_start_y = event.y
        
        # 이미지 드래그 시작 플래그 초기화 (이미지 드래그 방지)
        if canvas_obj == self.canvas_original:
            self.canvas_original_drag_start_x = None
            self.canvas_original_drag_start_y = None
        else:
            self.canvas_edited_drag_start_x = None
            self.canvas_edited_drag_start_y = None
        
        # 드래그 시작 로그
        if isinstance(landmark_index, int):
            print(f"[얼굴편집] 드래그 시작: 랜드마크 인덱스 {landmark_index}")
        
        # 현재 랜드마크의 이미지 좌표 계산 - LandmarkManager 사용
        if canvas_obj == self.canvas_original:
            if self.current_image is None:
                return
            img = self.current_image
            # 랜드마크 가져오기 (커스텀 또는 원본) - LandmarkManager 사용
            custom = self.landmark_manager.get_custom_landmarks()
            face = self.landmark_manager.get_face_landmarks()
            if custom is not None:
                landmarks = custom
            elif face is not None:
                landmarks = face
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if landmarks is None:
                    return
                self.landmark_manager.set_face_landmarks(landmarks)
                self.face_landmarks = self.landmark_manager.get_face_landmarks()
                # 원본 랜드마크도 저장
                if not self.landmark_manager.has_original_landmarks():
                    self.landmark_manager.set_original_landmarks(landmarks)
                    self.original_landmarks = self.landmark_manager.get_original_landmarks()
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            if self.edited_image is None:
                return
            img = self.edited_image
            # 편집된 이미지의 랜드마크는 커스텀 랜드마크 사용 - LandmarkManager 사용
            custom = self.landmark_manager.get_custom_landmarks()
            if custom is not None:
                landmarks = custom
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.edited_image)
                if landmarks is None:
                    return
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if landmarks is None or landmark_index >= len(landmarks):
            return
        
        self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = landmarks[landmark_index]
        
        # 커스텀 랜드마크 초기화 (처음 드래그할 때) - LandmarkManager 사용
        # 주의: custom_landmarks가 없을 때만 초기화 (사이즈 변환이 이미 적용된 상태 보존)
        # 사이즈 변경 후 드래그 시 사이즈 변환이 반복 적용되는 문제 방지:
        # - custom_landmarks가 이미 있으면 그대로 사용 (사이즈 변환 포함)
        # - custom_landmarks가 없으면 transformed_landmarks 또는 원본으로 초기화
        custom = self.landmark_manager.get_custom_landmarks()
        if custom is None:
            # custom_landmarks가 없으면 transformed_landmarks 우선 사용 (사이즈 변환 포함)
            transformed = self.landmark_manager.get_transformed_landmarks()
            if transformed is not None:
                # transformed_landmarks는 set_transformed_landmarks로 직접 참조로 저장되므로,
                # custom_landmarks에 직접 참조로 저장하면 같은 리스트를 공유하게 되어 수정 시 transformed_landmarks도 변경됨
                # 따라서 복사본이 필요함 (custom_landmarks는 수정 가능해야 함)
                self.landmark_manager.set_custom_landmarks(list(transformed), reason="on_polygon_drag_start")
                print(f"[얼굴편집] 드래그 시작: transformed_landmarks를 custom_landmarks로 설정 (사이즈 변환 포함, 복사본 생성)")
            else:
                # transformed_landmarks가 없으면 원본 얼굴 랜드마크 사용
                original_face = self.landmark_manager.get_original_face_landmarks()
                if original_face is not None:
                    # 원본을 복사본으로 설정 (변환 적용을 위해)
                    self.landmark_manager.set_custom_landmarks(list(original_face), reason="on_polygon_drag_start")
                    print(f"[얼굴편집] 드래그 시작: 원본 얼굴 랜드마크를 custom_landmarks로 설정")
                elif landmarks is not None:
                    # 원본이 없으면 현재 landmarks 사용
                    self.landmark_manager.set_custom_landmarks(list(landmarks) if landmarks is not None else None, reason="on_polygon_drag_start")
                    print(f"[얼굴편집] 드래그 시작: 현재 landmarks를 custom_landmarks로 설정")
        else:
            # custom_landmarks가 이미 있으면 그대로 사용 (사이즈 변환 포함된 상태 보존)
            print(f"[얼굴편집] 드래그 시작: 기존 custom_landmarks 유지 (길이={len(custom)})")
        
        # 선택된 포인트 표시 (큰 원으로 강조)
        self._draw_selected_landmark_indicator(canvas_obj, landmark_index, event.x, event.y)
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_polygon_drag(self, event, landmark_index, canvas_obj):
        """폴리곤에서 찾은 포인트 드래그 중"""
        # 포인트가 선택되어 있고 드래그 중인 경우에만 처리
        if not self.dragging_polygon or self.dragged_polygon_index != landmark_index:
            return
        
        # 중앙 포인트 드래그의 경우 ('left' 또는 'right' 문자열)
        if isinstance(landmark_index, str):
            # on_iris_center_drag로 위임
            self.on_iris_center_drag(event, landmark_index, canvas_obj)
            return
        
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is None:
            return
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            # display_size가 없으면 이미지 크기 사용
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 좌표를 이미지 좌표로 변환
        # 이미지 중심이 pos_x, pos_y에 있으므로
        rel_x = (event.x - pos_x) / scale_x
        rel_y = (event.y - pos_y) / scale_y
        img_x = img_width / 2 + rel_x
        img_y = img_height / 2 + rel_y
        
        # 이미지 경계 내로 제한
        img_x = max(0, min(img_width - 1, img_x))
        img_y = max(0, min(img_height - 1, img_y))
        
        # 랜드마크 위치 업데이트
        # landmark_index가 정수인지 확인 (중앙 포인트 드래그의 경우 'left'/'right' 문자열일 수 있음)
        if isinstance(landmark_index, int) and landmark_index >= 0:
            # 이전 위치 가져오기 (디버깅용)
            old_pos = None
            custom = self.landmark_manager.get_custom_landmarks()
            if custom is not None and landmark_index < len(custom):
                old_pos = custom[landmark_index]
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(landmark_index, (img_x, img_y))
                self.landmark_manager.mark_as_dragged(landmark_index)
            
            # 디버깅: 인덱스와 위치 변경 확인
            if old_pos is not None and (abs(old_pos[0] - img_x) > 0.1 or abs(old_pos[1] - img_y) > 0.1):
                print(f"[얼굴편집] 랜드마크 인덱스 {landmark_index} 위치 변경: ({old_pos[0]:.1f}, {old_pos[1]:.1f}) -> ({img_x:.1f}, {img_y:.1f})")
            
            # 선택된 포인트 표시 업데이트
            self._update_selected_landmark_indicator(canvas_obj, event.x, event.y)
        elif isinstance(landmark_index, str):
            # 중앙 포인트 드래그의 경우 ('left' 또는 'right') - on_iris_center_drag에서 처리됨
            # 이미 위에서 on_iris_center_drag로 위임했으므로 여기서는 처리하지 않음
            pass
        
        # 성능 최적화: 드래그 중에는 실시간 미리보기 비활성화
        # 드래그 종료 시에만 최종 편집 적용
        # 실시간 미리보기가 필요하면 아래 주석을 해제하고 쓰로틀링 추가
        # use_warping = getattr(self, 'use_landmark_warping', None)
        # if use_warping is not None and hasattr(use_warping, 'get') and use_warping.get():
        #     self.apply_polygon_drag_preview()
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_polygon_drag_end(self, event, landmark_index, canvas_obj):
        """폴리곤에서 찾은 포인트 드래그 종료"""
        if not self.dragging_polygon or self.dragged_polygon_index != landmark_index:
            return
        
        # 드래그 종료 로그
        if isinstance(landmark_index, int):
            dragged_count = len(self.landmark_manager.get_dragged_indices())
            print(f"[얼굴편집] 드래그 종료: 랜드마크 인덱스 {landmark_index}, 드래그된 포인트 {dragged_count}개")
        
        # 드래그 종료 시 항상 변형 적용
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is not None:
            self.apply_polygon_drag_final()
        
        # 마지막으로 선택한 포인트 인덱스 저장 (드래그 종료 후에도 유지)
        # landmark_index는 정수이므로 그대로 저장
        self.last_selected_landmark_index = landmark_index
        
        # 선택된 포인트 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 드래그 종료 시 플래그 초기화 (이미지 드래그 가능하도록)
        # 주의: 드래그 표시(_dragged_indices)는 유지 (슬라이더 변형 시 제외하기 위해)
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.dragged_polygon_canvas = None
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_iris_center_drag_start(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 시작
        iris_side: 'left' 또는 'right' (좌표 기반)
        """
        # 드래그 시작
        self.dragging_polygon = True
        self.dragged_polygon_index = iris_side  # 'left' 또는 'right' 저장
        self.dragged_polygon_canvas = canvas_obj
        
        # 드래그 시작 위치 저장
        self.polygon_drag_start_x = event.x
        self.polygon_drag_start_y = event.y
        
        # 이미지 드래그 시작 플래그 초기화
        if canvas_obj == self.canvas_original:
            self.canvas_original_drag_start_x = None
            self.canvas_original_drag_start_y = None
        else:
            self.canvas_edited_drag_start_x = None
            self.canvas_edited_drag_start_y = None
        
        # 현재 이미지 가져오기
        if canvas_obj == self.canvas_original:
            if self.current_image is None:
                return
            img = self.current_image
        else:
            if self.edited_image is None:
                return
            img = self.edited_image
        
        # 중앙 포인트 좌표 가져오기
        if iris_side == 'left' and hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None:
            self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = self._left_iris_center_coord
        elif iris_side == 'right' and hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None:
            self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = self._right_iris_center_coord
        else:
            # 좌표가 없으면 original_landmarks에서 계산
            original = self.landmark_manager.get_original_landmarks_full()
            
            if original is not None:
                img_width, img_height = img.size
                left_iris_indices, right_iris_indices = self._get_iris_indices()
                if iris_side == 'left':
                    center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                else:
                    center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                if center is not None:
                    self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = center
                else:
                    return
            else:
                return
        
        # 선택된 포인트 표시
        self._draw_selected_landmark_indicator(canvas_obj, None, event.x, event.y)
        
        return "break"
    
    def on_iris_center_drag(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 중
        iris_side: 'left' 또는 'right' (좌표 기반)
        """
        if not self.dragging_polygon or self.dragged_polygon_index != iris_side:
            return
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 좌표를 이미지 좌표로 변환
        rel_x = (event.x - pos_x) / scale_x
        rel_y = (event.y - pos_y) / scale_y
        new_center_x = img_width / 2 + rel_x
        new_center_y = img_height / 2 + rel_y
        
        # 이미지 경계 내로 제한
        new_center_x = max(0, min(img_width - 1, new_center_x))
        new_center_y = max(0, min(img_height - 1, new_center_y))
        
        # 중앙 포인트 좌표 업데이트
        # custom_landmarks의 배열 끝 인덱스도 직접 업데이트 (방법 A)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is not None and len(custom) >= 2:
            # 계산된 중앙 포인트 인덱스: 
            # custom_landmarks에는 눈동자 포인트가 제거되고 중앙 포인트가 추가되어 있음
            # morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저 (len-2), MediaPipe RIGHT_IRIS 나중 (len-1)
            # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
            # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
            # 따라서: len-2 = MediaPipe LEFT_IRIS (사용자 왼쪽), len-1 = MediaPipe RIGHT_IRIS (사용자 오른쪽)
            if iris_side == 'left':
                left_idx = len(custom) - 2  # MediaPipe LEFT_IRIS = 사용자 왼쪽
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(left_idx, (new_center_x, new_center_y))
                self.landmark_manager.set_iris_center_coords(
                    (new_center_x, new_center_y),
                    self.landmark_manager.get_right_iris_center_coord()
                )
            elif iris_side == 'right':
                right_idx = len(custom) - 1  # MediaPipe RIGHT_IRIS = 사용자 오른쪽
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(right_idx, (new_center_x, new_center_y))
                self.landmark_manager.set_iris_center_coords(
                    self.landmark_manager.get_left_iris_center_coord(),
                    (new_center_x, new_center_y)
                )
        else:
            # custom_landmarks가 없거나 길이가 부족한 경우
            # face_landmarks를 가져와서 중앙 포인트를 추가한 custom_landmarks 생성
            face_landmarks_list = self.landmark_manager.get_face_landmarks()
            if face_landmarks_list is not None:
                # face_landmarks에 중앙 포인트 추가 (470개 구조)
                custom = list(face_landmarks_list)
                if iris_side == 'left':
                    left_center = (new_center_x, new_center_y)
                    right_center = self.landmark_manager.get_right_iris_center_coord()
                else:
                    left_center = self.landmark_manager.get_left_iris_center_coord()
                    right_center = (new_center_x, new_center_y)
                
                if left_center is not None and right_center is not None:
                    custom.append(left_center)
                    custom.append(right_center)
                    self.landmark_manager.set_custom_landmarks(custom, reason="on_iris_center_drag_create")
                    self.landmark_manager.set_iris_center_coords(left_center, right_center)
        
        # 선택된 포인트 표시 업데이트
        self._update_selected_landmark_indicator(canvas_obj, event.x, event.y)
        
        return "break"
    
    def on_iris_center_drag_end(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 종료"""
        if not self.dragging_polygon or self.dragged_polygon_index != iris_side:
            return
        
        # 드래그 종료 시 항상 변형 적용
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is not None:
            self.apply_polygon_drag_final()
        
        # 선택된 포인트 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 드래그 종료 시 플래그 초기화
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.dragged_polygon_canvas = None
        
        # 폴리곤 표시가 활성화되어 있으면 폴리곤 다시 그리기
        if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'update_face_features_display'):
                self.update_face_features_display()
        
        return "break"
    
    def apply_polygon_drag_preview(self):
        """폴리곤 드래그 중 실시간 미리보기 (현재 비활성화: 성능 최적화)"""
        # 성능 최적화: 드래그 중에는 실시간 미리보기 비활성화
        # 드래그 종료 시에만 최종 편집 적용
        pass
    
    def apply_polygon_drag_final(self):
        """폴리곤 드래그 종료 시 최종 편집 적용"""
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is None or self.current_image is None:
            return
        
        try:
            # 원본 랜드마크 가져오기 (LandmarkManager 사용)
            if not self.landmark_manager.has_original_landmarks():
                original_landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if original_landmarks is None:
                    print("[얼굴편집] 원본 랜드마크 감지 실패")
                    return
                self.landmark_manager.set_original_landmarks(original_landmarks)
                self.original_landmarks = self.landmark_manager.get_original_landmarks()
            else:
                original_landmarks = self.landmark_manager.get_original_landmarks()
            
            # 슬라이더로 변형된 랜드마크가 있으면 그것을 기준으로 사용
            # custom_landmarks는 슬라이더 변형 + 드래그 변형이 모두 적용된 상태
            # 이미지 변형 시에는 원본 랜드마크를 기준으로 custom_landmarks를 사용
            
            print(f"[얼굴편집] 랜드마크 변형 적용: 원본 {len(original_landmarks)}개, 변형 {len(self.custom_landmarks)}개")
            
            # 디버깅: 변형된 랜드마크 확인
            changed_indices = []
            for i in range(min(len(original_landmarks), len(self.custom_landmarks))):
                orig = original_landmarks[i]
                custom = self.custom_landmarks[i]
                diff = ((custom[0] - orig[0])**2 + (custom[1] - orig[1])**2)**0.5
                if diff > 0.1:
                    changed_indices.append((i, diff))
            if changed_indices:
                print(f"[얼굴편집] 변형된 랜드마크 인덱스: {[idx for idx, _ in changed_indices[:10]]} (총 {len(changed_indices)}개)")
            else:
                print(f"[얼굴편집] 경고: 변형된 랜드마크가 없습니다!")
            
            # 마지막으로 선택한 포인트 인덱스 확인
            if hasattr(self, 'last_selected_landmark_index') and self.last_selected_landmark_index is not None:
                last_idx = self.last_selected_landmark_index
                # 중앙 포인트 드래그의 경우 'left'/'right' 문자열이므로 정수 체크 필요
                if isinstance(last_idx, int) and last_idx >= 0:
                    # custom_landmarks 가져오기 (LandmarkManager 사용)
                    custom = self.landmark_manager.get_custom_landmarks()
                    
                    if custom is not None and last_idx < len(original_landmarks) and last_idx < len(custom):
                        orig_pos = original_landmarks[last_idx]
                        custom_pos = custom[last_idx]
                        diff = ((custom_pos[0] - orig_pos[0])**2 + (custom_pos[1] - orig_pos[1])**2)**0.5
                        print(f"[얼굴편집] 마지막 선택 포인트 인덱스 {last_idx}: 원본=({orig_pos[0]:.1f}, {orig_pos[1]:.1f}), 변형=({custom_pos[0]:.1f}, {custom_pos[1]:.1f}), 거리={diff:.1f}픽셀")
                elif isinstance(last_idx, str):
                    # 중앙 포인트 드래그의 경우 ('left' 또는 'right')
                    print(f"[얼굴편집] 마지막 선택 포인트: 중앙 포인트 ({last_idx})")
            
            # 공통 슬라이더 적용 (morph_face_by_polygons 호출 전에 custom_landmarks 변환)
            # _apply_common_sliders_to_landmarks가 custom_landmarks를 변환하므로 먼저 호출
            if hasattr(self, '_apply_common_sliders'):
                # _apply_common_sliders는 _apply_common_sliders_to_landmarks를 호출하여 custom_landmarks를 변환
                # base_image를 전달하여 슬라이더가 모두 기본값일 때 원본으로 복원할 수 있도록 함
                base_image = self.aligned_image if hasattr(self, 'aligned_image') and self.aligned_image is not None else self.current_image
                temp_result = self._apply_common_sliders(self.current_image, base_image=base_image)
                if temp_result is not None:
                    # custom_landmarks가 변환되었으므로 다시 확인
                    changed_indices_after = []
                    # custom_landmarks 가져오기 (LandmarkManager 사용)
                    custom = self.landmark_manager.get_custom_landmarks()
                    
                    if custom is not None:
                        for i in range(min(len(original_landmarks), len(custom))):
                            orig = original_landmarks[i]
                            custom_point = custom[i]
                            diff = ((custom_point[0] - orig[0])**2 + (custom_point[1] - orig[1])**2)**0.5
                            if diff > 0.1:
                                changed_indices_after.append((i, diff))
                    if changed_indices_after:
                        print(f"[얼굴편집] 공통 슬라이더 적용 후 변형된 랜드마크: {len(changed_indices_after)}개")
            
            # 슬라이더가 모두 기본값이고 랜드마크가 변형되지 않았는지 확인
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
            
            # custom_landmarks 가져오기 (랜드마크 변형 확인용)
            custom_for_check = self.landmark_manager.get_custom_landmarks()
            
            # 랜드마크가 변형되었는지 확인
            landmarks_changed = False
            if custom_for_check is not None and len(original_landmarks) == len(custom_for_check):
                for i in range(len(original_landmarks)):
                    orig = original_landmarks[i]
                    custom_point = custom_for_check[i]
                    diff = ((custom_point[0] - orig[0])**2 + (custom_point[1] - orig[1])**2)**0.5
                    if diff > 0.1:
                        landmarks_changed = True
                        break
            
            # result 초기화
            result = None
            
            # 슬라이더가 모두 기본값이고 랜드마크도 변형되지 않았으면 원본 이미지 반환
            if not conditions_met:
                # 랜드마크가 변형되지 않았을 때만 custom_landmarks를 원본으로 복원
                # (드래그로 변경한 랜드마크는 보존해야 함)
                if not landmarks_changed:
                    # 슬라이더가 모두 기본값이고 랜드마크도 변형되지 않았으면 custom_landmarks를 원본으로 복원
                    original_face = self.landmark_manager.get_original_face_landmarks()
                    if original_face is not None:
                        self.landmark_manager.set_custom_landmarks(original_face, reason="슬라이더 초기화")
                    
                    print(f"[얼굴편집] 슬라이더와 랜드마크가 모두 기본값이므로 원본 이미지로 복원")
                    result = base_image
                else:
                    # 랜드마크는 변형되었지만 슬라이더는 기본값이므로 morph_face_by_polygons 호출
                    # custom_landmarks는 드래그로 변경된 상태를 유지해야 하므로 복원하지 않음
                    print(f"[얼굴편집] 슬라이더는 기본값이지만 랜드마크가 변형되어 있으므로 morph_face_by_polygons 호출")
                    result = None  # 아래에서 morph_face_by_polygons 호출
            
            # result가 None이면 morph_face_by_polygons 호출
            if result is None:
                # 랜드마크 변형 적용 (원본 이미지와 원본 랜드마크를 기준으로)
                # 고급 모드 여부와 관계없이 Delaunay Triangulation 사용
                # 마지막으로 선택한 포인트 인덱스 전달 (인덱스 기반 직접 매핑을 위해)
                last_selected_index = getattr(self, 'last_selected_landmark_index', None)
                # 중앙 포인트 좌표 가져오기 (드래그로 변환된 좌표)
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                
                result = face_morphing.morph_face_by_polygons(
                    self.current_image,  # 원본 이미지
                    original_landmarks,  # 원본 랜드마크
                    self.custom_landmarks,  # 변형된 랜드마크 (공통 슬라이더 변환 포함)
                    selected_point_indices=[last_selected_index] if last_selected_index is not None else None,  # 선택한 포인트 인덱스
                    left_iris_center_coord=left_center,  # 드래그로 변환된 왼쪽 중앙 포인트
                    right_iris_center_coord=right_center  # 드래그로 변환된 오른쪽 중앙 포인트
                )
            
            if result is None:
                print("[얼굴편집] 랜드마크 변형 결과가 None입니다")
                return
            
            # 편집된 이미지 업데이트
            self.edited_image = result
            self.face_landmarks = self.custom_landmarks  # 현재 편집된 랜드마크 저장 (표시용)
            
            # UI 업데이트 최적화: 이미지가 변경되었을 때만 업데이트
            try:
                import hashlib
                current_hash = hashlib.md5(result.tobytes()).hexdigest()
                if current_hash != getattr(self, '_last_edited_image_hash', None):
                    self.show_edited_preview()
                    self._last_edited_image_hash = current_hash
            except Exception as e:
                # 해시 계산 실패 시 안전하게 항상 업데이트
                self.show_edited_preview()
            
            # 랜드마크 표시 업데이트 (이미 조건부 호출됨)
            if self.show_landmark_points.get():
                self.update_face_features_display()
            
            print("[얼굴편집] 랜드마크 드래그 최종 적용 완료")
            
        except Exception as e:
            print(f"[얼굴편집] 랜드마크 드래그 최종 적용 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_nearest_landmark_for_drag(self, event, landmarks, current_tab, canvas_obj):
        """캔버스 레벨에서 가장 가까운 랜드마크 포인트 찾기 (화면에 보이는 모든 포인트 중에서)"""
        if landmarks is None or len(landmarks) == 0:
            return None
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return None
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 크기 가져오기 (화면 범위 확인용)
        canvas_width = canvas_obj.winfo_width()
        canvas_height = canvas_obj.winfo_height()
        
        # 이미지 영역 계산 (이미지가 화면에 보이는 범위)
        image_left = pos_x - display_width / 2
        image_right = pos_x + display_width / 2
        image_top = pos_y - display_height / 2
        image_bottom = pos_y + display_height / 2
        
        # 클릭 위치가 이미지 영역 밖에 있으면 포인트를 찾지 않음
        click_threshold = 15  # 캔버스 좌표계 기준 선택 범위 (픽셀)
        margin = click_threshold
        if (event.x < image_left - margin or event.x > image_right + margin or
            event.y < image_top - margin or event.y > image_bottom + margin):
            # 이미지 영역 밖을 클릭했으면 포인트를 찾지 않음
            return None
        
        # 화면에 보이는 포인트 확인
        # 1. 랜드마크 체크박스가 체크되어 있으면 polygon_point_map에 있는 포인트
        # 2. 폴리곤만 체크되어 있으면 현재 탭에 해당하는 포인트들 (폴리곤에 포함된 포인트)
        # 캔버스 타입 결정
        canvas_type = 'original' if canvas_obj == self.canvas_original else 'edited'
        visible_point_set = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
        polygon_items = self.landmark_polygon_items[canvas_type]
        
        # 폴리곤에 포함된 포인트만 확인 (polygon_point_map 사용)
        # 확장 레벨로 추가된 포인트도 포함됨
        if len(polygon_items) > 0:
            # 폴리곤이 그려져 있으면 polygon_point_map에 있는 포인트만 확인
            # 이렇게 하면 확장 레벨로 추가된 포인트도 포함됨
            visible_indices = list(visible_point_set)
        else:
            # 폴리곤이 그려져 있지 않으면 빈 리스트
            visible_indices = []
        
        # 중앙 포인트를 먼저 체크 (눈동자 포인트보다 우선)
        # 눈동자 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 찾지 않음
        center_radius = 10  # 중앙 포인트 클릭 범위 (캔버스 좌표계 기준, 픽셀)
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
            RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            
            # 왼쪽 눈동자 중앙 포인트 체크
            left_iris_indices_set = set()
            for idx1, idx2 in LEFT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    left_iris_indices_set.add(idx1)
                    left_iris_indices_set.add(idx2)
            if 468 < len(landmarks):
                left_iris_indices_set.add(468)
            
            if left_iris_indices_set:
                left_iris_coords = []
                for idx in left_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        left_iris_coords.append((img_x, img_y))
                
                if left_iris_coords:
                    center_x = sum(c[0] for c in left_iris_coords) / len(left_iris_coords)
                    center_y = sum(c[1] for c in left_iris_coords) / len(left_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        # 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 제외
                        visible_indices = [idx for idx in visible_indices if idx not in left_iris_indices_set]
            
            # 오른쪽 눈동자 중앙 포인트 체크
            right_iris_indices_set = set()
            for idx1, idx2 in RIGHT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    right_iris_indices_set.add(idx1)
                    right_iris_indices_set.add(idx2)
            if 473 < len(landmarks):
                right_iris_indices_set.add(473)
            
            if right_iris_indices_set:
                right_iris_coords = []
                for idx in right_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        right_iris_coords.append((img_x, img_y))
                
                if right_iris_coords:
                    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
                    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        # 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 제외
                        visible_indices = [idx for idx in visible_indices if idx not in right_iris_indices_set]
        except (ImportError, AttributeError):
            # MediaPipe가 없거나 FACEMESH_LEFT_IRIS/FACEMESH_RIGHT_IRIS가 없으면 스킵
            pass
        
        min_distance = float('inf')
        nearest_idx = None
        
        for idx in visible_indices:
            if idx >= len(landmarks):
                continue
            landmark = landmarks[idx]
            if landmark is None:
                continue
            
            # 랜드마크 좌표 (이미지 좌표계)
            if isinstance(landmark, tuple):
                lm_img_x, lm_img_y = landmark
            else:
                lm_img_x = landmark.x * img_width
                lm_img_y = landmark.y * img_height
            
            # 랜드마크를 캔버스 좌표로 변환
            rel_lm_x = (lm_img_x - img_width / 2) * scale_x
            rel_lm_y = (lm_img_y - img_height / 2) * scale_y
            lm_canvas_x = pos_x + rel_lm_x
            lm_canvas_y = pos_y + rel_lm_y
            
            # 포인트가 이미지 영역 내에 있는지 확인 (이미지 영역 밖의 포인트는 선택 불가)
            if (lm_canvas_x < image_left or lm_canvas_x > image_right or
                lm_canvas_y < image_top or lm_canvas_y > image_bottom):
                # 이미지 영역 밖에 있는 포인트는 건너뛰기
                continue
            
            # 화면에 보이는 포인트만 확인 (캔버스 범위 내에 있는지 체크)
            # 마진을 두어 약간 벗어난 포인트도 선택 가능하도록 함
            margin = click_threshold
            if (lm_canvas_x < -margin or lm_canvas_x > canvas_width + margin or
                lm_canvas_y < -margin or lm_canvas_y > canvas_height + margin):
                # 화면 범위 밖에 있는 포인트는 건너뛰기
                continue
            
            # 캔버스 좌표계 기준으로 거리 계산 (화면에서 보이는 거리)
            distance = math.sqrt((event.x - lm_canvas_x)**2 + (event.y - lm_canvas_y)**2)
            
            # 최소 거리 업데이트 (캔버스 좌표계 기준 15픽셀 이내만 선택)
            # 이미 드래그 중인 포인트를 우선하지 않고, 항상 가장 가까운 포인트를 선택
            if distance < min_distance and distance < click_threshold:
                min_distance = distance
                nearest_idx = idx
        
        return nearest_idx
    
    def _check_iris_center_click(self, event, landmarks, canvas_obj):
        """중앙 포인트가 클릭 범위 내에 있는지 확인"""
        if landmarks is None or len(landmarks) == 0:
            return False
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return False
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        center_radius = 25  # 중앙 포인트 클릭 범위 (캔버스 좌표계 기준, 픽셀)
        
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
            RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            
            # 왼쪽 눈동자 중앙 포인트 체크 (계산값)
            left_iris_indices_set = set()
            for idx1, idx2 in LEFT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    left_iris_indices_set.add(idx1)
                    left_iris_indices_set.add(idx2)
            if 468 < len(landmarks):
                left_iris_indices_set.add(468)
            
            if left_iris_indices_set:
                left_iris_coords = []
                for idx in left_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        left_iris_coords.append((img_x, img_y))
                
                if left_iris_coords:
                    center_x = sum(c[0] for c in left_iris_coords) / len(left_iris_coords)
                    center_y = sum(c[1] for c in left_iris_coords) / len(left_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        return True
            
            # 오른쪽 눈동자 중앙 포인트 체크 (계산값)
            right_iris_indices_set = set()
            for idx1, idx2 in RIGHT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    right_iris_indices_set.add(idx1)
                    right_iris_indices_set.add(idx2)
            if 473 < len(landmarks):
                right_iris_indices_set.add(473)
            
            if right_iris_indices_set:
                right_iris_coords = []
                for idx in right_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        right_iris_coords.append((img_x, img_y))
                
                if right_iris_coords:
                    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
                    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        return True
        except (ImportError, AttributeError):
            # MediaPipe가 없거나 FACEMESH_LEFT_IRIS/FACEMESH_RIGHT_IRIS가 없으면 스킵
            pass
        
        return False
    
    def _calculate_iris_center(self, landmarks, iris_indices, img_width, img_height):
        """눈동자 인덱스에서 중앙 포인트 계산
        
        Args:
            landmarks: 랜드마크 리스트
            iris_indices: 눈동자 인덱스 리스트
            img_width: 이미지 너비
            img_height: 이미지 높이
        
        Returns:
            (center_x, center_y) 튜플 또는 None
        """
        if not landmarks or not iris_indices:
            return None
        
        iris_coords = []
        for idx in iris_indices:
            if idx < len(landmarks):
                pt = landmarks[idx]
                if isinstance(pt, tuple):
                    iris_coords.append(pt)
                else:
                    iris_coords.append((pt.x * img_width, pt.y * img_height))
        
        if not iris_coords:
            return None
        
        center_x = sum(c[0] for c in iris_coords) / len(iris_coords)
        center_y = sum(c[1] for c in iris_coords) / len(iris_coords)
        return (center_x, center_y)
    
    def _get_iris_indices(self):
        """MediaPipe 눈동자 인덱스 반환 (공통 유틸리티 함수 사용)
        
        Returns:
            (left_iris_indices, right_iris_indices) 튜플
        """
        try:
            from utils.face_morphing.region_extraction import get_iris_indices
            return get_iris_indices()
        except ImportError:
            # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
            return [474, 475, 476, 477], [469, 470, 471, 472]
    