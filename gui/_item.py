import tkinter as tk
from tkinter import ttk

import globals as gl

from . import _realm
from . import _city



class ItemTab:
    _width00 = 268
    _width01 = 260

    _height0 = 300
    _height1 = 284

    skills=[]
    skillv=[]

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        _realm.RealmTab(self.rootframe, 0, 0)
        _city.CityTab(self.rootframe, 1, 0)

        self.build_tab_item(self.rootframe, 0, 1)

    def item_selected(self, index, value):
        selected = gl.items[index]
        if selected.name != value:
            print(f"잘못된 아이템 정보입니다: {index}, {value}")
            return
        
        owner = gl.generals[selected.owner] if 0 <= selected.owner and selected.owner < len(gl.generals) else None
        self.ownernum.config(text='{0}'.format('-'))
        self.ownername.delete(0, tk.END)
        if owner is not None:
            self.ownernum.config(text='{0}'.format(owner.num))
            self.ownername.insert(0, owner.name)
        else:
            self.ownername.insert(0, '주인 없음')

        self.itemnum.config(text='{0:3}.'.format(selected.num))
        self.itemname.delete(0, tk.END)
        self.itemname.insert(0, selected.name)

        self.market.delete(0, tk.END)
        self.market.insert(0, '{0}'.format(selected.market))

        statname = gl._itemStats_[selected.item_type]
        if 0 >= len(statname):
            statname = '-'
        self.stattype.config(text='{0}'.format(statname))

        itemtype = gl._itemTypes_[selected.item_type]
        self.typename.config(text='{0}'.format(itemtype))

        self.itemtype.delete(0, tk.END)
        self.itemtype.insert(0, '{0}'.format( str(selected.item_type)))

        self.itemstats.delete(0, tk.END)
        self.itemstats.insert(0, '{0}'.format( str(selected.stats) if 0 < selected.stats else ''))

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
        for i, name in enumerate(gl._propNames_):
            var = tk.IntVar()
            checked = tk.Checkbutton(frame_skills, text=name, width=6, height=1, highlightthickness=0, borderwidth=0, variable=var )
            checked.grid(row=i//4, column=i%4, sticky="w", pady=0,ipady=0)
            self.skills.append(checked)
            self.skillv.append(var)            

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="아이템 기본 설정", width=self._width01, height=100)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0, pady=(4, 0))
        frame_b1.grid_propagate(False)  # 크기 고정

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=48, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=0)
        frame_b2.grid_propagate(False)  # 크기 고정

        self.itemnum = tk.Label(frame_b1, text="", width=4, anchor="e")
        self.itemnum.grid(row=0, column=0, )
        self.itemname = tk.Entry(frame_b1, width=10, ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemname.grid(row=0, column=1, padx=(4,0))

        self.ownernum = tk.Label(frame_b1, text="-", width=6, anchor="e" )
        self.ownernum.grid(row=0, column=2, padx=0)
        self.ownername = tk.Entry(frame_b1, width=10 )
        self.ownername.grid(row=0, column=3, padx=(4,0))

        self.typename = tk.Label(frame_b2, text="종류", width=4, anchor="e")
        self.typename.grid(row=0, column=0, )
        self.itemtype = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemtype.grid(row=0, column=1, padx=(4,0))

        self.stattype = tk.Label(frame_b2, text="-", width=4, anchor="e")
        self.stattype.grid(row=1, column=0, )
        
        self.itemstats = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemstats.grid(row=1, column=1, padx=(4,0))

        tk.Label(frame_b2, text="매매", width=6, anchor="e").grid(row=0, column=2, padx=0)
        self.market = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.market.grid(row=0, column=3, padx=(4,0))

        tk.Label(frame_b2, text="가격", width=6, anchor="e").grid(row=1, column=2, padx=0)
        self.itemprice = tk.Entry(frame_b2, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemprice.grid(row=1, column=3, padx=(4,0))


    def build_tab_item(self, parent, nr, nc):
        self.frame_item = tk.LabelFrame(parent, text="", width=self._width00+120, height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_item.grid(row=nr, column=nc, rowspan=2, padx=(4,0))
        self.frame_item.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_00 = tk.LabelFrame(self.frame_item, text="", width=100, height=self._height0-8,)
        self.frame_00.grid(row=0, column=0, padx=(4,0))
        self.frame_00.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_00, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        scr_height = int(self._height0/16)
        self.lb_items = tk.Listbox(self.frame_00, height=scr_height, width=12, highlightthickness=0, relief="flat")
        self.lb_items.pack(side="left", fill="both", expand=True)
        self.lb_items.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_items.yview)
        self.lb_items.config(yscrollcommand=scrollbar.set)
        for item in gl.items:
            self.lb_items.insert(tk.END, " {0}".format(item.name))

        self.frame_01 = tk.LabelFrame(self.frame_item, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        self.frame_01.grid(row=0, column=1, padx=(4,0))
        self.frame_01.grid_propagate(False)  # 크기 고정
        
        self.build_basic(self.frame_01, 0, 0) # 기본 설정
        self.build_skills(self.frame_01, 1, 0) # 특기


    