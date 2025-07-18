import tkinter as tk
from tkinter import ttk

import globals as gl

class CityTab:
    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.build_tab_city(self.rootframe)

    def city_selected(self, index, value):
        selected = gl.generals[index]
        if selected.name != value:
            print(f"잘못된 아이템 정보입니다: {index}, {value}")
            return
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index)
            self.city_selected(index, value)

    def build_tab_city(self, parent):
        
        _width00 = 272
        _width01 = 264
        _height0 = 520

        # 좌측 장수 리스트
        self.frame_item = tk.Frame(parent)
        self.frame_item.grid(row=0, column=0, padx=(8,0), pady=0)

        #tk.Label(self.frame_left, text="", pady=0).pack()
        #font=font.Font(family="맑은 고딕", size=10, underline=0),
        self.listbox_item = tk.Listbox(self.frame_item, height=30, width=12)
        self.listbox_item.pack(fill="y")

        for city in gl.cities:
            self.listbox_item.insert(tk.END, "{0}".format(city.name))            

        frame_1 = tk.LabelFrame(parent, text="", width=_width00, height=_height0, borderwidth=0, highlightthickness=0)
        frame_1.grid(row=0, column=1, padx=(4,0))
        frame_1.grid_propagate(False)  # 크기 고정

        # 기본 설정
        frame_basic = tk.LabelFrame(frame_1, text="도시 기본 설정", width=_width01, height=72)
        frame_basic.grid(row=0, column=0)
        frame_basic.grid_propagate(False)  # 크기 고정            