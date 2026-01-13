"""
얼굴 추출 패널 - 파일 관리 Mixin
파일 선택, 로드 관련 기능을 담당
"""
import os
import glob
import tkinter as tk
from tkinter import filedialog

import utils.kaodata_image as kaodata_image


class FileManagerMixin:
    """파일 관리 기능 Mixin"""
    
    def refresh_file_list(self):
        """파일 목록 새로고침"""
        self.file_listbox.delete(0, tk.END)
        
        # 이미지 디렉토리 경로 가져오기 (얼굴 추출 패널 폴더가 있으면 사용, 없으면 png_dir 사용)
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
        
        # 파일 경로 구성 (얼굴 추출 패널 폴더가 있으면 사용, 없으면 png_dir 사용)
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            png_dir = self.face_extract_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        file_path = os.path.join(png_dir, filename)
        
        if os.path.exists(file_path):
            self.load_image(file_path)
    
    def browse_file(self):
        """파일 선택 대화상자"""
        # 저장된 이미지 디렉토리 경로 가져오기 (얼굴 추출 패널 폴더가 있으면 사용)
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            initial_dir = self.face_extract_dir
        else:
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
            # 선택한 파일의 디렉토리 경로 저장 (얼굴 추출 패널 폴더에 저장, png_dir은 변경하지 않음)
            import globals as gl
            import utils.config as config
            source_dir = os.path.dirname(file_path)
            if not os.path.isabs(source_dir):
                source_dir = os.path.abspath(source_dir)
            # 얼굴 추출 패널 폴더 업데이트 (불러오기와 저장 모두 이 폴더 사용)
            self.face_extract_dir = source_dir
            gl._face_extract_dir = source_dir
            # 설정 파일에 저장
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
    
    def _get_or_select_extract_folder(self):
        """얼굴 추출 이미지 저장 폴더 가져오기 (없으면 선택)"""
        import globals as gl
        import utils.config as config
        
        # 이미 설정된 폴더가 있으면 반환
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            return self.face_extract_dir
        
        # 폴더 선택 대화상자
        initial_dir = self.face_extract_dir if self.face_extract_dir else None
        if initial_dir and not os.path.exists(initial_dir):
            initial_dir = None
        
        folder_path = filedialog.askdirectory(
            title="얼굴 추출 이미지 저장 폴더 선택",
            initialdir=initial_dir
        )
        
        if folder_path:
            # 절대 경로로 변환
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            # 저장
            self.face_extract_dir = folder_path
            gl._face_extract_dir = folder_path
            config.save_config()
            
            return folder_path
        
        return None
    
    def load_image(self, file_path):
        """이미지 로드 및 얼굴 추출"""
        try:
            # 이미지 읽기
            from PIL import Image
            img = Image.open(file_path)
            
            # 이미지 저장
            self.current_image = img
            self.current_image_path = file_path
            
            # 모든 캐시 무효화 (새 이미지 로드)
            self._adjusted_image_cache = None
            self._palette_image_cache = None
            self._original_preview_cache = None
            self._landmarks_adjusted_cache = None
            
            # 파일명 표시 (리스트박스에서 선택된 항목 강조)
            filename = os.path.basename(file_path)
            for i in range(self.file_listbox.size()):
                if self.file_listbox.get(i) == filename:
                    self.file_listbox.selection_clear(0, tk.END)
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
            
            # 미리보기 타이틀 업데이트
            self._update_preview_titles(filename)
            
            # 이미지별 파라미터 불러오기
            self._load_image_params(file_path)
            
            # 얼굴 추출
            self.extract_face()
            
            # 수동 영역 설정이 로드된 경우 UI 업데이트 (입력 필드 활성화/비활성화)
            if hasattr(self, 'use_manual_region') and hasattr(self, 'manual_x_entry'):
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
            
            # 원본 이미지 미리보기 표시
            self.show_original_preview()
            
            # 파일 이름은 미리보기 타이틀에 이미 표시되므로 상태 라벨에는 표시하지 않음
            # self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            print(f"[얼굴추출] 이미지 로드 실패: {e}")
            self.status_label.config(text=f"에러: 이미지 로드 실패 - {e}", fg="red")
