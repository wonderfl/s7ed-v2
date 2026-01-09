"""
얼굴 추출 전용 패널 - 얼굴 인식을 사용하여 이미지에서 얼굴을 자동으로 추출하고 저장
"""
import os
import glob
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import utils.image_adjustments as image_adjustments
import gui.frame_basic as _basic
import utils.config as config

class FaceExtractPanel(tk.Toplevel):
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
        
        self.label_original = tk.Label(left_frame, text="원본 이미지", font=("", 9))
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
            self.label_original.config(text=f"원본 이미지 ({filename})")
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
                    print(f"[얼굴추출] 자동 감지 실패: {e}")
        
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
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기 (얼굴 추출 패널 폴더가 있으면 사용, 없으면 png_dir 사용)
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            png_dir = self.face_extract_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        
        if not os.path.exists(png_dir):
            self.file_listbox.insert(0, f"디렉토리를 찾을 수 없습니다: {png_dir}")
            return
        
        # 지원하는 이미지 파일 확장자
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.tiff', '*.tif', '*.webp']
        
        # 모든 이미지 파일 목록 가져오기
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(png_dir, ext)))
            image_files.extend(glob.glob(os.path.join(png_dir, ext.upper())))
        
        # 중복 제거 (Windows에서 대소문자 구분 안 함으로 인한 중복 방지)
        # 정규화된 경로를 사용하여 중복 제거
        image_files = list(set(os.path.normpath(f) for f in image_files))
        image_files.sort()
        
        if not image_files:
            self.file_listbox.insert(0, "이미지 파일이 없습니다")
            return
        
        # 파일명만 리스트박스에 추가
        for file_path in image_files:
            filename = os.path.basename(file_path)
            self.file_listbox.insert(tk.END, filename)
        
        # 첫 번째 파일 자동 선택
        if len(image_files) > 0:
            self.file_listbox.selection_set(0)
            self.file_listbox.see(0)
            self.on_file_select()
    
    def on_listbox_key(self):
        """리스트박스 키보드 이벤트"""
        selection = self.file_listbox.curselection()
        if selection:
            self.on_file_select()
    
    def on_listbox_select(self):
        """리스트박스 선택 변경 이벤트 (자동 로드)"""
        selection = self.file_listbox.curselection()
        if selection:
            self.on_file_select()
    
    def on_file_select(self):
        """리스트박스에서 파일 선택"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        filename = self.file_listbox.get(index)
        
        # 파일 경로 구성 (얼굴 추출 패널 폴더가 있으면 사용, 없으면 png_dir 사용)
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            png_dir = self.face_extract_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        file_path = os.path.join(png_dir, filename)
        
        if os.path.exists(file_path):
            self.load_image(file_path)
    
    def browse_file(self):
        """파일 선택 대화상자"""
        # 저장된 이미지 디렉토리 경로 가져오기 (얼굴 추출 패널 폴더가 있으면 사용)
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            initial_dir = self.face_extract_dir
        else:
            initial_dir = kaodata_image.get_png_dir()
            if not os.path.exists(initial_dir):
                initial_dir = None
        
        file_path = filedialog.askopenfilename(
            title="이미지 파일 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("JPEG 파일", "*.jpg *.jpeg"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_path:
            # 선택한 파일의 디렉토리 경로 저장 (얼굴 추출 패널 폴더에 저장, png_dir은 변경하지 않음)
            import globals as gl
            import utils.config as config
            source_dir = os.path.dirname(file_path)
            if not os.path.isabs(source_dir):
                source_dir = os.path.abspath(source_dir)
            # 얼굴 추출 패널 폴더 업데이트 (불러오기와 저장 모두 이 폴더 사용)
            self.face_extract_dir = source_dir
            gl._face_extract_dir = source_dir
            # 설정 파일에 저장
            config.save_config()
            
            # 파일 목록 새로고침
            self.refresh_file_list()
            
            # 선택한 파일을 리스트박스에서 찾아서 선택
            filename = os.path.basename(file_path)
            for i in range(self.file_listbox.size()):
                if self.file_listbox.get(i) == filename:
                    self.file_listbox.selection_clear(0, tk.END)
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
            
            self.load_image(file_path)
    
    def _get_or_select_extract_folder(self):
        """얼굴 추출 이미지 저장 폴더 가져오기 (없으면 선택)"""
        import globals as gl
        import utils.config as config
        
        # 이미 설정된 폴더가 있으면 반환
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            return self.face_extract_dir
        
        # 폴더 선택 대화상자
        initial_dir = self.face_extract_dir if self.face_extract_dir else None
        if initial_dir and not os.path.exists(initial_dir):
            initial_dir = None
        
        folder_path = filedialog.askdirectory(
            title="얼굴 추출 이미지 저장 폴더 선택",
            initialdir=initial_dir
        )
        
        if folder_path:
            # 절대 경로로 변환
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            # 저장
            self.face_extract_dir = folder_path
            gl._face_extract_dir = folder_path
            config.save_config()
            
            return folder_path
        
        return None
    
    def _load_image_params(self, image_path):
        """이미지별 파라미터를 불러와서 적용"""
        if not image_path:
            # 파라미터 파일 상태 업데이트
            if hasattr(self, 'params_status_label'):
                self.params_status_label.config(text="", fg="gray")
            return
        
        # 파라미터 파일 존재 여부 확인
        config_path = f"{image_path}.s7ed.json"
        params_exists = os.path.exists(config_path)
        
        # 파라미터 파일 상태 표시
        if hasattr(self, 'params_status_label'):
            if params_exists:
                self.params_status_label.config(text="[파라미터 있음]", fg="green")
            else:
                self.params_status_label.config(text="[파라미터 없음]", fg="gray")
        
        params = config.load_face_extract_params(image_path)
        if not params:
            return
        
        try:
            # 팔레트 설정
            if 'palette_method' in params:
                self.palette_method.set(params['palette_method'])
            if 'use_palette' in params:
                self.use_palette.set(params['use_palette'])
            
            # 위치/배율 설정
            if 'crop_scale' in params:
                self.crop_scale.set(params['crop_scale'])
            if 'center_offset_x' in params:
                self.center_offset_x.set(params['center_offset_x'])
            if 'center_offset_y' in params:
                self.center_offset_y.set(params['center_offset_y'])
            
            # 이미지 조정 설정
            if 'brightness' in params:
                self.brightness.set(params['brightness'])
            if 'contrast' in params:
                self.contrast.set(params['contrast'])
            if 'saturation' in params:
                self.saturation.set(params['saturation'])
            if 'color_temp' in params:
                self.color_temp.set(params['color_temp'])
            if 'hue' in params:
                self.hue.set(params['hue'])
            if 'sharpness' in params:
                self.sharpness.set(params['sharpness'])
            if 'exposure' in params:
                self.exposure.set(params['exposure'])
            if 'equalize' in params:
                self.equalize.set(params['equalize'])
            if 'gamma' in params:
                self.gamma.set(params['gamma'])
            if 'vibrance' in params:
                self.vibrance.set(params['vibrance'])
            if 'clarity' in params:
                self.clarity.set(params['clarity'])
            if 'dehaze' in params:
                self.dehaze.set(params['dehaze'])
            if 'tint' in params:
                self.tint.set(params['tint'])
            if 'noise_reduction' in params:
                self.noise_reduction.set(params['noise_reduction'])
            if 'vignette' in params:
                self.vignette.set(params['vignette'])
            
            # 수동 영역 설정
            if 'use_manual_region' in params:
                self.use_manual_region.set(params['use_manual_region'])
            if 'manual_x' in params:
                self.manual_x.set(params['manual_x'])
            if 'manual_y' in params:
                self.manual_y.set(params['manual_y'])
            if 'manual_w' in params:
                self.manual_w.set(params['manual_w'])
            if 'manual_h' in params:
                self.manual_h.set(params['manual_h'])
            
            # 실제 사용된 얼굴 영역 (수동이든 자동이든)
            if all(key in params for key in ['face_region_x', 'face_region_y', 'face_region_w', 'face_region_h']):
                if params['face_region_x'] is not None and params['face_region_y'] is not None and \
                   params['face_region_w'] is not None and params['face_region_h'] is not None:
                    self.detected_face_region = (
                        params['face_region_x'],
                        params['face_region_y'],
                        params['face_region_w'],
                        params['face_region_h']
                    )
            
            # 수동 영역 설정 UI 업데이트 (체크박스 상태 및 입력 필드 활성화/비활성화)
            # extract_face는 load_image에서 호출되므로 여기서는 UI만 업데이트
            if 'use_manual_region' in params:
                # 체크박스는 변수 설정만으로 자동 반영됨
                # 입력 필드 활성화/비활성화는 on_manual_region_toggle에서 처리되지만,
                # 이미지가 로드되기 전이므로 여기서는 불필요 (load_image에서 extract_face 호출 후 처리됨)
                pass
            
            # UI 업데이트 콜백 호출
            # 이미지 조정 슬라이더 라벨 업데이트
            if hasattr(self, '_label_mapping'):
                for key, (var, label, formatter) in self._label_mapping.items():
                    if key in params:
                        label.config(text=formatter(var.get()))
            
            # 위치/배율 설정 UI 업데이트 (라벨만, extract_face는 load_image에서 호출)
            if 'crop_scale' in params or 'center_offset_x' in params or 'center_offset_y' in params:
                if hasattr(self, 'scale_label'):
                    scale_value = self.crop_scale.get()
                    self.scale_label.config(text=f"{int(scale_value * 100)}%")
                if hasattr(self, 'offset_x_label'):
                    offset_x = self.center_offset_x.get()
                    self.offset_x_label.config(text=str(offset_x))
                if hasattr(self, 'offset_y_label'):
                    offset_y = self.center_offset_y.get()
                    self.offset_y_label.config(text=str(offset_y))
            
            # 팔레트 설정 UI는 변수 설정만으로 자동 반영됨 (체크박스, 콤보박스)
            # 팔레트 미리보기는 extract_face 후에 update_palette_preview에서 처리됨
            
        except Exception as e:
            print(f"[얼굴추출] 파라미터 로드 실패: {e}")
    
    def _save_image_params(self, image_path):
        """현재 파라미터를 이미지별 설정 파일로 저장"""
        if not image_path:
            return
        
        try:
            # numpy 타입을 기본 Python 타입으로 변환하는 헬퍼 함수
            def to_python_type(value):
                """numpy 타입을 기본 Python 타입으로 변환"""
                import numpy as np
                if isinstance(value, (np.integer, np.int32, np.int64)):
                    return int(value)
                elif isinstance(value, (np.floating, np.float32, np.float64)):
                    return float(value)
                elif isinstance(value, np.ndarray):
                    return value.tolist()
                else:
                    return value
            
            params = {
                # 팔레트 설정
                'palette_method': str(self.palette_method.get()),
                'use_palette': bool(self.use_palette.get()),
                
                # 위치/배율 설정
                'crop_scale': float(self.crop_scale.get()),
                'center_offset_x': int(self.center_offset_x.get()),
                'center_offset_y': int(self.center_offset_y.get()),
                
                # 이미지 조정 설정
                'brightness': float(self.brightness.get()),
                'contrast': float(self.contrast.get()),
                'saturation': float(self.saturation.get()),
                'color_temp': float(self.color_temp.get()),
                'hue': float(self.hue.get()),
                'sharpness': float(self.sharpness.get()),
                'exposure': float(self.exposure.get()),
                'equalize': float(self.equalize.get()),
                'gamma': float(self.gamma.get()),
                'vibrance': float(self.vibrance.get()),
                'clarity': float(self.clarity.get()),
                'dehaze': float(self.dehaze.get()),
                'tint': float(self.tint.get()),
                'noise_reduction': float(self.noise_reduction.get()),
                'vignette': float(self.vignette.get()),
                
                # 수동 영역 사용 여부 및 좌표
                'use_manual_region': bool(self.use_manual_region.get()),
                'manual_x': int(self.manual_x.get()),
                'manual_y': int(self.manual_y.get()),
                'manual_w': int(self.manual_w.get()),
                'manual_h': int(self.manual_h.get()),
                
                # 실제 사용된 얼굴 영역 (수동이든 자동이든)
                'face_region_x': to_python_type(self.detected_face_region[0]) if self.detected_face_region else None,
                'face_region_y': to_python_type(self.detected_face_region[1]) if self.detected_face_region else None,
                'face_region_w': to_python_type(self.detected_face_region[2]) if self.detected_face_region else None,
                'face_region_h': to_python_type(self.detected_face_region[3]) if self.detected_face_region else None,
            }
            
            config.save_face_extract_params(image_path, params)
            
            # 파라미터 파일 상태 업데이트
            if hasattr(self, 'params_status_label'):
                self.params_status_label.config(text="[파라미터 있음]", fg="green")
        except Exception as e:
            print(f"[얼굴추출] 파라미터 저장 실패: {e}")
    
    def load_image(self, file_path):
        """이미지 로드 및 얼굴 추출"""
        try:
            # 이미지 읽기
            img = Image.open(file_path)
            
            # 이미지 저장
            self.current_image = img
            self.current_image_path = file_path
            
            # 파일명 표시 (리스트박스에서 선택된 항목 강조)
            filename = os.path.basename(file_path)
            for i in range(self.file_listbox.size()):
                if self.file_listbox.get(i) == filename:
                    self.file_listbox.selection_clear(0, tk.END)
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
            
            # 미리보기 타이틀 업데이트
            self._update_preview_titles(filename)
            
            # 이미지별 파라미터 불러오기
            self._load_image_params(file_path)
            
            # 얼굴 추출
            self.extract_face()
            
            # 수동 영역 설정이 로드된 경우 UI 업데이트 (입력 필드 활성화/비활성화)
            if hasattr(self, 'use_manual_region') and hasattr(self, 'manual_x_entry'):
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
            
            # 원본 이미지 미리보기 표시
            self.show_original_preview()
            
            # 파일 이름은 미리보기 타이틀에 이미 표시되므로 상태 라벨에는 표시하지 않음
            # self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
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
                    print(f"[얼굴추출] 랜드마크 감지 실패: {e}")
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
            print(f"[얼굴추출] 얼굴 추출 실패: {e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
            messagebox.showerror("에러", f"얼굴 추출 실패:\n{e}")
            # 미리보기 초기화
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
                self.image_created_extracted_original = None
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
                self.image_created_extracted_adjusted = None
    
    def show_extracted_original(self):
        """추출 원본 이미지 미리보기 표시 (조정 없음)"""
        if self.extracted_image is None:
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
                self.image_created_extracted_original = None
            # 얼굴 중심점 마커도 삭제
            if self.face_center_marker_extracted:
                try:
                    for marker_id in self.face_center_marker_extracted:
                        self.canvas_extracted_original.delete(marker_id)
                except:
                    pass
                self.face_center_marker_extracted = None
            return
        
        try:
            # 이미지 복사
            display_img = self.extracted_image.copy()
            
            # RGB 모드로 변환
            if display_img.mode != 'RGB':
                if display_img.mode == 'RGBA':
                    background = Image.new('RGB', display_img.size, (0, 0, 0))
                    background.paste(display_img, mask=display_img.split()[3])
                    display_img = background
                else:
                    display_img = display_img.convert('RGB')
            
            # 이미지 리사이즈 (288x360)
            preview_size = (288, 360)
            resized = display_img.resize(preview_size, Image.LANCZOS)
        
        # PhotoImage로 변환
            self.tk_image_extracted_original = ImageTk.PhotoImage(resized)
        
        # Canvas에 표시
            if self.image_created_extracted_original:
                self.canvas_extracted_original.delete(self.image_created_extracted_original)
            
            self.image_created_extracted_original = self.canvas_extracted_original.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_extracted_original
            )
            
            # 3x3 격자 그리기
            self.draw_grid_extracted()
            
            # 얼굴 중심점 표시
            self.draw_face_center_marker()
        except Exception as e:
            print(f"[얼굴추출] 추출 원본 이미지 미리보기 표시 실패: {e}")
    
    def show_extracted_adjusted(self):
        """추출 조정 이미지 미리보기 표시 (모든 조정 적용)"""
        if self.extracted_image is None:
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
                self.image_created_extracted_adjusted = None
            return
        
        try:
            # 이미지 조정 파이프라인 적용
            adjustments = self._get_adjustment_values()
            result = image_adjustments.process_image_pipeline(
                self.extracted_image.copy(),
                adjustments,
                resize_after=(288, 360)  # Sharpness 전에 리사이즈
            )
            
            # PhotoImage로 변환
            self.tk_image_extracted_adjusted = ImageTk.PhotoImage(result)
            
            # Canvas에 표시
            if self.image_created_extracted_adjusted:
                self.canvas_extracted_adjusted.delete(self.image_created_extracted_adjusted)
            
            self.image_created_extracted_adjusted = self.canvas_extracted_adjusted.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_extracted_adjusted
            )
        except Exception as e:
            print(f"[얼굴추출] 추출 조정 이미지 미리보기 표시 실패: {e}")
    
    def draw_grid_extracted(self):
        """추출 원본 이미지에 3x3 격자 그리기"""
        # 기존 격자선 삭제
        for line_id in self.grid_lines_extracted:
            try:
                self.canvas_extracted_original.delete(line_id)
            except:
                pass
        self.grid_lines_extracted.clear()
        
        if self.image_created_extracted_original is None or self.tk_image_extracted_original is None:
            return
        
        # 실제 이미지 크기 가져오기 (288x360)
        img_width = 288
        img_height = 360
        
        # 이미지 중심 위치
        center_x = 144  # 288 / 2
        center_y = 180  # 360 / 2
        
        # 이미지 시작 위치 (좌상단)
        start_x = center_x - img_width // 2
        start_y = center_y - img_height // 2
        
        # 격자선 색상
        grid_color = "white"
        grid_width = 1
        
        # 수직선 2개 (이미지 너비를 3등분)
        for i in range(1, 3):
            x = start_x + (img_width * i // 3)
            line_id = self.canvas_extracted_original.create_line(
                x, start_y,
                x, start_y + img_height,
                fill=grid_color,
                width=grid_width,
                tags="grid"
            )
            self.grid_lines_extracted.append(line_id)
        
        # 수평선 2개 (이미지 높이를 3등분)
        for i in range(1, 3):
            y = start_y + (img_height * i // 3)
            line_id = self.canvas_extracted_original.create_line(
                start_x, y,
                start_x + img_width, y,
                fill=grid_color,
                width=grid_width,
                tags="grid"
            )
            self.grid_lines_extracted.append(line_id)
    
    def draw_face_center_marker(self):
        """추출 원본 이미지에 얼굴 중심점 표시"""
        # 기존 마커 삭제
        if self.face_center_marker_extracted:
            try:
                for marker_id in self.face_center_marker_extracted:
                    self.canvas_extracted_original.delete(marker_id)
            except:
                pass
            self.face_center_marker_extracted = None
        
        if self.extracted_image is None or self.image_created_extracted_original is None:
            return
        
        try:
            # 얼굴 중심점 계산
            face_center_x = None
            face_center_y = None
            
            # MediaPipe 랜드마크가 있으면 사용
            if self.detected_key_landmarks and self.detected_key_landmarks.get('face_center'):
                # 원본 이미지의 얼굴 중심점
                orig_face_center = self.detected_key_landmarks['face_center']
                orig_face_center_x, orig_face_center_y = orig_face_center
                
                # 원본 이미지 크기
                orig_width, orig_height = self.current_image.size
                
                # 추출된 이미지 크기 (96x120)
                extracted_width, extracted_height = self.extracted_image.size
                
                # 크롭 시작 좌표 계산 (extract_face_region 로직과 동일하게)
                crop_scale = self.crop_scale.get()
                offset_x = self.center_offset_x.get()
                offset_y = self.center_offset_y.get()
                
                if self.detected_face_region:
                    x, y, w, h = self.detected_face_region
                    detected_face_center_x = x + w // 2
                    detected_face_center_y = y + h // 2
                    
                    crop_center_x = detected_face_center_x + offset_x
                    crop_center_y = detected_face_center_y + offset_y
                    
                    target_ratio = 96 / 120
                    if w / h > target_ratio:
                        crop_height = int(h * crop_scale)
                        crop_width = int(crop_height * target_ratio)
                    else:
                        crop_width = int(w * crop_scale)
                        crop_height = int(crop_width / target_ratio)
                    
                    x_start = max(0, min(crop_center_x - crop_width // 2, orig_width - crop_width))
                    y_start = max(0, min(crop_center_y - crop_height // 2, orig_height - crop_height))
                    
                    # 원본 이미지의 얼굴 중심점을 추출된 이미지 좌표로 변환
                    face_center_x = orig_face_center_x - x_start
                    face_center_y = orig_face_center_y - y_start
                    
                    # 추출된 이미지 범위 내에 있는지 확인
                    if 0 <= face_center_x < extracted_width and 0 <= face_center_y < extracted_height:
                        # 미리보기 좌표로 변환 (96x120 -> 288x360)
                        scale_x = 288 / extracted_width
                        scale_y = 360 / extracted_height
                        
                        preview_x = face_center_x * scale_x
                        preview_y = face_center_y * scale_y
                        
                        # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
                        canvas_center_x = 144  # 288 / 2
                        canvas_center_y = 180  # 360 / 2
                        
                        marker_x = canvas_center_x - 288 // 2 + preview_x
                        marker_y = canvas_center_y - 360 // 2 + preview_y
                        
                        # 십자가 모양으로 표시 (노란색)
                        cross_size = 10
                        # 수평선
                        line1 = self.canvas_extracted_original.create_line(
                            marker_x - cross_size, marker_y,
                            marker_x + cross_size, marker_y,
                            fill="yellow", width=2, tags="face_center"
                        )
                        # 수직선
                        line2 = self.canvas_extracted_original.create_line(
                            marker_x, marker_y - cross_size,
                            marker_x, marker_y + cross_size,
                            fill="yellow", width=2, tags="face_center"
                        )
                        # # 중심점
                        # point = self.canvas_extracted_original.create_oval(
                        #     marker_x - 3, marker_y - 3,
                        #     marker_x + 3, marker_y + 3,
                        #     fill="yellow", outline="yellow", tags="face_center"
                        # )
                        
                        # 마커 ID 저장 (나중에 삭제하기 위해)
                        # self.face_center_marker_extracted = (line1, line2, point)
            
        except Exception as e:
            print(f"[얼굴추출] 얼굴 중심점 표시 실패: {e}")
    
    def update_palette_preview(self):
        """팔레트 적용 이미지 계산 및 미리보기 업데이트"""
        if self.extracted_image is None:
            # 팔레트 미리보기 초기화
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
            self.palette_applied_image = None
            return
        
        try:
            # 팔레트 적용 여부 확인
            if not self.use_palette.get():
                # 팔레트 미적용 시 추출된 이미지 그대로 사용
                self.palette_applied_image = None
                # 미리보기 초기화
                if self.image_created_palette:
                    self.canvas_palette.delete(self.image_created_palette)
                    self.image_created_palette = None
                return
            
            # 변환 방법 가져오기
            method = self.palette_method.get()
            dither = (method == 'dither')
            
            # 1단계: 이미지 전처리 (팔레트 적용 전)
            adjustments = self._get_adjustment_values()
            processed_img = image_adjustments.process_image_pipeline(
                self.extracted_image.copy(),
                adjustments,
                resize_before=(kaodata_image.FACE_WIDTH, kaodata_image.FACE_HEIGHT)  # Equalize 후 리사이즈
            )
            
            # 2단계: 마지막에 팔레트 적용
            self.palette_applied_image = kaodata_image.convert_to_palette_colors(
                processed_img,
                palette=kaodata_image.FACE_PALETTE,
                method=method,
                dither=dither
            )
            
            # 미리보기 표시
            self.show_palette_preview()
            
        except Exception as e:
            print(f"[얼굴추출] 팔레트 적용 실패: {e}")
            self.palette_applied_image = None
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
    
    def show_palette_preview(self):
        """팔레트 적용 이미지 미리보기 표시 (96x120 크기로 확대)"""
        if self.palette_applied_image is None:
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
            return
        
        try:
            # 팔레트 모드 이미지를 RGB로 변환하여 표시
            # (PIL의 PhotoImage는 P 모드를 직접 지원하지 않을 수 있음)
            if self.palette_applied_image.mode == 'P':
                # 팔레트 모드를 RGB로 변환 (팔레트 색상이 제대로 적용되도록)
                preview_img = self.palette_applied_image.convert('RGB')
            else:
                preview_img = self.palette_applied_image
            
            # 이미지가 96x120인지 확인하고, 미리보기 크기로 확대
            # 팔레트 적용 이미지는 이미 96x120으로 리사이즈되어 있음
            # 미리보기 크기로 확대 표시
            # 이미지가 96x120인지 확인하고, 미리보기 크기로 확대 (288x360)
            preview_size = (288, 360)
            resized = preview_img.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_palette = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
            
            self.image_created_palette = self.canvas_palette.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_palette
            )
        except Exception as e:
            print(f"[얼굴추출] 팔레트 미리보기 표시 실패: {e}")
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
                self.image_created_palette = None
    
    def show_original_preview(self):
        """원본 이미지를 96x120 비율로 최대 크롭해서 미리보기 표시 (0,0 기준)"""
        if self.current_image is None:
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            if self.crop_rect_original:
                self.canvas_original.delete(self.crop_rect_original)
                self.crop_rect_original = None
            if self.actual_crop_rect_original:
                self.canvas_original.delete(self.actual_crop_rect_original)
                self.actual_crop_rect_original = None
            return
        
        try:
            # 96x120 비율 (0.8)
            target_ratio = 96 / 120  # 0.8
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            img_ratio = img_width / img_height
            
            # 96x120 비율에 맞춰서 최대 크롭 (0,0 기준)
            if img_ratio > target_ratio:
                # 이미지가 더 넓음 -> 높이를 기준으로 크롭
                crop_height = img_height
                crop_width = int(crop_height * target_ratio)
            else:
                # 이미지가 더 높음 -> 너비를 기준으로 크롭
                crop_width = img_width
                crop_height = int(crop_width / target_ratio)
            
            # 0,0 기준으로 크롭
            x_start = 0
            y_start = 0
            x_end = min(crop_width, img_width)
            y_end = min(crop_height, img_height)
            
            # 크롭
            cropped = self.current_image.crop((x_start, y_start, x_end, y_end))
            
            # 랜드마크 표시 옵션이 켜져 있고 랜드마크가 있으면 그리기
            if self.show_landmarks.get() and self.detected_landmarks is not None:
                try:
                    from utils.face_landmarks import draw_landmarks
                    # 랜드마크 좌표를 크롭된 영역에 맞게 조정
                    adjusted_landmarks = []
                    for x, y in self.detected_landmarks:
                        # 크롭 영역 기준으로 좌표 조정
                        adjusted_x = x - x_start
                        adjusted_y = y - y_start
                        adjusted_landmarks.append((adjusted_x, adjusted_y))
                    
                    # 주요 랜드마크도 조정
                    adjusted_key_landmarks = None
                    if self.detected_key_landmarks:
                        adjusted_key_landmarks = {}
                        for key, value in self.detected_key_landmarks.items():
                            if value:
                                x, y = value
                                adjusted_key_landmarks[key] = (x - x_start, y - y_start)
                            else:
                                adjusted_key_landmarks[key] = None
                    
                    # 랜드마크 그리기
                    cropped = draw_landmarks(
                        cropped, 
                        adjusted_landmarks, 
                        adjusted_key_landmarks,
                        show_all_points=False
                    )
                except Exception as e:
                    print(f"[얼굴추출] 랜드마크 그리기 실패: {e}")
            
            # 이미지 리사이즈 (미리보기용, 288x360)
            preview_size = (288, 360)
            resized = cropped.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_original = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
            
            self.image_created_original = self.canvas_original.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_original
            )
            
            # 크롭 영역 테두리 그리기
            self.draw_crop_region_on_original()
            
        except Exception as e:
            print(f"[얼굴추출] 원본 이미지 표시 실패: {e}")
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            if self.crop_rect_original:
                self.canvas_original.delete(self.crop_rect_original)
                self.crop_rect_original = None
    
    def draw_crop_region_on_original(self):
        """원본 이미지 미리보기에 크롭 영역을 테두리로 표시"""
        # 기존 테두리 제거
        if self.crop_rect_original:
            self.canvas_original.delete(self.crop_rect_original)
            self.crop_rect_original = None
        
        if self.current_image is None:
            return
        
        # 크롭 영역 좌표 가져오기
        crop_x, crop_y, crop_w, crop_h = None, None, None, None
        
        if self.use_manual_region.get():
            # 수동 영역 사용
            try:
                crop_x = int(self.manual_x.get())
                crop_y = int(self.manual_y.get())
                crop_w = int(self.manual_w.get())
                crop_h = int(self.manual_h.get())
            except (ValueError, tk.TclError):
                return
        elif self.detected_face_region is not None:
            # 감지된 영역 사용
            crop_x, crop_y, crop_w, crop_h = self.detected_face_region
        
        if crop_x is None or crop_y is None or crop_w is None or crop_h is None:
            return
        
        # 원본 이미지 크기
        img_width, img_height = self.current_image.size
        
        # 96x120 비율로 크롭된 미리보기 영역 계산
        target_ratio = 96 / 120  # 0.8
        if img_width / img_height > target_ratio:
            preview_crop_height = img_height
            preview_crop_width = int(preview_crop_height * target_ratio)
        else:
            preview_crop_width = img_width
            preview_crop_height = int(preview_crop_width / target_ratio)
        
        # 크롭 영역이 미리보기 영역 내에 있는지 확인
        if crop_x < 0 or crop_y < 0 or crop_x + crop_w > preview_crop_width or crop_y + crop_h > preview_crop_height:
            # 크롭 영역이 미리보기 영역을 벗어남
            return
        
        # 미리보기 크기 (288x360)
        preview_width = 288
        preview_height = 360
        
        # 크롭 영역 좌표를 미리보기 좌표로 변환
        scale_x = preview_width / preview_crop_width
        scale_y = preview_height / preview_crop_height
        
        rect_x1 = crop_x * scale_x
        rect_y1 = crop_y * scale_y
        rect_x2 = (crop_x + crop_w) * scale_x
        rect_y2 = (crop_y + crop_h) * scale_y
        
        # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
        canvas_center_x = 144  # 288 / 2
        canvas_center_y = 180  # 360 / 2
        
        rect_x1_canvas = canvas_center_x - preview_width // 2 + rect_x1
        rect_y1_canvas = canvas_center_y - preview_height // 2 + rect_y1
        rect_x2_canvas = canvas_center_x - preview_width // 2 + rect_x2
        rect_y2_canvas = canvas_center_y - preview_height // 2 + rect_y2
        
        # 얼굴/수동 영역 테두리 그리기 (빨간색, 두께 2)
        # 수동 영역 모드일 때는 태그를 추가하여 드래그 가능하게 함
        tags = ("draggable",) if self.use_manual_region.get() else ()
        self.crop_rect_original = self.canvas_original.create_rectangle(
            rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas,
            outline="red", width=2, tags=tags
        )
        
        # 실제 크롭 영역 계산 및 표시
        self.draw_actual_crop_region(crop_x, crop_y, crop_w, crop_h, preview_crop_width, preview_crop_height)
    
    def draw_actual_crop_region(self, face_x, face_y, face_w, face_h, preview_crop_width, preview_crop_height):
        """실제 크롭 영역을 계산하고 테두리로 표시"""
        # 기존 테두리 제거
        if self.actual_crop_rect_original:
            self.canvas_original.delete(self.actual_crop_rect_original)
            self.actual_crop_rect_original = None
        
        if self.current_image is None:
            return
        
        try:
            # 현재 설정값 가져오기
            crop_scale = self.crop_scale.get()
            offset_x = self.center_offset_x.get()
            offset_y = self.center_offset_y.get()
            
            # 목표 비율 (96:120 = 0.8)
            target_ratio = 96 / 120  # 0.8
            
            # 얼굴 영역을 중심으로 96:120 비율로 크롭할 크기 계산
            if face_w / face_h > target_ratio:
                # 얼굴이 더 넓음 -> 높이를 기준으로 크롭
                crop_height = int(face_h * crop_scale)
                crop_width = int(crop_height * target_ratio)
            else:
                # 얼굴이 더 높음 -> 너비를 기준으로 크롭
                crop_width = int(face_w * crop_scale)
                crop_height = int(crop_width / target_ratio)
            
            # 96:120 비율 보장
            actual_ratio = crop_width / crop_height if crop_height > 0 else target_ratio
            if abs(actual_ratio - target_ratio) > 0.01:
                if face_w / face_h > target_ratio:
                    crop_width = int(crop_height * target_ratio)
                else:
                    crop_height = int(crop_width / target_ratio)
            
            # 감지된 얼굴 영역의 중심점 계산
            # extract_face_region과 동일한 로직 사용
            detected_face_center_x = face_x + face_w // 2
            detected_face_center_y = face_y + face_h // 2
            
            # 크롭 중심점 계산 (오프셋 적용)
            crop_center_x = detected_face_center_x + offset_x
            crop_center_y = detected_face_center_y + offset_y
            
            # 크롭 영역 좌표 계산
            actual_crop_x = crop_center_x - crop_width // 2
            actual_crop_y = crop_center_y - crop_height // 2
            actual_crop_x2 = actual_crop_x + crop_width
            actual_crop_y2 = actual_crop_y + crop_height
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            
            # 경계 조정
            if actual_crop_x < 0:
                actual_crop_x = 0
            if actual_crop_y < 0:
                actual_crop_y = 0
            if actual_crop_x2 > img_width:
                actual_crop_x2 = img_width
            if actual_crop_y2 > img_height:
                actual_crop_y2 = img_height
            
            # 크롭 영역이 미리보기 영역 내에 있는지 확인
            if actual_crop_x < 0 or actual_crop_y < 0 or actual_crop_x2 > preview_crop_width or actual_crop_y2 > preview_crop_height:
                # 크롭 영역이 미리보기 영역을 벗어남
                return
            
            # 미리보기 크기 (288x360)
            preview_width = 288
            preview_height = 360
            
            # 크롭 영역 좌표를 미리보기 좌표로 변환
            scale_x = preview_width / preview_crop_width
            scale_y = preview_height / preview_crop_height
            
            rect_x1 = actual_crop_x * scale_x
            rect_y1 = actual_crop_y * scale_y
            rect_x2 = actual_crop_x2 * scale_x
            rect_y2 = actual_crop_y2 * scale_y
            
            # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
            canvas_center_x = 144  # 288 / 2
            canvas_center_y = 180  # 360 / 2
            
            rect_x1_canvas = canvas_center_x - preview_width // 2 + rect_x1
            rect_y1_canvas = canvas_center_y - preview_height // 2 + rect_y1
            rect_x2_canvas = canvas_center_x - preview_width // 2 + rect_x2
            rect_y2_canvas = canvas_center_y - preview_height // 2 + rect_y2
            
            # 실제 크롭 영역 테두리 그리기 (파란색, 두께 2)
            self.actual_crop_rect_original = self.canvas_original.create_rectangle(
                rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas,
                outline="white", width=1
            )
        except Exception as e:
            print(f"[얼굴추출] 실제 크롭 영역 표시 실패: {e}")
    
    def save_image(self):
        """이미지를 Kaodata.s7에 저장 (나중에 사용 예정)"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "얼굴을 추출할 수 없습니다.")
            return
        
        if self.face_entry is None:
            messagebox.showwarning("경고", "저장 위치 기능이 비활성화되어 있습니다.")
            return
        
        try:
            # 얼굴 번호 확인
            faceno_str = self.face_entry.get().strip()
            if not faceno_str:
                messagebox.showwarning("경고", "얼굴 번호를 입력하세요.")
                return
            
            faceno = int(faceno_str)
            
            if faceno < 0 or faceno >= 648:
                messagebox.showerror("에러", "얼굴 번호는 0~647 사이여야 합니다.")
                return
            
            # 확인 대화상자
            filename = os.path.basename(self.current_image_path) if self.current_image_path else "이미지"
            result = messagebox.askyesno(
                "확인",
                f"추출된 얼굴 이미지를 얼굴 번호 {faceno}에 저장하시겠습니까?\n\n기존 이미지는 덮어씌워집니다."
            )
            
            if not result:
                return
            
            # 저장
            kaodata_image.save_face_image(faceno, self.extracted_image)
            
            # 완료 메시지는 messagebox로 표시되므로 상태 라벨에는 표시하지 않음
            # self.status_label.config(
            #     text=f"저장 완료: 얼굴 번호 {faceno}에 저장되었습니다.",
            #     fg="green"
            # )
            
            messagebox.showinfo("완료", f"얼굴 번호 {faceno}에 저장되었습니다.")
            
        except ValueError:
            messagebox.showerror("에러", "얼굴 번호는 숫자여야 합니다.")
        except Exception as e:
            messagebox.showerror("에러", f"저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def save_extracted_png(self):
        """추출된 이미지(팔레트 적용 전)를 PNG 파일로 저장"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            png_filename = f"{base_name}_extracted.png"
            
            # 저장 폴더 경로 결정 (설정된 폴더가 있으면 사용, 없으면 선택하거나 원본 이미지와 같은 디렉토리의 faces 폴더)
            faces_dir = self._get_or_select_extract_folder()
            if not faces_dir:
                # 사용자가 취소한 경우, 원본 이미지와 같은 디렉토리의 faces 폴더 사용
                original_dir = os.path.dirname(self.current_image_path)
                faces_dir = os.path.join(original_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (추출된 원본 이미지)
            self.extracted_image.save(file_path, "PNG")
            
            # 완료 메시지는 상태 라벨에 표시하지 않음 (에러/경고만 표시)
            # self.status_label.config(
            #     text=f"원본 저장 완료: {png_filename} (faces 폴더)",
            #     fg="green"
            # )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def save_png(self):
        """팔레트 적용된 이미지를 PNG 파일로 저장 (faces 폴더에 원본 파일명으로)"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        # 팔레트 적용 여부 확인
        if not self.use_palette.get() or self.palette_applied_image is None:
            messagebox.showwarning("경고", "팔레트가 적용되지 않았습니다. '원본 저장' 버튼을 사용하세요.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            # 앞부분의 영문자와 '_' 제거 (예: ABC_something -> something)
            base_name = re.sub(r'^[A-Za-z]+_', '', base_name)
            png_filename = f"{base_name}_s7.png"
            
            # 저장 폴더 경로 결정 (설정된 폴더가 있으면 사용, 없으면 선택하거나 원본 이미지와 같은 디렉토리의 faces 폴더)
            extract_dir = self._get_or_select_extract_folder()
            if not extract_dir:
                # 사용자가 취소한 경우, 원본 이미지와 같은 디렉토리의 faces 폴더 사용
                extract_dir = os.path.dirname(self.current_image_path)
                
            faces_dir = os.path.join(extract_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (팔레트 적용된 이미지)
            self.palette_applied_image.save(file_path, "PNG")
            
            # 이미지별 파라미터 저장
            self._save_image_params(self.current_image_path)
            
            # 완료 메시지는 상태 라벨에 표시하지 않음 (에러/경고만 표시)
            # self.status_label.config(
            #     text=f"PNG 저장 완료: {png_filename} (팔레트 적용, faces 폴더)",
            #     fg="green"
            # )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def on_canvas_click(self, event):
        """Canvas 클릭 이벤트 (드래그 시작)"""
        if not self.use_manual_region.get():
            return
        
        if self.crop_rect_original is None:
            return
        
        # 클릭한 위치가 테두리 사각형 내부인지 확인
        x, y = event.x, event.y
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) >= 4:
            rect_x1, rect_y1, rect_x2, rect_y2 = coords[0], coords[1], coords[2], coords[3]
            if rect_x1 <= x <= rect_x2 and rect_y1 <= y <= rect_y2:
                self.is_dragging = True
                self.drag_start_x = x
                self.drag_start_y = y
                
                # 현재 수동 영역 좌표 저장
                try:
                    self.drag_original_x = int(self.manual_x.get())
                    self.drag_original_y = int(self.manual_y.get())
                except (ValueError, tk.TclError):
                    self.is_dragging = False
    
    def on_canvas_drag(self, event):
        """Canvas 드래그 이벤트"""
        if not self.is_dragging or not self.use_manual_region.get():
            return
        
        if self.crop_rect_original is None or self.current_image is None:
            return
        
        # 드래그 거리 계산
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # 테두리 사각형 이동
        self.canvas_original.move(self.crop_rect_original, dx, dy)
        
        # 실제 크롭 영역 테두리도 함께 이동
        if self.actual_crop_rect_original:
            self.canvas_original.move(self.actual_crop_rect_original, dx, dy)
        
        # 다음 드래그를 위해 시작 위치 업데이트
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # 드래그 중에도 수동 영역 좌표 업데이트 및 재계산 (성능을 위해 제한)
        # Canvas 좌표를 원본 이미지 좌표로 변환
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) >= 4:
            rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas = coords[0], coords[1], coords[2], coords[3]
            
            # 원본 이미지 크기
            img_width, img_height = self.current_image.size
            
            # 96x120 비율로 크롭된 미리보기 영역 계산
            target_ratio = 96 / 120  # 0.8
            if img_width / img_height > target_ratio:
                preview_crop_height = img_height
                preview_crop_width = int(preview_crop_height * target_ratio)
            else:
                preview_crop_width = img_width
                preview_crop_height = int(preview_crop_width / target_ratio)
            
            # 미리보기 크기 (288x360)
            preview_width = 288
            preview_height = 360
            
            # Canvas 좌표를 미리보기 좌표로 변환
            canvas_center_x = 144  # 288 / 2
            canvas_center_y = 180  # 360 / 2
            
            rect_x1_preview = rect_x1_canvas - (canvas_center_x - preview_width // 2)
            rect_y1_preview = rect_y1_canvas - (canvas_center_y - preview_height // 2)
            
            # 미리보기 좌표를 원본 이미지 좌표로 변환
            scale_x = preview_width / preview_crop_width
            scale_y = preview_height / preview_crop_height
            
            new_x = int(rect_x1_preview / scale_x)
            new_y = int(rect_y1_preview / scale_y)
            
            # 수동 영역 크기 가져오기
            try:
                crop_w = int(self.manual_w.get())
                crop_h = int(self.manual_h.get())
            except (ValueError, tk.TclError):
                return
            
            # 경계 내로 제한
            new_x = max(0, min(new_x, preview_crop_width - crop_w))
            new_y = max(0, min(new_y, preview_crop_height - crop_h))
            
            # 수동 영역 입력 필드 업데이트
            self.manual_x.set(new_x)
            self.manual_y.set(new_y)
            
            # 드래그 중에는 재계산하지 않고, 드래그 종료 시에만 재계산
            # (성능 문제 방지)
    
    def on_canvas_release(self, event):
        """Canvas 드래그 종료 이벤트"""
        if not self.is_dragging:
            return
        
        self.is_dragging = False
        
        if self.crop_rect_original is None or self.current_image is None:
            return
        
        # Canvas 좌표를 원본 이미지 좌표로 변환
        coords = self.canvas_original.coords(self.crop_rect_original)
        if len(coords) < 4:
            return
        
        rect_x1_canvas, rect_y1_canvas, rect_x2_canvas, rect_y2_canvas = coords[0], coords[1], coords[2], coords[3]
        
        # 원본 이미지 크기
        img_width, img_height = self.current_image.size
        
        # 96x120 비율로 크롭된 미리보기 영역 계산
        target_ratio = 96 / 120  # 0.8
        if img_width / img_height > target_ratio:
            preview_crop_height = img_height
            preview_crop_width = int(preview_crop_height * target_ratio)
        else:
            preview_crop_width = img_width
            preview_crop_height = int(preview_crop_width / target_ratio)
        
        # 미리보기 크기 (288x360)
        preview_width = 288
        preview_height = 360
        
        # Canvas 좌표를 미리보기 좌표로 변환
        canvas_center_x = 144  # 288 / 2
        canvas_center_y = 180  # 360 / 2
        
        rect_x1_preview = rect_x1_canvas - (canvas_center_x - preview_width // 2)
        rect_y1_preview = rect_y1_canvas - (canvas_center_y - preview_height // 2)
        
        # 미리보기 좌표를 원본 이미지 좌표로 변환
        scale_x = preview_width / preview_crop_width
        scale_y = preview_height / preview_crop_height
        
        new_x = int(rect_x1_preview / scale_x)
        new_y = int(rect_y1_preview / scale_y)
        
        # 경계 체크
        try:
            crop_w = int(self.manual_w.get())
            crop_h = int(self.manual_h.get())
        except (ValueError, tk.TclError):
            return
        
        # 경계 내로 제한
        new_x = max(0, min(new_x, preview_crop_width - crop_w))
        new_y = max(0, min(new_y, preview_crop_height - crop_h))
        
        # 수동 영역 입력 필드 업데이트
        self.manual_x.set(new_x)
        self.manual_y.set(new_y)
        
        # 테두리 다시 그리기 (경계 조정 반영)
        self.draw_crop_region_on_original()
        
        # 자동으로 재추출 (화면 비율도 재계산됨)
        # 수동 영역 좌표가 업데이트된 후 extract_face() 호출
        if self.current_image is not None:
            # 수동 영역 변경을 강제로 반영하기 위해 extract_face() 직접 호출
            self.extract_face()
            
            # UI 강제 업데이트 (extract_face()에서 업데이트되지만 확실히 하기 위해)
            self.update_idletasks()
            
            # 화면 비율 UI 강제 업데이트 (extract_face()에서 업데이트되지만 확실히 하기 위해)
            # 크롭된 이미지가 업데이트된 후에 재계산
            if hasattr(self, 'face_percentage_label') and self.detected_face_region is not None and self.extracted_image is not None:
                crop_scale = self.crop_scale.get()
                offset_x = self.center_offset_x.get()
                offset_y = self.center_offset_y.get()
                face_percentage = self._calculate_face_percentage(self.detected_face_region, crop_scale, offset_x, offset_y, self.extracted_image)
                self.face_percentage_label.config(text=f"{face_percentage:.1f}%")
                self.face_percentage_label.update_idletasks()
    
    def on_close(self):
        """창 닫기"""
        self.destroy()

def show_face_extract_panel(parent=None):
    """얼굴 추출 패널 표시"""
    panel = FaceExtractPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel

