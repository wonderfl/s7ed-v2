"""
얼굴 편집 패널 - 파일 관리 Mixin
파일 선택, 로드 관련 기능을 담당
"""
import os
import math
import time
import json
import glob
import tkinter as tk
from tkinter import filedialog, messagebox

from pathlib import Path
from datetime import datetime, timezone

from gui.FaceForge.utils import landmarks as utilmarks
from gui.FaceForge.utils import settings

from .landmark import StateKeys

from utils.logger import log, debug, info, error, log
from gui.FaceForge.utils.debugs import DEBUG_FILES, DEBUG_GUIDE_LINES

class FileManagerMixin:
    """파일 관리 기능 Mixin"""
    
    def _create_file_selection_ui(self, parent):
        """파일 선택 UI 생성"""
        file_frame = tk.LabelFrame(parent, text="이미지 파일 선택", padx=5, pady=5)
        file_frame.pack(fill=tk.BOTH, expand=False)
        
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
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=15)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="찾아보기...", command=self.browse_file, width=15)
        btn_browse.pack(side=tk.LEFT)

        self.has_parameter = tk.Button(button_frame, text="파라미터", width=15, state="disabled")
        self.has_parameter.pack(side=tk.LEFT)
        
        return file_frame
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        if DEBUG_FILES:
            print("[refresh_file_list]",f": face_edit_dir: {self.face_edit_dir}")

        # file_listbox가 없으면 (팝업창이 아직 열리지 않았으면) 스킵
        if not hasattr(self, 'file_listbox') or self.file_listbox is None:
            return
        
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            png_dir = self.face_edit_dir
        else:
            png_dir = "."
        
        if not png_dir or not os.path.exists(png_dir):
            self.file_listbox.insert(0, f"디렉토리를 찾을 수 없습니다: {png_dir}")
            return
        
        # 지원하는 이미지 파일 확장자
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.jfif', '*.gif', '*.bmp', '*.tiff', '*.tif', '*.webp']
        
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
        if DEBUG_FILES:
            print("[on_file_select]",f":called.. ")
        
        selection = self.file_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        filename = self.file_listbox.get(index)

        # 파일 경로 구성
        png_dir = "."
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            png_dir = self.face_edit_dir
        file_path = os.path.join(png_dir, filename)
        
        if DEBUG_FILES:
            debug("on_file_select", f"filename: {filename}, file_path: {file_path},  face_edit_dir: {self.face_edit_dir}")
        if os.path.exists(file_path):
            result = self.load_image(file_path)
            if True == result:
                self.has_parameter.config(state="normal")
            else:
                self.has_parameter.config(state="disabled")
    
    def browse_file(self):
        """파일 선택 대화상자"""
        if self.face_edit_dir and os.path.exists(self.face_edit_dir):
            initial_dir = self.face_edit_dir
        else:
            initial_dir = "."
        
        file_path = filedialog.askopenfilename(
            title="이미지 파일 선택",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.jfif *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_path:
            source_dir = os.path.dirname(file_path)
            if not os.path.isabs(source_dir):
                source_dir = os.path.abspath(source_dir)
            self.face_edit_dir = source_dir
            settings.save_settings(self)
            
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
        if DEBUG_FILES:
            info("load_image",
                f"file_path: {file_path}, "
                f"face_edit_dir: {self.face_edit_dir}"
            )
        try:
            from PIL import Image
            img = Image.open(file_path)
            self.current_image = img
            self.current_image_path = file_path

            # 원본 이미지 저장
            self.original_image = img.copy()
            self.original_image_path = file_path

            self._stable_base_scale = 1.0
            self._stable_base_display_width = img.size[0]
            self._stable_base_display_height = img.size[1]
            
            # 확대/축소 비율 초기화
            if not hasattr(self, 'zoom_scale_original'):
                self.zoom_scale_original = 1.0
            
            # 원본 이미지 기본 크기 초기화
            if not hasattr(self, 'original_image_base_size'):
                self.original_image_base_size = None

            self.label_image_size.config(text=f"{img.width} x {img.height}")

            self._reset_region_checkbox()
            if hasattr(self, "_reset_common_sliders"):
                self._reset_common_sliders()            

            self._last_warping_state_signature = None
            self.region_params.clear()            # 부위별 슬라이더/드래그 상태 초기화
            
            # 랜드마크 초기화 (새 이미지 로드 시)
            # LandmarkManager 사용하여 초기화
            self.landmark_manager.reset(keep_original=False)
            
            self._reset_alignment_params()
            need_warping = self.load_parameters(file_path)
            if need_warping:
                landmarks = self.landmark_manager.get_original_face_landmarks()
            else:
                params = self.alignment_params if need_warping else self._get_alignment_params()
                detected, landmarks = utilmarks.detect_face_landmarks(img, params)
                if detected:
                    self.landmark_manager.set_original_landmarks(landmarks, img.width, img.height)
                    # ✅ 현재 편집 상태도 원본으로 초기화
                    self.landmark_manager.set_current_landmarks(landmarks.copy(), reason="load_image")

                    # ✅ landmark_state 업데이트
                    self.landmark_manager.set_state_value(
                        StateKeys.SECTION_ORIGINAL,
                        StateKeys.KEY_FACE_LANDMARKS,
                        landmarks[:468] if len(landmarks) >= 468 else landmarks
                    )
                    self.landmark_manager.set_state_value(
                        StateKeys.SECTION_CURRENT,
                        StateKeys.KEY_FACE_LANDMARKS,
                        landmarks[:468].copy() if len(landmarks) >= 468 else landmarks.copy()
                    )

            angle = self._get_guide_axis_angle(landmarks, img.size)
            if angle is not None:
                self.label_face_axis.config(text=f"{math.degrees(angle):.1f}°")

            is_warping_enabled = self.use_landmark_warping.get()
            if need_warping and is_warping_enabled:
                self.on_warping_change()

            if DEBUG_GUIDE_LINES:
                _original_landmarks = self.landmark_manager.get_original_face_landmarks()
                _edited_landmarks = self.landmark_manager.get_face_landmarks()
                debug("load_image",
                    f"landmarks={len(landmarks)}, detected: {detected}, "
                    f"_original_face_landmarks: {len(_original_landmarks) if _original_landmarks else -1}, "
                    f"face_landmarks: {len(_edited_landmarks) if _edited_landmarks else -1}"
                )
            
            # 미리보기 업데이트
            polygons_enabled = False
            if hasattr(self, '_is_polygon_display_enabled'):
                try:
                    polygons_enabled = self._is_polygon_display_enabled()
                except Exception:  # pylint: disable=broad-except
                    polygons_enabled = False

            pivots_enabled = False
            if hasattr(self, '_is_pivot_display_enabled'):
                try:
                    pivots_enabled = self._is_pivot_display_enabled()
                except pivots_enabled:  # pylint: disable=broad-except
                    polygons_enabled = False                    

            guides_enabled = False
            if hasattr(self, '_is_guides_display_enabled'):
                try:
                    guides_enabled = self._is_guides_display_enabled()
                except Exception:  # pylint: disable=broad-except
                    guides_enabled = False

            bbox_enabled = False
            if hasattr(self, '_is_bbox_frame_display_enabled'):
                try:
                    bbox_enabled = self._is_bbox_frame_display_enabled()
                except Exception:  # pylint: disable=broad-except
                    bbox_enabled = False                    

            if hasattr(self, 'update_face_edit_display'):
                self.update_face_edit_display(
                    image=True,
                    polygons=polygons_enabled,
                    pivots=pivots_enabled,
                    guides=guides_enabled,
                    bbox=bbox_enabled,
                    force_original=True,
                )
            else:
                if hasattr(self, 'show_original_preview'):
                    self.show_original_preview()
            
            #self.show_image_popup(img)

            filename = os.path.basename(file_path)
            self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            #messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
            return False
        
        return need_warping

    def save_image(self, base_path: str):
        """편집본을 base_path 기준으로 저장, 중복 시 _1, _2 …"""
        
        current = getattr(self, "current_image", None)
        if current is None:
            error("save_current_image", "편집된 이미지가 없습니다.")
            return
    
        path = Path(base_path)
        stem = path.stem
        suffix = path.suffix or ".png"

        candidate = path
        counter = 1
        while candidate.exists():
            candidate = path.with_name(f"{stem}_{counter}{suffix}")
            counter += 1
    
        try:

            current.save(candidate)
            log("save_current_image", f"Saved: {candidate}")

        except Exception as exc:
            error("save_current_image", f"저장 실패: {exc}")

    def load_parameters(self, image_path: str) -> bool:
        params_dir = Path(image_path).parent / "parameters"
        json_path = params_dir / f"{Path(image_path).stem}.warp.json"

        print(json_path)
        if not json_path.exists():
            return False
    
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.alignment_params = data.get("alignments", {})            
            self._set_alignment_params()
            if self.alignment_params:
                self.status_var.set("Alignment params loaded. Re-detecting...")
                self._detect_apply_alignment()

            # 새 헬퍼: 드래그 포인트/인덱스 복원
            self.region_params = data.get("regions", {})
            self.update_region_slider_state()            
            applied = self._restore_dragged_points_from_region_params()
            if applied:
                self.status_var.set("Dragged points restored.")

            log("load_parameters", f"current[ {self.get_bbox_lips(self.landmark_manager.get_current_landmarks()) }")

            return True
        except Exception as exc:
            error("load_parameters", f"불러오기 실패: {exc}")
            return False



    def save_parameters(self, base_path: str):
        """편집본을 base_path 기준으로 저장, 중복 시 _1, _2 …"""
        
        path = Path(base_path)
        candidate = path
    
        try:

            timestamp = time.time()
            timestamp_iso = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

            original_name = getattr(self, "current_image_path", None)
            alignment_params = self._get_alignment_params()

            data = {
                "version": 1,
                "alignments": alignment_params,
                "regions": self.region_params,              # 부위별 enabled/sliders/dragged_points
                "global": {
                    "original_image": os.path.basename(original_name) if original_name else None,
                    "timestamp": timestamp,
                    "timestamp_iso": timestamp_iso,
                },
            }

            # JSON 파일 저장
            params_dir = Path(candidate).parent / "parameters"
            params_dir.mkdir(parents=True, exist_ok=True)

            json_path = params_dir / f"{candidate.stem}.warp.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_var.set(f"저장 완료: {os.path.basename(json_path)}")
            
        except Exception as exc:
            self.status_var.set("저장 실패")
            error("save_parameters", f"저장 실패: {exc}")

    def _restore_dragged_points_from_region_params(self) -> bool:
        lm = getattr(self, "landmark_manager", None)
        if lm is None or not self.region_params:
            return False

        restored = False
        state = lm.get_landmark_state()
        current = state[StateKeys.SECTION_CURRENT][StateKeys.KEY_FACE_LANDMARKS]

        if current is None and lm.has_original_face_landmarks():
            current = list(lm.get_original_face_landmarks())
            lm.set_current_landmarks(current, reason="load_parameters")

        lm.clear_dragged_indices()

        for entry in self.region_params.values():
            dragged = entry.get("dragged_points") or {}
            for idx_str, coord in dragged.items():
                idx = int(idx_str)
                if current is None or not (0 <= idx < len(current)):
                    continue
                current[idx] = tuple(coord)
                lm.mark_as_dragged(idx)
                restored = True
                #print(f"restored: {idx}, {coord}")

        if restored:
            lm.set_state_value(StateKeys.SECTION_CURRENT,
                            StateKeys.KEY_FACE_LANDMARKS, current)
            lm.set_state_value(StateKeys.SECTION_CURRENT,
                            StateKeys.KEY_DRAGGED_INDICES,
                            lm.get_dragged_indices())
        return restored            