"""
얼굴 편집 전용 패널 - 얼굴 랜드마크 정렬, 특징 보정, 스타일 전송, 나이 변환
"""
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import utils.config as config
import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform

class FaceEditPanel(tk.Toplevel):
    """얼굴 편집 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 편집")
        self.resizable(False, False)
        
        # 현재 선택된 이미지
        self.current_image = None
        self.current_image_path = None
        self.edited_image = None  # 편집된 이미지
        
        # 얼굴 랜드마크 정보 (나중에 추가)
        self.face_landmarks = None
        
        # 얼굴 특징 보정 설정 (Phase 1)
        self.eye_size = tk.DoubleVar(value=1.0)  # 눈 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.nose_size = tk.DoubleVar(value=1.0)  # 코 크기 (0.5 ~ 2.0, 기본값: 1.0)
        self.jaw_size = tk.DoubleVar(value=0.0)  # 턱선 조정 (-50 ~ +50, 기본값: 0.0)
        self.face_width = tk.DoubleVar(value=1.0)  # 얼굴 너비 (0.5 ~ 2.0, 기본값: 1.0)
        self.face_height = tk.DoubleVar(value=1.0)  # 얼굴 높이 (0.5 ~ 2.0, 기본값: 1.0)
        
        # 얼굴 정렬 설정
        self.auto_align = tk.BooleanVar(value=True)  # 자동 정렬 사용 여부
        
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
        
        # 상단 좌우 배치 프레임
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 왼쪽: 파일 선택 UI
        file_frame = self._create_file_selection_ui(top_frame)
        
        # 오른쪽: 편집 설정 프레임
        settings_frame = tk.LabelFrame(top_frame, text="얼굴 편집 설정", padx=5, pady=5)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 얼굴 정렬 UI (나중에 추가)
        self._create_face_alignment_ui(settings_frame)
        
        # 얼굴 특징 보정 UI (Phase 1)
        self._create_face_morphing_ui(settings_frame)
        
        # 스타일 전송 UI (Phase 2)
        self._create_style_transfer_ui(settings_frame)
        
        # 나이 변환 UI (Phase 2)
        self._create_age_transform_ui(settings_frame)
        
        # 미리보기 UI
        self._create_preview_ui(main_frame)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="준비됨", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 위젯 생성 완료 후 파일 목록 로드
        self.after(100, self.refresh_file_list)
    
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
        self.file_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select())
        
        # 버튼 프레임
        button_frame = tk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=12)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="찾아보기...", command=self.browse_file, width=12)
        btn_browse.pack(side=tk.LEFT)
        
        return file_frame
    
    def _create_face_alignment_ui(self, parent):
        """얼굴 정렬 UI 생성 (나중에 랜드마크 기능 추가 시 구현)"""
        alignment_frame = tk.LabelFrame(parent, text="얼굴 정렬", padx=5, pady=5)
        alignment_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 자동 정렬 체크박스
        auto_align_check = tk.Checkbutton(
            alignment_frame,
            text="자동 정렬 (랜드마크 기반)",
            variable=self.auto_align,
            command=self.on_alignment_change
        )
        auto_align_check.pack(side=tk.LEFT)
        
        # MediaPipe 사용 가능 여부 표시
        if face_landmarks.is_available():
            tk.Label(alignment_frame, text="(사용 가능)", fg="green").pack(side=tk.LEFT, padx=(10, 0))
        else:
            tk.Label(alignment_frame, text="(MediaPipe 필요)", fg="orange").pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_face_morphing_ui(self, parent):
        """얼굴 특징 보정 UI 생성"""
        morphing_frame = tk.LabelFrame(parent, text="얼굴 특징 보정", padx=5, pady=5)
        morphing_frame.pack(fill=tk.X, pady=(0, 5))
        
        scaled_length = 200
        label_width = 10
        
        # 초기화 버튼
        reset_button_frame = tk.Frame(morphing_frame)
        reset_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_reset = tk.Button(
            reset_button_frame,
            text="초기화",
            command=self.reset_morphing,
            width=10,
            bg="#FF9800",
            fg="white"
        )
        btn_reset.pack(side=tk.LEFT)
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
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
        
        # 눈 크기
        self.eye_size_label = create_slider(morphing_frame, "눈 크기:", self.eye_size, 0.5, 2.0, 0.01, "100%")
        
        # 코 크기
        self.nose_size_label = create_slider(morphing_frame, "코 크기:", self.nose_size, 0.5, 2.0, 0.01, "100%")
        
        # 턱선 조정
        self.jaw_size_label = create_slider(morphing_frame, "턱선:", self.jaw_size, -50.0, 50.0, 1.0, "0")
        
        # 얼굴 너비
        self.face_width_label = create_slider(morphing_frame, "얼굴 너비:", self.face_width, 0.5, 2.0, 0.01, "100%")
        
        # 얼굴 높이
        self.face_height_label = create_slider(morphing_frame, "얼굴 높이:", self.face_height, 0.5, 2.0, 0.01, "100%")
    
    def _create_style_transfer_ui(self, parent):
        """스타일 전송 UI 생성"""
        style_frame = tk.LabelFrame(parent, text="스타일 전송", padx=5, pady=5)
        style_frame.pack(fill=tk.X, pady=(0, 5))
        
        scaled_length = 200
        label_width = 10
        
        # 스타일 이미지 선택 버튼
        style_button_frame = tk.Frame(style_frame)
        style_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_select_style = tk.Button(
            style_button_frame,
            text="스타일 이미지 선택...",
            command=self.select_style_image,
            width=20
        )
        btn_select_style.pack(side=tk.LEFT, padx=(0, 5))
        
        self.style_image_label = tk.Label(style_button_frame, text="(선택 안 됨)", fg="gray", anchor="w")
        self.style_image_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, label_text, variable, from_val, to_val, resolution, default_label="", width=6):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e")
            title_label.pack(side=tk.LEFT, padx=(0, 5))
            
            scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                command=self.on_style_change,
                length=scaled_length,
                showvalue=False
            )
            scale.pack(side=tk.LEFT, padx=(0, 5))
            
            value_label = tk.Label(frame, text=default_label, width=width)
            value_label.pack(side=tk.LEFT)
            return value_label
        
        # 색상 전송 강도
        self.color_strength_label = create_slider(style_frame, "색상 강도:", self.color_strength, 0.0, 1.0, 0.01, "0%")
        
        # 텍스처 전송 강도
        self.texture_strength_label = create_slider(style_frame, "텍스처 강도:", self.texture_strength, 0.0, 1.0, 0.01, "0%")
    
    def _create_age_transform_ui(self, parent):
        """나이 변환 UI 생성"""
        age_frame = tk.LabelFrame(parent, text="나이 변환", padx=5, pady=5)
        age_frame.pack(fill=tk.X, pady=(0, 5))
        
        scaled_length = 200
        label_width = 10
        
        # 초기화 버튼
        reset_button_frame = tk.Frame(age_frame)
        reset_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_reset = tk.Button(
            reset_button_frame,
            text="초기화",
            command=self.reset_age,
            width=10,
            bg="#FF9800",
            fg="white"
        )
        btn_reset.pack(side=tk.LEFT)
        
        # 나이 조정 슬라이더
        frame = tk.Frame(age_frame)
        frame.pack(fill=tk.X)
        
        title_label = tk.Label(frame, text="나이 조정:", width=label_width, anchor="e")
        title_label.pack(side=tk.LEFT, padx=(0, 5))
        
        age_scale = tk.Scale(
            frame,
            from_=-50.0,
            to=50.0,
            resolution=1.0,
            orient=tk.HORIZONTAL,
            variable=self.age_adjustment,
            command=self.on_age_change,
            length=scaled_length,
            showvalue=False
        )
        age_scale.pack(side=tk.LEFT, padx=(0, 5))
        
        self.age_label = tk.Label(frame, text="0세", width=8)
        self.age_label.pack(side=tk.LEFT)
        
        # 설명 라벨
        tk.Label(age_frame, text="(음수=어리게, 양수=늙게)", fg="gray", font=("", 8)).pack()
    
    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""
        preview_frame = tk.LabelFrame(parent, text="미리보기", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 이미지 크기: 288x360
        preview_width = 288
        preview_height = 360
        
        # 좌측: 원본 이미지
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
        
        # 우측: 편집된 이미지
        right_frame = tk.Frame(preview_frame)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        right_top_frame = tk.Frame(right_frame)
        right_top_frame.pack(fill=tk.X)
        
        self.label_edited = tk.Label(right_top_frame, text="편집된 이미지", font=("", 9))
        self.label_edited.pack(side=tk.LEFT)
        
        btn_save = tk.Button(right_top_frame, text="PNG 저장", command=self.save_png, width=12, bg="#4CAF50", fg="white")
        btn_save.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_edited = tk.Canvas(
            right_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        self.canvas_edited.pack(padx=5, pady=5)
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            png_dir = self.face_edit_dir
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
        
        # 중복 제거
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
    
    def on_file_select(self):
        """리스트박스에서 파일 선택"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        filename = self.file_listbox.get(index)
        
        # 파일 경로 구성
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            png_dir = self.face_edit_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        file_path = os.path.join(png_dir, filename)
        
        if os.path.exists(file_path):
            self.load_image(file_path)
    
    def browse_file(self):
        """파일 선택 대화상자"""
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            initial_dir = self.face_edit_dir
        else:
            initial_dir = kaodata_image.get_png_dir()
            if not os.path.exists(initial_dir):
                initial_dir = None
        
        file_path = filedialog.askopenfilename(
            title="이미지 파일 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_path:
            import globals as gl
            import utils.config as config
            source_dir = os.path.dirname(file_path)
            if not os.path.isabs(source_dir):
                source_dir = os.path.abspath(source_dir)
            self.face_edit_dir = source_dir
            gl._face_extract_dir = source_dir
            config.save_config()
            
            self.refresh_file_list()
            
            filename = os.path.basename(file_path)
            for i in range(self.file_listbox.size()):
                if self.file_listbox.get(i) == filename:
                    self.file_listbox.selection_clear(0, tk.END)
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
            
            self.load_image(file_path)
    
    def load_image(self, file_path):
        """이미지 로드"""
        try:
            img = Image.open(file_path)
            self.current_image = img
            self.current_image_path = file_path
            
            # 자동 정렬이 활성화되어 있으면 정렬 적용
            if self.auto_align.get():
                self.apply_alignment()
            else:
                # 편집된 이미지 초기화
                self.edited_image = img.copy()
            
            # 미리보기 업데이트
            self.show_original_preview()
            self.show_edited_preview()
            
            filename = os.path.basename(file_path)
            self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def show_original_preview(self):
        """원본 이미지 미리보기 표시"""
        if self.current_image is None:
            if self.image_created_original:
                self.canvas_original.delete(self.image_created_original)
                self.image_created_original = None
            return
        
        try:
            # 이미지 리사이즈 (미리보기용, 288x360)
            preview_size = (288, 360)
            resized = self.current_image.resize(preview_size, Image.LANCZOS)
            
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
        except Exception as e:
            print(f"[얼굴편집] 원본 이미지 표시 실패: {e}")
    
    def show_edited_preview(self):
        """편집된 이미지 미리보기 표시"""
        if self.edited_image is None:
            if self.image_created_edited:
                self.canvas_edited.delete(self.image_created_edited)
                self.image_created_edited = None
            return
        
        try:
            # 이미지 리사이즈 (미리보기용, 288x360)
            preview_size = (288, 360)
            resized = self.edited_image.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_edited = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_edited:
                self.canvas_edited.delete(self.image_created_edited)
            
            self.image_created_edited = self.canvas_edited.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_edited
            )
        except Exception as e:
            print(f"[얼굴편집] 편집된 이미지 표시 실패: {e}")
    
    def on_alignment_change(self):
        """얼굴 정렬 설정 변경 시 호출"""
        if self.current_image is not None and self.auto_align.get():
            self.apply_alignment()
    
    def apply_alignment(self):
        """얼굴 정렬 적용"""
        if self.current_image is None:
            return
        
        if not face_landmarks.is_available():
            self.status_label.config(text="경고: MediaPipe가 설치되지 않았습니다.", fg="orange")
            # MediaPipe가 없어도 이미지는 로드
            self.edited_image = self.current_image.copy()
            return
        
        try:
            # 얼굴 정렬
            aligned_image, angle = face_landmarks.align_face(self.current_image)
            
            # 정렬된 이미지를 현재 이미지로 설정
            self.current_image = aligned_image
            self.edited_image = aligned_image.copy()
            
            # 미리보기 업데이트
            self.show_original_preview()
            self.show_edited_preview()
            
            if abs(angle) > 0.1:
                self.status_label.config(text=f"얼굴 정렬 완료 (회전: {angle:.1f}도)", fg="green")
            else:
                self.status_label.config(text="얼굴 정렬 완료 (이미 정렬됨)", fg="green")
                
        except Exception as e:
            print(f"[얼굴편집] 얼굴 정렬 실패: {e}")
            self.status_label.config(text=f"얼굴 정렬 실패: {e}", fg="red")
            # 정렬 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            # 정렬 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
    
    def on_morphing_change(self, value=None):
        """얼굴 특징 보정 변경 시 호출"""
        # 라벨 업데이트
        eye_value = self.eye_size.get()
        self.eye_size_label.config(text=f"{int(eye_value * 100)}%")
        
        nose_value = self.nose_size.get()
        self.nose_size_label.config(text=f"{int(nose_value * 100)}%")
        
        jaw_value = self.jaw_size.get()
        self.jaw_size_label.config(text=f"{int(jaw_value)}")
        
        face_width_value = self.face_width.get()
        self.face_width_label.config(text=f"{int(face_width_value * 100)}%")
        
        face_height_value = self.face_height.get()
        self.face_height_label.config(text=f"{int(face_height_value * 100)}%")
        
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def select_style_image(self):
        """스타일 이미지 선택"""
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            initial_dir = self.face_edit_dir
        else:
            initial_dir = kaodata_image.get_png_dir()
            if not os.path.exists(initial_dir):
                initial_dir = None
        
        file_path = filedialog.askopenfilename(
            title="스타일 이미지 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_path:
            self.style_image_path = file_path
            filename = os.path.basename(file_path)
            self.style_image_label.config(text=f"선택됨: {filename}", fg="green")
            
            # 이미지가 로드되어 있으면 스타일 적용
            if self.current_image is not None:
                self.apply_editing()
    
    def on_style_change(self, value=None):
        """스타일 전송 설정 변경 시 호출"""
        # 라벨 업데이트
        color_value = self.color_strength.get()
        self.color_strength_label.config(text=f"{int(color_value * 100)}%")
        
        texture_value = self.texture_strength.get()
        self.texture_strength_label.config(text=f"{int(texture_value * 100)}%")
        
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def on_age_change(self, value=None):
        """나이 변환 설정 변경 시 호출"""
        # 라벨 업데이트
        age_value = self.age_adjustment.get()
        if age_value < 0:
            self.age_label.config(text=f"{int(age_value)}세", fg="blue")
        elif age_value > 0:
            self.age_label.config(text=f"+{int(age_value)}세", fg="red")
        else:
            self.age_label.config(text="0세", fg="black")
        
        # 이미지가 로드되어 있으면 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def reset_age(self):
        """나이 변환 값 초기화"""
        self.age_adjustment.set(0.0)
        self.on_age_change()
        
        # 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def reset_morphing(self):
        """얼굴 특징 보정 값들을 모두 초기화"""
        self.eye_size.set(1.0)
        self.nose_size.set(1.0)
        self.jaw_size.set(0.0)
        self.face_width.set(1.0)
        self.face_height.set(1.0)
        
        # 라벨 업데이트
        self.on_morphing_change()
        
        # 편집 적용
        if self.current_image is not None:
            self.apply_editing()
    
    def apply_editing(self):
        """편집 적용"""
        if self.current_image is None:
            return
        
        try:
            # 처리 순서: 특징 보정 → 스타일 전송 → 나이 변환
            
            # 1. 얼굴 특징 보정 적용
            result = face_morphing.apply_all_adjustments(
                self.current_image,
                eye_size=self.eye_size.get(),
                nose_size=self.nose_size.get(),
                jaw_adjustment=self.jaw_size.get(),
                face_width=self.face_width.get(),
                face_height=self.face_height.get()
            )
            
            # 2. 스타일 전송 적용
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
                    print(f"[얼굴편집] 스타일 전송 실패: {e}")
            
            # 3. 나이 변환 적용
            age_adjustment = self.age_adjustment.get()
            if abs(age_adjustment) >= 1.0:
                result = face_transform.transform_age(result, age_adjustment=int(age_adjustment))
            
            self.edited_image = result
            
            # 미리보기 업데이트
            self.show_edited_preview()
            
        except Exception as e:
            print(f"[얼굴편집] 편집 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 원본 이미지 사용
            self.edited_image = self.current_image.copy()
            self.show_edited_preview()
    
    def save_png(self):
        """편집된 이미지를 PNG 파일로 저장"""
        if self.edited_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            png_filename = f"{base_name}_edited.png"
            
            # 저장 폴더 경로 결정
            if self.face_edit_dir and os.path.exists(self.face_edit_dir):
                save_dir = self.face_edit_dir
            else:
                save_dir = os.path.dirname(self.current_image_path)
            
            # 파일 경로
            file_path = os.path.join(save_dir, png_filename)
            
            # PNG로 저장
            self.edited_image.save(file_path, "PNG")
            
            self.status_label.config(
                text=f"저장 완료: {png_filename}",
                fg="green"
            )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def on_close(self):
        """창 닫기"""
        self.destroy()

def show_face_edit_panel(parent=None):
    """얼굴 편집 패널 표시"""
    panel = FaceEditPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel
