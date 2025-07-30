import re

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import globals as gl

class ListupFrame:
    
    def __init__(self, app, parent, nr, nc):
        self.app = app
        self.rootframe = parent
        self.build_listup(app, parent, nr, nc) # 특기

    def find_item(self, str):
        found = -1
        items = self.lb_generals.get(0, tk.END)
        for i, item in enumerate(items):
            if str not in item:
                continue
            found = i
            break
        print("found:", found, str)
        return found
    
    def focus_generals(self):
        self.lb_generals.focus_set()

    def items(self):        
        return list(self.lb_generals.get(0, tk.END))
    
    def selections(self):
        _indices = self.lb_generals.curselection()
        return [self.lb_generals.get(i) for i in _indices]    

    def focus_num(self, num, now=False):
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(num)             # index 위치 선택
        self.lb_generals.activate(num)                  # 키보드 포커스 이동
        self.lb_generals.see(num)                       # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")
        if True == now:
            self.lb_generals.focus_set()

    def reload_listup(self, listup):        
        self.lb_generals.delete(0, tk.END)
        for general in listup:
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
        self.focus_num(0)

    def listup_generals(self):
        _app = self.app
        _app.general_selected = None

        gn = len(gl.generals)
        realm_filter = []
        realm_filter.append("세력전체")
        realm_filter.append("세력없음")
        for realm in gl.realms:
            if 0 > realm.ruler or realm.ruler >= gn:
                continue
            ruler_name = " {0:3}. {1}".format( realm.num, gl.generals[realm.ruler].name)        
            realm_filter.append(ruler_name)
        
        self.realm_filter['values'] = realm_filter
        self.realm_filter.set("세력전체")

        city_filter=[]
        city_filter.append("도시전체")
        city_filter.append("새로운장수")
        for i, name in enumerate(gl._cityNames_):
            city_filter.append('{0:2}.{1}'.format(i,name))        

        self.city_filter['values'] = city_filter
        self.city_filter.set("도시전체")

        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))        

    def on_selected_general(self, index, value):
        _app = self.app
        _app.general_selected = None

        gn = len(gl.generals)
        values = [p for p in re.split(r'[ .,]', value) if p]
        
        _num = int(values[0])
        if 0 > _num or _num >= gn:
            print(f"잘못된 정보입니다: {index}, {value}, {_num}")
            return

        _selected = gl.generals[_num]
        if _selected.name != values[1]:
            print("'{0}' != '{1}'".format(_selected.name, values[1]))
            print(f"잘못된 이름입니다: {index}, {value}, {values}")
            return        
        _app.general_selected = _selected
        _app.refresh_general(_selected)
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.on_selected_general(index, value)        

    def on_enter_realm(self, event):
        _app = self.app
        if _app.general_selected is None:
            return
        
        entri = event.widget
        try:
            value = int(entri.get())
            if 0 > value or value > 255:
                print("error: overflow.. ", value)
                return
            _app.general_selected.realm = value
            _app.general_selected.unpacked[27] = value
        except:
            print("error:..")            

    def realm_selected(self, event):
        _app = self.app
        _app.general_selected = None

        selected = self.realm_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]

        city_filters = []
        _app.realm_num = -1
        if '세력전체' != values[0]:
            if '세력없음' == values[0]:
                _app.realm_num = 255
            else:
                _app.realm_num = int(values[0]) # 세력 넘버
                city_filters.append("세력전체")

        if -1 == _app.realm_num or 254 <= _app.realm_num:
            city_filters.append("도시전체")
        
        city_filters.append("새로운장수")
        listup=[]
        _app.city_num = -1
        for i, city in enumerate(gl.cities):
            if _app.realm_num != -1 and city.realm != _app.realm_num:
                continue
            city_filters.append('{0:3}. {1}'.format(city.num,city.name))
            listup.append(city.num)

        self.city_filter['values'] = city_filters
        self.city_filter.set("세력전체")
        if -1 == _app.realm_num or 255 == _app.realm_num:
            self.city_filter.set("도시전체")

        #print('filter: {}, {}'.format(self.realm_num, self.city_num))
        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if -1 == _app.realm_num and -1 == _app.city_num:
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue

            if 255 == _app.realm_num and 255 == general.realm:
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue

            if 254 == _app.city_num and 520 <= general.num and general.city in listup: # 새로운 장수만
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue            

            if -1 != _app.realm_num:
                if general.realm == _app.realm_num and general.city in listup:
                    self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))

        self.focus_num(0)
        self.focus_generals()        
         
    def city_selected(self, event):
        _app = self.app
        _app.general_selected = None
        selected = self.city_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]        
        filters = []
        _app.city_num = -1
        if '세력전체' != values[0] and '도시전체' != values[0]:
            if '새로운장수' == values[0]:
                _app.city_num = -2
            else:
                _app.city_num = int(values[0]) # 세력 넘버
            filters.append("세력전체")

        listup=[]
        for i, city in enumerate(gl.cities):
            if 0 <= _app.city_num and ( -1 != _app.realm_num and city.realm != _app.realm_num):
                continue
            if 0 <= _app.city_num and city.num != _app.city_num:
                continue            
            filters.append('{0:3}. {1}'.format(city.num,city.name))
            listup.append(city.num)                    

        print('city selected: 세력[ {0} ], 도시[ {1}, {2} ]'.format(_app.realm_num, _app.city_num, len(listup)))

        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if -1 == _app.city_num and (-1 != _app.realm_num and _app.realm_num != general.realm):
                continue
            if -2 == _app.city_num and (520 > general.num or (-1 != _app.realm_num and _app.realm_num != general.realm)):
                continue
            if general.city not in listup:
                continue
            if -1 != _app.realm_num and _app.realm_num != general.realm:
                continue

            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))

        self.focus_num(0)
        self.focus_generals()

    def build_listup(self, app, parent, nr, nc):
        app.general_selected = None
        gn = len(gl.generals)

        realm_filters=[]
        self.realm_filter = ttk.Combobox(parent, values=realm_filters, width=12, )
        self.realm_filter.pack(side="top", fill="y", pady=(8,0))
        self.realm_filter.bind("<<ComboboxSelected>>", self.realm_selected)

        city_filters=[]
        city_filters.append("도시전체")
        city_filters.append("새로운장수")
        for i, name in enumerate(gl._cityNames_):
            city_filters.append('{0:2}.{1}'.format(i,name))
        self.city_filter = ttk.Combobox(parent, values=city_filters, width=12, )
        self.city_filter.pack(side="top", fill="y", pady=(2,8))  
        self.city_filter.bind("<<ComboboxSelected>>", self.city_selected)

        # 좌측 장수 리스트
        self.frame_listup = tk.LabelFrame(parent, text="", width=100, height=app._height0-48, ) #borderwidth=0, highlightthickness=0)
        self.frame_listup.pack(side="top", pady=0, fill="y")

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y", pady=2)

        str_height = int((app._height0-72)/16)
        self.lb_generals = tk.Listbox(self.frame_listup, selectmode=tk.EXTENDED,
                                      width=12, height=str_height, 
                                      highlightthickness=0, relief="flat")
        self.lb_generals.pack(side="left", pady=2, fill="both", expand=True)
        self.lb_generals.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_generals.yview)
        self.lb_generals.config(yscrollcommand=scrollbar.set)