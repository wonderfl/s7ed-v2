"""
얼굴 편집 패널 - 캔버스 이벤트 처리 Mixin
드래그, 확대/축소 관련 기능을 담당
"""
import os
import tkinter as tk
from tkinter import messagebox


class CanvasEventHandlerMixin:
    """캔버스 이벤트 처리 기능 Mixin"""
    
    def on_canvas_original_drag_start(self, event):
        """원본 이미지 캔버스 드래그 시작"""
        if self.image_created_original is None:
            return
        
        # 드래그 시작 위치 저장 (마우스 클릭 위치)
        self.canvas_original_drag_start_x = event.x
        self.canvas_original_drag_start_y = event.y
        
        # 현재 이미지의 실제 위치를 캔버스에서 가져오기
        preview_width = 384
        preview_height = 480
        
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
                    preview_width = 480
                    preview_height = 600
                    self.canvas_original_drag_start_image_x = preview_width // 2
                    self.canvas_original_drag_start_image_y = preview_height // 2
            except Exception as e:
                print(f"[얼굴편집] 드래그 중 위치 가져오기 실패: {e}")
                preview_width = 384
                preview_height = 480
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
        except Exception as e:
            print(f"[얼굴편집] 원본 이미지 위치 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def on_canvas_original_drag_end(self, event):
        """원본 이미지 캔버스 드래그 종료"""
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
            except Exception as e:
                print(f"[얼굴편집] 드래그 종료 시 위치 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        self.canvas_original_drag_start_x = None
        self.canvas_original_drag_start_y = None
        self.canvas_original_drag_start_image_x = None
        self.canvas_original_drag_start_image_y = None
    
    def zoom_in_original(self):
        """원본 이미지 확대"""
        if self.current_image is None:
            return
        
        # 확대 제한 (최대 8배)
        if self.zoom_scale_original < 8.0:
            # 현재 이미지 위치 저장
            if self.image_created_original:
                try:
                    coords = self.canvas_original.coords(self.image_created_original)
                    if coords and len(coords) >= 2:
                        self.canvas_original_pos_x = coords[0]
                        self.canvas_original_pos_y = coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 확대 시 위치 저장 실패: {e}")
            
            self.zoom_scale_original = min(self.zoom_scale_original * 1.5, 8.0)
            self.show_original_preview()
            # 편집된 이미지도 동일하게 확대/축소 및 위치 동기화
            self.show_edited_preview()
    
    def zoom_out_original(self):
        """원본 이미지 축소"""
        if self.current_image is None:
            return
        
        # 축소 제한 (최소 0.2배)
        if self.zoom_scale_original > 0.2:
            # 현재 이미지 위치 저장
            if self.image_created_original:
                try:
                    coords = self.canvas_original.coords(self.image_created_original)
                    if coords and len(coords) >= 2:
                        self.canvas_original_pos_x = coords[0]
                        self.canvas_original_pos_y = coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 축소 시 위치 저장 실패: {e}")
            
            self.zoom_scale_original = max(self.zoom_scale_original / 1.5, 0.2)
            self.show_original_preview()
            # 편집된 이미지도 동일하게 확대/축소 및 위치 동기화
            self.show_edited_preview()
    
    def zoom_reset_original(self):
        """원본 이미지 확대/축소 초기화"""
        if self.current_image is None:
            return
        
        self.zoom_scale_original = 1.0
        # 위치를 중앙으로 초기화
        preview_width = 384
        preview_height = 480
        self.canvas_original_pos_x = preview_width // 2
        self.canvas_original_pos_y = preview_height // 2
        self.show_original_preview()
        # 편집된 이미지도 동일하게 초기화 및 위치 동기화
        self.show_edited_preview()
    
    def on_canvas_edited_drag_start(self, event):
        """편집된 이미지 캔버스 드래그 시작"""
        if self.image_created_edited is None:
            return
        
        # 드래그 시작 위치 저장 (마우스 클릭 위치)
        self.canvas_edited_drag_start_x = event.x
        self.canvas_edited_drag_start_y = event.y
        
        # 현재 이미지의 실제 위치를 캔버스에서 가져오기
        preview_width = 384
        preview_height = 480
        
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
                    preview_width = 480
                    preview_height = 600
                    self.canvas_edited_drag_start_image_x = preview_width // 2
                    self.canvas_edited_drag_start_image_y = preview_height // 2
            except Exception as e:
                print(f"[얼굴편집] 드래그 중 위치 가져오기 실패: {e}")
                preview_width = 384
                preview_height = 480
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
        except Exception as e:
            print(f"[얼굴편집] 편집된 이미지 위치 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def on_canvas_edited_drag_end(self, event):
        """편집된 이미지 캔버스 드래그 종료"""
        # 드래그 종료 시 현재 위치를 저장만 하고 경계 제한은 적용하지 않음
        # 사용자가 드래그한 위치를 그대로 유지
        if self.image_created_edited is not None:
            try:
                coords = self.canvas_edited.coords(self.image_created_edited)
                if coords and len(coords) >= 2:
                    # 현재 위치를 저장만 함 (경계 제한 없이)
                    self.canvas_edited_pos_x = coords[0]
                    self.canvas_edited_pos_y = coords[1]
            except Exception as e:
                print(f"[얼굴편집] 드래그 종료 시 위치 저장 실패: {e}")
                import traceback
                traceback.print_exc()
        
        self.canvas_edited_drag_start_x = None
        self.canvas_edited_drag_start_y = None
        self.canvas_edited_drag_start_image_x = None
        self.canvas_edited_drag_start_image_y = None
    
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
