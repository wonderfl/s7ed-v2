"""
비슷한 얼굴 찾기 전용 패널
이미지와 비슷한 얼굴을 찾아서 목록으로 표시하는 기능
"""
import os
import glob
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import platform

import utils.kaodata_image as kaodata_image
import utils.face_landmarks as face_landmarks
from gui.face_extract.similar import SimilarFaceManagerMixin

# Windows에서 경고음 비활성화를 위한 함수
def _silent_messagebox(title, message, icon='info', buttons='ok'):
    """경고음 없이 메시지 박스 표시"""
    if platform.system() == 'Windows':
        try:
            import ctypes
            from ctypes import wintypes
            
            # Windows API 상수
            MB_OK = 0x00000000
            MB_OKCANCEL = 0x00000001
            MB_YESNO = 0x00000004
            MB_ICONINFORMATION = 0x00000040
            MB_ICONWARNING = 0x00000030
            MB_ICONERROR = 0x00000010
            MB_ICONQUESTION = 0x00000020
            MB_TASKMODAL = 0x00002000  # 시스템 모달 대신 태스크 모달 사용 (경고음 방지)
            
            # 아이콘 선택
            icon_flag = MB_ICONINFORMATION
            if icon == 'warning':
                icon_flag = MB_ICONWARNING
            elif icon == 'error':
                icon_flag = MB_ICONERROR
            elif icon == 'question':
                icon_flag = MB_ICONQUESTION
            
            # 버튼 선택
            button_flag = MB_OK
            if buttons == 'yesno':
                button_flag = MB_YESNO
            elif buttons == 'okcancel':
                button_flag = MB_OKCANCEL
            
            # 경고음 비활성화를 위해 태스크 모달 사용
            result = ctypes.windll.user32.MessageBoxW(
                0,  # hWnd (NULL)
                message,
                title,
                icon_flag | button_flag | MB_TASKMODAL
            )
            
            # 결과 변환
            if buttons == 'yesno':
                return result == 6  # IDYES = 6
            elif buttons == 'okcancel':
                return result == 1  # IDOK = 1
            return True
        except:
            # 실패 시 기본 messagebox 사용
            if buttons == 'yesno':
                return messagebox.askyesno(title, message)
            elif buttons == 'okcancel':
                return messagebox.askokcancel(title, message)
            elif icon == 'error':
                messagebox.showerror(title, message)
            elif icon == 'warning':
                messagebox.showwarning(title, message)
            else:
                messagebox.showinfo(title, message)
            return True
    else:
        # Windows가 아니면 기본 messagebox 사용
        if buttons == 'yesno':
            return messagebox.askyesno(title, message)
        elif buttons == 'okcancel':
            return messagebox.askokcancel(title, message)
        elif icon == 'error':
            messagebox.showerror(title, message)
        elif icon == 'warning':
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
        return True


