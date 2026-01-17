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
        
        # 현재 랜드마크의 이미지 좌표 계산
        if canvas_obj == self.canvas_original:
            if self.current_image is None:
                return
            img = self.current_image
            # 랜드마크 가져오기 (커스텀 또는 원본)
            if self.custom_landmarks is not None:
                landmarks = self.custom_landmarks
            elif self.face_landmarks is not None:
                landmarks = self.face_landmarks
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if landmarks is None:
                    return
                self.face_landmarks = landmarks
                # 원본 랜드마크도 저장
                if self.original_landmarks is None:
                    self.original_landmarks = list(landmarks)
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            if self.edited_image is None:
                return
            img = self.edited_image
            # 편집된 이미지의 랜드마크는 커스텀 랜드마크 사용
            if self.custom_landmarks is not None:
                landmarks = self.custom_landmarks
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.edited_image)
                if landmarks is None:
                    return
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if landmarks is None or landmark_index >= len(landmarks):
            return
        
        self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = landmarks[landmark_index]
        
        # 커스텀 랜드마크 초기화 (처음 드래그할 때)
        # 슬라이더로 변형된 랜드마크가 있으면 그것을 기준으로 사용
        if self.custom_landmarks is None:
            # face_landmarks가 있으면 (슬라이더로 변형된 랜드마크) 그것을 사용
            if self.face_landmarks is not None:
                self.custom_landmarks = list(self.face_landmarks)
            else:
                self.custom_landmarks = list(landmarks) if landmarks else None
        
        # 선택된 포인트 표시 (큰 원으로 강조)
        self._draw_selected_landmark_indicator(canvas_obj, landmark_index, event.x, event.y)
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_polygon_drag(self, event, landmark_index, canvas_obj):
        """폴리곤에서 찾은 포인트 드래그 중"""
        # 포인트가 선택되어 있고 드래그 중인 경우에만 처리
        if not self.dragging_polygon or self.dragged_polygon_index != landmark_index:
            return
        
        if self.custom_landmarks is None:
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
        if landmark_index < len(self.custom_landmarks):
            old_pos = self.custom_landmarks[landmark_index]
            self.custom_landmarks[landmark_index] = (img_x, img_y)
            # 디버깅: 인덱스와 위치 변경 확인
            if abs(old_pos[0] - img_x) > 0.1 or abs(old_pos[1] - img_y) > 0.1:
                print(f"[얼굴편집] 랜드마크 인덱스 {landmark_index} 위치 변경: ({old_pos[0]:.1f}, {old_pos[1]:.1f}) -> ({img_x:.1f}, {img_y:.1f})")
            
            # 랜드마크 포인트 위치 업데이트
            # polygon_point_map은 이제 포인트 아이템 ID가 아니라 True 값만 저장하므로
            # 포인트 아이템을 직접 업데이트할 수 없음
            # 대신 랜드마크가 그려져 있으면 landmark_point_map을 사용해야 함
            # 하지만 현재는 폴리곤에서만 드래그하므로 포인트 아이템 업데이트는 불필요
            # 폴리곤 드래그 중에는 포인트 아이템을 업데이트하지 않음
            
            # 선택된 포인트 표시 업데이트
            self._update_selected_landmark_indicator(canvas_obj, event.x, event.y)
            
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
        
        # 드래그 종료 시 항상 변형 적용
        if self.custom_landmarks is not None:
            self.apply_polygon_drag_final()
        
        # 마지막으로 선택한 포인트 인덱스 저장 (드래그 종료 후에도 유지)
        self.last_selected_landmark_index = landmark_index
        print(f"[얼굴편집] 드래그 종료: 마지막 선택 포인트 인덱스 {landmark_index} 저장")
        
        # 선택된 포인트 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 드래그 종료 시 플래그 초기화 (이미지 드래그 가능하도록)
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.dragged_polygon_canvas = None
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def apply_polygon_drag_preview(self):
        """폴리곤 드래그 중 실시간 미리보기 (현재 비활성화: 성능 최적화)"""
        # 성능 최적화: 드래그 중에는 실시간 미리보기 비활성화
        # 드래그 종료 시에만 최종 편집 적용
        pass
    
    def apply_polygon_drag_final(self):
        """폴리곤 드래그 종료 시 최종 편집 적용"""
        if self.custom_landmarks is None or self.current_image is None:
            return
        
        try:
            # 원본 랜드마크 가져오기 (항상 원본 이미지 기준)
            if self.original_landmarks is None:
                original_landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if original_landmarks is None:
                    print("[얼굴편집] 원본 랜드마크 감지 실패")
                    return
                self.original_landmarks = original_landmarks
            else:
                original_landmarks = self.original_landmarks
            
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
                if last_idx < len(original_landmarks) and last_idx < len(self.custom_landmarks):
                    orig_pos = original_landmarks[last_idx]
                    custom_pos = self.custom_landmarks[last_idx]
                    diff = ((custom_pos[0] - orig_pos[0])**2 + (custom_pos[1] - orig_pos[1])**2)**0.5
                    print(f"[얼굴편집] 마지막 선택 포인트 인덱스 {last_idx}: 원본=({orig_pos[0]:.1f}, {orig_pos[1]:.1f}), 변형=({custom_pos[0]:.1f}, {custom_pos[1]:.1f}), 거리={diff:.1f}픽셀")
            
            # 랜드마크 변형 적용 (원본 이미지와 원본 랜드마크를 기준으로)
            # 고급 모드 여부와 관계없이 Delaunay Triangulation 사용
            # 마지막으로 선택한 포인트 인덱스 전달 (인덱스 기반 직접 매핑을 위해)
            last_selected_index = getattr(self, 'last_selected_landmark_index', None)
            result = face_morphing.morph_face_by_polygons(
                self.current_image,  # 원본 이미지
                original_landmarks,  # 원본 랜드마크
                self.custom_landmarks,  # 변형된 랜드마크
                selected_point_indices=[last_selected_index] if last_selected_index is not None else None  # 선택한 포인트 인덱스
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
        if canvas_obj == self.canvas_original:
            visible_point_map = self.polygon_point_map_original
            polygon_items = self.landmark_polygon_items_original
        else:
            visible_point_map = self.polygon_point_map_edited
            polygon_items = self.landmark_polygon_items_edited
        
        # 폴리곤에 포함된 포인트만 확인 (polygon_point_map 사용)
        # 확장 레벨로 추가된 포인트도 포함됨
        if len(polygon_items) > 0:
            # 폴리곤이 그려져 있으면 polygon_point_map에 있는 포인트만 확인
            # 이렇게 하면 확장 레벨로 추가된 포인트도 포함됨
            visible_indices = list(visible_point_map.keys())
        else:
            # 폴리곤이 그려져 있지 않으면 빈 리스트
            visible_indices = []
        
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
