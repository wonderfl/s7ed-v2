import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

import gui._general as _gnl
import gui._item as _item
import gui._popup as _popup

import commands.files as file

import globals as gl

_value = ""

class GeneralEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("삼국지 VII - 장수 에디터 (전체 GUI 구성)")
        self.create_widgets()

    def create_widgets(self):

        notebook = ttk.Notebook(self.root)  # 탭 컨테이너
        #notebook.pack(fill="both", expand=True)    

        # 각 탭에 넣을 프레임 생성
        self.tab1 = ttk.Frame(notebook)
        self.tab2 = ttk.Frame(notebook)

        # 장수 전체 정보
        #notebook.add(self.tab1, text="세력/도시/아이템")
        self.itemTab = _item.ItemTab(self.tab1)

        # 아이템 전체 정보        
        #notebook.add(self.tab2, text="  장수  ")
        #self.generalTab = _gnl.GeneralTab(self.tab2)
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH)
        self.generalTab = _gnl.GeneralTab(self.frame)

        # 하단 footbar
        self.footbar = tk.Frame(self.root, bg="lightgray", height=30)
        self.footbar.pack(side=tk.BOTTOM, fill=tk.X)

        # footbar 내부 내용 (예: 상태 텍스트)
        self.status = tk.Label(self.footbar, text="준비됨", bg="lightgray", anchor="w")
        self.status.pack(side=tk.LEFT, padx=10)

        # 하단 푸터/풋바
        #self.footbar = tk.Frame(self.root)
        #self.footbar.pack(side="bottom", fill="x")


def open_file():
    filepath = filedialog.askopenfilename(filetypes=[("s7 Files", "*.s7"), ("All Files", "*.*")])
    if filepath:
        file.open_file(filepath)
        #messagebox.showinfo("로딩 완료", f"{filepath}를 불러왔습니다.")

        _app.generalTab.listup_generals()
        _app.status.config(text="로딩 완료: {0}를 불러왔습니다.".format(filepath))

def save_file():
    filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    #if filepath:
    #    with open(filepath, "w", encoding="utf-8") as file:
    #        file.write(text.get("1.0", tk.END))
    #    messagebox.showinfo("저장 완료", f"{filepath}에 저장되었습니다.")

def info_open():
    _app.generalTab.show_popup()
    

_root = tk.Tk()
_app = GeneralEditorApp(_root)

def app():
    
    #_root.title("파일 입출력 예제")

    # 메뉴 바 생성
    menu_bar = tk.Menu(_root)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="열기", command=open_file)
    file_menu.add_command(label="저장", command=save_file)
    file_menu.add_separator()
    file_menu.add_command(label="종료", command=_root.quit)

    info_menu = tk.Menu(menu_bar, tearoff=0, )
    info_menu.add_command(label="정보", command=info_open)

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="도움말", command=open_file)

    menu_bar.add_cascade(label="파일", menu=file_menu)
    menu_bar.add_cascade(label="정보", menu=info_menu)
    menu_bar.add_cascade(label="도움말", menu=help_menu)

    _root.config(menu=menu_bar)

    # 텍스트 편집기 영역
    #text = tk.Text(root, wrap="word")
    #text.pack(expand=True, fill="both")

    #editor = GeneralEditorApp(_root)
    _root.mainloop()

if __name__ == "__main__":
    app()

