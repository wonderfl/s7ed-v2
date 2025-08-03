import os
import re

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import globals as gl

from . import _realm
from . import _city

from commands import files



class ItemTab:
    _width00 = 268
    _width01 = 264

    _height0 = 276
    _height1 = 280

    skills=[]
    skillv=[]

    entry_vars = {}
    entry_ids = {}    
    
    item_selected = None

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.build_player(self.rootframe, 0, 1)
        self.build_tab_item(self.rootframe, 1, 1)
        
        self.item_selected = None

    def listup_items(self):
        print('{0}, {1}'.format(gl._scene, gl._player_name))
        
        self.item_selected = None
        self.current_scene.delete(0, tk.END)
        self.current_scene.insert(0, '{0}'.format(gl._scene))

        self.player_name.delete(0, tk.END)
        self.player_name.insert(0, '{0:3}. {1}'.format(gl._player_num, gl._player_name))

        self.current_year.delete(0, tk.END)
        self.current_year.insert(0, '{0:5}'.format(gl._year))
        self.current_month.delete(0, tk.END)
        self.current_month.insert(0, '{0:5}'.format(gl._month))
        self.current_gold.delete(0, tk.END)
        self.current_gold.insert(0, '{0}'.format(gl.hero_golds))

        gn = len(gl.generals)
        owners=[]
        ownerset=set()

        self.lb_items.delete(0, tk.END)
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
        filter.append("판매중")
        for owner in sorted(owners):
            filter.append(owner)

        self.owner_filter["values"] = filter
        self.owner_filter.set("주인전체")

    def on_selected_owner(self, event):
        
        self.item_selected = None

        selected = self.owner_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]        
        filters = []
        self.owner_num = -1
        if '주인전체' != values[0]:
            if '주인없음' == values[0]:
                self.owner_num = 65535
            elif '판매중' == values[0]:
                self.owner_num = -2
            else:
                self.owner_num = int(values[0])

        self.lb_items.delete(0, tk.END)
        for item in gl.items:
            if -2 == self.owner_num and 3 == item.market:
                self.lb_items.insert(tk.END, " {0:2}. {1}".format(item.num, item.name))
                continue

            if -1 == self.owner_num or (-1 != self.owner_num and  self.owner_num == item.owner):
                self.lb_items.insert(tk.END, " {0:2}. {1}".format(item.num, item.name))

    def on_selected_item(self, index, value):
        self.item_selected = None
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
        
        self.item_changed = False
        self.owner_changed = False
        self.owner_prev = 65535
        self.item_selected = selected

        self.itemname.delete(0, tk.END)
        self.itemname.insert(0, '{0}'.format(selected.name))

        owner = gl.generals[selected.owner] if 0 <= selected.owner and selected.owner < len(gl.generals) else None
        
        self.nextitem.config(text='{0}'.format( selected.next if 0 <= selected.next < item_max else '-'))

        self.ownernum.config(text='{0}'.format('-'))
        self.ownername.delete(0, tk.END)
        ownername = '주인없음'
        if owner is not None:
            self.ownernum.config(text='{0}'.format(owner.num))
            ownername=owner.name
        self.ownername.insert(0, ownername)

        self.market.delete(0, tk.END)
        self.market.insert(0, '{0}'.format(selected.market))

        statname = gl._itemStats_[selected.item_type]
        if 0 >= len(statname):
            statname = '-'
        self.stattype.config(text='{0}'.format(statname))

        itemtype = gl._itemTypes_[selected.item_type]
        self.typename.config(text='{0}'.format(itemtype))

        #self.itemtype.delete(0, tk.END)
        #self.itemtype.insert(0, '{0}'.format( str(selected.item_type)))

        self.itemstats.delete(0, tk.END)
        self.itemstats.insert(0, '{0}'.format( str(selected.stats) if 0 < selected.stats else ''))

        self.itemprice.delete(0, tk.END)
        self.itemprice.insert(0, '{0}'.format( str(selected.price) if 0 < selected.price else ''))        

        for i in range(32):
            val = gl.bit32from(selected.u00, i, 1)
            self.skillv[i].set(val)
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.on_selected_item(index, value)

    def on_check_skills(self, pos):
        if self.item_selected is None:
            return
        self.item_changed = True

        value = self.skillv[pos].get()
        data0 = self.item_selected.u00
        data1 = gl.set_bits(data0, value, pos, 1)

        print('{0}[{1}]: {2:2}[ {3}, {4} ] '.format(self.item_selected.num, self.item_selected.name, pos, format(data0, '032b'), format(data1, '032b')))
        self.item_selected.u00 = data1
        self.item_selected.unpacked[0] = data1

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
            checked = tk.Checkbutton(self.frame_b1, text=name, font=smallfont, variable=var, width=6, height=0, 
                                     highlightthickness=0, borderwidth=0, 
                                     command=lambda i=i: self.on_check_skills(i))
            checked.grid(row=i//4, column=i%4, sticky="w", padx=(4,0),pady=0,ipady=0)
            self.skills.append(checked)
            self.skillv.append(var)

    def save_owner_items(self, owner):
        print("save_owner_items: {0}. {1}[{2}]".format(owner.num, owner.name, owner.item, ))
        if owner is None:
            print("owner empty..")
            return
        
        maxitems = len(gl.items)
        items = [item for item in gl.items if item.owner == owner.num]
        if 0 < len(items):
            owner.unpacked[48] = items[0].num  # 아이템 소유자 정보 갱신
            owner.item = items[0].num  # 아이템 소유자 정보 갱신
            print("소유자 아이템: {0}[{1}], {2}개".format(owner.name, owner.item, len(items),))
            for i, item in enumerate(items):
                next = items[i+1].num if i+1 < len(items) else 255
                if 0 <= next < maxitems:
                    next = next

                print("아이템: {0:3}. {1:3}[{2:3} => {3:3}], {4}".format(i, item.num, next, item.next,item.name))
                if item.next == next:
                    continue

                item.next = next 
                item.unpacked[8] = next
                files.test_save_item_selected( gl._loading_file, item, True)
        else:
            owner.unpacked[48] = 255  # 아이템 소유자 정보 갱신
            owner.item = 255  # 아이템 소유자 정보 갱신

        files.test_save_general_selected(gl._loading_file, 1, owner, True)

    def save_item(self):
        if self.item_selected is None:
            print("아이템 선택 안됨")
            return
                
        if False == self.item_changed:
            print("아이템 변경 없음")
            return 
                
        print("save item..")
        selected = self.item_selected
        max_generals = len(gl.generals)
        
        owner_prev = gl.generals[self.owner_prev] if 0 <= self.owner_prev < max_generals else None
        if owner_prev is not None:
            print("아이템 이전 소유자 저장")
            self.save_owner_items(owner_prev)        

        owner = gl.generals[selected.owner] if 0 <= selected.owner < max_generals else None
        if owner is None:
            selected.owner = 65535
            selected.unpacked[1] = 65535
            selected.next = 255
            selected.unpacked[8] = 255
            files.test_save_item_selected( gl._loading_file, selected, True)
            return
        files.test_save_item_selected( gl._loading_file, selected, True)

        if False == self.owner_changed:
            print("아이템 소유 변경 없음")
            return            
        if self.owner_prev == selected.owner:
            print("아이템 소유 이전과 동일")
            return            
        self.save_owner_items(owner)

    def build_basic(self, parent, nr, nc):
        self.frame_basic = tk.LabelFrame(parent, text="아이템 기본 설정", width=self._width01, height=96)
        self.frame_basic.grid(row=nr, column=nc, pady=0 )
        self.frame_basic.grid_propagate(False)  # 크기 고정
                
        self.frame_b1 = tk.LabelFrame(self.frame_basic, text="", width=self._width01-4, height=28, borderwidth=0, highlightthickness=0)
        self.frame_b1.grid(row=0, column=0, pady=(4, 0))
        self.frame_b1.grid_propagate(False)  # 크기 고정

        self.frame_b2 = tk.LabelFrame(self.frame_basic, text="", width=self._width01-4, height=42, borderwidth=0, highlightthickness=0)
        self.frame_b2.grid(row=1, column=0)
        self.frame_b2.grid_propagate(False)  # 크기 고정

        label = tk.Label(self.frame_b1, text="이름", width=4, anchor="e", )#borderwidth=1, relief="solid", )
        label.grid(row=0, column=0, padx=(0,0))
        self.itemname = tk.Entry(self.frame_b1, width=10 )
        self.itemname.grid(row=0, column=1, padx=(4,0))

        label = tk.Label(self.frame_b1, text="소유", width=4, anchor="e", )#borderwidth=1, relief="solid",)
        label.grid(row=0, column=2, padx=(8,0))
        self.ownername = tk.Entry(self.frame_b1, width=7 )
        self.ownername.grid(row=0, column=3, padx=(4,0))
        self.ownername.bind("<Return>", self.on_enter_ownername)                
        self.ownernum = tk.Label(self.frame_b1, text="-", width=3, anchor="w", )#borderwidth=1, relief="solid",  )
        self.ownernum.grid(row=0, column=4, padx=(0,0))
        self.nextitem = tk.Label(self.frame_b1, text="-", width=2, anchor="w", )#borderwidth=1, relief="solid",  )
        self.nextitem.grid(row=0, column=5, padx=(0,0))        

        
        # 빈칸 추가 Save 버튼때문에
        #label = tk.Label(self.frame_b1, text="", width=4, anchor="e", borderwidth=1, relief="solid",  )
        #label.grid(row=0, column=2, padx=0)

        self.stattype = tk.Label(self.frame_b2, text="-", width=4, anchor="e", )#borderwidth=1, relief="solid", )
        self.stattype.grid(row=0, column=0, padx=(0,0) )
        
        self.itemstats = tk.Entry(self.frame_b2, width=6,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemstats.grid(row=0, column=1, padx=(4,0))
        self.itemstats.bind("<Return>", self.on_enter_stats)

        self.typename = tk.Label(self.frame_b2, text="종류", width=4, anchor="e", )#borderwidth=1, relief="solid",  )
        self.typename.grid(row=0, column=2, padx=(0,0))
        #self.itemtype = tk.Entry(self.frame_b2, width=2,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        #self.itemtype.grid(row=0, column=1, padx=(4,0))        

        label = tk.Label(self.frame_b2, text="가격", width=4, anchor="e", )#borderwidth=1, relief="solid", )
        label.grid(row=1, column=0, padx=(0,0))
        self.itemprice = tk.Entry(self.frame_b2, width=6,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.itemprice.grid(row=1, column=1, padx=(4,0))        

        label = tk.Label(self.frame_b2, text="매매", width=4, anchor="e", )#borderwidth=1, relief="solid", )
        label.grid(row=1, column=2, padx=(4,0))
        self.market = tk.Entry(self.frame_b2, width=2, ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.market.grid(row=1, column=3, padx=(0,0))
        self.market.bind("<Return>", self.on_enter_market)

        self.frame_b3 = tk.LabelFrame(self.frame_b2, text="", width=self._width01-4, height=44, borderwidth=0, highlightthickness=0)
        self.frame_b3.grid(row=0, column=4, rowspan=2, padx=(8,0), pady=(0,0))
        self.frame_b3.grid_propagate(False)  # 크기 고정                

        frame1 = tk.LabelFrame(self.frame_b3, width=96, height=40, highlightbackground="black", highlightthickness=0)
        frame1.pack(padx=(8,0), pady=(0,0), )
        frame1.pack_propagate(False)
        tk.Button( frame1, text="Save Item", height=2, 
                    relief="flat", bd=0,   # 내부 border 제거
                    #borderwidth=1, relief="solid",
                    command=lambda: self.save_item(),).pack(fill=tk.BOTH, padx=(0,0), pady=(0,0), )
        #grid(row=0, column=0, padx=(0,0), pady=(0,0))

    def save_player(self):
        filename = gl._loading_file
        if 0 >= len(filename):
            print("error: file name empty..")
            return
        if False == os.path.exists(filename):
            print("error: file not exist.. ", filename)
            gl._loading_file = ''
            return
        files.save_player_gold(filename)


    def on_enter_ownername(self, event):
        if self.item_selected is None:
            print("error: item not selected..")
            return
        
        selected = self.item_selected
        entri = event.widget
        data0 = entri.get()
        
        value = data0.strip()
        if 0 >= len(value):
            print("error: owner name empty..")
            return
        
        owner = None
        if value.isdigit():
            gn = len(gl.generals)
            try:
                num = int(value)
                if 0 > num or num >= gn:
                    print("overflow: {0}".format(value))
                    return
                owner = gl.generals[num]
            except:
                print('error: {0}'.format(value))
                return
        else:
            # 장수 이름으로 검색
            if '-' != value:
                for i, general in enumerate(gl.generals):
                    if value == general.name:
                        owner = general
                        break
        if owner is None and '-' != value:
            print("error: owner not found: {0}".format(value))
            return
        owner_num, owner_name = (owner.num, owner.name) if owner is not None else (65535, '-')
        print("on_enter_ownername: {0:3}[{1:3}] => {2:3}[{3}]".format(selected.num, selected.owner, owner_num, owner_name))

        self.item_changed = True
        self.owner_changed = True

        self.owner_prev = selected.owner
        
        selected.owner = owner_num
        selected.unpacked[1] = owner_num

        self.ownername.delete(0, tk.END)
        self.ownername.insert(0, owner_name)
        self.ownernum.config(text='{0}'.format(owner_num if 65535 != owner_num else '-'))
        self.nextitem.config(text='{0}'.format(selected.next if 255 != selected.next else '-'))


    def on_enter_stats(self, event):
        entri = event.widget
        value0 = entri.get()
        try:
            if self.item_selected.item_type in (0,2,3,9,10,11):
                print("error: not type {0}, {1}".format(self.item_selected.item_type, value0))
                return
            value1 = int(value0)
            self.item_selected.stats = value1
            self.item_selected.unpacked[7] = value1
            
            self.item_changed = True
            print("on_enter_stats: {0}".format(value1))
        except ValueError:
             print(f"error: stats [{value0}]")

    def on_enter_market(self, event):
        entri = event.widget
        value0 = entri.get()
        try:
            value1 = int(value0)
            if value1 not in (0, 1, 3):
                print("error: out of range {0}".format(value1))
                return
            self.item_selected.market = value1
            self.item_selected.unpacked[2] = value1
            
            self.item_changed = True
            print("on_enter_market: {0}".format(value1))
        except ValueError:
             print(f"error: market [{value0}]")

    def on_enter(self, event):
        entry = event.widget
        key = self.entry_ids[entry]
        try:
            value = int(self.entry_vars[key].get())
            if 0 > value or value > 60000:
                print("error: out of range {0}[{1}]".format(key, value))
                return
            gl.hero_golds = value
            print("on_enter: {0}[{1}]".format(key, value))            
        except ValueError:
             print(f"[{key}] 숫자 아님: {self.entry_vars[key].get()}")

    def build_player(self, parent, nr, nc):
        frame_player = tk.LabelFrame(parent, text="시나리오 기본 설정", width=self._width00+120, height=96, )# borderwidth=0, highlightthickness=0)
        frame_player.grid(row=nr, column=nc, pady=0 )
        frame_player.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_player, text="", width=self._width00+108, height=50, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0, sticky="nsew", pady=(8, 0))
        frame_b1.grid_propagate(False)  # 크기 고정

        tk.Label(frame_b1, text="시나리오", width=8, anchor="e").grid(row=0, column=0, padx=0, pady=0)
        self.current_scene = tk.Entry(frame_b1, width=10,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.current_scene.grid(row=0, column=1, padx=(4,0), pady=0)

        tk.Label(frame_b1, text="게임날짜", width=8, anchor="e").grid(row=0, column=2, padx=0, pady=0)
        self.current_year = tk.Entry(frame_b1, width=4,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.current_year.grid(row=0, column=3, padx=(4,0), pady=0)
        self.current_month = tk.Entry(frame_b1, width=4,  ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.current_month.grid(row=0, column=4, padx=(2,0), pady=0)

        tk.Label(frame_b1, text="이름", width=8, anchor="e").grid(row=1, column=0, padx=(0,0), pady=0)
        self.player_name = tk.Entry(frame_b1, width=10, ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.player_name.grid(row=1, column=1, padx=(4,0), pady=0)        

        tk.Label(frame_b1, text="소지금", width=8, anchor="e").grid(row=1, column=2, padx=0, pady=0)

        var_gold = tk.StringVar()
        self.current_gold = tk.Entry(frame_b1, width=9,  textvariable=var_gold ) # state="disabled", disabledbackground="white", disabledforeground="black")
        self.current_gold.grid(row=1, column=3, columnspan=2, padx=(4,0), pady=0)
        self.current_gold.bind("<Return>", self.on_enter)

        self.entry_vars["소지금"] = var_gold
        self.entry_ids[self.current_gold] = "소지금"


        frame1 = tk.LabelFrame(frame_b1, width=80, height=26, highlightbackground="black", highlightthickness=0)
        frame1.grid(row=1, column=5, padx=(16,0), pady=(0,0),)
        frame1.grid_propagate(False)
        tk.Button( frame1, text="Save Gold", relief="flat", bd=0,   # 내부 border 제거
                    command=lambda: self.save_player(), ).grid(row=0, column=0, padx=(8,0))
        
    def build_tab_item(self, parent, nr, nc):
        self.frame_item = tk.LabelFrame(parent, text="", width=self._width00+136, height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_item.grid(row=nr, column=nc, padx=(4,0), pady=(0,8), sticky="nsew",)
        self.frame_item.grid_propagate(False)  # 크기 고정

        self.frame_00 = tk.LabelFrame(self.frame_item, text="", width=100, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_00.grid(row=0, column=0, padx=(4,0), pady=0,)
        self.frame_00.grid_propagate(False)  # 크기 고정

        owner_filters=[]
        self.owner_filter = ttk.Combobox(self.frame_00, values=owner_filters, width=14, )
        self.owner_filter.pack(side="top", fill="y")
        self.owner_filter.bind("<<ComboboxSelected>>", self.on_selected_owner)

        # 좌측 장수 리스트
        self.frame_listup = tk.LabelFrame(self.frame_00, text="", width=self._width00+136, height=self._height0, )# borderwidth=0, highlightthickness=0, )
        self.frame_listup.pack(side="top", pady=4, fill="y")        

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        scr_height = int((self._height0-32)/16)
        self.lb_items = tk.Listbox(self.frame_listup, height=scr_height, width=14, highlightthickness=0, relief="flat")
        self.lb_items.pack(side="left", pady=0, fill="both", expand=True)
        self.lb_items.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_items.yview)
        self.lb_items.config(yscrollcommand=scrollbar.set)

        self.frame_01 = tk.LabelFrame(self.frame_item, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        self.frame_01.grid(row=0, column=1, sticky='nw',padx=(4,0))
        self.frame_01.grid_propagate(False)  # 크기 고정                

        self.build_basic(self.frame_01, 1, 0) # 기본 설정
        self.build_skills(self.frame_01, 2, 0) # 특기

        self.listup_items() # 특기
