"""
얼굴 편집 패널 - 메인 클래스
모든 Mixin을 상속받아 통합된 FaceEditPanel 클래스를 제공
클래스 정의 및 초기화 로직을 담당
"""
import tkinter as tk
from PIL import Image, ImageTk

from .file import FileManagerMixin
from .preview import PreviewManagerMixin
from .polygon_renderer import PolygonRendererMixin
from .landmark_display import LandmarkDisplayMixin
from .tab_renderer import TabRendererMixin
from .canvas_drag_handler import CanvasDragHandlerMixin
from .polygon_drag_handler import PolygonDragHandlerMixin
from .canvas import CanvasEventHandlerMixin
from .slider_ui import SliderUIMixin
from .morphing import MorphingManagerMixin
from .style import StyleManagerMixin
from .age import AgeManagerMixin
from .widget_creator import WidgetCreatorMixin


class FaceEditPanel(
    tk.Toplevel,
    FileManagerMixin,
    PreviewManagerMixin,
    PolygonRendererMixin,
    LandmarkDisplayMixin,
    TabRendererMixin,
    CanvasDragHandlerMixin,
    PolygonDragHandlerMixin,
    CanvasEventHandlerMixin,
    SliderUIMixin,
    MorphingManagerMixin,
    StyleManagerMixin,
    AgeManagerMixin,
    WidgetCreatorMixin
):
    """얼굴 편집 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 편집")
        self.resizable(True, True)  # 리사이즈 허용
        
        # 메인 창 캔버스 초기 크기 설정 (먼저 정의)
        self.canvas_initial_width = 384  # 캔버스 초기 너비
        self.canvas_initial_height = 480  # 캔버스 초기 높이
        self.canvas_min_width = 288  # 캔버스 최소 너비
        self.canvas_min_height = 360  # 캔버스 최소 높이
        
        # 창 최소 크기 설정 (캔버스 최소값 * 2 + 여백)
        # 두 캔버스가 최소값까지 줄어들 수 있도록 창 최소 크기 설정
        min_window_width = (self.canvas_min_width * 2) + 50  # 두 캔버스 + 여백
        min_window_height = self.canvas_min_height + 100  # 캔버스 + 버튼 + 여백
        self.minsize(min_window_width, min_window_height)  # 최소 크기 설정
        
        # 현재 선택된 이미지
        self.current_image = None
        self.current_image_path = None
        self.aligned_image = None  # 정렬된 이미지 (편집의 기반)
        self.edited_image = None  # 편집된 이미지 (최종 결과)
        
        # 얼굴 랜드마크 정보 (나중에 추가)
        self.face_landmarks = None
        
        # 얼굴 특징 보정 설정 (Phase 1)
        self.eye_size = tk.DoubleVar(value=1.0)  # 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.nose_size = tk.DoubleVar(value=1.0)  # 코 크기 (0.5 ~ 2.0, 기본값: 1.0)
        # 입술 편집 설정 (5가지: 윗입술 모양, 아랫입술 모양, 윗입술 너비, 아랫입술 너비, 입 벌림 정도)
        self.upper_lip_shape = tk.DoubleVar(value=1.0)  # 윗입술 모양/두께 (0.5 ~ 2.0, 기본값: 1.0)
        self.lower_lip_shape = tk.DoubleVar(value=1.0)  # 아랫입술 모양/두께 (0.5 ~ 2.0, 기본값: 1.0)
        self.upper_lip_width = tk.DoubleVar(value=1.0)  # 윗입술 너비 (0.5 ~ 2.0, 기본값: 1.0)
        self.lower_lip_width = tk.DoubleVar(value=1.0)  # 아랫입술 너비 (0.5 ~ 2.0, 기본값: 1.0)
        self.upper_lip_vertical_move = tk.DoubleVar(value=0.0)  # 윗입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=위로, 음수=아래로)
        self.lower_lip_vertical_move = tk.DoubleVar(value=0.0)  # 아랫입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=아래로, 음수=위로)
        self.jaw_size = tk.DoubleVar(value=0.0)  # 턱선 조정 (-50 ~ +50, 기본값: 0.0)
        self.face_width = tk.DoubleVar(value=1.0)  # 얼굴 너비 (0.5 ~ 2.0, 기본값: 1.0)
        self.face_height = tk.DoubleVar(value=1.0)  # 얼굴 높이 (0.5 ~ 2.0, 기본값: 1.0)
        
        # 눈 편집 고급 설정
        self.left_eye_size = tk.DoubleVar(value=1.0)  # 왼쪽 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.right_eye_size = tk.DoubleVar(value=1.0)  # 오른쪽 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.eye_spacing = tk.BooleanVar(value=False)  # 눈 간격 조정 활성화 여부
        self.left_eye_position_y = tk.DoubleVar(value=0.0)  # 왼쪽 눈 수직 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.right_eye_position_y = tk.DoubleVar(value=0.0)  # 오른쪽 눈 수직 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.left_eye_position_x = tk.DoubleVar(value=0.0)  # 왼쪽 눈 수평 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.right_eye_position_x = tk.DoubleVar(value=0.0)  # 오른쪽 눈 수평 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.show_eye_region = tk.BooleanVar(value=False)  # 눈 영역 표시 여부 (기본값: True)
        self.show_lip_region = tk.BooleanVar(value=False)  # 입술 영역 표시 여부 (기본값: False)
        self.show_landmark_points = tk.BooleanVar(value=False)  # 랜드마크 포인트(점) 표시 여부 (기본값: False)
        self.show_landmark_lines = tk.BooleanVar(value=False)  # 랜드마크 연결선 표시 여부 (기본값: False)
        self.show_landmark_polygons = tk.BooleanVar(value=False)  # 랜드마크 폴리곤 표시 여부 (기본값: False)
        self.show_landmark_indices = tk.BooleanVar(value=False)  # 랜드마크 인덱스 번호 표시 여부 (기본값: False)
        self.polygon_expansion_level = tk.IntVar(value=1)  # 폴리곤 주변 확장 레벨 (0~5, 기본값: 1)
        self.current_morphing_tab = "눈"  # 현재 선택된 얼굴 특징 보정 탭 (전체, 눈, 눈썹, 코, 입, 턱선, 윤곽)
        self.use_individual_eye_region = tk.BooleanVar(value=False)  # 눈 영역 개별 적용 여부
        self.use_landmark_warping = tk.BooleanVar(value=False)  # 랜드마크 직접 변형 모드 사용 여부 (기본값: False)
        self.eye_region_padding = tk.DoubleVar(value=0.3)  # 눈 영역 패딩 비율 (0.0 ~ 1.0, 기본값: 0.3)
        self.left_eye_region_padding = tk.DoubleVar(value=0.3)  # 왼쪽 눈 영역 패딩 비율
        self.right_eye_region_padding = tk.DoubleVar(value=0.3)  # 오른쪽 눈 영역 패딩 비율
        self.eye_region_offset_x = tk.DoubleVar(value=0.0)  # 눈 영역 수평 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.eye_region_offset_y = tk.DoubleVar(value=0.0)  # 눈 영역 수직 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.left_eye_region_offset_x = tk.DoubleVar(value=0.0)  # 왼쪽 눈 영역 수평 오프셋
        self.left_eye_region_offset_y = tk.DoubleVar(value=0.0)  # 왼쪽 눈 영역 수직 오프셋
        self.right_eye_region_offset_x = tk.DoubleVar(value=0.0)  # 오른쪽 눈 영역 수평 오프셋
        self.right_eye_region_offset_y = tk.DoubleVar(value=0.0)  # 오른쪽 눈 영역 수직 오프셋
        
        # 입술 영역 조정 설정
        self.use_individual_lip_region = tk.BooleanVar(value=False)  # 입술 영역 개별 적용 여부
        self.upper_lip_region_padding_x = tk.DoubleVar(value=0.2)  # 윗입술 영역 가로 패딩 비율 (0.0 ~ 1.0, 기본값: 0.2)
        self.upper_lip_region_padding_y = tk.DoubleVar(value=0.3)  # 윗입술 영역 세로 패딩 비율 (0.0 ~ 1.0, 기본값: 0.3)
        self.lower_lip_region_padding_x = tk.DoubleVar(value=0.2)  # 아래입술 영역 가로 패딩 비율
        self.lower_lip_region_padding_y = tk.DoubleVar(value=0.3)  # 아래입술 영역 세로 패딩 비율
        self.upper_lip_region_offset_x = tk.DoubleVar(value=0.0)  # 윗입술 영역 수평 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.upper_lip_region_offset_y = tk.DoubleVar(value=0.0)  # 윗입술 영역 수직 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.lower_lip_region_offset_x = tk.DoubleVar(value=0.0)  # 아래입술 영역 수평 오프셋
        self.lower_lip_region_offset_y = tk.DoubleVar(value=0.0)  # 아래입술 영역 수직 오프셋
        
        # 얼굴 정렬 설정
        self.auto_align = tk.BooleanVar(value=False)  # 자동 정렬 사용 여부
        
        # 스타일 전송 설정 (Phase 2)
        self.style_image_path = None  # 스타일 소스 이미지 경로
        self.color_strength = tk.DoubleVar(value=0.0)  # 색상 전송 강도 (0.0 ~ 1.0, 기본값: 0.0)
        self.texture_strength = tk.DoubleVar(value=0.0)  # 텍스처 전송 강도 (0.0 ~ 1.0, 기본값: 0.0)
        
        # 나이 변환 설정 (Phase 2)
        self.age_adjustment = tk.DoubleVar(value=0.0)  # 나이 조정 (-50 ~ +50 세, 기본값: 0.0)
        
        # 미리보기 이미지
        self.tk_image_original = None
        self.tk_image_edited = None
        self.image_created_original = None
        self.image_created_edited = None
        
        # 눈 영역 표시용 캔버스 아이템
        self.eye_region_rects_original = []  # 원본 이미지의 눈 영역 사각형
        self.eye_region_rects_edited = []  # 편집된 이미지의 눈 영역 사각형
        
        # 입술 영역 표시용 캔버스 아이템
        self.lip_region_rects_original = []  # 원본 이미지의 입술 영역 사각형
        self.lip_region_rects_edited = []  # 편집된 이미지의 입술 영역 사각형
        
        # 랜드마크 표시용 캔버스 아이템
        self.landmarks_items_original = []  # 원본 이미지의 랜드마크 아이템
        self.landmarks_items_edited = []  # 편집된 이미지의 랜드마크 아이템
        self.landmarks_items_transformed = []  # 원본 이미지에 표시되는 변형된 랜드마크 아이템
        self.polygon_point_map_original = {}  # 포인트 인덱스 -> 캔버스 아이템 ID 매핑 (원본)
        self.polygon_point_map_edited = {}  # 포인트 인덱스 -> 캔버스 아이템 ID 매핑 (편집)
        self.landmark_polygon_items_original = []  # 원본 이미지의 폴리곤 아이템
        self.landmark_polygon_items_edited = []  # 편집된 이미지의 폴리곤 아이템
        self.selected_polygon_group = None  # 선택된 폴리곤 그룹 (눈, 코, 입 등)
        
        # 폴리곤 드래그 관련 변수
        self.dragging_polygon = False  # 폴리곤에서 포인트 드래그 중 여부
        self.dragged_polygon_index = None  # 드래그 중인 포인트 인덱스
        self.last_selected_landmark_index = None  # 마지막으로 선택/드래그한 포인트 인덱스 (드래그 종료 후에도 유지)
        self.dragged_polygon_canvas = None  # 드래그 중인 캔버스 (original/edited)
        self.polygon_drag_start_x = None  # 드래그 시작 x 좌표
        self.polygon_drag_start_y = None  # 드래그 시작 y 좌표
        self.polygon_drag_start_img_x = None  # 드래그 시작 이미지 x 좌표
        self.polygon_drag_start_img_y = None  # 드래그 시작 이미지 y 좌표
        self.custom_landmarks = None
        self.selected_landmark_indicator_original = None  # 원본 이미지의 선택된 포인트 표시 아이템
        self.selected_landmark_indicator_edited = None  # 편집된 이미지의 선택된 포인트 표시 아이템
        self.selected_landmark_lines_original = []  # 원본 이미지의 선택된 포인트 연결선 아이템
        self.selected_landmark_lines_edited = []  # 편집된 이미지의 선택된 포인트 연결선 아이템  # 사용자가 수정한 랜드마크 (드래그로 변경된 경우)
        self.original_landmarks = None  # 원본 이미지의 랜드마크 (항상 보존)
        
        # 성능 최적화: 이미지 변경 감지 및 리사이즈 캐싱
        self._last_edited_image_hash = None  # 이전 편집된 이미지 해시
        self._resize_cache = {}  # 이미지 리사이즈 캐시
        self._resize_cache_max_size = 10  # 최대 캐시 크기
        self.transformed_landmarks = None  # 변형된 랜드마크 (apply_editing에서 계산)
        
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
        
        # "원래대로" 버튼 플래그
        self.is_resetting_position = False
        self.canvas_edited_drag_start_image_x = None
        self.canvas_edited_drag_start_image_y = None
        
        # 원본 이미지 확대/축소 변수
        self.zoom_scale_original = 1.0  # 확대/축소 비율
        self.original_image_base_size = None  # 원본 이미지 기본 크기
        self.zoom_max_scale = 40.0  # 최대 확대 비율
        self.zoom_min_scale = 0.1  # 최소 축소 비율
        
        # 캔버스 크기 설정
        self.preview_width = 800  # 캔버스 너비 (기존: 480)
        self.preview_height = 1000  # 캔버스 높이 (기존: 600)
        
        # 확대/축소 최적화 변수
        self._zoom_update_pending = False  # 확대/축소 업데이트 대기 중 플래그
        self._is_zooming = False  # 확대/축소 중 플래그 (랜드마크 업데이트 지연용)
        
        # 캔버스 리사이즈 제어 플래그 (무한 루프 방지)
        self._resizing_canvas = False
        
        # 마우스 위치 저장 (확대/축소 중심점용)
        self._last_mouse_x_original = None
        self._last_mouse_y_original = None
        self._last_mouse_x_edited = None
        self._last_mouse_y_edited = None
        
        # 얼굴 편집 폴더 경로 (config에서 로드)
        import globals as gl
        self.face_edit_dir = gl._face_extract_dir if gl._face_extract_dir else None
        
        # 팝업창 참조 변수 초기화
        self.file_list_popup = None
        self.settings_popup = None
        
        self.create_widgets()
        
        # 창 초기 크기 설정 (캔버스 초기 크기 * 2 + 여백)
        initial_window_width = (self.canvas_initial_width * 2) + 50  # 두 캔버스 + 여백
        initial_window_height = self.canvas_initial_height + 100  # 캔버스 + 버튼 + 여백
        self.geometry(f"{initial_window_width}x{initial_window_height}")
        
        # 창을 화면 중앙에 배치
        self.update_idletasks()  # 창 크기 계산을 위해 업데이트
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    
    def show_file_list_popup(self):
        """파일 리스트 팝업창 표시"""
        if self.file_list_popup is not None and self.file_list_popup.winfo_exists():
            # 이미 열려있으면 포커스만 이동
            self.file_list_popup.lift()
            self.file_list_popup.focus()
            return
        
        # 새 팝업창 생성
        popup = tk.Toplevel(self)
        popup.title("파일 선택")
        popup.transient(self)
        popup.resizable(True, True)
        popup.minsize(400, 300)
        
        # 파일 선택 UI를 팝업창에 배치
        file_frame = self._create_file_selection_ui(popup)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 팝업창이 열릴 때 파일 목록 로드
        popup.after(100, self.refresh_file_list)
        
        # 팝업창 닫기 이벤트
        def on_popup_close():
            self.file_list_popup = None
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.file_list_popup = popup
    
    def show_settings_popup(self):
        """편집 설정 팝업창 표시"""
        if self.settings_popup is not None and self.settings_popup.winfo_exists():
            # 이미 열려있으면 포커스만 이동
            self.settings_popup.lift()
            self.settings_popup.focus()
            return
        
        # 새 팝업창 생성
        popup = tk.Toplevel(self)
        popup.title("얼굴 편집 설정")
        popup.transient(self)
        popup.resizable(True, True)
        popup.minsize(400, 500)
        
        # 설정 프레임
        settings_frame = tk.LabelFrame(popup, text="얼굴 편집 설정", padx=5, pady=5)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 얼굴 정렬 UI (탭 외부에 유지)
        self._create_face_alignment_ui(settings_frame)
        
        # 탭 노트북 생성 (얼굴 특징 보정, 스타일 전송, 나이 변환)
        from tkinter import ttk
        main_notebook = ttk.Notebook(settings_frame)
        main_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 얼굴 특징 보정 탭
        morphing_tab = self._create_face_morphing_ui(main_notebook)
        main_notebook.add(morphing_tab, text="얼굴 특징 보정")
        
        # 스타일 전송 탭
        style_tab = self._create_style_transfer_ui(main_notebook)
        main_notebook.add(style_tab, text="스타일 전송")
        
        # 나이 변환 탭
        age_tab = self._create_age_transform_ui(main_notebook)
        main_notebook.add(age_tab, text="나이 변환")
        
        # 팝업창 닫기 이벤트
        def on_popup_close():
            self.settings_popup = None
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.settings_popup = popup
    
    def on_close(self):
        """창 닫기"""
        # 팝업창도 함께 닫기
        if self.file_list_popup is not None and self.file_list_popup.winfo_exists():
            self.file_list_popup.destroy()
        if self.settings_popup is not None and self.settings_popup.winfo_exists():
            self.settings_popup.destroy()
        self.destroy()


def show_face_edit_panel(parent=None):
    """얼굴 편집 패널 표시"""
    panel = FaceEditPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel


class FaceEditPanelV2(FaceEditPanel):
    """얼굴 편집 V2 패널

    기존 FaceEditPanel을 상속하여 공통 동작은 그대로 두고,
    향후 눈/입 편집 UI 및 랜드마크 기반 제어를 단계적으로 개선하기 위한 실험용 패널.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # V2 패널임을 명확히 구분하기 위해 제목만 우선 변경
        self.title("얼굴 편집 V2")
        # V2: 랜드마크 기반 모핑을 기본값으로 활성화 (계획서대로)
        self.use_landmark_warping.set(True)
    
    def _create_eye_tab(self, notebook):
        """눈 탭 UI 생성 (V2: 영역 설정 슬라이더 제거)"""
        from tkinter import ttk
        import tkinter as tk
        
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수 (눈 크기 전용 - 동기화 처리를 위해)
        def create_eye_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 1.0  # 눈 크기 기본값
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_size.set(default_value)
                    else:
                        self.left_eye_size.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            def on_eye_slider_change(value):
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_size.set(float(value))
                    else:
                        self.left_eye_size.set(float(value))
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수평 전용)
        def create_eye_position_x_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                if self.eye_spacing.get():
                    if is_left:
                        self.right_eye_position_x.set(-default_value)
                    else:
                        self.left_eye_position_x.set(-default_value)
                elif not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_x.set(default_value)
                    else:
                        self.left_eye_position_x.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            def on_eye_position_x_slider_change(value):
                if self.eye_spacing.get():
                    if is_left:
                        self.right_eye_position_x.set(-float(value))
                    else:
                        self.left_eye_position_x.set(-float(value))
                elif not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_x.set(float(value))
                    else:
                        self.left_eye_position_x.set(float(value))
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_x_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수직 전용)
        def create_eye_position_y_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_y.set(default_value)
                    else:
                        self.left_eye_position_y.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            def on_eye_position_y_slider_change(value):
                if not self.use_individual_eye_region.get():
                    if is_left:
                        self.right_eye_position_y.set(float(value))
                    else:
                        self.left_eye_position_y.set(float(value))
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_y_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # V2: 영역 설정 프레임 제거, 눈 모양/이동 조정만 표시
        eye_shape_frame = tk.LabelFrame(tab_frame, text="눈 모양 / 이동", padx=5, pady=5)
        eye_shape_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 0))
        
        # 왼쪽/오른쪽 눈 크기 슬라이더
        self.left_eye_size_label = create_eye_slider(eye_shape_frame, "왼쪽 눈 크기:", self.left_eye_size, 0.5, 2.0, 0.01, "100%", is_left=True)
        self.right_eye_size_label = create_eye_slider(eye_shape_frame, "오른쪽 눈 크기:", self.right_eye_size, 0.5, 2.0, 0.01, "100%", is_left=False)
        
        # 눈 위치 조정 (왼쪽/오른쪽 개별)
        self.left_eye_position_y_label = create_eye_position_y_slider(eye_shape_frame, "왼쪽 눈 수직:", self.left_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_y_label = create_eye_position_y_slider(eye_shape_frame, "오른쪽 눈 수직:", self.right_eye_position_y, -10.0, 10.0, 1.0, "0", is_left=False)
        
        self.left_eye_position_x_label = create_eye_position_x_slider(eye_shape_frame, "왼쪽 눈 수평:", self.left_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=True)
        self.right_eye_position_x_label = create_eye_position_x_slider(eye_shape_frame, "오른쪽 눈 수평:", self.right_eye_position_x, -10.0, 10.0, 1.0, "0", is_left=False)
        
        return tab_frame
    
    def _create_mouth_tab(self, notebook):
        """입 탭 UI 생성 (V2: 영역 설정 슬라이더 제거)"""
        import tkinter as tk
        
        tab_frame = tk.Frame(notebook, padx=5, pady=5)
        
        scaled_length = 200
        label_width = 16
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=1.0):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            def reset_slider(event):
                variable.set(default_value)
                self.on_morphing_change()
            
            title_label.bind("<Button-1>", reset_slider)
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_morphing_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # V2: 영역 설정 프레임 제거, 입술 모양/이동 조정만 표시
        lip_shape_frame = tk.LabelFrame(tab_frame, text="입술 모양 / 이동", padx=5, pady=5)
        lip_shape_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 0))
        
        # 입술 모양 조정 슬라이더
        self.upper_lip_shape_label = create_slider(lip_shape_frame, "윗입술 모양:", self.upper_lip_shape, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        self.lower_lip_shape_label = create_slider(lip_shape_frame, "아랫입술 모양:", self.lower_lip_shape, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        self.upper_lip_width_label = create_slider(lip_shape_frame, "윗입술 너비:", self.upper_lip_width, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        self.lower_lip_width_label = create_slider(lip_shape_frame, "아랫입술 너비:", self.lower_lip_width, 0.2, 4.0, 0.01, "100%", default_value=1.0)
        self.upper_lip_vertical_move_label = create_slider(lip_shape_frame, "윗입술 수직 이동:", self.upper_lip_vertical_move, -50.0, 50.0, 1.0, "0", default_value=0.0)
        self.lower_lip_vertical_move_label = create_slider(lip_shape_frame, "아랫입술 수직 이동:", self.lower_lip_vertical_move, -50.0, 50.0, 1.0, "0", default_value=0.0)
        
        return tab_frame
    
    def apply_editing(self):
        """편집 적용 (V2: 영역 파라미터를 기본값으로 고정)"""
        if self.current_image is None:
            return
        
        try:
            import utils.face_morphing as face_morphing
            import utils.style_transfer as style_transfer
            import utils.face_transform as face_transform
            import os
            from PIL import Image
            
            # 처리 순서: 정렬 → 특징 보정 → 스타일 전송 → 나이 변환
            base_image = self.aligned_image if self.aligned_image is not None else self.current_image
            
            # 눈 편집 파라미터 결정
            if self.use_individual_eye_region.get():
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.right_eye_size.get()
            else:
                left_eye_size = self.left_eye_size.get()
                right_eye_size = self.left_eye_size.get()
            
            # V2: 눈 크기 값 유효성 검사 및 기본값 보정
            if left_eye_size is None or not (0.1 <= left_eye_size <= 5.0):
                print(f"[얼굴편집V2] 경고: 왼쪽 눈 크기 값이 유효하지 않음: {left_eye_size}, 기본값 1.0으로 설정")
                left_eye_size = 1.0
            if right_eye_size is None or not (0.1 <= right_eye_size <= 5.0):
                print(f"[얼굴편집V2] 경고: 오른쪽 눈 크기 값이 유효하지 않음: {right_eye_size}, 기본값 1.0으로 설정")
                right_eye_size = 1.0
            
            # 변형된 랜드마크 계산 (랜드마크 표시용)
            import utils.face_landmarks as face_landmarks
            
            # 원본 랜드마크 가져오기 (항상 원본을 기준으로 변형)
            base_landmarks = None
            if hasattr(self, 'original_landmarks') and self.original_landmarks is not None:
                base_landmarks = self.original_landmarks
            else:
                # original_landmarks가 없으면 face_landmarks 사용 (없으면 감지)
                if self.face_landmarks is None:
                    self.face_landmarks, _ = face_landmarks.detect_face_landmarks(base_image)
                    # 원본 랜드마크 저장
                    if self.face_landmarks is not None:
                        self.original_landmarks = list(self.face_landmarks)
                base_landmarks = self.face_landmarks
            
            if self.use_landmark_warping.get():
                # 랜드마크 기반 변형 모드: 변형된 랜드마크 계산
                if base_landmarks is not None:
                    # 변형된 랜드마크 계산 (항상 원본을 기준으로)
                    transformed = face_morphing.transform_points_for_eye_size(
                        base_landmarks,
                        eye_size_ratio=1.0,
                        left_eye_size_ratio=left_eye_size,
                        right_eye_size_ratio=right_eye_size
                    )
                    
                    # 눈 위치 변형
                    transformed = face_morphing.transform_points_for_eye_position(
                        transformed,
                        left_eye_position_x=self.left_eye_position_x.get(),
                        right_eye_position_x=self.right_eye_position_x.get(),
                        left_eye_position_y=self.left_eye_position_y.get(),
                        right_eye_position_y=self.right_eye_position_y.get()
                    )
                    
                    # 코 크기 변형
                    transformed = face_morphing.transform_points_for_nose_size(
                        transformed,
                        nose_size_ratio=self.nose_size.get()
                    )
                    
                    # 입술 변형
                    transformed = face_morphing.transform_points_for_lip_shape(
                        transformed,
                        upper_lip_shape=self.upper_lip_shape.get(),
                        lower_lip_shape=self.lower_lip_shape.get()
                    )
                    transformed = face_morphing.transform_points_for_lip_width(
                        transformed,
                        upper_lip_width=self.upper_lip_width.get(),
                        lower_lip_width=self.lower_lip_width.get()
                    )
                    
                    self.transformed_landmarks = transformed
                    # custom_landmarks도 업데이트 (폴리곤 표시용)
                    self.custom_landmarks = transformed
                else:
                    self.transformed_landmarks = None
                    self.custom_landmarks = None
            else:
                self.transformed_landmarks = None
                # use_landmark_warping이 꺼져 있어도 슬라이더 값에 따라 랜드마크 변형
                if base_landmarks is not None:
                    # 변형된 랜드마크 계산 (항상 원본을 기준으로)
                    transformed = face_morphing.transform_points_for_eye_size(
                        base_landmarks,
                        eye_size_ratio=1.0,
                        left_eye_size_ratio=left_eye_size,
                        right_eye_size_ratio=right_eye_size
                    )
                    
                    # 눈 위치 변형
                    transformed = face_morphing.transform_points_for_eye_position(
                        transformed,
                        left_eye_position_x=self.left_eye_position_x.get(),
                        right_eye_position_x=self.right_eye_position_x.get(),
                        left_eye_position_y=self.left_eye_position_y.get(),
                        right_eye_position_y=self.right_eye_position_y.get()
                    )
                    
                    # 코 크기 변형
                    transformed = face_morphing.transform_points_for_nose_size(
                        transformed,
                        nose_size_ratio=self.nose_size.get()
                    )
                    
                    # 입술 변형
                    transformed = face_morphing.transform_points_for_lip_shape(
                        transformed,
                        upper_lip_shape=self.upper_lip_shape.get(),
                        lower_lip_shape=self.lower_lip_shape.get()
                    )
                    transformed = face_morphing.transform_points_for_lip_width(
                        transformed,
                        upper_lip_width=self.upper_lip_width.get(),
                        lower_lip_width=self.lower_lip_width.get()
                    )
                    
                    # custom_landmarks 업데이트 (폴리곤 표시용)
                    self.custom_landmarks = transformed
                else:
                    self.custom_landmarks = None
            
            # V2: 영역 파라미터는 모두 None으로 전달하여 기본값(자동 계산) 사용
            # 입 편집 파라미터 전달
            result = face_morphing.apply_all_adjustments(
                base_image,
                eye_size=None,
                left_eye_size=left_eye_size,
                right_eye_size=right_eye_size,
                eye_spacing=self.eye_spacing.get(),
                left_eye_position_y=self.left_eye_position_y.get(),
                right_eye_position_y=self.right_eye_position_y.get(),
                left_eye_position_x=self.left_eye_position_x.get(),
                right_eye_position_x=self.right_eye_position_x.get(),
                # V2: 영역 파라미터를 None으로 전달하여 기본값 사용
                eye_region_padding=None,
                eye_region_offset_x=None,
                eye_region_offset_y=None,
                left_eye_region_padding=None,
                right_eye_region_padding=None,
                left_eye_region_offset_x=None,
                left_eye_region_offset_y=None,
                right_eye_region_offset_x=None,
                right_eye_region_offset_y=None,
                nose_size=self.nose_size.get(),
                upper_lip_shape=self.upper_lip_shape.get(),
                lower_lip_shape=self.lower_lip_shape.get(),
                upper_lip_width=self.upper_lip_width.get(),
                lower_lip_width=self.lower_lip_width.get(),
                upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
                lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
                use_individual_lip_region=self.use_individual_lip_region.get(),
                # V2: 입술 영역 파라미터도 None으로 전달하여 기본값 사용
                upper_lip_region_padding_x=None,
                upper_lip_region_padding_y=None,
                lower_lip_region_padding_x=None,
                lower_lip_region_padding_y=None,
                upper_lip_region_offset_x=None,
                upper_lip_region_offset_y=None,
                lower_lip_region_offset_x=None,
                lower_lip_region_offset_y=None,
                use_landmark_warping=self.use_landmark_warping.get(),
                jaw_adjustment=self.jaw_size.get(),
                face_width=self.face_width.get(),
                face_height=self.face_height.get()
            )
            
            # 스타일 전송 적용
            if self.style_image_path and os.path.exists(self.style_image_path):
                try:
                    style_image = Image.open(self.style_image_path)
                    color_strength = self.color_strength.get()
                    texture_strength = self.texture_strength.get()
                    
                    if color_strength > 0.0 or texture_strength > 0.0:
                        result = style_transfer.transfer_style(
                            style_image,
                            result,
                            color_strength=color_strength,
                            texture_strength=texture_strength
                        )
                except Exception as e:
                    print(f"[얼굴편집V2] 스타일 전송 실패: {e}")
            
            # 나이 변환 적용
            age_adjustment = self.age_adjustment.get()
            if abs(age_adjustment) >= 1.0:
                result = face_transform.transform_age(result, age_adjustment=int(age_adjustment))
            
            self.edited_image = result
            
            # 미리보기 업데이트
            self.show_edited_preview()
            
            # 랜드마크 표시 업데이트 (변형된 랜드마크도 함께 표시)
            if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                self.update_face_features_display()
            
            # 영역 표시 업데이트
            if self.show_eye_region.get():
                self.update_eye_region_display()
            if self.show_lip_region.get():
                self.update_lip_region_display()
            
        except Exception as e:
            print(f"[얼굴편집V2] 편집 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            self.edited_image = self.current_image.copy()
            self.show_edited_preview()
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출 (V2: 영역 관련 라벨 업데이트 제거)"""
        # 왼쪽/오른쪽 눈 라벨 업데이트
        if hasattr(self, 'left_eye_size_label'):
            left_eye_value = self.left_eye_size.get()
            self.left_eye_size_label.config(text=f"{int(left_eye_value * 100)}%")
        
        if hasattr(self, 'right_eye_size_label'):
            right_eye_value = self.right_eye_size.get()
            self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
        
        if hasattr(self, 'nose_size_label'):
            nose_value = self.nose_size.get()
            self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        # 입 편집 라벨 업데이트
        if hasattr(self, 'upper_lip_shape_label'):
            upper_lip_shape_value = self.upper_lip_shape.get()
            self.upper_lip_shape_label.config(text=f"{int(upper_lip_shape_value * 100)}%")
        
        if hasattr(self, 'lower_lip_shape_label'):
            lower_lip_shape_value = self.lower_lip_shape.get()
            self.lower_lip_shape_label.config(text=f"{int(lower_lip_shape_value * 100)}%")
        
        if hasattr(self, 'upper_lip_width_label'):
            upper_lip_width_value = self.upper_lip_width.get()
            self.upper_lip_width_label.config(text=f"{int(upper_lip_width_value * 100)}%")
        
        if hasattr(self, 'lower_lip_width_label'):
            lower_lip_width_value = self.lower_lip_width.get()
            self.lower_lip_width_label.config(text=f"{int(lower_lip_width_value * 100)}%")
        
        if hasattr(self, 'upper_lip_vertical_move_label'):
            upper_lip_vertical_move_value = self.upper_lip_vertical_move.get()
            self.upper_lip_vertical_move_label.config(text=f"{int(upper_lip_vertical_move_value)}")
        
        if hasattr(self, 'lower_lip_vertical_move_label'):
            lower_lip_vertical_move_value = self.lower_lip_vertical_move.get()
            self.lower_lip_vertical_move_label.config(text=f"{int(lower_lip_vertical_move_value)}")
        
        # V2: 영역 관련 라벨 업데이트 제거 (라벨이 없으므로)
        
        if hasattr(self, 'jaw_size_label'):
            jaw_value = self.jaw_size.get()
            self.jaw_size_label.config(text=f"{int(jaw_value)}")
        
        if hasattr(self, 'face_width_label'):
            face_width_value = self.face_width.get()
            self.face_width_label.config(text=f"{int(face_width_value * 100)}%")
        
        if hasattr(self, 'face_height_label'):
            face_height_value = self.face_height.get()
            self.face_height_label.config(text=f"{int(face_height_value * 100)}%")
        
        # 눈 위치 라벨 업데이트
        if hasattr(self, 'left_eye_position_y_label'):
            left_eye_position_y_value = self.left_eye_position_y.get()
            self.left_eye_position_y_label.config(text=f"{int(left_eye_position_y_value)}")
        
        if hasattr(self, 'right_eye_position_y_label'):
            right_eye_position_y_value = self.right_eye_position_y.get()
            self.right_eye_position_y_label.config(text=f"{int(right_eye_position_y_value)}")
        
        if hasattr(self, 'left_eye_position_x_label'):
            left_eye_position_x_value = self.left_eye_position_x.get()
            self.left_eye_position_x_label.config(text=f"{int(left_eye_position_x_value)}")
        
        if hasattr(self, 'right_eye_position_x_label'):
            right_eye_position_x_value = self.right_eye_position_x.get()
            self.right_eye_position_x_label.config(text=f"{int(right_eye_position_x_value)}")
        
        # V2: 눈 영역 라벨 업데이트 제거 (라벨이 없으므로)
        
        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        if self.current_image is not None:
            use_warping = getattr(self, 'use_landmark_warping', None)
            if use_warping is not None and hasattr(use_warping, 'get') and use_warping.get():
                # 고급 모드일 때도 슬라이더 값에 따라 custom_landmarks 업데이트
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()
                
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    if hasattr(self, 'apply_polygon_drag_final'):
                        self.apply_polygon_drag_final()
                        if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                            self.update_face_features_display()
                        return
        
        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()
            
            # 편집 적용 전에 현재 위치를 명시적으로 저장
            if self.image_created_original is not None:
                try:
                    original_coords = self.canvas_original.coords(self.image_created_original)
                    if original_coords and len(original_coords) >= 2:
                        self.canvas_original_pos_x = original_coords[0]
                        self.canvas_original_pos_y = original_coords[1]
                except Exception as e:
                    print(f"[얼굴편집V2] 원본 위치 저장 실패: {e}")
            
            # 편집된 이미지 위치도 저장
            if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                self.canvas_edited_pos_x = self.canvas_original_pos_x
                self.canvas_edited_pos_y = self.canvas_original_pos_y
            elif self.image_created_edited is not None:
                try:
                    edited_coords = self.canvas_edited.coords(self.image_created_edited)
                    if edited_coords and len(edited_coords) >= 2:
                        self.canvas_edited_pos_x = edited_coords[0]
                        self.canvas_edited_pos_y = edited_coords[1]
                except Exception as e:
                    print(f"[얼굴편집V2] 편집 위치 저장 실패: {e}")
            
            self.apply_editing()
            # 눈 영역 표시 업데이트
            if self.show_eye_region.get():
                self.update_eye_region_display()
            # 입술 영역 표시 업데이트
            if self.show_lip_region.get():
                self.update_lip_region_display()
            
            # 폴리곤 표시 업데이트 (custom_landmarks가 이미 update_polygons_only에서 업데이트되었으므로)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # custom_landmarks가 있으면 폴리곤만 다시 그리기
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items_original):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items_original.clear()
                    if hasattr(self, 'polygon_point_map_original'):
                        self.polygon_point_map_original.clear()
                    
                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        self._draw_landmark_polygons(
                            self.canvas_original,
                            self.current_image,
                            self.custom_landmarks,
                            self.canvas_original_pos_x,
                            self.canvas_original_pos_y,
                            self.landmark_polygon_items_original,
                            "green",
                                        current_tab
                                    )
                    # custom_landmarks가 없으면 전체 업데이트
                    self.update_face_features_display()


def show_face_edit_panel_v2(parent=None):
    """얼굴 편집 V2 패널 표시 (실험용 신규 패널)"""
    panel = FaceEditPanelV2(parent)
    panel.transient(parent)
    return panel
