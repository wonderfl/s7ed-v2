"""
얼굴 편집 패널 - 캔버스 드래그 처리 Mixin
캔버스 이미지 드래그 이벤트 처리를 담당
"""
import math
import time
import tkinter as tk
from utils.logger import debug, info, warning, error, log
from gui.FaceForge.utils.debugs import DEBUG_CANVAS_DRAG, DEBUG_CANVAS_DRAGGING

class CanvasDragMixin:
    """캔버스 드래그 처리 기능 Mixin"""

    def find_nearest_polygon_point(self, canvas_x, canvas_y, threshold=10):
        """캔버스 좌표에서 가장 가까운 폴리곤 포인트 찾기"""
        if not self.polygon_edit_mode.get():
            return None

        landmarks = self.landmark_manager.get_current_landmarks()
        if not landmarks:
            return None

        # ✅ 확장 레벨 가져오기
        expansion_level = getattr(self, 'region_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'region_expansion_level') else 1            
        
        # ✅ 선택된 부위의 인덱스 수집
        target_indices = self._get_selected_regions_expanded(len(landmarks), expansion_level)

        # 랜드마크 좌표를 캔버스 좌표로 변환
        img_width, img_height = self.current_image.size
        display_size = getattr(self.canvas_original, 'display_size', (img_width, img_height))

        scale_x = display_size[0] / img_width
        scale_y = display_size[1] / img_height
        coords = self.canvas_original.coords(self.image_created_original)

        if DEBUG_CANVAS_DRAG:
            info("find_nearest_polygon_point", 
                f"img_size=({img_width}, {img_height}), landmarks={len(landmarks)}, display_size={display_size}, "
                f"canvas_pos=({self.canvas_original_pos_x}, {self.canvas_original_pos_y}), \n"
                f"scale=({scale_x:.3f}, {scale_y:.3f}), coords=({coords})"
            )
        
        nearest_point = None
        min_distance = float('inf')

        # 랜드마크 좌표를 캔버스 좌표로 변환
        rel_x = (canvas_x - self.canvas_original_pos_x) / scale_x
        rel_y = (canvas_y - self.canvas_original_pos_y) / scale_y
        click_img_x = img_width / 2 + rel_x
        click_img_y = img_height / 2 + rel_y
        
        for i in target_indices:
            if i >= len(landmarks):
                continue
            landmark_x, landmark_y = landmarks[i]
            # 거리 계산
            distance = math.sqrt((click_img_x - landmark_x)**2 + (click_img_y - landmark_y)**2)
            if distance < threshold and distance < min_distance:
                min_distance = distance
                nearest_point = i
        
        if DEBUG_CANVAS_DRAG:
            log("find_nearest_polygon_point", f": nearest={nearest_point}, pos({canvas_x}, {canvas_y}), threshold={threshold}")

        return nearest_point

    def on_polygon_drag_start(self, event, dragging_index):
        """폴리곤 포인트 드래그 시작"""
        self.dragging_polygon = True
        self.dragging_index = dragging_index

        # 드래그 시작 위치 저장
        self.polygon_drag_start_x = event.x
        self.polygon_drag_start_y = event.y        
        
        # 현재 랜드마크 복사
        current_landmarks = self.landmark_manager.get_current_landmarks()
        self.drag_start_landmarks = current_landmarks.copy()
        
        if DEBUG_CANVAS_DRAGGING:
            debug("on_polygon_drag_start", f": dragging_index={dragging_index}")
    
    def on_polygon_dragging(self, event, canvas):
        """폴리곤 포인트 드래그 중"""
        if not self.dragging_polygon:
            return
        
        # 캔버스 좌표를 랜드마크 좌표로 변환
        img_width, img_height = self.current_image.size
        display_size = getattr(self.canvas_original, 'display_size', (img_width, img_height))

        scale_x = display_size[0] / img_width
        scale_y = display_size[1] / img_height

        img_center_x = self.canvas_original_pos_x
        img_center_y = self.canvas_original_pos_y

        coords = canvas.coords(self.image_created_original if canvas == self.canvas_original else self.image_created_edited)
        if coords and len(coords) >= 2:
            img_center_x = coords[0]
            img_center_y = coords[1]        
        
        # ✅ render.py와 동일한 좌표 변환
        rel_x = (event.x - img_center_x) / scale_x
        rel_y = (event.y - img_center_y) / scale_y

        target_x = img_width / 2 + rel_x
        target_y = img_height / 2 + rel_y

        if DEBUG_CANVAS_DRAGGING:
            debug("on_polygon_dragging", f": event={event}, dragged={self.dragging_index}, target=({target_x:.3f}, {target_y:.3f})")
        
        # 랜드마크 업데이트
        current_landmarks = self.landmark_manager.get_current_landmarks()
        current_landmarks[self.dragging_index] = (target_x, target_y)
        self.landmark_manager.set_current_landmarks(current_landmarks, reason="on_polygon_dragging")
        # 드래그된 포인트로 표시
        self.landmark_manager.mark_as_dragged(self.dragging_index)        

        if not hasattr(self, '_last_drag_update_time'):
            self._last_drag_update_time = 0
        
        current_time = time.time()
        if current_time - self._last_drag_update_time >= 0.040:  # 25 FPS
            self._last_drag_update_time = current_time
            # 실시간으로 오버레이 업데이트
            self.draw_overlays_current()
    
    def on_polygon_drag_end(self, event):
        """폴리곤 포인트 드래그 종료"""
        if not self.dragging_polygon:
            return

        self.last_selected_landmark_index = self.dragging_index

        current_landmarks = self.landmark_manager.get_current_landmarks()
        if (current_landmarks and self.dragging_index is not None
                and 0 <= self.dragging_index < len(current_landmarks)
                and hasattr(self, '_store_dragged_point')):
            self._store_dragged_point(self.dragging_index, current_landmarks[self.dragging_index])
            if DEBUG_CANVAS_DRAGGING:
                debug("on_polygon_drag_end", f": dragged={self.dragging_index}, currents={len(current_landmarks)}")

        self.dragging_polygon = False
        self.dragging_index = None

        # warping 적용 (필요하면)
        update_warping = self.use_landmark_warping.get()
        if update_warping:
            # 드래그 종료 시 이미지 워프 적용
            if hasattr(self, 'apply_polygon_warping'):
                if DEBUG_CANVAS_DRAGGING:
                    print(f"[on_polygon_drag_end] Applying image warping after drag")
                    print(f"[on_polygon_drag_end] current_landmarks count: {len(self.landmark_manager.get_current_landmarks()) if self.landmark_manager.get_current_landmarks() else 0}")    
                self.apply_polygon_warping(
                    desc="on_polygon_drag_end",
                    force_slider_mode=True,
                )
        
        if DEBUG_CANVAS_DRAGGING:
            debug("on_polygon_drag_end", f"warping={update_warping}, last_dragged={self.last_selected_landmark_index}")        
    
    def on_canvas_original_drag_start(self, event):
        """원본 이미지 캔버스 드래그 시작"""
        if DEBUG_CANVAS_DRAG:
            debug("on_canvas_original_drag_start", f"event: {event}, {self.dragging_polygon}")

        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        if getattr(self, 'dragging_polygon', False):
            return

        # ✅ 폴리곤 편집 모드 체크
        if self.polygon_edit_mode.get():
            # 폴리곤 포인트 찾기
            point_index = self.find_nearest_polygon_point(event.x, event.y)
            if point_index is not None:
                # 폴리곤 드래그 시작
                self.on_polygon_drag_start(event, point_index)
                return  # 이미지 드래그 안 함

            self.polygon_drag_start_x = None
            self.polygon_drag_start_y = None
        
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
        if DEBUG_CANVAS_DRAGGING:
            info("on_canvas_original_drag", 
            f"event: {event}, dragging: {self.dragging_polygon}, dragged_index: {self.dragging_index},\n"
            f"drag_start_x: {self.polygon_drag_start_x}")

        # 폴리곤에서 포인트 드래그 중이면 이미지 드래그 방지
        # 단, 실제로 포인트가 선택되어 있고 드래그가 시작된 경우에만 처리
        if (getattr(self, 'dragging_polygon', False) and 
            getattr(self, 'dragging_index', None) is not None and
            getattr(self, 'polygon_drag_start_x', None) is not None):
            # 폴리곤에서 찾은 포인트 드래그 중
            self.on_polygon_dragging(event, self.canvas_original)
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
            
            refresh = getattr(self, '_refresh_face_edit_display', None)
            if callable(refresh):
                refresh(
                    image=True,
                    polygons=self._is_polygon_display_enabled(),
                    pivots=self._is_pivot_display_enabled(),
                    guides=self._is_guides_display_enabled(),
                    bbox=self._is_bbox_frame_display_enabled(),
                    force_original=False,
                )
            # elif hasattr(self, '_draw_guides'):
            #     self._draw_guides()
            
            # 바운딩 박스도 함께 이동 (폴리곤이 체크되어 있을 때만)
            if (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get() and
                hasattr(self, 'bbox_rect_original') and self.bbox_rect_original is not None):
                # 바운딩 박스의 상대 위치를 유지하면서 이동
                if (hasattr(self, 'current_image') and self.current_image is not None and
                    hasattr(self, 'landmark_manager') and self.landmark_manager is not None):
                    try:
                        img_width, img_height = self.current_image.size
                        bbox = self.landmark_manager.get_original_bbox(img_width, img_height)
                        if bbox is not None:
                            min_x, min_y, max_x, max_y = bbox
                            display_size = getattr(self.canvas_original, 'display_size', None)
                            if display_size is not None:
                                display_width, display_height = display_size
                                scale_x = display_width / img_width
                                scale_y = display_height / img_height
                                
                                # 바운딩 박스 좌표를 캔버스 좌표로 변환
                                rel_x1 = (min_x - img_width / 2) * scale_x
                                rel_y1 = (min_y - img_height / 2) * scale_y
                                rel_x2 = (max_x - img_width / 2) * scale_x
                                rel_y2 = (max_y - img_height / 2) * scale_y
                                
                                canvas_x1 = new_x + rel_x1
                                canvas_y1 = new_y + rel_y1
                                canvas_x2 = new_x + rel_x2
                                canvas_y2 = new_y + rel_y2
                                
                                # 바운딩 박스 위치 업데이트
                                self.canvas_original.coords(self.bbox_back_original, canvas_x1+1, canvas_y1+1, canvas_x2+1, canvas_y2+1)
                                self.canvas_original.coords(self.bbox_rect_original, canvas_x1, canvas_y1, canvas_x2, canvas_y2)
                    except Exception as e:
                        # 바운딩 박스 업데이트 실패는 무시 (드래그 중이므로)
                        pass
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def on_canvas_original_drag_end(self, event):
        """원본 이미지 캔버스 드래그 종료"""
        is_dragging_polygon = getattr(self, 'dragging_polygon', False)
        is_dragging_index = getattr(self, 'dragging_index', None) 

        if DEBUG_CANVAS_DRAG:
            debug("on_canvas_original_drag_end", f"event: {event}, drag: {self.dragging_polygon}, dragged: {self.dragging_index}")

        # 폴리곤에서 포인트 드래그 중이면 드래그 종료
        if is_dragging_polygon and  is_dragging_index is not None:
            self.on_polygon_drag_end(event)
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
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
        
        self.canvas_original_drag_start_x = None
        self.canvas_original_drag_start_y = None
        self.canvas_original_drag_start_image_x = None
        self.canvas_original_drag_start_image_y = None
    
