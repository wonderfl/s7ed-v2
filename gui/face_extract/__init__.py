"""
얼굴 추출 전용 패널 - 얼굴 인식을 사용하여 이미지에서 얼굴을 자동으로 추출하고 저장
"""
import os
import hashlib
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import utils.image_adjustments as image_adjustments
from gui.frame import basic as _basic
import utils.config as config
from .file import FileManagerMixin
from .preview import PreviewManagerMixin
from .canvas import CanvasEventHandlerMixin
from .save import SaveManagerMixin
from .params import ParameterManagerMixin

# 로거 (지연 로딩)
_logger = None

def _get_logger():
    """로거 가져오기 (지연 로딩)"""
    global _logger
    if _logger is None:
        from utils.logger import get_logger
        _logger = get_logger('얼굴추출')
    return _logger

class FaceExtractPanel(FileManagerMixin, PreviewManagerMixin, CanvasEventHandlerMixin, SaveManagerMixin, ParameterManagerMixin, tk.Toplevel):
    """얼굴 추출 전용 패널 - 얼굴 인식이 항상 활성화"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 추출")
        self.resizable(False, False)
        
        # 현재 선택된 이미지
        self.current_image = None
        self.current_image_path = None
        self.extracted_image = None
        self.palette_applied_image = None  # 팔레트 적용된 이미지
        
        # 얼굴 정보
        self.face_detected = False
        self.detected_face_region = None  # (x, y, w, h)
        self.detected_eye_y = None  # 자동 감지 모드에서 감지된 눈높이 (수동 영역 모드에서 사용)
        self.detected_landmarks = None  # MediaPipe로 감지된 랜드마크 포인트 리스트
        self.detected_key_landmarks = None  # 주요 랜드마크 딕셔너리
        self.crop_start_coords = None  # 크롭 시작 좌표 (x_start, y_start) - 성능 최적화용
        
        # 설정값
        self.crop_scale = tk.DoubleVar(value=2.0)  # 기본값: 2.0 (200%)
        self.center_offset_x = tk.IntVar(value=0)
        self.center_offset_y = tk.IntVar(value=0)
        self.use_mediapipe = tk.BooleanVar(value=True)  # MediaPipe 사용 여부 (기본값: True, MediaPipe 사용)
        self.show_landmarks = tk.BooleanVar(value=False)  # 랜드마크 표시 여부
        
        # 팔레트 변환 설정
        self.palette_method = tk.StringVar(value='nearest')  # 'nearest', 'quantize', 'dither' (기본값: nearest - 더 정확함)
        self.use_palette = tk.BooleanVar(value=True)  # 팔레트 적용 여부
        
        # 밝기/대비 조정 설정
        self.brightness = tk.DoubleVar(value=1.0)  # 밝기 (0.0 ~ 2.0, 기본값: 1.0)
        self.contrast = tk.DoubleVar(value=1.0)  # 대비 (0.0 ~ 2.0, 기본값: 1.0)
        self.color_temp = tk.DoubleVar(value=0.0)  # 색온도 (-100 ~ 100, 기본값: 0.0, 음수=차갑게, 양수=따뜻하게)
        self.saturation = tk.DoubleVar(value=1.0)  # 채도 (0.0 ~ 2.0, 기본값: 1.0)
        self.hue = tk.DoubleVar(value=0.0)  # 색조 (-180 ~ 180, 기본값: 0.0, 음수=반시계방향, 양수=시계방향)
        self.sharpness = tk.DoubleVar(value=1.0)  # 선명도 (0.0 ~ 2.0, 기본값: 1.0, 1.0 미만=흐림, 1.0 초과=선명)
        self.exposure = tk.DoubleVar(value=1.0)  # 노출 (0.0 ~ 2.0, 기본값: 1.0, 1.0 미만=어둡게, 1.0 초과=밝게)
        self.equalize = tk.DoubleVar(value=0.0)  # 평탄화 (0.0 ~ 1.0, 기본값: 0.0, 0.0=평탄화 없음, 1.0=완전 평탄화)
        self.gamma = tk.DoubleVar(value=1.0)  # 감마 보정 (0.5 ~ 2.0, 기본값: 1.0)
        self.vibrance = tk.DoubleVar(value=1.0)  # 비브런스 (0.0 ~ 2.0, 기본값: 1.0)
        self.clarity = tk.DoubleVar(value=0.0)  # 명확도 (-100 ~ +100, 기본값: 0.0)
        self.dehaze = tk.DoubleVar(value=0.0)  # 안개 제거 (-100 ~ +100, 기본값: 0.0)
        self.tint = tk.DoubleVar(value=0.0)  # 틴트 (-150 ~ +150, 기본값: 0.0)
        self.noise_reduction = tk.DoubleVar(value=0.0)  # 노이즈 제거 (0.0 ~ 100.0, 기본값: 0.0)
        self.vignette = tk.DoubleVar(value=0.0)  # 비네팅 (-100 ~ +100, 기본값: 0.0)
        self.empty1 = tk.DoubleVar(value=0.0)  # 틴트 (-150 ~ +150, 기본값: 0.0)
        self.empty2 = tk.DoubleVar(value=0.0)  # 틴트 (-150 ~ +150, 기본값: 0.0)
        
        # 수동 영역 설정
        self.use_manual_region = tk.BooleanVar(value=False)
        self.manual_x = tk.IntVar(value=0)
        self.manual_y = tk.IntVar(value=0)
        self.manual_w = tk.IntVar(value=0)
        self.manual_h = tk.IntVar(value=0)
        
        # 미리보기 이미지
        self.tk_image_original = None
        self.tk_image_extracted_original = None
        self.tk_image_extracted_adjusted = None
        self.tk_image_palette = None
        self.image_created_original = None
        self.image_created_extracted_original = None
        self.image_created_extracted_adjusted = None
        self.image_created_palette = None
        self.grid_lines_extracted = []  # 추출 이미지 격자선 ID 저장
        self.face_center_marker_extracted = None  # 추출 원본 이미지에 그려진 얼굴 중심점 마커
        self.crop_rect_original = None  # 원본 이미지에 그려진 얼굴/수동 영역 테두리
        self.actual_crop_rect_original = None  # 원본 이미지에 그려진 실제 크롭 영역 테두리
        
        # 성능 최적화용 캐시
        self._adjusted_image_cache = None  # 조정 이미지 캐시 {'hash': str, 'image': PIL.Image}
        self._palette_image_cache = None  # 팔레트 이미지 캐시 {'hash': str, 'image': PIL.Image}
        self._original_preview_cache = None  # 원본 미리보기 캐시 {'hash': str, 'image': PIL.Image}
        self._landmarks_adjusted_cache = None  # 랜드마크 좌표 조정 캐시 {'hash': str, 'landmarks': list}
        
        # 저장 위치 (나중에 사용 예정)
        self.face_entry = None
        
        # 드래그 관련 변수
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_original_x = None
        self.drag_original_y = None
        self.is_dragging = False
        
        # 얼굴 추출 폴더 경로 (config에서 로드) - 불러오기와 저장 모두 이 폴더 사용
        import globals as gl
        self.face_extract_dir = gl._face_extract_dir if gl._face_extract_dir else None
        
        self.create_widgets()
        
        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단 좌우 배치 프레임
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 왼쪽: 파일 선택 UI
        file_frame = self._create_file_selection_ui(top_frame)
        
        # 오른쪽: 설정 프레임
        settings_frame = tk.LabelFrame(top_frame, text="face Area Settings", padx=5, pady=5)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 얼굴 영역 설정 UI
        self._create_face_area_settings_ui(settings_frame)
        
        # 이미지 조정 UI
        self._create_image_adjustment_ui(settings_frame)
        
        # 팔레트 설정 UI
        self._create_palette_settings_ui(settings_frame)
        
        # 수동 영역 설정 UI
        self._create_manual_region_ui(settings_frame)
        
        # 미리보기 UI
        self._create_preview_ui(main_frame)
        
        # 상태 표시 (에러/경고 메시지만 표시)
        self.status_label = tk.Label(main_frame, text="", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 위젯 생성 완료 후 파일 목록 로드
        self.after(100, self.refresh_file_list)
        
        # 라벨 매핑 초기화 (라벨들이 모두 생성된 후)
        self._init_label_mapping()
    
    def _create_file_selection_ui(self, parent):
        """파일 선택 UI 생성"""
        file_frame = tk.LabelFrame(parent, text="이미지 파일 선택", padx=5, pady=5)
        file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 파일 목록 프레임
        list_frame = tk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 리스트박스와 스크롤바
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=8)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 리스트박스 이벤트 바인딩
        self.file_listbox.bind('<Double-Button-1>', lambda e: self.on_file_select())
        self.file_listbox.bind('<Return>', lambda e: self.on_file_select())
        self.file_listbox.bind('<Up>', lambda e: self.on_listbox_key())
        self.file_listbox.bind('<Down>', lambda e: self.on_listbox_key())
        self.file_listbox.bind('<<ListboxSelect>>', lambda e: self.on_listbox_select())
        
        # 버튼 프레임
        button_frame = tk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=12)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="찾아보기...", command=self.browse_file, width=12)
        btn_browse.pack(side=tk.LEFT)
        
        return file_frame
    
    def _create_face_area_settings_ui(self, parent):
        """얼굴 영역 설정 UI 생성"""
        scaled_length = 240
        label_width = 12
        
        # 얼굴 영역 설정 슬라이더 (한 줄에 배치)
        face_area_frame = tk.Frame(parent)
        face_area_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 크기 비율 설정
        scale_frame = tk.Frame(face_area_frame)
        scale_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Size Ratio 타이틀 라벨에 클릭 이벤트 바인딩
        def reset_size_ratio(event):
            scale_scale.set(2.0)
            self.crop_scale.set(2.0)
            self.on_setting_change()
        
        size_ratio_label = tk.Label(scale_frame, text="Size Ratio:", width=label_width, anchor="e", cursor="hand2")
        size_ratio_label.pack(side=tk.LEFT, padx=(0, 5))
        size_ratio_label.bind("<Button-1>", reset_size_ratio)
        
        scale_scale = tk.Scale(
            scale_frame,
            from_=0.5,
            to=5.0,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=self.crop_scale,
            command=self.on_setting_change,
            length=scaled_length,
            showvalue=False
        )
        scale_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.scale_label = tk.Label(scale_frame, text="200%", width=8)
        self.scale_label.pack(side=tk.LEFT)
        
        # X 오프셋 (좌우)
        offset_x_frame = tk.Frame(face_area_frame)
        offset_x_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # X Offset 타이틀 라벨에 클릭 이벤트 바인딩
        def reset_x_offset(event):
            offset_x_scale.set(0)
            self.center_offset_x.set(0)
            self.on_setting_change()
        
        x_offset_label = tk.Label(offset_x_frame, text="X Offset:", width=label_width, anchor="e", cursor="hand2")
        x_offset_label.pack(side=tk.LEFT, padx=(0, 5))
        x_offset_label.bind("<Button-1>", reset_x_offset)
        
        offset_x_scale = tk.Scale(
            offset_x_frame,
            from_=-200,
            to=200,
            resolution=1,
            orient=tk.HORIZONTAL,
            variable=self.center_offset_x,
            command=self.on_setting_change,
            length=scaled_length,
            showvalue=False
        )
        offset_x_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.offset_x_label = tk.Label(offset_x_frame, text="0", width=6)
        self.offset_x_label.pack(side=tk.LEFT)
        
        # Y 오프셋 (상하)
        offset_y_frame = tk.Frame(face_area_frame)
        offset_y_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Y Offset 타이틀 라벨에 클릭 이벤트 바인딩
        def reset_y_offset(event):
            offset_y_scale.set(0)
            self.center_offset_y.set(0)
            self.on_setting_change()
        
        y_offset_label = tk.Label(offset_y_frame, text="Y Offset:", width=label_width, anchor="e", cursor="hand2")
        y_offset_label.pack(side=tk.LEFT, padx=(0, 5))
        y_offset_label.bind("<Button-1>", reset_y_offset)
        
        offset_y_scale = tk.Scale(
            offset_y_frame,
            from_=-200,
            to=200,
            resolution=1,
            orient=tk.HORIZONTAL,
            variable=self.center_offset_y,
            command=self.on_setting_change,
            length=scaled_length,
            showvalue=False
        )
        offset_y_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.offset_y_label = tk.Label(offset_y_frame, text="0", width=6)
        self.offset_y_label.pack(side=tk.LEFT)
    
    def _create_image_adjustment_ui(self, parent):
        """이미지 조정 UI 생성"""
        scaled_length = 240
        label_width = 12
        
        # 밝기/대비 조정 프레임
        adjust_frame = tk.LabelFrame(parent, text="Image Processing", padx=5, pady=5)
        adjust_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 초기화 버튼
        reset_button_frame = tk.Frame(adjust_frame)
        reset_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_reset = tk.Button(
            reset_button_frame,
            text="초기화",
            command=self.reset_adjustments,
            width=10,
            bg="#FF9800",
            fg="white"
        )
        btn_reset.pack(side=tk.LEFT)
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            # 기본값이 없으면 변수의 현재 값을 기본값으로 사용
            if default_value is None:
                default_value = variable.get()
            
            # 기본값을 명시적으로 저장 (클로저 문제 방지)
            reset_value = default_value
            
            # 타이틀 라벨 생성 및 클릭 이벤트 바인딩 (해당 슬라이더만 초기화)
            def reset_single_slider(event):
                # 슬라이더 값 변경 (Scale 위젯의 set 메서드 직접 호출)
                scale.set(reset_value)
                # 변수도 동기화
                variable.set(reset_value)
                # 슬라이더 값 변경 후 즉시 업데이트
                self.on_adjust_change()
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            title_label.bind("<Button-1>", reset_single_slider)
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_adjust_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 1줄: 밝기, 감마, 노출 (밝기 관련)
        row1_frame = tk.Frame(adjust_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.brightness_label = create_slider(row1_frame, "Brightness:", self.brightness, 0.5, 1.5, 0.01, "100%", default_value=1.0)
        self.gamma_label = create_slider(row1_frame, "Gamma:", self.gamma, 0.5, 2.0, 0.01, "100%", default_value=1.0)
        self.exposure_label = create_slider(row1_frame, "Exposure:", self.exposure, 0.5, 1.5, 0.01, "100%", default_value=1.0)
        
        # 2줄: 대비, 선명도, Clarity (대비/선명도 관련)
        row2_frame = tk.Frame(adjust_frame)
        row2_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.contrast_label = create_slider(row2_frame, "Contrast:", self.contrast, 0.5, 1.5, 0.01, "100%", default_value=1.0)
        self.sharpness_label = create_slider(row2_frame, "Sharpness:", self.sharpness, 0.0, 3.0, 0.01, "100%", default_value=1.0)
        self.clarity_label = create_slider(row2_frame, "Clarity:", self.clarity, -100.0, 100.0, 1.0, "0", default_value=0.0)
        
        # 3줄: Dehaze, 평탄화, Noise Reduction
        row3_frame = tk.Frame(adjust_frame)
        row3_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.dehaze_label = create_slider(row3_frame, "Dehaze:", self.dehaze, -100.0, 100.0, 1.0, "0", default_value=0.0)
        self.vibrance_label = create_slider(row3_frame, "Vibrance:", self.vibrance, 0.0, 2.0, 0.01, "100%", default_value=1.0)        
        self.vignette_label = create_slider(row3_frame, "Vignette:", self.vignette, -100.0, 100.0, 1.0, "0", default_value=0.0)        
        
        # 4줄: 채도, Vibrance, 색조 (색상 관련)
        row4_frame = tk.Frame(adjust_frame)
        row4_frame.pack(fill=tk.X, pady=(0, 5))

        self.hue_label = create_slider(row4_frame, "Hue:", self.hue, -60.0, 60.0, 1.0, "0", default_value=0.0)        
        self.saturation_label = create_slider(row4_frame, "Saturation:", self.saturation, 0.5, 1.5, 0.01, "100%", default_value=1.0)
        self.equalize_label = create_slider(row4_frame, "Equalize:", self.equalize, 0.0, 0.5, 0.005, "0%", default_value=0.0)
        
        # 5줄: 색온도, 틴트, Vignette
        row5_frame = tk.Frame(adjust_frame)
        row5_frame.pack(fill=tk.X)
        
        self.color_temp_label = create_slider(row5_frame, "Color Temp:", self.color_temp, -300.0, 300.0, 1.0, "0", default_value=0.0)
        self.tint_label = create_slider(row5_frame, "Tint:", self.tint, -150.0, 150.0, 1.0, "0", default_value=0.0)
        self.noise_reduction_label = create_slider(row5_frame, "DeNoise:", self.noise_reduction, 0.0, 100.0, 1.0, "0", default_value=0.0)
    
    def _create_palette_settings_ui(self, parent):
        """팔레트 설정 UI 생성"""
        # 팔레트 변환 설정 프레임
        palette_frame = tk.LabelFrame(parent, text="팔레트 변환 설정", padx=5, pady=5)
        palette_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 팔레트 적용 체크박스
        palette_check = tk.Checkbutton(
            palette_frame,
            text="팔레트 적용",
            variable=self.use_palette,
            command=self.on_palette_setting_change
        )
        palette_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 변환 방법 선택
        tk.Label(palette_frame, text="방법:").pack(side=tk.LEFT, padx=(0, 5))
        method_combo = tk.OptionMenu(
            palette_frame,
            self.palette_method,
            'nearest',
            'quantize',
            'dither',
            command=self.on_palette_setting_change
        )
        method_combo.pack(side=tk.LEFT)
    
    def _create_manual_region_ui(self, parent):
        """수동 영역 설정 UI 생성"""
        # 수동 영역 설정 프레임
        manual_frame = tk.LabelFrame(parent, text="Face Detect Settings", padx=5, pady=5)
        manual_frame.pack( fill=tk.X, pady=(0, 5))

        # 체크박스들을 같은 줄에 배치하기 위한 상위 프레임
        checkbox_frame = tk.Frame(manual_frame)
        checkbox_frame.pack(fill=tk.X, pady=(5, 0))

        # MediaPipe 옵션 체크박스
        mediapipe_frame = tk.Frame(checkbox_frame)
        mediapipe_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # MediaPipe 사용 가능 여부 확인
        try:
            from utils.face_landmarks import is_available
            mediapipe_available = is_available()
        except ImportError:
            mediapipe_available = False
        
        if mediapipe_available:
            mediapipe_check = tk.Checkbutton(
                mediapipe_frame,
                text="MediaPipe 사용",
                variable=self.use_mediapipe,
                command=self.on_setting_change
            )
            mediapipe_check.pack(side=tk.LEFT)
            
            # 랜드마크 표시 체크박스
            landmarks_check = tk.Checkbutton(
                mediapipe_frame,
                text="랜드마크 표시",
                variable=self.show_landmarks,
                command=self.on_landmarks_toggle
            )
            landmarks_check.pack(side=tk.LEFT, padx=(10, 0))
        else:
            mediapipe_label = tk.Label(
                mediapipe_frame,
                text="MediaPipe 사용 불가 (설치 필요: pip install mediapipe)",
                fg="gray"
            )
            mediapipe_label.pack(side=tk.LEFT)              

        # 수동 영역 사용 체크박스
        check_frame = tk.Frame(checkbox_frame)
        check_frame.pack(side=tk.LEFT)
        
        manual_check = tk.Checkbutton(
            check_frame,
            text="수동 영역",
            variable=self.use_manual_region,
            command=self.on_manual_region_toggle
        )
        manual_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 영역 좌표 입력 필드
        coord_frame = tk.Frame(check_frame)
        coord_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(coord_frame, text="X:").pack(side=tk.LEFT, padx=(0, 2))
        self.manual_x_entry = tk.Entry(coord_frame, width=6, textvariable=self.manual_x, state=tk.DISABLED)
        self.manual_x_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.manual_x_entry.bind("<KeyRelease>", lambda e: self.on_manual_region_change())
        
        tk.Label(coord_frame, text="Y:").pack(side=tk.LEFT, padx=(0, 2))
        self.manual_y_entry = tk.Entry(coord_frame, width=6, textvariable=self.manual_y, state=tk.DISABLED)
        self.manual_y_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.manual_y_entry.bind("<KeyRelease>", lambda e: self.on_manual_region_change())
        
        tk.Label(coord_frame, text="너비:").pack(side=tk.LEFT, padx=(0, 2))
        self.manual_w_entry = tk.Entry(coord_frame, width=6, textvariable=self.manual_w, state=tk.DISABLED)
        self.manual_w_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.manual_w_entry.bind("<KeyRelease>", lambda e: self.on_manual_region_change())
        
        tk.Label(coord_frame, text="높이:").pack(side=tk.LEFT, padx=(0, 2))
        self.manual_h_entry = tk.Entry(coord_frame, width=6, textvariable=self.manual_h, state=tk.DISABLED)
        self.manual_h_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.manual_h_entry.bind("<KeyRelease>", lambda e: self.on_manual_region_change())
        
        # 화면 비율 표시
        tk.Label(coord_frame, text="화면 비율:").pack(side=tk.LEFT, padx=(10, 2))
        self.face_percentage_label = tk.Label(coord_frame, text="0.0%", width=8, fg="blue")
        self.face_percentage_label.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_apply_detected = tk.Button(coord_frame, text="감지된 값 적용", command=self.apply_detected_region, width=15)
        btn_apply_detected.pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""
        # 이미지 미리보기 프레임 (4개 이미지 나란히 표시)
        preview_frame = tk.LabelFrame(parent, text="미리보기", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 이미지 크기: 288x360
        preview_width = 288
        preview_height = 360
        
        # 1. 좌측: 원본 이미지
        left_frame = tk.Frame(preview_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.label_original = tk.Label(left_frame, text="원본 이미지", font=("", 9), width=40, anchor="w")
        self.label_original.pack()
        self.canvas_original = tk.Canvas(
            left_frame, 
            width=preview_width, 
            height=preview_height,
            bg="gray"
        )
        self.canvas_original.pack(padx=5, pady=5)
        
        # 마우스 드래그 이벤트 바인딩 (수동 영역 모드일 때만)
        self.canvas_original.bind("<Button-1>", self.on_canvas_click)
        self.canvas_original.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # 2. 추출 원본 (조정 전)
        extracted_original_frame = tk.Frame(preview_frame)
        extracted_original_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        extracted_original_top_frame = tk.Frame(extracted_original_frame)
        extracted_original_top_frame.pack(fill=tk.X)
        
        self.label_extracted_original = tk.Label(extracted_original_top_frame, text="추출 원본", font=("", 9))
        self.label_extracted_original.pack(side=tk.LEFT)
        
        btn_save_extracted_original = tk.Button(extracted_original_top_frame, text="원본 저장", command=self.save_extracted_png, width=12, bg="#4CAF50", fg="white")
        btn_save_extracted_original.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_extracted_original = tk.Canvas(
            extracted_original_frame, 
            width=preview_width, 
            height=preview_height,
            bg="gray"
        )
        self.canvas_extracted_original.pack(padx=5, pady=5)
        
        # 3. 추출 조정 (조정 후)
        extracted_adjusted_frame = tk.Frame(preview_frame)
        extracted_adjusted_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        extracted_adjusted_top_frame = tk.Frame(extracted_adjusted_frame)
        extracted_adjusted_top_frame.pack(fill=tk.X)
        
        self.label_extracted_adjusted = tk.Label(extracted_adjusted_top_frame, text="추출 조정", font=("", 9))
        self.label_extracted_adjusted.pack(side=tk.LEFT)
        
        self.canvas_extracted_adjusted = tk.Canvas(
            extracted_adjusted_frame, 
            width=preview_width, 
            height=preview_height,
            bg="gray"
        )
        self.canvas_extracted_adjusted.pack(padx=5, pady=5)
        
        # 4. 우측: 팔레트 적용 버전
        right_frame = tk.Frame(preview_frame)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        right_top_frame = tk.Frame(right_frame)
        right_top_frame.pack(fill=tk.X)
        
        self.label_palette = tk.Label(right_top_frame, text="팔레트 적용", font=("", 9))
        self.label_palette.pack(side=tk.LEFT)
        
        btn_save_png = tk.Button(right_top_frame, text="PNG 저장", command=self.save_png, width=12, bg="#2196F3", fg="white")
        btn_save_png.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_delete_png = tk.Button(right_top_frame, text="삭제", command=self.delete_png, width=12, bg="#F44336", fg="white", state=tk.DISABLED)
        self.btn_delete_png.pack(side=tk.LEFT, padx=(5, 0))
        
        # 파라미터 파일 존재 여부 표시 라벨
        self.params_status_label = tk.Label(right_top_frame, text="", fg="gray", font=("", 8))
        self.params_status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.canvas_palette = tk.Canvas(
            right_frame, 
            width=preview_width, 
            height=preview_height,
            bg="gray"
        )
        self.canvas_palette.pack(padx=5, pady=5)
    
    def _update_preview_titles(self, filename):
        """미리보기 타이틀에 파일명 추가 (원본 이미지만)"""
        if filename:
            # 파일명이 너무 길면 잘라서 표시 (최대 30자)
            if len(filename) > 30:
                display_name = filename[:27] + "..."
            else:
                display_name = filename
            self.label_original.config(text=f"원본 이미지 ({display_name})")
        else:
            self.label_original.config(text="원본 이미지")
    
    def on_setting_change(self, value=None):
        """설정 변경 시 호출"""
        # 라벨 업데이트
        scale_value = self.crop_scale.get()
        self.scale_label.config(text=f"{int(scale_value * 100)}%")
        
        offset_x = self.center_offset_x.get()
        self.offset_x_label.config(text=str(offset_x))
        
        offset_y = self.center_offset_y.get()
        self.offset_y_label.config(text=str(offset_y))
        
        # 이미지가 로드되어 있으면 재추출 (모든 모드에서)
        if self.current_image is not None:
            self.extract_face()
            # 크롭 영역 테두리 업데이트
            self.draw_crop_region_on_original()
    
    def on_palette_setting_change(self):
        """팔레트 설정 변경 시 호출"""
        # 팔레트 적용 버전 재계산 및 표시
        if self.extracted_image is not None:
            self.update_palette_preview()
    
    def on_landmarks_toggle(self):
        """랜드마크 표시 체크박스 토글"""
        # 원본 이미지 미리보기 업데이트
        if self.current_image is not None:
            self.show_original_preview()
    
    def on_manual_region_toggle(self):
        """수동 영역 사용 체크박스 토글"""
        if self.use_manual_region.get():
            # 수동 영역 입력 필드 활성화
            self.manual_x_entry.config(state=tk.NORMAL)
            self.manual_y_entry.config(state=tk.NORMAL)
            self.manual_w_entry.config(state=tk.NORMAL)
            self.manual_h_entry.config(state=tk.NORMAL)
        else:
            # 수동 영역 입력 필드 비활성화
            self.manual_x_entry.config(state=tk.DISABLED)
            self.manual_y_entry.config(state=tk.DISABLED)
            self.manual_w_entry.config(state=tk.DISABLED)
            self.manual_h_entry.config(state=tk.DISABLED)
            
            # 체크박스를 해제하면 자동 감지 모드로 전환
            # 감지된 영역이 있으면 그 값을 유지하고, 없으면 자동 감지 시도
            if self.detected_face_region is None and self.current_image is not None:
                # 자동 감지 시도 (수동 영역 없이)
                try:
                    crop_scale = self.crop_scale.get()
                    offset_x = self.center_offset_x.get()
                    offset_y = self.center_offset_y.get()
                    
                    result = kaodata_image.extract_face_region(
                        self.current_image.copy(),
                        crop_scale=crop_scale,
                        center_offset_x=offset_x,
                        center_offset_y=offset_y,
                        manual_region=None,  # 자동 감지
                        return_face_region=True,
                        use_mediapipe=self.use_mediapipe.get()
                    )
                    
                    if isinstance(result, tuple):
                        self.extracted_image, detected_region = result
                        if detected_region is not None:
                            self.detected_face_region = detected_region
                            # 수동 영역 입력 필드에 자동으로 채우기
                            x, y, w, h = detected_region
                            self.manual_x.set(x)
                            self.manual_y.set(y)
                            self.manual_w.set(w)
                            self.manual_h.set(h)
                            self.face_detected = True
                            self.show_extracted_original()
                            self.show_extracted_adjusted()
                            self.show_original_preview()
                            self.draw_crop_region_on_original()
                            self.status_label.config(
                                text=f"자동 감지 완료 | 감지된 영역: 위치=({x}, {y}), 크기={w}x{h}",
                                fg="green"
                            )
                            return
                except Exception as e:
                    # 자동 감지 실패는 무시 (사용자가 수동으로 조정할 수 있음)
                    _get_logger().warning(f"자동 감지 실패: {e}")
        
        # 이미지가 로드되어 있으면 재추출 (수동 영역 모드일 때만)
        if self.current_image is not None:
            self.extract_face()
    
    def on_manual_region_change(self):
        """수동 영역 입력 필드 변경 시 호출"""
        if self.use_manual_region.get() and self.current_image is not None:
            # 수동 영역 변경 시 즉시 재계산
            try:
                # 수동 영역 좌표 가져오기
                x = int(self.manual_x.get())
                y = int(self.manual_y.get())
                w = int(self.manual_w.get())
                h = int(self.manual_h.get())
                
                # extract_face() 호출
                self.extract_face()
                
                # UI 강제 업데이트 (extract_face()에서 업데이트되지만 확실히 하기 위해)
                self.update_idletasks()
                
                # 화면 비율 강제 재계산 및 UI 업데이트 (크롭된 이미지 사용)
                if self.detected_face_region is not None and self.extracted_image is not None:
                    crop_scale = self.crop_scale.get()
                    offset_x = self.center_offset_x.get()
                    offset_y = self.center_offset_y.get()
                    face_percentage = self._calculate_face_percentage(self.detected_face_region, crop_scale, offset_x, offset_y, self.extracted_image)
                    if hasattr(self, 'face_percentage_label'):
                        self.face_percentage_label.config(text=f"{face_percentage:.1f}%")
                        self.face_percentage_label.update_idletasks()
                
                # 크롭 영역 테두리 업데이트
                self.draw_crop_region_on_original()
            except (ValueError, tk.TclError):
                # 유효하지 않은 값이면 무시
                pass
    
    def on_palette_setting_change(self, value=None):
        """팔레트 설정 변경 시 호출"""
        # 팔레트 미리보기 업데이트
        self.update_palette_preview()
    
    def reset_adjustments(self):
        """이미지 조정 값들을 모두 초기화"""
        # 모든 조정 값을 기본값으로 설정
        self.equalize.set(0.0)
        self.brightness.set(1.0)
        self.contrast.set(1.0)
        self.saturation.set(1.0)
        self.hue.set(0.0)
        self.exposure.set(1.0)
        self.color_temp.set(0.0)
        self.sharpness.set(1.0)
        self.gamma.set(1.0)
        self.vibrance.set(1.0)
        self.clarity.set(0.0)
        self.dehaze.set(0.0)
        self.tint.set(0.0)
        self.noise_reduction.set(0.0)
        self.vignette.set(0.0)
        
        # 라벨 업데이트
        self.on_adjust_change()
        
        # 미리보기 업데이트
        if self.extracted_image is not None:
            self.show_extracted_original()
            self.show_extracted_adjusted()
            self.update_palette_preview()
    
    def _get_adjustment_values(self):
        """모든 이미지 조정 값을 딕셔너리로 반환"""
        return {
            'equalize': self.equalize.get(),
            'brightness': self.brightness.get(),
            'contrast': self.contrast.get(),
            'noise_reduction': self.noise_reduction.get(),
            'clarity': self.clarity.get(),
            'dehaze': self.dehaze.get(),
            'saturation': self.saturation.get(),
            'vibrance': self.vibrance.get(),
            'hue': self.hue.get(),
            'color_temp': self.color_temp.get(),
            'tint': self.tint.get(),
            'gamma': self.gamma.get(),
            'exposure': self.exposure.get(),
            'sharpness': self.sharpness.get(),
            'vignette': self.vignette.get(),
        }
    
    def _get_adjustments_hash(self):
        """조정값 해시 생성"""
        adjustments = self._get_adjustment_values()
        # 딕셔너리를 정렬된 튜플로 변환하여 일관된 해시 생성
        adjustments_str = str(sorted(adjustments.items()))
        return hashlib.md5(adjustments_str.encode()).hexdigest()
    
    def _get_palette_settings_hash(self):
        """팔레트 설정 해시 생성 (조정값 + 팔레트 방법 + 디더링 여부)"""
        adjustments_hash = self._get_adjustments_hash()
        method = self.palette_method.get()
        dither = (method == 'dither')
        settings_str = f"{adjustments_hash}_{method}_{dither}"
        return hashlib.md5(settings_str.encode()).hexdigest()
    
    def _get_original_preview_hash(self):
        """원본 미리보기 해시 생성 (이미지 크기 + 크롭 영역)"""
        if self.current_image is None:
            return None
        img_width, img_height = self.current_image.size
        # 96x120 비율로 크롭하므로 크롭 영역은 이미지 크기에 따라 결정됨
        target_ratio = 96 / 120
        img_ratio = img_width / img_height
        if img_ratio > target_ratio:
            crop_height = img_height
            crop_width = int(crop_height * target_ratio)
        else:
            crop_width = img_width
            crop_height = int(crop_width / target_ratio)
        preview_str = f"{img_width}_{img_height}_{crop_width}_{crop_height}"
        return hashlib.md5(preview_str.encode()).hexdigest()
    
    def _get_landmarks_adjusted_hash(self):
        """랜드마크 좌표 조정 해시 생성 (크롭 영역 기준)"""
        if self.current_image is None:
            return None
        img_width, img_height = self.current_image.size
        target_ratio = 96 / 120
        img_ratio = img_width / img_height
        if img_ratio > target_ratio:
            crop_height = img_height
            crop_width = int(crop_height * target_ratio)
        else:
            crop_width = img_width
            crop_height = int(crop_width / target_ratio)
        # 크롭 영역은 항상 (0, 0)에서 시작하므로 x_start, y_start는 0
        hash_str = f"{img_width}_{img_height}_{crop_width}_{crop_height}_0_0"
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def _init_label_mapping(self):
        """라벨-변수 매핑 딕셔너리 초기화"""
        # 포맷 함수 정의
        def format_percent(value):
            return f"{int(value * 100)}%"
        
        def format_int(value):
            return f"{int(value)}"
        
        # 라벨-변수-포맷 매핑
        self._label_mapping = {
            'brightness': (self.brightness, self.brightness_label, format_percent),
            'contrast': (self.contrast, self.contrast_label, format_percent),
            'saturation': (self.saturation, self.saturation_label, format_percent),
            'sharpness': (self.sharpness, self.sharpness_label, format_percent),
            'exposure': (self.exposure, self.exposure_label, format_percent),
            'equalize': (self.equalize, self.equalize_label, format_percent),
            'gamma': (self.gamma, self.gamma_label, format_percent),
            'vibrance': (self.vibrance, self.vibrance_label, format_percent),
            'color_temp': (self.color_temp, self.color_temp_label, format_int),
            'hue': (self.hue, self.hue_label, format_int),
            'clarity': (self.clarity, self.clarity_label, format_int),
            'dehaze': (self.dehaze, self.dehaze_label, format_int),
            'tint': (self.tint, self.tint_label, format_int),
            'noise_reduction': (self.noise_reduction, self.noise_reduction_label, format_int),
            'vignette': (self.vignette, self.vignette_label, format_int),
        }
    
    def on_adjust_change(self, value=None):
        """밝기/대비/색온도/채도 조정 시 호출"""
        # 라벨 업데이트 (자동화)
        if not hasattr(self, '_label_mapping'):
            self._init_label_mapping()
        
        for key, (variable, label, formatter) in self._label_mapping.items():
            value = variable.get()
            label.config(text=formatter(value))
        
        # 이미지가 로드되어 있으면 미리보기 업데이트
        if self.extracted_image is not None:
            # 추출된 이미지 미리보기 업데이트
            self.show_extracted_original()
            self.show_extracted_adjusted()
            # 팔레트 미리보기 업데이트
            self.update_palette_preview()
    
    def apply_detected_region(self):
        """감지된 얼굴 영역을 수동 영역 입력 필드에 적용"""
        if self.detected_face_region is not None:
            x, y, w, h = self.detected_face_region
            self.manual_x.set(x)
            self.manual_y.set(y)
            self.manual_w.set(w)
            self.manual_h.set(h)
            self.use_manual_region.set(True)
            self.on_manual_region_toggle()
    def _calculate_face_percentage(self, detected_region, crop_scale, offset_x, offset_y, extracted_image=None):
        """화면 비율 계산 (헬퍼 함수)
        
        Args:
            detected_region: 얼굴 영역 (x, y, w, h) - 원본 이미지 기준
            crop_scale: 크롭 배율
            offset_x: X 오프셋
            offset_y: Y 오프셋
            extracted_image: 크롭된 이미지 (None이면 self.extracted_image 사용)
        """
        if detected_region is None or self.current_image is None:
            return 0.0
        
        if extracted_image is None:
            extracted_image = self.extracted_image
        
        if extracted_image is None:
            return 0.0
        
        x, y, w, h = detected_region
        crop_width, crop_height = extracted_image.size
        orig_width, orig_height = self.current_image.size
        
        # 크롭 시작 좌표 계산 (간단화)
        face_center_x = x + w // 2
        estimated_eye_y = y + h // 3
        crop_center_x = face_center_x + offset_x
        crop_center_y = estimated_eye_y + offset_y
        target_ratio = 96 / 120
        
        # 크롭 크기 계산
        if w / h > target_ratio:
            calc_crop_height = int(h * crop_scale)
            calc_crop_width = int(calc_crop_height * target_ratio)
        else:
            calc_crop_width = int(w * crop_scale)
            calc_crop_height = int(calc_crop_width / target_ratio)
        
        # 크롭 시작 좌표 (경계 조정 포함)
        x_start = max(0, min(crop_center_x - calc_crop_width // 2, orig_width - calc_crop_width))
        y_start = max(0, min(crop_center_y - calc_crop_height // 2, orig_height - calc_crop_height))
        
        # 크롭된 이미지 기준으로 얼굴 영역 변환 (교집합 계산)
        face_in_crop_x1 = max(0, x - x_start)
        face_in_crop_y1 = max(0, y - y_start)
        face_in_crop_x2 = min(crop_width, x + w - x_start)
        face_in_crop_y2 = min(crop_height, y + h - y_start)
        
        # 크롭된 이미지 내에서 얼굴 영역 면적
        if face_in_crop_x2 > face_in_crop_x1 and face_in_crop_y2 > face_in_crop_y1:
            face_area = (face_in_crop_x2 - face_in_crop_x1) * (face_in_crop_y2 - face_in_crop_y1)
            crop_area = crop_width * crop_height
            return (face_area / crop_area) * 100 if crop_area > 0 else 0.0
        
        return 0.0
    
    def extract_face(self):
        """얼굴 추출"""
        if self.current_image is None:
            return
        
        try:
            # 현재 설정값 가져오기
            crop_scale = self.crop_scale.get()
            offset_x = self.center_offset_x.get()
            offset_y = self.center_offset_y.get()
            
            # 수동 영역 사용 여부 확인
            manual_region = None
            if self.use_manual_region.get():
                try:
                    x = int(self.manual_x.get())
                    y = int(self.manual_y.get())
                    w = int(self.manual_w.get())
                    h = int(self.manual_h.get())
                    if w > 0 and h > 0:
                        manual_region = (x, y, w, h)
                    else:
                        raise ValueError("너비와 높이는 0보다 커야 합니다.")
                except (ValueError, tk.TclError):
                    self.status_label.config(text="경고: 수동 영역 좌표가 유효하지 않습니다.", fg="orange")
                    return
            
            # MediaPipe를 사용하는 경우 랜드마크 감지
            if self.use_mediapipe.get():
                try:
                    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, is_available
                    if is_available():
                        landmarks, detected = detect_face_landmarks(self.current_image.copy())
                        if detected and landmarks:
                            self.detected_landmarks = landmarks
                            self.detected_key_landmarks = get_key_landmarks(landmarks)
                        else:
                            self.detected_landmarks = None
                            self.detected_key_landmarks = None
                    else:
                        self.detected_landmarks = None
                        self.detected_key_landmarks = None
                except Exception as e:
                    _get_logger().warning(f"랜드마크 감지 실패: {e}")
                    self.detected_landmarks = None
                    self.detected_key_landmarks = None
            else:
                self.detected_landmarks = None
                self.detected_key_landmarks = None
            
            # 얼굴 추출 (얼굴 영역 좌표도 함께 받기)
            result = kaodata_image.extract_face_region(
                self.current_image.copy(),
                crop_scale=crop_scale,
                center_offset_x=offset_x,
                center_offset_y=offset_y,
                manual_region=manual_region,
                return_face_region=True,
                use_mediapipe=self.use_mediapipe.get()
            )
            
            # 결과가 튜플인 경우 (이미지, 얼굴영역)
            if isinstance(result, tuple):
                self.extracted_image, detected_region = result
                # 감지된 영역이 있으면 저장 (수동 영역 사용 시에도 저장)
                if detected_region is not None:
                    x, y, w, h = detected_region
                    
                    # 화면 비율 계산 (헬퍼 함수 사용) - 크롭된 이미지 전달
                    face_percentage = self._calculate_face_percentage(detected_region, crop_scale, offset_x, offset_y, self.extracted_image)
                    
                    # 크롭 시작 좌표 캐시 (성능 최적화)
                    if self.detected_face_region:
                        x, y, w, h = self.detected_face_region
                        orig_width, orig_height = self.current_image.size
                        extracted_width, extracted_height = self.extracted_image.size
                        
                        # 크롭 시작 좌표 계산 (MediaPipe 사용 시와 동일한 로직)
                        if self.use_mediapipe.get() and self.detected_key_landmarks:
                            # MediaPipe 사용 시: 감지된 얼굴 영역의 중심점 사용
                            detected_face_center_x = x + w // 2
                            detected_face_center_y = y + h // 2
                            crop_center_x = detected_face_center_x + offset_x
                            crop_center_y = detected_face_center_y + offset_y
                        else:
                            # OpenCV 사용 시: 얼굴 중심점과 추정 눈높이 사용
                            face_center_x = x + w // 2
                            estimated_eye_y = y + h // 3
                            crop_center_x = face_center_x + offset_x
                            crop_center_y = estimated_eye_y + offset_y
                        
                        target_ratio = 96 / 120
                        if w / h > target_ratio:
                            calc_crop_height = int(h * crop_scale)
                            calc_crop_width = int(calc_crop_height * target_ratio)
                        else:
                            calc_crop_width = int(w * crop_scale)
                            calc_crop_height = int(calc_crop_width / target_ratio)
                        
                        x_start = max(0, min(crop_center_x - calc_crop_width // 2, orig_width - calc_crop_width))
                        y_start = max(0, min(crop_center_y - calc_crop_height // 2, orig_height - calc_crop_height))
                        self.crop_start_coords = (x_start, y_start)
                    else:
                        self.crop_start_coords = None
                    
                    # 수동 영역을 사용하지 않은 경우에만 감지된 영역 저장 및 입력 필드에 채우기
                    if not self.use_manual_region.get():
                        self.detected_face_region = detected_region
                        # 수동 영역 입력 필드에 자동으로 채우기
                        self.manual_x.set(x)
                        self.manual_y.set(y)
                        self.manual_w.set(w)
                        self.manual_h.set(h)
                        # 감지된 위치와 사이즈는 UI에 이미 표시되므로 상태 라벨에는 표시하지 않음
                        # status_text = f"얼굴 추출 완료 | 감지된 영역: 위치=({x}, {y}), 크기={w}x{h} | 화면 비율: {face_percentage:.1f}%"
                        # self.status_label.config(text=status_text, fg="green")
                        # 화면 비율 UI 업데이트
                        if hasattr(self, 'face_percentage_label'):
                            self.face_percentage_label.config(text=f"{face_percentage:.1f}%")
                    else:
                        # 수동 영역 사용 시에도 detected_region을 저장 (테두리 표시용)
                        self.detected_face_region = detected_region
                        # 수동 영역 사용 시 - 정보는 UI에 이미 표시되므로 상태 라벨에는 표시하지 않음
                        # status_text = f"얼굴 추출 완료 | 수동 영역: 위치=({x}, {y}), 크기={w}x{h} | 화면 비율: {face_percentage:.1f}%"
                        # self.status_label.config(text=status_text, fg="green")
                        # 화면 비율 UI 업데이트 (강제 업데이트)
                        if hasattr(self, 'face_percentage_label'):
                            self.face_percentage_label.config(text=f"{face_percentage:.1f}%")
                            # UI 강제 업데이트
                            self.face_percentage_label.update_idletasks()
                            # 창 강제 업데이트
                            self.update_idletasks()
                else:
                    # detected_region이 None인 경우 화면 비율 0%로 표시
                    if hasattr(self, 'face_percentage_label'):
                        self.face_percentage_label.config(text="0.0%")
                    # 완료 메시지는 UI에 이미 표시되므로 상태 라벨에는 표시하지 않음
                    # self.status_label.config(text="얼굴 추출 완료", fg="green")
            else:
                # 결과가 이미지만인 경우 (이전 버전 호환)
                self.extracted_image = result
                self.detected_face_region = None
                # 완료 메시지는 UI에 이미 표시되므로 상태 라벨에는 표시하지 않음
                # self.status_label.config(text="얼굴 추출 완료", fg="green")
            
            self.face_detected = True
            
            # 캐시 무효화 (extracted_image가 변경되었으므로)
            self._adjusted_image_cache = None
            self._palette_image_cache = None
            
            # 미리보기 업데이트
            self.show_extracted_original()
            self.show_extracted_adjusted()
            self.show_original_preview()
            # 팔레트 적용 버전 계산 및 표시
            self.update_palette_preview()
            # 크롭 영역 테두리 업데이트
            self.draw_crop_region_on_original()
            
        except ValueError as e:
            # 얼굴을 찾을 수 없는 경우 - 수동 영역 모드로 자동 전환
            self.face_detected = False
            self.extracted_image = None
            
            # 원본 이미지가 있으면 중앙 영역을 기본값으로 설정
            if self.current_image is not None:
                img_width, img_height = self.current_image.size
                
                # 96x120 비율로 중앙 영역 계산
                target_ratio = 96 / 120  # 0.8
                
                if img_width / img_height > target_ratio:
                    # 이미지가 더 넓음 -> 높이를 기준으로
                    crop_height = int(img_height * 0.6)  # 이미지 높이의 60%
                    crop_width = int(crop_height * target_ratio)
                else:
                    # 이미지가 더 높음 -> 너비를 기준으로
                    crop_width = int(img_width * 0.6)  # 이미지 너비의 60%
                    crop_height = int(crop_width / target_ratio)
                
                # 중앙 좌표 계산
                x = (img_width - crop_width) // 2
                y = (img_height - crop_height) // 2
                
                # 수동 영역 입력 필드에 값 설정
                self.manual_x.set(x)
                self.manual_y.set(y)
                self.manual_w.set(crop_width)
                self.manual_h.set(crop_height)
                
                # 수동 영역 사용 체크박스 활성화
                self.use_manual_region.set(True)
                self.on_manual_region_toggle()
                
                # 수동 영역으로 다시 추출 시도
                try:
                    manual_region = (x, y, crop_width, crop_height)
                    crop_scale = self.crop_scale.get()
                    offset_x = self.center_offset_x.get()
                    offset_y = self.center_offset_y.get()
                    
                    result = kaodata_image.extract_face_region(
                        self.current_image.copy(),
                        crop_scale=crop_scale,
                        center_offset_x=offset_x,
                        center_offset_y=offset_y,
                        manual_region=manual_region,
                        return_face_region=True,
                        use_mediapipe=self.use_mediapipe.get()
                    )
                    
                    if isinstance(result, tuple):
                        self.extracted_image, _ = result
                    else:
                        self.extracted_image = result
                    
                    self.face_detected = True
                    self.show_extracted_original()
                    self.show_extracted_adjusted()
                    self.update_palette_preview()
                    
                    self.status_label.config(
                        text=f"얼굴 인식 실패 - 수동 영역 모드로 전환됨 (위치: {x}, {y}, 크기: {crop_width}x{crop_height})",
                        fg="orange"
                    )
                except Exception as extract_error:
                    self.status_label.config(text=f"경고: {str(e)} (수동 영역 추출도 실패: {extract_error})", fg="orange")
                    # 미리보기 초기화
                    if self.image_created_extracted_original:
                        self.canvas_extracted_original.delete(self.image_created_extracted_original)
                        self.image_created_extracted_original = None
                    if self.image_created_extracted_adjusted:
                        self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
                        self.image_created_extracted_adjusted = None
            else:
                self.status_label.config(text=f"경고: {str(e)}", fg="orange")
                messagebox.showwarning("얼굴 인식 실패", str(e))
                # 미리보기 초기화
                if self.image_created_extracted:
                    self.canvas_extracted.delete(self.image_created_extracted)
                    self.image_created_extracted = None
                # 격자선도 삭제
                for line_id in self.grid_lines_extracted:
                    try:
                        self.canvas_extracted.delete(line_id)
                    except:
                        pass
                self.grid_lines_extracted.clear()
        except Exception as e:
            self.face_detected = False
            self.extracted_image = None
            _get_logger().error(f"얼굴 추출 실패: {e}", exc_info=True)
            self.status_label.config(text=f"에러: {e}", fg="red")
            messagebox.showerror("에러", f"얼굴 추출 실패:\n{e}")
            # 미리보기 초기화
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
                self.image_created_extracted_original = None
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
                self.image_created_extracted_adjusted = None
    def on_close(self):
        """창 닫기"""
        self.destroy()

def show_face_extract_panel(parent=None):
    """얼굴 추출 패널 표시"""
    panel = FaceExtractPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel

