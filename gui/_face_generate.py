"""
얼굴 생성 전용 패널 - 여러 얼굴 합성 및 파트 조합
"""
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import utils.config as config
import utils.face_landmarks as face_landmarks
import utils.face_generation as face_generation

class FaceGeneratePanel(tk.Toplevel):
    """얼굴 생성 전용 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 생성")
        self.resizable(False, False)
        
        # 생성 모드 (morphing: 합성, parts: 파트 조합)
        self.generation_mode = tk.StringVar(value="morphing")
        
        # 얼굴 합성 관련 변수
        self.face_images = []  # 선택된 얼굴 이미지 리스트
        self.face_weights = []  # 각 얼굴의 가중치
        
        # 얼굴 파트 조합 관련 변수
        self.part_sources = {
            'left_eye': None,
            'right_eye': None,
            'nose': None,
            'mouth': None,
            'face_outline': None,
            'skin': None
        }
        
        # 생성된 이미지
        self.generated_image = None
        
        # 미리보기 이미지
        self.tk_image_generated = None
        self.image_created_generated = None
        
        # 얼굴 생성 폴더 경로
        import globals as gl
        self.face_generate_dir = gl._face_extract_dir if gl._face_extract_dir else None
        
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
        
        # 오른쪽: 생성 설정 프레임
        settings_frame = tk.LabelFrame(top_frame, text="얼굴 생성 설정", padx=5, pady=5)
        settings_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 생성 모드 선택 UI
        self._create_mode_selection_ui(settings_frame)
        
        # 얼굴 합성 UI (Phase 3)
        self._create_morphing_ui(settings_frame)
        
        # 얼굴 파트 조합 UI (Phase 3)
        self._create_parts_ui(settings_frame)
        
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
        
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 리스트박스 이벤트 바인딩
        self.file_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_selection_change())
        
        # 버튼 프레임
        button_frame = tk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=12)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="찾아보기...", command=self.browse_file, width=12)
        btn_browse.pack(side=tk.LEFT)
        
        return file_frame
    
    def _create_mode_selection_ui(self, parent):
        """생성 모드 선택 UI"""
        mode_frame = tk.LabelFrame(parent, text="생성 모드", padx=5, pady=5)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 합성 모드 라디오 버튼
        rb_morphing = tk.Radiobutton(
            mode_frame,
            text="얼굴 합성 (Face Morphing)",
            variable=self.generation_mode,
            value="morphing",
            command=self.on_mode_change
        )
        rb_morphing.pack(side=tk.LEFT, padx=(0, 10))
        
        # 파트 조합 모드 라디오 버튼
        rb_parts = tk.Radiobutton(
            mode_frame,
            text="얼굴 파트 조합",
            variable=self.generation_mode,
            value="parts",
            command=self.on_mode_change
        )
        rb_parts.pack(side=tk.LEFT)
    
    def _create_morphing_ui(self, parent):
        """얼굴 합성 UI"""
        morphing_frame = tk.LabelFrame(parent, text="얼굴 합성", padx=5, pady=5)
        morphing_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 선택된 얼굴 목록
        list_label = tk.Label(morphing_frame, text="선택된 얼굴:", anchor="w")
        list_label.pack(fill=tk.X, pady=(0, 5))
        
        # 선택된 얼굴 리스트박스
        list_frame = tk.Frame(morphing_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.selected_faces_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=4)
        self.selected_faces_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.selected_faces_listbox.yview)
        
        # 버튼 프레임
        button_frame = tk.Frame(morphing_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        btn_add = tk.Button(button_frame, text="추가", command=self.add_selected_faces, width=10)
        btn_add.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_remove = tk.Button(button_frame, text="제거", command=self.remove_selected_face, width=10)
        btn_remove.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_clear = tk.Button(button_frame, text="전체 제거", command=self.clear_faces, width=10)
        btn_clear.pack(side=tk.LEFT)
        
        # 합성 버튼
        btn_generate = tk.Button(
            morphing_frame,
            text="얼굴 합성",
            command=self.generate_morphing,
            width=20,
            bg="#2196F3",
            fg="white"
        )
        btn_generate.pack(fill=tk.X)
    
    def _create_parts_ui(self, parent):
        """얼굴 파트 조합 UI"""
        parts_frame = tk.LabelFrame(parent, text="얼굴 파트 조합", padx=5, pady=5)
        parts_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 파트별 소스 선택
        parts = [
            ('left_eye', '왼쪽 눈'),
            ('right_eye', '오른쪽 눈'),
            ('nose', '코'),
            ('mouth', '입'),
            ('face_outline', '얼굴 윤곽'),
            ('skin', '피부')
        ]
        
        self.part_labels = {}
        for part_key, part_name in parts:
            frame = tk.Frame(parts_frame)
            frame.pack(fill=tk.X, pady=(0, 3))
            
            tk.Label(frame, text=f"{part_name}:", width=12, anchor="e").pack(side=tk.LEFT, padx=(0, 5))
            
            part_label = tk.Label(frame, text="(선택 안 됨)", fg="gray", anchor="w")
            part_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.part_labels[part_key] = part_label
            
            btn_select = tk.Button(frame, text="선택", command=lambda k=part_key: self.select_part_source(k), width=8)
            btn_select.pack(side=tk.LEFT, padx=(5, 0))
        
        # 생성 버튼
        btn_generate = tk.Button(
            parts_frame,
            text="파트 조합 생성",
            command=self.generate_parts,
            width=20,
            bg="#9C27B0",
            fg="white"
        )
        btn_generate.pack(fill=tk.X, pady=(5, 0))
    
    def _create_preview_ui(self, parent):
        """미리보기 UI 생성"""
        preview_frame = tk.LabelFrame(parent, text=f"미리보기 ({self.original_image_path})", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 이미지 크기: 288x360
        preview_width = 288
        preview_height = 360
        
        # 중앙: 생성된 이미지
        center_frame = tk.Frame(preview_frame)
        center_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        center_top_frame = tk.Frame(center_frame)
        center_top_frame.pack(fill=tk.X)
        
        self.label_generated = tk.Label(center_top_frame, text="생성된 이미지", font=("", 9))
        self.label_generated.pack(side=tk.LEFT)
        
        btn_save = tk.Button(center_top_frame, text="PNG 저장", command=self.save_png, width=12, bg="#4CAF50", fg="white")
        btn_save.pack(side=tk.LEFT, padx=(10, 0))
        
        self.canvas_generated = tk.Canvas(
            center_frame,
            width=preview_width,
            height=preview_height,
            bg="gray"
        )
        self.canvas_generated.pack(padx=5, pady=5)
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_generate_dir and os.path.exists(self.face_generate_dir):
            png_dir = self.face_generate_dir
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
    
    def browse_file(self):
        """파일 선택 대화상자"""
        if self.face_generate_dir and os.path.exists(self.face_generate_dir):
            initial_dir = self.face_generate_dir
        else:
            initial_dir = kaodata_image.get_png_dir()
            if not os.path.exists(initial_dir):
                initial_dir = None
        
        file_paths = filedialog.askopenfilenames(
            title="이미지 파일 선택 (여러 개 선택 가능)",
            filetypes=[
                ("이미지 파일", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.tif *.webp"),
                ("PNG 파일", "*.png"),
                ("모든 파일", "*.*")
            ],
            initialdir=initial_dir
        )
        
        if file_paths:
            import globals as gl
            import utils.config as config
            source_dir = os.path.dirname(file_paths[0])
            if not os.path.isabs(source_dir):
                source_dir = os.path.abspath(source_dir)
            self.face_generate_dir = source_dir
            gl._face_extract_dir = source_dir
            config.save_config()
            
            self.refresh_file_list()
            
            # 선택한 파일들을 리스트박스에서 찾아서 선택
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                for i in range(self.file_listbox.size()):
                    if self.file_listbox.get(i) == filename:
                        self.file_listbox.selection_set(i)
                        break
    
    def on_file_selection_change(self):
        """파일 선택 변경 이벤트"""
        # 리스트박스에서 선택된 파일들을 표시만 (추가하지 않음)
        pass
    
    def on_mode_change(self):
        """생성 모드 변경 시 호출"""
        # 모드에 따라 UI 표시/숨김
        # TODO: 모드별 UI 표시/숨김 처리
        pass
    
    def add_selected_faces(self):
        """선택된 얼굴들을 추가"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "추가할 이미지를 선택하세요.")
            return
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_generate_dir and os.path.exists(self.face_generate_dir):
            png_dir = self.face_generate_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        
        added_count = 0
        for index in selection:
            filename = self.file_listbox.get(index)
            file_path = os.path.join(png_dir, filename)
            
            if os.path.exists(file_path) and file_path not in self.face_images:
                self.face_images.append(file_path)
                self.face_weights.append(1.0)  # 기본 가중치
                self.selected_faces_listbox.insert(tk.END, filename)
                added_count += 1
        
        if added_count > 0:
            self.status_label.config(text=f"{added_count}개 얼굴 추가됨", fg="green")
        else:
            self.status_label.config(text="추가할 얼굴이 없습니다", fg="orange")
    
    def remove_selected_face(self):
        """선택된 얼굴 제거"""
        selection = self.selected_faces_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "제거할 얼굴을 선택하세요.")
            return
        
        # 역순으로 제거 (인덱스 변경 방지)
        for index in reversed(selection):
            self.selected_faces_listbox.delete(index)
            del self.face_images[index]
            del self.face_weights[index]
        
        self.status_label.config(text="얼굴 제거됨", fg="green")
    
    def clear_faces(self):
        """모든 얼굴 제거"""
        self.selected_faces_listbox.delete(0, tk.END)
        self.face_images.clear()
        self.face_weights.clear()
        self.status_label.config(text="모든 얼굴 제거됨", fg="green")
    
    def generate_morphing(self):
        """얼굴 합성 생성"""
        if len(self.face_images) < 2:
            messagebox.showwarning("경고", "얼굴 합성을 하려면 최소 2개 이상의 얼굴이 필요합니다.")
            return
        
        try:
            self.status_label.config(text="얼굴 합성 중...", fg="blue")
            self.update()
            
            # 얼굴 이미지 로드
            face_imgs = []
            for file_path in self.face_images:
                img = Image.open(file_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                face_imgs.append(img)
            
            # 얼굴 합성
            self.generated_image = face_generation.morph_faces(face_imgs, weights=self.face_weights)
            
            # 미리보기 업데이트
            self.show_generated_preview()
            
            self.status_label.config(text=f"얼굴 합성 완료 ({len(self.face_images)}개 얼굴)", fg="green")
            
        except Exception as e:
            print(f"[얼굴생성] 얼굴 합성 실패: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("에러", f"얼굴 합성 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def select_part_source(self, part_key):
        """파트 소스 선택"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "파트 소스로 사용할 이미지를 선택하세요.")
            return
        
        # 첫 번째 선택된 파일 사용
        index = selection[0]
        filename = self.file_listbox.get(index)
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_generate_dir and os.path.exists(self.face_generate_dir):
            png_dir = self.face_generate_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        file_path = os.path.join(png_dir, filename)
        
        if os.path.exists(file_path):
            self.part_sources[part_key] = file_path
            part_names = {
                'left_eye': '왼쪽 눈',
                'right_eye': '오른쪽 눈',
                'nose': '코',
                'mouth': '입',
                'face_outline': '얼굴 윤곽',
                'skin': '피부'
            }
            self.part_labels[part_key].config(text=f"선택됨: {filename}", fg="green")
            self.status_label.config(text=f"{part_names[part_key]} 소스 선택: {filename}", fg="green")
    
    def generate_parts(self):
        """얼굴 파트 조합 생성"""
        # 최소한 하나의 파트는 선택되어야 함
        selected_parts = [k for k, v in self.part_sources.items() if v is not None]
        if not selected_parts:
            messagebox.showwarning("경고", "최소한 하나의 파트를 선택하세요.")
            return
        
        try:
            self.status_label.config(text="파트 조합 생성 중...", fg="blue")
            self.update()
            
            # 파트 이미지 로드
            part_images = {}
            for part_key, file_path in self.part_sources.items():
                if file_path and os.path.exists(file_path):
                    img = Image.open(file_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    part_images[part_key] = img
            
            # 파트 조합
            self.generated_image = face_generation.combine_face_parts(part_images)
            
            # 미리보기 업데이트
            self.show_generated_preview()
            
            self.status_label.config(text=f"파트 조합 완료 ({len(selected_parts)}개 파트)", fg="green")
            
        except Exception as e:
            print(f"[얼굴생성] 파트 조합 실패: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("에러", f"파트 조합 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def show_generated_preview(self):
        """생성된 이미지 미리보기 표시"""
        if self.generated_image is None:
            if self.image_created_generated:
                self.canvas_generated.delete(self.image_created_generated)
                self.image_created_generated = None
            return
        
        try:
            # 이미지 리사이즈 (미리보기용, 288x360)
            preview_size = (288, 360)
            resized = self.generated_image.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_generated = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_generated:
                self.canvas_generated.delete(self.image_created_generated)
            
            self.image_created_generated = self.canvas_generated.create_image(
                144,  # 288 / 2
                180,  # 360 / 2
                image=self.tk_image_generated
            )
        except Exception as e:
            print(f"[얼굴생성] 생성된 이미지 표시 실패: {e}")
    
    def save_png(self):
        """생성된 이미지를 PNG 파일로 저장"""
        if self.generated_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        try:
            # 파일명 생성
            if self.generation_mode.get() == "morphing":
                base_name = f"face_morphing_{len(self.face_images)}faces"
            else:
                base_name = "face_parts_combined"
            
            png_filename = f"{base_name}.png"
            
            # 저장 폴더 경로 결정
            if self.face_generate_dir and os.path.exists(self.face_generate_dir):
                save_dir = self.face_generate_dir
            else:
                save_dir = kaodata_image.get_png_dir()
            
            # 파일 경로
            file_path = os.path.join(save_dir, png_filename)
            
            # 중복 방지
            counter = 1
            while os.path.exists(file_path):
                png_filename = f"{base_name}_{counter}.png"
                file_path = os.path.join(save_dir, png_filename)
                counter += 1
            
            # PNG로 저장
            self.generated_image.save(file_path, "PNG")
            
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

def show_face_generate_panel(parent=None):
    """얼굴 생성 패널 표시"""
    panel = FaceGeneratePanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    return panel
