"""
얼굴 편집 패널 - 미리보기 관리 Mixin
미리보기 표시 관련 기능을 담당
"""
import math
import time
import tkinter as tk
from PIL import Image, ImageTk

from gui.FaceForge.utils import landmarks as utilmarks

from .guide import GuideLinesManager

from utils.logger import log, debug, info
from gui.FaceForge.utils.debugs import DEBUG_PREVIEW_UPDATE, DEBUG_PREVIEW_RATIO, DEBUG_GUIDE_LINES_UPDATE, DEBUG_REGION_PIVOTS

class PreviewManagerMixin:

    _CHANGE_SOURCE_REFRESH_DEFAULTS = {
        'slider': dict(image=True, landmarks=True, overlays=True, guide_lines=True),
        'drag': dict(image=True, landmarks=True, overlays=True, guide_lines=True),
        'option': dict(image=False, landmarks=True, overlays=True, guide_lines=False),
        'programmatic': dict(image=True, landmarks=True, overlays=True, guide_lines=True),
        'none': dict(image=True, landmarks=False, overlays=False, guide_lines=False),
    }
    
    _REGION_FLAG_ATTRS = (
        'show_face_oval', 'show_left_eye', 'show_right_eye', 'show_left_eyebrow',
        'show_right_eyebrow', 'show_nose', 'show_lips', 'show_upper_lips',
        'show_lower_lips', 'show_left_iris', 'show_right_iris', 'show_contours',
        'show_tesselation'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if DEBUG_PREVIEW_UPDATE:
            debug("PreviewManagerMixin", f" : initialized..")
        self.guide_lines_manager = GuideLinesManager(self)

    def _initialize_face_feature_cache_state(self):
        if not hasattr(self, '_face_feature_update_in_progress'):
            self._face_feature_update_in_progress = False
        if not hasattr(self, '_face_feature_update_requested'):
            self._face_feature_update_requested = False
        if not hasattr(self, '_last_face_feature_signature'):
            self._last_face_feature_signature = None        

    def _initialize_display_update_state(self):
        if not hasattr(self, '_last_preview_update_signature'):
            self._last_preview_update_signature = None
        if not hasattr(self, '_last_change_source'):
            self._last_change_source = 'none'
        if not hasattr(self, '_last_displayed_original_image_id'):
            self._last_displayed_original_image_id = None
        if not hasattr(self, '_last_displayed_current_image_id'):
            self._last_displayed_current_image_id = None          

    def _set_change_source(self, source):
        """이벤트 소스 플래그를 안전하게 설정"""
        self._initialize_display_update_state()
        self._last_change_source = source            

    def _is_landmark_display_enabled(self):
        """랜드마크/폴리곤/연결선 렌더링이 필요한지 여부"""
        show_points = bool(getattr(self, 'show_landmark_points', None) and self.show_landmark_points.get())
        show_lines = bool(getattr(self, 'show_landmark_lines', None) and self.show_landmark_lines.get())
        show_polygons = bool(getattr(self, 'show_landmark_polygons', None) and self.show_landmark_polygons.get())
        return show_points or show_lines or show_polygons

    def _is_polygon_display_enabled(self):
        """눈/입술 영역 또는 폴리곤 오버레이가 필요한지 여부"""
        show_polygons = bool(getattr(self, 'show_landmark_polygons', None) and self.show_landmark_polygons.get())
        return show_polygons

    def _is_pivot_display_enabled(self):
        """눈/입술 영역 또는 폴리곤 오버레이가 필요한지 여부"""
        show_pivots = bool(getattr(self, 'show_landmark_pivots', None) and self.show_landmark_pivots.get())
        return show_pivots

    def _is_guides_display_enabled(self):
        return bool(getattr(self, 'show_guide_lines', None) and self.show_guide_lines.get())

    def _is_bbox_frame_display_enabled(self):
        return bool(getattr(self, 'show_bbox_frame', None) and self.show_bbox_frame.get())        

    def _compute_display_flags(self):
        polygon_flag = False
        try:
            polygon_flag = self._is_polygon_display_enabled()
        except Exception:  # pylint: disable=broad-except
            polygon_flag = False

        pivots_flag = False
        try:
            pivots_flag = self._is_pivot_display_enabled()
        except Exception:  # pylint: disable=broad-except
            pivots_flag = False

        guides_flag = False
        try:
            guides_flag = self._is_guides_display_enabled()
        except Exception:  # pylint: disable=broad-except
            guides_flag = False

        bbox_flag = False
        try:
            bbox_flag = self._is_bbox_frame_display_enabled()
        except Exception:  # pylint: disable=broad-except
            bbox_flag = False            

        return polygon_flag, pivots_flag, guides_flag, bbox_flag

    def _refresh_face_edit_display(
        self,
        *,
        image=True,
        polygons=None,
        pivots=None,
        guides=None,
        bbox=None,
        force_original=False,
    ):
        polygons_flag, pivots_flag, guide_lines_flag, bbox_flag = self._compute_display_flags()
        
        if polygons is not None:
            polygons_flag = polygons
        if pivots is not None:
            pivots_flag = pivots
        if guides is not None:
            guides_flag = guides
        if bbox is not None:
            bbox_flag = bbox

        if DEBUG_PREVIEW_UPDATE:
            debug("_refresh_face_edit_display", f": image={image}, polygons={polygons_flag}, pivots={pivots_flag}, guides={guides_flag}, bbox={bbox_flag}")

        self.clear_face_features_all()
        
        self.update_face_edit_display(
            image=image,
            polygons=polygons_flag,
            pivots=pivots_flag,
            guides=guides_flag,
            bbox=bbox_flag,
            force_original=force_original,
        )

    def _request_face_edit_refresh(
        self,
        *,
        image=None,
        polygons=None,
        pivots=None,
        guides=None,
        bbox=None,
        force_original=False,
    ):
        """이벤트 소스에 맞는 기본 플래그를 적용해 디스플레이 갱신 요청."""
        self._initialize_display_update_state()

        source = getattr(self, '_last_change_source', 'none') or 'none'
        defaults = self._CHANGE_SOURCE_REFRESH_DEFAULTS.get(
            source,
            self._CHANGE_SOURCE_REFRESH_DEFAULTS['none'],
        )

        if image is None:
            image = defaults['image']

        if polygons is None:
            polygons = defaults['polygons']
        if pivots is None:
            pivots = defaults['pivots']                        
        if guides is None:
            guides = defaults['guide_lines']
        if bbox is None:
            bbox = defaults['bbox']

        if not force_original and source == 'programmatic' and image:
            force_original = True

        # 오버레이/랜드마크 전용 갱신 시에도 이전 시그니처를 무효화해 중복 스킵 방지
        if image or polygons or pivots:
            self._last_preview_update_signature = None

        self._refresh_face_edit_display(
            image=image,
            polygons=polygons,
            pivots=pivots,
            guides=guides,
            bbox=bbox,
            force_original=force_original,
        )


    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""

        if not hasattr(self, 'guide_lines_manager'):
            self.guide_lines_manager = GuideLinesManager(self)

        # parent가 Toplevel이면 전체 창을 사용, 아니면 LabelFrame 사용

        preview_frame = tk.Frame(parent, padx=0, pady=0)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # 이미지 크기 (변수에서 가져오기, 없으면 기본값 사용)
        preview_width = getattr(self, 'preview_width', 800)
        preview_height = getattr(self, 'preview_height', 1000)

        # 좌측: 원본 이미지
        original_frame = tk.Frame(preview_frame)

        status_frame = tk.Frame(preview_frame)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)        
        
        original_frame.pack(fill=tk.BOTH, expand=True)

        # 상태바
        self.status_var = tk.StringVar(value="이미지를 열어주세요")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, relief=tk.FLAT)
        self.status_label.pack(fill=tk.X, pady=(0, 0))        
        
        original_top_frame = tk.Frame(original_frame)
        original_top_frame.pack(fill=tk.X)
        
        self.label_original = tk.Label(original_top_frame, text="원본 이미지", font=("", 9))
        self.label_original.pack(side=tk.LEFT)

        self.label_image_size = tk.Label(original_top_frame, text="사이즈", font=("", 9))
        self.label_image_size.pack(side=tk.LEFT, padx=(8, 0))

        self.label_face_axis = tk.Label(original_top_frame, text="얼굴축", font=("", 9))
        self.label_face_axis.pack(side=tk.LEFT, padx=(8, 0))

        self.save_parameters_btn = tk.Button(original_top_frame, width=16, text="Save Parameters", command=self.save_current_parameters, state=tk.NORMAL )
        self.save_parameters_btn.pack(side=tk.RIGHT,  padx=4)                

        self.save_image_btn = tk.Button(original_top_frame, width=16, text="Save Image", command=self.save_current_image, state=tk.NORMAL )
        self.save_image_btn.pack(side=tk.RIGHT,  padx=4)
        
        self.canvas_original = tk.Canvas(
            original_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        #self.canvas_original.pack(padx=5, pady=5)
        self.canvas_original.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 마우스 드래그 이벤트 바인딩
        self.canvas_original.bind("<Button-1>", self.on_canvas_original_drag_start)
        self.canvas_original.bind("<B1-Motion>", self.on_canvas_original_drag)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_original_drag_end)
        
        def on_canvas_resize(event):
            self.preview_width = event.width
            self.preview_height = event.height

            # 창 크기가 바뀌면 드래그 상태 초기화
            self.canvas_original_drag_start_x = None
            self.canvas_original_drag_start_y = None
            self.canvas_original_drag_start_image_x = None
            self.canvas_original_drag_start_image_y = None

            self.update_face_edit_display(
                image=True, 
                polygons=self._is_polygon_display_enabled(), 
                pivots=self._is_pivot_display_enabled(), 
                guides=self._is_guides_display_enabled(), 
                bbox=self._is_bbox_frame_display_enabled(), 
                force_original=True)
            
        self.canvas_original.bind("<Configure>", on_canvas_resize)            

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

            # 이벤트 쓰로틀링 - 빠른 휠 움직임 방지
            current_time = time.time()
            if current_time - self._last_wheel_time < 0.05:  # 50ms 이내
                return
            self._last_wheel_time = current_time
            
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
                max_scale = getattr(self, 'zoom_max_scale', 16.0)  # 최대 확대 비율
                min_scale = getattr(self, 'zoom_min_scale', 0.2)  # 최소 축소 비율                
                
                new_scale = old_scale
                if event.delta > 0:
                    # 확대
                    if old_scale < max_scale:
                        zoom_scale = round(old_scale * 1.1, 2)
                        new_scale = min(zoom_scale, max_scale)
                    else:
                        return
                elif event.delta < 0:
                    # 축소
                    if old_scale > min_scale:
                        zoom_scale = round(old_scale * 0.9, 2)  # 10% 축소
                        new_scale = max(zoom_scale, min_scale)
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
                    self.update_face_edit_display(
                        image=True,
                        polygons=self._is_polygon_display_enabled(),
                        pivots=self._is_pivot_display_enabled(),
                        guides=self._is_guides_display_enabled(),
                        bbox=self._is_bbox_frame_display_enabled(),
                        force_original=True,
                    )
                
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

    def show_original_preview(self, include_features=True):
        """원본 이미지 미리보기 표시"""
        if DEBUG_PREVIEW_UPDATE:
            debug("show_original_preview", f"current_image: {self.current_image is not None}, {id(self.current_image)}")

        if not (hasattr(self, 'canvas_original')
                and self.canvas_original
                and self.canvas_original.winfo_exists()):
            return            

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
            # 창 크기가 바뀌어도 기존 base_scale 유지
            if not hasattr(self, '_stable_base_scale'):
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
                
                self._stable_base_scale = base_scale
                self._stable_base_display_width = base_display_width
                self._stable_base_display_height = base_display_height
                base_ratio = base_display_width/base_display_height
                if DEBUG_PREVIEW_RATIO:
                    log("_stable_base_scale: None, ", f"base display[{base_ratio:.3f}, ( {base_display_width}, {base_display_height} )]")
            else:
                # 저장된 기본 스케일 사용
                base_scale = self._stable_base_scale
                base_display_width = self._stable_base_display_width
                base_display_height = self._stable_base_display_height
                base_ratio = base_display_width/base_display_height
                if DEBUG_PREVIEW_RATIO:
                    log("stable_base_scale: True, ", f"base display[{base_ratio:.3f}, ( {base_display_width}, {base_display_height} )]")
            
            # 확대/축소 비율 적용 (원본 전용)
            # 화면 크기가 바뀌어도 기존 확대/축소 비율 유지
            if not hasattr(self, 'zoom_scale_original'):
                self.zoom_scale_original = 1.0
            zoom_scale_original = self.zoom_scale_original

            display_width = int(base_display_width * zoom_scale_original)
            display_height = int(base_display_height * zoom_scale_original)

            base_ratio = base_display_width/base_display_height
            display_ratio = display_width/display_height

            if DEBUG_PREVIEW_RATIO:
                info("show_original_preview", 
                    f"canvas[ {canvas_ratio:.3f}, ({preview_width}, {preview_height}) ], "
                    f"image[ {img_ratio:.3f}, ({img_width}, {img_height}) ], \n"
                    f"base[ {base_ratio:.3f}, ({base_display_width}, {base_display_height}) ], "
                    f"display[ {display_ratio:.3f}, ({display_width}, {display_height}) ]")            
            
            # 원본 이미지 기본 크기 저장 (처음 로드 시)
            # 화면 크기가 바뀌어도 기본 크기 유지
            if self.original_image_base_size is None:
                self.original_image_base_size = (base_display_width, base_display_height)
            else:
                # 기존 기본 크기 유지하되, 새 화면 크기에 맞게 조정
                old_base_width, old_base_height = self.original_image_base_size
                if preview_width != old_base_width or preview_height != old_base_height:
                    # 화면 크기가 바뀌면 기본 크기도 업데이트
                    self.original_image_base_size = (base_display_width, base_display_height)
            
            # 성능 최적화된 이미지 리사이즈
            try:
                from .optimizer import _optimizer
                scale_factor = zoom_scale_original
                resized = _optimizer.optimized_resize(
                    self.current_image, (display_width, display_height), scale_factor
                )
            except ImportError:
                # 폴백: 기존 방식
                if display_width > self.current_image.size[0] or display_height > self.current_image.size[1]:
                    resized = self.current_image.resize((display_width, display_height), Image.BILINEAR)
                else:
                    resized = self.current_image.resize((display_width, display_height), Image.LANCZOS)
            
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
            
            # 이미지를 먼저 그리기 (폴리곤이 위에 오도록)
            self.image_created_original = self.canvas_original.create_image(
                self.canvas_original_pos_x,
                self.canvas_original_pos_y,
                anchor=tk.CENTER,
                image=self.tk_image_original,
                tags="image"
            )
            
            # 캔버스에 표시 크기 저장 (드래그 경계 계산용)
            self.canvas_original.display_size = (display_width, display_height)
            
            self.update_preview_canvas(self.current_image)
                
        except Exception as e:
            print(f"[원본 이미지 미리보기] 오류 발생: {e}")
            pass

    def _build_preview_update_signature(
        self,
        image,
        polygons,
        pivots,
        guides,
        bbox,
        force_original,
        should_update_original,
        should_update_current,
    ):
        current_image = getattr(self, 'current_image', None)
        current_id = (
            id(current_image)
            if should_update_current and current_image is not None
            else getattr(self, '_last_displayed_current_image_id', None)
        )
        original_image = getattr(self, 'original_image', None)
        original_id = (
            id(original_image)
            if should_update_original and original_image is not None
            else getattr(self, '_last_displayed_original_image_id', None)
        )
        return (
            image,
            polygons,
            pivots,
            guides,
            bbox,
            force_original,
            current_id,
            original_id,

            self.canvas_original_pos_x,
            self.canvas_original_pos_y,
            self.canvas_edited_pos_x,
            self.canvas_edited_pos_y,
        )

    def update_face_edit_display(
        self,
        image=True,
        polygons=False,
        pivots=False,
        guides=False,
        bbox=False,
        *,
        force_original=False,
    ):
        """미리보기/오버레이/랜드마크 갱신을 단일 진입점으로 처리"""
        has_canvas_original = (
            hasattr(self, 'canvas_original')
            and self.canvas_original is not None
            and self.canvas_original.winfo_exists()
        )
        last_signature = getattr(self, '_last_preview_update_signature', None)

        if DEBUG_PREVIEW_UPDATE:
            print()
            info("update_face_edit_display", 
                f"polygons={polygons},pivots={pivots},guides={guides},bbox={bbox},force={force_original}, "
                f"original={ id(self.original_image) if self.current_image else 'None'}, "
                f"current={ id(self.current_image) if self.current_image else 'None'}, "
                #f"\n{last_signature}, canvas={has_canvas_original}"
            )

        if not has_canvas_original:
            return

        self._initialize_display_update_state()

        image_created_original = getattr(self, 'image_created_original', None)
        has_original_canvas_image = image_created_original is not None
        has_current_image = getattr(self, 'current_image', None) is not None

        should_update_original = False
        if force_original:
            should_update_original = True
        elif image and not has_original_canvas_image:
            should_update_original = True

        should_update_current = image and has_current_image

        requested_signature = self._build_preview_update_signature(
            image,
            polygons,
            pivots,
            guides,
            bbox,
            force_original,
            should_update_original,
            should_update_current,
        )

        if requested_signature == last_signature:
            if DEBUG_PREVIEW_UPDATE:
                info("update_face_edit_display", "Skipping duplicate update")
            return

        try:

            if image:
                if should_update_original and self.current_image is not None:
                    #self.show_original_preview(include_features=False)
                    self._last_displayed_original_image_id = id(self.current_image)
                elif should_update_original:
                    self._last_displayed_original_image_id = None

                if should_update_current:
                    self.show_original_preview(include_features=False)
                    self._last_displayed_current_image_id = id(self.current_image)

                else:
                    self._last_displayed_current_image_id = None

            elif force_original and self.current_image is not None:
                self.show_original_preview(include_features=False)
                self._last_displayed_original_image_id = id(self.current_image)
            elif force_original:
                self.show_original_preview(include_features=False)
                self._last_displayed_original_image_id = None
            
            self.draw_overlays_current()
            self._last_preview_update_signature = requested_signature
        finally:
            # 이벤트 소스 초기화 (다음 업데이트를 위해 비움)
            self._last_change_source = 'none'

    
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
            self.canvas_original.delete("region_pivot")
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


    def clear_face_features_all(self):
        """모든 오버레이 요소 제거 (폴리곤, 가이드선, 피벗, bbox)"""
        try:
            
            for item_id in self.landmarks_items_original:
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmarks_items_original.clear()

            for item_id in self.landmarks_items_edited:
                try:
                    self.canvas_edited.delete(item_id)
                except Exception:
                    pass
            self.landmarks_items_edited.clear()
            
            for item_id in self.landmarks_items_transformed:
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmarks_items_transformed.clear()

            # 폴리곤 아이템 제거
            for item_id in self.landmark_polygon_items['original']:
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items['original'].clear()
            self.polygon_point_map_original.clear()
            
            for item_id in self.landmark_polygon_items['edited']:
                try:
                    self.canvas_edited.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items['edited'].clear()
            self.polygon_point_map_edited.clear()
            
            # 가이드선 제거
            if hasattr(self, 'guide_lines_manager'):
                self.guide_lines_manager.clear_guide_lines(self.canvas_original, 'original')
            
            # pivot 제거
            try:
                self.canvas_original.delete("region_pivot")
            except Exception:
                pass
            
            # bbox 제거
            if hasattr(self, 'clear_bbox_display'):
                self.clear_bbox_display()
                
            # 폴리곤 태그로 제거
            try:
                self.canvas_original.delete("landmarks_polygon")
                self.canvas_original.delete("landmarks_polygon_fill")
            except Exception:
                pass
            
        except Exception as e:
            if DEBUG_PREVIEW_UPDATE:
                warn("clear_all_overlays", f": {e}")


    def update_face_features_display(self, desc=""):
        """얼굴 특징 표시 업데이트 (랜드마크 포인트, 연결선, 폴리곤)"""
        if DEBUG_PREVIEW_UPDATE:
            warn("update_face_features_display",f": {desc}")

        self._initialize_face_feature_cache_state()
        if getattr(self, '_face_feature_update_in_progress', False):
            self._face_feature_update_requested = True
            return

        self._face_feature_update_in_progress = True
        self._face_feature_update_requested = False

        try:
            show_polygons = self.show_landmark_polygons.get() if hasattr(self, 'show_landmark_polygons') else False
            show_pivots = self.show_landmark_pivots.get() if hasattr(self, 'show_landmark_pivots') else False
            show_guides = self.show_guide_lines.get() if hasattr(self, 'show_guide_lines') else False
            show_bbox = self.show_bbox_frame.get() if hasattr(self, 'show_bbox_frame') else False
            if DEBUG_PREVIEW_UPDATE:
                debug("update_face_features_display",f": polygons:{show_polygons}, pivots:{show_pivots}, guides:{show_guides}, bbox:{show_bbox}")

            signature = self._build_face_feature_signature(None, show_polygons, show_pivots, show_guides, show_bbox)
            if self._last_face_feature_signature == signature:
                return
            self._last_face_feature_signature = signature

            # 바운딩 박스 표시 업데이트
            show_bbox = self.show_bbox_frame.get() if hasattr(self, 'show_bbox_frame') else False
            if show_bbox and hasattr(self, '_draw_bbox'):
                self._draw_bbox()            


            # 랜드마크 감지 (원본 이미지) - 연결선만 표시해도 랜드마크 좌표 필요
            # 커스텀 랜드마크가 있으면 사용, 없으면 새로 감지
            landmarks = self.landmark_manager.get_current_landmarks()
            if landmarks is None:
                if show_polygons:
                    from utils.logger import print_warning
                    warn("update_face_features_display", "연결선/폴리곤 표시를 위해 랜드마크가 필요하지만 감지되지 않음")
                return

            signature = self._build_face_feature_signature(landmarks, show_polygons, show_pivots, show_guides, show_bbox)
            if self._last_face_feature_signature == signature:
                return
            self._last_face_feature_signature = signature

            # 현재 탭 가져오기
            current_tab = getattr(self, 'current_morphing_tab', '눈')
            
            # 원본 이미지에 랜드마크/연결선/폴리곤 표시
            # 저장된 위치 변수 사용 (성능 최적화: canvas.coords() 호출 제거)
            show_indices = self.show_landmark_indices.get() if hasattr(self, 'show_landmark_indices') else False
            self._draw_landmark_polygons(
                self.canvas_original, 
                self.current_image,               
                landmarks,
                self.canvas_original_pos_x,
                self.canvas_original_pos_y,
                self.landmark_polygon_items['original'],  # 연결선과 폴리곤 아이템을 별도로 관리
                self.show_polygon_color.get() if hasattr(self, 'show_polygon_color') else "green", 
                current_tab
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
            show_pivots = self.show_landmark_pivots.get() if hasattr(self, 'show_landmark_pivots') else False
            if show_pivots:
                self._draw_pivots(
                    self.canvas_original,
                    self.current_image,
                    landmarks,
                    self.canvas_original_pos_x,
                    self.canvas_original_pos_y,
                    self.landmarks_items_original
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            self._face_feature_update_in_progress = False
            if getattr(self, '_face_feature_update_requested', False):
                self._face_feature_update_requested = False

    def _build_face_feature_signature(self, landmarks, show_polygons, show_pivots, show_guides, show_bbox):
        region_state = tuple(self._get_var_value(name) for name in self._REGION_FLAG_ATTRS)
        zoom = round(getattr(self, 'zoom_scale_original', 1.0), 4)
        pos_x = round(self.canvas_original_pos_x or 0, 2) if getattr(self, 'canvas_original_pos_x', None) is not None else None
        pos_y = round(self.canvas_original_pos_y or 0, 2) if getattr(self, 'canvas_original_pos_y', None) is not None else None
        landmark_sig = self._compute_landmark_checksum(landmarks)
        return (
            landmark_sig,
            show_polygons,
            show_pivots,
            show_guides,
            show_bbox,
            region_state,
            zoom,
            pos_x,
            pos_y,
            landmark_sig
        )

    def _compute_landmark_checksum(self, landmarks):
        if not landmarks:
            return None
        length = len(landmarks)
        if length == 0:
            return None
        sample_indices = [0, length // 2, length - 1]
        samples = []
        for idx in sample_indices:
            if idx < 0 or idx >= length:
                continue
            point = landmarks[idx]
            if isinstance(point, tuple):
                x, y = point[:2]
            else:
                x = getattr(point, 'x', 0)
                y = getattr(point, 'y', 0)
            try:
                x_val = float(x)
                y_val = float(y)
            except (TypeError, ValueError):
                x_val, y_val = 0.0, 0.0
            samples.append(round(x_val, 3))
            samples.append(round(y_val, 3))
        return (length, tuple(samples))                

    def _get_var_value(self, attr_name):
        var = getattr(self, attr_name, None)
        if var is None or not hasattr(var, 'get'):
            return None
        try:
            return var.get()
        except Exception:
            return None


    """랜드마크 표시 기능 Mixin"""   