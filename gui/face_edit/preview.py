"""
얼굴 편집 패널 - 미리보기 관리 Mixin
미리보기 표시 관련 기능을 담당
"""
import math
import tkinter as tk
from PIL import Image, ImageTk

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
from .polygon_renderer import PolygonRendererMixin
from .landmark_display import LandmarkDisplayMixin


class PreviewManagerMixin:
    """미리보기 관리 기능 Mixin"""
    
    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""
        # parent가 Toplevel이면 전체 창을 사용, 아니면 LabelFrame 사용
        if isinstance(parent, tk.Toplevel):
            preview_frame = tk.Frame(parent, padx=10, pady=10)
            preview_frame.pack(fill=tk.BOTH, expand=True)
        else:
            preview_frame = tk.LabelFrame(parent, text="미리보기", padx=5, pady=5)
            preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 이미지 크기 (변수에서 가져오기, 없으면 기본값 사용)
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)
        
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
                    preview_width = getattr(self, 'preview_width', 800)
                    preview_height = getattr(self, 'preview_height', 1000)
                    old_display_width = preview_width
                    old_display_height = preview_height
                
                # 마우스 위치에서 이미지 중심까지의 거리
                img_mouse_x = mouse_x - old_img_x
                img_mouse_y = mouse_y - old_img_y
                
                # 확대/축소 비율 변경 (더 세밀한 조정: 1.1배씩)
                zoom_factor = 1.1  # 스크롤 한 번에 10%씩 확대/축소
                max_scale = getattr(self, 'zoom_max_scale', 8.0)  # 최대 확대 비율
                min_scale = getattr(self, 'zoom_min_scale', 0.2)  # 최소 축소 비율
                if event.delta > 0:
                    # 확대
                    if old_scale < max_scale:
                        new_scale = min(old_scale * zoom_factor, max_scale)
                    else:
                        return
                elif event.delta < 0:
                    # 축소
                    if old_scale > min_scale:
                        new_scale = max(old_scale / zoom_factor, min_scale)
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
                
                # 위치 저장 (마우스 휠 확대/축소 시 계산된 위치를 명시적으로 설정)
                self.canvas_original_pos_x = new_img_x
                self.canvas_original_pos_y = new_img_y
                # 편집된 이미지도 동일한 위치로 동기화
                self.canvas_edited_pos_x = new_img_x
                self.canvas_edited_pos_y = new_img_y
                
                # 성능 최적화: 연속 스크롤 시 debounce 처리
                if hasattr(self, '_zoom_update_pending') and self._zoom_update_pending:
                    # 이미 대기 중인 업데이트가 있으면 취소
                    try:
                        self.after_cancel(self._zoom_update_id)
                    except:
                        pass
                
                # 이미지 업데이트를 약간 지연시켜 연속 스크롤 시 성능 향상
                def update_zoom():
                    self._zoom_update_pending = False
                    self.show_original_preview()
                    self.show_edited_preview()
                    
                    # 마우스 휠 확대/축소 후 랜드마크 다시 그리기
                    if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                        if hasattr(self, 'update_face_features_display'):
                            self.update_face_features_display()
                
                self._zoom_update_pending = True
                self._zoom_update_id = self.after(50, update_zoom)  # 50ms 지연
                
            except Exception as e:
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
            preview_width = getattr(self, 'preview_width', 800)
            preview_height = getattr(self, 'preview_height', 1000)

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
            
            # 이미지 리사이즈 캐싱 (성능 최적화)
            cache_key = (id(self.current_image), display_width, display_height)
            resize_cache = getattr(self, '_resize_cache', {})
            
            if cache_key in resize_cache:
                resized = resize_cache[cache_key]
            else:
                # 이미지 리사이즈 (비율 유지, 확대/축소 적용)
                # 성능 최적화: 확대 시에는 BILINEAR 사용 (LANCZOS는 너무 느림)
                # 축소 시에만 LANCZOS 사용하여 품질 유지
                if display_width > self.current_image.size[0] or display_height > self.current_image.size[1]:
                    # 확대: BILINEAR 사용 (빠름)
                    resized = self.current_image.resize((display_width, display_height), Image.BILINEAR)
                else:
                    # 축소: LANCZOS 사용 (고품질)
                    resized = self.current_image.resize((display_width, display_height), Image.LANCZOS)
                
                # LRU 캐시 관리
                resize_cache_max_size = getattr(self, '_resize_cache_max_size', 10)
                if len(resize_cache) >= resize_cache_max_size:
                    # 가장 오래된 항목 제거 (FIFO)
                    oldest_key = next(iter(resize_cache))
                    del resize_cache[oldest_key]
                resize_cache[cache_key] = resized
                self._resize_cache = resize_cache
            
            # PhotoImage로 변환
            self.tk_image_original = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_original:
                # 기존 이미지의 위치를 가져와서 유지
                # 단, 이미 설정된 위치가 있으면 덮어쓰지 않음 (마우스 휠 확대/축소 등)
                if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                    try:
                        old_coords = self.canvas_original.coords(self.image_created_original)
                        if old_coords and len(old_coords) >= 2:
                            # 캔버스의 실제 위치를 사용
                            self.canvas_original_pos_x = old_coords[0]
                            self.canvas_original_pos_y = old_coords[1]
                    except Exception as e:
                        print(f"[원본 이미지 미리보기] 기존 이미지의 위치를 가져오는 중 오류 발생: {e}")
                        pass
                
                self.canvas_original.delete(self.image_created_original)
            
            # 이미지 위치 결정 (처음 로드 시 또는 위치가 없을 때 중앙 배치)
            # 단, 0,0은 유효한 위치일 수 있으므로 None일 때만 중앙 배치
            if self.canvas_original_pos_x is None:
                self.canvas_original_pos_x = preview_width // 2
            if self.canvas_original_pos_y is None:
                self.canvas_original_pos_y = preview_height // 2
            
            # 이미지가 캔버스 안에 완전히 들어오도록 위치 제한
            # "원래대로" 버튼을 누른 경우에만 경계 제한 적용
            if getattr(self, 'is_resetting_position', False):
                half_width = display_width // 2
                half_height = display_height // 2
                
                # 경계 제한: 이미지가 캔버스 밖으로 나가지 않도록
                if display_width >= preview_width:
                    self.canvas_original_pos_x = max(half_width, min(preview_width - half_width, self.canvas_original_pos_x))
                else:
                    # 이미지가 캔버스보다 작으면 중앙 배치
                    self.canvas_original_pos_x = preview_width // 2
                
                if display_height >= preview_height:
                    self.canvas_original_pos_y = max(half_height, min(preview_height - half_height, self.canvas_original_pos_y))
                else:
                    # 이미지가 캔버스보다 작으면 중앙 배치
                    self.canvas_original_pos_y = preview_height // 2
            
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
            # 입술 영역 표시 업데이트
            if self.show_lip_region.get():
                self.update_lip_region_display()
            # 바운딩 박스 표시 업데이트 (폴리곤이 체크되어 있을 때만)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                self.update_bbox_display()
            # 랜드마크 또는 연결선 표시 업데이트 (확대/축소 중이면 스킵)
            if not getattr(self, '_is_zooming', False):
                if self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()):
                    self.update_face_features_display()
        except Exception as e:
            print(f"[원본 이미지 미리보기] 오류 발생: {e}")
            pass
    
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
            preview_width = getattr(self, 'preview_width', 800)
            preview_height = getattr(self, 'preview_height', 1000)

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
            
            print("[편집된 이미지 미리보기] display size:", f"{display_width}x{display_height}, scale: {self.zoom_scale_original}")
            
            # 이미지 리사이즈 캐싱 (성능 최적화)
            cache_key = (id(self.edited_image), display_width, display_height)
            resize_cache = getattr(self, '_resize_cache', {})
            
            if cache_key in resize_cache:
                resized = resize_cache[cache_key]
            else:
                # 이미지 리사이즈 (비율 유지, 확대/축소 적용)
                # 성능 최적화: 확대 시에는 BILINEAR 사용 (LANCZOS는 너무 느림)
                # 축소 시에만 LANCZOS 사용하여 품질 유지
                if display_width > self.edited_image.size[0] or display_height > self.edited_image.size[1]:
                    # 확대: BILINEAR 사용 (빠름)
                    resized = self.edited_image.resize((display_width, display_height), Image.BILINEAR)
                else:
                    # 축소: LANCZOS 사용 (고품질)
                    resized = self.edited_image.resize((display_width, display_height), Image.LANCZOS)
                
                # LRU 캐시 관리
                resize_cache_max_size = getattr(self, '_resize_cache_max_size', 10)
                if len(resize_cache) >= resize_cache_max_size:
                    # 가장 오래된 항목 제거 (FIFO)
                    oldest_key = next(iter(resize_cache))
                    del resize_cache[oldest_key]
                resize_cache[cache_key] = resized
                self._resize_cache = resize_cache
            
            # PhotoImage로 변환
            self.tk_image_edited = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            # 위치 결정: 이미 설정된 위치를 절대 덮어쓰지 않음
            # 1. 먼저 캔버스에서 현재 위치를 가져옴 (이미지가 존재하는 경우)
            saved_pos_x = None
            saved_pos_y = None
            
            if self.image_created_edited:
                try:
                    old_coords = self.canvas_edited.coords(self.image_created_edited)
                    if old_coords and len(old_coords) >= 2:
                        saved_pos_x = old_coords[0]
                        saved_pos_y = old_coords[1]
                except Exception as e:
                    print(f"[편집된 이미지 미리보기] 기존 이미지의 위치를 가져오는 중 오류 발생: {e}")
                    pass
                
                self.canvas_edited.delete(self.image_created_edited)
            
            # 위치 결정: 이미 설정된 위치가 있으면 그대로 사용, 없으면 캔버스에서 가져온 위치 사용
            if self.canvas_edited_pos_x is not None and self.canvas_edited_pos_y is not None:
                # 이미 설정된 위치가 있으면 그대로 사용 (절대 변경하지 않음)
                pass
            elif saved_pos_x is not None and saved_pos_y is not None:
                # 캔버스에서 가져온 위치 사용
                self.canvas_edited_pos_x = saved_pos_x
                self.canvas_edited_pos_y = saved_pos_y
            elif self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                # 원본 이미지 위치와 동기화
                self.canvas_edited_pos_x = self.canvas_original_pos_x
                self.canvas_edited_pos_y = self.canvas_original_pos_y
            else:
                # 위치가 없으면 중앙 배치
                if self.canvas_edited_pos_x is None:
                    self.canvas_edited_pos_x = preview_width // 2
                if self.canvas_edited_pos_y is None:
                    self.canvas_edited_pos_y = preview_height // 2
            
            # 이미지가 캔버스 안에 완전히 들어오도록 위치 제한
            # "원래대로" 버튼을 누른 경우에만 경계 제한 적용
            if getattr(self, 'is_resetting_position', False):
                half_width = display_width // 2
                half_height = display_height // 2
                
                # 경계 제한: 이미지가 캔버스 밖으로 나가지 않도록
                if display_width >= preview_width:
                    self.canvas_edited_pos_x = max(half_width, min(preview_width - half_width, self.canvas_edited_pos_x))
                else:
                    # 이미지가 캔버스보다 작으면 중앙 배치
                    self.canvas_edited_pos_x = preview_width // 2
                
                if display_height >= preview_height:
                    self.canvas_edited_pos_y = max(half_height, min(preview_height - half_height, self.canvas_edited_pos_y))
                else:
                    # 이미지가 캔버스보다 작으면 중앙 배치
                    self.canvas_edited_pos_y = preview_height // 2
            

            
            self.image_created_edited = self.canvas_edited.create_image(
                self.canvas_edited_pos_x,
                self.canvas_edited_pos_y,
                anchor=tk.CENTER,
                image=self.tk_image_edited
            )
            
            print(f"[편집된 이미지 미리보기] Canvas Image ID: {self.image_created_edited}, x={self.canvas_edited_pos_x}, y={self.canvas_edited_pos_y}")
            
            # 이미지를 맨 위로 올리기 (랜드마크나 폴리곤 뒤에 가려지지 않도록)
            self.canvas_edited.tag_raise(self.image_created_edited)
            
            # 캔버스에 표시 크기 저장 (드래그 경계 계산용)
            self.canvas_edited.display_size = (display_width, display_height)
            
            # 눈 영역 표시는 원본 이미지에만 표시되므로 여기서는 업데이트하지 않음
            # 입술 영역 표시 업데이트 (편집된 이미지에도 표시)
            if self.show_lip_region.get():
                self.update_lip_region_display()
            # 바운딩 박스 표시 업데이트 (폴리곤이 체크되어 있을 때만)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                self.update_bbox_display()
            # 랜드마크 또는 연결선 표시 업데이트 (편집된 이미지에도 표시, 확대/축소 중이면 스킵)
            if not getattr(self, '_is_zooming', False):
                if self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()):
                    self.update_face_features_display()
        except Exception as e:
            print(f"[편집된 이미지 미리보기] 오류 발생: {e}")
            pass
    
    def clear_eye_region_display(self):
        """눈 영역 표시 제거"""
        # 원본 이미지의 눈 영역 제거
        for rect_id in self.eye_region_rects_original:
            try:
                self.canvas_original.delete(rect_id)
            except Exception as e:
                print(f"[원본 이미지 눈 영역 표시 제거] 오류 발생: {e}")
                pass
        self.eye_region_rects_original.clear()
        
        # 편집된 이미지의 눈 영역 제거
        for rect_id in self.eye_region_rects_edited:
            try:
                self.canvas_edited.delete(rect_id)
            except Exception as e:
                print(f"[눈 영역 표시 제거] 오류 발생: {e}")
                pass
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
                    import traceback
                    traceback.print_exc()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def clear_lip_region_display(self):
        """입술 영역 표시 제거"""
        # 원본 이미지의 입술 영역 제거
        for rect_id in self.lip_region_rects_original:
            try:
                self.canvas_original.delete(rect_id)
            except Exception as e:
                print(f"[원본 이미지 입술 영역 표시 제거] 오류 발생: {e}")
                pass
        self.lip_region_rects_original.clear()
        
        # 편집된 이미지의 입술 영역 제거
        for rect_id in self.lip_region_rects_edited:
            try:
                self.canvas_edited.delete(rect_id)
            except Exception as e:
                print(f"[편집된 이미지 입술 영역 표시 제거] 오류 발생: {e}")
                pass
        self.lip_region_rects_edited.clear()
    
    def update_lip_region_display(self):
        """입술 영역 표시 업데이트"""
        if not self.show_lip_region.get() or self.current_image is None:
            return
        
        try:
            # 기존 입술 영역 제거
            self.clear_lip_region_display()
            
            # 랜드마크 감지
            landmarks, detected = face_landmarks.detect_face_landmarks(self.current_image)
            if not detected:
                return
            
            key_landmarks = face_landmarks.get_key_landmarks(landmarks)
            if key_landmarks is None or key_landmarks['mouth'] is None:
                return
            
            mouth_center = key_landmarks['mouth']
            mouth_center_y = mouth_center[1]
            
            # MediaPipe 입술 랜드마크 인덱스
            ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
            
            # 윗입술과 아래입술 포인트 분리
            upper_lip_points = []
            lower_lip_points = []
            for i in ALL_LIP_INDICES:
                if i < len(landmarks):
                    point = landmarks[i]
                    if point[1] < mouth_center_y:
                        upper_lip_points.append(point)
                    elif point[1] > mouth_center_y:
                        lower_lip_points.append(point)
            
            # 입술 영역 파라미터 가져오기 (개별 적용 여부에 따라)
            if self.use_individual_lip_region.get():
                # 개별 적용 모드
                upper_padding_x = self.upper_lip_region_padding_x.get()
                upper_padding_y = self.upper_lip_region_padding_y.get()
                upper_offset_x = self.upper_lip_region_offset_x.get()
                upper_offset_y = self.upper_lip_region_offset_y.get()
                lower_padding_x = self.lower_lip_region_padding_x.get()
                lower_padding_y = self.lower_lip_region_padding_y.get()
                lower_offset_x = self.lower_lip_region_offset_x.get()
                lower_offset_y = self.lower_lip_region_offset_y.get()
            else:
                # 동기화 모드
                upper_padding_x = self.upper_lip_region_padding_x.get()
                upper_padding_y = self.upper_lip_region_padding_y.get()
                upper_offset_x = self.upper_lip_region_offset_x.get()
                upper_offset_y = self.upper_lip_region_offset_y.get()
                lower_padding_x = self.upper_lip_region_padding_x.get()
                lower_padding_y = self.upper_lip_region_padding_y.get()
                lower_offset_x = self.upper_lip_region_offset_x.get()
                lower_offset_y = self.upper_lip_region_offset_y.get()
            
            # 원본 이미지에 입술 영역 표시
            for canvas, image, rects_list, pos_x, pos_y, display_size in [
                (self.canvas_original, self.current_image, self.lip_region_rects_original, 
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
                
                # 윗입술 영역 표시
                if upper_lip_points:
                    upper_x_coords = [p[0] for p in upper_lip_points]
                    upper_y_coords = [p[1] for p in upper_lip_points]
                    x_min = int(min(upper_x_coords))
                    x_max = int(max(upper_x_coords))
                    y_min = int(min(upper_y_coords))
                    y_max = min(int(max(upper_y_coords)), int(mouth_center_y))
                    
                    # 패딩 추가 (파라미터 적용)
                    padding_x = int((x_max - x_min) * upper_padding_x)
                    padding_y = int((y_max - y_min) * upper_padding_y)
                    x1 = max(0, x_min - padding_x + int(upper_offset_x))
                    y1 = max(0, y_min - padding_y + int(upper_offset_y))
                    x2 = min(img_width, x_max + padding_x + int(upper_offset_x))
                    y2 = min(img_height, y_max + int(upper_offset_y))
                    
                    # 캔버스 좌표로 변환
                    rel_x1 = (x1 - img_width / 2) * scale_x
                    rel_y1 = (y1 - img_height / 2) * scale_y
                    rel_x2 = (x2 - img_width / 2) * scale_x
                    rel_y2 = (y2 - img_height / 2) * scale_y
                    
                    canvas_x1 = pos_x + rel_x1
                    canvas_y1 = pos_y + rel_y1
                    canvas_x2 = pos_x + rel_x2
                    canvas_y2 = pos_y + rel_y2
                    
                    # 사각형 그리기 (윗입술: 빨간색)
                    rect_id = canvas.create_rectangle(
                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                        outline="red", width=2, tags="lip_region"
                    )
                    rects_list.append(rect_id)
                
                # 아래입술 영역 표시
                if lower_lip_points:
                    lower_x_coords = [p[0] for p in lower_lip_points]
                    lower_y_coords = [p[1] for p in lower_lip_points]
                    x_min = int(min(lower_x_coords))
                    x_max = int(max(lower_x_coords))
                    y_min = max(int(min(lower_y_coords)), int(mouth_center_y))
                    y_max = int(max(lower_y_coords))
                    
                    # 패딩 추가 (파라미터 적용)
                    padding_x = int((x_max - x_min) * lower_padding_x)
                    padding_y = int((y_max - y_min) * lower_padding_y)
                    x1 = max(0, x_min - padding_x + int(lower_offset_x))
                    y1 = max(0, y_min + int(lower_offset_y))
                    x2 = min(img_width, x_max + padding_x + int(lower_offset_x))
                    y2 = min(img_height, y_max + padding_y + int(lower_offset_y))
                    
                    # 캔버스 좌표로 변환
                    rel_x1 = (x1 - img_width / 2) * scale_x
                    rel_y1 = (y1 - img_height / 2) * scale_y
                    rel_x2 = (x2 - img_width / 2) * scale_x
                    rel_y2 = (y2 - img_height / 2) * scale_y
                    
                    canvas_x1 = pos_x + rel_x1
                    canvas_y1 = pos_y + rel_y1
                    canvas_x2 = pos_x + rel_x2
                    canvas_y2 = pos_y + rel_y2
                    
                    # 사각형 그리기 (아래입술: 파란색)
                    rect_id = canvas.create_rectangle(
                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                        outline="blue", width=2, tags="lip_region"
                    )
                    rects_list.append(rect_id)
            
            # 편집된 이미지에 입술 영역 표시
            if self.edited_image is not None:
                try:
                    edited_landmarks, edited_detected = face_landmarks.detect_face_landmarks(self.edited_image)
                    if edited_detected:
                        edited_key_landmarks = face_landmarks.get_key_landmarks(edited_landmarks)
                        if edited_key_landmarks is not None and edited_key_landmarks['mouth'] is not None:
                            edited_mouth_center = edited_key_landmarks['mouth']
                            edited_mouth_center_y = edited_mouth_center[1]
                            
                            # 편집된 이미지의 윗입술과 아래입술 포인트 분리
                            edited_upper_lip_points = []
                            edited_lower_lip_points = []
                            for i in ALL_LIP_INDICES:
                                if i < len(edited_landmarks):
                                    point = edited_landmarks[i]
                                    if point[1] < edited_mouth_center_y:
                                        edited_upper_lip_points.append(point)
                                    elif point[1] > edited_mouth_center_y:
                                        edited_lower_lip_points.append(point)
                            
                            for canvas, image, rects_list, pos_x, pos_y, display_size in [
                                (self.canvas_edited, self.edited_image, self.lip_region_rects_edited,
                                 self.canvas_edited_pos_x, self.canvas_edited_pos_y,
                                 getattr(self.canvas_edited, 'display_size', None))
                            ]:
                                if image is None or pos_x is None or pos_y is None or display_size is None:
                                    continue
                                
                                img_width, img_height = image.size
                                display_width, display_height = display_size
                                
                                scale_x = display_width / img_width
                                scale_y = display_height / img_height
                                
                                # 편집된 이미지의 윗입술 영역 표시
                                if edited_upper_lip_points:
                                    upper_x_coords = [p[0] for p in edited_upper_lip_points]
                                    upper_y_coords = [p[1] for p in edited_upper_lip_points]
                                    x_min = int(min(upper_x_coords))
                                    x_max = int(max(upper_x_coords))
                                    y_min = int(min(upper_y_coords))
                                    y_max = min(int(max(upper_y_coords)), int(edited_mouth_center_y))
                                    
                                    padding_x = int((x_max - x_min) * upper_padding_x)
                                    padding_y = int((y_max - y_min) * upper_padding_y)
                                    x1 = max(0, x_min - padding_x + int(upper_offset_x))
                                    y1 = max(0, y_min - padding_y + int(upper_offset_y))
                                    x2 = min(img_width, x_max + padding_x + int(upper_offset_x))
                                    y2 = min(img_height, y_max + int(upper_offset_y))
                                    
                                    rel_x1 = (x1 - img_width / 2) * scale_x
                                    rel_y1 = (y1 - img_height / 2) * scale_y
                                    rel_x2 = (x2 - img_width / 2) * scale_x
                                    rel_y2 = (y2 - img_height / 2) * scale_y
                                    
                                    canvas_x1 = pos_x + rel_x1
                                    canvas_y1 = pos_y + rel_y1
                                    canvas_x2 = pos_x + rel_x2
                                    canvas_y2 = pos_y + rel_y2
                                    
                                    rect_id = canvas.create_rectangle(
                                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                                        outline="red", width=2, tags="lip_region"
                                    )
                                    rects_list.append(rect_id)
                                
                                # 편집된 이미지의 아래입술 영역 표시
                                if edited_lower_lip_points:
                                    lower_x_coords = [p[0] for p in edited_lower_lip_points]
                                    lower_y_coords = [p[1] for p in edited_lower_lip_points]
                                    x_min = int(min(lower_x_coords))
                                    x_max = int(max(lower_x_coords))
                                    y_min = max(int(min(lower_y_coords)), int(edited_mouth_center_y))
                                    y_max = int(max(lower_y_coords))
                                    
                                    padding_x = int((x_max - x_min) * lower_padding_x)
                                    padding_y = int((y_max - y_min) * lower_padding_y)
                                    x1 = max(0, x_min - padding_x + int(lower_offset_x))
                                    y1 = max(0, y_min + int(lower_offset_y))
                                    x2 = min(img_width, x_max + padding_x + int(lower_offset_x))
                                    y2 = min(img_height, y_max + padding_y + int(lower_offset_y))
                                    
                                    rel_x1 = (x1 - img_width / 2) * scale_x
                                    rel_y1 = (y1 - img_height / 2) * scale_y
                                    rel_x2 = (x2 - img_width / 2) * scale_x
                                    rel_y2 = (y2 - img_height / 2) * scale_y
                                    
                                    canvas_x1 = pos_x + rel_x1
                                    canvas_y1 = pos_y + rel_y1
                                    canvas_x2 = pos_x + rel_x2
                                    canvas_y2 = pos_y + rel_y2
                                    
                                    rect_id = canvas.create_rectangle(
                                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                                        outline="blue", width=2, tags="lip_region"
                                    )
                                    rects_list.append(rect_id)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def clear_bbox_display(self):
        """바운딩 박스 표시 제거"""
        # 원본 이미지의 바운딩 박스 제거
        if self.bbox_rect_original is not None:
            try:
                self.canvas_original.delete(self.bbox_rect_original)
            except Exception as e:
                print(f"[바운딩 박스 표시 제거] 오류 발생: {e}")
                pass
        self.bbox_rect_original = None
    
    def update_bbox_display(self):
        """바운딩 박스 표시 업데이트"""
        if self.current_image is None:
            return
        
        try:
            # 기존 바운딩 박스 제거
            self.clear_bbox_display()
            
            # 바운딩 박스 가져오기
            if not hasattr(self, 'landmark_manager'):
                return
            
            img_width, img_height = self.current_image.size
            bbox = self.landmark_manager.get_original_bbox(img_width, img_height)
            
            # 바운딩 박스가 None이면 계산 시도
            if bbox is None:
                # 랜드마크를 사용하여 바운딩 박스 계산
                landmarks = self.landmark_manager.get_original_landmarks()
                if landmarks is None:
                    landmarks = self.landmark_manager.get_face_landmarks()
                
                if landmarks is not None:
                    from utils.face_morphing.polygon_morphing.core import _calculate_landmark_bounding_box
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        left_iris_indices, right_iris_indices = get_iris_indices()
                        iris_contour_indices = set(left_iris_indices + right_iris_indices)
                        iris_center_indices = {468, 473}
                        iris_indices = iris_contour_indices | iris_center_indices
                    except:
                        iris_indices = {468, 469, 470, 471, 472, 473, 474, 475, 476, 477}
                    
                    landmarks_no_iris = [pt for i, pt in enumerate(landmarks) if i not in iris_indices]
                    bbox = _calculate_landmark_bounding_box(landmarks_no_iris, img_width, img_height, padding_ratio=0.5)
                    
                    if bbox is not None:
                        # 계산된 바운딩 박스를 캐시에 저장
                        self.landmark_manager.set_original_bbox(bbox, img_width, img_height)
            
            if bbox is None:
                return
            
            min_x, min_y, max_x, max_y = bbox
            
            # 원본 이미지에 바운딩 박스 표시
            if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                return
            
            display_size = getattr(self.canvas_original, 'display_size', None)
            if display_size is None:
                return
            
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
            display_width, display_height = display_size
            
            # 이미지 스케일 계산
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 바운딩 박스 좌표를 캔버스 좌표로 변환
            rel_x1 = (min_x - img_width / 2) * scale_x
            rel_y1 = (min_y - img_height / 2) * scale_y
            rel_x2 = (max_x - img_width / 2) * scale_x
            rel_y2 = (max_y - img_height / 2) * scale_y
            
            canvas_x1 = pos_x + rel_x1
            canvas_y1 = pos_y + rel_y1
            canvas_x2 = pos_x + rel_x2
            canvas_y2 = pos_y + rel_y2
            
            # 바운딩 박스 사각형 그리기 (빨간색, 두꺼운 선)
            self.bbox_rect_original = self.canvas_original.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline="red", width=3, tags="bbox"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def clear_landmarks_display(self):
        """랜드마크 표시 제거"""
        # 변형된 랜드마크 아이템도 제거
        if hasattr(self, 'landmarks_items_transformed'):
            for item_id in self.landmarks_items_transformed:
                try:
                    if hasattr(self, 'canvas_original'):
                        self.canvas_original.delete(item_id)
                except:
                    pass
            self.landmarks_items_transformed.clear()
        # 원본 이미지의 랜드마크 제거 (포인트 + 폴리곤)
        for item_id in self.landmarks_items_original:
            try:
                self.canvas_original.delete(item_id)
            except Exception as e:
                print(f"[원본 이미지 랜드마크 제거] 오류 발생: {e}")
                pass
        self.landmarks_items_original.clear()
        # landmark_point_map은 더 이상 사용하지 않음 (polygon_point_map으로 대체됨)
        
        # 중심점 태그로 제거
        try:
            self.canvas_original.delete("region_center")
        except Exception:
            pass
        
        # 폴리곤 태그로 제거
        try:
            self.canvas_original.delete("landmarks_polygon")
            self.canvas_original.delete("landmarks_polygon_fill")
        except Exception:
            pass
        
        # 폴리곤 아이템 제거
        for item_id in self.landmark_polygon_items['original']:
            try:
                self.canvas_original.delete(item_id)
            except Exception:
                pass
        self.landmark_polygon_items['original'].clear()
        # 폴리곤 포인트 맵도 초기화
        self.polygon_point_map_original.clear()

        # 편집된 이미지의 랜드마크 제거 (포인트 + 폴리곤)
        for item_id in self.landmarks_items_edited:
            try:
                self.canvas_edited.delete(item_id)
            except Exception as e:
                print(f"[편집된 이미지 랜드마크 제거] 오류 발생: {e}")
                pass
        self.landmarks_items_edited.clear()
        # landmark_point_map은 더 이상 사용하지 않음 (polygon_point_map으로 대체됨)
        
        # 폴리곤 태그로 제거
        try:
            self.canvas_edited.delete("landmarks_polygon")
            self.canvas_edited.delete("landmarks_polygon_fill")
        except Exception:
            pass
        
        # 폴리곤 아이템 제거
        for item_id in self.landmark_polygon_items['edited']:
            try:
                self.canvas_edited.delete(item_id)
            except Exception:
                pass
        self.landmark_polygon_items['edited'].clear()
        # 폴리곤 포인트 맵도 초기화
        self.polygon_point_map_edited.clear()
    
    def update_face_features_display(self):
        """얼굴 특징 표시 업데이트 (랜드마크 포인트, 연결선, 폴리곤)"""
        # 랜드마크, 연결선, 폴리곤 중 하나라도 체크되어 있으면 랜드마크 감지 필요
        show_landmarks = self.show_landmark_points.get() if hasattr(self, 'show_landmark_points') else False
        show_lines = self.show_landmark_lines.get() if hasattr(self, 'show_landmark_lines') else False
        show_polygons = self.show_landmark_polygons.get() if hasattr(self, 'show_landmark_polygons') else False
        
        if (not show_landmarks and not show_lines and not show_polygons) or self.current_image is None:
            # 둘 다 체크 해제되어 있으면 랜드마크 제거
            if not show_landmarks:
                self.clear_landmarks_display()
            if not show_lines and not show_polygons:
                # 연결선 및 폴리곤 제거
                # 원본 이미지의 연결선/폴리곤 제거
                for item_id in self.landmark_polygon_items['original']:
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                # 폴리곤 포인트 맵도 초기화
                self.polygon_point_map_original.clear()
                # 편집된 이미지의 연결선/폴리곤 제거
                for item_id in self.landmark_polygon_items['edited']:
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 폴리곤 포인트 맵도 초기화
                self.polygon_point_map_edited.clear()
                # 연결선 태그로도 제거 시도
                for item_id in self.canvas_original.find_withtag("landmarks_polygon"):
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                for item_id in self.canvas_edited.find_withtag("landmarks_polygon"):
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
            # 폴리곤이 체크 해제되면 바운딩 박스도 제거
            if not show_polygons and hasattr(self, 'clear_bbox_display'):
                self.clear_bbox_display()
            return

        try:
            # 탭 변경 시 기존 폴리곤과 연결선을 먼저 제거 (항상 제거 후 다시 그리기)
            # 중심점 제거
            try:
                self.canvas_original.delete("region_center")
            except Exception:
                pass
            
            # 원본 이미지의 연결선/폴리곤 제거
            for item_id in self.landmark_polygon_items['original']:
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items['original'].clear()
            # 폴리곤 포인트 맵도 초기화
            self.polygon_point_map_original.clear()
            # 편집된 이미지의 연결선/폴리곤 제거
            for item_id in self.landmark_polygon_items['edited']:
                try:
                    self.canvas_edited.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items['edited'].clear()
            # 폴리곤 포인트 맵도 초기화
            self.polygon_point_map_edited.clear()
            # 연결선 태그로도 제거 시도
            for item_id in self.canvas_original.find_withtag("landmarks_polygon"):
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            for item_id in self.canvas_edited.find_withtag("landmarks_polygon"):
                try:
                    self.canvas_edited.delete(item_id)
                except Exception:
                    pass
            
            # 기존 연결선과 폴리곤 제거 (체크박스가 해제된 경우)
            if not show_lines and not show_polygons:
                # 원본 이미지의 연결선/폴리곤 제거
                for item_id in self.landmark_polygon_items['original']:
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['original'].clear()
                # 폴리곤 포인트 맵도 초기화
                self.polygon_point_map_original.clear()
                # 편집된 이미지의 연결선/폴리곤 제거
                for item_id in self.landmark_polygon_items['edited']:
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items['edited'].clear()
                # 폴리곤 포인트 맵도 초기화
                self.polygon_point_map_edited.clear()
            
            # 기존 랜드마크 포인트만 제거 (랜드마크 체크박스가 해제된 경우에만)
            # 연결선과 폴리곤은 clear_landmarks_display에서 제거하지 않음 (독립적으로 관리)
            if not show_landmarks:
                # 랜드마크 포인트만 제거 (연결선/폴리곤은 유지)
                for item_id in self.landmarks_items_original:
                    try:
                        self.canvas_original.delete(item_id)
                    except Exception:
                        pass
                self.landmarks_items_original.clear()
                self.polygon_point_map_original.clear()
                
                for item_id in self.landmarks_items_edited:
                    try:
                        self.canvas_edited.delete(item_id)
                    except Exception:
                        pass
                self.landmarks_items_edited.clear()
                self.polygon_point_map_edited.clear()
                
                # 변형된 랜드마크도 제거
                if hasattr(self, 'landmarks_items_transformed'):
                    for item_id in self.landmarks_items_transformed:
                        try:
                            self.canvas_original.delete(item_id)
                        except Exception:
                            pass
                    self.landmarks_items_transformed.clear()

            # 랜드마크 감지 (원본 이미지) - 연결선만 표시해도 랜드마크 좌표 필요
            # 커스텀 랜드마크가 있으면 사용, 없으면 새로 감지
            if self.custom_landmarks is not None:
                landmarks = self.custom_landmarks
                detected = True

            elif self.face_landmarks is not None:
                landmarks = self.face_landmarks
                detected = True

            else:
                landmarks, detected = face_landmarks.detect_face_landmarks(self.current_image)
                if detected and landmarks is not None:
                    self.face_landmarks = landmarks

            if not detected or landmarks is None:
                if show_lines or show_polygons:
                    from utils.logger import print_warning
                    print_warning("얼굴편집", "연결선/폴리곤 표시를 위해 랜드마크가 필요하지만 감지되지 않음")
                return

            # 현재 탭 가져오기
            current_tab = getattr(self, 'current_morphing_tab', '눈')
            
            # 원본 이미지에 랜드마크/연결선/폴리곤 표시
            # 저장된 위치 변수 사용 (성능 최적화: canvas.coords() 호출 제거)
            show_indices = self.show_landmark_indices.get() if hasattr(self, 'show_landmark_indices') else False
            self._draw_landmarks_on_canvas(
                self.canvas_original, 
                self.current_image, 
                landmarks,
                self.canvas_original_pos_x,
                self.canvas_original_pos_y,
                self.landmarks_items_original,
                "green",  # 원본 이미지는 초록색
                draw_points=show_landmarks,
                draw_lines=show_lines,  # 연결선 표시는 체크박스로 제어
                draw_polygons=show_polygons,  # 폴리곤 표시는 체크박스로 제어
                polygon_items_list=self.landmark_polygon_items['original'],  # 연결선과 폴리곤 아이템을 별도로 관리
                show_indices=show_indices  # 인덱스 번호 표시
            )
            
            # 원본 이미지에 변형된 랜드마크도 함께 표시 (랜드마크 기반 변형 모드일 때만)
            if (hasattr(self, 'use_landmark_warping') and 
                self.use_landmark_warping.get() and 
                hasattr(self, 'transformed_landmarks') and 
                self.transformed_landmarks is not None):
                # 기존 변형된 랜드마크 아이템 제거
                if hasattr(self, 'landmarks_items_transformed'):
                    for item_id in self.landmarks_items_transformed:
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmarks_items_transformed.clear()
                
                # 변형된 랜드마크를 빨간색으로 표시 (연결선 포함, 폴리곤은 제외)
                # 변형된 랜드마크의 연결선과 폴리곤도 landmark_polygon_items['original']에 추가
                self._draw_landmarks_on_canvas(
                    self.canvas_original,
                    self.current_image,
                    self.transformed_landmarks,
                    self.canvas_original_pos_x,
                    self.canvas_original_pos_y,
                    self.landmarks_items_transformed if hasattr(self, 'landmarks_items_transformed') else [],
                    "red",  # 변형된 랜드마크는 빨간색
                    draw_points=show_landmarks,
                    draw_lines=show_lines,  # 연결선 표시는 체크박스로 제어
                    draw_polygons=False,  # 변형된 랜드마크에는 폴리곤 표시하지 않음
                    polygon_items_list=self.landmark_polygon_items['original'],  # 연결선과 폴리곤 아이템을 별도로 관리
                    show_indices=show_indices  # 인덱스 번호 표시
                )
            
            # 선택된 부위의 중심점 그리기 (전체 탭이고 체크박스가 활성화되어 있을 때만)
            show_centers = self.show_region_centers.get() if hasattr(self, 'show_region_centers') else False
            if current_tab == "전체" and show_centers:
                self._draw_region_centers(
                    self.canvas_original,
                    self.current_image,
                    landmarks,
                    self.canvas_original_pos_x,
                    self.canvas_original_pos_y,
                    self.landmarks_items_original
                )

            # 편집된 이미지에 랜드마크 표시 제거 (불필요한 감지 및 렌더링 제거)
            # 편집된 이미지는 변형된 결과만 보여주면 되므로 랜드마크 표시 불필요
            
            # 바운딩 박스 표시 업데이트 (폴리곤이 체크되어 있을 때만)
            if show_polygons and hasattr(self, 'update_bbox_display'):
                self.update_bbox_display()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    
