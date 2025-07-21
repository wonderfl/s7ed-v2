import re

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import globals as gl

from . import _realm
from . import _city



class ItemTab:
    _width00 = 268
    _width01 = 264

    _height0 = 368
    _height1 = 268

    skills=[]
    skillv=[]

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.realmTab = _realm.RealmTab(self.rootframe, 0, 0)
        self.cityTab = _city.CityTab(self.rootframe, 1, 0)

        self.build_tab_item(self.rootframe, 0, 1)

    def listup_items(self):
        self.realmTab.listup_realms()
        self.cityTab.listup_cities()

        self.lb_items.delete(0, tk.END)
        for item in gl.items:
            self.lb_items.insert(tk.END, " {0:2}. {1}".format(item.num, item.name))

    def owner_selected(self, event):
        selected = self.owner_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]        
        filters = []
        self.owner_num = -1
        if '주인전체' != values[0]:
            if '주인없음' == values[0]:
                self.owner_num = 65535
            else:
                self.owner_num = int(values[0])

        self.lb_items.delete(0, tk.END)
        for item in gl.items:
            if -1 == self.owner_num or (-1 != self.owner_num and  self.owner_num == item.owner):
                self.lb_items.insert(tk.END, " {0:2}. {1}".format(item.num, item.name))

    def item_selected(self, index, value):
        item_max = len(gl.items)        
        values = [p for p in re.split(r'[.,]', value) if p]
        if( 2>len(values)):
            print(f"잘못된 아이템 정보입니다: {index}[ {values} ], 전체 세력: {item_max}")
            return
        _num = int(values[0])
        if 0 > _num or _num >= item_max:
            print(f"잘못된 아아템 정보입니다: {index}[ {values[0]}, {values[1]} ], 전체 아이템: {item_max}")
            return
        _name = values[1].strip()
        selected = gl.items[_num]
        if selected.name != _name:
            print(f"잘못된 아이템 정보입니다: {index}, {value}, :{_name}, {selected.name},")
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

        #print(selected.u00)
        for i in range(32):
            val = gl.bit32from(selected.u00, i, 1)
            self.skillv[i].set(val)
            # if 0 < val:
            #     print("{0:2}, val:{1}, var:{2}".format(i, val, self.skillv[i].get()))
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.item_selected(index, value)

    def build_skills(self, parent, nr, nc):
        self.frame_skills = tk.LabelFrame(parent, text="아이템 특기", width=self._width01, height=156)
        self.frame_skills.grid(row=nr, column=nc, pady=(8,0) )
        self.frame_skills.grid_propagate(False)  # 크기 고정

        self.frame_b1 = tk.LabelFrame(self.frame_skills, text="", width=self._width01-4, height=124, borderwidth=0, highlightthickness=0)
        self.frame_b1.grid(row=0, column=0, pady=(4, 0))
        self.frame_b1.grid_propagate(False)  # 크기 고정

        self.skills.clear()
        self.skillv.clear()
        smallfont = tkfont.Font(family="맑은 고딕", size=8)
        for i, name in enumerate(gl._propNames_):
            var = tk.IntVar()
            checked = tk.Checkbutton(self.frame_b1, text=name, font=smallfont, variable=var, width=6, height=0, highlightthickness=0, borderwidth=0,  )
            checked.grid(row=i//4, column=i%4, sticky="w", padx=(4,0),pady=0,ipady=0)
            self.skills.append(checked)
            self.skillv.append(var)

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="아이템 기본 설정", width=self._width01, height=100)
        frame_basic.grid(row=nr, column=nc, pady=0 )
        frame_basic.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0, pady=(8, 0))
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
        self.frame_item = tk.LabelFrame(parent, text="", width=self._width00+136, height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_item.grid(row=nr, column=nc, rowspan=2, padx=(8,0), pady=(8,0), sticky="nsew",)
        self.frame_item.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_00 = tk.LabelFrame(self.frame_item, text="", width=100, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_00.grid(row=0, column=0, padx=(4,0), pady=0,)
        self.frame_00.grid_propagate(False)  # 크기 고정

        self.frame_01 = tk.LabelFrame(self.frame_item, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        self.frame_01.grid(row=0, column=1, sticky='nw',padx=(4,0))
        self.frame_01.grid_propagate(False)  # 크기 고정

        owner_filters=[]
        self.owner_filter = ttk.Combobox(self.frame_00, values=owner_filters, width=14, )
        self.owner_filter.pack(side="top", fill="y")
        self.owner_filter.bind("<<ComboboxSelected>>", self.owner_selected)

        self.frame_listup = tk.LabelFrame(self.frame_00, text="", width=self._width00+136, height=self._height0, )# borderwidth=0, highlightthickness=0, )
        self.frame_listup.pack(side="top", pady=4, fill="y")        

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        scr_height = int((self._height0-16)/16)
        self.lb_items = tk.Listbox(self.frame_listup, height=scr_height, width=14, highlightthickness=0, relief="flat")
        self.lb_items.pack(side="left", pady=0, fill="both", expand=True)
        self.lb_items.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_items.yview)
        self.lb_items.config(yscrollcommand=scrollbar.set)
        
        self.build_basic(self.frame_01, 0, 0) # 기본 설정
        self.build_skills(self.frame_01, 1, 0) # 특기

        self.listup_items() # 특기

    def listup_items(self):
        gn = len(gl.generals)
        owners=[]
        #owners.append("전체")
        #owners.append("주인없음")
        ownerset=set()
        for item in gl.items:
            self.lb_items.insert(tk.END, " {0:2}. {1}".format(item.num, item.name))
            if 0 <= item.owner and item.owner < gn:                
                owner = gl.generals[item.owner]
                if owner.num in ownerset:
                    continue                
                ownerset.add(owner.num)
                owners.append(' {0:3}. {1}'.format(owner.num, owner.name))
        
        filter = []
        filter.append("주인전체")
        filter.append("주인없음")
        for owner in sorted(owners):
            filter.append(owner)

        self.owner_filter["values"] = filter
        self.owner_filter.set("주인전체")