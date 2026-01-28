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
from .popup_manager import PopupManagerMixin
from .guide_line_scaling import GuideLineScalingMixin
from .editing_pipeline import EditingPipelineMixin
from .landmark_manager import LandmarkManager


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
    WidgetCreatorMixin,
    PopupManagerMixin,
    GuideLineScalingMixin,
    EditingPipelineMixin,
):
    """얼굴 편집 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 편집")
        self.resizable(True, True)  # 리사이즈 허용
        
        # PolygonRendererMixin 초기화 (DrawingMixin 포함)
        PolygonRendererMixin.__init__(self)
        
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
        
        # 랜드마크 상태 관리자 (중앙화) - property setter가 사용하므로 먼저 초기화 필요
        self.landmark_manager = LandmarkManager()
        
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
        self.blend_ratio = tk.DoubleVar(value=1.0)  # 블렌딩 비율 (0.0 ~ 1.0, 기본값: 1.0)
        
        # 눈 편집 고급 설정
        self.left_eye_size = tk.DoubleVar(value=1.0)  # 왼쪽 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.right_eye_size = tk.DoubleVar(value=1.0)  # 오른쪽 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.eye_spacing = tk.BooleanVar(value=False)  # 눈 간격 조정 활성화 여부
        self.iris_clamping_enabled = tk.BooleanVar(value=True)  # 눈동자 이동 범위 제한 활성화 여부
        self.iris_clamping_margin_ratio = tk.DoubleVar(value=0.3)  # 눈동자 이동 범위 제한 마진 비율 (0.0 ~ 1.0, 기본값: 0.3)
        self.left_eye_position_y = tk.DoubleVar(value=0.0)  # 왼쪽 눈 수직 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.right_eye_position_y = tk.DoubleVar(value=0.0)  # 오른쪽 눈 수직 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.left_eye_position_x = tk.DoubleVar(value=0.0)  # 왼쪽 눈 수평 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.right_eye_position_x = tk.DoubleVar(value=0.0)  # 오른쪽 눈 수평 위치 조정 (-10 ~ +10 픽셀, 기본값: 0)
        self.use_guide_line_scaling = tk.BooleanVar(value=True)  # 지시선 기반 스케일링 사용 여부
        self.show_eye_region = tk.BooleanVar(value=False)  # 눈 영역 표시 여부 (기본값: True)
        self.show_lip_region = tk.BooleanVar(value=False)  # 입술 영역 표시 여부 (기본값: False)
        self.show_guide_lines = tk.BooleanVar(value=False)  # 지시선 표시 여부 (기본값: False)
        self.show_landmark_points = tk.BooleanVar(value=False)  # 랜드마크 포인트(점) 표시 여부 (기본값: False)
        self.show_landmark_lines = tk.BooleanVar(value=False)  # 랜드마크 연결선 표시 여부 (기본값: False)
        self.show_landmark_polygons = tk.BooleanVar(value=False)  # 랜드마크 폴리곤 표시 여부 (기본값: False)
        self.show_landmark_indices = tk.BooleanVar(value=False)  # 랜드마크 인덱스 번호 표시 여부 (기본값: False)
        self.show_region_centers = tk.BooleanVar(value=False)  # 부위 중심점 표시 여부 (기본값: False)
        
        # MediaPipe 부위 선택 변수 (전체 탭용)
        self.show_face_oval = tk.BooleanVar(value=False)  # Face Oval 표시 여부
        self.show_left_eye = tk.BooleanVar(value=False)  # Left Eye 표시 여부
        self.show_right_eye = tk.BooleanVar(value=False)  # Right Eye 표시 여부
        self.show_left_eyebrow = tk.BooleanVar(value=False)  # Left Eyebrow 표시 여부
        self.show_right_eyebrow = tk.BooleanVar(value=False)  # Right Eyebrow 표시 여부
        self.show_nose = tk.BooleanVar(value=False)  # Nose 표시 여부
        self.show_lips = tk.BooleanVar(value=False)  # Lips 표시 여부 (하위 호환성 유지)
        self.show_upper_lips = tk.BooleanVar(value=False)  # Upper Lips 표시 여부
        self.show_lower_lips = tk.BooleanVar(value=False)  # Lower Lips 표시 여부
        self.show_left_iris = tk.BooleanVar(value=False)  # Left Iris 표시 여부 (refine_landmarks=True일 때만 사용 가능)
        self.show_right_iris = tk.BooleanVar(value=False)  # Right Iris 표시 여부 (refine_landmarks=True일 때만 사용 가능)
        self.show_iris_connections = tk.BooleanVar(value=True)  # 눈동자 중심점 연결 폴리곤 표시 여부 (기본값: True)
        self.show_iris_eyelid_connections = tk.BooleanVar(value=True)  # 눈동자-눈꺼풀 연결선 표시 여부 (기본값: True)
        self.iris_mapping_method = tk.StringVar(value="iris_outline")  # 눈동자 맵핑 방법 (iris_outline/eye_landmarks)
        self.show_contours = tk.BooleanVar(value=False)  # Contours 표시 여부
        self.show_tesselation = tk.BooleanVar(value=False)  # Tesselation 표시 여부
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
        
        # 공통 슬라이더 변수 (선택된 모든 부위에 공통 적용)
        self.region_center_offset_x = tk.DoubleVar(value=0.0)  # 중심점 오프셋 X (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_center_offset_y = tk.DoubleVar(value=0.0)  # 중심점 오프셋 Y (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_size = tk.DoubleVar(value=1.0)  # 크기 비율 (0.5 ~ 2.0, 기본값: 1.0) - 하위 호환성 유지
        self.region_size_x = tk.DoubleVar(value=1.0)  # 크기 비율 X (0.5 ~ 2.0, 기본값: 1.0)
        self.region_size_y = tk.DoubleVar(value=1.0)  # 크기 비율 Y (0.5 ~ 2.0, 기본값: 1.0)
        self.region_position_x = tk.DoubleVar(value=0.0)  # 위치 이동 X (-50 ~ +50 픽셀, 기본값: 0.0)
        self.region_position_y = tk.DoubleVar(value=0.0)  # 위치 이동 Y (-50 ~ +50 픽셀, 기본값: 0.0)
        
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
        
        # 눈동자 중앙 포인트 좌표 저장 (인덱스 대신 좌표만 저장)
        # 중앙 포인트 좌표는 landmark_manager에서 관리
        # 하위 호환성을 위해 속성 유지 (점진적 마이그레이션)
        self._left_iris_center_coord = None  # @deprecated: landmark_manager.get_left_iris_center_coord() 사용
        self._right_iris_center_coord = None  # @deprecated: landmark_manager.get_right_iris_center_coord() 사용
        
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
        
        # 바운딩 박스 표시용 캔버스 아이템
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
            'edited': []     # 편집 캔버스의 폴리곤 아이템
        }
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
        # 랜드마크는 property로 관리 (아래에 정의)
        self.selected_landmark_indicator_original = None  # 원본 이미지의 선택된 포인트 표시 아이템
        self.selected_landmark_indicator_edited = None  # 편집된 이미지의 선택된 포인트 표시 아이템
        self.selected_landmark_lines_original = []  # 원본 이미지의 선택된 포인트 연결선 아이템
        self.selected_landmark_lines_edited = []  # 편집된 이미지의 선택된 포인트 연결선 아이템
        
        # 성능 최적화: 이미지 변경 감지 및 리사이즈 캐싱
        self._last_edited_image_hash = None  # 이전 편집된 이미지 해시
        self._resize_cache = {}  # 이미지 리사이즈 캐시
        self._resize_cache_max_size = 10  # 최대 캐시 크기
        
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
        self._skip_morphing_change = False  # 확대/축소 시 on_morphing_change 건너뛰기 플래그
        
        # 확대/축소 플래그 자동 해제 타이머
        self._zoom_timer = None
        
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
        self._apply_guide_scaling_state(self.use_guide_line_scaling.get())
        self._last_guide_scaling_state = None

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
    
    
    # ========== 랜드마크 Property (직접 참조, 복사본 없음) ==========
    
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
    
    @original_landmarks.setter
    def original_landmarks(self, value):
        """원본 랜드마크 설정 (LandmarkManager를 통해서만)"""
        self.landmark_manager.set_original_landmarks(value)
    
    @property
    def face_landmarks(self):
        """현재 편집된 랜드마크 (LandmarkManager의 _face_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._face_landmarks  # 직접 참조 (복사본 없음)
    
    @face_landmarks.setter
    def face_landmarks(self, value):
        """현재 편집된 랜드마크 설정 (LandmarkManager를 통해서만)
        
        직접 참조로 저장 (복사본 없음)
        """
        # value가 이미 LandmarkManager의 _face_landmarks인 경우 저장 불필요
        if value is self.landmark_manager._face_landmarks:
            return
        # 직접 참조로 저장 (복사본 없음)
        self.landmark_manager.set_face_landmarks(value)
    
    @property
    def transformed_landmarks(self):
        """변형된 랜드마크 (LandmarkManager의 _transformed_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._transformed_landmarks  # 직접 참조 (복사본 없음)
    
    @transformed_landmarks.setter
    def transformed_landmarks(self, value):
        """변형된 랜드마크 설정 (LandmarkManager를 통해서만)
        
        직접 참조로 저장 (복사본 없음)
        """
        # value가 이미 LandmarkManager의 _transformed_landmarks인 경우 저장 불필요
        if value is self.landmark_manager._transformed_landmarks:
            return
        # 직접 참조로 저장 (복사본 없음)
        self.landmark_manager.set_transformed_landmarks(value)


def show_face_edit_panel(parent=None):
    """얼굴 편집 패널 표시 (기존 V1 패널)"""
    panel = FaceEditPanel(parent)
    panel.transient(parent)
    return panel
