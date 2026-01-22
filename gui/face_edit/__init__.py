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
        self.show_eye_region = tk.BooleanVar(value=False)  # 눈 영역 표시 여부 (기본값: True)
        self.show_lip_region = tk.BooleanVar(value=False)  # 입술 영역 표시 여부 (기본값: False)
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
    
    
    # ========== 랜드마크 Property (직접 참조, 복사본 없음) ==========
    
    @property
    def custom_landmarks(self):
        """사용자 수정 랜드마크 (LandmarkManager의 _custom_landmarks 직접 참조, 복사본 없음)"""
        return self.landmark_manager._custom_landmarks  # 직접 참조
    
    @custom_landmarks.setter
    def custom_landmarks(self, value):
        """사용자 수정 랜드마크 설정 (LandmarkManager를 통해서만)
        
        직접 참조로 저장 (복사본 없음)
        """
        # value가 이미 LandmarkManager의 _custom_landmarks인 경우 저장 불필요
        if value is self.landmark_manager._custom_landmarks:
            return
        # 직접 참조로 저장 (복사본 없음)
        self.landmark_manager.set_custom_landmarks(value, reason="legacy_setter")
    
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
    
    # ========== 기타 메서드 ==========
    
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
        # 동기화 중 플래그 (무한 루프 방지)
        _syncing_eye_size = False
        
        def create_eye_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 1.0  # 눈 크기 기본값
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            
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
                nonlocal _syncing_eye_size
                
                # 동기화 중이면 라벨만 업데이트하고 리턴 (무한 루프 방지)
                if _syncing_eye_size:
                    value_label.config(text=f"{int(float(value) * 100)}%")
                    return
                
                # 드래그 중에는 라벨만 직접 업데이트 (성능 최적화)
                value_label.config(text=f"{int(float(value) * 100)}%")
                
                # 개별 조정 모드가 아니면 동기화
                if not self.use_individual_eye_region.get():
                    _syncing_eye_size = True
                    try:
                        if is_left:
                            # 오른쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'right_eye_size_label') and self.right_eye_size_label is not None:
                                self.right_eye_size_label.config(text=f"{int(float(value) * 100)}%")
                            self.right_eye_size.set(float(value))
                        else:
                            # 왼쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'left_eye_size_label') and self.left_eye_size_label is not None:
                                self.left_eye_size_label.config(text=f"{int(float(value) * 100)}%")
                            self.left_eye_size.set(float(value))
                    finally:
                        _syncing_eye_size = False
            
            def on_eye_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_slider_change,  # 드래그 중에는 라벨만 업데이트
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_slider_release)  # 드래그 종료 시 적용
            
            # value_label을 슬라이더 오른쪽에 배치
            value_label.pack(side=tk.LEFT)
            
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수평 전용)
        # 동기화 중 플래그 (무한 루프 방지)
        _syncing_eye_position_x = False
        
        def create_eye_position_x_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            # value_label은 나중에 슬라이더 오른쪽에 배치됨
            
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
                nonlocal _syncing_eye_position_x
                
                # 동기화 중이면 라벨만 업데이트하고 리턴 (무한 루프 방지)
                if _syncing_eye_position_x:
                    value_label.config(text=f"{int(float(value))}")
                    return
                
                # 드래그 중에는 라벨만 직접 업데이트 (성능 최적화)
                value_label.config(text=f"{int(float(value))}")
                
                # 동기화 처리
                _syncing_eye_position_x = True
                try:
                    if self.eye_spacing.get():
                        if is_left:
                            # 오른쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'right_eye_position_x_label') and self.right_eye_position_x_label is not None:
                                self.right_eye_position_x_label.config(text=f"{int(-float(value))}")
                            self.right_eye_position_x.set(-float(value))
                        else:
                            # 왼쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'left_eye_position_x_label') and self.left_eye_position_x_label is not None:
                                self.left_eye_position_x_label.config(text=f"{int(-float(value))}")
                            self.left_eye_position_x.set(-float(value))
                    elif not self.use_individual_eye_region.get():
                        if is_left:
                            # 오른쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'right_eye_position_x_label') and self.right_eye_position_x_label is not None:
                                self.right_eye_position_x_label.config(text=f"{int(float(value))}")
                            self.right_eye_position_x.set(float(value))
                        else:
                            # 왼쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'left_eye_position_x_label') and self.left_eye_position_x_label is not None:
                                self.left_eye_position_x_label.config(text=f"{int(float(value))}")
                            self.left_eye_position_x.set(float(value))
                finally:
                    _syncing_eye_position_x = False
            
            def on_eye_position_x_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_x_slider_change,  # 드래그 중에는 라벨만 업데이트
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_position_x_slider_release)  # 드래그 종료 시 적용
            
            # value_label을 슬라이더 오른쪽에 배치
            value_label.pack(side=tk.LEFT)
            
            return value_label
        
        # 눈 위치 조정 슬라이더 생성 헬퍼 함수 (눈 수직 전용)
        # 동기화 중 플래그 (무한 루프 방지)
        _syncing_eye_position_y = False
        
        def create_eye_position_y_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, is_left=True):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            # value_label은 나중에 슬라이더 오른쪽에 배치됨
            
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
                nonlocal _syncing_eye_position_y
                
                # 동기화 중이면 라벨만 업데이트하고 리턴 (무한 루프 방지)
                if _syncing_eye_position_y:
                    value_label.config(text=f"{int(float(value))}")
                    return
                
                # 드래그 중에는 라벨만 직접 업데이트 (성능 최적화)
                value_label.config(text=f"{int(float(value))}")
                
                # 개별 조정 모드가 아니면 동기화
                _syncing_eye_position_y = True
                try:
                    if not self.use_individual_eye_region.get():
                        if is_left:
                            # 오른쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'right_eye_position_y_label') and self.right_eye_position_y_label is not None:
                                self.right_eye_position_y_label.config(text=f"{int(float(value))}")
                            self.right_eye_position_y.set(float(value))
                        else:
                            # 왼쪽 눈 슬라이더의 라벨 직접 업데이트
                            if hasattr(self, 'left_eye_position_y_label') and self.left_eye_position_y_label is not None:
                                self.left_eye_position_y_label.config(text=f"{int(float(value))}")
                            self.left_eye_position_y.set(float(value))
                finally:
                    _syncing_eye_position_y = False
            
            def on_eye_position_y_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_eye_position_y_slider_change,  # 드래그 중에는 라벨만 업데이트
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_eye_position_y_slider_release)  # 드래그 종료 시 적용
            
            # value_label을 슬라이더 오른쪽에 배치
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
        
        # ==============================
        # 3. 눈동자 이동 범위 제한 영역
        # ==============================
        iris_clamping_frame = tk.LabelFrame(tab_frame, text="눈동자 이동 범위 제한", padx=5, pady=5)
        iris_clamping_frame.pack(fill=tk.BOTH, expand=False, pady=(5, 0))
        
        # 눈동자 이동 범위 제한 토글
        clamping_checkbox = tk.Checkbutton(
            iris_clamping_frame,
            text="눈동자 이동 범위 제한 활성화",
            variable=self.iris_clamping_enabled,
            command=self.on_morphing_change
        )
        clamping_checkbox.pack(anchor=tk.W, pady=(0, 5))
        
        # 제한 마진 비율 슬라이더
        def create_margin_slider(parent, label_text, variable, from_val, to_val, resolution, default_label=""):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=6)
            value_label.pack(side=tk.LEFT)
            
            def on_slider_change(value):
                value_label.config(text=f"{float(value):.1f}")
                self.on_morphing_change()
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=on_slider_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            return value_label
        
        self.iris_clamping_margin_ratio_label = create_margin_slider(
            iris_clamping_frame,
            "제한 마진 비율:",
            self.iris_clamping_margin_ratio,
            0.0,
            1.0,
            0.01,
            "0.3"
        )
        
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
            
            value_label = tk.Label(frame, text=default_label, width=width)
            # value_label은 나중에 슬라이더 오른쪽에 배치됨
            
            def on_slider_change(value):
                # 드래그 중에는 라벨만 업데이트 (성능 최적화)
                if hasattr(self, 'update_labels_only'):
                    self.update_labels_only()
                else:
                    # update_labels_only가 없으면 라벨만 직접 업데이트
                    if '%' in default_label:
                        value_label.config(text=f"{int(float(value) * 100)}%")
                    else:
                        value_label.config(text=f"{int(float(value))}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_morphing_change()
            
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
                command=on_slider_change,  # 드래그 중에는 라벨만 업데이트
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            scale.bind("<ButtonRelease-1>", on_slider_release)  # 드래그 종료 시 적용
            
            # value_label을 슬라이더 오른쪽에 배치
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
                from utils.logger import print_warning
                print_warning("얼굴편집V2", f"왼쪽 눈 크기 값이 유효하지 않음: {left_eye_size}, 기본값 1.0으로 설정")
                left_eye_size = 1.0
            if right_eye_size is None or not (0.1 <= right_eye_size <= 5.0):
                from utils.logger import print_warning
                print_warning("얼굴편집V2", f"오른쪽 눈 크기 값이 유효하지 않음: {right_eye_size}, 기본값 1.0으로 설정")
                right_eye_size = 1.0
            
            # 변형된 랜드마크 계산 (랜드마크 표시용)
            import utils.face_landmarks as face_landmarks
            
            # 원본 랜드마크 가져오기 (항상 원본을 기준으로 변형)
            base_landmarks = None
            # original_landmarks 가져오기 (LandmarkManager 사용)
            if not self.landmark_manager.has_original_landmarks():
                # original_landmarks가 없으면 face_landmarks 사용 (없으면 감지)
                if self.landmark_manager.get_face_landmarks() is None:
                    detected, _ = face_landmarks.detect_face_landmarks(base_image)
                    if detected is not None:
                        self.landmark_manager.set_face_landmarks(detected)
                        # 이미지 크기와 함께 바운딩 박스 계산하여 캐싱
                        img_width, img_height = base_image.size
                        self.landmark_manager.set_original_landmarks(detected, img_width, img_height)
                        self.face_landmarks = self.landmark_manager.get_face_landmarks()
                        self.original_landmarks = self.landmark_manager.get_original_landmarks()
                base_landmarks = self.landmark_manager.get_face_landmarks()
            else:
                base_landmarks = self.landmark_manager.get_original_landmarks()
            # 폴백
            if base_landmarks is None:
                base_landmarks = self.landmark_manager.get_face_landmarks()
            
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
                    
                    # transformed_landmarks 및 custom_landmarks 업데이트 (LandmarkManager 사용)
                    self.landmark_manager.set_transformed_landmarks(transformed)
                    self.landmark_manager.set_custom_landmarks(transformed, reason="__init__ use_landmark_warping")
                    self.transformed_landmarks = self.landmark_manager.get_transformed_landmarks()
                    
                    # 중앙 포인트 좌표 초기화 (original_landmarks에서 계산)
                    if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                        original = self.landmark_manager.get_original_landmarks()
                        if original is not None:
                            img_width, img_height = self.current_image.size
                            left_iris_indices, right_iris_indices = self._get_iris_indices()
                            # 드래그 좌표가 없으면 original_landmarks에서 계산
                            left_center = self.landmark_manager.get_left_iris_center_coord()
                            right_center = self.landmark_manager.get_right_iris_center_coord()
                            
                            if left_center is None:
                                left_center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                            if right_center is None:
                                right_center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                            
                            self.landmark_manager.set_iris_center_coords(left_center, right_center)
                            self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
                            self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
                    else:
                        # LandmarkManager가 없으면 기존 방식 사용
                        self.transformed_landmarks = transformed
                        self.custom_landmarks = transformed  # 직접 참조 (복사본 없음)
                        # 중앙 포인트 좌표 초기화 (original_landmarks에서 계산)
                        if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                            if hasattr(self, 'original_landmarks') and self.original_landmarks is not None:
                                img_width, img_height = self.current_image.size
                                left_iris_indices, right_iris_indices = self._get_iris_indices()
                                # 드래그 좌표가 없으면 original_landmarks에서 계산
                                if not (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None):
                                    left_center = self._calculate_iris_center(self.original_landmarks, left_iris_indices, img_width, img_height)
                                    if left_center is not None:
                                        self._left_iris_center_coord = left_center
                                if not (hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None):
                                    right_center = self._calculate_iris_center(self.original_landmarks, right_iris_indices, img_width, img_height)
                                    if right_center is not None:
                                        self._right_iris_center_coord = right_center
                else:
                    # transformed_landmarks 및 custom_landmarks 초기화 (LandmarkManager 사용)
                    self.landmark_manager.set_transformed_landmarks(None)
                    self.landmark_manager.set_custom_landmarks(None, reason="__init__ use_landmark_warping_false")
                    self.transformed_landmarks = self.landmark_manager.get_transformed_landmarks()
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
                    
                    # custom_landmarks 업데이트 (중앙 포인트는 좌표 기반으로 별도 관리)
                    self.custom_landmarks = transformed  # 직접 참조 (복사본 없음)
                    # 중앙 포인트 좌표 초기화 (original_landmarks에서 계산)
                    if hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center') and self.current_image is not None:
                        if self.original_landmarks is not None:
                            img_width, img_height = self.current_image.size
                            left_iris_indices, right_iris_indices = self._get_iris_indices()
                            # 드래그 좌표가 없으면 original_landmarks에서 계산
                            if not (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None):
                                left_center = self._calculate_iris_center(self.original_landmarks, left_iris_indices, img_width, img_height)
                                if left_center is not None:
                                    self._left_iris_center_coord = left_center
                            if not (hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None):
                                right_center = self._calculate_iris_center(self.original_landmarks, right_iris_indices, img_width, img_height)
                                if right_center is not None:
                                    self._right_iris_center_coord = right_center
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
                clamping_enabled=self.iris_clamping_enabled.get(),
                margin_ratio=self.iris_clamping_margin_ratio.get(),
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
            # 고급 모드에서 폴리곤 표시가 활성화되어 있으면 눈/입술 영역 표시는 하지 않음 (폴리곤으로 대체)
            show_polygons = hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()
            if not show_polygons:
                # 눈 영역 표시 업데이트
                if self.show_eye_region.get():
                    self.update_eye_region_display()
                # 입술 영역 표시 업데이트
                if hasattr(self, 'show_lip_region') and self.show_lip_region.get():
                    self.update_lip_region_display()
            else:
                # 폴리곤이 활성화되면 기존 타원형 영역 제거
                if hasattr(self, 'clear_eye_region_display'):
                    self.clear_eye_region_display()
                if hasattr(self, 'clear_lip_region_display'):
                    self.clear_lip_region_display()
            
            # 폴리곤 표시 업데이트 (custom_landmarks가 이미 update_polygons_only에서 업데이트되었으므로)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # custom_landmarks가 있으면 폴리곤만 다시 그리기
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            self.canvas_original.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items['original'].clear()
                    self.polygon_point_map_original.clear()
                    
                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        # custom_landmarks 가져오기 (LandmarkManager 사용)
                        custom = self.landmark_manager.get_custom_landmarks()
                        
                        if custom is not None:
                            # Tesselation 모드 확인
                            is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())
                            
                            # Tesselation 모드일 때 iris_centers 전달
                            iris_centers_for_drawing = None
                            face_landmarks_for_drawing = custom
                            
                            if is_tesselation_selected:
                                # Tesselation 모드: iris_centers 사용
                                iris_centers_for_drawing = self.landmark_manager.get_custom_iris_centers()
                                if iris_centers_for_drawing is None and len(custom) == 470:
                                    # custom_landmarks에서 중앙 포인트 추출 (마지막 2개)
                                    iris_centers_for_drawing = custom[-2:]
                                    face_landmarks_for_drawing = custom[:-2]  # 468개
                            
                            self._draw_landmark_polygons(
                                self.canvas_original,
                                self.current_image,
                                face_landmarks_for_drawing,  # 468개 또는 470개
                                self.canvas_original_pos_x,
                                self.canvas_original_pos_y,
                                self.landmark_polygon_items['original'],
                                "green",
                                current_tab,
                                iris_centers=iris_centers_for_drawing,  # Tesselation 모드일 때만 전달
                                force_use_custom=True  # custom_landmarks를 명시적으로 전달했으므로 강제 사용
                            )
                    # custom_landmarks가 없으면 전체 업데이트
                    self.update_face_features_display()


def show_face_edit_panel_v2(parent=None):
    """얼굴 편집 V2 패널 표시 (실험용 신규 패널)"""
    panel = FaceEditPanelV2(parent)
    panel.transient(parent)
    return panel
