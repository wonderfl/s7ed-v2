import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.face_landmarks import detect_face_landmarks
from gui.face_edit.landmark_manager import LandmarkManager
from gui.face_edit.polygon_renderer.tab_drawers import TabDrawersMixin
from gui.face_edit.polygon_renderer.all_tab_drawer import AllTabDrawerMixin
from utils.face_morphing.polygon_morphing.core import _prepare_iris_centers # 클램핑 로직 테스트용

# Tkinter 캔버스에 이미지 및 랜드마크를 그리는 기본 클래스
class DebugCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.image_tk = None
        self.current_image = None
        self.landmarks = None
        self.display_scale_factor = 1.0
        self.image_on_canvas = None

    def set_image(self, pil_image):
        self.current_image = pil_image
        self.image_tk = ImageTk.PhotoImage(pil_image)
        if self.image_on_canvas:
            self.itemconfig(self.image_on_canvas, image=self.image_tk)
        else:
            self.image_on_canvas = self.create_image(0, 0, anchor="nw", image=self.image_tk)
        self.config(width=pil_image.width, height=pil_image.height)
        self.display_size = (pil_image.width, pil_image.height) # _draw_iris_tab_polygons에서 사용

    def set_landmarks(self, landmarks):
        self.landmarks = landmarks

    def clear_drawings(self):
        for item in self.find_withtag("landmarks_polygon"):
            self.delete(item)

