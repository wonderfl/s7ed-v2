"""
얼굴 추출 패널 - 캔버스 이벤트 Mixin
캔버스 마우스 이벤트 처리 관련 기능을 담당
"""
import tkinter as tk


class CanvasEventHandlerMixin:
    """캔버스 이벤트 처리 기능 Mixin"""
    
    def on_canvas_click(self, event):
        """Canvas 클릭 이벤트 (드래그 시작)"""
        if not self.use_manual_region.get():
            return
        
        if self.crop_rect_original is None:
            return
        
        # 클릭한 위치가 테두리 사각형 내부인지 확인
        x, y = event.x, event.y
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) >= 4:
            rect_x1, rect_y1, rect_x2, rect_y2 = coords[0], coords[1], coords[2], coords[3]
            if rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2:
                self.is_dragging = True
                self.drag_start_x = x
                self.drag_start_y = y
                
                # 현재 수동 영역 좌표 저장
                try:
                    self.drag_original_x = int(self.manual_x.get())
                    self.drag_original_y = int(self.manual_y.get())
                except (ValueError, tk.TclError):
                    self.is_dragging = False
    
    def on_canvas_drag(self, event):
        """Canvas 드래그 이벤트"""
        if not self.is_dragging or not self.use_manual_region.get():
            return
        
        if self.crop_rect_original is None or self.current_image is None:
            return
        
        # 드래그 거리 계산
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # 테두리 사각형 이동
        self.canvas_original.move(self.crop_rect_original, dx, dy)
        
        # 실제 크롭 영역 테두리도 함께 이동
        if self.actual_crop_rect_original:
            self.canvas_original.move(self.actual_crop_rect_original, dx, dy)
        
        # 다음 드래그를 위해 시작 위치 업데이트
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # 드래그 중에도 수동 영역 좌표 업데이트 및 재계산 (성능을 위해 제한)
        # Canvas 좌표를 원본 이미지 좌표로 변환
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) >= 4:
            rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas = coords[0], coords[1], coords[2], coords[3]
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            
            # 96x120 비율로 크롭된 미리보기 영역 계산
            target_ratio = 96 / 120  # 0.8
            if img_width / img_height > target_ratio:
                preview_crop_height = img_height
                preview_crop_width = int(preview_crop_height * target_ratio)
            else:
                preview_crop_width = img_width
                preview_crop_height = int(preview_crop_width / target_ratio)
            
            # 미리보기 크기 (288x360)
            preview_width = 288
            preview_height = 360
            
            # Canvas 좌표를 미리보기 좌표로 변환
            canvas_center_x = 144  # 288 / 2
            canvas_center_y = 180  # 360 / 2
            
            rect_x1_preview = rect_x1_canvas - (canvas_center_x - preview_width // 2)
            rect_y1_preview = rect_y1_canvas - (canvas_center_y - preview_height // 2)
            
            # 미리보기 좌표를 원본 이미지 좌표로 변환
            scale_x = preview_width / preview_crop_width
            scale_y = preview_height / preview_crop_height
            
            new_x = int(rect_x1_preview / scale_x)
            new_y = int(rect_y1_preview / scale_y)
            
            # 수동 영역 크기 가져오기
            try:
                crop_w = int(self.manual_w.get())
                crop_h = int(self.manual_h.get())
            except (ValueError, tk.TclError):
                return
            
            # 경계 내로 제한
            new_x = max(0, min(new_x, preview_crop_width - crop_w))
            new_y = max(0, min(new_y, preview_crop_height - crop_h))
            
            # 수동 영역 입력 필드 업데이트
            self.manual_x.set(new_x)
            self.manual_y.set(new_y)
            
            # 드래그 중에는 재계산하지 않고, 드래그 종료 시에만 재계산
            # (성능 문제 방지)
    
    def on_canvas_release(self, event):
        """Canvas 드래그 종료 이벤트"""
        if not self.is_dragging:
            return
        
        self.is_dragging = False
        
        if self.crop_rect_original is None or self.current_image is None:
            return
        
        # Canvas 좌표를 원본 이미지 좌표로 변환
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) < 4:
            return
        
        rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas = coords[0], coords[1], coords[2], coords[3]
        
        # 원본 이미지 크기
        img_width, img_height = self.current_image.size
        
        # 96x120 비율로 크롭된 미리보기 영역 계산
        target_ratio = 96 / 120  # 0.8
        if img_width / img_height > target_ratio:
            preview_crop_height = img_height
            preview_crop_width = int(preview_crop_height * target_ratio)
        else:
            preview_crop_width = img_width
            preview_crop_height = int(preview_crop_width / target_ratio)
        
        # 미리보기 크기 (288x360)
        preview_width = 288
        preview_height = 360
        
        # Canvas 좌표를 미리보기 좌표로 변환
        canvas_center_x = 144  # 288 / 2
        canvas_center_y = 180  # 360 / 2
        
        rect_x1_preview = rect_x1_canvas - (canvas_center_x - preview_width // 2)
        rect_y1_preview = rect_y1_canvas - (canvas_center_y - preview_height // 2)
        
        # 미리보기 좌표를 원본 이미지 좌표로 변환
        scale_x = preview_width / preview_crop_width
        scale_y = preview_height / preview_crop_height
        
        new_x = int(rect_x1_preview / scale_x)
        new_y = int(rect_y1_preview / scale_y)
        
        # 수동 영역 크기 가져오기
        try:
            crop_w = int(self.manual_w.get())
            crop_h = int(self.manual_h.get())
        except (ValueError, tk.TclError):
            return
        
        # 경계 내로 제한
        new_x = max(0, min(new_x, preview_crop_width - crop_w))
        new_y = max(0, min(new_y, preview_crop_height - crop_h))
        
        # 경계 체크
        try:
            crop_w = int(self.manual_w.get())
            crop_h = int(self.manual_h.get())
        except (ValueError, tk.TclError):
            return
        
        # 경계 내로 제한
        new_x = max(0, min(new_x, preview_crop_width - crop_w))
        new_y = max(0, min(new_y, preview_crop_height - crop_h))
        
        # 수동 영역 입력 필드 업데이트
        self.manual_x.set(new_x)
        self.manual_y.set(new_y)
        
        # 테두리 다시 그리기 (경계 조정 반영)
        self.draw_crop_region_on_original()
        
        # 자동으로 재추출 (화면 비율도 재계산됨)
        # 수동 영역 좌표가 업데이트된 후 extract_face() 호출
        if self.current_image is not None:
            # 수동 영역 변경을 강제로 반영하기 위해 extract_face() 직접 호출
            self.extract_face()
            
            # UI 강제 업데이트 (extract_face()에서 업데이트되지만 확실히 하기 위해)
            self.update_idletasks()
            
            # 화면 비율 UI 강제 업데이트 (extract_face()에서 업데이트되지만 확실히 하기 위해)
            # 크롭된 이미지가 업데이트된 후에 재계산
            if hasattr(self, 'face_percentage_label') and self.detected_face_region is not None and self.extracted_image is not None:
                crop_scale = self.crop_scale.get()
                offset_x = self.center_offset_x.get()
                offset_y = self.center_offset_y.get()
                face_percentage = self._calculate_face_percentage(self.detected_face_region, crop_scale, offset_x, offset_y, self.extracted_image)
                self.face_percentage_label.config(text=f"{face_percentage:.1f}%")
                self.face_percentage_label.update_idletasks()
