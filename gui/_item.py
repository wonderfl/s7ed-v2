import tkinter as tk
from tkinter import ttk

import globals as gl

class ItemTab:
    _width00 = 276
    _width01 = 262
    _height0 = 328

    skills=[]
    skillv=[]

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.build_tab_item(self.rootframe)

    def item_selected(self, index, value):
        selected = gl.items[index]
        if selected.name != value:
            print(f"잘못된 아이템 정보입니다: {index}, {value}")
            return
        
        owner = gl.generals[selected.owner] if 0 <= selected.owner and selected.owner < len(gl.generals) else None
        self.ownername.config(text='{0}'.format('  - '))
        self.ownernum.delete(0, tk.END)
        if owner is not None:
            self.ownername.config(text='{0}'.format(owner.name))
            self.ownernum.insert(0, owner.num)

        self.itemnum.config(text='{0:3}.'.format(selected.num))
        self.itemname.delete(0, tk.END)
        self.itemname.insert(0, selected.name)

        self.market.delete(0, tk.END)
        self.market.insert(0, '{0}'.format(selected.market))

        statname = gl._itemStats_[selected.item_type]
        if 0 >= len(statname):
            statname = '-'
        self.itemtype.config(text='{0}'.format(statname))
        self.itemstats.delete(0, tk.END)
        self.itemstats.insert(0, '{0}'.format( '+'+str(selected.stats) if 0 < selected.stats else ''))

        self.itemprice.delete(0, tk.END)
        self.itemprice.insert(0, '{0}'.format( str(selected.price) if 0 < selected.price else ''))        

        for i in range(32):
            self.skillv[i].set(gl.bit32from(selected.u00, i, 1))
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.item_selected(index, value)

    def build_skills(self, parent, nr, nc):
        frame_skills = tk.LabelFrame(parent, text="무장 특기", width=self._width01, height=172)
        frame_skills.grid(row=nr, column=nc, pady=(4,0) )
        frame_skills.grid_propagate(False)  # 크기 고정
        skill_names = [
            "첩보","발명","조교","상재", "응사","반계","수습","정찰",
            "무쌍","돌격","일기","강행", "수복","수군","화시","난시",
            "선동","신산","허보","천문", "수공","고무","욕설","혈공",
            "귀모","성흔","행동","단련", "의술","점복","평가","부호",
        ]
        for i, name in enumerate(skill_names):
            var = tk.IntVar()
            checked = tk.Checkbutton(frame_skills, text=name, width=6, height=1, highlightthickness=0, borderwidth=0, variable=var )
            checked.grid(row=i//4, column=i%4, sticky="w", pady=0,ipady=0)
            self.skills.append(checked)
            self.skillv.append(var)            

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="아이템 기본 설정", width=self._width01, height=144)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0)
        frame_b1.grid_propagate(False)  # 크기 고정

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=96, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=0)
        frame_b2.grid_propagate(False)  # 크기 고정

        self.ownername = tk.Label(frame_b1, text="", width=8, anchor="e" )
        self.ownername.grid(row=0, column=0)
        self.ownernum = tk.Entry(frame_b1, width=10 )
        self.ownernum.grid(row=0, column=1, padx=(4,0))        

        self.itemnum = tk.Label(frame_b2, text="", width=8, anchor="e")
        self.itemnum.grid(row=0, column=0, )
        self.itemname = tk.Entry(frame_b2, width=10, ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemname.grid(row=0, column=1, padx=(4,0))

        self.itemtype = tk.Label(frame_b2, text="", width=8, anchor="e")
        self.itemtype.grid(row=1, column=0, )
        
        self.itemstats = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemstats.grid(row=1, column=1, padx=(4,0))

        tk.Label(frame_b2, text="매매", width=8, anchor="e").grid(row=2, column=0, )
        self.market = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.market.grid(row=2, column=1, padx=(4,0))        

        tk.Label(frame_b2, text="가격", width=8, anchor="e").grid(row=3, column=0, )
        self.itemprice = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemprice.grid(row=3, column=1, padx=(4,0))        


    def build_tab_item(self, parent):

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(parent, text="", width=100, height=self._height0,)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_0, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.lb_items = tk.Listbox(self.frame_0, height=20, width=10, highlightthickness=0, relief="flat")
        self.lb_items.pack(side="left", fill="both", expand=True)
        self.lb_items.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_items.yview)
        self.lb_items.config(yscrollcommand=scrollbar.set)
        for item in gl.items:
            self.lb_items.insert(tk.END, " {0}".format(item.name))

        self.frame_1 = tk.LabelFrame(parent, text="", width=self._width00, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정
        
        self.build_basic(self.frame_1, 0, 0) # 기본 설정
        self.build_skills(self.frame_1, 1, 0) # 특기
        