class FaceSimilarPanel(SimilarFaceManagerMixin, tk.Toplevel):
    """비슷한 얼굴 찾기 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("비슷한 얼굴 찾기")
        self.resizable(True, True)
        
        # 현재 선택된 이미지
        self.current_image_path = None
        
        # 얼굴 추출 폴더 경로
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
        
        # 좌우 배치 프레임
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽: 파일 선택 UI
        left_frame = self._create_file_selection_ui(content_frame)
        
        # 오른쪽: 검색 결과 UI
        right_frame = self._create_result_ui(content_frame)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
        
        # 위젯 생성 완료 후 파일 목록 로드
        self.after(100, self.refresh_file_list)
    
    def _create_file_selection_ui(self, parent):
        """파일 선택 UI 생성"""
        file_frame = tk.LabelFrame(parent, text="이미지 파일 선택", padx=5, pady=5)
        file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))  # expand=True로 확장 가능
        
        # 현재 선택된 이미지 미리보기 (우선적으로 크기 조정)
        preview_frame = tk.LabelFrame(file_frame, text="선택된 이미지", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 파일 목록 프레임 (프리뷰 다음에 배치, expand 없음)
        list_frame = tk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, pady=(0, 5))
        
        # 리스트박스와 스크롤바
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 리스트박스 선택 이벤트
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        # 버튼 프레임
        button_frame = tk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=10)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="폴더 선택", command=self.browse_folder, width=10)
        btn_browse.pack(side=tk.LEFT)
        
        # 캔버스로 미리보기 표시 (프레임 크기에 맞춰 동적 조정)
        self.current_image_canvas = tk.Canvas(preview_frame, bg="gray")
        self.current_image_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 프레임 크기 변경 시 이미지 다시 그리기
        preview_frame.bind("<Configure>", self._on_preview_frame_resize)
        
        # 확대 상태 변수
        self.zoom_scale = 1.0
        self.zoom_base_size = (384, 480)
        self.original_image = None
        self.original_image_size = None
        self._last_zoom_scale = 1.0
        
        # 확대/축소 버튼
        zoom_frame = tk.Frame(preview_frame)
        zoom_frame.pack(pady=(5, 0))
        
        btn_zoom_in = tk.Button(zoom_frame, text="확대", command=self._zoom_in, width=8)
        btn_zoom_in.pack(side=tk.LEFT, padx=2)
        
        btn_zoom_out = tk.Button(zoom_frame, text="축소", command=self._zoom_out, width=8)
        btn_zoom_out.pack(side=tk.LEFT, padx=2)
        
        btn_zoom_reset = tk.Button(zoom_frame, text="원래대로", command=self._zoom_reset, width=8)
        btn_zoom_reset.pack(side=tk.LEFT, padx=2)
        
        # 마우스 드래그로 이동
        self.current_image_canvas.bind("<Button-1>", self._on_canvas_click)
        self.current_image_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.current_image_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.current_image_canvas.config(cursor="hand2")
        
        self.current_image_photo = None
        self.canvas_drag_start_x = None
        self.canvas_drag_start_y = None
        self.canvas_image_pos_x = 192  # 초기 중앙 위치
        self.canvas_image_pos_y = 240
        self.canvas_image_start_x = None  # 드래그 시작 시 이미지 위치
        self.canvas_image_start_y = None
        
        return file_frame
    
    def _create_result_ui(self, parent):
        """검색 결과 UI 생성"""
        result_frame = tk.LabelFrame(parent, text="비슷한 얼굴 목록", padx=5, pady=5)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH)  # expand 제거하여 너비 고정
        
        # 상단: 버튼과 상태 라벨
        top_frame = tk.Frame(result_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_find_similar_faces = tk.Button(top_frame, text="비슷한 얼굴 찾기", command=self.on_find_similar_faces, width=15, bg="#9C27B0", fg="white")
        btn_find_similar_faces.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_find_similar_clothing = tk.Button(top_frame, text="비슷한 옷 찾기", command=self.on_find_similar_clothing, width=15, bg="#4CAF50", fg="white")
        btn_find_similar_clothing.pack(side=tk.LEFT, padx=(0, 10))
        
        self.similar_faces_status_label = tk.Label(top_frame, text="", fg="gray", font=("", 8))
        self.similar_faces_status_label.pack(side=tk.LEFT)
        
        # 스크롤 가능한 프레임
        canvas_frame = tk.Frame(result_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 캔버스와 스크롤바
        self.similar_faces_canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.similar_faces_canvas.yview)
        self.similar_faces_scrollable_frame = tk.Frame(self.similar_faces_canvas)
        
        self.similar_faces_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.similar_faces_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 스크롤 가능한 프레임을 캔버스에 배치
        self.similar_faces_canvas.create_window((0, 0), window=self.similar_faces_scrollable_frame, anchor=tk.NW)
        
        # 스크롤 영역 업데이트
        self.similar_faces_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.similar_faces_canvas.configure(scrollregion=self.similar_faces_canvas.bbox("all"))
        )
        
        # 마우스 휠 바인딩
        def _on_mousewheel(event):
            self.similar_faces_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.similar_faces_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 초기 상태: 비어있음
        self.similar_faces_list = []
        
        return result_frame
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기
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
    
    def browse_folder(self):
        """폴더 선택"""
        import globals as gl
        import utils.config as config
        
        initial_dir = self.face_extract_dir if self.face_extract_dir else None
        if initial_dir and not os.path.exists(initial_dir):
            initial_dir = None
        
        folder_path = filedialog.askdirectory(
            title="이미지 폴더 선택",
            initialdir=initial_dir
        )
        
        if folder_path:
            # 절대 경로로 변환
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            self.face_extract_dir = folder_path
            gl._face_extract_dir = folder_path
            config.save_config()
            
            self.refresh_file_list()
    
    def on_file_select(self, event):
        """파일 선택 시 호출"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        try:
            # 선택된 파일명 가져오기
            filename = self.file_listbox.get(selection[0])
            
            # 이미지 디렉토리 경로 가져오기
            if self.face_extract_dir and os.path.exists(self.face_extract_dir):
                png_dir = self.face_extract_dir
            else:
                png_dir = kaodata_image.get_png_dir()
            
            file_path = os.path.join(png_dir, filename)
            
            if not os.path.exists(file_path):
                messagebox.showerror("에러", "파일을 찾을 수 없습니다.")
                return
            
            # 이미지 로드 및 미리보기 표시
            self.current_image_path = file_path
            self._show_current_image_preview(file_path)
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지 로드 실패:\n{e}")
    
    def _on_preview_frame_resize(self, event=None):
        """프리뷰 프레임 크기 변경 시 이미지 다시 그리기"""
        if hasattr(self, 'current_image_path') and self.current_image_path:
            self._show_current_image_preview(self.current_image_path)
    
    def _show_current_image_preview(self, file_path):
        """현재 선택된 이미지 미리보기 표시 (원본 이미지 전체, 크기 조정 없이)"""
        try:
            # 기존 이미지 삭제
            if self.current_image_photo:
                self.current_image_canvas.delete("all")
            
            # 원본 이미지 로드
            self.original_image = Image.open(file_path)
            if self.original_image.mode != 'RGB':
                self.original_image = self.original_image.convert('RGB')
            
            # 원본 이미지 크기 저장
            img_width, img_height = self.original_image.size
            self.original_image_size = (img_width, img_height)
            
            # 캔버스 크기 (동적으로 가져오기)
            self.current_image_canvas.update_idletasks()  # 크기 정보 갱신
            canvas_width = self.current_image_canvas.winfo_width()
            canvas_height = self.current_image_canvas.winfo_height()
            
            # 캔버스 크기가 0이면 기본값 사용
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 384
                canvas_height = 480
            
            # 확대 비율 적용하여 실제 표시할 이미지 크기 계산
            display_width = int(img_width * self.zoom_scale)
            display_height = int(img_height * self.zoom_scale)
            
            # 원본 이미지를 확대 비율로 리사이즈 (비율 유지)
            resized_image = self.original_image.resize((display_width, display_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
            
            # 기존 이미지 위치 저장 (확대/축소 또는 새 이미지 선택 시 위치 유지)
            if hasattr(self.current_image_canvas, 'image_id') and self.current_image_canvas.image_id:
                try:
                    coords = self.current_image_canvas.coords(self.current_image_canvas.image_id)
                    if coords and len(coords) >= 2:
                        # 확대 비율 변화에 따라 위치 조정
                        old_zoom = getattr(self, '_last_zoom_scale', 1.0)
                        if old_zoom > 0:
                            scale_factor = self.zoom_scale / old_zoom
                            self.canvas_image_pos_x = coords[0] * scale_factor
                            self.canvas_image_pos_y = coords[1] * scale_factor
                except:
                    pass
            
            # 이미지 위치 초기화 (최초 로드 시에만)
            if not hasattr(self, 'canvas_image_pos_x') or self.canvas_image_pos_x is None:
                # 이미지 중앙을 캔버스 중앙에 배치
                self.canvas_image_pos_x = canvas_width // 2
                self.canvas_image_pos_y = canvas_height // 2
            
            # 위치를 캔버스 범위 내로 제한 (이미지 크기에 맞게 조정, 위치 유지)
            half_width = display_width // 2
            half_height = display_height // 2
            
            if display_width <= canvas_width:
                # 이미지가 캔버스보다 작으면 중앙에 배치 (위치 유지하지 않음)
                self.canvas_image_pos_x = canvas_width // 2
            else:
                # 이미지가 캔버스보다 크면 경계 내로 제한 (위치 유지하되 범위 내로)
                self.canvas_image_pos_x = max(half_width, min(canvas_width - half_width, self.canvas_image_pos_x))
            
            if display_height <= canvas_height:
                # 이미지가 캔버스보다 작으면 중앙에 배치 (위치 유지하지 않음)
                self.canvas_image_pos_y = canvas_height // 2
            else:
                # 이미지가 캔버스보다 크면 경계 내로 제한 (위치 유지하되 범위 내로)
                self.canvas_image_pos_y = max(half_height, min(canvas_height - half_height, self.canvas_image_pos_y))
            
            # 기존 이미지 삭제
            self.current_image_canvas.delete("all")
            
            # 캔버스에 표시
            image_id = self.current_image_canvas.create_image(
                self.canvas_image_pos_x, 
                self.canvas_image_pos_y, 
                anchor=tk.CENTER, 
                image=photo
            )
            self.current_image_photo = photo  # 참조 유지
            self.current_image_canvas.image_photo = photo  # 참조 유지
            self.current_image_canvas.display_image = resized_image  # 표시용 이미지 저장
            self.current_image_canvas.image_id = image_id  # 이미지 ID 저장
            self.current_image_canvas.display_size = (display_width, display_height)  # 표시 크기 저장
            
            # 현재 확대 비율 저장
            self._last_zoom_scale = self.zoom_scale
            
        except Exception as e:
            print(f"[비슷한얼굴] 미리보기 로드 실패: {e}")
            self.current_image_canvas.delete("all")
            self.current_image_canvas.update_idletasks()
            canvas_width = self.current_image_canvas.winfo_width()
            canvas_height = self.current_image_canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 384
                canvas_height = 480
            self.current_image_canvas.create_text(
                canvas_width // 2, canvas_height // 2, 
                text="[이미지 로드 실패]", 
                fill="white",
                font=("", 10)
            )
    
    def on_find_similar_faces(self):
        """비슷한 얼굴 찾기 버튼 클릭 시 호출"""
        if not self.current_image_path:
            messagebox.showwarning("경고", "이미지를 먼저 선택하세요.")
            return
        
        # 기존 목록 클리어
        for widget in self.similar_faces_scrollable_frame.winfo_children():
            widget.destroy()
        
        self.similar_faces_status_label.config(text="검색 중...", fg="blue")
        self.update()
        
        try:
            # 비슷한 얼굴 찾기 (얼굴만 비교)
            similar_faces = self.find_similar_faces(
                reference_image_path=self.current_image_path, 
                top_n=10,
                include_clothing=False
            )
            
            if not similar_faces:
                self.similar_faces_status_label.config(text="비슷한 얼굴을 찾을 수 없습니다.", fg="gray")
                return
            
            # 결과 표시
            self.similar_faces_list = similar_faces
            self._display_similar_faces(similar_faces)
            
            self.similar_faces_status_label.config(
                text=f"{len(similar_faces)}개 얼굴을 찾았습니다.",
                fg="green"
            )
            
        except Exception as e:
            messagebox.showerror("에러", f"비슷한 얼굴 검색 실패:\n{e}")
            self.similar_faces_status_label.config(text="검색 실패", fg="red")
    
    def on_find_similar_clothing(self):
        """옷만 찾기 버튼 클릭 시 호출"""
        if not self.current_image_path:
            messagebox.showwarning("경고", "이미지를 먼저 선택하세요.")
            return
        
        # 기존 목록 클리어
        for widget in self.similar_faces_scrollable_frame.winfo_children():
            widget.destroy()
        
        self.similar_faces_status_label.config(text="검색 중...", fg="blue")
        self.update()
        
        try:
            # 기준 이미지의 옷 특징 추출
            reference_clothing = self._extract_clothing_features_for_image(self.current_image_path)
            if reference_clothing is None:
                messagebox.showwarning("경고", "옷 영역을 찾을 수 없습니다.")
                self.similar_faces_status_label.config(text="옷 영역 없음", fg="gray")
                return
            
            # 이미지 디렉토리 경로 가져오기
            if self.face_extract_dir and os.path.exists(self.face_extract_dir):
                png_dir = self.face_extract_dir
            else:
                png_dir = kaodata_image.get_png_dir()
            
            if not os.path.exists(png_dir):
                return []
            
            # 모든 이미지 파일 찾기
            import glob
            image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.tiff', '*.tif', '*.webp']
            image_files = []
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(png_dir, ext)))
                image_files.extend(glob.glob(os.path.join(png_dir, ext.upper())))
            
            # 중복 제거
            image_files = list(set(os.path.normpath(f) for f in image_files))
            
            # 기준 이미지는 제외
            image_files = [f for f in image_files if f != self.current_image_path]
            
            # 모든 이미지의 옷 특징 추출 및 비교
            similarities = []
            total = len(image_files)
            
            for idx, image_path in enumerate(image_files):
                try:
                    clothing_features = self._extract_clothing_features_for_image(image_path)
                    if clothing_features is not None:
                        similarity = face_landmarks.calculate_clothing_similarity(reference_clothing, clothing_features)
                        similarities.append((similarity, image_path))
                    
                    # 진행률 업데이트
                    if hasattr(self, 'similar_faces_status_label'):
                        progress = int((idx + 1) / total * 100)
                        self.similar_faces_status_label.config(
                            text=f"검색 중... {idx + 1}/{total} ({progress}%)"
                        )
                        self.update()
                        
                except Exception as e:
                    print(f"[비슷한옷] 이미지 처리 실패 ({image_path}): {e}")
                    continue
            
            # 유사도가 높은 순으로 정렬
            similarities.sort(key=lambda x: x[0], reverse=True)
            
            # 90% 이상 유사도만 필터링
            similar_faces = [(sim, path) for sim, path in similarities if sim >= 0.9]
            
            if not similar_faces:
                self.similar_faces_status_label.config(text="비슷한 옷을 찾을 수 없습니다. (90% 이상)", fg="gray")
                return
            
            # 결과 표시
            self.similar_faces_list = similar_faces
            self._display_similar_faces(similar_faces)
            
            self.similar_faces_status_label.config(
                text=f"{len(similar_faces)}개 옷을 찾았습니다.",
                fg="green"
            )
            
        except Exception as e:
            messagebox.showerror("에러", f"옷만 검색 실패:\n{e}")
            self.similar_faces_status_label.config(text="검색 실패", fg="red")
    
    def _extract_clothing_features_for_image(self, image_path):
        """이미지에서 옷 특징만 추출 (캐싱 포함)"""
        # 캐시 확인 (features 폴더 내)
        from gui.face_extract.similar import _get_features_dir, _get_features_cache_filename
        features_dir = _get_features_dir(image_path)
        cache_filename = _get_features_cache_filename(image_path, '_clothing_only')
        cache_key = os.path.join(features_dir, cache_filename)
        cached_features = self._load_features_cache_by_key(image_path, cache_key)
        if cached_features is not None:
            return cached_features
        
        try:
            # 이미지 로드
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 옷 특징 벡터 추출
            features = face_landmarks.extract_clothing_features_vector(image)
            
            # 캐시 저장
            if features is not None:
                self._save_features_cache_by_key(image_path, cache_key, features)
            
            return features
            
        except Exception as e:
            print(f"[비슷한옷] 옷 특징 추출 실패 ({image_path}): {e}")
            return None
    
    def _display_similar_faces(self, similar_faces):
        """비슷한 얼굴 목록 표시"""
        thumbnail_size = (96, 120)  # 썸네일 크기
        
        for idx, (similarity, file_path) in enumerate(similar_faces):
            # 각 항목을 위한 프레임
            item_frame = tk.Frame(self.similar_faces_scrollable_frame, relief=tk.RAISED, borderwidth=1)
            item_frame.pack(fill=tk.X, padx=2, pady=2)
            
            # 썸네일 이미지 로드 및 표시
            try:
                image = Image.open(file_path)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # 썸네일 생성
                image.thumbnail(thumbnail_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # 썸네일 라벨
                thumbnail_label = tk.Label(item_frame, image=photo)
                thumbnail_label.image = photo  # 참조 유지
                thumbnail_label.pack(side=tk.LEFT, padx=5, pady=5)
                
                # 클릭 이벤트 바인딩
                thumbnail_label.bind("<Button-1>", lambda e, path=file_path: self._load_similar_face_image(path))
                
            except Exception as e:
                print(f"[비슷한얼굴] 썸네일 로드 실패 ({file_path}): {e}")
                # 썸네일 로드 실패 시 빈 라벨
                empty_label = tk.Label(item_frame, text="[이미지 없음]", width=12, height=15, bg="gray")
                empty_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 정보 프레임
            info_frame = tk.Frame(item_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 파일명
            filename = os.path.basename(file_path)
            filename_label = tk.Label(info_frame, text=filename, font=("", 9), anchor="w")
            filename_label.pack(fill=tk.X)
            
            # 유사도 점수
            similarity_percent = similarity * 100
            similarity_label = tk.Label(
                info_frame, 
                text=f"유사도: {similarity_percent:.1f}%", 
                font=("", 8),
                fg="blue",
                anchor="w"
            )
            similarity_label.pack(fill=tk.X)
            
            # 파일 존재 여부 표시
            status_frame = tk.Frame(info_frame)
            status_frame.pack(fill=tk.X, pady=(2, 0))
            
            # 피처 파일 확인
            from gui.face_extract.similar import _get_features_dir, _get_features_cache_filename
            features_dir = _get_features_dir(file_path)
            has_features = False
            for suffix in ['', '_clothing', '_clothing_only']:
                cache_filename = _get_features_cache_filename(file_path, suffix)
                cache_path = os.path.join(features_dir, cache_filename)
                if os.path.exists(cache_path):
                    has_features = True
                    break
            
            # 파라미터 파일 확인
            import utils.config as config_util
            parameters_dir = config_util._get_parameters_dir(file_path)
            params_filename = config_util._get_parameters_filename(file_path)
            params_path = os.path.join(parameters_dir, params_filename)
            has_params = os.path.exists(params_path)
            
            # 추출 이미지 확인
            import re
            original_filename = os.path.basename(file_path)
            base_name = os.path.splitext(original_filename)[0]
            base_name = re.sub(r'^[A-Za-z]+_', '', base_name)
            png_filename = f"{base_name}_s7.png"
            image_dir = os.path.dirname(file_path)
            faces_dir = os.path.join(image_dir, "faces")
            png_file_path = os.path.join(faces_dir, png_filename)
            has_extracted = os.path.exists(png_file_path)
            
            # 상태 표시
            status_texts = []
            if has_features:
                status_texts.append("피처")
            if has_params:
                status_texts.append("파라미터")
            if has_extracted:
                status_texts.append("추출")
            
            if status_texts:
                status_text = " | ".join(status_texts)
                status_label = tk.Label(
                    status_frame,
                    text=status_text,
                    fg="green",
                    anchor="w"
                )
                status_label.pack(side=tk.LEFT)
            else:
                status_label = tk.Label(
                    status_frame,
                    text="없음",
                    font=("", 7),
                    fg="gray",
                    anchor="w"
                )
                status_label.pack(side=tk.LEFT)
            
            # 삭제 버튼 (클로저 문제 방지를 위해 함수로 감싸기)
            def make_delete_handler(img_path, frame):
                def handler():
                    self._delete_result_image(img_path, frame)
                return handler
            
            btn_delete = tk.Button(
                item_frame, 
                text="삭제", 
                command=make_delete_handler(file_path, item_frame),
                width=8,
            )
            btn_delete.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # 더블클릭으로 이미지 선택
            item_frame.bind("<Double-Button-1>", lambda e, path=file_path: self._load_similar_face_image(path))
            filename_label.bind("<Double-Button-1>", lambda e, path=file_path: self._load_similar_face_image(path))
            similarity_label.bind("<Double-Button-1>", lambda e, path=file_path: self._load_similar_face_image(path))
        
        # 스크롤 영역 업데이트
        self.similar_faces_canvas.update_idletasks()
        self.similar_faces_canvas.configure(scrollregion=self.similar_faces_canvas.bbox("all"))
    
    def _load_similar_face_image(self, file_path):
        """비슷한 얼굴 이미지 클릭 시 해당 이미지 선택"""
        if not os.path.exists(file_path):
            messagebox.showerror("에러", "파일을 찾을 수 없습니다.")
            return
        
        # 파일 목록에서 해당 파일 찾기
        filename = os.path.basename(file_path)
        for i in range(self.file_listbox.size()):
            if self.file_listbox.get(i) == filename:
                self.file_listbox.selection_clear(0, tk.END)
                self.file_listbox.selection_set(i)
                self.file_listbox.see(i)
                break
        
        # 이미지 선택 (on_file_select가 자동으로 호출됨)
        self.current_image_path = file_path
        self._show_current_image_preview(file_path)
    
    def _delete_result_image(self, file_path, item_frame):
        """검색 결과에서 이미지 삭제"""
        # 파일 경로 정규화
        file_path = os.path.normpath(file_path)
        
        # 경고음 비활성화
        original_bell = self.bell
        self.bell = lambda: None
        
        # root 객체의 bell도 비활성화
        root = self._get_root()
        original_root_bell = None
        if root and hasattr(root, 'bell'):
            original_root_bell = root.bell
            root.bell = lambda: None
        
        try:
            if not os.path.exists(file_path):
                _silent_messagebox("에러", "파일을 찾을 수 없습니다.", icon='error')
                return
            
            filename = os.path.basename(file_path)
            result = _silent_messagebox(
                "확인",
                f"다음 파일을 삭제하시겠습니까?\n\n{filename}\n\n경로: {file_path}\n\n관련된 추출 이미지, features, parameters 파일도 함께 삭제됩니다.",
                icon='question',
                buttons='yesno'
            )
        finally:
            # 원래대로 복원
            self.bell = original_bell
            if original_root_bell is not None and root:
                root.bell = original_root_bell
        
        if not result:
            return
        
        # 디버깅: 삭제할 파일 경로 출력
        print(f"[비슷한얼굴] 삭제 시작: {file_path}")
        
        try:
            deleted_files = []
            
            # 이미지 파일 삭제
            try:
                os.remove(file_path)
                deleted_files.append("이미지 파일")
            except Exception as e:
                # 경고음 비활성화
                original_bell = self.bell
                self.bell = lambda: None
                root = self._get_root()
                original_root_bell = None
                if root and hasattr(root, 'bell'):
                    original_root_bell = root.bell
                    root.bell = lambda: None
                try:
                    _silent_messagebox("에러", f"이미지 파일 삭제 실패:\n{e}", icon='error')
                finally:
                    self.bell = original_bell
                    if original_root_bell is not None and root:
                        root.bell = original_root_bell
                return
            
            # 추출 이미지 파일 삭제 (faces 폴더 내)
            import re
            original_filename = os.path.basename(file_path)
            base_name = os.path.splitext(original_filename)[0]
            # 앞부분의 영문자와 '_' 제거 (예: ABC_something -> something)
            base_name = re.sub(r'^[A-Za-z]+_', '', base_name)
            png_filename = f"{base_name}_s7.png"
            
            # 원본 이미지와 같은 디렉토리의 faces 폴더 확인
            image_dir = os.path.dirname(file_path)
            faces_dir = os.path.join(image_dir, "faces")
            png_file_path = os.path.join(faces_dir, png_filename)
            
            if os.path.exists(png_file_path):
                try:
                    os.remove(png_file_path)
                    deleted_files.append("추출 이미지 (faces 폴더)")
                except Exception as e:
                    print(f"[비슷한얼굴] 추출 이미지 삭제 실패 ({png_file_path}): {e}")
            
            # features 캐시 파일 삭제
            from gui.face_extract.similar import _get_features_dir, _get_features_cache_filename
            features_dir = _get_features_dir(file_path)
            for suffix in ['', '_clothing', '_clothing_only']:
                cache_filename = _get_features_cache_filename(file_path, suffix)
                cache_path = os.path.join(features_dir, cache_filename)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                        deleted_files.append(f"features 캐시 ({suffix or '기본'})")
                    except Exception as e:
                        print(f"[비슷한얼굴] features 캐시 삭제 실패 ({cache_path}): {e}")
            
            # parameters 파일 삭제
            import utils.config as config_util
            parameters_dir = config_util._get_parameters_dir(file_path)
            params_filename = config_util._get_parameters_filename(file_path)
            params_path = os.path.join(parameters_dir, params_filename)
            if os.path.exists(params_path):
                try:
                    os.remove(params_path)
                    deleted_files.append("parameters 파일")
                except Exception as e:
                    print(f"[비슷한얼굴] parameters 파일 삭제 실패 ({params_path}): {e}")
            
            # 결과 목록에서 항목 제거
            item_frame.destroy()
            
            # 파일 목록에서도 제거 (정확한 경로로 매칭)
            filename = os.path.basename(file_path)
            # 이미지 디렉토리 경로 가져오기
            if self.face_extract_dir and os.path.exists(self.face_extract_dir):
                png_dir = self.face_extract_dir
            else:
                png_dir = kaodata_image.get_png_dir()
            
            # 파일 목록에서 정확한 파일만 제거
            for i in range(self.file_listbox.size()):
                listbox_filename = self.file_listbox.get(i)
                if listbox_filename == filename:
                    # 경로도 확인하여 정확히 일치하는 경우만 삭제
                    listbox_file_path = os.path.normpath(os.path.join(png_dir, listbox_filename))
                    if listbox_file_path == file_path:
                        self.file_listbox.delete(i)
                        print(f"[비슷한얼굴] 파일 목록에서 제거: {listbox_filename}")
                        break
            
            # 현재 선택된 이미지가 삭제된 경우 초기화
            if self.current_image_path == file_path:
                self.current_image_path = None
                self.current_image_canvas.delete("all")
                self.current_image_photo = None
            
            # 스크롤 영역 업데이트
            self.similar_faces_canvas.update_idletasks()
            self.similar_faces_canvas.configure(scrollregion=self.similar_faces_canvas.bbox("all"))
            
            # 경고음 없이 완료 메시지 표시
            _silent_messagebox("완료", f"파일이 삭제되었습니다.\n\n삭제된 항목:\n" + "\n".join(f"- {f}" for f in deleted_files), icon='info')
            
        except Exception as e:
            # 경고음 비활성화
            original_bell = self.bell
            self.bell = lambda: None
            root = self._get_root()
            original_root_bell = None
            if root and hasattr(root, 'bell'):
                original_root_bell = root.bell
                root.bell = lambda: None
            try:
                _silent_messagebox("에러", f"삭제 실패:\n{e}", icon='error')
            finally:
                self.bell = original_bell
                if original_root_bell is not None and root:
                    root.bell = original_root_bell
    
    def _get_root(self):
        """루트 윈도우 가져오기"""
        widget = self
        while widget:
            if isinstance(widget, tk.Tk):
                return widget
            widget = widget.master
        # Tk 객체를 찾을 수 없으면 _default_root 사용
        try:
            return tk._default_root
        except:
            return None
    
    def _zoom_in(self):
        """이미지 확대"""
        if self.zoom_scale < 3.0:
            # 현재 이미지 위치 저장
            if hasattr(self.current_image_canvas, 'image_id') and self.current_image_canvas.image_id:
                coords = self.current_image_canvas.coords(self.current_image_canvas.image_id)
                if coords:
                    self.canvas_image_pos_x = coords[0]
                    self.canvas_image_pos_y = coords[1]
            
            self.zoom_scale = min(self.zoom_scale * 1.5, 3.0)
            if self.current_image_path:
                self._show_current_image_preview(self.current_image_path)
    
    def _zoom_out(self):
        """이미지 축소"""
        if self.zoom_scale > 0.5:
            # 현재 이미지 위치 저장
            if hasattr(self.current_image_canvas, 'image_id') and self.current_image_canvas.image_id:
                coords = self.current_image_canvas.coords(self.current_image_canvas.image_id)
                if coords:
                    self.canvas_image_pos_x = coords[0]
                    self.canvas_image_pos_y = coords[1]
            
            self.zoom_scale = max(self.zoom_scale / 1.5, 0.5)
            if self.current_image_path:
                self._show_current_image_preview(self.current_image_path)
    
    def _zoom_reset(self):
        """이미지 확대/축소 초기화"""
        self.zoom_scale = 1.0
        self.canvas_image_pos_x = 192
        self.canvas_image_pos_y = 240
        if self.current_image_path:
            self._show_current_image_preview(self.current_image_path)
    
    def _on_canvas_click(self, event):
        """캔버스 클릭 시 드래그 시작"""
        # 현재 이미지 위치 확인 (이미지 ID가 있으면 coords에서 가져오기)
        if hasattr(self.current_image_canvas, 'image_id') and self.current_image_canvas.image_id:
            try:
                coords = self.current_image_canvas.coords(self.current_image_canvas.image_id)
                if coords and len(coords) >= 2:
                    current_x = coords[0]
                    current_y = coords[1]
                else:
                    current_x = self.canvas_image_pos_x if hasattr(self, 'canvas_image_pos_x') else 192
                    current_y = self.canvas_image_pos_y if hasattr(self, 'canvas_image_pos_y') else 240
            except:
                current_x = self.canvas_image_pos_x if hasattr(self, 'canvas_image_pos_x') else 192
                current_y = self.canvas_image_pos_y if hasattr(self, 'canvas_image_pos_y') else 240
        else:
            current_x = self.canvas_image_pos_x if hasattr(self, 'canvas_image_pos_x') else 192
            current_y = self.canvas_image_pos_y if hasattr(self, 'canvas_image_pos_y') else 240
        
        # 클릭 시점의 마우스 위치와 이미지 위치 저장
        self.canvas_drag_start_x = event.x
        self.canvas_drag_start_y = event.y
        self.canvas_image_start_x = current_x
        self.canvas_image_start_y = current_y
    
    def _on_canvas_drag(self, event):
        """캔버스 드래그 시 이미지 이동"""
        # 드래그 시작 정보 확인
        if (self.canvas_drag_start_x is None or 
            self.canvas_drag_start_y is None or
            self.canvas_image_start_x is None or
            self.canvas_image_start_y is None):
            return
        
        if not self.current_image_photo:
            return
        
        # 이동 거리 계산
        dx = event.x - self.canvas_drag_start_x
        dy = event.y - self.canvas_drag_start_y
        
        # 드래그 시작 시점의 이미지 위치 + 이동 거리로 새로운 위치 계산
        new_x = self.canvas_image_start_x + dx
        new_y = self.canvas_image_start_y + dy
        
        # 캔버스 크기 (동적으로 가져오기)
        self.current_image_canvas.update_idletasks()
        canvas_width = self.current_image_canvas.winfo_width()
        canvas_height = self.current_image_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 384
            canvas_height = 480
        
        # 표시된 이미지 크기
        if hasattr(self.current_image_canvas, 'display_size'):
            display_width, display_height = self.current_image_canvas.display_size
        else:
            # 표시 크기를 모르면 원본 이미지 크기 기준으로 추정
            if hasattr(self, 'original_image_size') and self.original_image_size:
                img_width, img_height = self.original_image_size
                display_width = int(img_width * self.zoom_scale)
                display_height = int(img_height * self.zoom_scale)
            else:
                display_width = canvas_width
                display_height = canvas_height
        
        half_width = display_width // 2
        half_height = display_height // 2
        
        # 경계 제한: 이미지가 캔버스보다 작으면 중앙에 배치, 크면 일부만 보이도록 이동 가능
        if display_width <= canvas_width:
            # 이미지가 캔버스보다 작으면 중앙에 배치
            new_x = canvas_width // 2
        else:
            # 이미지가 캔버스보다 크면 경계 내로 제한 (일부만 보여도 이동 가능)
            min_visible_ratio = 0.05  # 최소 5%는 보여야 함
            min_visible_width = display_width * min_visible_ratio
            new_x = max(canvas_width - (display_width - min_visible_width), 
                       min(display_width - min_visible_width, new_x))
        
        if display_height <= canvas_height:
            # 이미지가 캔버스보다 작으면 중앙에 배치
            new_y = canvas_height // 2
        else:
            # 이미지가 캔버스보다 크면 경계 내로 제한 (일부만 보여도 이동 가능)
            min_visible_ratio = 0.05  # 최소 5%는 보여야 함
            min_visible_height = display_height * min_visible_ratio
            new_y = max(canvas_height - (display_height - min_visible_height), 
                       min(display_height - min_visible_height, new_y))
        
        # 이미지 위치 업데이트 (coords로 직접 업데이트)
        if hasattr(self.current_image_canvas, 'image_id') and self.current_image_canvas.image_id:
            try:
                self.current_image_canvas.coords(self.current_image_canvas.image_id, new_x, new_y)
            except Exception as e:
                # coords 업데이트 실패 시 다시 그리기
                print(f"[비슷한얼굴] coords 업데이트 실패: {e}")
                self.current_image_canvas.delete("all")
                image_id = self.current_image_canvas.create_image(
                    new_x, 
                    new_y, 
                    anchor=tk.CENTER, 
                    image=self.current_image_photo
                )
                self.current_image_canvas.image_id = image_id
        else:
            # 이미지 ID가 없으면 다시 그리기
            self.current_image_canvas.delete("all")
            image_id = self.current_image_canvas.create_image(
                new_x, 
                new_y, 
                anchor=tk.CENTER, 
                image=self.current_image_photo
            )
            self.current_image_canvas.image_id = image_id
        
        # 현재 이미지 위치 업데이트
        self.canvas_image_pos_x = new_x
        self.canvas_image_pos_y = new_y
    
    def _on_canvas_release(self, event):
        """캔버스 마우스 버튼 놓음"""
        self.canvas_drag_start_x = None
        self.canvas_drag_start_y = None
        self.canvas_image_start_x = None
        self.canvas_image_start_y = None
    
    def on_close(self):
        """창 닫기"""
        self.destroy()


def show_face_similar_panel(parent=None):
    """비슷한 얼굴 찾기 패널 표시"""
    # 경고음 비활성화
    original_bell = None
    if parent and hasattr(parent, 'bell'):
        original_bell = parent.bell
        parent.bell = lambda: None
    
    root = parent
    while root and not isinstance(root, tk.Tk):
        root = getattr(root, 'master', None)
    if root is None:
        try:
            root = tk._default_root
        except:
            pass
    
    original_root_bell = None
    if root and hasattr(root, 'bell'):
        original_root_bell = root.bell
        root.bell = lambda: None
    
    try:
        panel = FaceSimilarPanel(parent)
        panel.transient(parent)  # 부모 창에 종속
        return panel
    finally:
        # 원래대로 복원
        if original_bell is not None and parent:
            parent.bell = original_bell
        if original_root_bell is not None and root:
            root.bell = original_root_bell
