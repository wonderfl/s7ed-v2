"""
캔버스 이벤트 처리 기능 Mixin
이미지 확대/축소, 이동, 마우스 휠 등의 이벤트 처리
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
        
        # 확대 비율 계산
        zoom_factor = getattr(self, 'zoom_factor', 1.2)
        new_scale = min(old_scale * zoom_factor, max_scale)
        
        # 새로운 표시 크기
        new_display_width = int(preview_width * new_scale)
        new_display_height = int(preview_height * new_scale)
        
        # 마우스 위치를 중심으로 확대 (캔버스 좌표계)
        canvas_width = self.canvas_original.winfo_width()
        canvas_height = self.canvas_original.winfo_height()
        
        # 마우스 위치에 해당하는 이미지 내부 좌표 계산
        if old_display_width > 0 and old_display_height > 0:
            mouse_img_x = (mouse_x - old_img_x) / old_display_width * preview_width
            mouse_img_y = (mouse_y - old_img_y) / old_display_height * preview_height
        else:
            mouse_img_x = preview_width / 2
            mouse_img_y = preview_height / 2
        
        # 새로운 이미지 위치 계산 (마우스 위치를 중심으로)
        new_img_x = mouse_x - mouse_img_x * new_scale
        new_img_y = mouse_y - mouse_img_y * new_scale
        
        # 새로운 위치와 스케일 적용
        self.zoom_scale_original = new_scale
        self.zoom_scale_edited = new_scale
        self.zoom_scale_original = new_scale
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
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
        
        # 축소 비율 계산
        zoom_factor = getattr(self, 'zoom_factor', 1.2)
        new_scale = max(old_scale / zoom_factor, min_scale)
        
        # 새로운 표시 크기
        new_display_width = int(preview_width * new_scale)
        new_display_height = int(preview_height * new_scale)
        
        # 마우스 위치를 중심으로 축소 (캔버스 좌표계)
        canvas_width = self.canvas_original.winfo_width()
        canvas_height = self.canvas_original.winfo_height()
        
        # 마우스 위치에 해당하는 이미지 내부 좌표 계산
        if old_display_width > 0 and old_display_height > 0:
            mouse_img_x = (mouse_x - old_img_x) / old_display_width * preview_width
            mouse_img_y = (mouse_y - old_img_y) / old_display_height * preview_height
        else:
            mouse_img_x = preview_width / 2
            mouse_img_y = preview_height / 2
        
        # 새로운 이미지 위치 계산 (마우스 위치를 중심으로)
        new_img_x = mouse_x - mouse_img_x * new_scale
        new_img_y = mouse_y - mouse_img_y * new_scale
        
        # 새로운 위치와 스케일 적용 (양쪽 동기화)
        self.zoom_scale_original = new_scale
        self.zoom_scale_edited = new_scale
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_reset_original(self):
        """원본 이미지 원래대로"""
        if self.current_image is None:
            return
        
        # 원래 크기로 리셋
        self.zoom_scale_original = 1.0
        self.zoom_scale_edited = 1.0
        self.canvas_original_pos_x = 0
        self.canvas_original_pos_y = 0
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_original_preview()
        # 편집된 이미지도 동일하게 리셋
        self.show_edited_preview()
        
        # 리셋 완료 후 랜드마크 다시 그리기 (지연 처리)
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
        self.after(100, update_landmarks_after_reset)
    
    def zoom_in_edited(self, mouse_x=None, mouse_y=None):
        """편집된 이미지 확대 (마우스 위치를 중심으로)"""
        if self.edited_image is None:
            return
        
        # 확대 제한
        max_scale = getattr(self, 'zoom_max_scale', 8.0)  # 최대 확대 비율
        if self.zoom_scale_edited >= max_scale:
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
        old_scale = self.zoom_scale_edited
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 확대 비율 계산
        zoom_factor = getattr(self, 'zoom_factor', 1.2)
        new_scale = min(old_scale * zoom_factor, max_scale)
        
        # 새로운 표시 크기
        new_display_width = int(preview_width * new_scale)
        new_display_height = int(preview_height * new_scale)
        
        # 마우스 위치를 중심으로 확대 (캔버스 좌표계)
        canvas_width = self.canvas_edited.winfo_width()
        canvas_height = self.canvas_edited.winfo_height()
        
        # 마우스 위치에 해당하는 이미지 내부 좌표 계산
        if old_display_width > 0 and old_display_height > 0:
            mouse_img_x = (mouse_x - old_img_x) / old_display_width * preview_width
            mouse_img_y = (mouse_y - old_img_y) / old_display_height * preview_height
        else:
            mouse_img_x = preview_width / 2
            mouse_img_y = preview_height / 2
        
        # 새로운 이미지 위치 계산 (마우스 위치를 중심으로)
        new_img_x = mouse_x - mouse_img_x * new_scale
        new_img_y = mouse_y - mouse_img_y * new_scale
        
        # 새로운 위치와 스케일 적용
        self.zoom_scale_edited = new_scale
        self.zoom_scale_original = new_scale
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        self.canvas_original_pos_x = new_img_x
        self.canvas_original_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_edited_preview()
        # 원본 이미지도 동일하게 확대/축소 및 위치 동기화
        self.show_original_preview()
        
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_out_edited(self, mouse_x=None, mouse_y=None):
        """편집된 이미지 축소 (마우스 위치를 중심으로)"""
        if self.edited_image is None:
            return
        
        # 축소 제한
        min_scale = getattr(self, 'zoom_min_scale', 0.2)  # 최소 축소 비율
        if self.zoom_scale_edited <= min_scale:
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
        old_scale = self.zoom_scale_edited
        
        # 이미지 표시 크기 계산
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        old_display_width = int(preview_width * old_scale)
        old_display_height = int(preview_height * old_scale)
        
        # 축소 비율 계산
        zoom_factor = getattr(self, 'zoom_factor', 1.2)
        new_scale = max(old_scale / zoom_factor, min_scale)
        
        # 새로운 표시 크기
        new_display_width = int(preview_width * new_scale)
        new_display_height = int(preview_height * new_scale)
        
        # 마우스 위치를 중심으로 축소 (캔버스 좌표계)
        canvas_width = self.canvas_edited.winfo_width()
        canvas_height = self.canvas_edited.winfo_height()
        
        # 마우스 위치에 해당하는 이미지 내부 좌표 계산
        if old_display_width > 0 and old_display_height > 0:
            mouse_img_x = (mouse_x - old_img_x) / old_display_width * preview_width
            mouse_img_y = (mouse_y - old_img_y) / old_display_height * preview_height
        else:
            mouse_img_x = preview_width / 2
            mouse_img_y = preview_height / 2
        
        # 새로운 이미지 위치 계산 (마우스 위치를 중심으로)
        new_img_x = mouse_x - mouse_img_x * new_scale
        new_img_y = mouse_y - mouse_img_y * new_scale
        
        # 새로운 위치와 스케일 적용 (양쪽 동기화)
        self.zoom_scale_edited = new_scale
        self.zoom_scale_original = new_scale
        self.canvas_edited_pos_x = new_img_x
        self.canvas_edited_pos_y = new_img_y
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_edited_preview()
        # 원본 이미지도 동일하게 확대/축소 및 위치 동기화
        self.show_original_preview()
        
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
        self.after(100, update_landmarks_after_zoom)
    
    def zoom_reset_edited(self):
        """편집된 이미지 원래대로"""
        if self.edited_image is None:
            return
        
        # 원래 크기로 리셋
        self.zoom_scale_edited = 1.0
        self.zoom_scale_original = 1.0
        self.canvas_edited_pos_x = 0
        self.canvas_edited_pos_y = 0
        self.canvas_original_pos_x = 0
        self.canvas_original_pos_y = 0
        
        # 확대/축소 중 플래그 설정 (랜드마크 업데이트 지연)
        self._is_zooming = True
        
        self.show_edited_preview()
        # 원본 이미지도 동일하게 리셋
        self.show_original_preview()
        
        # 리셋 완료 후 랜드마크 다시 그리기 (지연 처리)
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
            
            # 지시선 업데이트
            if hasattr(self, 'update_guide_lines'):
                self.update_guide_lines()
        
        self.after(100, update_landmarks_after_reset)
    
    def save_png(self):
        """편집된 이미지를 PNG 파일로 저장"""
        if self.edited_image is None:
            messagebox.showwarning("경고", "편집된 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 기반으로 저장 파일명 생성
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            png_filename = f"{base_name}_edited.png"
            
            # 저장 디렉토리 설정
            if hasattr(self, 'face_edit_dir') and self.face_edit_dir and os.path.exists(self.face_edit_dir):
                save_dir = self.face_edit_dir
            else:
                save_dir = os.path.dirname(self.current_image_path)
            
            # 파일 경로 생성
            file_path = os.path.join(save_dir, png_filename)
            
            # PNG로 저장
            self.edited_image.save(file_path, "PNG")
            
            if hasattr(self, 'status_label'):
                self.status_label.config(
                    text=f"저장 완료: {png_filename}",
                    fg="green"
                )
            
            messagebox.showinfo("성공", f"이미지가 저장되었습니다:\n{file_path}")
            
        except Exception as e:
            if hasattr(self, 'status_label'):
                self.status_label.config(
                    text=f"저장 실패: {str(e)}",
                    fg="red"
                )
            messagebox.showerror("오류", f"이미지 저장 실패:\n{str(e)}")
