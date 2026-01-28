"""Popup and window management mixin for FaceEditPanel."""
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

        morphing_tab = self._create_face_morphing_ui(main_notebook)
        main_notebook.add(morphing_tab, text="얼굴 특징 보정")

        style_tab = self._create_style_transfer_ui(main_notebook)
        main_notebook.add(style_tab, text="스타일 전송")

        age_tab = self._create_age_transform_ui(main_notebook)
        main_notebook.add(age_tab, text="나이 변환")

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
