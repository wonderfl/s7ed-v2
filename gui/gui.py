import os
import re

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

import gui._general as _gnl
import gui._item as _item
import gui._popup as _popup
import gui.frame_button as _button

import commands.files as file

import globals as gl

_value = ""

class GeneralEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("삼국지 VII - 장수 에디터 (전체 GUI 구성)")
        
        self.root.bind("<Control-f>", self.show_search_entry)  # Ctrl+F 핫키 등록        

        self.create_widgets()

    def create_widgets(self):
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH)
        
        self.generalTab = _gnl.GeneralTab(self.frame)

        # 하단 footbar
        self.footbar = tk.Frame(self.root, bg="lightgray", height=30)
        self.footbar.pack(side=tk.BOTTOM, fill=tk.X)

        # footbar 내부 내용 (예: 상태 텍스트)
        self.status = tk.Label(self.footbar, text="준비됨", bg="lightgray", anchor="w")
        self.status.pack(side=tk.LEFT, padx=10)

    def show_search_entry(self, event=None):
        # 이미 검색창이 떠 있다면 무시
        if hasattr(self, 'search_window') and self.search_window.winfo_exists():
            self.search_window.lift()
            return

        # 검색창 띄우기
        self.search_window = tk.Toplevel(self.root)
        self.search_window.resizable(False, False)
        self.search_window.attributes('-toolwindow', True)
        self.search_window.title("이름으로 검색")
        self.root.update_idletasks()  # geometry 정보 갱신
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()

        # 팝업 크기
        popup_width = 200
        popup_height = 100

        # 중앙 위치 계산 (부모 창 안에서)
        x = px + (pw - popup_width) // 4
        y = py + (ph - popup_height) // 4

        self.search_window.geometry(f"+{x}+{y}")
        self.search_window.bind("<Escape>", lambda event: self.search_window.destroy())

        frame1 = tk.LabelFrame(self.search_window, text="", width=176, height=32, )
        frame1.grid(row=0, column=0, padx=8, pady=4)
        frame1.grid_propagate(False)  # 크기 고정

        self.serch_label = tk.Label(frame1, text="찾을 이름 :", width=8, height=1, anchor="w")
        self.serch_label.grid(row=0, column=0, padx=4, pady=4)
        self.search_entry = tk.Entry(frame1, width=12,)
        self.search_entry.grid(row=0, column=1, padx=4, pady=4)
        self.search_entry.focus_set()

        # 엔터 입력 시 검색 실행
        self.search_entry.bind("<Return>", self.do_search)

    def do_search(self, event=None):
        keyword = self.search_entry.get()
        if 1 >= len(keyword.strip()):
            return
        items = self.generalTab.items()
        li = len(items)

        ix = 0
        selected = _app.generalTab.general_selected
        if selected is not None:
            strkey = " {0:3}. {1}".format(selected.num, selected.name)
            for i, item in enumerate(items):
                if strkey not in item:
                    continue
                ix = i+1
                break

        generals = items[ix:] + items[:ix]
        for i, general in enumerate(generals):
            if keyword not in general:
                continue
            num = (ix + i) % li
            self.generalTab.focus_num(num)
            break

        self.search_window.destroy()  # 검색 후 닫기


def open_file():
    gl._loading_file = ""
    filepath = filedialog.askopenfilename(filetypes=[("s7 Files", "*.s7"), ("All Files", "*.*")])
    if filepath:
        file.open_file(filepath)
        #messagebox.showinfo("로딩 완료", f"{filepath}를 불러왔습니다.")

        _app.generalTab.listup_generals()
        _app.status.config(text="로딩 완료: {0}를 불러왔습니다.".format(filepath))
        gl._loading_file = filepath

def reload_file():
    filename = gl._loading_file
    if 0 >= len(filename):
        print("error: file name empty..")
        return
    if False == os.path.exists(filename):
        print("error: file not exist.. ", filename)
        gl._loading_file = ''
        return

    file.open_file(filename)

    _app.generalTab.listup_generals()
    _app.status.config(text="로딩 완료: {0}를 다시 불러왔습니다.".format(filename))
    
    gl._loading_file = filename

def save_file():
    filename = gl._loading_file
    if 0 >= len(filename):
        print("error: file name empty..")
        return
    if False == os.path.exists(filename):
        print("error: file not exist.. ", filename)
        gl._loading_file = ''
        return
        
    file.save_file(filename)
    gl._loading_file = filename

    _app.status.config(text="저장 완료: {0}를 저장하였습니다.".format(filename))


def save_as_file():
    filepath = filedialog.asksaveasfilename(defaultextension=".s7",
                                             filetypes=[("s7 Files", "*.s7"), ("All Files", "*.*")])
    file.save_file(filepath)
    gl._loading_file = filepath


def export_file():
    print("export")
    #file.test_save_file('export.csv')

def open_help():
    print("help")

def open_about():
    print("help")

def info_open():
    _app.generalTab.show_popup()
    
_root = tk.Tk()
_app = GeneralEditorApp(_root)

def app():

    # 메뉴 바 생성
    menu_bar = tk.Menu(_root)

    file_menu = tk.Menu(menu_bar, tearoff=0, )
    file_menu.add_command(label="Open", command=open_file)
    file_menu.add_command(label="Reload", command=reload_file)
    file_menu.add_separator()
    file_menu.add_command(label="Save ", command=save_file)
    file_menu.add_command(label="Save as", command=save_as_file)    

    file_menu.add_separator()
    file_menu.add_command(label="Export", command=export_file)

    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=_root.quit)

    info_menu = tk.Menu(menu_bar, tearoff=0,)
    info_menu.add_command(label="etc", command=info_open)

    add_menu = tk.Menu(menu_bar, tearoff=0,)
    add_menu.add_command(label="충성 +5", command=info_open)
    add_menu.add_command(label="친밀 +10", command=info_open)    
    add_menu.add_command(label="병사 +500", command=info_open)    
    add_menu.add_command(label="건강 ++", command=info_open)

    full_menu = tk.Menu(menu_bar, tearoff=0,)
    full_menu.add_command(label="행동력: 200", command=info_open)
    full_menu.add_command(label="훈련: 100", command=info_open)
    full_menu.add_command(label="포획: 00", command=info_open)

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="City/Item", command=info_open)
    help_menu.add_command(label="about", command=open_about)
    help_menu.add_command(label="help", command=open_help)    

    menu_bar.add_cascade(label="File", menu=file_menu)
    menu_bar.add_cascade(label="Add+", menu=add_menu)
    menu_bar.add_cascade(label="Full", menu=full_menu)
    menu_bar.add_cascade(label="Help", menu=help_menu)
    menu_bar.add_cascade(label="Save", command=save_file)    
    menu_bar.add_cascade(label="Reload", command=reload_file)    
    menu_bar.add_cascade(label="City/Item", command=info_open)    

    _root.config(menu=menu_bar)
    _root.mainloop()

if __name__ == "__main__":
    app()

