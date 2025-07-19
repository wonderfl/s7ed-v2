import tkinter as tk
from tkinter import ttk

import globals as gl

class CityTab:
    _width00 = 160
    _width01 = 156

    _height0 = 264
    _height1 = 256

    entries = []

    def __init__(self, tab, nr, nc):
        self.rootframe = tab
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.build_tab_city(self.rootframe, nr, nc)

    def city_selected(self, index, value):
        cn = len(gl.cities)
        if 0 > index or index >= cn:
            print(f"찾을 수 없는 도시 정보입니다: {index}:{value}.")
            return
        city_name = gl.cities[index].name.strip()
        if city_name != value:
            print(f"잘못된 도시 정보입니다: {index}:{value}, {city_name}")
            return
        city = gl.cities[index]
        self.city_num.config(text='{0}'.format(city.num))
        
        self.city_name.delete(0, tk.END)
        self.city_name.insert(0, '{0}'.format(city.name))
        
        gov_name = '  - '
        gn = len(gl.generals)
        if 0 <= city.governor and city.governor < gn:
            gov = gl.generals[city.governor]
            gov_name = gov.name

        self.city_gov_name.config(text='{0}'.format(gov_name))
        values = [
            city.governor, city.golds, city.foods, city.peoples*100, 
            city.devs, city.devmax, city.shops, city.shopmax,
            city.secu, city.tech, city.defs, gl.sentiments[city.num]
        ]
        for i, entri in enumerate(self.entries):
            entri.delete(0, tk.END)
            entri.insert(0, values[i])
        
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.city_selected(index, value)

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="도시 기본 설정", width=self._width01, height=self._height1)
        frame_basic.grid(row=nr, column=nc, )
        frame_basic.grid_propagate(False)  # 크기 고정

        tk.Label(frame_basic, text="도시:", width=4, anchor="e" ).grid(row=0, column=0, padx=(4,0))
        self.city_num = tk.Label(frame_basic, text="", width=6, anchor="e" )
        self.city_num.grid(row=0, column=1, padx=0)
        self.city_name = tk.Entry(frame_basic, width=6 )
        self.city_name.grid(row=0, column=2, padx=0)

        tk.Label(frame_basic, text="태수:", width=4, anchor="e" ).grid(row=1, column=0, padx=(4,0))
        self.city_gov_name = tk.Label(frame_basic, text="", width=7, anchor="e" )
        self.city_gov_name.grid(row=1, column=1, padx=0)
        self.city_gov_num = tk.Entry(frame_basic, width=6 )
        self.city_gov_num.grid(row=1, column=2, padx=0)
        self.entries.append(self.city_gov_num)

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
        self.city_devmax = tk.Entry(frame_basic, width=6 )
        self.city_devmax.grid(row=5, column=2, padx=0)
        self.entries.append(self.city_devmax)

        tk.Label(frame_basic, text="상업:", width=4, anchor="e" ).grid(row=6, column=0, padx=(4,0))
        self.city_shops = tk.Entry(frame_basic, width=7 )
        self.city_shops.grid(row=6, column=1, padx=0)
        self.entries.append(self.city_shops)
        self.city_shopmax = tk.Entry(frame_basic, width=6 )
        self.city_shopmax.grid(row=6, column=2, padx=0)
        self.entries.append(self.city_shopmax)

        tk.Label(frame_basic, text="치안:", width=4, anchor="e" ).grid(row=7, column=0, padx=(4,0))
        self.city_secu = tk.Entry(frame_basic, width=7 )
        self.city_secu.grid(row=7, column=1, padx=0)
        self.entries.append(self.city_secu)

        tk.Label(frame_basic, text="기술:", width=4, anchor="e" ).grid(row=8, column=0, padx=(4,0))
        self.city_tech = tk.Entry(frame_basic, width=7 )
        self.city_tech.grid(row=8, column=1, padx=0)
        self.entries.append(self.city_tech)

        tk.Label(frame_basic, text="방어:", width=4, anchor="e" ).grid(row=9, column=0, padx=(4,0))
        self.city_defs = tk.Entry(frame_basic, width=7 )
        self.city_defs.grid(row=9, column=1, padx=0)
        self.entries.append(self.city_defs)

        tk.Label(frame_basic, text="민심:", width=4, anchor="e" ).grid(row=10, column=0, padx=(4,0))
        self.city_sentiment = tk.Entry(frame_basic, width=7 )
        self.city_sentiment.grid(row=10, column=1, padx=0)
        self.entries.append(self.city_sentiment)


    def build_tab_city(self, parent, nr, nc):
        self.frame_city = tk.LabelFrame(parent, text="", width=self._width00+120, height=self._height0, borderwidth=0, highlightthickness=0 )
        self.frame_city.grid(row=nr, column=nc, padx=(4,0), pady=(8,8))
        self.frame_city.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(self.frame_city, text="", width=100, height=self._height0-8,)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_0, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        listbox_height = int((self._height0-8)/16)
        self.lb_cities = tk.Listbox(self.frame_0, height=listbox_height, width=12, highlightthickness=0, relief="flat")
        self.lb_cities.pack(side="left", fill="both", expand=True)
        self.lb_cities.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_cities.yview)
        self.lb_cities.config(yscrollcommand=scrollbar.set)
        for city in gl.cities:
            self.lb_cities.insert(tk.END, " {0}".format(city.name))

        self.frame_1 = tk.LabelFrame(self.frame_city, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정
        
        self.build_basic(self.frame_1, 0, 0) # 기본 설정