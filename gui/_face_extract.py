"""
얼굴 추출 전용 패널 - 얼굴 인식을 사용하여 이미지에서 얼굴을 자동으로 추출하고 저장
"""
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import gui.frame_basic as _basic

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
        
        # 설정값
        self.crop_scale = tk.DoubleVar(value=2.0)  # 기본값: 2.0 (200%)
        self.center_offset_x = tk.IntVar(value=0)
        self.center_offset_y = tk.IntVar(value=0)
        
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
        
        # 수동 영역 설정
        self.use_manual_region = tk.BooleanVar(value=False)
        self.manual_x = tk.IntVar(value=0)
        self.manual_y = tk.IntVar(value=0)
        self.manual_w = tk.IntVar(value=0)
        self.manual_h = tk.IntVar(value=0)
        
        # 미리보기 이미지
        self.tk_image_extracted = None
        self.tk_image_original = None
        self.tk_image_palette = None
        self.image_created_extracted = None
        self.image_created_original = None
        self.image_created_palette = None
        self.grid_lines_extracted = []  # 추출 이미지 격자선 ID 저장
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
        
        # 왼쪽: 파일 선택 프레임
        file_frame = tk.LabelFrame(top_frame, text="이미지 파일 선택", padx=5, pady=5)
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
        
        # 오른쪽: 설정 프레임
        settings_frame = tk.LabelFrame(top_frame, text="얼굴 영역 설정", padx=5, pady=5)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 크기 비율 설정
        scale_frame = tk.Frame(settings_frame)
        scale_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(scale_frame, text="크기 비율:").pack(side=tk.LEFT, padx=(0, 5))
        scale_scale = tk.Scale(
            scale_frame,
            from_=0.5,
            to=5.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.crop_scale,
            command=self.on_setting_change,
            length=200,
            showvalue=False
        )
        scale_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.scale_label = tk.Label(scale_frame, text="200%", width=8)
        self.scale_label.pack(side=tk.LEFT)
        
        # 중심점 오프셋 설정 (세로 배치)
        offset_frame = tk.Frame(settings_frame)
        offset_frame.pack(fill=tk.X, pady=(0, 5))
        
        # X 오프셋 (좌우)
        offset_x_frame = tk.Frame(offset_frame)
        offset_x_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(offset_x_frame, text="중심점 X (좌우):").pack(side=tk.LEFT, padx=(0, 5))
        offset_x_scale = tk.Scale(
            offset_x_frame,
            from_=-200,
            to=200,
            resolution=1,
            orient=tk.HORIZONTAL,
            variable=self.center_offset_x,
            command=self.on_setting_change,
            length=300,
            showvalue=False
        )
        offset_x_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        self.offset_x_label = tk.Label(offset_x_frame, text="0", width=6)
        self.offset_x_label.pack(side=tk.LEFT)
        
        # Y 오프셋 (상하)
        offset_y_frame = tk.Frame(offset_frame)
        offset_y_frame.pack(fill=tk.X)
        
        tk.Label(offset_y_frame, text="중심점 Y (상하):").pack(side=tk.LEFT, padx=(0, 5))
        offset_y_scale = tk.Scale(
            offset_y_frame,
            from_=-200,
            to=200,
            resolution=1,
            orient=tk.HORIZONTAL,
            variable=self.center_offset_y,
            command=self.on_setting_change,
            length=300,
            showvalue=False
        )
        offset_y_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        self.offset_y_label = tk.Label(offset_y_frame, text="0", width=6)
        self.offset_y_label.pack(side=tk.LEFT)

        scaled_length = 300
        label_width = 8
        
        # 밝기/대비 조정 프레임
        adjust_frame = tk.LabelFrame(settings_frame, text="이미지 조정", padx=5, pady=5)
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
        
        # 1줄: 밝기, 평탄화
        row1_frame = tk.Frame(adjust_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 밝기 조정
        brightness_frame = tk.Frame(row1_frame)
        brightness_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        tk.Label(brightness_frame, text="밝기:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        brightness_scale = tk.Scale(
            brightness_frame,
            from_=0.5,
            to=1.5,
            resolution=0.01,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.brightness,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        brightness_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.brightness_label = tk.Label(brightness_frame, text="100%", width=6)
        self.brightness_label.pack(side=tk.LEFT)
        
        # 평탄화 조정
        equalize_frame = tk.Frame(row1_frame)
        equalize_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(equalize_frame, text="평탄화:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        equalize_scale = tk.Scale(
            equalize_frame,
            from_=0.0,
            to=0.5,
            resolution=0.005,  # 1% 스텝
            orient=tk.HORIZONTAL,
            variable=self.equalize,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        equalize_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.equalize_label = tk.Label(equalize_frame, text="0%", width=6)
        self.equalize_label.pack(side=tk.LEFT)
        
        # 2줄: 대비, 선명도
        row2_frame = tk.Frame(adjust_frame)
        row2_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 대비 조정
        contrast_frame = tk.Frame(row2_frame)
        contrast_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        tk.Label(contrast_frame, text="대비:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        contrast_scale = tk.Scale(
            contrast_frame,
            from_=0.5,
            to=1.5,
            resolution=0.01,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.contrast,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        contrast_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.contrast_label = tk.Label(contrast_frame, text="100%", width=6)
        self.contrast_label.pack(side=tk.LEFT)
        
        # 선명도 조정
        sharpness_frame = tk.Frame(row2_frame)
        sharpness_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(sharpness_frame, text="선명도:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        sharpness_scale = tk.Scale(
            sharpness_frame,
            from_=0.0,
            to=3.0,
            resolution=0.01,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.sharpness,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        sharpness_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.sharpness_label = tk.Label(sharpness_frame, text="100%", width=6)
        self.sharpness_label.pack(side=tk.LEFT)
        
        # 3줄: 채도, 색온도
        row3_frame = tk.Frame(adjust_frame)
        row3_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 채도 조정
        saturation_frame = tk.Frame(row3_frame)
        saturation_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        tk.Label(saturation_frame, text="채도:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        saturation_scale = tk.Scale(
            saturation_frame,
            from_=0.5,
            to=1.5,
            resolution=0.01,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.saturation,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        saturation_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.saturation_label = tk.Label(saturation_frame, text="100%", width=6)
        self.saturation_label.pack(side=tk.LEFT)
        
        # 색온도 조정
        color_temp_frame = tk.Frame(row3_frame)
        color_temp_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(color_temp_frame, text="색온도:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        color_temp_scale = tk.Scale(
            color_temp_frame,
            from_=-300.0,
            to=300.0,
            resolution=1.0,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.color_temp,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        color_temp_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.color_temp_label = tk.Label(color_temp_frame, text="0", width=6)
        self.color_temp_label.pack(side=tk.LEFT)
        
        # 4줄: 색조, 노출
        row4_frame = tk.Frame(adjust_frame)
        row4_frame.pack(fill=tk.X)
        
        # 색조 조정
        hue_frame = tk.Frame(row4_frame)
        hue_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        tk.Label(hue_frame, text="색조:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        hue_scale = tk.Scale(
            hue_frame,
            from_=-60.0,
            to=60.0,
            resolution=1,  # 1도 스텝
            orient=tk.HORIZONTAL,
            variable=self.hue,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        hue_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.hue_label = tk.Label(hue_frame, text="0", width=6)
        self.hue_label.pack(side=tk.LEFT)
        
        # 노출 조정
        exposure_frame = tk.Frame(row4_frame)
        exposure_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(exposure_frame, text="노출:", width=label_width, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
        exposure_scale = tk.Scale(
            exposure_frame,
            from_=0.5,
            to=1.5,
            resolution=0.01,  # 2% 스텝
            orient=tk.HORIZONTAL,
            variable=self.exposure,
            command=self.on_adjust_change,
            length=scaled_length,
            showvalue=False
        )
        exposure_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.exposure_label = tk.Label(exposure_frame, text="100%", width=6)
        self.exposure_label.pack(side=tk.LEFT)
        
        # 팔레트 변환 설정 프레임
        palette_frame = tk.LabelFrame(settings_frame, text="팔레트 변환 설정", padx=5, pady=5)
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
        
        # 수동 영역 설정 프레임
        manual_frame = tk.LabelFrame(settings_frame, text="수동 영역 설정", padx=5, pady=5)
        manual_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 수동 영역 사용 체크박스
        manual_check = tk.Checkbutton(
            manual_frame,
            text="수동 영역 사용",
            variable=self.use_manual_region,
            command=self.on_manual_region_toggle
        )
        manual_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 영역 좌표 입력 필드
        coord_frame = tk.Frame(manual_frame)
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
        
        btn_apply_detected = tk.Button(coord_frame, text="감지된 값 적용", command=self.apply_detected_region, width=12)
        btn_apply_detected.pack(side=tk.LEFT, padx=(10, 0))
        
        # 이미지 미리보기 프레임 (2개 이미지 나란히 표시)
        preview_frame = tk.LabelFrame(main_frame, text="미리보기", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 좌측: 원본 이미지 (96x120 비율로 크롭)
        left_frame = tk.Frame(preview_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(left_frame, text="원본 이미지 (96x120 비율)", font=("", 9)).pack()
        self.canvas_original = tk.Canvas(
            left_frame, 
            width=_basic.BasicFrame.image_width *4, 
            height=_basic.BasicFrame.image_height*4,
            bg="gray"
        )
        self.canvas_original.pack(padx=5, pady=5)
        
        # 마우스 드래그 이벤트 바인딩 (수동 영역 모드일 때만)
        self.canvas_original.bind("<Button-1>", self.on_canvas_click)
        self.canvas_original.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # 중간: 추출된 얼굴 이미지
        middle_frame = tk.Frame(preview_frame)
        middle_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 추출된 얼굴 라벨과 버튼을 가로로 배치
        middle_top_frame = tk.Frame(middle_frame)
        middle_top_frame.pack(fill=tk.X)
        
        tk.Label(middle_top_frame, text="추출된 얼굴", font=("", 9)).pack(side=tk.LEFT)
        
        # 추출 이미지 저장 버튼 (라벨 옆)
        btn_save_extracted = tk.Button(middle_top_frame, text="원본 저장", command=self.save_extracted_png, width=12, bg="#4CAF50", fg="white")
        btn_save_extracted.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_extracted = tk.Canvas(
            middle_frame, 
            width=_basic.BasicFrame.image_width *4, 
            height=_basic.BasicFrame.image_height*4,
            bg="gray"
        )
        self.canvas_extracted.pack(padx=5, pady=5)
        
        # 우측: 팔레트 적용 버전
        right_frame = tk.Frame(preview_frame)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 팔레트 적용 라벨과 버튼을 가로로 배치
        right_top_frame = tk.Frame(right_frame)
        right_top_frame.pack(fill=tk.X)
        
        tk.Label(right_top_frame, text="팔레트 적용", font=("", 9)).pack(side=tk.LEFT)
        
        # PNG 저장 버튼 (라벨 옆)
        btn_save_png = tk.Button(right_top_frame, text="PNG 저장", command=self.save_png, width=12, bg="#2196F3", fg="white")
        btn_save_png.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_palette = tk.Canvas(
            right_frame, 
            width=_basic.BasicFrame.image_width *4, 
            height=_basic.BasicFrame.image_height*4,
            bg="gray"
        )
        self.canvas_palette.pack(padx=5, pady=5)
        
        # 얼굴 번호 입력 프레임 (나중에 사용 예정)
        # face_frame = tk.LabelFrame(main_frame, text="저장 위치", padx=5, pady=5)
        # face_frame.pack(fill=tk.X, pady=(0, 10))
        # 
        # tk.Label(face_frame, text="얼굴 번호:").pack(side=tk.LEFT, padx=(0, 5))
        # 
        # self.face_entry = tk.Entry(face_frame, width=10)
        # self.face_entry.pack(side=tk.LEFT, padx=(0, 5))
        # self.face_entry.insert(0, "0")
        # self.face_entry.bind("<Return>", lambda e: self.save_image())
        # 
        # tk.Label(face_frame, text="(0~647)", fg="gray").pack(side=tk.LEFT)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="준비됨", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 위젯 생성 완료 후 파일 목록 로드
        self.after(100, self.refresh_file_list)
    
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
                        return_face_region=True
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
                            self.show_extracted_preview()
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
            self.extract_face()
            # 크롭 영역 테두리 업데이트
            self.draw_crop_region_on_original()
    
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
        
        # 라벨 업데이트
        self.on_adjust_change()
        
        # 미리보기 업데이트
        if self.extracted_image is not None:
            self.show_extracted_preview()
            self.update_palette_preview()
    
    def on_adjust_change(self, value=None):
        """밝기/대비/색온도/채도 조정 시 호출"""
        # 라벨 업데이트
        brightness_value = self.brightness.get()
        self.brightness_label.config(text=f"{int(brightness_value * 100)}%")
        
        contrast_value = self.contrast.get()
        self.contrast_label.config(text=f"{int(contrast_value * 100)}%")
        
        color_temp_value = self.color_temp.get()
        self.color_temp_label.config(text=f"{int(color_temp_value)}")
        
        saturation_value = self.saturation.get()
        self.saturation_label.config(text=f"{int(saturation_value * 100)}%")
        
        hue_value = self.hue.get()
        self.hue_label.config(text=f"{int(hue_value)}")
        
        sharpness_value = self.sharpness.get()
        self.sharpness_label.config(text=f"{int(sharpness_value * 100)}%")
        
        exposure_value = self.exposure.get()
        self.exposure_label.config(text=f"{int(exposure_value * 100)}%")
        
        equalize_value = self.equalize.get()
        self.equalize_label.config(text=f"{int(equalize_value * 100)}%")
        
        # 이미지가 로드되어 있으면 미리보기 업데이트
        if self.extracted_image is not None:
            # 추출된 이미지 미리보기 업데이트
            self.show_extracted_preview()
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
        
        # 이미지 디렉토리 경로 가져오기
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
        
        # 파일 경로 구성
        png_dir = kaodata_image.get_png_dir()
        file_path = os.path.join(png_dir, filename)
        
        if os.path.exists(file_path):
            self.load_image(file_path)
    
    def browse_file(self):
        """파일 선택 대화상자"""
        # 저장된 이미지 디렉토리 경로 가져오기
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
            # 선택한 파일의 디렉토리 경로 저장
            png_dir = os.path.dirname(file_path)
            kaodata_image.set_png_dir(png_dir)
            # 설정 파일에 저장
            import utils.config as config
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
            
            # 얼굴 추출
            self.extract_face()
            
            # 원본 이미지 미리보기 표시
            self.show_original_preview()
            
            self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
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
            
            # 얼굴 추출 (얼굴 영역 좌표도 함께 받기)
            result = kaodata_image.extract_face_region(
                self.current_image.copy(),
                crop_scale=crop_scale,
                center_offset_x=offset_x,
                center_offset_y=offset_y,
                manual_region=manual_region,
                return_face_region=True
            )
            
            # 결과가 튜플인 경우 (이미지, 얼굴영역)
            if isinstance(result, tuple):
                self.extracted_image, detected_region = result
                # 감지된 영역이 있으면 저장 (수동 영역 사용 시에도 저장)
                if detected_region is not None:
                    x, y, w, h = detected_region
                    # 수동 영역을 사용하지 않은 경우에만 감지된 영역 저장 및 입력 필드에 채우기
                    if not self.use_manual_region.get():
                        self.detected_face_region = detected_region
                        # 수동 영역 입력 필드에 자동으로 채우기
                        self.manual_x.set(x)
                        self.manual_y.set(y)
                        self.manual_w.set(w)
                        self.manual_h.set(h)
                        # 감지된 위치와 사이즈 출력
                        status_text = f"얼굴 추출 완료 | 감지된 영역: 위치=({x}, {y}), 크기={w}x{h}"
                        self.status_label.config(text=status_text, fg="green")
                    else:
                        # 수동 영역 사용 시에도 detected_region을 저장 (테두리 표시용)
                        self.detected_face_region = detected_region
                        # 수동 영역 사용 시
                        status_text = f"얼굴 추출 완료 | 수동 영역: 위치=({x}, {y}), 크기={w}x{h}"
                        self.status_label.config(text=status_text, fg="green")
                else:
                    self.status_label.config(text="얼굴 추출 완료", fg="green")
            else:
                # 결과가 이미지만인 경우 (이전 버전 호환)
                self.extracted_image = result
                self.detected_face_region = None
                self.status_label.config(text="얼굴 추출 완료", fg="green")
            
            self.face_detected = True
            
            # 미리보기 업데이트
            self.show_extracted_preview()
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
                        return_face_region=True
                    )
                    
                    if isinstance(result, tuple):
                        self.extracted_image, _ = result
                    else:
                        self.extracted_image = result
                    
                    self.face_detected = True
                    self.show_extracted_preview()
                    self.update_palette_preview()
                    
                    self.status_label.config(
                        text=f"얼굴 인식 실패 - 수동 영역 모드로 전환됨 (위치: {x}, {y}, 크기: {crop_width}x{crop_height})",
                        fg="orange"
                    )
                except Exception as extract_error:
                    self.status_label.config(text=f"경고: {str(e)} (수동 영역 추출도 실패: {extract_error})", fg="orange")
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
    
    def show_extracted_preview(self):
        """추출된 얼굴 이미지 미리보기 표시 (밝기/대비 조정 적용)"""
        if self.extracted_image is None:
            return
        
        try:
            # 밝기/대비 조정 적용
            from PIL import ImageEnhance
            
            # 이미지 복사
            display_img = self.extracted_image.copy()
            
            # RGB 모드로 변환 (밝기/대비 조정을 위해)
            if display_img.mode != 'RGB':
                if display_img.mode == 'RGBA':
                    background = Image.new('RGB', display_img.size, (0, 0, 0))
                    background.paste(display_img, mask=display_img.split()[3])
                    display_img = background
                else:
                    display_img = display_img.convert('RGB')
            
            # 평탄화 (Histogram Equalization) - 강도 조절 가능
            equalize_value = self.equalize.get()
            if equalize_value > 0.0:
                try:
                    import cv2
                    import numpy as np
                    # 원본 이미지 저장
                    original_img = display_img.copy()
                    # PIL Image를 numpy array로 변환
                    img_array = np.array(display_img)
                    # RGB를 BGR로 변환 (OpenCV는 BGR 사용)
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                    # YUV 색공간으로 변환하여 밝기 채널만 평탄화
                    img_yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
                    img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
                    # 다시 BGR로 변환
                    img_bgr = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
                    # BGR을 RGB로 변환하여 PIL Image로 복원
                    img_array = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    equalized_img = Image.fromarray(img_array)
                    # 원본과 평탄화된 이미지를 강도에 따라 블렌딩
                    if equalize_value < 1.0:
                        # 블렌딩: (1 - equalize_value) * 원본 + equalize_value * 평탄화
                        display_img = Image.blend(original_img, equalized_img, equalize_value)
                    else:
                        display_img = equalized_img
                except ImportError:
                    # OpenCV가 없으면 PIL의 ImageOps.equalize 사용
                    try:
                        from PIL import ImageOps
                        original_img = display_img.copy()
                        equalized_img = ImageOps.equalize(display_img)
                        if equalize_value < 1.0:
                            display_img = Image.blend(original_img, equalized_img, equalize_value)
                        else:
                            display_img = equalized_img
                    except Exception as e:
                        print(f"[얼굴추출] 평탄화 실패: {e}")
                except Exception as e:
                    print(f"[얼굴추출] 평탄화 실패: {e}")
            
            # 밝기 조정
            brightness_value = self.brightness.get()
            if brightness_value != 1.0:
                enhancer = ImageEnhance.Brightness(display_img)
                display_img = enhancer.enhance(brightness_value)
            
            # 대비 조정
            contrast_value = self.contrast.get()
            if contrast_value != 1.0:
                enhancer = ImageEnhance.Contrast(display_img)
                display_img = enhancer.enhance(contrast_value)
            
            # 채도 조정
            saturation_value = self.saturation.get()
            if saturation_value != 1.0:
                enhancer = ImageEnhance.Color(display_img)
                display_img = enhancer.enhance(saturation_value)
            
            # 색조 조정
            hue_value = self.hue.get()
            if hue_value != 0.0:
                try:
                    import cv2
                    import numpy as np
                    # PIL Image를 numpy array로 변환
                    img_array = np.array(display_img, dtype=np.uint8)
                    # RGB를 HSV로 변환
                    img_hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
                    # Hue 채널 조정 (-180 ~ 180 범위를 0 ~ 180으로 변환하여 조정)
                    # HSV의 Hue는 0~180 범위이므로, -180~180 범위를 더해서 조정
                    img_hsv[:, :, 0] = (img_hsv[:, :, 0].astype(np.int16) + int(hue_value)) % 180
                    # 다시 RGB로 변환
                    img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
                    display_img = Image.fromarray(img_array)
                except ImportError:
                    print("[얼굴추출] OpenCV가 없어 색조 조정을 건너뜁니다.")
                except Exception as e:
                    print(f"[얼굴추출] 색조 조정 실패: {e}")
            
            # 색온도 조정
            color_temp_value = self.color_temp.get()
            if color_temp_value != 0.0:
                try:
                    import numpy as np
                    img_array = np.array(display_img, dtype=np.float32)
                    
                    # 색온도 조정 (따뜻하게=양수: 빨강/노랑 증가, 차갑게=음수: 파랑 증가)
                    # -100 ~ 100 범위를 -0.3 ~ 0.3으로 정규화
                    temp_factor = color_temp_value / 100.0 * 0.3
                    
                    if temp_factor > 0:
                        # 따뜻하게: 빨강, 초록 증가
                        img_array[:, :, 0] = np.clip(img_array[:, :, 0] + temp_factor * 50, 0, 255)  # R 증가
                        img_array[:, :, 1] = np.clip(img_array[:, :, 1] + temp_factor * 30, 0, 255)  # G 증가
                    else:
                        # 차갑게: 파랑 증가
                        img_array[:, :, 2] = np.clip(img_array[:, :, 2] - temp_factor * 50, 0, 255)  # B 증가
                    
                    display_img = Image.fromarray(img_array.astype(np.uint8))
                except ImportError:
                    print("[얼굴추출] numpy가 없어 색온도 조정을 건너뜁니다.")
            
            # 노출 조정
            exposure_value = self.exposure.get()
            if exposure_value != 1.0:
                try:
                    import numpy as np
                    img_array = np.array(display_img, dtype=np.float32)
                    
                    # 노출 조정: 지수 함수 사용 (exposure > 1.0: 밝게, < 1.0: 어둡게)
                    # 0.0 ~ 2.0 범위를 0.25 ~ 4.0 지수 범위로 변환
                    # exposure = 0.0 -> factor = 0.25 (매우 어둡게)
                    # exposure = 1.0 -> factor = 1.0 (원본)
                    # exposure = 2.0 -> factor = 4.0 (매우 밝게)
                    exposure_factor = 0.25 * (4.0 ** exposure_value)
                    
                    img_array = img_array * exposure_factor
                    img_array = np.clip(img_array, 0, 255)
                    
                    display_img = Image.fromarray(img_array.astype(np.uint8))
                except ImportError:
                    print("[얼굴추출] numpy가 없어 노출 조정을 건너뜁니다.")
            
            # 이미지 리사이즈
            preview_size = (_basic.BasicFrame.image_width *4, _basic.BasicFrame.image_height*4)
            resized = display_img.resize(preview_size, Image.LANCZOS)
            
            # 선명도 조정 (리사이즈 이후)
            sharpness_value = self.sharpness.get()
            if sharpness_value != 1.0:
                enhancer = ImageEnhance.Sharpness(resized)
                resized = enhancer.enhance(sharpness_value)
            
            # PhotoImage로 변환
            self.tk_image_extracted = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_extracted:
                self.canvas_extracted.delete(self.image_created_extracted)
            
            self.image_created_extracted = self.canvas_extracted.create_image(
                _basic.BasicFrame.image_width *2,
                _basic.BasicFrame.image_height *2,
                image=self.tk_image_extracted
            )
            
            # 3x3 격자 그리기
            self.draw_grid_extracted()
        except Exception as e:
            print(f"[얼굴추출] 추출 이미지 미리보기 표시 실패: {e}")
    
    def draw_grid_extracted(self):
        """추출 이미지에 3x3 격자 그리기"""
        # 기존 격자선 삭제
        for line_id in self.grid_lines_extracted:
            try:
                self.canvas_extracted.delete(line_id)
            except:
                pass
        self.grid_lines_extracted.clear()
        
        if self.image_created_extracted is None or self.tk_image_extracted is None:
            return
        
        # 실제 이미지 크기 가져오기
        try:
            # PhotoImage는 width와 height 속성을 가짐
            img_width = self.tk_image_extracted.width()
            img_height = self.tk_image_extracted.height()
        except AttributeError:
            # width() 메서드가 없는 경우 속성으로 접근
            try:
                img_width = self.tk_image_extracted.width
                img_height = self.tk_image_extracted.height
            except:
                # 폴백: 예상 크기 사용
                img_width = _basic.BasicFrame.image_width * 4
                img_height = _basic.BasicFrame.image_height * 4
        except:
            # 폴백: 예상 크기 사용
            img_width = _basic.BasicFrame.image_width * 4
            img_height = _basic.BasicFrame.image_height * 4
        
        # 이미지 중심 위치
        center_x = _basic.BasicFrame.image_width * 2
        center_y = _basic.BasicFrame.image_height * 2
        
        # 이미지 시작 위치 (좌상단)
        start_x = center_x - img_width // 2
        start_y = center_y - img_height // 2
        
        # 격자선 색상 (빨간색, 두께 3으로 더 잘 보이게)
        grid_color = "white"
        grid_width = 1
        
        # 수직선 2개 (이미지 너비를 3등분)
        for i in range(1, 3):
            x = start_x + (img_width * i // 3)
            line_id = self.canvas_extracted.create_line(
                x, start_y,
                x, start_y + img_height,
                fill=grid_color,
                width=grid_width,
                tags="grid"  # 태그 추가로 나중에 쉽게 삭제 가능
            )
            self.grid_lines_extracted.append(line_id)
        
        # 수평선 2개 (이미지 높이를 3등분)
        for i in range(1, 3):
            y = start_y + (img_height * i // 3)
            line_id = self.canvas_extracted.create_line(
                start_x, y,
                start_x + img_width, y,
                fill=grid_color,
                width=grid_width,
                tags="grid"  # 태그 추가로 나중에 쉽게 삭제 가능
            )
            self.grid_lines_extracted.append(line_id)
    
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
            # 추출된 이미지 복사
            processed_img = self.extracted_image.copy()
            
            # RGB 모드로 확실히 변환 (전처리 단계)
            if processed_img.mode != 'RGB':
                if processed_img.mode == 'RGBA':
                    # 알파 채널이 있는 경우 배경을 검은색으로 설정
                    background = Image.new('RGB', processed_img.size, (0, 0, 0))
                    background.paste(processed_img, mask=processed_img.split()[3])
                    processed_img = background
                else:
                    processed_img = processed_img.convert('RGB')
            
            # 평탄화 (Histogram Equalization) - 강도 조절 가능
            equalize_value = self.equalize.get()
            if equalize_value > 0.0:
                try:
                    import cv2
                    import numpy as np
                    # 원본 이미지 저장
                    original_img = processed_img.copy()
                    # PIL Image를 numpy array로 변환
                    img_array = np.array(processed_img)
                    # RGB를 BGR로 변환 (OpenCV는 BGR 사용)
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                    # YUV 색공간으로 변환하여 밝기 채널만 평탄화
                    img_yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
                    img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
                    # 다시 BGR로 변환
                    img_bgr = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
                    # BGR을 RGB로 변환하여 PIL Image로 복원
                    img_array = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    equalized_img = Image.fromarray(img_array)
                    # 원본과 평탄화된 이미지를 강도에 따라 블렌딩
                    if equalize_value < 1.0:
                        # 블렌딩: (1 - equalize_value) * 원본 + equalize_value * 평탄화
                        processed_img = Image.blend(original_img, equalized_img, equalize_value)
                    else:
                        processed_img = equalized_img
                except ImportError:
                    # OpenCV가 없으면 PIL의 ImageOps.equalize 사용
                    try:
                        from PIL import ImageOps
                        original_img = processed_img.copy()
                        equalized_img = ImageOps.equalize(processed_img)
                        if equalize_value < 1.0:
                            processed_img = Image.blend(original_img, equalized_img, equalize_value)
                        else:
                            processed_img = equalized_img
                    except Exception as e:
                        print(f"[얼굴추출] 평탄화 실패: {e}")
                except Exception as e:
                    print(f"[얼굴추출] 평탄화 실패: {e}")
            
            # 밝기/대비 조정 적용
            from PIL import ImageEnhance
            
            brightness_value = self.brightness.get()
            if brightness_value != 1.0:
                enhancer = ImageEnhance.Brightness(processed_img)
                processed_img = enhancer.enhance(brightness_value)
            
            contrast_value = self.contrast.get()
            if contrast_value != 1.0:
                enhancer = ImageEnhance.Contrast(processed_img)
                processed_img = enhancer.enhance(contrast_value)
            
            # 채도 조정
            saturation_value = self.saturation.get()
            if saturation_value != 1.0:
                enhancer = ImageEnhance.Color(processed_img)
                processed_img = enhancer.enhance(saturation_value)
            
            # 색조 조정
            hue_value = self.hue.get()
            if hue_value != 0.0:
                try:
                    import cv2
                    import numpy as np
                    # PIL Image를 numpy array로 변환
                    img_array = np.array(processed_img, dtype=np.uint8)
                    # RGB를 HSV로 변환
                    img_hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
                    # Hue 채널 조정 (-180 ~ 180 범위를 0 ~ 180으로 변환하여 조정)
                    # HSV의 Hue는 0~180 범위이므로, -180~180 범위를 더해서 조정
                    img_hsv[:, :, 0] = (img_hsv[:, :, 0].astype(np.int16) + int(hue_value)) % 180
                    # 다시 RGB로 변환
                    img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
                    processed_img = Image.fromarray(img_array)
                except ImportError:
                    print("[얼굴추출] OpenCV가 없어 색조 조정을 건너뜁니다.")
                except Exception as e:
                    print(f"[얼굴추출] 색조 조정 실패: {e}")
            
            # 색온도 조정
            color_temp_value = self.color_temp.get()
            if color_temp_value != 0.0:
                try:
                    import numpy as np
                    img_array = np.array(processed_img, dtype=np.float32)
                    
                    # 색온도 조정 (따뜻하게=양수: 빨강/노랑 증가, 차갑게=음수: 파랑 증가)
                    # -100 ~ 100 범위를 -0.3 ~ 0.3으로 정규화
                    temp_factor = color_temp_value / 100.0 * 0.3
                    
                    if temp_factor > 0:
                        # 따뜻하게: 빨강, 초록 증가
                        img_array[:, :, 0] = np.clip(img_array[:, :, 0] + temp_factor * 50, 0, 255)  # R 증가
                        img_array[:, :, 1] = np.clip(img_array[:, :, 1] + temp_factor * 30, 0, 255)  # G 증가
                    else:
                        # 차갑게: 파랑 증가
                        img_array[:, :, 2] = np.clip(img_array[:, :, 2] - temp_factor * 50, 0, 255)  # B 증가
                    
                    processed_img = Image.fromarray(img_array.astype(np.uint8))
                except ImportError:
                    print("[얼굴추출] numpy가 없어 색온도 조정을 건너뜁니다.")
            
            # 노출 조정
            exposure_value = self.exposure.get()
            if exposure_value != 1.0:
                try:
                    import numpy as np
                    img_array = np.array(processed_img, dtype=np.float32)
                    
                    # 노출 조정: 지수 함수 사용 (exposure > 1.0: 밝게, < 1.0: 어둡게)
                    # 0.0 ~ 2.0 범위를 0.25 ~ 4.0 지수 범위로 변환
                    # exposure = 0.0 -> factor = 0.25 (매우 어둡게)
                    # exposure = 1.0 -> factor = 1.0 (원본)
                    # exposure = 2.0 -> factor = 4.0 (매우 밝게)
                    exposure_factor = 0.25 * (4.0 ** exposure_value)
                    
                    img_array = img_array * exposure_factor
                    img_array = np.clip(img_array, 0, 255)
                    
                    processed_img = Image.fromarray(img_array.astype(np.uint8))
                except ImportError:
                    print("[얼굴추출] numpy가 없어 노출 조정을 건너뜁니다.")
            
            # 리사이즈 (96x120)
            processed_img = processed_img.resize(
                (kaodata_image.FACE_WIDTH, kaodata_image.FACE_HEIGHT),
                Image.LANCZOS
            )
            
            # 선명도 조정 (리사이즈 이후)
            sharpness_value = self.sharpness.get()
            if sharpness_value != 1.0:
                enhancer = ImageEnhance.Sharpness(processed_img)
                processed_img = enhancer.enhance(sharpness_value)
            
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
            preview_size = (_basic.BasicFrame.image_width *4, _basic.BasicFrame.image_height*4)
            # LANCZOS로 확대하여 더 부드럽게 표시
            resized = preview_img.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_palette = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_palette:
                self.canvas_palette.delete(self.image_created_palette)
            
            self.image_created_palette = self.canvas_palette.create_image(
                _basic.BasicFrame.image_width *2,
                _basic.BasicFrame.image_height *2,
                image=self.tk_image_palette
            )
        except Exception as e:
            print(f"[얼굴추출] 팔레트 미리보기 표시 실패: {e}")
            import traceback
            traceback.print_exc()
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
            
            # 이미지 리사이즈 (미리보기용)
            preview_size = (_basic.BasicFrame.image_width *4, _basic.BasicFrame.image_height*4)
            resized = cropped.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_original = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
            
            self.image_created_original = self.canvas_original.create_image(
                _basic.BasicFrame.image_width *2,
                _basic.BasicFrame.image_height *2,
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
        
        # 미리보기 크기
        preview_width = _basic.BasicFrame.image_width * 4
        preview_height = _basic.BasicFrame.image_height * 4
        
        # 크롭 영역 좌표를 미리보기 좌표로 변환
        scale_x = preview_width / preview_crop_width
        scale_y = preview_height / preview_crop_height
        
        rect_x1 = crop_x * scale_x
        rect_y1 = crop_y * scale_y
        rect_x2 = (crop_x + crop_w) * scale_x
        rect_y2 = (crop_y + crop_h) * scale_y
        
        # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
        canvas_center_x = _basic.BasicFrame.image_width * 2
        canvas_center_y = _basic.BasicFrame.image_height * 2
        
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
            
            # 얼굴 중심점 계산
            # X축은 얼굴 중심, Y축은 눈높이 추정 (얼굴 상단 1/3 지점)
            # extract_face_region과 동일한 로직 사용
            face_center_x = face_x + face_w // 2
            # 눈은 일반적으로 얼굴 상단 1/3 지점에 위치
            estimated_eye_y = face_y + face_h // 3
            
            # 크롭 중심점 계산 (오프셋 적용)
            crop_center_x = face_center_x + offset_x
            crop_center_y = estimated_eye_y + offset_y
            
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
            
            # 미리보기 크기
            preview_width = _basic.BasicFrame.image_width * 4
            preview_height = _basic.BasicFrame.image_height * 4
            
            # 크롭 영역 좌표를 미리보기 좌표로 변환
            scale_x = preview_width / preview_crop_width
            scale_y = preview_height / preview_crop_height
            
            rect_x1 = actual_crop_x * scale_x
            rect_y1 = actual_crop_y * scale_y
            rect_x2 = actual_crop_x2 * scale_x
            rect_y2 = actual_crop_y2 * scale_y
            
            # Canvas 좌표로 변환 (이미지가 중앙에 배치됨)
            canvas_center_x = _basic.BasicFrame.image_width * 2
            canvas_center_y = _basic.BasicFrame.image_height * 2
            
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
            
            self.status_label.config(
                text=f"저장 완료: 얼굴 번호 {faceno}에 저장되었습니다.",
                fg="green"
            )
            
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
            
            # faces 폴더 경로 (원본 이미지와 같은 디렉토리의 faces 폴더)
            original_dir = os.path.dirname(self.current_image_path)
            faces_dir = os.path.join(original_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (추출된 원본 이미지)
            self.extracted_image.save(file_path, "PNG")
            
            self.status_label.config(
                text=f"원본 저장 완료: {png_filename} (faces 폴더)",
                fg="green"
            )
        
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
            png_filename = f"{base_name}_palette.png"
            
            # faces 폴더 경로 (원본 이미지와 같은 디렉토리의 faces 폴더)
            original_dir = os.path.dirname(self.current_image_path)
            faces_dir = os.path.join(original_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (팔레트 적용된 이미지)
            self.palette_applied_image.save(file_path, "PNG")
            
            self.status_label.config(
                text=f"PNG 저장 완료: {png_filename} (팔레트 적용, faces 폴더)",
                fg="green"
            )
        
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
        
        # 미리보기 크기
        preview_width = _basic.BasicFrame.image_width * 4
        preview_height = _basic.BasicFrame.image_height * 4
        
        # Canvas 좌표를 미리보기 좌표로 변환
        canvas_center_x = _basic.BasicFrame.image_width * 2
        canvas_center_y = _basic.BasicFrame.image_height * 2
        
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
        
        # 자동으로 재추출
        if self.current_image is not None:
            self.extract_face()
    
    def on_close(self):
        """창 닫기"""
        self.destroy()

def show_face_extract_panel(parent=None):
    """얼굴 추출 패널 표시"""
    panel = FaceExtractPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel

