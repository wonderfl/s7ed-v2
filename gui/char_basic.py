import tkinter as tk
from tkinter import ttk

import globals as gl
from . import _city
from . import _realm



class CharacterBasicFrame:

    _width00 = 276
    _width01 = 272
    _height0 = 540

    _width10 = 328
    _width11 = 320

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.build_frame_basic(self.rootframe, 0, 0)
        return

    def general_selected(self, index, value):
        #print(f"선택된 항목 처리: {value}")
        selected = gl.generals[index]
        if selected.name != value:
            print(f"잘못된 정보입니다: {index}, {value}")
            return
        self.name0.delete(0, tk.END)
        self.name0.insert(0, selected.name0)
        self.name1.delete(0, tk.END)        
        self.name1.insert(0, selected.name1)
        self.name2.delete(0, tk.END)
        self.name2.insert(0, selected.name2)
        self.face.delete(0, tk.END)
        self.face.insert(0, selected.faceno)
        
        self.genderv.set(selected.gender)
        self.turnv.set(selected.turned)


    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            #print(f"[선택] {index}: {value}")
            # 선택시 호출할 함수
            self.general_selected(index, value)


    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="무장 기본 설정", width=self._width01, height=72)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0)
        frame_b1.grid_propagate(False)  # 크기 고정        

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=0)
        frame_b2.grid_propagate(False)  # 크기 고정                

        #entry_row(frame_b1, ["성", "명", "자"])
        tk.Label(frame_b1, text="성").grid(row=0, column=0)
        self.name0 = tk.Entry(frame_b1, width=4 )
        self.name0.grid(row=0, column=1)

        tk.Label(frame_b1, text="명").grid(row=0, column=2)
        self.name1 = tk.Entry(frame_b1, width=4 )
        self.name1.grid(row=0, column=3)

        tk.Label(frame_b1, text="자").grid(row=0, column=4)
        self.name2 = tk.Entry(frame_b1, width=4 )
        self.name2.grid(row=0, column=5)

        tk.Label(frame_b1, text="별명").grid(row=0, column=6)
        tk.Entry(frame_b1, width=8 ).grid(row=0, column=7)                        

        tk.Label(frame_b2, text="얼굴").grid(row=1, column=0)
        self.face = tk.Entry(frame_b2, width=4)
        self.face.grid(row=1, column=1)

        self.genderv = tk.IntVar()
        tk.Label(frame_b2, text="성별").grid(row=1, column=3)
        tk.Radiobutton(frame_b2, text="남", variable=self.genderv, value=0).grid(row=1, column=4)
        tk.Radiobutton(frame_b2, text="여", variable=self.genderv, value=1).grid(row=1, column=5)
        
        var = tk.IntVar()
        self.turned = tk.Checkbutton(frame_b2, text="행동유무", variable=var)
        self.turned.grid(row=1, column=7)
        self.turnv = var


    def build_frame_basic(self, parent, nr, nc):

        self.frame_general = tk.LabelFrame(parent, text="", width= (108+self._width00+self._width10), height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_general.grid(row=nr, column=nc, rowspan=2, padx=(4,0))
        self.frame_general.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(self.frame_general, text="", width=100, height=self._height0,)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_0, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.lb_generals = tk.Listbox(self.frame_0, height=33, width=10,  highlightthickness=0,relief="flat")
        self.lb_generals.pack(side="left", fill="both", expand=True)
        self.lb_generals.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_generals.yview)
        self.lb_generals.config(yscrollcommand=scrollbar.set)
        for general in gl.generals:
            self.lb_generals.insert(tk.END, " {0}".format(general.name))

        self.frame_1 = tk.LabelFrame(self.frame_general, text="", width=self._width00, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정

        self.build_basic(self.frame_1, 0, 0) # 기본 설정            