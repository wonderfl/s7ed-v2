"""
얼굴 편집 패널 v2 - 전체 탭과 고급 모드 전용
단순화된 구조로 재설계된 얼굴 편집 패널
"""
import os
import tkinter as tk
from PIL import Image, ImageTk

# 핵심 Mixin들만 남기기
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
from .widget_creator import WidgetCreatorMixin
from .popup_manager import PopupManagerMixin
from .guide_line_scaling import GuideLineScalingMixin
from .landmark_manager import LandmarkManager
from .launcher import show_face_edit_panel


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
    WidgetCreatorMixin,
    PopupManagerMixin,
    GuideLineScalingMixin,
):
    """전체 탭과 고급 모드 전용 얼굴 편집 패널 v2"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 편집 v2 - 전체 탭 전용")
        self.resizable(True, True)
        
        # PolygonRendererMixin 초기화
        PolygonRendererMixin.__init__(self)

        # 캔버스 초기 크기 설정
        self.canvas_initial_width = 384
        self.canvas_initial_height = 480
        self.canvas_min_width = 288
        self.canvas_min_height = 360
        
        # 창 최소 크기 설정
        min_window_width = (self.canvas_min_width * 2) + 50
        min_window_height = self.canvas_min_height + 100
        self.minsize(min_window_width, min_window_height)
        
        # 이미지 상태
        self.current_image = None
        self.current_image_path = None
        self.aligned_image = None
        self.edited_image = None
        
        # 랜드마크 상태 관리자
        self.landmark_manager = LandmarkManager()
        
        # 얼굴 랜드마크 정보
        self.face_landmarks = None
        
        # 전체 탭 전용 변수들
        self.current_morphing_tab = "전체"  # 전체 탭만 지원
        
        # MediaPipe 부위 선택 변수 (전체 탭용)
        self.show_face_oval = tk.BooleanVar(value=False)
        self.show_left_eye = tk.BooleanVar(value=False)
        self.show_right_eye = tk.BooleanVar(value=False)
        self.show_left_eyebrow = tk.BooleanVar(value=False)
        self.show_right_eyebrow = tk.BooleanVar(value=False)
        self.show_nose = tk.BooleanVar(value=False)
        self.show_lips = tk.BooleanVar(value=False)
        self.show_contours = tk.BooleanVar(value=False)
        self.show_tesselation = tk.BooleanVar(value=False)
        
        # 표시 옵션
        self.show_landmark_points = tk.BooleanVar(value=False)
        self.show_landmark_lines = tk.BooleanVar(value=False)
        self.show_landmark_polygons = tk.BooleanVar(value=False)
        self.show_landmark_indices = tk.BooleanVar(value=False)
        self.show_region_centers = tk.BooleanVar(value=False)
        
        # 고급 모드 관련
        self.use_landmark_warping = tk.BooleanVar(value=True)
        self.use_guide_line_scaling = tk.BooleanVar(value=True)
        self.show_guide_lines = tk.BooleanVar(value=True)
        
        # 얼굴 정렬 설정
        self.auto_align = tk.BooleanVar(value=False)
        
        # 개별 영역 관련 (v2에서는 기본값 False)
        self.use_individual_eye_region = tk.BooleanVar(value=False)
        
        # 개별 탭 관련 변수들 (호환성 유지)
        self.left_eye_size = tk.DoubleVar(value=1.0)
        self.right_eye_size = tk.DoubleVar(value=1.0)
        self.eye_spacing = tk.BooleanVar(value=False)
        self.iris_clamping_enabled = tk.BooleanVar(value=True)
        self.iris_clamping_margin_ratio = tk.DoubleVar(value=0.3)
        self.left_eye_position_y = tk.DoubleVar(value=0.0)
        self.right_eye_position_y = tk.DoubleVar(value=0.0)
        self.left_eye_position_x = tk.DoubleVar(value=0.0)
        self.right_eye_position_x = tk.DoubleVar(value=0.0)
        self.show_eye_region = tk.BooleanVar(value=False)
        self.show_lip_region = tk.BooleanVar(value=False)
        self.upper_lip_shape = tk.DoubleVar(value=1.0)
        self.lower_lip_shape = tk.DoubleVar(value=1.0)
        self.upper_lip_width = tk.DoubleVar(value=1.0)
        self.lower_lip_width = tk.DoubleVar(value=1.0)
        self.upper_lip_vertical_move = tk.DoubleVar(value=0.0)
        self.lower_lip_vertical_move = tk.DoubleVar(value=0.0)
        self.jaw_size = tk.DoubleVar(value=0.0)
        self.nose_size = tk.DoubleVar(value=1.0)
        self.face_width = tk.DoubleVar(value=1.0)
        self.face_height = tk.DoubleVar(value=1.0)
        self.blend_ratio = tk.DoubleVar(value=1.0)
        
        # 추가 호환성 변수들
        self.eye_region_padding = tk.DoubleVar(value=0.3)
        self.left_eye_region_padding = tk.DoubleVar(value=0.3)
        self.right_eye_region_padding = tk.DoubleVar(value=0.3)
        self.eye_region_offset_x = tk.DoubleVar(value=0.0)
        self.eye_region_offset_y = tk.DoubleVar(value=0.0)
        self.left_eye_region_offset_x = tk.DoubleVar(value=0.0)
        self.left_eye_region_offset_y = tk.DoubleVar(value=0.0)
        self.right_eye_region_offset_x = tk.DoubleVar(value=0.0)
        self.right_eye_region_offset_y = tk.DoubleVar(value=0.0)
        self.use_individual_lip_region = tk.BooleanVar(value=False)
        self.upper_lip_region_padding_x = tk.DoubleVar(value=0.2)
        self.upper_lip_region_padding_y = tk.DoubleVar(value=0.3)
        self.lower_lip_region_padding_x = tk.DoubleVar(value=0.2)
        self.lower_lip_region_padding_y = tk.DoubleVar(value=0.3)
        self.upper_lip_region_offset_x = tk.DoubleVar(value=0.0)
        self.upper_lip_region_offset_y = tk.DoubleVar(value=0.0)
        self.lower_lip_region_offset_x = tk.DoubleVar(value=0.0)
        self.lower_lip_region_offset_y = tk.DoubleVar(value=0.0)
        self.iris_mapping_method = tk.StringVar(value="iris_outline")
        self.show_iris_connections = tk.BooleanVar(value=True)
        self.show_iris_eyelid_connections = tk.BooleanVar(value=True)
        self.show_upper_lips = tk.BooleanVar(value=False)
        self.show_lower_lips = tk.BooleanVar(value=False)
        self.show_left_iris = tk.BooleanVar(value=False)
        self.show_right_iris = tk.BooleanVar(value=False)
        self.age_adjustment = tk.DoubleVar(value=0.0)
        self.style_image_path = None
        self.color_strength = tk.DoubleVar(value=0.0)
        self.texture_strength = tk.DoubleVar(value=0.0)
        
        # 공통 슬라이더 변수
        self.region_center_offset_x = tk.DoubleVar(value=0.0)
        self.region_center_offset_y = tk.DoubleVar(value=0.0)
        self.region_size_x = tk.DoubleVar(value=1.0)
        self.region_size_y = tk.DoubleVar(value=1.0)
        self.region_position_x = tk.DoubleVar(value=0.0)
        self.region_position_y = tk.DoubleVar(value=0.0)
        
        # 폴리곤 관련
        self.polygon_expansion_level = tk.IntVar(value=1)
        self.polygon_point_map_original = set()
        self.polygon_point_map_edited = set()
        self.landmark_polygon_items = {
            'original': [],
            'edited': []
        }
        
        # 드래그 관련
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.last_selected_landmark_index = None
        self.dragged_polygon_canvas = None
        self.polygon_drag_start_x = None
        self.polygon_drag_start_y = None
        
        # 캔버스 위치
        self.canvas_original_pos_x = None
        self.canvas_original_pos_y = None
        self.canvas_edited_pos_x = None
        self.canvas_edited_pos_y = None
        
        # 확대/축소
        self.zoom_scale_original = 1.0
        self.zoom_scale_edited = 1.0
        self.zoom_max_scale = 40.0
        self.zoom_min_scale = 0.1
        
        # 미리보기 이미지
        self.tk_image_original = None
        self.tk_image_edited = None
        
        # 랜드마크 표시용 캔버스 아이템
        self.landmarks_items_original = []
        self.landmarks_items_edited = []
        self.landmarks_items_transformed = []
        
        # 바운딩 박스 표시용 캔버스 아이템
        self.bbox_rect_original = None
        
        # 눈 영역 표시용 캔버스 아이템 (호환성 유지)
        self.eye_region_rects_original = []
        self.eye_region_rects_edited = []
        
        # 입술 영역 표시용 캔버스 아이템 (호환성 유지)
        self.lip_region_rects_original = []
        self.lip_region_rects_edited = []
        
        # 폴리곤 드래그 관련 변수 (호환성 유지)
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.last_selected_landmark_index = None
        self.dragged_polygon_canvas = None
        self.polygon_drag_start_x = None
        self.polygon_drag_start_y = None
        self.polygon_drag_start_img_x = None
        self.polygon_drag_start_img_y = None
        
        # 선택된 랜드마크 표시 아이템
        self.selected_landmark_indicator_original = None
        self.selected_landmark_indicator_edited = None
        self.selected_landmark_lines_original = []
        self.selected_landmark_lines_edited = []
        
        # 캔버스 위치 추적 변수
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
        
        # 확대/축소 관련 변수
        self.zoom_scale_original = 1.0
        self.zoom_scale_edited = 1.0
        self.zoom_max_scale = 40.0
        self.zoom_min_scale = 0.1
        self.original_image_base_size = None
        self.edited_image_base_size = None
        
        # 성능 최적화 변수
        self._last_edited_image_hash = None
        self._resize_cache = {}
        self._resize_cache_max_size = 10
        
        # 확대/축소 최적화 변수
        self._zoom_update_pending = False
        self._is_zooming = False
        self._skip_morphing_change = False
        self._zoom_timer = None
        
        # 마우스 위치 저장
        self._last_mouse_x_original = None
        self._last_mouse_y_original = None
        self._last_mouse_x_edited = None
        self._last_mouse_y_edited = None
        
        # "원래대로" 버튼 플래그
        self.is_resetting_position = False
        
        # 캔버스 크기 설정
        self.preview_width = 800
        self.preview_height = 1000
        
        # 팝업창 참조
        self.file_list_popup = None
        self.settings_popup = None
        
        # 캔버스 리사이즈 제어 플래그
        self._resizing_canvas = False
        
        # 얼굴 편집 폴더 경로
        import globals as gl
        self.face_edit_dir = gl._face_extract_dir if gl._face_extract_dir else None
        
        # 설정 파일 경로
        self.settings_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        
        # 설정 로드
        self._load_settings()
        
        # UI 생성
        self.create_widgets()
        self._apply_guide_scaling_state(self.use_guide_line_scaling.get())
        
        # 창 초기 크기 및 위치 설정
        initial_window_width = (self.canvas_initial_width * 2) + 50
        initial_window_height = self.canvas_initial_height + 100
        self.geometry(f"{initial_window_width}x{initial_window_height}")
        
        # 화면 중앙 배치
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    # ========== 랜드마크 Property ==========
    
    @property
    def custom_landmarks(self):
        """사용자 수정 랜드마크"""
        return self.landmark_manager._custom_landmarks
    
    @property
    def original_landmarks(self):
        """원본 랜드마크"""
        return self.landmark_manager.get_original_landmarks_full()
    
    @original_landmarks.setter
    def original_landmarks(self, value):
        """원본 랜드마크 설정"""
        self.landmark_manager.set_original_landmarks(value)
    
    @property
    def face_landmarks(self):
        """현재 편집된 랜드마크"""
        return self.landmark_manager._face_landmarks
    
    @face_landmarks.setter
    def face_landmarks(self, value):
        """현재 편집된 랜드마크 설정"""
        if value is self.landmark_manager._face_landmarks:
            return
        self.landmark_manager.set_face_landmarks(value)
    
    @property
    def transformed_landmarks(self):
        """변형된 랜드마크"""
        return self.landmark_manager._transformed_landmarks
    
    @transformed_landmarks.setter
    def transformed_landmarks(self, value):
        """변형된 랜드마크 설정"""
        if value is self.landmark_manager._transformed_landmarks:
            return
        self.landmark_manager.set_transformed_landmarks(value)
    
    def _load_settings(self):
        """설정 파일에서 설정 로드"""
        try:
            if os.path.exists(self.settings_file_path):
                import json
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 기존 config.json 형식 호환성
                if 'face_extract_dir' in settings and settings['face_extract_dir']:
                    self.face_edit_dir = settings['face_extract_dir']
                elif 'face_edit_dir' in settings and settings['face_edit_dir']:
                    self.face_edit_dir = settings['face_edit_dir']
                
                # v2 전용 설정 (없으면 기본값 사용)
                if 'show_landmark_points' in settings:
                    self.show_landmark_points.set(settings['show_landmark_points'])
                if 'show_landmark_lines' in settings:
                    self.show_landmark_lines.set(settings['show_landmark_lines'])
                if 'show_landmark_polygons' in settings:
                    self.show_landmark_polygons.set(settings['show_landmark_polygons'])
                if 'use_landmark_warping' in settings:
                    self.use_landmark_warping.set(settings['use_landmark_warping'])
                if 'use_guide_line_scaling' in settings:
                    self.use_guide_line_scaling.set(settings['use_guide_line_scaling'])
                if 'show_guide_lines' in settings:
                    self.show_guide_lines.set(settings['show_guide_lines'])
                if 'polygon_expansion_level' in settings:
                    self.polygon_expansion_level.set(settings['polygon_expansion_level'])
                
                print(f"설정 로드 완료: {self.settings_file_path}")
                print(f"파일 경로: {self.face_edit_dir}")
        except Exception as e:
            print(f"설정 로드 실패: {e}")
    
    def _save_settings(self):
        """설정 파일에 설정 저장"""
        try:
            import json
            
            # 기존 설정 로드 (있으면)
            existing_settings = {}
            if os.path.exists(self.settings_file_path):
                try:
                    with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                        existing_settings = json.load(f)
                except:
                    existing_settings = {}
            
            # 기존 설정 유지하면서 v2 설정 추가/업데이트
            existing_settings['face_extract_dir'] = self.face_edit_dir
            existing_settings['show_landmark_points'] = self.show_landmark_points.get()
            existing_settings['show_landmark_lines'] = self.show_landmark_lines.get()
            existing_settings['show_landmark_polygons'] = self.show_landmark_polygons.get()
            existing_settings['use_landmark_warping'] = self.use_landmark_warping.get()
            existing_settings['use_guide_line_scaling'] = self.use_guide_line_scaling.get()
            existing_settings['show_guide_lines'] = self.show_guide_lines.get()
            existing_settings['polygon_expansion_level'] = self.polygon_expansion_level.get()
            
            with open(self.settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=2, ensure_ascii=False)
            
            print(f"설정 저장 완료: {self.settings_file_path}")
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    def on_close(self):
        """창 닫기"""
        try:
            # 설정 저장
            self._save_settings()
            
            # 팝업창 닫기
            if self.file_list_popup and self.file_list_popup.winfo_exists():
                self.file_list_popup.destroy()
            if self.settings_popup and self.settings_popup.winfo_exists():
                self.settings_popup.destroy()
            
            self.destroy()
        except Exception as e:
            print(f"창 닫기 실패: {e}")
            self.destroy()
