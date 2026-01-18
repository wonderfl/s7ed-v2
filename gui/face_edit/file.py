"""
얼굴 편집 패널 - 파일 관리 Mixin
파일 선택, 로드 관련 기능을 담당
"""
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox

import utils.kaodata_image as kaodata_image
import utils.config as config


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
        
        btn_refresh = tk.Button(button_frame, text="새로고침", command=self.refresh_file_list, width=12)
        btn_refresh.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(button_frame, text="찾아보기...", command=self.browse_file, width=12)
        btn_browse.pack(side=tk.LEFT)
        
        return file_frame
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        # file_listbox가 없으면 (팝업창이 아직 열리지 않았으면) 스킵
        if not hasattr(self, 'file_listbox') or self.file_listbox is None:
            return
        
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
            from PIL import Image
            img = Image.open(file_path)
            self.current_image = img
            self.current_image_path = file_path
            
            # 확대/축소 비율과 위치는 유지 (초기화하지 않음)
            # zoom_scale_original은 초기화하지 않고 유지
            if not hasattr(self, 'zoom_scale_original'):
                self.zoom_scale_original = 1.0
            
            # 위치도 유지 (초기화하지 않음)
            # 위치가 설정되어 있지 않으면 중앙으로 설정
            preview_width = getattr(self, 'preview_width', 800)
            preview_height = getattr(self, 'preview_height', 1000)
            
            if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                # 캔버스 크기 가져오기 (캔버스가 생성되어 있으면 실제 크기, 없으면 기본값)
                try:
                    canvas_width = self.canvas_original.winfo_width()
                    canvas_height = self.canvas_original.winfo_height()
                except:
                    canvas_width = preview_width
                    canvas_height = preview_height
                
                # 중앙 위치 계산 (위치가 없을 때만)
                self.canvas_original_pos_x = canvas_width // 2
                self.canvas_original_pos_y = canvas_height // 2
                self.canvas_edited_pos_x = canvas_width // 2
                self.canvas_edited_pos_y = canvas_height // 2
            
            self.original_image_base_size = None
            
            # 랜드마크 초기화 (새 이미지 로드 시)
            # LandmarkManager 사용하여 초기화
            if hasattr(self, 'landmark_manager'):
                self.landmark_manager.reset(keep_original=False)
                # 하위 호환성
                self.original_landmarks = self.landmark_manager.get_original_landmarks()
                self.face_landmarks = self.landmark_manager.get_face_landmarks()
                self.custom_landmarks = self.landmark_manager.get_custom_landmarks()
            else:
                # LandmarkManager가 없으면 기존 방식 사용
                self.original_landmarks = None
                self.face_landmarks = None
                self.custom_landmarks = None
            
            # 자동 정렬이 활성화되어 있으면 정렬 적용
            if self.auto_align.get():
                self.apply_alignment()
            else:
                # 정렬 없이 원본 이미지를 기반으로 설정
                self.aligned_image = None
                self.edited_image = img.copy()
            
            # 미리보기 업데이트
            if hasattr(self, 'show_original_preview'):
                self.show_original_preview()
            if hasattr(self, 'show_edited_preview'):
                self.show_edited_preview()
            
            filename = os.path.basename(file_path)
            self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
