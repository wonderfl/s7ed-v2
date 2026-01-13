"""
얼굴 편집 패널 - 미리보기 관리 Mixin
미리보기 표시 관련 기능을 담당
"""
import tkinter as tk
from PIL import Image, ImageTk

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


class PreviewManagerMixin:
    """미리보기 관리 기능 Mixin"""
    
    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""
        preview_frame = tk.LabelFrame(parent, text="미리보기", padx=5, pady=5)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 이미지 크기: 480x600
        preview_width = 480
        preview_height = 600
        
        # 좌측: 원본 이미지
        original_frame = tk.Frame(preview_frame)
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 2), pady=5)
        
        original_top_frame = tk.Frame(original_frame)
        original_top_frame.pack(fill=tk.X)
        
        self.label_original = tk.Label(original_top_frame, text="원본 이미지", font=("", 9))
        self.label_original.pack(side=tk.LEFT)
        
        # 확대/축소 버튼 프레임
        zoom_frame = tk.Frame(original_top_frame)
        zoom_frame.pack(side=tk.RIGHT)
        
        btn_zoom_in = tk.Button(zoom_frame, text="확대", command=self.zoom_in_original, width=6)
        btn_zoom_in.pack(side=tk.LEFT, padx=2)
        
        btn_zoom_out = tk.Button(zoom_frame, text="축소", command=self.zoom_out_original, width=6)
        btn_zoom_out.pack(side=tk.LEFT, padx=2)
        
        btn_zoom_reset = tk.Button(zoom_frame, text="원래대로", command=self.zoom_reset_original, width=8)
        btn_zoom_reset.pack(side=tk.LEFT, padx=2)
        
        self.canvas_original = tk.Canvas(
            original_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        self.canvas_original.pack(padx=5, pady=5)
        
        # 마우스 드래그 이벤트 바인딩
        self.canvas_original.bind("<Button-1>", self.on_canvas_original_drag_start)
        self.canvas_original.bind("<B1-Motion>", self.on_canvas_original_drag)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_original_drag_end)
        
        # 마우스 휠로 확대/축소
        def on_mousewheel_original(event):
            # 캔버스 위에 마우스가 있는지 확인
            if not self.canvas_original.winfo_containing(event.x_root, event.y_root):
                return
            
            # 마우스 위치를 중심으로 확대/축소
            # 캔버스 좌표계에서 마우스 위치
            mouse_x = event.x
            mouse_y = event.y
            
            if self.current_image is None or self.image_created_original is None:
                return
            
            try:
                # 현재 이미지 위치와 확대/축소 비율
                old_coords = self.canvas_original.coords(self.image_created_original)
                if not old_coords or len(old_coords) < 2:
                    return
                
                old_img_x = old_coords[0]
                old_img_y = old_coords[1]
                old_scale = self.zoom_scale_original
                
                # 이미지 상의 마우스 위치 (이미지 중심 기준)
                if hasattr(self.canvas_original, 'display_size'):
                    old_display_width, old_display_height = self.canvas_original.display_size
                else:
                    preview_width = 480
                    preview_height = 600
                    old_display_width = preview_width
                    old_display_height = preview_height
                
                # 마우스 위치에서 이미지 중심까지의 거리
                img_mouse_x = mouse_x - old_img_x
                img_mouse_y = mouse_y - old_img_y
                
                # 확대/축소 비율 변경
                if event.delta > 0:
                    # 확대
                    if old_scale < 8.0:
                        new_scale = min(old_scale * 1.5, 8.0)
                    else:
                        return
                elif event.delta < 0:
                    # 축소
                    if old_scale > 0.2:
                        new_scale = max(old_scale / 1.5, 0.2)
                    else:
                        return
                else:
                    return
                
                # 확대/축소 비율 업데이트
                self.zoom_scale_original = new_scale
                
                # 새로운 이미지 크기 계산
                scale_ratio = new_scale / old_scale
                new_display_width = int(old_display_width * scale_ratio)
                new_display_height = int(old_display_height * scale_ratio)
                
                # 마우스 위치를 중심으로 이미지 위치 조정
                # 확대/축소 후에도 마우스가 같은 이미지 상의 점을 가리키도록
                new_img_x = mouse_x - img_mouse_x * scale_ratio
                new_img_y = mouse_y - img_mouse_y * scale_ratio
                
                # 위치 저장
                self.canvas_original_pos_x = new_img_x
                self.canvas_original_pos_y = new_img_y
                
                # 이미지 다시 표시
                self.show_original_preview()
                # 편집된 이미지도 동일하게 확대/축소 및 위치 동기화
                self.show_edited_preview()
                
            except Exception as e:
                print(f"[얼굴편집] 마우스 휠 확대/축소 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # Windows에서 마우스 휠 이벤트 바인딩
        self.canvas_original.bind("<MouseWheel>", on_mousewheel_original)
        
        # 캔버스에 마우스가 들어올 때 포커스 설정
        def on_enter_canvas(event):
            self.canvas_original.focus_set()
        self.canvas_original.bind("<Enter>", on_enter_canvas)
        
        # 우측: 편집된 이미지
        edited_frame = tk.Frame(preview_frame)
        edited_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 5), pady=5)
        
        edited_top_frame = tk.Frame(edited_frame)
        edited_top_frame.pack(fill=tk.X)
        
        self.label_edited = tk.Label(edited_top_frame, text="편집된 이미지", font=("", 9))
        self.label_edited.pack(side=tk.LEFT)
        
        btn_save = tk.Button(edited_top_frame, text="PNG 저장", command=self.save_png, width=12, bg="#4CAF50", fg="white")
        btn_save.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_edited = tk.Canvas(
            edited_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        self.canvas_edited.pack(padx=5, pady=5)
        
        # 마우스 드래그 이벤트 바인딩
        self.canvas_edited.bind("<Button-1>", self.on_canvas_edited_drag_start)
        self.canvas_edited.bind("<B1-Motion>", self.on_canvas_edited_drag)
        self.canvas_edited.bind("<ButtonRelease-1>", self.on_canvas_edited_drag_end)
        
        return preview_frame
    
    def show_original_preview(self):
        """원본 이미지 미리보기 표시"""
        if self.current_image is None:
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            self.canvas_original_pos_x = None
            self.canvas_original_pos_y = None
            return
        
        try:
            # 캔버스 크기
            preview_width = 480
            preview_height = 600
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            img_ratio = img_width / img_height
            canvas_ratio = preview_width / preview_height
            
            # 기본 스케일 계산 (캔버스에 맞추기)
            if img_ratio > canvas_ratio:
                # 이미지가 더 넓음 -> 너비 기준으로 스케일
                base_scale = preview_width / img_width
                base_display_width = preview_width
                base_display_height = int(img_height * base_scale)
            else:
                # 이미지가 더 높음 -> 높이 기준으로 스케일
                base_scale = preview_height / img_height
                base_display_width = int(img_width * base_scale)
                base_display_height = preview_height
            
            # 확대/축소 비율 적용
            display_width = int(base_display_width * self.zoom_scale_original)
            display_height = int(base_display_height * self.zoom_scale_original)
            
            # 원본 이미지 기본 크기 저장 (처음 로드 시)
            if self.original_image_base_size is None:
                self.original_image_base_size = (base_display_width, base_display_height)
            
            # 이미지 리사이즈 (비율 유지, 확대/축소 적용)
            resized = self.current_image.resize((display_width, display_height), Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_original = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_original:
                # 기존 이미지의 위치를 가져와서 유지 (위치가 설정되지 않은 경우에만)
                if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                    try:
                        old_coords = self.canvas_original.coords(self.image_created_original)
                        if old_coords and len(old_coords) >= 2:
                            self.canvas_original_pos_x = old_coords[0]
                            self.canvas_original_pos_y = old_coords[1]
                    except Exception as e:
                        print(f"[얼굴편집] 기존 위치 가져오기 실패: {e}")
                
                self.canvas_original.delete(self.image_created_original)
            
            # 이미지 위치 결정 (처음 로드 시 또는 위치가 없을 때 중앙 배치)
            if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                self.canvas_original_pos_x = preview_width // 2
                self.canvas_original_pos_y = preview_height // 2
            
            # 경계 제한 제거: 확대/축소 시에도 사용자가 설정한 위치 유지
            
            self.image_created_original = self.canvas_original.create_image(
                self.canvas_original_pos_x,
                self.canvas_original_pos_y,
                anchor=tk.CENTER,
                image=self.tk_image_original
            )
            
            # 캔버스에 표시 크기 저장 (드래그 경계 계산용)
            self.canvas_original.display_size = (display_width, display_height)
            
            # 눈 영역 표시 업데이트
            if self.show_eye_region.get():
                self.update_eye_region_display()
        except Exception as e:
            print(f"[얼굴편집] 원본 이미지 표시 실패: {e}")
    
    def show_edited_preview(self):
        """편집된 이미지 미리보기 표시"""
        if self.edited_image is None:
            if self.image_created_edited:
                self.canvas_edited.delete(self.image_created_edited)
                self.image_created_edited = None
            self.canvas_edited_pos_x = None
            self.canvas_edited_pos_y = None
            return
        
        try:
            # 캔버스 크기
            preview_width = 480
            preview_height = 600
            
            # 편집된 이미지 크기
            img_width, img_height = self.edited_image.size
            img_ratio = img_width / img_height
            canvas_ratio = preview_width / preview_height
            
            # 기본 스케일 계산 (캔버스에 맞추기)
            if img_ratio > canvas_ratio:
                # 이미지가 더 넓음 -> 너비 기준으로 스케일
                base_scale = preview_width / img_width
                base_display_width = preview_width
                base_display_height = int(img_height * base_scale)
            else:
                # 이미지가 더 높음 -> 높이 기준으로 스케일
                base_scale = preview_height / img_height
                base_display_width = int(img_width * base_scale)
                base_display_height = preview_height
            
            # 원본 이미지와 동일한 확대/축소 비율 적용
            display_width = int(base_display_width * self.zoom_scale_original)
            display_height = int(base_display_height * self.zoom_scale_original)
            
            # 이미지 리사이즈 (비율 유지, 확대/축소 적용)
            resized = self.edited_image.resize((display_width, display_height), Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_edited = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_edited:
                # 기존 이미지의 위치를 가져와서 유지
                try:
                    old_coords = self.canvas_edited.coords(self.image_created_edited)
                    if old_coords and len(old_coords) >= 2:
                        self.canvas_edited_pos_x = old_coords[0]
                        self.canvas_edited_pos_y = old_coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 기존 위치 가져오기 실패: {e}")
                
                self.canvas_edited.delete(self.image_created_edited)
            
            # 원본 이미지와 동일한 위치 사용 (동기화)
            if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                self.canvas_edited_pos_x = self.canvas_original_pos_x
                self.canvas_edited_pos_y = self.canvas_original_pos_y
            elif self.canvas_edited_pos_x is None or self.canvas_edited_pos_y is None:
                # 위치가 없으면 중앙 배치
                self.canvas_edited_pos_x = preview_width // 2
                self.canvas_edited_pos_y = preview_height // 2
            
            self.image_created_edited = self.canvas_edited.create_image(
                self.canvas_edited_pos_x,
                self.canvas_edited_pos_y,
                anchor=tk.CENTER,
                image=self.tk_image_edited
            )
            
            # 캔버스에 표시 크기 저장 (드래그 경계 계산용)
            self.canvas_edited.display_size = (display_width, display_height)
            
            # 눈 영역 표시는 원본 이미지에만 표시되므로 여기서는 업데이트하지 않음
        except Exception as e:
            print(f"[얼굴편집] 편집된 이미지 표시 실패: {e}")
    
    def clear_eye_region_display(self):
        """눈 영역 표시 제거"""
        # 원본 이미지의 눈 영역 제거
        for rect_id in self.eye_region_rects_original:
            try:
                self.canvas_original.delete(rect_id)
            except Exception as e:
                print(f"[얼굴편집] 눈 영역 제거 실패: {e}")
        self.eye_region_rects_original.clear()
        
        # 편집된 이미지의 눈 영역 제거
        for rect_id in self.eye_region_rects_edited:
            try:
                self.canvas_edited.delete(rect_id)
            except Exception as e:
                print(f"[얼굴편집] 눈 영역 제거 실패: {e}")
        self.eye_region_rects_edited.clear()
    
    def update_eye_region_display(self):
        """눈 영역 표시 업데이트"""
        if not self.show_eye_region.get() or self.current_image is None:
            return
        
        try:
            # 기존 눈 영역 제거
            self.clear_eye_region_display()
            
            # 랜드마크 감지
            landmarks, detected = face_landmarks.detect_face_landmarks(self.current_image)
            if not detected:
                return
            
            key_landmarks = face_landmarks.get_key_landmarks(landmarks)
            if key_landmarks is None:
                return
            
            # 눈 영역 파라미터 가져오기 (개별 적용 여부에 따라)
            if self.use_individual_eye_region.get():
                # 개별 적용 모드
                left_padding = self.left_eye_region_padding.get()
                right_padding = self.right_eye_region_padding.get()
                left_offset_x = self.left_eye_region_offset_x.get()
                left_offset_y = self.left_eye_region_offset_y.get()
                right_offset_x = self.right_eye_region_offset_x.get()
                right_offset_y = self.right_eye_region_offset_y.get()
            else:
                # 동기화 모드
                left_padding = self.left_eye_region_padding.get()
                right_padding = self.left_eye_region_padding.get()
                left_offset_x = self.left_eye_region_offset_x.get()
                left_offset_y = self.left_eye_region_offset_y.get()
                right_offset_x = self.left_eye_region_offset_x.get()
                right_offset_y = self.left_eye_region_offset_y.get()
            
            # 원본 이미지에 눈 영역 표시
            for canvas, image, rects_list, pos_x, pos_y, display_size in [
                (self.canvas_original, self.current_image, self.eye_region_rects_original, 
                 self.canvas_original_pos_x, self.canvas_original_pos_y, 
                 getattr(self.canvas_original, 'display_size', None))
            ]:
                if image is None or pos_x is None or pos_y is None or display_size is None:
                    continue
                
                img_width, img_height = image.size
                display_width, display_height = display_size
                
                # 이미지 스케일 계산
                scale_x = display_width / img_width
                scale_y = display_height / img_height
                
                # 왼쪽/오른쪽 눈 영역 계산 및 표시 (개별 파라미터 사용)
                for eye_name, padding, offset_x, offset_y in [
                    ('left', left_padding, left_offset_x, left_offset_y),
                    ('right', right_padding, right_offset_x, right_offset_y)
                ]:
                    eye_region, eye_center = face_morphing._get_eye_region(
                        key_landmarks, img_width, img_height, eye_name, landmarks, padding, offset_x, offset_y
                    )
                    x1, y1, x2, y2 = eye_region
                    
                    # 타원형 마스크 계산 (실제 적용되는 모양과 동일하게)
                    eye_width = x2 - x1
                    eye_height = y2 - y1
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # 타원의 반지름 계산 (마스크 크기 고려)
                    mask_size = max(15, min(eye_width, eye_height) // 4)
                    if mask_size % 2 == 0:
                        mask_size += 1
                    radius_x = max(1, eye_width // 2 - mask_size // 3)
                    radius_y = max(1, eye_height // 2 - mask_size // 3)
                    
                    # 타원형 좌표 계산
                    ellipse_x1 = center_x - radius_x
                    ellipse_y1 = center_y - radius_y
                    ellipse_x2 = center_x + radius_x
                    ellipse_y2 = center_y + radius_y
                    
                    # 캔버스 좌표로 변환
                    rel_x1 = (ellipse_x1 - img_width / 2) * scale_x
                    rel_y1 = (ellipse_y1 - img_height / 2) * scale_y
                    rel_x2 = (ellipse_x2 - img_width / 2) * scale_x
                    rel_y2 = (ellipse_y2 - img_height / 2) * scale_y
                    
                    # 캔버스 절대 좌표
                    canvas_x1 = pos_x + rel_x1
                    canvas_y1 = pos_y + rel_y1
                    canvas_x2 = pos_x + rel_x2
                    canvas_y2 = pos_y + rel_y2
                    
                    # 타원형 그리기 (빨간색 테두리, 두께 1)
                    oval_id = canvas.create_oval(
                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                        outline="red", width=1, tags="eye_region"
                    )
                    rects_list.append(oval_id)
            
            # 편집된 이미지에 실제 적용된 영역 표시
            if self.edited_image is not None:
                try:
                    # 편집된 이미지에서 랜드마크 다시 감지
                    edited_landmarks, edited_detected = face_landmarks.detect_face_landmarks(self.edited_image)
                    if edited_detected:
                        edited_key_landmarks = face_landmarks.get_key_landmarks(edited_landmarks)
                        if edited_key_landmarks is not None:
                            # 편집된 이미지의 눈 영역 계산 (위치 조정이 적용된 후의 실제 영역)
                            for canvas, image, rects_list, pos_x, pos_y, display_size in [
                                (self.canvas_edited, self.edited_image, self.eye_region_rects_edited,
                                 self.canvas_edited_pos_x, self.canvas_edited_pos_y,
                                 getattr(self.canvas_edited, 'display_size', None))
                            ]:
                                if image is None or pos_x is None or pos_y is None or display_size is None:
                                    continue
                                
                                img_width, img_height = image.size
                                display_width, display_height = display_size
                                
                                # 이미지 스케일 계산
                                scale_x = display_width / img_width
                                scale_y = display_height / img_height
                                
                                # 왼쪽/오른쪽 눈 영역 계산 및 표시 (편집된 이미지의 실제 적용된 영역)
                                for eye_name, padding, offset_x, offset_y in [
                                    ('left', left_padding, left_offset_x, left_offset_y),
                                    ('right', right_padding, right_offset_x, right_offset_y)
                                ]:
                                    # 편집된 이미지의 랜드마크에서 눈 영역 계산
                                    # offset은 원본 이미지에서 영역을 계산할 때 사용된 값이므로
                                    # 편집된 이미지에서도 동일한 offset을 적용해야 실제 적용된 영역을 정확히 표시할 수 있음
                                    eye_region, eye_center = face_morphing._get_eye_region(
                                        edited_key_landmarks, img_width, img_height, eye_name, edited_landmarks, 
                                        padding, offset_x, offset_y  # 원본과 동일한 offset 적용
                                    )
                                    x1, y1, x2, y2 = eye_region
                                    
                                    # 타원형 마스크 계산 (실제 적용되는 모양과 동일하게)
                                    eye_width = x2 - x1
                                    eye_height = y2 - y1
                                    center_x = (x1 + x2) / 2
                                    center_y = (y1 + y2) / 2
                                    
                                    # 타원의 반지름 계산 (마스크 크기 고려)
                                    mask_size = max(15, min(eye_width, eye_height) // 4)
                                    if mask_size % 2 == 0:
                                        mask_size += 1
                                    radius_x = max(1, eye_width // 2 - mask_size // 3)
                                    radius_y = max(1, eye_height // 2 - mask_size // 3)
                                    
                                    # 타원형 좌표 계산
                                    ellipse_x1 = center_x - radius_x
                                    ellipse_y1 = center_y - radius_y
                                    ellipse_x2 = center_x + radius_x
                                    ellipse_y2 = center_y + radius_y
                                    
                                    # 캔버스 좌표로 변환
                                    rel_x1 = (ellipse_x1 - img_width / 2) * scale_x
                                    rel_y1 = (ellipse_y1 - img_height / 2) * scale_y
                                    rel_x2 = (ellipse_x2 - img_width / 2) * scale_x
                                    rel_y2 = (ellipse_y2 - img_height / 2) * scale_y
                                    
                                    # 캔버스 절대 좌표
                                    canvas_x1 = pos_x + rel_x1
                                    canvas_y1 = pos_y + rel_y1
                                    canvas_x2 = pos_x + rel_x2
                                    canvas_y2 = pos_y + rel_y2
                                    
                                    # 타원형 그리기 (파란색 테두리, 두께 1) - 편집된 이미지는 파란색으로 구분
                                    oval_id = canvas.create_oval(
                                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                                        outline="blue", width=1, tags="eye_region"
                                    )
                                    rects_list.append(oval_id)
                except Exception as e:
                    print(f"[얼굴편집] 편집된 이미지 눈 영역 표시 실패: {e}")
                    import traceback
                    traceback.print_exc()
        
        except Exception as e:
            print(f"[얼굴편집] 눈 영역 표시 실패: {e}")
            import traceback
            traceback.print_exc()
