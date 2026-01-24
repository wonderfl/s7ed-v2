"""
얼굴 편집 패널 - 위젯 생성 Mixin
위젯 생성 및 UI 구성 로직을 담당
"""
import tkinter as tk


class WidgetCreatorMixin:
    """위젯 생성 기능 Mixin"""
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단: 버튼 프레임
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_file_select = tk.Button(button_frame, text="파일 선택", command=self.show_file_list_popup, width=12)
        btn_file_select.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_settings = tk.Button(button_frame, text="편집 설정", command=self.show_settings_popup, width=12)
        btn_settings.pack(side=tk.LEFT)
        
        # 중앙: 좌측(원본) + 우측(편집본) - grid 레이아웃 사용
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # grid 컬럼을 균등하게 분할 (두 컬럼이 같은 비율로 확장)
        content_frame.grid_columnconfigure(0, weight=1, minsize=self.canvas_min_width + 10)
        content_frame.grid_columnconfigure(1, weight=1, minsize=self.canvas_min_width + 10)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # content_frame의 최소 크기 제한
        def on_content_frame_configure(event):
            if self._resizing_canvas:
                return
            content_width = event.width
            content_height = event.height
            
            # 각 프레임이 최소 크기를 유지하도록 계산
            button_height = 30
            min_frame_width = self.canvas_min_width + 10  # 패딩 고려
            min_frame_height = self.canvas_min_height + button_height + 10
            required_width = (min_frame_width * 2) + 5  # 두 프레임 + 여백
            required_height = min_frame_height
            
            # content_frame이 최소 크기보다 작으면 창 크기 조정
            if content_width < required_width or content_height < required_height:
                self._resizing_canvas = True
                try:
                    window_width = self.winfo_width()
                    window_height = self.winfo_height()
                    new_width = max(window_width, required_width + 50)
                    new_height = max(window_height, required_height + 100)
                    if new_width != window_width or new_height != window_height:
                        self.geometry(f"{new_width}x{new_height}")
                finally:
                    self.after_idle(lambda: setattr(self, '_resizing_canvas', False))
        
        content_frame.bind("<Configure>", on_content_frame_configure)
        
        # 좌측: 원본 이미지
        original_frame = tk.LabelFrame(content_frame, text="원본", padx=5, pady=5)
        original_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 원본 이미지 캔버스 (크게)
        self.canvas_original = tk.Canvas(
            original_frame,
            width=self.canvas_initial_width,
            height=self.canvas_initial_height,
            bg="gray"
        )
        self.canvas_original.pack(fill=tk.BOTH, expand=True)
        self.image_created_original = None
        
        # 원본 이미지 확대/축소 버튼
        original_zoom_frame = tk.Frame(original_frame)
        original_zoom_frame.pack(fill=tk.X, pady=(5, 0))
        
        btn_zoom_in_original = tk.Button(original_zoom_frame, text="확대", command=self.zoom_in_original, width=6)
        btn_zoom_in_original.pack(side=tk.LEFT, padx=2)
        btn_zoom_out_original = tk.Button(original_zoom_frame, text="축소", command=self.zoom_out_original, width=6)
        btn_zoom_out_original.pack(side=tk.LEFT, padx=2)
        btn_zoom_reset_original = tk.Button(original_zoom_frame, text="원래대로", command=self.zoom_reset_original, width=8)
        btn_zoom_reset_original.pack(side=tk.LEFT, padx=2)
        # 원본 이미지 좌표 표시 라벨
        self.original_coord_label = tk.Label(original_zoom_frame, text="", font=("", 8), width=8)
        self.original_coord_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 원본 이미지 드래그 이벤트 바인딩
        self.canvas_original.bind("<Button-1>", self.on_canvas_original_drag_start)
        self.canvas_original.bind("<B1-Motion>", self.on_canvas_original_drag)
        self.canvas_original.bind("<ButtonRelease-1>", self.on_canvas_original_drag_end)
        
        # 마우스 휠로 확대/축소 (원본 이미지) - 마우스 위치를 중심으로 확대/축소
        def on_mousewheel_original_wrapper(event):
            if not self.canvas_original.winfo_containing(event.x_root, event.y_root):
                return
            
            # 마우스 위치 저장
            self._last_mouse_x_original = event.x
            self._last_mouse_y_original = event.y
            
            if event.delta > 0:
                self.zoom_in_original(mouse_x=event.x, mouse_y=event.y)
            elif event.delta < 0:
                self.zoom_out_original(mouse_x=event.x, mouse_y=event.y)
        
        self.canvas_original.bind("<MouseWheel>", on_mousewheel_original_wrapper)
        
        # 마우스 이동 시 위치 저장 및 좌표 표시
        def on_mouse_move_original(event):
            self._last_mouse_x_original = event.x
            self._last_mouse_y_original = event.y
            
            # 이미지 좌표 계산 및 표시
            if self.current_image is not None:
                img_width, img_height = self.current_image.size
                pos_x = getattr(self, 'canvas_original_pos_x', None)
                pos_y = getattr(self, 'canvas_original_pos_y', None)
                
                if pos_x is not None and pos_y is not None:
                    display_size = getattr(self.canvas_original, 'display_size', None)
                    if display_size is None:
                        display_width = img_width
                        display_height = img_height
                    else:
                        display_width, display_height = display_size
                    
                    scale_x = display_width / img_width
                    scale_y = display_height / img_height
                    
                    # 캔버스 좌표를 이미지 좌표로 변환
                    rel_x = (event.x - pos_x) / scale_x
                    rel_y = (event.y - pos_y) / scale_y
                    img_x = int(img_width / 2 + rel_x)
                    img_y = int(img_height / 2 + rel_y)
                    
                    # 이미지 범위 내인지 확인
                    if 0 <= img_x < img_width and 0 <= img_y < img_height:
                        if hasattr(self, 'original_coord_label'):
                            self.original_coord_label.config(text=f"({img_x}, {img_y})")
                    else:
                        if hasattr(self, 'original_coord_label'):
                            self.original_coord_label.config(text="")
                else:
                    if hasattr(self, 'original_coord_label'):
                        self.original_coord_label.config(text="")
            else:
                if hasattr(self, 'original_coord_label'):
                    self.original_coord_label.config(text="")
        
        self.canvas_original.bind("<Motion>", on_mouse_move_original)
        
        # 캔버스에 마우스가 들어올 때 포커스 설정
        def on_enter_canvas_original(event):
            self.canvas_original.focus_set()
        self.canvas_original.bind("<Enter>", on_enter_canvas_original)
        
        # 캔버스에서 마우스가 나갈 때 좌표 라벨 초기화
        def on_leave_canvas_original(event):
            if hasattr(self, 'original_coord_label'):
                self.original_coord_label.config(text="")
        self.canvas_original.bind("<Leave>", on_leave_canvas_original)
        
        # 우측: 편집된 이미지 프리뷰
        edited_preview_frame = tk.LabelFrame(content_frame, text="편집된 이미지", padx=5, pady=5)
        edited_preview_frame.grid(row=0, column=1, sticky="nsew")
        
        # 편집된 이미지 캔버스
        self.canvas_edited = tk.Canvas(
            edited_preview_frame,
            width=self.canvas_initial_width,
            height=self.canvas_initial_height,
            bg="gray"
        )
        self.canvas_edited.pack(fill=tk.BOTH, expand=True)
        self.image_created_edited = None
        
        # 편집된 이미지 확대/축소 버튼
        edited_zoom_frame = tk.Frame(edited_preview_frame)
        edited_zoom_frame.pack(fill=tk.X, pady=(5, 0))
        
        btn_zoom_in_edited = tk.Button(edited_zoom_frame, text="확대", command=self.zoom_in_edited, width=6)
        btn_zoom_in_edited.pack(side=tk.LEFT, padx=2)
        btn_zoom_out_edited = tk.Button(edited_zoom_frame, text="축소", command=self.zoom_out_edited, width=6)
        btn_zoom_out_edited.pack(side=tk.LEFT, padx=2)
        btn_zoom_reset_edited = tk.Button(edited_zoom_frame, text="원래대로", command=self.zoom_reset_edited, width=8)
        btn_zoom_reset_edited.pack(side=tk.LEFT, padx=2)

        # 편집 이미지 좌표 표시 라벨
        self.edited_coord_label = tk.Label(edited_zoom_frame, text="", font=("", 8), width=8)
        self.edited_coord_label.pack(side=tk.LEFT, padx=(5, 0))

        btn_save = tk.Button(edited_zoom_frame, text="편집된 PNG 저장", command=self.save_png, width=12,
                            bg="#4CAF50", fg="white", bd=2, cursor="hand2")
        btn_save.pack(side=tk.LEFT, padx=(5, 0))
        
        # 편집된 이미지 드래그 이벤트 바인딩
        self.canvas_edited.bind("<Button-1>", self.on_canvas_edited_drag_start)
        self.canvas_edited.bind("<B1-Motion>", self.on_canvas_edited_drag)
        self.canvas_edited.bind("<ButtonRelease-1>", self.on_canvas_edited_drag_end)
        
        # 마우스 휠로 확대/축소 (편집된 이미지) - 마우스 위치를 중심으로 확대/축소
        def on_mousewheel_edited_wrapper(event):
            if not self.canvas_edited.winfo_containing(event.x_root, event.y_root):
                return
            
            # 마우스 위치 저장
            self._last_mouse_x_edited = event.x
            self._last_mouse_y_edited = event.y
            
            if event.delta > 0:
                self.zoom_in_edited(mouse_x=event.x, mouse_y=event.y)
            elif event.delta < 0:
                self.zoom_out_edited(mouse_x=event.x, mouse_y=event.y)
        
        self.canvas_edited.bind("<MouseWheel>", on_mousewheel_edited_wrapper)
        
        # 마우스 이동 시 위치 저장 및 좌표 표시
        def on_mouse_move_edited(event):
            self._last_mouse_x_edited = event.x
            self._last_mouse_y_edited = event.y
            
            # 이미지 좌표 계산 및 표시
            if self.edited_image is not None:
                img_width, img_height = self.edited_image.size
                pos_x = getattr(self, 'canvas_edited_pos_x', None)
                pos_y = getattr(self, 'canvas_edited_pos_y', None)
                
                if pos_x is not None and pos_y is not None:
                    display_size = getattr(self.canvas_edited, 'display_size', None)
                    if display_size is None:
                        display_width = img_width
                        display_height = img_height
                    else:
                        display_width, display_height = display_size
                    
                    scale_x = display_width / img_width
                    scale_y = display_height / img_height
                    
                    # 캔버스 좌표를 이미지 좌표로 변환
                    rel_x = (event.x - pos_x) / scale_x
                    rel_y = (event.y - pos_y) / scale_y
                    img_x = int(img_width / 2 + rel_x)
                    img_y = int(img_height / 2 + rel_y)
                    
                    # 이미지 범위 내인지 확인
                    if 0 <= img_x < img_width and 0 <= img_y < img_height:
                        if hasattr(self, 'edited_coord_label'):
                            self.edited_coord_label.config(text=f"({img_x}, {img_y})")
                    else:
                        if hasattr(self, 'edited_coord_label'):
                            self.edited_coord_label.config(text="")
                else:
                    if hasattr(self, 'edited_coord_label'):
                        self.edited_coord_label.config(text="")
            else:
                if hasattr(self, 'edited_coord_label'):
                    self.edited_coord_label.config(text="")
        
        self.canvas_edited.bind("<Motion>", on_mouse_move_edited)
        
        # 캔버스에 마우스가 들어올 때 포커스 설정
        def on_enter_canvas_edited(event):
            self.canvas_edited.focus_set()
        self.canvas_edited.bind("<Enter>", on_enter_canvas_edited)
        
        # 캔버스에서 마우스가 나갈 때 좌표 라벨 초기화
        def on_leave_canvas_edited(event):
            if hasattr(self, 'edited_coord_label'):
                self.edited_coord_label.config(text="")
        self.canvas_edited.bind("<Leave>", on_leave_canvas_edited)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="준비됨", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        
        # 파일 목록은 팝업창이 열릴 때 로드되므로 여기서는 로드하지 않음
