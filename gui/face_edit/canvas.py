"""
얼굴 편집 패널 - 캔버스 이벤트 처리 Mixin
확대/축소 및 이미지 저장 관련 기능을 담당
"""
import os
import tkinter as tk
from tkinter import messagebox


class CanvasEventHandlerMixin:
    """캔버스 이벤트 처리 기능 Mixin"""
    
    
    def zoom_in_original(self, mouse_x=None, mouse_y=None):
        """원본 이미지 확대 (마우스 위치를 중심으로)"""
        if self.current_image is None:
            return
        
        # 확대 제한
        max_scale = getattr(self, 'zoom_max_scale', 8.0)  # 최대 확대 비율
        if self.zoom_scale_original >= max_scale:
            return
        
        # 마우스 위치가 제공되지 않으면 저장된 위치 또는 캔버스 중앙 사용
        if mouse_x is None or mouse_y is None:
            mouse_x = getattr(self, '_last_mouse_x_original', None)
            mouse_y = getattr(self, '_last_mouse_y_original', None)
            if mouse_x is None or mouse_y is None:
                # 캔버스 중앙 사용
                canvas_width = self.canvas_original.winfo_width()
                canvas_height = self.canvas_original.winfo_height()
                mouse_x = canvas_width // 2
                mouse_y = canvas_height // 2
        
        # 현재 이미지 위치와 크기 가져오기
        old_img_x = self.canvas_original_pos_x
        old_img_y = self.canvas_original_pos_y
        old_scale = self.zoom_scale_original
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 마우스 위치에서 이미지 중심까지의 거리
        img_mouse_x = mouse_x - old_img_x
        img_mouse_y = mouse_y - old_img_y
        
        # 확대 비율 업데이트
        new_scale = min(old_scale * 1.1, max_scale)
        scale_ratio = new_scale / old_scale
        
        # 새로운 이미지 크기
        new_display_width = int(old_display_width * scale_ratio)
        new_display_height = int(old_display_height * scale_ratio)
        
        # 마우스 위치를 중심으로 이미지 위치 조정
        new_img_x = mouse_x - img_mouse_x * scale_ratio
        new_img_y = mouse_y - img_mouse_y * scale_ratio
        
        # 위치 저장
        self.zoom_scale_original = new_scale
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        # 편집된 이미지도 동일한 위치로 동기화
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_original_preview()
        # 편집된 이미지도 동일하게 확대/축소 및 위치 동기화
        self.show_edited_preview()
        
        # 확대/축소 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_zoom():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_out_original(self, mouse_x=None, mouse_y=None):
        """원본 이미지 축소 (마우스 위치를 중심으로)"""
        if self.current_image is None:
            return
        
        # 축소 제한
        min_scale = getattr(self, 'zoom_min_scale', 0.2)  # 최소 축소 비율
        if self.zoom_scale_original <= min_scale:
            return
        
        # 마우스 위치가 제공되지 않으면 저장된 위치 또는 캔버스 중앙 사용
        if mouse_x is None or mouse_y is None:
            mouse_x = getattr(self, '_last_mouse_x_original', None)
            mouse_y = getattr(self, '_last_mouse_y_original', None)
            if mouse_x is None or mouse_y is None:
                # 캔버스 중앙 사용
                canvas_width = self.canvas_original.winfo_width()
                canvas_height = self.canvas_original.winfo_height()
                mouse_x = canvas_width // 2
                mouse_y = canvas_height // 2
        
        # 현재 이미지 위치와 크기 가져오기
        old_img_x = self.canvas_original_pos_x
        old_img_y = self.canvas_original_pos_y
        old_scale = self.zoom_scale_original
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 마우스 위치에서 이미지 중심까지의 거리
        img_mouse_x = mouse_x - old_img_x
        img_mouse_y = mouse_y - old_img_y
        
        # 축소 비율 업데이트
        new_scale = max(old_scale / 1.1, min_scale)
        scale_ratio = new_scale / old_scale
        
        # 새로운 이미지 크기
        new_display_width = int(old_display_width * scale_ratio)
        new_display_height = int(old_display_height * scale_ratio)
        
        # 마우스 위치를 중심으로 이미지 위치 조정
        new_img_x = mouse_x - img_mouse_x * scale_ratio
        new_img_y = mouse_y - img_mouse_y * scale_ratio
        
        # 위치 저장
        self.zoom_scale_original = new_scale
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        # 편집된 이미지도 동일한 위치로 동기화
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_original_preview()
        # 편집된 이미지도 동일하게 확대/축소 및 위치 동기화
        self.show_edited_preview()
        
        # 확대/축소 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_zoom():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_reset_original(self):
        """원본 이미지 확대/축소 초기화"""
        if self.current_image is None:
            return
        
        # "원래대로" 버튼 플래그 설정
        self.is_resetting_position = True
        
        self.zoom_scale_original = 1.0
        # 위치를 중앙으로 초기화
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        self.canvas_original_pos_x = preview_width // 2
        self.canvas_original_pos_y = preview_height // 2
        
        # 확대/축소 중 플래그 설정
        self._is_zooming = True
        
        self.show_original_preview()
        # 편집된 이미지도 동일하게 초기화 및 위치 동기화
        self.show_edited_preview()

        # 플래그 해제
        self.is_resetting_position = False
        
        # 확대/축소 초기화 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_reset():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_reset)
    
    def zoom_in_edited(self, mouse_x=None, mouse_y=None):
        """편집된 이미지 확대 (마우스 위치를 중심으로)"""
        if self.edited_image is None:
            return
        
        # 원본과 동일한 확대 비율 사용
        max_scale = getattr(self, 'zoom_max_scale', 8.0)
        if self.zoom_scale_original >= max_scale:
            return
        
        # 마우스 위치가 제공되지 않으면 저장된 위치 또는 캔버스 중앙 사용
        if mouse_x is None or mouse_y is None:
            mouse_x = getattr(self, '_last_mouse_x_edited', None)
            mouse_y = getattr(self, '_last_mouse_y_edited', None)
            if mouse_x is None or mouse_y is None:
                # 캔버스 중앙 사용
                canvas_width = self.canvas_edited.winfo_width()
                canvas_height = self.canvas_edited.winfo_height()
                mouse_x = canvas_width // 2
                mouse_y = canvas_height // 2
        
        # 현재 이미지 위치와 크기 가져오기
        old_img_x = self.canvas_edited_pos_x
        old_img_y = self.canvas_edited_pos_y
        old_scale = self.zoom_scale_original
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 마우스 위치에서 이미지 중심까지의 거리
        img_mouse_x = mouse_x - old_img_x
        img_mouse_y = mouse_y - old_img_y
        
        # 확대 비율 업데이트
        new_scale = min(old_scale * 1.1, max_scale)
        scale_ratio = new_scale / old_scale
        
        # 새로운 이미지 크기
        new_display_width = int(old_display_width * scale_ratio)
        new_display_height = int(old_display_height * scale_ratio)
        
        # 마우스 위치를 중심으로 이미지 위치 조정
        new_img_x = mouse_x - img_mouse_x * scale_ratio
        new_img_y = mouse_y - img_mouse_y * scale_ratio
        
        # 위치 저장
        self.zoom_scale_original = new_scale
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        # 원본 이미지도 동일한 위치로 동기화
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정
        self._is_zooming = True
        
        self.show_original_preview()
        self.show_edited_preview()
        
        # 확대/축소 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_zoom():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_out_edited(self, mouse_x=None, mouse_y=None):
        """편집된 이미지 축소 (마우스 위치를 중심으로)"""
        if self.edited_image is None:
            return
        
        # 원본과 동일한 축소 비율 사용
        min_scale = getattr(self, 'zoom_min_scale', 0.2)
        if self.zoom_scale_original <= min_scale:
            return
        
        # 마우스 위치가 제공되지 않으면 저장된 위치 또는 캔버스 중앙 사용
        if mouse_x is None or mouse_y is None:
            mouse_x = getattr(self, '_last_mouse_x_edited', None)
            mouse_y = getattr(self, '_last_mouse_y_edited', None)
            if mouse_x is None or mouse_y is None:
                # 캔버스 중앙 사용
                canvas_width = self.canvas_edited.winfo_width()
                canvas_height = self.canvas_edited.winfo_height()
                mouse_x = canvas_width // 2
                mouse_y = canvas_height // 2
        
        # 현재 이미지 위치와 크기 가져오기
        old_img_x = self.canvas_edited_pos_x
        old_img_y = self.canvas_edited_pos_y
        old_scale = self.zoom_scale_original
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 마우스 위치에서 이미지 중심까지의 거리
        img_mouse_x = mouse_x - old_img_x
        img_mouse_y = mouse_y - old_img_y
        
        # 축소 비율 업데이트
        new_scale = max(old_scale / 1.1, min_scale)
        scale_ratio = new_scale / old_scale
        
        # 새로운 이미지 크기
        new_display_width = int(old_display_width * scale_ratio)
        new_display_height = int(old_display_height * scale_ratio)
        
        # 마우스 위치를 중심으로 이미지 위치 조정
        new_img_x = mouse_x - img_mouse_x * scale_ratio
        new_img_y = mouse_y - img_mouse_y * scale_ratio
        
        # 위치 저장
        self.zoom_scale_original = new_scale
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        # 원본 이미지도 동일한 위치로 동기화
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정
        self._is_zooming = True
        
        self.show_original_preview()
        self.show_edited_preview()
        
        # 확대/축소 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_zoom():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_reset_edited(self):
        """편집된 이미지 확대/축소 초기화"""
        if self.edited_image is None:
            return
        
        # "원래대로" 버튼 플래그 설정
        self.is_resetting_position = True
        
        self.zoom_scale_original = 1.0
        # 위치를 중앙으로 초기화
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        self.canvas_edited_pos_x = preview_width // 2
        self.canvas_edited_pos_y = preview_height // 2
        
        # 확대/축소 중 플래그 설정
        self._is_zooming = True
        
        self.show_original_preview()
        self.show_edited_preview()

        # 플래그 해제
        self.is_resetting_position = False
        
        # 확대/축소 초기화 완료 후 랜드마크 다시 그리기 (지연 처리)
        def update_landmarks_after_reset():
            self._is_zooming = False
            if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                # 기존 랜드마크 제거 (중복 방지)
                if hasattr(self, 'clear_landmarks_display'):
                    self.clear_landmarks_display()
                # 연결선 및 폴리곤도 제거
                for item_id in list(self.landmark_polygon_items['original']):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                for item_id in list(self.landmark_polygon_items['edited']):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 랜드마크 다시 그리기
                if hasattr(self, 'update_face_features_display'):
                    self.update_face_features_display()
        
        self.after(100, update_landmarks_after_reset)
    
    
    def save_png(self):
        """편집된 이미지를 PNG 파일로 저장"""
        if self.edited_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            png_filename = f"{base_name}_edited.png"
            
            # 저장 폴더 경로 결정
            if self.face_edit_dir and os.path.exists(self.face_edit_dir):
                save_dir = self.face_edit_dir
            else:
                save_dir = os.path.dirname(self.current_image_path)
            
            # 파일 경로
            file_path = os.path.join(save_dir, png_filename)
            
            # PNG로 저장
            self.edited_image.save(file_path, "PNG")
            
            self.status_label.config(
                text=f"저장 완료: {png_filename}",
                fg="green"
            )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    