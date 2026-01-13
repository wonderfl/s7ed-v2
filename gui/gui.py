import os
import re

import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import filedialog, messagebox

import gui._general as _gnl
import gui._item as _item
import gui._popup as _popup
from gui.frame import button as _button
import gui._face_import as _face_import
from gui import face_extract as _face_extract
from gui.face_edit import show_face_edit_panel
import gui._face_generate as _face_generate
import gui._face_similar as _face_similar

import commands.files as file

import globals as gl
import utils.kaodata_image as kaodata_image
import utils.config as config

_value = ""

class GeneralEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("삼국지 VII - 장수 에디터 (전체 GUI 구성)")
        
        self.root.bind("<Control-f>", self.show_search_entry)  # Ctrl+F 핫키 등록        

        # TkFixedFont 가져오기
        fixed_font = font.nametofont("TkFixedFont")

        # TkDefaultFont 가져오기
        default_font = font.nametofont("TkDefaultFont")

        # TkDefaultFont를 TkFixedFont와 동일하게 설정
        default_font.configure(
            family=fixed_font.cget("family"),
            size=8,
            weight="normal"
        )

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

        self.root.resizable(False, False)

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

        ix = -1
        selected = _app.generalTab.listupFrame.index_selected()
        if 0 > selected >= li:
            return
        ix = selected+1
        print("found: {0} / {1}".format(ix, li))
        if ix < 0:
            print("not found: ", keyword)
            return
        
        generals = items[ix:] + items[:ix]
        num = -1
        for i, iid in enumerate(generals):
            item = self.generalTab.listupFrame.lb_generals.item(iid, 'values')
            #print("search: {0} / {1} - {2}".format(i, li, item))
            if keyword not in item[2]:
                continue
            num = (ix + i) % li
            self.generalTab.focus_num(num, True)
            break

        print("found: {0}, {1}".format( num, ix))
        self.search_window.destroy()  # 검색 후 닫기


def open_file():
    gl._loading_file = ""
    
    # 저장 파일 디렉토리 설정 (마지막으로 연 파일의 디렉토리 또는 기본값)
    initial_dir = None
    if gl._save_file_dir and os.path.exists(gl._save_file_dir):
        initial_dir = gl._save_file_dir
    elif gl._loading_file and os.path.exists(gl._loading_file):
        initial_dir = os.path.dirname(gl._loading_file)
    
    filepath = filedialog.askopenfilename(
        title="저장 파일 선택",
        filetypes=[("s7 Files", "*.s7"), ("All Files", "*.*")],
        initialdir=initial_dir
    )
    if filepath:
        file.open_file(filepath)
        #messagebox.showinfo("로딩 완료", f"{filepath}를 불러왔습니다.")

        _app.generalTab.listup_generals()
        _app.status.config(text="로딩 완료: {0}를 불러왔습니다.".format(filepath))
        gl._loading_file = filepath
        gl._save_file_dir = os.path.dirname(filepath)  # 저장 파일 디렉토리 기억
        config.save_config()  # 설정 파일에 저장

def open_face_file():
    """얼굴 파일(Kaodata.s7) 열기"""
    filepath = filedialog.askopenfilename(
        title="얼굴 파일 선택",
        filetypes=[("Kaodata Files", "Kaodata.s7"), ("s7 Files", "*.s7"), ("All Files", "*.*")]
    )
    if filepath:
        kaodata_image.set_face_file_path(filepath)
        _app.status.config(text="얼굴 파일 설정: {0}".format(filepath))
        config.save_config()  # 설정 파일에 저장
        messagebox.showinfo("완료", f"얼굴 파일이 설정되었습니다.\n\n{filepath}")

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


def check_and_reload_file():
    """파일 변경을 체크하고 사용자에게 확인 후 리로드"""
    filename = gl._loading_file
    if file.check_file_changed():
        result = messagebox.askyesno(
            "파일 변경 감지",
            f"파일이 외부에서 변경되었습니다.\n\n{filename}\n\n다시 불러오시겠습니까?",
            icon='question'
        )
        
        if result:
            # 사용자가 "예"를 선택한 경우 리로드
            reload_file()


    if gl._is_saving:
        gl._is_saving = False
        try:
            gl._file_mtime = os.path.getmtime(filename)
            print(f"[파일저장중] mtime 업데이트: {gl._file_mtime}")
        except Exception as e:
            print(f"[파일체크] mtime 업데이트 실패: {e}")

    # 1초 후 다시 체크
    _root.after(1000, check_and_reload_file)

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
    # mtime 업데이트는 commands/files.py의 save_file()에서 처리됨

    _app.status.config(text="저장 완료: {0}를 저장하였습니다.".format(filename))


def save_as_file():
    # 저장 파일 디렉토리 설정
    initial_dir = None
    if gl._save_file_dir and os.path.exists(gl._save_file_dir):
        initial_dir = gl._save_file_dir
    elif gl._loading_file and os.path.exists(gl._loading_file):
        initial_dir = os.path.dirname(gl._loading_file)
    
    filepath = filedialog.asksaveasfilename(
        title="저장 파일 선택",
        defaultextension=".s7",
        filetypes=[("s7 Files", "*.s7"), ("All Files", "*.*")],
        initialdir=initial_dir
    )
    if filepath:
        file.save_file(filepath)
        gl._loading_file = filepath
        gl._save_file_dir = os.path.dirname(filepath)  # 저장 파일 디렉토리 기억
        config.save_config()  # 설정 파일에 저장


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
    file_menu.add_command(label="얼굴 파일 열기...", command=open_face_file)
    file_menu.add_command(label="얼굴 이미지 가져오기...", command=lambda: _face_import.show_face_import_panel(_root))
    file_menu.add_command(label="얼굴 추출...", command=lambda: _face_extract.show_face_extract_panel(_root))
    file_menu.add_command(label="얼굴 편집...", command=lambda: show_face_edit_panel(_root))
    file_menu.add_command(label="얼굴 생성...", command=lambda: _face_generate.show_face_generate_panel(_root))
    file_menu.add_command(label="비슷한 얼굴 찾기...", command=lambda: _face_similar.show_face_similar_panel(_root))

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
    menu_bar.add_cascade(label="Face Extract", command=lambda: _face_extract.show_face_extract_panel(_root))
    menu_bar.add_cascade(label="Face Morph", command=lambda: show_face_edit_panel(_root))

    _root.config(menu=menu_bar)
    
    # 설정 파일 로드
    config.load_config()
    
    # 파일 변경 감지 시작 (1초마다 체크)
    _root.after(1000, check_and_reload_file)
    
    _root.mainloop()

if __name__ == "__main__":
    app()

