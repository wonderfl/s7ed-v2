import tkinter as tk
from tkinter import ttk

import gui._general as t_gnl
import gui._item as t_item
import gui._city as t_city
import gui._realm as t_realm

import globals as gl

_value = ""

class OfficerEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("삼국지 VII - 장수 에디터 (전체 GUI 구성)")
        self.create_widgets()

    def create_widgets(self):

        notebook = ttk.Notebook(self.root)  # 탭 컨테이너
        notebook.pack(fill="both", expand=True)    

        # 각 탭에 넣을 프레임 생성
        self.tab1 = ttk.Frame(notebook)
        self.tab2 = ttk.Frame(notebook)
        self.tab3 = ttk.Frame(notebook)
        self.tab4 = ttk.Frame(notebook)

        # 장수 전체 정보
        notebook.add(self.tab1, text="  장수   ")
        t_gnl.GeneralTab(self.tab1)

        # 아이템 전체 정보        
        notebook.add(self.tab2, text="  아이템  ")
        t_item.ItemTab(self.tab2)

        # 도시 전체 정보        
        notebook.add(self.tab3, text="  도시    ")
        t_city.CityTab(self.tab3)

        # 세력 전체 정보        
        notebook.add(self.tab4, text="  세력    ")
        t_realm.RealmTab(self.tab4)


        # 하단 푸터/풋바
        #self.footbar = tk.Frame(self.root)
        #self.footbar.pack(side="bottom", fill="x")



def app():
    root = tk.Tk()
    app = OfficerEditorApp(root)

    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = OfficerEditorApp(root)

    root.mainloop()

