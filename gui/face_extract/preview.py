"""
얼굴 추출 패널 - 미리보기 관리 Mixin
이미지 미리보기 표시 및 캐싱 관련 기능을 담당
"""
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import utils.image_adjustments as image_adjustments


class PreviewManagerMixin:
    """미리보기 관리 기능 Mixin"""
    
    def show_extracted_original(self):
        """추출 원본 이미지 미리보기 표시 (조정 없음)"""
        if self.extracted_image is None:
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
                self.image_created_extracted_original = None
            # 얼굴 중심점 마커도 삭제
            if self.face_center_marker_extracted:
                try:
                    for marker_id in self.face_center_marker_extracted:
                        self.canvas_extracted_original.delete(marker_id)
                except:
                    pass
                self.face_center_marker_extracted = None
            return
        
        try:
            # 이미지 복사
            display_img = self.extracted_image.copy()
            
            # RGB 모드로 변환
            if display_img.mode != 'RGB':
                if display_img.mode == 'RGBA':
                    background = Image.new('RGB', display_img.size, (0, 0, 0))
                    background.paste(display_img, mask=display_img.split()[3])
                    display_img = background
                else:
                    display_img = display_img.convert('RGB')
            
            # 이미지 리사이즈 (288x360)
            preview_size = (288, 360)
            resized = display_img.resize(preview_size, Image.LANCZOS)
        
        # PhotoImage로 변환
            self.tk_image_extracted_original = ImageTk.PhotoImage(resized)
        
        # Canvas에 표시
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
            
            self.image_created_extracted_original = self.canvas_extracted_original.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_extracted_original
            )
            
            # 3x3 격자 그리기
            self.draw_grid_extracted()
            
            # 얼굴 중심점 표시
            self.draw_face_center_marker()
        except Exception as e:
            print(f"[얼굴추출] 추출 원본 이미지 미리보기 표시 실패: {e}")
    
    def show_extracted_adjusted(self):
        """추출 조정 이미지 미리보기 표시 (모든 조정 적용)"""
        if self.extracted_image is None:
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
                self.image_created_extracted_adjusted = None
            self._adjusted_image_cache = None  # 캐시 무효화
            return
        
        try:
            # 조정값 해시 계산
            current_hash = self._get_adjustments_hash()
            
            # 캐시 확인
            if (self._adjusted_image_cache is not None and 
                self._adjusted_image_cache.get('hash') == current_hash):
                # 캐시 히트: 캐시된 이미지 사용
                result = self._adjusted_image_cache['image']
            else:
                # 캐시 미스: 이미지 조정 파이프라인 적용
                adjustments = self._get_adjustment_values()
                result = image_adjustments.process_image_pipeline(
                    self.extracted_image.copy(),
                    adjustments,
                    resize_after=(288, 360)  # Sharpness 전에 리사이즈
                )
                # 캐시 업데이트
                self._adjusted_image_cache = {
                    'hash': current_hash,
                    'image': result
                }
            
            # PhotoImage로 변환
            self.tk_image_extracted_adjusted = ImageTk.PhotoImage(result)
            
            # Canvas에 표시
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
            
            self.image_created_extracted_adjusted = self.canvas_extracted_adjusted.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_extracted_adjusted
            )
        except Exception as e:
            print(f"[얼굴추출] 추출 조정 이미지 미리보기 표시 실패: {e}")
    
    def draw_grid_extracted(self):
        """추출 원본 이미지에 3x3 격자 그리기"""
        # 기존 격자선 삭제
        for line_id in self.grid_lines_extracted:
            try:
                self.canvas_extracted_original.delete(line_id)
            except:
                pass
        self.grid_lines_extracted.clear()
        
        if self.image_created_extracted_original is None or self.tk_image_extracted_original is None:
            return
        
        # 실제 이미지 크기 가져오기 (288x360)
        img_width = 288
        img_height = 360
        
        # 이미지 중심 위치
        center_x = 144  # 288 / 2
        center_y = 180  # 360 / 2
        
        # 이미지 시작 위치 (좌상단)
        start_x = center_x - img_width // 2
        start_y = center_y - img_height // 2
        
        # 격자선 색상
        grid_color = "white"
        grid_width = 1
        
        # 수직선 2개 (이미지 너비를 3등분)
        for i in range(1, 3):
            x = start_x + (img_width * i // 3)
            line_id = self.canvas_extracted_original.create_line(
                x, start_y,
                x, start_y + img_height,
                fill=grid_color,
                width=grid_width,
                tags="grid"
            )
            self.grid_lines_extracted.append(line_id)
        
        # 수평선 2개 (이미지 높이를 3등분)
        for i in range(1, 3):
            y = start_y + (img_height * i // 3)
            line_id = self.canvas_extracted_original.create_line(
                start_x, y,
                start_x + img_width, y,
                fill=grid_color,
                width=grid_width,
                tags="grid"
            )
            self.grid_lines_extracted.append(line_id)
    
    def draw_face_center_marker(self):
        """추출 원본 이미지에 얼굴 중심점 표시"""
        # 기존 마커 삭제 (tags를 사용하여 한 번에 삭제)
        self.canvas_extracted_original.delete("face_center")
        self.face_center_marker_extracted = None
        
        if self.extracted_image is None or self.image_created_extracted_original is None:
            return
        
        try:
            # 얼굴 중심점 계산
            face_center_x = None
            face_center_y = None
            
            # MediaPipe 랜드마크가 있으면 사용
            if self.detected_key_landmarks and self.detected_key_landmarks.get('face_center'):
                # 원본 이미지의 얼굴 중심점
                orig_face_center = self.detected_key_landmarks['face_center']
                orig_face_center_x, orig_face_center_y = orig_face_center
                
                # 원본 이미지 크기
                orig_width, orig_height = self.current_image.size
                
                # 추출된 이미지 크기 (96x120)
                extracted_width, extracted_height = self.extracted_image.size
                
                # 크롭 시작 좌표 계산 (extract_face_region 로직과 동일하게)
                crop_scale = self.crop_scale.get()
                offset_x = self.center_offset_x.get()
                offset_y = self.center_offset_y.get()
                
                if self.detected_face_region:
                    x, y, w, h = self.detected_face_region
                    detected_face_center_x = x + w // 2
                    detected_face_center_y = y + h // 2
                    
                    crop_center_x = detected_face_center_x + offset_x
                    crop_center_y = detected_face_center_y + offset_y
                    
                    target_ratio = 96 / 120
                    if w / h > target_ratio:
                        crop_height = int(h * crop_scale)
                        crop_width = int(crop_height * target_ratio)
                    else:
                        crop_width = int(w * crop_scale)
                        crop_height = int(crop_width / target_ratio)
                    
                    x_start = max(0, min(crop_center_x - crop_width // 2, orig_width - crop_width))
                    y_start = max(0, min(crop_center_y - crop_height // 2, orig_height - crop_height))
                    
                    # 원본 이미지의 얼굴 중심점을 추출된 이미지 좌표로 변환
                    face_center_x = orig_face_center_x - x_start
                    face_center_y = orig_face_center_y - y_start
                    
                    # 추출된 이미지 범위 내에 있는지 확인
                    if 0 <= face_center_x < extracted_width and 0 <= face_center_y < extracted_height:
                        # 미리보기 좌표로 변환 (96x120 -> 288x360)
                        scale_x = 288 / extracted_width
                        scale_y = 360 / extracted_height
                        
                        preview_x = face_center_x * scale_x
                        preview_y = face_center_y * scale_y
                        
                        # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
                        canvas_center_x = 144  # 288 / 2
                        canvas_center_y = 180  # 360 / 2
                        
                        marker_x = canvas_center_x - 288 // 2 + preview_x
                        marker_y = canvas_center_y - 360 // 2 + preview_y
                        
                        # 십자가 모양으로 표시 (노란색)
                        cross_size = 10
                        # 수평선
                        line1 = self.canvas_extracted_original.create_line(
                            marker_x - cross_size, marker_y,
                            marker_x + cross_size, marker_y,
                            fill="yellow", width=2, tags="face_center"
                        )
                        # 수직선
                        line2 = self.canvas_extracted_original.create_line(
                            marker_x, marker_y - cross_size,
                            marker_x, marker_y + cross_size,
                            fill="yellow", width=2, tags="face_center"
                        )
                        # 마커 ID 저장 (나중에 삭제하기 위해)
                        self.face_center_marker_extracted = (line1, line2)
            
        except Exception as e:
            print(f"[얼굴추출] 얼굴 중심점 표시 실패: {e}")
    
    def update_palette_preview(self):
        """팔레트 적용 이미지 계산 및 미리보기 업데이트"""
        if self.extracted_image is None:
            # 팔레트 미리보기 초기화
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
            self.palette_applied_image = None
            self._palette_image_cache = None  # 캐시 무효화
            return
        
        try:
            # 팔레트 적용 여부 확인
            if not self.use_palette.get():
                # 팔레트 미적용 시 추출된 이미지 그대로 사용
                self.palette_applied_image = None
                # 미리보기 초기화
                if self.image_created_palette:
                    self.canvas_palette.delete(self.image_created_palette)
                    self.image_created_palette = None
                self._palette_image_cache = None  # 캐시 무효화
                return
            
            # 팔레트 설정 해시 계산
            current_hash = self._get_palette_settings_hash()
            
            # 캐시 확인
            if (self._palette_image_cache is not None and 
                self._palette_image_cache.get('hash') == current_hash):
                # 캐시 히트: 캐시된 이미지 사용
                self.palette_applied_image = self._palette_image_cache['image']
            else:
                # 캐시 미스: 팔레트 변환 수행
                # 변환 방법 가져오기
                method = self.palette_method.get()
                dither = (method == 'dither')
                
                # 1단계: 이미지 전처리 (팔레트 적용 전)
                adjustments = self._get_adjustment_values()
                processed_img = image_adjustments.process_image_pipeline(
                    self.extracted_image.copy(),
                    adjustments,
                    resize_before=(kaodata_image.FACE_WIDTH, kaodata_image.FACE_HEIGHT)  # Equalize 후 리사이즈
                )
                
                # 2단계: 마지막에 팔레트 적용
                self.palette_applied_image = kaodata_image.convert_to_palette_colors(
                    processed_img,
                    palette=kaodata_image.FACE_PALETTE,
                    method=method,
                    dither=dither
                )
                
                # 캐시 업데이트
                self._palette_image_cache = {
                    'hash': current_hash,
                    'image': self.palette_applied_image
                }
            
            # 미리보기 표시
            self.show_palette_preview()
            
        except Exception as e:
            print(f"[얼굴추출] 팔레트 적용 실패: {e}")
            self.palette_applied_image = None
            self._palette_image_cache = None  # 캐시 무효화
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
    
    def show_palette_preview(self):
        """팔레트 적용 이미지 미리보기 표시 (96x120 크기로 확대)"""
        if self.palette_applied_image is None:
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
            return
        
        try:
            # 팔레트 모드 이미지를 RGB로 변환하여 표시
            # (PIL의 PhotoImage는 P 모드를 직접 지원하지 않을 수 있음)
            if self.palette_applied_image.mode == 'P':
                # 팔레트 모드를 RGB로 변환 (팔레트 색상이 제대로 적용되도록)
                preview_img = self.palette_applied_image.convert('RGB')
            else:
                preview_img = self.palette_applied_image
            
            # 이미지가 96x120인지 확인하고, 미리보기 크기로 확대
            # 팔레트 적용 이미지는 이미 96x120으로 리사이즈되어 있음
            # 미리보기 크기로 확대 표시
            # 이미지가 96x120인지 확인하고, 미리보기 크기로 확대 (288x360)
            preview_size = (288, 360)
            resized = preview_img.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_palette = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
            
            self.image_created_palette = self.canvas_palette.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_palette
            )
        except Exception as e:
            print(f"[얼굴추출] 팔레트 미리보기 표시 실패: {e}")
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
    
    def show_original_preview(self):
        """원본 이미지를 96x120 비율로 최대 크롭해서 미리보기 표시 (0,0 기준)"""
        if self.current_image is None:
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            if self.crop_rect_original:
                self.canvas_original.delete(self.crop_rect_original)
                self.crop_rect_original = None
            if self.actual_crop_rect_original:
                self.canvas_original.delete(self.actual_crop_rect_original)
                self.actual_crop_rect_original = None
            # 캐시 무효화
            self._original_preview_cache = None
            self._landmarks_adjusted_cache = None
            return
        
        try:
            # 원본 미리보기 해시 계산
            current_hash = self._get_original_preview_hash()
            
            # 캐시 확인
            if (current_hash is not None and 
                self._original_preview_cache is not None and 
                self._original_preview_cache.get('hash') == current_hash):
                # 캐시 히트: 캐시된 이미지 사용
                cropped = self._original_preview_cache['image']
            else:
                # 캐시 미스: 크롭 수행
                # 96x120 비율 (0.8)
                target_ratio = 96 / 120  # 0.8
                
                # 원본 이미지 크기
                img_width, img_height = self.current_image.size
                img_ratio = img_width / img_height
                
                # 96x120 비율에 맞춰서 최대 크롭 (0,0 기준)
                if img_ratio > target_ratio:
                    # 이미지가 더 넓음 -> 높이를 기준으로 크롭
                    crop_height = img_height
                    crop_width = int(crop_height * target_ratio)
                else:
                    # 이미지가 더 높음 -> 너비를 기준으로 크롭
                    crop_width = img_width
                    crop_height = int(crop_width / target_ratio)
                
                # 0,0 기준으로 크롭
                x_start = 0
                y_start = 0
                x_end = min(crop_width, img_width)
                y_end = min(crop_height, img_height)
                
                # 크롭
                cropped = self.current_image.crop((x_start, y_start, x_end, y_end))
                
                # 캐시 업데이트
                if current_hash is not None:
                    self._original_preview_cache = {
                        'hash': current_hash,
                        'image': cropped
                    }
            
            # 랜드마크 표시 옵션이 켜져 있고 랜드마크가 있으면 그리기
            if self.show_landmarks.get() and self.detected_landmarks is not None:
                try:
                    from utils.face_landmarks import draw_landmarks
                    
                    # 랜드마크 좌표 조정 캐시 확인
                    landmarks_hash = self._get_landmarks_adjusted_hash()
                    if (landmarks_hash is not None and 
                        self._landmarks_adjusted_cache is not None and 
                        self._landmarks_adjusted_cache.get('hash') == landmarks_hash):
                        # 캐시 히트: 캐시된 좌표 사용
                        adjusted_landmarks = self._landmarks_adjusted_cache.get('landmarks', [])
                        adjusted_key_landmarks = self._landmarks_adjusted_cache.get('key_landmarks')
                    else:
                        # 캐시 미스: 좌표 조정 수행
                        # 크롭 영역 계산 (캐시에서 가져오거나 재계산)
                        target_ratio = 96 / 120
                        img_width, img_height = self.current_image.size
                        img_ratio = img_width / img_height
                        if img_ratio > target_ratio:
                            crop_height = img_height
                            crop_width = int(crop_height * target_ratio)
                        else:
                            crop_width = img_width
                            crop_height = int(crop_width / target_ratio)
                        x_start = 0
                        y_start = 0
                        
                        # 랜드마크 좌표를 크롭된 영역에 맞게 조정
                        adjusted_landmarks = []
                        for x, y in self.detected_landmarks:
                            # 크롭 영역 기준으로 좌표 조정
                            adjusted_x = x - x_start
                            adjusted_y = y - y_start
                            adjusted_landmarks.append((adjusted_x, adjusted_y))
                        
                        # 주요 랜드마크도 조정
                        adjusted_key_landmarks = None
                        if self.detected_key_landmarks:
                            adjusted_key_landmarks = {}
                            for key, value in self.detected_key_landmarks.items():
                                if value:
                                    x, y = value
                                    adjusted_key_landmarks[key] = (x - x_start, y - y_start)
                                else:
                                    adjusted_key_landmarks[key] = None
                        
                        # 캐시 업데이트 (랜드마크와 주요 랜드마크 모두 포함)
                        if landmarks_hash is not None:
                            self._landmarks_adjusted_cache = {
                                'hash': landmarks_hash,
                                'landmarks': adjusted_landmarks,
                                'key_landmarks': adjusted_key_landmarks
                            }
                    
                    # 랜드마크 그리기
                    cropped = draw_landmarks(
                        cropped, 
                        adjusted_landmarks, 
                        adjusted_key_landmarks,
                        show_all_points=False
                    )
                except Exception as e:
                    print(f"[얼굴추출] 랜드마크 그리기 실패: {e}")
            
            # 이미지 리사이즈 (미리보기용, 288x360)
            preview_size = (288, 360)
            resized = cropped.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_original = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
            
            self.image_created_original = self.canvas_original.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_original
            )
            
            # 크롭 영역 테두리 그리기
            self.draw_crop_region_on_original()
            
        except Exception as e:
            print(f"[얼굴추출] 원본 이미지 표시 실패: {e}")
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            if self.crop_rect_original:
                self.canvas_original.delete(self.crop_rect_original)
                self.crop_rect_original = None
    
    def draw_crop_region_on_original(self):
        """원본 이미지 미리보기에 크롭 영역을 테두리로 표시"""
        # 기존 테두리 제거
        if self.crop_rect_original:
            self.canvas_original.delete(self.crop_rect_original)
            self.crop_rect_original = None
        
        if self.current_image is None:
            return
        
        # 크롭 영역 좌표 가져오기
        crop_x, crop_y, crop_w, crop_h = None, None, None, None
        
        if self.use_manual_region.get():
            # 수동 영역 사용
            try:
                crop_x = int(self.manual_x.get())
                crop_y = int(self.manual_y.get())
                crop_w = int(self.manual_w.get())
                crop_h = int(self.manual_h.get())
            except (ValueError, tk.TclError):
                return
        elif self.detected_face_region is not None:
            # 감지된 영역 사용
            crop_x, crop_y, crop_w, crop_h = self.detected_face_region
        
        if crop_x is None or crop_y is None or crop_w is None or crop_h is None:
            return
        
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
        
        # 크롭 영역이 미리보기 영역 내에 있는지 확인
        if crop_x < 0 or crop_y < 0 or crop_x + crop_w > preview_crop_width or crop_y + crop_h > preview_crop_height:
            # 크롭 영역이 미리보기 영역을 벗어남
            return
        
        # 미리보기 크기 (288x360)
        preview_width = 288
        preview_height = 360
        
        # 크롭 영역 좌표를 미리보기 좌표로 변환
        scale_x = preview_width / preview_crop_width
        scale_y = preview_height / preview_crop_height
        
        rect_x1 = crop_x * scale_x
        rect_y1 = crop_y * scale_y
        rect_x2 = (crop_x + crop_w) * scale_x
        rect_y2 = (crop_y + crop_h) * scale_y
        
        # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
        canvas_center_x = 144  # 288 / 2
        canvas_center_y = 180  # 360 / 2
        
        rect_x1_canvas = canvas_center_x - preview_width // 2 + rect_x1
        rect_y1_canvas = canvas_center_y - preview_height // 2 + rect_y1
        rect_x2_canvas = canvas_center_x - preview_width // 2 + rect_x2
        rect_y2_canvas = canvas_center_y - preview_height // 2 + rect_y2
        
        # 얼굴/수동 영역 테두리 그리기 (빨간색, 두께 2)
        # 수동 영역 모드일 때는 태그를 추가하여 드래그 가능하게 함
        import tkinter as tk
        tags = ("draggable",) if self.use_manual_region.get() else ()
        self.crop_rect_original = self.canvas_original.create_rectangle(
            rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas,
            outline="red", width=2, tags=tags
        )
        
        # 실제 크롭 영역 계산 및 표시
        self.draw_actual_crop_region(crop_x, crop_y, crop_w, crop_h, preview_crop_width, preview_crop_height)
    
    def draw_actual_crop_region(self, face_x, face_y, face_w, face_h, preview_crop_width, preview_crop_height):
        """실제 크롭 영역을 계산하고 테두리로 표시"""
        # 기존 테두리 제거
        if self.actual_crop_rect_original:
            self.canvas_original.delete(self.actual_crop_rect_original)
            self.actual_crop_rect_original = None
        
        if self.current_image is None:
            return
        
        try:
            # 현재 설정값 가져오기
            crop_scale = self.crop_scale.get()
            offset_x = self.center_offset_x.get()
            offset_y = self.center_offset_y.get()
            
            # 목표 비율 (96:120 = 0.8)
            target_ratio = 96 / 120  # 0.8
            
            # 얼굴 영역을 중심으로 96:120 비율로 크롭할 크기 계산
            if face_w / face_h > target_ratio:
                # 얼굴이 더 넓음 -> 높이를 기준으로 크롭
                crop_height = int(face_h * crop_scale)
                crop_width = int(crop_height * target_ratio)
            else:
                # 얼굴이 더 높음 -> 너비를 기준으로 크롭
                crop_width = int(face_w * crop_scale)
                crop_height = int(crop_width / target_ratio)
            
            # 96:120 비율 보장
            actual_ratio = crop_width / crop_height if crop_height > 0 else target_ratio
            if abs(actual_ratio - target_ratio) > 0.01:
                if face_w / face_h > target_ratio:
                    crop_width = int(crop_height * target_ratio)
                else:
                    crop_height = int(crop_width / target_ratio)
            
            # 감지된 얼굴 영역의 중심점 계산
            # extract_face_region과 동일한 로직 사용
            detected_face_center_x = face_x + face_w // 2
            detected_face_center_y = face_y + face_h // 2
            
            # 크롭 중심점 계산 (오프셋 적용)
            crop_center_x = detected_face_center_x + offset_x
            crop_center_y = detected_face_center_y + offset_y
            
            # 크롭 영역 좌표 계산
            actual_crop_x = crop_center_x - crop_width // 2
            actual_crop_y = crop_center_y - crop_height // 2
            actual_crop_x2 = actual_crop_x + crop_width
            actual_crop_y2 = actual_crop_y + crop_height
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            
            # 경계 조정
            if actual_crop_x < 0:
                actual_crop_x = 0
            if actual_crop_y < 0:
                actual_crop_y = 0
            if actual_crop_x2 > img_width:
                actual_crop_x2 = img_width
            if actual_crop_y2 > img_height:
                actual_crop_y2 = img_height
            
            # 크롭 영역이 미리보기 영역 내에 있는지 확인
            if actual_crop_x < 0 or actual_crop_y < 0 or actual_crop_x2 > preview_crop_width or actual_crop_y2 > preview_crop_height:
                # 크롭 영역이 미리보기 영역을 벗어남
                return
            
            # 미리보기 크기 (288x360)
            preview_width = 288
            preview_height = 360
            
            # 크롭 영역 좌표를 미리보기 좌표로 변환
            scale_x = preview_width / preview_crop_width
            scale_y = preview_height / preview_crop_height
            
            rect_x1 = actual_crop_x * scale_x
            rect_y1 = actual_crop_y * scale_y
            rect_x2 = actual_crop_x2 * scale_x
            rect_y2 = actual_crop_y2 * scale_y
            
            # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
            canvas_center_x = 144  # 288 / 2
            canvas_center_y = 180  # 360 / 2
            
            rect_x1_canvas = canvas_center_x - preview_width // 2 + rect_x1
            rect_y1_canvas = canvas_center_y - preview_height // 2 + rect_y1
            rect_x2_canvas = canvas_center_x - preview_width // 2 + rect_x2
            rect_y2_canvas = canvas_center_y - preview_height // 2 + rect_y2
            
            # 실제 크롭 영역 테두리 그리기 (파란색, 두께 2)
            self.actual_crop_rect_original = self.canvas_original.create_rectangle(
                rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas,
                outline="white", width=1
            )
        except Exception as e:
            print(f"[얼굴추출] 실제 크롭 영역 표시 실패: {e}")
