"""Popup and window management mixin for FaceEditPanel."""
import os
import tkinter as tk
from tkinter import ttk


class PopupManagerMixin:
    """Provides file/settings popup helpers for the face edit panel."""

    def show_file_list_popup(self):
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
        popup.minsize(400, 500)

        settings_frame = tk.LabelFrame(popup, text="얼굴 편집 설정", padx=5, pady=5)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._create_face_alignment_ui(settings_frame)

        main_notebook = ttk.Notebook(settings_frame)
        main_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        morphing_tab = self._create_morphing_ui(main_notebook)
        main_notebook.add(morphing_tab, text="얼굴 특징 보정")

        # v2에서는 스타일 전송, 나이 변환 제거됨
        
        # 파일 경로 설정 탭
        path_tab = tk.Frame(main_notebook)
        main_notebook.add(path_tab, text="파일 경로")
        
        # 파일 경로 설정 UI
        path_frame = tk.LabelFrame(path_tab, text="얼굴 이미지 폴더", padx=5, pady=5)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 현재 경로 표시
        current_path_frame = tk.Frame(path_frame)
        current_path_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(current_path_frame, text="현재 경로:").pack(side=tk.LEFT)
        current_path_label = tk.Label(current_path_frame, text=self.face_edit_dir or "설정되지 않음", 
                                    fg="blue", cursor="hand2")
        current_path_label.pack(side=tk.LEFT, padx=(10, 0))
        
        def browse_folder():
            from tkinter import filedialog
            folder_path = filedialog.askdirectory(
                title="얼굴 이미지 폴더 선택",
                initialdir=self.face_edit_dir or os.path.expanduser("~")
            )
            if folder_path:
                self.face_edit_dir = folder_path
                current_path_label.config(text=folder_path)
                print(f"파일 경로 변경: {folder_path}")
        
        # 경로 선택 버튼
        button_frame = tk.Frame(path_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        browse_btn = tk.Button(button_frame, text="폴더 선택", command=browse_folder)
        browse_btn.pack(side=tk.LEFT)
        
        def on_popup_close():
            self.settings_popup = None
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        self.settings_popup = popup

    def on_close(self):
        """창 닫기"""
        if self.file_list_popup is not None and self.file_list_popup.winfo_exists():
            self.file_list_popup.destroy()
        if self.settings_popup is not None and self.settings_popup.winfo_exists():
            self.settings_popup.destroy()
        self.destroy()
