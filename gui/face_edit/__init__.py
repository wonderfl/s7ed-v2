"""
얼굴 편집 패널 - 메인 클래스
모든 Mixin을 상속받아 통합된 FaceEditPanel 클래스를 제공
"""
import tkinter as tk

from .file import FileManagerMixin
from .preview import PreviewManagerMixin
from .canvas import CanvasEventHandlerMixin
from .morphing import MorphingManagerMixin
from .style import StyleManagerMixin
from .age import AgeManagerMixin


class FaceEditPanel(
    tk.Toplevel,
    FileManagerMixin,
    PreviewManagerMixin,
    CanvasEventHandlerMixin,
    MorphingManagerMixin,
    StyleManagerMixin,
    AgeManagerMixin
):
    """얼굴 편집 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 편집")
        self.resizable(False, False)
        
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
        self.show_eye_region = tk.BooleanVar(value=True)  # 눈 영역 표시 여부 (기본값: True)
        self.use_individual_eye_region = tk.BooleanVar(value=False)  # 눈 영역 개별 적용 여부
        self.eye_region_padding = tk.DoubleVar(value=0.3)  # 눈 영역 패딩 비율 (0.0 ~ 1.0, 기본값: 0.3)
        self.left_eye_region_padding = tk.DoubleVar(value=0.3)  # 왼쪽 눈 영역 패딩 비율
        self.right_eye_region_padding = tk.DoubleVar(value=0.3)  # 오른쪽 눈 영역 패딩 비율
        self.eye_region_offset_x = tk.DoubleVar(value=0.0)  # 눈 영역 수평 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.eye_region_offset_y = tk.DoubleVar(value=0.0)  # 눈 영역 수직 오프셋 (-20 ~ +20 픽셀, 기본값: 0)
        self.left_eye_region_offset_x = tk.DoubleVar(value=0.0)  # 왼쪽 눈 영역 수평 오프셋
        self.left_eye_region_offset_y = tk.DoubleVar(value=0.0)  # 왼쪽 눈 영역 수직 오프셋
        self.right_eye_region_offset_x = tk.DoubleVar(value=0.0)  # 오른쪽 눈 영역 수평 오프셋
        self.right_eye_region_offset_y = tk.DoubleVar(value=0.0)  # 오른쪽 눈 영역 수직 오프셋
        
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
        
        # 원본 이미지 확대/축소 변수
        self.zoom_scale_original = 1.0  # 확대/축소 비율
        self.original_image_base_size = None  # 원본 이미지 기본 크기
        
        # 얼굴 편집 폴더 경로 (config에서 로드)
        import globals as gl
        self.face_edit_dir = gl._face_extract_dir if gl._face_extract_dir else None
        
        self.create_widgets()
        
        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단 가로 배치 프레임 (파일선택 - 미리보기 - 편집설정)
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 왼쪽: 파일 선택 UI
        file_frame = self._create_file_selection_ui(top_frame)
        
        # 중앙: 미리보기 UI
        preview_frame = self._create_preview_ui(top_frame)
        
        # 오른쪽: 편집 설정 프레임
        settings_frame = tk.LabelFrame(top_frame, text="얼굴 편집 설정", padx=5, pady=5)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
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
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="준비됨", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 위젯 생성 완료 후 파일 목록 로드
        self.after(100, self.refresh_file_list)
    
    def on_close(self):
        """창 닫기"""
        self.destroy()


def show_face_edit_panel(parent=None):
    """얼굴 편집 패널 표시"""
    panel = FaceEditPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel
