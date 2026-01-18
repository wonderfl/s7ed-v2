"""
얼굴 편집 패널 - 캔버스 드래그 처리 Mixin
캔버스 이미지 드래그 이벤트 처리를 담당
"""
import math


class CanvasDragHandlerMixin:
    """캔버스 드래그 처리 기능 Mixin"""
    
    def on_canvas_original_drag_start(self, event):
        """원본 이미지 캔버스 드래그 시작"""
        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        if getattr(self, 'dragging_polygon', False):
            return
        
        # 폴리곤 위에서 포인트를 찾아서 드래그 시작 시도
        # 폴리곤 클릭 이벤트를 제거했으므로, 캔버스 레벨에서 포인트를 찾아야 함
        # 하지만 포인트를 찾지 못했을 때만 이미지 드래그를 시작해야 함
        if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                landmarks = self.custom_landmarks
            elif hasattr(self, 'face_landmarks') and self.face_landmarks is not None:
                landmarks = self.face_landmarks
            else:
                landmarks = None
            
            if landmarks is not None:
                # 중앙 포인트를 먼저 체크 (눈동자 포인트보다 우선)
                # 중앙 포인트가 클릭 범위 내에 있으면 다른 포인트를 찾지 않음
                if hasattr(self, '_check_iris_center_click'):
                    if self._check_iris_center_click(event, landmarks, self.canvas_original):
                        # 중앙 포인트가 클릭되었으므로 다른 포인트를 찾지 않음
                        # tag_bind 이벤트가 처리할 것임
                        print(f"[얼굴편집] 중앙 포인트 클릭 감지 - 다른 포인트 찾기 건너뜀")
                        return
                
                # 화면에 보이는 모든 포인트 중에서 가장 가까운 포인트 찾기
                # 현재 탭에 해당하는 포인트만 찾는 것이 아니라 모든 포인트를 확인
                nearest_idx = self._find_nearest_landmark_for_drag(event, landmarks, None, self.canvas_original)
                if nearest_idx is not None:
                    # 포인트를 찾았으면 바로 드래그 시작
                    result = self.on_polygon_drag_start(event, nearest_idx, self.canvas_original)
                    # 포인트 드래그가 시작되었으므로 이미지 드래그는 하지 않음
                    return
                else:
                    # 포인트를 찾지 못했으면 빈 공간 클릭으로 간주
                    # 이미 선택된 포인트가 있으면 선택 해제하고 드래그 상태 완전히 초기화
                    if getattr(self, 'dragged_polygon_index', None) is not None:
                        self._remove_selected_landmark_indicator(self.canvas_original)
                        self.dragged_polygon_index = None
                        self.dragging_polygon = False
                        self.polygon_drag_start_x = None
                        self.polygon_drag_start_y = None
                        self.polygon_drag_start_img_x = None
                        self.polygon_drag_start_img_y = None
        
        # 연결선 클릭 확인 제거 (연결선 클릭 기능 제거됨)
        
        if self.image_created_original is None:
            return
        
        # 드래그 시작 위치 저장 (마우스 클릭 위치)
        self.canvas_original_drag_start_x = event.x
        self.canvas_original_drag_start_y = event.y
        
        # 현재 이미지의 실제 위치를 캔버스에서 가져오기
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        
        try:
            coords = self.canvas_original.coords(self.image_created_original)
            if coords and len(coords) >= 2 and coords[0] is not None and coords[1] is not None:
                # coords에서 위치를 가져옴
                self.canvas_original_drag_start_image_x = coords[0]
                self.canvas_original_drag_start_image_y = coords[1]
                # 저장된 위치도 업데이트
                self.canvas_original_pos_x = coords[0]
                self.canvas_original_pos_y = coords[1]
            else:
                # coords가 없거나 None이면 저장된 위치 사용
                if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                    self.canvas_original_drag_start_image_x = self.canvas_original_pos_x
                    self.canvas_original_drag_start_image_y = self.canvas_original_pos_y
                else:
                    # 저장된 위치도 없으면 중앙 위치 사용
                    self.canvas_original_drag_start_image_x = preview_width // 2
                    self.canvas_original_drag_start_image_y = preview_height // 2
                    self.canvas_original_pos_x = preview_width // 2
                    self.canvas_original_pos_y = preview_height // 2
        except Exception as e:
            print(f"[얼굴편집] 드래그 시작 시 위치 가져오기 실패: {e}")
            # 실패 시 저장된 위치 또는 중앙 위치 사용
            if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                self.canvas_original_drag_start_image_x = self.canvas_original_pos_x
                self.canvas_original_drag_start_image_y = self.canvas_original_pos_y
            else:
                self.canvas_original_drag_start_image_x = preview_width // 2
                self.canvas_original_drag_start_image_y = preview_height // 2
                self.canvas_original_pos_x = preview_width // 2
                self.canvas_original_pos_y = preview_height // 2
    
    def on_canvas_original_drag(self, event):
        """원본 이미지 캔버스 드래그 중"""
        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        # 단, 실제로 포인트가 선택되어 있고 드래그가 시작된 경우에만 처리
        if (getattr(self, 'dragging_polygon', False) and 
            getattr(self, 'dragged_polygon_index', None) is not None and
            getattr(self, 'polygon_drag_start_x', None) is not None):
            # 폴리곤에서 찾은 포인트 드래그 중
            self.on_polygon_drag(event, self.dragged_polygon_index, self.canvas_original)
            return
        
        if (self.canvas_original_drag_start_x is None or 
            self.canvas_original_drag_start_y is None or
            self.image_created_original is None):
            return
        
        # 드래그 시작 시 이미지 위치가 없으면 현재 위치에서 가져오기
        if (self.canvas_original_drag_start_image_x is None or 
            self.canvas_original_drag_start_image_y is None):
            try:
                coords = self.canvas_original.coords(self.image_created_original)
                if coords and len(coords) >= 2:
                    self.canvas_original_drag_start_image_x = coords[0]
                    self.canvas_original_drag_start_image_y = coords[1]
                else:
                    # coords가 없으면 중앙 위치 사용
                    preview_width = getattr(self, 'preview_width', 800)
                    preview_height = getattr(self, 'preview_height', 1000)
                    self.canvas_original_drag_start_image_x = preview_width // 2
                    self.canvas_original_drag_start_image_y = preview_height // 2
            except Exception as e:
                print(f"[얼굴편집] 드래그 중 위치 가져오기 실패: {e}")
                preview_width = getattr(self, 'preview_width', 800)
                preview_height = getattr(self, 'preview_height', 1000)
                self.canvas_original_drag_start_image_x = preview_width // 2
                self.canvas_original_drag_start_image_y = preview_height // 2
        
        # 이동 거리 계산
        dx = event.x - self.canvas_original_drag_start_x
        dy = event.y - self.canvas_original_drag_start_y
        
        # 새로운 이미지 위치 계산 (드래그 시작 위치 + 이동 거리)
        new_x = self.canvas_original_drag_start_image_x + dx
        new_y = self.canvas_original_drag_start_image_y + dy
        
        # 드래그 중에는 경계 제한 없이 자유롭게 이동
        # 경계 제한은 드래그 종료 시에만 적용
        
        # 이미지 위치 업데이트
        try:
            self.canvas_original.coords(self.image_created_original, new_x, new_y)
            self.canvas_original_pos_x = new_x
            self.canvas_original_pos_y = new_y
            # 편집된 이미지도 동일한 위치로 동기화
            if self.image_created_edited is not None:
                self.canvas_edited.coords(self.image_created_edited, new_x, new_y)
                self.canvas_edited_pos_x = new_x
                self.canvas_edited_pos_y = new_y
        except Exception as e:
            print(f"[얼굴편집] 원본 이미지 위치 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def on_canvas_original_drag_end(self, event):
        """원본 이미지 캔버스 드래그 종료"""
        # 폴리곤에서 포인트 드래그 중이면 드래그 종료
        if getattr(self, 'dragging_polygon', False) and getattr(self, 'dragged_polygon_index', None) is not None:
            self.on_polygon_drag_end(event, self.dragged_polygon_index, self.canvas_original)
            return
        # 드래그 종료 시 현재 위치를 저장만 하고 경계 제한은 적용하지 않음
        # 사용자가 드래그한 위치를 그대로 유지
        if self.image_created_original is not None:
            try:
                coords = self.canvas_original.coords(self.image_created_original)
                if coords and len(coords) >= 2:
                    # 현재 위치를 저장만 함 (경계 제한 없이)
                    self.canvas_original_pos_x = coords[0]
                    self.canvas_original_pos_y = coords[1]
                    # 편집된 이미지도 동일한 위치로 동기화
                    if self.image_created_edited is not None:
                        self.canvas_edited.coords(self.image_created_edited, coords[0], coords[1])
                        self.canvas_edited_pos_x = coords[0]
                        self.canvas_edited_pos_y = coords[1]
                    
                    # 랜드마크가 표시되어 있으면 기존 랜드마크 제거 후 새로운 위치에 다시 그리기
                    if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                        # 기존 랜드마크 제거
                        if hasattr(self, 'clear_landmarks_display'):
                            self.clear_landmarks_display()
                        # 연결선도 제거
                        for item_id in self.landmark_polygon_items['original']:
                            try:
                                self.canvas_original.delete(item_id)
                            except Exception:
                                pass
                        self.landmark_polygon_items['original'].clear()
                        for item_id in self.landmark_polygon_items['edited']:
                            try:
                                self.canvas_edited.delete(item_id)
                            except Exception:
                                pass
                        self.landmark_polygon_items['edited'].clear()
                        # 새로운 위치에 다시 그리기
                        if hasattr(self, 'update_face_features_display'):
                            self.update_face_features_display()
                    
                    # 눈 영역 표시 업데이트
                    if hasattr(self, 'show_eye_region') and self.show_eye_region.get():
                        if hasattr(self, 'update_eye_region_display'):
                            self.update_eye_region_display()
                    
                    # 입술 영역 표시 업데이트
                    if hasattr(self, 'show_lip_region') and self.show_lip_region.get():
                        if hasattr(self, 'update_lip_region_display'):
                            self.update_lip_region_display()
            except Exception as e:
                print(f"[얼굴편집] 드래그 종료 시 위치 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        self.canvas_original_drag_start_x = None
        self.canvas_original_drag_start_y = None
        self.canvas_original_drag_start_image_x = None
        self.canvas_original_drag_start_image_y = None
    
    def on_canvas_edited_drag_start(self, event):
        """편집된 이미지 캔버스 드래그 시작"""
        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        if getattr(self, 'dragging_polygon', False):
            return
        
        # 폴리곤 위에서 포인트를 찾아서 드래그 시작 시도
        # 폴리곤 클릭 이벤트를 제거했으므로, 캔버스 레벨에서 포인트를 찾아야 함
        if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                landmarks = self.custom_landmarks
            elif hasattr(self, 'face_landmarks') and self.face_landmarks is not None:
                landmarks = self.face_landmarks
            else:
                landmarks = None
            
            if landmarks is not None:
                # 중앙 포인트를 먼저 체크 (눈동자 포인트보다 우선)
                # 중앙 포인트가 클릭 범위 내에 있으면 다른 포인트를 찾지 않음
                if hasattr(self, '_check_iris_center_click'):
                    if self._check_iris_center_click(event, landmarks, self.canvas_edited):
                        # 중앙 포인트가 클릭되었으므로 다른 포인트를 찾지 않음
                        # tag_bind 이벤트가 처리할 것임
                        return
                
                # 화면에 보이는 모든 포인트 중에서 가장 가까운 포인트 찾기
                # 현재 탭에 해당하는 포인트만 찾는 것이 아니라 모든 포인트를 확인
                nearest_idx = self._find_nearest_landmark_for_drag(event, landmarks, None, self.canvas_edited)
                if nearest_idx is not None:
                    # 포인트를 찾았으면 바로 드래그 시작
                    result = self.on_polygon_drag_start(event, nearest_idx, self.canvas_edited)
                    # 포인트 드래그가 시작되었으므로 이미지 드래그는 하지 않음
                    return
                else:
                    # 포인트를 찾지 못했으면 빈 공간 클릭으로 간주
                    # 이미 선택된 포인트가 있으면 선택 해제하고 드래그 상태 완전히 초기화
                    if getattr(self, 'dragged_polygon_index', None) is not None:
                        self._remove_selected_landmark_indicator(self.canvas_edited)
                        self.dragged_polygon_index = None
                        self.dragging_polygon = False
                        self.polygon_drag_start_x = None
                        self.polygon_drag_start_y = None
                        self.polygon_drag_start_img_x = None
                        self.polygon_drag_start_img_y = None
        
        # 연결선 클릭 확인 제거 (연결선 클릭 기능 제거됨)
        
        if self.image_created_edited is None:
            return
        
        # 드래그 시작 위치 저장 (마우스 클릭 위치)
        self.canvas_edited_drag_start_x = event.x
        self.canvas_edited_drag_start_y = event.y
        
        # 현재 이미지의 실제 위치를 캔버스에서 가져오기
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        
        try:
            coords = self.canvas_edited.coords(self.image_created_edited)
            if coords and len(coords) >= 2 and coords[0] is not None and coords[1] is not None:
                # coords에서 위치를 가져옴
                self.canvas_edited_drag_start_image_x = coords[0]
                self.canvas_edited_drag_start_image_y = coords[1]
                # 저장된 위치도 업데이트
                self.canvas_edited_pos_x = coords[0]
                self.canvas_edited_pos_y = coords[1]
            else:
                # coords가 없거나 None이면 저장된 위치 사용
                if self.canvas_edited_pos_x is not None and self.canvas_edited_pos_y is not None:
                    self.canvas_edited_drag_start_image_x = self.canvas_edited_pos_x
                    self.canvas_edited_drag_start_image_y = self.canvas_edited_pos_y
                else:
                    # 저장된 위치도 없으면 중앙 위치 사용
                    self.canvas_edited_drag_start_image_x = preview_width // 2
                    self.canvas_edited_drag_start_image_y = preview_height // 2
                    self.canvas_edited_pos_x = preview_width // 2
                    self.canvas_edited_pos_y = preview_height // 2
        except Exception as e:
            print(f"[얼굴편집] 드래그 시작 시 위치 가져오기 실패: {e}")
            # 실패 시 저장된 위치 또는 중앙 위치 사용
            if self.canvas_edited_pos_x is not None and self.canvas_edited_pos_y is not None:
                self.canvas_edited_drag_start_image_x = self.canvas_edited_pos_x
                self.canvas_edited_drag_start_image_y = self.canvas_edited_pos_y
            else:
                self.canvas_edited_drag_start_image_x = preview_width // 2
                self.canvas_edited_drag_start_image_y = preview_height // 2
                self.canvas_edited_pos_x = preview_width // 2
                self.canvas_edited_pos_y = preview_height // 2
    
    def on_canvas_edited_drag(self, event):
        """편집된 이미지 캔버스 드래그 중"""
        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        # 단, 실제로 포인트가 선택되어 있고 드래그가 시작된 경우에만 처리
        if (getattr(self, 'dragging_polygon', False) and 
            getattr(self, 'dragged_polygon_index', None) is not None and
            getattr(self, 'polygon_drag_start_x', None) is not None):
            # 폴리곤에서 찾은 포인트 드래그 중
            self.on_polygon_drag(event, self.dragged_polygon_index, self.canvas_edited)
            return
        
        if (self.canvas_edited_drag_start_x is None or 
            self.canvas_edited_drag_start_y is None or
            self.image_created_edited is None):
            return
        
        # 드래그 시작 시 이미지 위치가 없으면 현재 위치에서 가져오기
        if (self.canvas_edited_drag_start_image_x is None or 
            self.canvas_edited_drag_start_image_y is None):
            try:
                coords = self.canvas_edited.coords(self.image_created_edited)
                if coords and len(coords) >= 2:
                    self.canvas_edited_drag_start_image_x = coords[0]
                    self.canvas_edited_drag_start_image_y = coords[1]
                else:
                    # coords가 없으면 중앙 위치 사용
                    preview_width = getattr(self, 'preview_width', 800)
                    preview_height = getattr(self, 'preview_height', 1000)
                    self.canvas_edited_drag_start_image_x = preview_width // 2
                    self.canvas_edited_drag_start_image_y = preview_height // 2
            except Exception as e:
                print(f"[얼굴편집] 드래그 중 위치 가져오기 실패: {e}")
                preview_width = getattr(self, 'preview_width', 800)
                preview_height = getattr(self, 'preview_height', 1000)
                self.canvas_edited_drag_start_image_x = preview_width // 2
                self.canvas_edited_drag_start_image_y = preview_height // 2
        
        # 이동 거리 계산
        dx = event.x - self.canvas_edited_drag_start_x
        dy = event.y - self.canvas_edited_drag_start_y
        
        # 새로운 이미지 위치 계산 (드래그 시작 위치 + 이동 거리)
        new_x = self.canvas_edited_drag_start_image_x + dx
        new_y = self.canvas_edited_drag_start_image_y + dy
        
        # 드래그 중에는 경계 제한 없이 자유롭게 이동
        # 경계 제한은 드래그 종료 시에만 적용
        
        # 이미지 위치 업데이트
        try:
            self.canvas_edited.coords(self.image_created_edited, new_x, new_y)
            self.canvas_edited_pos_x = new_x
            self.canvas_edited_pos_y = new_y
            # 원본 이미지도 동일한 위치로 동기화
            if self.image_created_original is not None:
                self.canvas_original.coords(self.image_created_original, new_x, new_y)
                self.canvas_original_pos_x = new_x
                self.canvas_original_pos_y = new_y
        except Exception as e:
            print(f"[얼굴편집] 편집된 이미지 위치 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def on_canvas_edited_drag_end(self, event):
        """편집된 이미지 캔버스 드래그 종료"""
        # 폴리곤에서 포인트 드래그 중이면 드래그 종료
        if getattr(self, 'dragging_polygon', False) and getattr(self, 'dragged_polygon_index', None) is not None:
            self.on_polygon_drag_end(event, self.dragged_polygon_index, self.canvas_edited)
            return
        # 드래그 종료 시 현재 위치를 저장만 하고 경계 제한은 적용하지 않음
        # 사용자가 드래그한 위치를 그대로 유지
        if self.image_created_edited is not None:
            try:
                coords = self.canvas_edited.coords(self.image_created_edited)
                if coords and len(coords) >= 2:
                    # 현재 위치를 저장만 함 (경계 제한 없이)
                    self.canvas_edited_pos_x = coords[0]
                    self.canvas_edited_pos_y = coords[1]
                    # 원본 이미지도 동일한 위치로 동기화
                    if self.image_created_original is not None:
                        self.canvas_original.coords(self.image_created_original, coords[0], coords[1])
                        self.canvas_original_pos_x = coords[0]
                        self.canvas_original_pos_y = coords[1]
                    
                    # 랜드마크가 표시되어 있으면 기존 랜드마크 제거 후 새로운 위치에 다시 그리기
                    if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                        # 기존 랜드마크 제거
                        if hasattr(self, 'clear_landmarks_display'):
                            self.clear_landmarks_display()
                        # 연결선도 제거
                        for item_id in self.landmark_polygon_items['original']:
                            try:
                                self.canvas_original.delete(item_id)
                            except Exception:
                                pass
                        self.landmark_polygon_items['original'].clear()
                        for item_id in self.landmark_polygon_items['edited']:
                            try:
                                self.canvas_edited.delete(item_id)
                            except Exception:
                                pass
                        self.landmark_polygon_items['edited'].clear()
                        # 새로운 위치에 다시 그리기
                        if hasattr(self, 'update_face_features_display'):
                            self.update_face_features_display()
                    
                    # 눈 영역 표시 업데이트
                    if hasattr(self, 'show_eye_region') and self.show_eye_region.get():
                        if hasattr(self, 'update_eye_region_display'):
                            self.update_eye_region_display()
                    
                    # 입술 영역 표시 업데이트
                    if hasattr(self, 'show_lip_region') and self.show_lip_region.get():
                        if hasattr(self, 'update_lip_region_display'):
                            self.update_lip_region_display()
            except Exception as e:
                print(f"[얼굴편집] 드래그 종료 시 위치 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        self.canvas_edited_drag_start_x = None
        self.canvas_edited_drag_start_y = None
        self.canvas_edited_drag_start_image_x = None
        self.canvas_edited_drag_start_image_y = None
