import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os

from .drag import CanvasDragMixin
from .drawing import DrawingsMixin
from .file import FileManagerMixin
from .handler import HandlersMixin
from .landmark import LandmarkManager
from .polygon import PolygonBuilderMixin
from .popup import PopupManagerMixin
from .preview import PreviewManagerMixin
from .region import RegionPanelMixin
from .render import RenderManagerMixin
from .warp import WarpingMixin
from .transform import TransformMixin

from utils.logger import debug, error, log, info
from gui.FaceForge.utils import settings as settings
from gui.FaceForge.utils.debugs import DEBUG_INIT_SETTINGS, DEBUG_PREVIEW_UPDATE

class FaceForgePanel(
    CanvasDragMixin,
    DrawingsMixin,
    FileManagerMixin,
    HandlersMixin,
    LandmarkManager,
    PolygonBuilderMixin,    
    PopupManagerMixin,        
    PreviewManagerMixin,
    RegionPanelMixin,
    RenderManagerMixin,
    WarpingMixin,
    TransformMixin,
    tk.Toplevel,    
):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("FaceForge - 얼굴 모핑")
        self.geometry("800x600+400+0")

        # MediaPipe 부위 선택 변수 (전체 탭용)
        self.show_left_iris = tk.BooleanVar(value=False)  # Left Iris 표시 여부 (refine_landmarks=True일 때만 사용 가능)
        self.show_right_iris = tk.BooleanVar(value=False)  # Right Iris 표시 여부 (refine_landmarks=True일 때만 사용 가능)        
        self.show_face_oval = tk.BooleanVar(value=False)  # Face Oval 표시 여부        
        self.show_left_eyebrow = tk.BooleanVar(value=False)  # Left Eyebrow 표시 여부
        self.show_right_eyebrow = tk.BooleanVar(value=False)  # Right Eyebrow 표시 여부
        self.show_nose = tk.BooleanVar(value=False)  # Nose 표시 여부
        self.show_left_eye = tk.BooleanVar(value=False)  # Left Eye 표시 여부
        self.show_right_eye = tk.BooleanVar(value=False)  # Right Eye 표시 여부        
        self.show_lips = tk.BooleanVar(value=False)  # Lips 표시 여부 (하위 호환성 유지)
        self.show_upper_lips = tk.BooleanVar(value=False)  # Upper Lips 표시 여부
        self.show_lower_lips = tk.BooleanVar(value=False)  # Lower Lips 표시 여부
        self.show_contours = tk.BooleanVar(value=False)  # Contours 표시 여부
        self.show_tesselation = tk.BooleanVar(value=False)  # Tesselation 표시 여부        

        self.show_polygon_color = tk.StringVar(value="green")  # Tesselation 표시 여부

        self.polygon_edit_mode = tk.BooleanVar(value=False)
        self.use_landmark_warping = tk.BooleanVar(value=False)  # 랜드마크 직접 변형 모드 사용 여부 (기본값: False)

        self.show_landmark_polygons = tk.BooleanVar(value=True)  # 랜드마크 폴리곤 표시 여부 (기본값: False)
        self.show_landmark_pivots = tk.BooleanVar(value=False)  # 부위 중심점 표시 여부 (기본값: False)                
        self.show_guide_lines = tk.BooleanVar(value=False)  # 지시선 표시 여부 (기본값: False)
        self.show_bbox_frame = tk.BooleanVar(value=False)  # 눈중심으로 얼굴을 포함한 경계박스 표시 여부 (기본값: False)        


        self.dragging_polygon = False  # 폴리곤에서 포인트 드래그 중 여부
        self.dragging_index = None  # 드래그 중인 포인트 인덱스

        self._last_cleanup_time = 0
        self._last_drag_update_time = 0
        self._last_wheel_time = 0        

        self.polygon_drag_start_x = None  # 드래그 시작 x 좌표
        self.polygon_drag_start_y = None  # 드래그 시작 y 좌표
        self.polygon_drag_start_img_x = None  # 드래그 시작 이미지 x 좌표
        self.polygon_drag_start_img_y = None  # 드래그 시작 이미지 y 좌표        

        # 공통 슬라이더 변수 (선택된 모든 부위에 공통 적용)
        self.region_pivot_x = tk.DoubleVar(value=0.0)  # 중심점 X (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_pivot_y = tk.DoubleVar(value=0.0)  # 중심점 Y (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_size_x = tk.DoubleVar(value=1.0)  # 크기 비율 X (0.5 ~ 2.0, 기본값: 1.0)
        self.region_size_y = tk.DoubleVar(value=1.0)  # 크기 비율 Y (0.5 ~ 2.0, 기본값: 1.0)
        self.region_position_x = tk.DoubleVar(value=0.0)  # 위치 이동 X (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_position_y = tk.DoubleVar(value=0.0)  # 위치 이동 Y (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_expansion_level = tk.IntVar(value=1)  # 폴리곤 주변 확장 레벨 (0~5, 기본값: 1)

        # 파일 관련 변수
        self.face_edit_dir = None
        self._face_file = None
        self._loading_file = None        
        self._save_file_dir = None
        self._window_config = None
        self._recent_files = []

        # 미리보기 이미지
        self.tk_image_original = None
        self.tk_image_edited = None
        self.image_created_original = None
        self.image_created_edited = None        


        # 이미지 위치 추적 변수 (드래그용)
        self.canvas_original_pos_x = None
        self.canvas_original_pos_y = None
        self.canvas_edited_pos_x = None
        self.canvas_edited_pos_y = None
        self.canvas_original_drag_start_x = None
        self.canvas_original_drag_start_y = None
        self.canvas_edited_drag_start_x = None
        self.canvas_edited_drag_start_y = None
        self.canvas_original_drag_start_image_x = None
        self.canvas_original_drag_start_image_y = None
        self.canvas_edited_drag_start_image_x = None
        self.canvas_edited_drag_start_image_y = None

        # 현재 선택된 이미지
        self.current_image = None
        self.current_image_path = None

        # 바운딩 박스 표시용 캔버스 아이템
        self.bbox_back_original = None  # 원본 이미지의 바운딩 박스 새도우
        self.bbox_rect_original = None  # 원본 이미지의 바운딩 박스 사각형

        # 랜드마크 표시용 캔버스 아이템
        self.landmarks_items_original = []  # 원본 이미지의 랜드마크 아이템
        self.landmarks_items_edited = []  # 편집된 이미지의 랜드마크 아이템
        self.landmarks_items_transformed = []  # 원본 이미지에 표시되는 변형된 랜드마크 아이템        

        # 폴리곤에 포함된 포인트 인덱스 (set으로 변경: dict에서 True만 저장하던 것을 간소화)
        self.polygon_point_map_original = set()  # 원본 캔버스의 폴리곤 포인트 인덱스
        self.polygon_point_map_edited = set()  # 편집 캔버스의 폴리곤 포인트 인덱스        
        
        # 폴리곤 캔버스 아이템 ID (캔버스별로 분리)
        self.landmark_polygon_items = {
            'original': [],  # 원본 캔버스의 폴리곤 아이템
            'edited': [],     # 편집 캔버스의 폴리곤 아이템
            'current': []     # 편집 캔버스의 폴리곤 아이템
        }

        self.landmark_manager = LandmarkManager()        

        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.close_popup)

        settings.load_settings(self)
        if DEBUG_INIT_SETTINGS:
            print(f"{'-'*50}", 
                f"\n _face_file: {self._face_file}, face_edit_dir: {self.face_edit_dir}, "
                f"_loading_file: {self._loading_file}, _save_file_dir: {self._save_file_dir}")
            
        
        # UI 생성
        self.create_widgets()

        # 팝업 생성
        self.file_list_popup = None
        self.settings_popup = None
        self.preview_popup = None

        self.create_popup()      



    # ========== 랜드마크 Property (직접 참조, 복사본 없음) ==========

    @property
    def original_face_landmarks(self):
        """사용자 수정 랜드마크 (LandmarkManager의 _custom_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._original_face_landmarks  # 직접 참조                        

    @property
    def current_face_landmarks(self):
        """사용자 수정 랜드마크 (LandmarkManager의 _custom_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._current_face_landmarks  # 직접 참조                

    @property
    def custom_landmarks(self):
        """사용자 수정 랜드마크 (LandmarkManager의 _custom_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._custom_landmarks  # 직접 참조
    
    @property
    def original_landmarks(self):
        """원본 랜드마크 (LandmarkManager의 get_original_landmarks_full() 직접 참조, 복사본 없음)
        
        주의: 기본적으로 직접 참조 반환 (복사본 없음)
        눈동자 포함이 필요하면 get_copied_original_landmarks_full_with_iris() 사용
        """
        return self.landmark_manager.get_original_landmarks_full()  # 468개 (직접 참조, 복사본 없음)        
    
    @property
    def face_landmarks(self):
        """현재 편집된 랜드마크 (LandmarkManager의 _face_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._face_landmarks  # 직접 참조 (복사본 없음)
    
    @property
    def transformed_landmarks(self):
        """변형된 랜드마크 (LandmarkManager의 _transformed_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._transformed_landmarks  # 직접 참조 (복사본 없음)
    
    def create_popup(self):
        """팝업 생성"""
        self.show_files_popup()
        self.show_settings_popup()

    def close_popup(self):
        """창 닫기"""
        try:
            print(f"{'-'*50}", f"\nface_edit_dir: {self.face_edit_dir}")
            # 설정 저장
            settings.save_settings(self)
            
            # 팝업창 닫기
            if self.file_list_popup and self.file_list_popup.winfo_exists():
                self.file_list_popup.destroy()
            if self.settings_popup and self.settings_popup.winfo_exists():
                self.settings_popup.destroy()
            if self.preview_popup and self.preview_popup.winfo_exists():
                self.preview_popup.destroy()
            
            self.destroy()
        except Exception as e:
            print(f"창 닫기 실패: {e}")
            self.destroy()

        
    def create_widgets(self):
        """UI 위젯 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 상단: 버튼 프레임
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_file_select = tk.Button(button_frame, text="파일 선택", command=self.show_files_popup, width=12)
        btn_file_select.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_settings = tk.Button(button_frame, text="편집 설정", command=self.show_settings_popup, width=12)
        btn_settings.pack(side=tk.LEFT, padx=(0, 5))

        btn_settings = tk.Button(button_frame, text="미리보기", command=self.show_preview_popup, width=12)
        btn_settings.pack(side=tk.LEFT, padx=(0, 5))


        def toggle_polygon_edit_mode():
            self.polygon_edit_mode.set(not self.polygon_edit_mode.get())
            if self.polygon_edit_mode.get():
                self.edit_polygon_btn.config(bg="lightgreen")
                self.canvas_original.config(cursor="crosshair")
            else:
                self.edit_polygon_btn.config(bg="SystemButtonFace")
                self.canvas_original.config(cursor="arrow")

        self.edit_polygon_btn = tk.Button(
            button_frame,
            text="폴리곤 편집", 
            command=toggle_polygon_edit_mode
        )
        self.edit_polygon_btn.pack(side=tk.LEFT, padx=5)


        checkbox_frame = tk.Frame(button_frame)
        checkbox_frame.pack(side=tk.LEFT, padx=(0, 5))

        # 부위 선택 체크박스 생성 함수
        def create_overlays_checkbox(parent, text, variable, row, col, exclusive_handler=None):
            def on_check_change():
                if exclusive_handler:
                    exclusive_handler()
                self.on_region_selection_change(text)
            
            check = tk.Checkbutton(
                parent,
                text=text,
                variable=variable,
                command=on_check_change
            )
            check.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            return check
        
        self.landmark_warping_check = create_overlays_checkbox(checkbox_frame, "warping", self.use_landmark_warping, 0, 0, None)
        self.landmark_warping_check.config(command = self.on_warping_change)
        
        self.landmark_polygon_check = create_overlays_checkbox(checkbox_frame, "polygon", self.show_landmark_polygons, 0, 1, None)
        self.landmark_pivot_check = create_overlays_checkbox(checkbox_frame, "pivot", self.show_landmark_pivots, 0, 2, None)        
        self.guide_lines_check = create_overlays_checkbox(checkbox_frame, "guide", self.show_guide_lines, 0, 3, None)
        self.bbox_frame_check = create_overlays_checkbox(checkbox_frame, "bbox", self.show_bbox_frame, 0, 4, None)

        self._create_preview_ui(main_frame)
        
    def open_image(self):
        """이미지 파일 열기"""
        file_types = [
            ("이미지 파일", "*.jpg *.jpeg *.jfif *.png *.bmp *.tiff"),
            ("모든 파일", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.image_path = file_path
                self.current_image = Image.open(file_path)
                self.display_image()
                self.process_btn.config(state=tk.NORMAL)
                self.status_var.set(f"이미지 로드됨: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("오류", f"이미지를 열 수 없습니다: {e}")
                self.status_var.set("이미지 로드 실패")
    
    def display_image(self):
        """캔버스에 이미지 표시"""
        if not self.current_image:
            return
            
        # 캔버스 크기에 맞게 이미지 리사이즈
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
        
        # 이미지 비율 유지하며 리사이즈
        img_ratio = self.current_image.width / self.current_image.height
        canvas_ratio = canvas_width / canvas_height
        
        if img_ratio > canvas_ratio:
            new_width = canvas_width - 20
            new_height = int(new_width / img_ratio)
        else:
            new_height = canvas_height - 20
            new_width = int(new_height * img_ratio)
        
        display_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_image)
        
        # 캔버스 중앙에 이미지 배치
        self.canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.tk_image, tags="image")
    
    def detect_face(self):
        """얼굴 감지 (임시 구현)"""
        if not self.current_image:
            return
            
        self.status_var.set("얼굴 감지 중...")
        # TODO: MediaPipe 얼굴 감지 구현
        self.status_var.set("얼굴 감지 완료 (기능 구현 예정)")
        self.save_btn.config(state=tk.NORMAL)
    
    def save_current_image(self):
        """이미지 저장"""
        if not self.current_image:
            return            

        file_types = [("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("All files", "*.*")]
        
        file_path = filedialog.asksaveasfilename(
            title="이미지 저장",
            defaultextension=".png",
            filetypes=file_types
        )
        
        if file_path:
            try:
                self.save_image(file_path)
                self.status_var.set(f"저장 완료: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
                self.status_var.set("저장 실패")

    def save_current_parameters(self):
        """이미지 저장"""
        if not self.current_image:
            return
        
        file_path = self.current_image_path
        if file_path:
            try:
                self.save_parameters(file_path)                
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")

    def _render_popup_image(self, entry):
        
        entry["is_rendering"] = True
        try:
            popup = entry["window"]
            label = entry["label"]
            raw = entry["original_image"]
            width, height = entry.get("size", raw.size)  # 창 내부 크기
            img_w, img_h = raw.size
            if width <= 0 or height <= 0:
                return
        
            scale = min(width / img_w, height / img_h)  # 비율 유지
            target_w = max(1, int(img_w * scale))
            target_h = max(1, int(img_h * scale))
            img = raw.copy()
            img = img.resize((target_w, target_h), Image.LANCZOS)
        
            tk_img = ImageTk.PhotoImage(img)
            label.config(image=tk_img)
            label.image = tk_img

            entry["last_render_size"] = (target_w, target_h)

        finally:

            entry["is_rendering"] = False


    def show_image_popup(self, image, title="Preview", fit=None, size=None):
        if not hasattr(self, "_image_popups"):
            self._image_popups = {}
        try:

            cached_bbox = self.landmark_manager.get_original_bbox(image.size[0], image.size[1] )
            if cached_bbox:
                cropped = image.crop(cached_bbox)
            else:
                cropped = image

            def _bind_resize_handler(entry):

                if entry.get("resize_bound"):
                    return

                def _remember_size(event, entry=entry):
                    if entry.get("is_rendering"):
                        return
                    new_size = (event.width, event.height)
                    if new_size == entry.get("size"):
                        return
                    if new_size == entry.get("last_render_size"):
                        return
                    entry["size"] = new_size

                    #print("resizing:", new_size)

                    self._render_popup_image(entry)

                entry["window"].bind("<Configure>", _remember_size, add="+")
                entry["resize_bound"] = True

            popup_entry = self._image_popups.get(title)
            if popup_entry is None:
                popup = tk.Toplevel(self)
                popup.title(title)
                popup.transient(self)
                popup_entry = {"window": popup}
                self._image_popups[title] = popup_entry

                if size:
                    width, height = size
                else:
                    width, height = cropped.width, cropped.height

                popup.geometry(f"{width}x{height}")

            else:
                popup = popup_entry["window"]
                if not popup.winfo_exists():
                    # 기존 엔트리 완전히 삭제
                    del self._image_popups[title]

                    popup = tk.Toplevel(self)
                    popup.title(title)
                    popup.transient(self)
                    popup_entry = {"window": popup}
                    self._image_popups[title] = popup_entry
                    
                    if size:
                        width, height = size
                    else:
                        width, height = cropped.width, cropped.height
                    popup.geometry(f"{width}x{height}")
                else:
                    # 재사용 경로에서도 반드시 값 할당
                    width = popup.winfo_width()
                    height = popup.winfo_height()

            content = popup_entry.get("frame") if popup_entry else None
            if content is None:
                content = tk.Frame(popup)
                content.pack(fill="both", expand=True)
                content.pack_propagate(False)
                popup_entry["frame"] = content
                label = tk.Label(content)
                label.pack(expand=True)
                popup_entry["label"] = label
            else:
                label = popup_entry["label"]



            popup_entry["size"] = (width, height)
            popup_entry["original_image"] = cropped   # ← 먼저 저장
            popup_entry["last_render_size"] = None

            _bind_resize_handler(popup_entry)

            self._render_popup_image(popup_entry)

            popup.deiconify()
            popup.lift()

            if DEBUG_PREVIEW_UPDATE:
                print("show_image_popup", f"image={id(image)}")

        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
