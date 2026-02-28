"""Popup and window management mixin for FaceEditPanel."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from .landmark import StateKeys

from utils.logger import log, debug
from gui.FaceForge.utils.debugs import DEBUG_CURRENT_LANDMARKS, DEBUG_PREVIEW_UPDATE


class PopupManagerMixin:
    """Provides file/settings popup helpers for the face edit panel."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview_popup = None
        self.canvas_preview = None

        self.detect_offset_x = tk.DoubleVar(value=0.0)
        self.detect_offset_y = tk.DoubleVar(value=0.0)
        self.detect_pivot_x = tk.DoubleVar(value=0.0)
        self.detect_pivot_y = tk.DoubleVar(value=0.0)
        self.detect_scale_x = tk.DoubleVar(value=1.0)
        self.detect_scale_y = tk.DoubleVar(value=1.0)
        self.detect_rotation_deg = tk.DoubleVar(value=0.0)

    def show_files_popup(self):
        """파일 리스트 팝업창 표시"""
        if self.file_list_popup is not None and self.file_list_popup.winfo_exists():
            self.file_list_popup.lift()
            self.file_list_popup.focus()
            return

        popup = tk.Toplevel(self)
        popup.title("파일 선택")
        popup.transient(self)
        popup.resizable(True, True)
        popup.minsize(400, 300)

        file_frame = self._create_file_selection_ui(popup)
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        popup.after(100, self.refresh_file_list)

        def on_popup_close():
            self.file_list_popup = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.file_list_popup = popup

    def _reset_alignment_params(self):
        self.detect_offset_x.set(0.0)
        self.detect_offset_y.set(0.0)
        self.detect_pivot_x.set(0.0)
        self.detect_pivot_y.set(0.0)        
        self.detect_scale_x.set(1.0)
        self.detect_scale_y.set(1.0)
        self.detect_rotation_deg.set(0.0)
        self.status_var.set("Alignment parameters reset.")

    def _get_alignment_params(self):
        params = {
            "offset_x": self.detect_offset_x.get(),
            "offset_y": self.detect_offset_y.get(),
            "scale_x": self.detect_scale_x.get(),
            "scale_y": self.detect_scale_y.get(),
            "pivot_x": self.detect_pivot_x.get(),
            "pivot_y": self.detect_pivot_y.get(),
            "rotation_deg": self.detect_rotation_deg.get(),
        }
        return params

    def _set_alignment_params(self):

        align = self.alignment_params or {}

        self.detect_offset_x.set(align.get("offset_x", 0.0))
        self.detect_offset_y.set(align.get("offset_y", 0.0))
        self.detect_scale_x.set(align.get("scale_x", 1.0))
        self.detect_scale_y.set(align.get("scale_y", 1.0))

        self.detect_pivot_x.set(align.get("pivot_x", 0))
        self.detect_pivot_y.set(align.get("pivot_y", 0))
        self.detect_rotation_deg.set(align.get("rotation_deg", 0.0))

    # gui/popup.py (또는 적절한 mixin)에 공통 헬퍼 추가
    def _apply_detected_landmarks(self, landmarks, reason="detect_alignment"):
        lm = self.landmark_manager
        lm.set_original_landmarks(landmarks, self.original_image.width, self.original_image.height)
        lm.set_current_landmarks(landmarks.copy(), reason=reason)
        
        current_landmarks = lm.get_current_landmarks()
        #print("_apply_detected_landmarks current", self.get_bbox_lips(current_landmarks))

        # landmark_state 동기화
        base = landmarks[:468] if len(landmarks) >= 468 else landmarks
        lm.set_state_value(StateKeys.SECTION_ORIGINAL, StateKeys.KEY_FACE_LANDMARKS, base)
        lm.set_state_value(StateKeys.SECTION_CURRENT, StateKeys.KEY_FACE_LANDMARKS, base.copy())

        # warp 섹션 초기화 (source=target=감지값)
        lm.set_state_section(StateKeys.SECTION_WARP, {
            StateKeys.KEY_SOURCE_LANDMARKS: base,
            StateKeys.KEY_TARGET_LANDMARKS: base.copy(),
            StateKeys.KEY_SELECTED_INDICES: [],
        })

        # 기타 표시/가이드 초기화가 필요하면 여기서 처리
        self._last_warping_state_signature = None


    def _detect_apply_alignment(self):

        params = self._get_alignment_params()
        if DEBUG_CURRENT_LANDMARKS:
            debug( "_detect_apply_alignment", f"params: {params}")

        from gui.FaceForge.utils import landmarks as utilmarks
        detected, landmarks = utilmarks.detect_face_landmarks(self.original_image, params)
        if detected:
            self.landmark_manager.reset(keep_original=False)
            self.clear_face_features_all()      # 기존 오버레이 제거
            self._apply_detected_landmarks(landmarks, reason="detect_alignment")            

            #self._reset_region_checkbox()
            self._reset_common_sliders()

            polygons_enabled = self._is_polygon_display_enabled()
            pivots_enabled = self._is_pivot_display_enabled()
            guides_enabled = self._is_guides_display_enabled()
            bbox_enabled = self._is_bbox_frame_display_enabled()

            self.image_created_original = None
            self._last_preview_update_signature = None  # 시그니처 무효화

            self.update_face_edit_display(
                image=True,
                polygons=polygons_enabled,
                pivots=pivots_enabled,
                guides=guides_enabled,
                bbox=bbox_enabled,
                force_original=True,
            )

        self.status_var.set("Dectect with parameters applied.")


    def _on_alignment_param_change(self):
        """Alignment 스핀박스 변경 시 호출"""
        # 예: 상태바 업데이트나 플래그 세팅
        self.status_var.set("Alignment parameters changed (re-run detection to apply).")


    def _build_alignment_controls(self, tab_frame):
        """Alignment 탭 UI 구성"""

        label_width = 9
        spin_width = 6

        control_frame = tk.LabelFrame(tab_frame, text="Alignment Controls", padx=5, pady=5)
        control_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))        

        # 오프셋 스핀박스
        tk.Label(control_frame, text="offset X", width=label_width, anchor='e' ).grid(row=0, column=0, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_offset_x,
                from_=-200, to=200, increment=0.5, width=spin_width,
                command=self._on_alignment_param_change).grid(row=0, column=1, padx=(8, 8))

        tk.Label(control_frame, text="offset Y", width=label_width, anchor='e' ).grid(row=0, column=2, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_offset_y,
                from_=-200, to=200, increment=0.5, width=spin_width,
                command=self._on_alignment_param_change).grid(row=0, column=3)

        # 스케일
        tk.Label(control_frame, text="scale X", width=label_width, anchor='e' ).grid(row=1, column=0, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_scale_x,
                from_=0.5, to=1.5, increment=0.01, width=spin_width,
                command=self._on_alignment_param_change).grid(row=1, column=1, padx=(8, 8))

        tk.Label(control_frame, text="scale Y", width=label_width, anchor='e' ).grid(row=1, column=2, sticky=tk.E, pady=(6,0))
        tk.Spinbox(control_frame, textvariable=self.detect_scale_y,
                from_=0.5, to=1.5, increment=0.01, width=spin_width,
                command=self._on_alignment_param_change).grid(row=1, column=3, padx=(8, 8))

        # 피봇 스핀박스
        tk.Label(control_frame, text="pivot X", width=label_width, anchor='e' ).grid(row=2, column=0, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_pivot_x,
                from_=-200, to=200, increment=0.5, width=spin_width,
                command=self._on_alignment_param_change).grid(row=2, column=1, padx=(8, 8))

        tk.Label(control_frame, text="pivot Y", width=label_width, anchor='e' ).grid(row=2, column=2, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_pivot_y,
                from_=-200, to=200, increment=0.5, width=spin_width,
                command=self._on_alignment_param_change).grid(row=2, column=3, padx=(8, 8))

        # 회전
        #tk.Label(control_frame, text="Rotation°", width=label_width, anchor='e' ).grid(row=3, column=0, sticky=tk.E)
        tk.Label(control_frame, text="rotation°", width=label_width, anchor='e' ).grid(row=3, column=0, sticky=tk.E, pady=(4,0))
        tk.Spinbox(control_frame, textvariable=self.detect_rotation_deg,
                from_=-30, to=30, increment=0.1, width=spin_width,
                command=self._on_alignment_param_change).grid(row=3, column=1, padx=(8, 8))

        button_frame = tk.LabelFrame(tab_frame, text="", padx=5, pady=5)
        button_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))                        

        # 값 초기화 버튼
        ttk.Button(button_frame, text="Reset", width=20, command=self._reset_alignment_params)\
            .grid(row=0, column=0, padx=(0, 16), pady=(4,0))        

        # 값 초기화 버튼
        ttk.Button(button_frame, text="Dectect", width=20, command=self._detect_apply_alignment)\
            .grid(row=0, column=1, padx=(0, 16), pady=(4,0))
        

    def show_settings_popup(self):
        """편집 설정 팝업창 표시"""
        if self.settings_popup is not None and self.settings_popup.winfo_exists():
            self.settings_popup.lift()
            self.settings_popup.focus()
            return

        popup = tk.Toplevel(self)
        popup.title("얼굴 편집 설정")
        popup.transient(self)
        popup.resizable(True, True)
        popup.geometry(f"400x500+0+330")  # 화면 좌측(100, 80)에 고정
        #popup.minsize(400, 500)

        settings_frame = tk.LabelFrame(popup, text="얼굴 편집 설정", padx=5, pady=5)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_face_region(settings_frame)

        main_notebook = ttk.Notebook(settings_frame)
        main_notebook.pack(fill=tk.BOTH, expand=True, pady=(8, 4))

        face_tab = self._create_face_tab(main_notebook)
        main_notebook.add(face_tab, text="얼굴부위 수정")

        alignment_tab = tk.Frame(main_notebook, padx=8, pady=0)
        main_notebook.add(alignment_tab, text="랜드마크 조정")
        
        # 탭 안에 원하는 UI 배치
        self._build_alignment_controls(alignment_tab)


        def on_popup_close():
            self.settings_popup = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.settings_popup = popup

    def show_preview_popup(self):
        """미리보기 팝업창 표시"""
        if DEBUG_PREVIEW_UPDATE:
            #log("show_preview_popup", f"{self.region_params}")
            for name, data in self.region_params.items():
                selected = data["enabled"]
                applied = data.get("applied", False)
                sliders = data.get("sliders", {})
                dragged = data.get("dragged_points", {})
                log("show_preview_popup", f"{name}: enabled={selected}, applied={applied}, dragged={len(dragged)}")

        if self.preview_popup is not None and self.preview_popup.winfo_exists():
            self.preview_popup.lift()
            self.preview_popup.focus()
            self.update_preview_canvas(self.current_image)
            return

        popup = tk.Toplevel(self)
        popup.title(f"미리보기 ({self.original_image_path})")
        popup.transient(self)
        popup.resizable(True, True)

        self.update_idletasks()  # 부모의 최신 위치/크기 반영
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        popup.geometry(f"400x500+{parent_x+parent_w}+{parent_y}")  # 화면 좌측(100, 80)에 고정

        preview_frame = tk.Frame(popup, )
        preview_frame.pack(fill=tk.BOTH, expand=True, )

        preview_width = 400
        preview_height = 500

        self.canvas_preview = tk.Canvas(
            preview_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        self.canvas_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        def on_popup_close():
            self.preview_popup = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)

        def on_canvas_resize(event):
            # 캔버스가 실제로 보이는 상태에서만 갱신
            if self.canvas_preview.winfo_exists():
                self.update_preview_canvas(self.current_image)
                    
        self.canvas_preview.bind("<Configure>", on_canvas_resize) 

        def _on_preview_click(event):
            target = self.original_image
            self.update_preview_canvas(target)
            self.preview_popup.title(f"원본보기 ({self.original_image_path})")
        
        def _on_preview_release(event):
            target = self.current_image
            self.update_preview_canvas(target)
            self.preview_popup.title(f"미리보기 ({self.original_image_path})")
            pass
        
        self.canvas_preview.bind("<Button-1>", _on_preview_click)
        self.canvas_preview.bind("<ButtonRelease-1>", _on_preview_release)
        self.preview_popup = popup
        
        self.update_preview_canvas(self.current_image)


    def on_close(self):
        """창 닫기"""
        if self.file_list_popup is not None and self.file_list_popup.winfo_exists():
            self.file_list_popup.destroy()
        if self.settings_popup is not None and self.settings_popup.winfo_exists():
            self.settings_popup.destroy()
        self.destroy()

    def update_preview_canvas(self, pil_image):
        if self.canvas_preview is None or pil_image is None:
            return
    
        # 필요하면 캔버스 크기에 맞게 리사이즈
        width = self.canvas_preview.winfo_width() or 400
        height = self.canvas_preview.winfo_height() or 500

        cached_bbox = self.landmark_manager.get_original_bbox(pil_image.size[0], pil_image.size[1] )
        cropped = pil_image.crop(cached_bbox) if cached_bbox else pil_image

        img_w, img_h = cropped.size
        scale = min(width / img_w, height / img_h)
        target_w = max(1, int(img_w * scale))
        target_h = max(1, int(img_h * scale))
        resized = cropped.resize((target_w, target_h), Image.LANCZOS)
    
        tk_img = ImageTk.PhotoImage(resized)
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(width // 2, height // 2, image=tk_img, anchor="center")
    
        # PhotoImage를 속성에 보관 (GC 방지)
        self.canvas_preview.image = tk_img