# 디버깅용 더미 FaceEditPanel (필요한 Mixin만 상속)
class MockFaceEditPanel(tk.Frame, TabDrawersMixin, AllTabDrawerMixin):
    def __init__(self, parent, debug_canvas_original, debug_canvas_edited, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas_original = debug_canvas_original
        self.canvas_edited = debug_canvas_edited
        self.landmark_manager = LandmarkManager() # 실제 LandmarkManager 사용

        # UI 변수 (FaceEditPanel에서 가져옴)
        self.iris_clamping_enabled = tk.BooleanVar(value=True)
        self.iris_clamping_margin_ratio = tk.DoubleVar(value=0.5)

        # 드래그 이벤트 관련 더미 속성 (tab_drawers에서 사용)
        self.on_iris_center_drag_start = lambda e, side, canvas: print(f"Drag Start: {side}")
        self.on_iris_center_drag = lambda e, side, canvas: print(f"Dragging: {side}")
        self.on_iris_center_drag_end = lambda e, side, canvas: print(f"Drag End: {side}")
        
        # 랜드마크 중심점 좌표 저장용 (tab_drawers에서 사용)
        self._left_iris_center_coord = None
        self._right_iris_center_coord = None

        # 더미 _get_iris_indices 및 _calculate_iris_center 메서드 (tab_drawers에서 사용)
        def _get_iris_indices_mock():
            from utils.face_morphing.region_extraction import get_iris_indices
            return get_iris_indices()
        self._get_iris_indices = _get_iris_indices_mock

        def _calculate_iris_center_mock(landmarks_list, iris_indices, img_w, img_h):
            iris_points = []
            for idx in iris_indices:
                if idx < len(landmarks_list):
                    pt = landmarks_list[idx]
                    iris_points.append( (pt.x * img_w, pt.y * img_h) if hasattr(pt, 'x') else pt )
            if iris_points:
                center_x = sum(p[0] for p in iris_points) / len(iris_points)
                center_y = sum(p[1] for p in iris_points) / len(iris_points)
                return (center_x, center_y)
            return None
        self._calculate_iris_center = _calculate_iris_center_mock


    def update_iris_display(self):
        self.canvas_original.clear_drawings()
        self.canvas_edited.clear_drawings()

        if self.landmark_manager.has_original_face_landmarks():
            original_landmarks = self.landmark_manager.get_original_face_landmarks()
            
            # 눈동자 중심점 정보 가져오기 (LandmarkManager에서 최신 정보 활용)
            left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
            right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
            iris_centers = [left_iris_center_coord, right_iris_center_coord]

            # _draw_iris_tab_polygons 함수 호출 (원본 캔버스)
            self._draw_iris_tab_polygons(
                self.canvas_original,
                self.canvas_original.current_image,
                original_landmarks,
                self.canvas_original.winfo_width() / 2, # center pos_x
                self.canvas_original.winfo_height() / 2, # center pos_y
                [], # items_list
                "blue", # color
                1.0, 1.0, # scale_x, scale_y
                self.canvas_original.current_image.width,
                self.canvas_original.current_image.height,
                0, # expansion_level
                True, # show_indices
                lambda pid, ti: None, # bind_polygon_click_events (dummy)
                False, # force_use_custom
                iris_centers, # iris_centers
                self.iris_clamping_enabled.get(),
                self.iris_clamping_margin_ratio.get()
            )

# 메인 디버깅 앱
class IrisMovementDebugger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("눈동자 이동 디버거")
        self.geometry("1000x800")

        self.image_path = None
        self.pil_image = None

        # UI 요소 생성
        self.create_widgets()
        
        # 랜드마크 매니저 초기화 (MockFaceEditPanel에서 사용)
        self.landmark_manager = LandmarkManager()

        # MockFaceEditPanel 인스턴스화
        self.mock_panel = MockFaceEditPanel(self, self.canvas_original, self.canvas_edited)
        self.mock_panel.pack_forget() # UI에 직접 표시하지는 않음

    def create_widgets(self):
        # 상단 프레임 (이미지 로드, 랜드마크 감지, 디버깅 버튼)
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, pady=5)

        tk.Button(top_frame, text="이미지 로드", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="랜드마크 감지", command=self.detect_landmarks).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="눈동자 표시 업데이트", command=self.update_display).pack(side=tk.LEFT, padx=5)

        # 캔버스 프레임
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_original = DebugCanvas(canvas_frame, bg="gray", highlightbackground="black", highlightthickness=1)
        self.canvas_original.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        self.canvas_edited = DebugCanvas(canvas_frame, bg="gray", highlightbackground="black", highlightthickness=1)
        self.canvas_edited.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)

        # 컨트롤 프레임 (클램핑 활성화, 마진 비율)
        control_frame = tk.LabelFrame(self, text="눈동자 이동 제한 설정", padx=5, pady=5)
        control_frame.pack(fill=tk.X, pady=5)

        tk.Checkbutton(control_frame, text="이동 범위 제한 활성화", 
                       variable=self.mock_panel.iris_clamping_enabled, command=self.update_display).pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="제한 마진 비율:").pack(side=tk.LEFT, padx=5)
        self.margin_slider = tk.Scale(control_frame, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                                     variable=self.mock_panel.iris_clamping_margin_ratio, command=lambda v: self.update_display(), length=200)
        self.margin_slider.pack(side=tk.LEFT, padx=5)

    def load_image(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if file_path:
            self.image_path = file_path
            self.pil_image = Image.open(file_path).convert("RGB")
            self.canvas_original.set_image(self.pil_image)
            self.canvas_edited.set_image(self.pil_image.copy()) # 편집용 이미지 복사
            self.landmark_manager.reset(keep_original=False) # 랜드마크 초기화
            self.detect_landmarks() # 이미지 로드 후 바로 랜드마크 감지

    def detect_landmarks(self):
        if self.pil_image:
            landmarks_detected, _ = detect_face_landmarks(self.pil_image)
            if landmarks_detected:
                self.landmark_manager.set_original_face_landmarks(landmarks_detected)
                
                # 원본 눈동자 랜드마크 설정 (_prepare_iris_centers에서 제거되는 iris_contour_indices)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_contour_indices = set(left_iris_indices + right_iris_indices)
                    iris_center_indices = {468, 473}
                    all_iris_indices = sorted(list(iris_contour_indices | iris_center_indices))
                    
                    original_iris_landmarks = [landmarks_detected[i] for i in all_iris_indices if i < len(landmarks_detected)]
                    self.landmark_manager.set_original_iris_landmarks(original_iris_landmarks)
                except ImportError:
                    pass

                # _prepare_iris_centers를 호출하여 눈동자 중심점 초기화 및 클램핑 적용 (임시)
                # 이 부분은 실제 morph_face_by_polygons의 동작을 모방하여 중심점만 업데이트
                img_width, img_height = self.pil_image.size
                original_landmarks_for_core = list(landmarks_detected) # core.py에 전달할 랜드마크 (원본)
                transformed_landmarks_for_core = list(landmarks_detected) # core.py에 전달할 랜드마크 (변형)

                # 더미 중앙 포인트 (초기 감지 위치)
                left_iris_center_init, right_iris_center_init = self.mock_panel._calculate_iris_center(landmarks_detected, left_iris_indices, img_width, img_height), self.mock_panel._calculate_iris_center(landmarks_detected, right_iris_indices, img_width, img_height)

                # _prepare_iris_centers 호출 (클램핑 로직 테스트)
                _, _, _, transformed_points_array, _ = _prepare_iris_centers(
                    original_landmarks_for_core, transformed_landmarks_for_core,
                    left_iris_center_init, right_iris_center_init,
                    left_iris_center_init, right_iris_center_init,
                    img_width, img_height,
                    clamping_enabled=self.mock_panel.iris_clamping_enabled.get(),
                    margin_ratio=self.mock_panel.iris_clamping_margin_ratio.get()
                )
                
                # transformed_points_array의 마지막 두 점이 클램핑 적용된 눈동자 중심점
                if len(transformed_points_array) >= 2:
                    left_center_clamped = tuple(transformed_points_array[-2])
                    right_center_clamped = tuple(transformed_points_array[-1])
                    self.mock_panel._left_iris_center_coord = left_center_clamped
                    self.mock_panel._right_iris_center_coord = right_center_clamped

                self.landmark_manager.set_face_landmarks(landmarks_detected) # 표시용
                self.landmark_manager.set_custom_landmarks(landmarks_detected) # 드래그 등 사용자 수정용
                self.update_display()
            else:
                print("랜드마크를 감지할 수 없습니다.")

    def update_display(self):
        # 이 함수는 MockFaceEditPanel의 update_iris_display를 호출합니다.
        self.mock_panel.update_iris_display()

if __name__ == "__main__":
    app = IrisMovementDebugger()
    app.mainloop()
