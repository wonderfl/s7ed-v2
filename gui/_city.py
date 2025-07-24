import re

import tkinter as tk
from tkinter import ttk

import globals as gl
from commands import files

class CityTab:
    _width00 = 176
    _width01 = 172

    _height0 = 268
    _height1 = 264

    entries = []

    def __init__(self, tab, nr, nc):
        self.rootframe = tab
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.entries.clear()
        self.build_tab_city(self.rootframe, nr, nc)

    def listup_cities(self):
        self.city_selected = None
        gn = len(gl.generals)
        filters = []
        filters.append("세력전체")
        filters.append("세력없음")        
        for realm in gl.realms:
            if 0 > realm.ruler or realm.ruler >= gn:
                continue
            ruler_name = " {0:3}. {1}".format( realm.num, gl.generals[realm.ruler].name)        
            filters.append(ruler_name)
        
        self.realm_filter['values'] = filters
        self.realm_filter.set("세력전체")

        self.lb_cities.delete(0, tk.END)
        for city in gl.cities:
            self.lb_cities.insert(tk.END, " {0:2}. {1}".format(city.num, city.name))

    def on_city_selected(self, index, value):
        self.city_selected = None
        cn = len(gl.cities)
        if 0 > index or index >= cn:
            print(f"찾을 수 없는 도시 정보입니다: {index}:{value}.")
            return
                
        values = [p for p in re.split(r'[ .,]', value) if p]
        if( 2>len(values)):
            print(f"잘못된 도시 정보입니다: {index}[ {values} ], 전체 도시: {cn}")
            return
        
        _num = int(values[0])
        if 0 > _num or _num >= cn:
            print(f"잘못된 도시 정보입니다: {index}[ {values[0]}, {values[1]} ], 전체 도시: {cn}")
            return
        _name = values[1]

        city_name = gl.cities[_num].name.strip()
        if city_name != _name:
            print(f"잘못된 도시 정보입니다: {index}:{value}, {city_name}")
            return
        
        city = gl.cities[_num]
        self.city_selected = city
        
        gn = len(gl.generals)
        realm_name = '없음'
        rn = len( gl.realms)
        if 0 <= city.realm and city.realm < rn:
            realm = gl.realms[city.realm]
            if 0 <= realm.ruler and realm.ruler < gn:
                realm_name = gl.generals[realm.ruler].name
        self.realm_name.config(text=realm_name)
        
        #realm_namenum = '{0}'.format(city.realm if rn > city.realm else ' -')
        #self.realm_namenum.delete(0, tk.END)
        #self.realm_namenum.insert(0, realm_namenum)
        
        gov_name = '  - '
        if 0 <= city.governor and city.governor < gn:
            gov = gl.generals[city.governor]
            if 1 >= gov.state:
                gov_name = gov.name

        self.city_gov_name.config(text='{0}'.format(gov_name))
        values = [
            city.golds, city.foods, city.peoples*100, 
            city.devs, city.devmax, city.shops, city.shopmax,
            city.secu, city.defs, city.tech,  gl.sentiments[city.num]
        ]
        for i, entri in enumerate(self.entries):
            entri.delete(0, tk.END)
            if 0 <= i and i < len(values):
                entri.insert(0, values[i])
            else:
                print("values: out of range ", i)
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.on_city_selected(index, value)

    def on_realm_selected(self, event):
        self.city_selected = None
        selected = self.realm_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]

        self.realm_num = -1
        if '세력전체' != values[0]:
            if '세력없음' == values[0]:
                self.realm_num = 255
            else:
                self.realm_num = int(values[0]) # 세력 넘버

        #print('filter: {0}, '.format(self.realm_num))
        self.lb_cities.delete(0, tk.END)
        for city in gl.cities:
            if -1 == self.realm_num or ( -1 != self.realm_num and self.realm_num == city.realm):
                self.lb_cities.insert(tk.END, " {0:2}. {1}".format(city.num, city.name))

    def save_city(self):
        if self.city_selected is None:
            print("error: save city: None")
            return
        
        print("save city: {0}".format(self.city_selected.name) )
        files.test_save_city_selected(gl._loading_file, self.city_selected, True)

    def on_enter_city(self, event, num):
        #print("on_enter_city: {0}".format(num))
        entri = event.widget
        value0 = entri.get()
        try:
            value1 = int(value0)
            if 0 == num:
                self.city_selected.golds = value1
                self.city_selected.unpacked[0] = value1
            elif 1 == num:
                self.city_selected.foods = value1
                self.city_selected.unpacked[1] = value1
            elif 2 == num:
                self.city_selected.peoples = int(value1/100)
                self.city_selected.unpacked[4] = self.city_selected.peoples
            elif 3 == num:
                self.city_selected.devs = value1
                self.city_selected.unpacked[5] = value1
            elif 4 == num:
                self.city_selected.devmax = value1
                self.city_selected.unpacked[6] = value1
            elif 5 == num:
                self.city_selected.shops = value1
                self.city_selected.unpacked[7] = value1
            elif 6 == num:
                self.city_selected.shopmax = value1
                self.city_selected.unpacked[8] = value1
            elif 7 == num:
                self.city_selected.secu = value1
                self.city_selected.unpacked[9] = value1
            elif 8 == num:
                self.city_selected.defs = value1
                self.city_selected.unpacked[10] = value1
            elif 9 == num:
                self.city_selected.tech = value1
                self.city_selected.unpacked[11] = value1
            elif 10 == num:
                self.city_selected.city_sentiment = value1
                gl.sentiments[self.city_selected.num] = value1

        except ValueError:
             print(f"error: {num} [{value0}]")

        num1 = num+1
        if num1 >= len(self.entries):
            num1 = 0
        self.entries[num1].focus_set()

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="도시 기본 설정", width=self._width01, height=self._height1-4)
        frame_basic.grid(row=nr, column=nc, )
        frame_basic.grid_propagate(False)  # 크기 고정

        tk.Label(frame_basic, text="세력:", width=4, anchor="e" ).grid(row=0, column=0, padx=(4,0))
        self.realm_name = tk.Label(frame_basic, text="", width=7, anchor="e" )
        self.realm_name.grid(row=0, column=1, padx=0)

        #tk.Button(frame_basic, text="SaveCity", width=6, height=1, relief="flat", command=lambda: self.save_city() ).grid(row=0, column=2, padx=(4,0))
        frame1 = tk.LabelFrame(frame_basic, width=64, height=27, )#highlightbackground="black", highlightthickness=0)
        frame1.grid(row=0, column=2, padx=(8,0), pady=(0,0),)
        frame1.grid_propagate(False)
        tk.Button( frame1, text="Save City", relief="flat", bd=0,   # 내부 border 제거
                    command=lambda: self.save_city(), ).grid(row=0, column=0, padx=(2,0))        

        #         
        #self.realm_namenum = tk.Entry(frame_basic, width=6 )
        #self.realm_namenum.grid(row=0, column=2, padx=0)


        self.entries.clear()

        tk.Label(frame_basic, text="태수:", width=4, anchor="e" ).grid(row=1, column=0, padx=(4,0))
        self.city_gov_name = tk.Label(frame_basic, text="", width=7, anchor="e" )
        self.city_gov_name.grid(row=1, column=1, padx=0)
        #self.city_gov_num = tk.Entry(frame_basic, width=6 )
        #self.city_gov_num.grid(row=1, column=2, padx=0)
        #self.entries.append(self.city_gov_num)

        tk.Label(frame_basic, text="  금:", width=4, anchor="e" ).grid(row=2, column=0, padx=(4,0))
        self.city_golds = tk.Entry(frame_basic, width=7 )
        self.city_golds.grid(row=2, column=1, padx=0)
        self.entries.append(self.city_golds)

        tk.Label(frame_basic, text="식량:", width=4, anchor="e" ).grid(row=3, column=0, padx=(4,0))
        self.city_foods = tk.Entry(frame_basic, width=7 )
        self.city_foods.grid(row=3, column=1, padx=0)
        self.entries.append(self.city_foods)

        tk.Label(frame_basic, text="인구:", width=4, anchor="e" ).grid(row=4, column=0, padx=(4,0))
        self.city_peoples = tk.Entry(frame_basic, width=7 )
        self.city_peoples.grid(row=4, column=1, padx=0)
        self.entries.append(self.city_peoples)

        tk.Label(frame_basic, text="개발:", width=4, anchor="e" ).grid(row=5, column=0, padx=(4,0))
        self.city_devs = tk.Entry(frame_basic, width=7 )
        self.city_devs.grid(row=5, column=1, padx=0)
        self.entries.append(self.city_devs)

        self.city_devmax = tk.Entry(frame_basic, width=8 )
        self.city_devmax.grid(row=5, column=2, padx=0)
        self.entries.append(self.city_devmax)

        tk.Label(frame_basic, text="상업:", width=4, anchor="e" ).grid(row=6, column=0, padx=(4,0))
        self.city_shops = tk.Entry(frame_basic, width=7 )
        self.city_shops.grid(row=6, column=1, padx=0)
        self.entries.append(self.city_shops)

        self.city_shopmax = tk.Entry(frame_basic, width=8 )
        self.city_shopmax.grid(row=6, column=2, padx=0)
        self.entries.append(self.city_shopmax)

        tk.Label(frame_basic, text="치안:", width=4, anchor="e" ).grid(row=7, column=0, padx=(4,0))
        self.city_secu = tk.Entry(frame_basic, width=7 )
        self.city_secu.grid(row=7, column=1, padx=0)
        self.entries.append(self.city_secu)

        tk.Label(frame_basic, text="방어:", width=4, anchor="e" ).grid(row=8, column=0, padx=(4,0))
        self.city_defs = tk.Entry(frame_basic, width=7 )
        self.city_defs.grid(row=8, column=1, padx=0)
        self.entries.append(self.city_defs)

        tk.Label(frame_basic, text="기술:", width=4, anchor="e" ).grid(row=9, column=0, padx=(4,0))
        self.city_tech = tk.Entry(frame_basic, width=7 )
        self.city_tech.grid(row=9, column=1, padx=0)
        self.entries.append(self.city_tech)

        tk.Label(frame_basic, text="민심:", width=4, anchor="e" ).grid(row=10, column=0, padx=(4,0))
        self.city_sentiment = tk.Entry(frame_basic, width=7 )
        self.city_sentiment.grid(row=10, column=1, padx=0)
        self.entries.append(self.city_sentiment)

        for i, entri in enumerate(self.entries):
            entri.bind("<Return>", lambda event, i=i: self.on_enter_city(event,i))


    def build_tab_city(self, parent, nr, nc):
        self.frame_city = tk.LabelFrame(parent, text="", width=self._width00+100, height=self._height0, borderwidth=0, highlightthickness=0 )
        self.frame_city.grid(row=nr, column=nc, padx=(4,0), pady=(0,0))
        self.frame_city.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(self.frame_city, text="", width=80, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        self.frame_1 = tk.LabelFrame(self.frame_city, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0), sticky='sw')
        self.frame_1.grid_propagate(False)  # 크기 고정

        realm_filters=[]
        self.realm_filter = ttk.Combobox(self.frame_0, values=realm_filters, width=10, )
        self.realm_filter.pack(side="top", fill="y")
        self.realm_filter.bind("<<ComboboxSelected>>", self.on_realm_selected)

        # 좌측 장수 리스트
        self.frame_listup = tk.LabelFrame(self.frame_0, text="", width=100, height=self._height0-8, )#borderwidth=0, highlightthickness=0)
        self.frame_listup.pack(side="top", pady=4, fill="y")

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        listbox_height = int((self._height0-32)/16)
        self.lb_cities = tk.Listbox(self.frame_listup, height=listbox_height, width=10, highlightthickness=0, relief="flat")
        self.lb_cities.pack(side="left", pady=0, fill="both", expand=True)
        self.lb_cities.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_cities.yview)
        self.lb_cities.config(yscrollcommand=scrollbar.set)
        
        #for city in gl.cities:
        #    self.lb_cities.insert(tk.END, " {0:2}. {1}".format(city.num, city.name))        

        self.build_basic(self.frame_1, 0, 0) # 기본 설정

        self.listup_cities()