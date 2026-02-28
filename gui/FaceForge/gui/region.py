"""
얼굴 편집 패널 - 슬라이더 UI 생성 Mixin
슬라이더 UI 생성 및 탭별 UI 구성을 담당
"""
import tkinter as tk
from tkinter import ttk

from utils.logger import log, debug
from gui.FaceForge.utils.debugs import DEBUG_REGION_PANEL

from .landmark import StateKeys  # 파일 상단 import 확인

import mediapipe as mp

# 각 영역 인덱스를 평탄화(정수 리스트)로 변환
def _flatten_pairs(pairs):
    flat = []
    for pair in pairs:
        if isinstance(pair, (list, tuple)):
            flat.extend(idx for idx in pair if isinstance(idx, int))
        elif isinstance(pair, int):
            flat.append(pair)
    return flat

class RegionPanelMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if DEBUG_REGION_PANEL:
            log("RegionPanelMixin", "init")

        self.alignment_params = {}            
        self.region_params = {}

        self.region_slider_values = {}        
        self.region_slider_meta = {}  # 슬라이더 메타 정보 저장

        self.region_sliders = []
        self.region_labels = []        

    def _ensure_region_entry(self, region_name):
        entry = self.region_params.get(region_name)
        if entry is None:
            entry = {
                "enabled": False,
                "sliders": {
                    "pivot_x": 0.0,
                    "pivot_y": 0.0,
                    "size_x": 1.0,
                    "size_y": 1.0,
                    "move_x": 0.0,
                    "move_y": 0.0,
                },
                "dragged_points": {},
            }
            self.region_params[region_name] = entry
        return entry

    def _store_dragged_point(self, index, coord):
        for _attr, check_name, region_name, indices in self._attr_pairs:
            if any(index in pair for pair in indices):
                entry = self._ensure_region_entry(region_name)
                entry["dragged_points"][index] = coord
                if DEBUG_REGION_PANEL:
                    log("_update_region_runtime_state", f"{region_name}: dragged:{index}, \nentry:{entry}")
                break
 
    def _update_region_runtime_state(self):
        slider_values, conditions = self._get_common_slider_values()
        for attr_name, check_name, region_name, _indices in self._attr_pairs:
            var = getattr(self, attr_name, None)
            enabled = bool(var.get()) if var else False
            entry = self._ensure_region_entry(region_name)
            entry["enabled"] = enabled
            if enabled:
                entry["sliders"] = slider_values.copy()
                if conditions.get("size_x_condition") or conditions.get("size_y_condition") or \
                    conditions.get("pos_x_condition") or conditions.get("pos_y_condition") or \
                    conditions.get("pivot_x_condition") or conditions.get("pivot_y_condition"):
                    entry["applied"] = True
                    
                if DEBUG_REGION_PANEL:
                    log("_update_region_runtime_state", f"{attr_name}: slider:{slider_values}, \nentry:{entry}")

    polygon_color_ix = 0
    polygon_colors = ["green","light green","cyan","light blue","blue","purple","red","orange","brown","pink","magenta","yellow","beige","white","light gray","gray","black"]

    mp_face_mesh = mp.solutions.face_mesh
    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
    LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
    RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
    LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
    RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
    NOSE = list(mp_face_mesh.FACEMESH_NOSE)
    LIPS = list(mp_face_mesh.FACEMESH_LIPS)
    FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
    CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
    TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)

    _attr_pairs = [
        ('show_face_oval', 'Face Oval', 'face_oval', FACE_OVAL),
        ('show_left_eye', 'Left Eye', 'left_eye', LEFT_EYE),
        ('show_right_eye', 'Right Eye', 'right_eye', RIGHT_EYE),
        ('show_left_eyebrow', 'Left Eyebrow', 'left_eyebrow', LEFT_EYEBROW),
        ('show_right_eyebrow', 'Right Eyebrow', 'right_eyebrow', RIGHT_EYEBROW),
        ('show_nose', 'Nose', 'nose', NOSE),
        ('show_lips', 'Lips', 'lips', LIPS),
        ('show_left_iris', 'Left Iris', 'left_iris', LEFT_IRIS),
        ('show_right_iris', 'Right Iris', 'right_iris', RIGHT_IRIS),
        ('show_contours', 'Contours', 'contours', CONTOURS),
        ('show_tesselation', 'Tesselation', 'tesselation', TESSELATION),
    ]

    def _has_region_name(self, regions_name):
        for _, _check, _name, _indices in self._attr_pairs:
            if _name == regions_name:
                return True
        return False

    def _get_region_indices(self, region_name):
        regions = []
        for _, _check, _name, _indices in self._attr_pairs:
            if _name != region_name:
                continue
            regions.append((_name, _indices))
            return regions
        return None

    def _get_region_expanded(self, len_landmarks, region_indices, expansion_level=1):
        
        target_indices = set()
        for pair in region_indices:
            if isinstance(pair, (list, tuple)):
                target_indices.update(pair)
            else:
                target_indices.add(pair)

        # ✅ 확장 레벨에 따라 주변 포인트 추가
        if expansion_level > 0:
            try:
                tesselation = self.TESSELATION
            
                # TESSELATION 그래프 구성
                tesselation_graph = {}
                for idx1, idx2 in tesselation:
                    if idx1 < len_landmarks and idx2 < len_landmarks:
                        if idx1 not in tesselation_graph:
                            tesselation_graph[idx1] = []
                        if idx2 not in tesselation_graph:
                            tesselation_graph[idx2] = []
                        tesselation_graph[idx1].append(idx2)
                        tesselation_graph[idx2].append(idx1)
                
                # 확장 레벨만큼 이웃 포인트 추가
                current_indices = target_indices.copy()
                for level in range(expansion_level):
                    next_level_indices = set()
                    found_in_graph = 0
                    total_neighbors = 0
                    for idx in current_indices:
                        if idx in tesselation_graph:
                            found_in_graph += 1
                            for neighbor in tesselation_graph[idx]:
                                total_neighbors += 1
                                if neighbor < len_landmarks:
                                    next_level_indices.add(neighbor)
                    target_indices.update(next_level_indices)
                    current_indices = next_level_indices
                
            except Exception as exc:
                error("_get_region_expanded", f"확장 실패: {exc}")
                import traceback
                traceback.print_exc()
      
        return list(target_indices)

    def _get_selected_regions(self):
        regions = []
        for attr_name, check_name, region_name, region_indices in self._attr_pairs:
            var = getattr(self, attr_name, None)
            if var is not None and hasattr(var, 'get') and var.get():
                regions.append((region_name, region_indices))
        return regions        

    def _get_selected_regions_expanded(self, len_landmarks, expansion_level=1):
        selected_regions = []
        for attr_name, check_name, region_name, region_indices in self._attr_pairs:
            var = getattr(self, attr_name, None)
            if var is not None and hasattr(var, 'get') and var.get():
                selected_regions.append((region_name, region_indices))

        # ✅ 중복 제거
        target_indices = set()
        for region_name, region_indices in selected_regions:
            # MediaPipe는 연결 쌍을 반환하므로 인덱스 추출
            for pair in region_indices:
                target_indices.update(pair)

        # ✅ 확장 레벨에 따라 주변 포인트 추가
        if expansion_level > 0:
            try:
                tesselation = self.TESSELATION
            
                # TESSELATION 그래프 구성
                tesselation_graph = {}
                for idx1, idx2 in tesselation:
                    if idx1 < len_landmarks and idx2 < len_landmarks:
                        if idx1 not in tesselation_graph:
                            tesselation_graph[idx1] = []
                        if idx2 not in tesselation_graph:
                            tesselation_graph[idx2] = []
                        tesselation_graph[idx1].append(idx2)
                        tesselation_graph[idx2].append(idx1)
                
                # 확장 레벨만큼 이웃 포인트 추가
                current_indices = target_indices.copy()
                for level in range(expansion_level):
                    next_level_indices = set()
                    for idx in current_indices:
                        if idx in tesselation_graph:
                            for neighbor in tesselation_graph[idx]:
                                if neighbor < len_landmarks:
                                    next_level_indices.add(neighbor)
                    target_indices.update(next_level_indices)
                    current_indices = next_level_indices
                    
            except ImportError:
                pass  # MediaPipe 없으면 확장 없음
      
        return list(target_indices)

    def _mark_change_source(self, source):
        if hasattr(self, '_set_change_source'):
            try:
                self._set_change_source(source)
            except Exception:
                pass

    def _get_common_slider_values(self):
        values = {
            'pivot_x': self.region_pivot_x.get(),
            'pivot_y': self.region_pivot_y.get(),
            'size_x': self.region_size_x.get(),
            'size_y': self.region_size_y.get(),
            'position_x': self.region_position_x.get(),
            'position_y': self.region_position_y.get(),
            'expansion_level': self.region_expansion_level.get()
        }
        conditions = {
            'size_x_condition': abs(values['size_x'] - 1.0) >= 0.01,
            'size_y_condition': abs(values['size_y'] - 1.0) >= 0.01,
            'pivot_x_condition': abs(values['pivot_x']) >= 0.1,
            'pivot_y_condition': abs(values['pivot_y']) >= 0.1,
            'pos_x_condition': abs(values['position_x']) >= 0.1,
            'pos_y_condition': abs(values['position_y']) >= 0.1,
        }
        conditions['size_condition'] = conditions['size_x_condition'] or conditions['size_y_condition']
        return values, conditions

    default_sliders = (
        ("pivot_x", 0.0),
        ("pivot_y", 0.0),
        ("size_x", 1.0),
        ("size_y", 1.0),
        ("position_x", 0.0),
        ("position_y", 0.0),
        ("expansion_level", 1),
    )

    def _iter_checkbox_vars(self):
        return (
            getattr(self, "show_face_oval", None),
            getattr(self, "show_left_eye", None),
            getattr(self, "show_right_eye", None),
            getattr(self, "show_left_eyebrow", None),
            getattr(self, "show_right_eyebrow", None),
            getattr(self, "show_nose", None),
            getattr(self, "show_lips", None),
            # getattr(self, "show_upper_lips", None),
            # getattr(self, "show_lower_lips", None),
            getattr(self, "show_left_iris", None),
            getattr(self, "show_right_iris", None),
            getattr(self, "show_contours", None),
            getattr(self, "show_tesselation", None),
        )

    def _reset_region_checkbox(self):
        for var in self._iter_checkbox_vars():
            if var is not None and hasattr(var, "set"):
                var.set(False)

    def _reset_common_sliders(self):        
        getattr(self, 'use_landmark_warping', None).set(False)
        for key, default in self.default_sliders:
            self._set_slider_value(key, default)            

    def _restore_common_sliders_from_region(self, selected_name):
        for _, check_name, region_name, _ in self._attr_pairs:
            if check_name != selected_name:
                continue

            entry = self.region_params.get(region_name)
            if entry and entry.get("applied") and entry.get("sliders"):
                sliders = entry["sliders"]
                for key, default in self.default_sliders:
                    self._set_slider_value(key, sliders.get(key, default))
                return True
                    
            for key, default in self.default_sliders:
                self._set_slider_value(key, default)

        return False


    def on_region_selection_change(self, text=""):
        """부위 선택 변경 시 호출"""
        if DEBUG_REGION_PANEL:
            print(f"[on_region_selection_change]", f"self.current_image={self.current_image is not None}, text={text}")
        
        self._restore_common_sliders_from_region(text)

        # 슬라이더 상태 업데이트
        if hasattr(self, 'update_region_slider_state'):
            self.update_region_slider_state()

        self._mark_change_source('option')
        
        # 랜드마크 표시 업데이트
        if self.current_image is not None:
            if hasattr(self, '_request_face_edit_refresh'):
                self._request_face_edit_refresh(
                    image=True,
                    polygons=self._is_polygon_display_enabled(),
                    pivots=self._is_pivot_display_enabled(),
                    guides=self._is_guides_display_enabled(),
                    bbox=self._is_bbox_frame_display_enabled(),
                )
            else:
                self._refresh_face_edit_display(
                    image=True,
                    polygons=self._is_polygon_display_enabled(),
                    pivots=self._is_pivot_display_enabled(),
                    guides=self._is_guides_display_enabled(),
                    bbox=self._is_bbox_frame_display_enabled(),
                )

    def _handle_slider_drag(self, event, scale, variable, label_text, value_label, default_label):
        """슬라이더 드래그 직접 처리"""
        try:
            slider_width = scale.winfo_width()
            click_x = event.x
            relative_x = max(0, min(click_x, slider_width))

            from_val = scale.cget("from")
            to_val = scale.cget("to")
            val = from_val + (to_val - from_val) * (relative_x / slider_width)

            if "exp" in label_text.lower():
                val = int(val)

            variable.set(val)
            scale.set(val)

            # 244-247번 라인 수정
            if default_label.endswith("%"):
                value_label.config(text=f"{(val * 100):.1f}%")
            else:
                # resolution에 따라 소수점 자리 동적 결정
                if hasattr(scale, 'resolution'):
                    resolution = scale.cget('resolution')
                    #print(f"[resolution]", f"label_text={label_text}, resolution={resolution}")
                    if resolution >= 1:
                        value_label.config(text=f"{int(val)}")
                    elif resolution >= 0.1:
                        value_label.config(text=f"{val:.1f}")
                    elif resolution >= 0.01:
                        value_label.config(text=f"{val:.2f}")
                    else:
                        value_label.config(text=f"{val:.3f}")
                else:
                    # 1. tk.Scale에 resolution=1로 설정했는데 hasattr(scale, 'resolution')가 False 
                    # 2. Tkinter 버그나 특성일 수 있음 
                    # 3. else 분기에서 exp level이 소수점으로 표시됨
                    if "exp" in label_text.lower():
                        value_label.config(text=f"{int(val)}")
                        #print(f"[resolution]", f"label={label_text}, text={value_label.cget('text')}, variable={variable.get()}, value={val:.3f}, final={final_val}")
                    else:
                        value_label.config(text=f"{val:.2f}")

        except Exception:
            pass

    def _format_slider_value(self, name, value):
        meta = getattr(self, "region_slider_meta", {}).get(name)
        
        #print(f"[_format_slider_value]", f"name={name}, value={value}, meta={meta}")
        if not meta:
            return f"{value:.2f}"

        if meta["is_percent"]:
            return f"{value * 100:.1f}%"
        if meta["is_int"]:
            return f"{int(value)}"
    
        res = meta["resolution"]
        if res >= 1:
            return f"{int(value)}"
        if res >= 0.1:
            return f"{value:.1f}"
        if res >= 0.01:
            return f"{value:.2f}"

        return f"{value:.3f}"



    def _set_slider_value(self, name, value):
        var = getattr(self, f"region_{name}")
        var.set(value)
        label = self.region_slider_values.get(name)
        if label:
            textvalue = self._format_slider_value(name, value)
            label.config(text=textvalue)

    def _create_face_region(self, parent):

        # MediaPipe 사용 가능 여부 확인
        try:            
            from gui.FaceForge.utils import landmarks
            mediapipe_available = landmarks.is_available()
        except Exception as e:
            mediapipe_available = False

        # 부위 선택 섹션 추가
        region_frame = tk.LabelFrame(parent, text="Region Selection", padx=5, pady=5)
        region_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        # 체크박스 그리드 배치 (2열로 변경)
        checkbox_frame = tk.Frame(region_frame)
        checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tesselation 상호 배타적 처리 함수
        def handle_tesselation_exclusive():
            """Tesselation과 개별 부위 상호 배타적 선택 처리"""
            if self.show_tesselation.get():
                # Tesselation 선택 시 다른 부위 체크박스 비활성화
                for check in [self.face_oval_check, self.left_eye_check, self.right_eye_check,
                             self.left_eyebrow_check, self.right_eyebrow_check, self.nose_check,
                             self.lips_check, self.left_iris_check,
                             self.right_iris_check, self.contours_check]:
                    if check:
                        check.config(state=tk.DISABLED)
            else:
                # Tesselation 해제 시 다른 부위 체크박스 활성화
                if mediapipe_available:
                    for check in [self.face_oval_check, self.left_eye_check, self.right_eye_check,
                                 self.left_eyebrow_check, self.right_eyebrow_check, self.nose_check,
                                 self.lips_check, self.left_iris_check,
                                 self.right_iris_check, self.contours_check]:
                        if check:
                            check.config(state=tk.NORMAL)
        
        def handle_individual_region_exclusive():
            """개별 부위 선택 시 Tesselation 체크박스 비활성화"""
            has_individual_selected = (self.show_face_oval.get() or self.show_left_eye.get() or
                                      self.show_right_eye.get() or self.show_left_eyebrow.get() or
                                      self.show_right_eyebrow.get() or self.show_nose.get() or
                                      self.show_lips.get() or
                                      self.show_left_iris.get() or self.show_right_iris.get() or
                                      self.show_contours.get())
            
            if has_individual_selected:
                if self.tesselation_check:
                    self.tesselation_check.config(state=tk.DISABLED)
                    # Tesselation이 선택되어 있으면 해제
                    if self.show_tesselation.get():
                        self.show_tesselation.set(False)
            else:
                if self.tesselation_check and mediapipe_available:
                    self.tesselation_check.config(state=tk.NORMAL)        


        # 부위 선택 체크박스 생성 함수
        def create_region_checkbox(parent, text, variable, row, col, exclusive_handler=None):
            def on_check_change():
                if DEBUG_REGION_PANEL:
                    print(f"{'-'*80}","\n[on_check_change] : " )
                if exclusive_handler:
                    exclusive_handler()
                self.on_region_selection_change(text)
            
            check = tk.Checkbutton(
                parent,
                text=text,
                variable=variable,
                command=on_check_change
            )
            check.grid(row=row, column=col, sticky=tk.W, padx=4, pady=0)
            if not mediapipe_available:
                check.config(state=tk.DISABLED)
            return check
        
        # 체크박스 배치 (3열)
        self.left_iris_check = create_region_checkbox(checkbox_frame, "Left Iris", self.show_left_iris, 0, 0, handle_individual_region_exclusive)
        self.right_iris_check = create_region_checkbox(checkbox_frame, "Right Iris", self.show_right_iris, 0, 1, handle_individual_region_exclusive)        
        self.tesselation_check = create_region_checkbox(checkbox_frame, "Tesselation", self.show_tesselation, 0, 2, handle_tesselation_exclusive)

        self.left_eye_check = create_region_checkbox(checkbox_frame, "Left Eye", self.show_left_eye, 1, 0, handle_individual_region_exclusive)
        self.right_eye_check = create_region_checkbox(checkbox_frame, "Right Eye", self.show_right_eye, 1, 1, handle_individual_region_exclusive)
        self.face_oval_check = create_region_checkbox(checkbox_frame, "Face Oval", self.show_face_oval, 1, 2, handle_individual_region_exclusive)

        self.left_eyebrow_check = create_region_checkbox(checkbox_frame, "Left Eyebrow", self.show_left_eyebrow, 2, 0, handle_individual_region_exclusive)
        self.right_eyebrow_check = create_region_checkbox(checkbox_frame, "Right Eyebrow", self.show_right_eyebrow, 2, 1, handle_individual_region_exclusive)                
        self.contours_check = create_region_checkbox(checkbox_frame, "Contours", self.show_contours, 2, 2, handle_individual_region_exclusive)
        
        self.nose_check = create_region_checkbox(checkbox_frame, "Nose", self.show_nose, 3, 0, handle_individual_region_exclusive)
        self.lips_check = create_region_checkbox(checkbox_frame, "Lips", self.show_lips, 3, 1, handle_individual_region_exclusive)

        # def on_color_selected(event):
        #     print(f"{'-'*80}","\n[on_color_selected] : " )
        #     self.polygon_color_ix = self.polygon_colors.index(self.show_polygon_color.get())
        #     self.on_region_selection_change()

        # combo = ttk.Combobox(checkbox_frame, textvariable=self.show_polygon_color, values=self.polygon_colors, state="readonly", width=9)
        # combo.grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        # combo.bind("<<ComboboxSelected>>", on_color_selected )
        # self.polygon_color_combo = combo

        exp_frame = tk.Frame(checkbox_frame)
        exp_frame.grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        
        exp_label = tk.Label(exp_frame, text="level", width=4, anchor=tk.W)
        exp_label.pack(side=tk.LEFT)
        
        exp_spinbox = tk.Spinbox(
            exp_frame,
            from_=0,
            to=15,
            textvariable=self.region_expansion_level,
            width=4,
            command=lambda: self.on_region_selection_change()
        )
        exp_spinbox.pack(side=tk.LEFT, padx=(0, 4))
        self.region_expansion_spinbox = exp_spinbox

        # MediaPipe가 없을 때 안내 메시지
        if not mediapipe_available:
            info_label = tk.Label(
                region_frame,
                text="(MediaPipe가 설치되지 않아 부위 선택을 사용할 수 없습니다)",
                fg="orange",
                font=("", 8)
            )
            info_label.pack(pady=(5, 0))        

    def _create_face_tab(self, notebook):
        """전체 얼굴 탭 UI 생성"""
        tab_frame = tk.Frame(notebook, padx=8, pady=0)
        
        scaled_length = 200
        label_width = 8
        
        # 슬라이더 생성 헬퍼 함수
        def create_slider(parent, name, label_text, variable, from_val, to_val, resolution, default_label="", width=6, default_value=None):
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=(0, 5))
            
            # default_value가 없으면 default_label에서 추론
            if default_value is None:
                if default_label.endswith("%") and "100" in default_label:
                    default_value = 1.0
                elif default_label == "0" or default_label == "":
                    default_value = 0.0
                else:
                    default_value = 0.0
            
            title_label = tk.Label(frame, text=label_text, width=label_width, anchor="e", cursor="hand2")
            title_label.pack(side=tk.LEFT, padx=(0, 4))

            # value_label을 슬라이더 오른쪽에 배치
            value_label = tk.Label(frame, text=default_label, width=width)

            # value_label은 나중에 슬라이더 오른쪽에 배치됨
            self.region_slider_values[name] = value_label
            self.region_slider_meta[name] = {
                "label": value_label,
                "is_percent": default_label.endswith("%"),
                "is_int": "exp" in label_text.lower(),
                "resolution": resolution,
            }

            #print("create_slider", f"{name}, {self.region_slider_meta[name]}")
            
            def on_slider_change(event):
                # 드래그 중에는 라벨만 업데이트 (성능 최적화)
                val = float(value_scale.get())
                variable.set(val)
                value_label.config(text=self._format_slider_value(name, val))
                #print("on_slider_change", f"{name}, {val}")
            
            def on_slider_release(event):
                # 드래그 종료 시 실제 편집 적용
                self.on_warping_change()
            
            def reset_slider(event):
                value_scale.set(default_value)
                variable.set(default_value)
                value_label.config(text=self._format_slider_value(name, default_value))
                self.on_warping_change()        
                return

            value_scale = tk.Scale(
                frame,
                from_=from_val,
                to=to_val,
                resolution=resolution,
                orient=tk.HORIZONTAL,
                variable=variable,
                length=scaled_length,
                showvalue=False,
                takefocus=1,  # 포커스 받도록 설정
                state=tk.NORMAL,  # 명시적으로 활성화
                cursor="hand2"  # 마우스 커서 변경
            )
            value_scale.pack(side=tk.LEFT, padx=(0, 5))
            value_label.pack(side=tk.LEFT)
            
            # 슬라이더 상태 확인
            value_scale.config(state=tk.NORMAL) #, command=lambda v: on_slider_change(v))
            
            # 드래그 이벤트 바인딩
            value_scale.bind("<B1-Motion>", on_slider_change)
            value_scale.bind("<ButtonRelease-1>", on_slider_release)  # 드래그 종료 시 적용
            value_scale.bind("<ButtonRelease-3>", on_slider_release)  # 오른쪽 버튼도 지원
            
            title_label.bind("<Button-1>", reset_slider)

            self.region_labels.append(value_label)
            self.region_sliders.append(value_scale)

            return value_label, value_scale
        
        # 공통 슬라이더 섹션 추가
        adjustment_frame = tk.LabelFrame(tab_frame, text="Region Adjustment", padx=5, pady=5)
        adjustment_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        # 공통 슬라이더 6개 생성 (Size X, Size Y 분리)
        create_slider(adjustment_frame, "pivot_x", "pivot X:", self.region_pivot_x, -100, 100, 0.01, "0.00", default_value=0.0)
        create_slider(adjustment_frame, "pivot_y", "pivot Y:", self.region_pivot_y, -100, 100, 0.01, "0.00", default_value=0.0)
        create_slider(adjustment_frame, "size_x", "size X:", self.region_size_x, 0.50, 1.50, 0.001, "100.0%", default_value=1.0)
        create_slider(adjustment_frame, "size_y", "size Y:", self.region_size_y, 0.50, 1.50, 0.001, "100.0%", default_value=1.0)
        create_slider(adjustment_frame, "position_x", "move X:", self.region_position_x, -20, 20, 0.01, "0.00", default_value=0.0)
        create_slider(adjustment_frame, "position_y", "move y:", self.region_position_y, -20, 20, 0.01, "0.00", default_value=0.0)
        #create_slider(adjustment_frame, "expansion_level", "exp level:", self.region_expansion_level, 0, 15, 1, "1", default_value=1)
        
        self.region_labels.append(self.region_expansion_level)

        # 폴리곤 확장 슬라이더
        #self.region_expansion_label = create_slider(adjustment_frame, "exp level:", self.region_expansion_level, 0, 15, 1, "1", default_value=1)
        
        # 초기 상태: 아무 부위도 선택되지 않으면 슬라이더 비활성화
        def update_slider_state():
            """선택된 부위에 따라 슬라이더 활성/비활성화"""
            has_selection = (self.show_face_oval.get() or self.show_left_eye.get() or
                           self.show_right_eye.get() or self.show_left_eyebrow.get() or
                           self.show_right_eyebrow.get() or self.show_nose.get() or
                           self.show_lips.get() or self.show_upper_lips.get() or self.show_lower_lips.get() or
                           self.show_left_iris.get() or self.show_right_iris.get() or
                           self.show_contours.get() or self.show_tesselation.get() )
            
            state = tk.NORMAL if has_selection else tk.DISABLED
            for slider in self.region_sliders:
                slider.config(state=state)
        
        # 슬라이더 상태 업데이트를 위한 함수 (나중에 morphing.py에서 호출)
        self.update_region_slider_state = update_slider_state
        
        # 초기 상태 설정
        update_slider_state()
        
        return tab_frame


    def collect_region_edit_state(self):
        slider_values, _conditions = self._get_common_slider_values()
        state = self.landmark_manager.get_landmark_state()
        current_landmarks = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_FACE_LANDMARKS]
        dragged_indices = self.landmark_manager.get_dragged_indices()
    
        def is_index_in_region(idx, region_pairs):
            for a, b in region_pairs:
                if idx == a or idx == b:
                    return True
            return False
    
        regions_data = {}
        for attr_name, check_name, region_name, region_indices in self._attr_pairs:
            var = getattr(self, attr_name, None)
            enabled = bool(var.get()) if var else False
            entry = {"enabled": enabled}
            if enabled:
                entry["indices"] = region_indices
                entry["sliders"] = slider_values.copy()
                entry["dragged_points"] = {
                    idx: current_landmarks[idx]
                    for idx in dragged_indices
                    if is_index_in_region(idx, region_indices)
                }
            regions_data[region_name] = entry

            #entry["dragged_points"] 생성 부분을 str(idx) 대신 idx 그대로 저장하도록 수정(@gui/region.py#626-651).
            #JSON 저장이 필요하면 파일로 쓰기 직전에만 key = str(idx) 변환을 수행하거나, default=str 옵션을 줍니다.            
    
        return {
            "version": 1,
            "regions": regions_data,
            "global": {
                "selected_regions": self._get_selected_regions(),
                "slider_defaults": slider_values,
            },
        }

    def save_region_edit_state(self):
        from utils import settings
        
        parameters_dir = settings._get_parameters_dir(self.current_image_path)
        filename = settings._get_parameters_filename(self.current_image_path)
        save_path = os.path.join(parameters_dir, filename)

        import json, os
        
        data = self.collect_region_edit_state()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)