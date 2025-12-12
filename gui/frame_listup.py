import re

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import globals as gl

class ListupFrame:
    
    def __init__(self, tab, frame, nr, nc):
        self.parentTab = tab
        self.rootframe = frame
        self.build_listup(tab, frame, nr, nc) # 특기

    def find_item_num(self, num):
        found = -1
        key= "{0:3}".format(num)
        children = self.lb_generals.get_children()
        for i, iid in enumerate(children):
            item = self.lb_generals.item(iid, 'values')
            #print("find:", num, item[0], num==item[0])
            if key != item[0]:
                continue
            found = i
            break

        # items = self.lb_generals.get(0, tk.END)
        # for i, item in enumerate(items):
        #     if str not in item:
        #         continue
        #     found = i
        #     break

        print("found:", found, num)
        return found
    
    def focus_generals(self):
        self.lb_generals.focus_set()

    def items(self):        
        return self.lb_generals.get_children()
    
    def selections(self):
        selected = self.lb_generals.selection()
        if not selected:
            return None
        return [self.lb_generals.item(i,'values') for i in selected]
    
    def index_selected(self):
        selected = self.lb_generals.selection()
        if not selected:
            return -1
        children = self.lb_generals.get_children()
        return children.index(selected[0])

    def focus_num(self, num, now=False):
        if num < 0:
            return
        items = self.lb_generals.get_children()
        if num >= len(items):
            return
        iid = items[num]

        # 선택 해제
        selections = self.lb_generals.selection()
        self.lb_generals.selection_remove(*selections)
        self.lb_generals.selection_set(iid)             # index 위치 선택        
        self.lb_generals.focus(iid)
        if True == now:
            self.lb_generals.see(iid)

        #self.lb_generals.selection_remove(*items)
        
        # self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        # self.lb_generals.selection_set(num)             # index 위치 선택
        # self.lb_generals.activate(num)                  # 키보드 포커스 이동
        # self.lb_generals.see(num)                       # 해당 항목이 보이도록 스크롤
        # self.lb_generals.event_generate("<<ListboxSelect>>")
        # if True == now:
        #     self.lb_generals.focus_set()

    def reload_listup(self, listup):        
        #self.lb_generals.delete(0, tk.END)
        self.lb_generals.delete(*self.lb_generals.get_children())
        for general in listup:
            #self.lb_generals.insert(tk.END, general.profile())
            self.lb_generals.insert("", "end", values=general.profile())
        self.focus_num(0)

    def listup_generals(self):
        _app = self.parentTab
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
        _app.realm_num = -1

        city_filter=[]
        city_filter.append("도시전체")
        city_filter.append("새로운장수")
        for i, name in enumerate(gl._cityNames_):
            city_filter.append('{0:2}.{1}'.format(i,name))        

        self.city_filter['values'] = city_filter
        self.city_filter.set("도시전체")        
        _app.city_num = -1

        #self.lb_generals.delete(0, tk.END)
        self.lb_generals.delete(*self.lb_generals.get_children())
        for general in gl.generals:
            #self.lb_generals.insert(tk.END, general.profile())
            self.lb_generals.insert("", "end", values=general.profile())

    def on_selected_general(self, index, values):
        _app = self.parentTab
        _app.general_selected = None

        gn = len(gl.generals)
        #values = [p for p in re.split(r'[ .,]', value) if p]
        #values = tree.item(iid, 'values')  # 컬럼 모드일 경우
        
        _num = int(values[0])
        if 0 > _num or _num >= gn:
            print(f"잘못된 정보입니다: {index}, {values}, {_num}")
            return

        _selected = gl.generals[_num]
        if _selected.name != values[2]:
            print("'{0}' != '{1}'".format(_selected.name, values[1]))
            print(f"잘못된 이름입니다: {index}, {values}, {values}")
            return        
        _app.general_selected = _selected
        _app.refresh_general(_selected)
        
    def on_selected(self, event):
        tree = event.widget
        selection = tree.selection()
        if selection:
            iid = selection[0]
            #value = widget.item(iid, 'text').strip()
            values = tree.item(iid, 'values')
            self.on_selected_general(iid, values)        

    def on_enter_realm(self, event):
        _app = self.parentTab
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
        _app = self.parentTab
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
        #self.lb_generals.delete(0, tk.END)
        self.lb_generals.delete(*self.lb_generals.get_children())
        for general in gl.generals:
            if -1 == _app.realm_num and -1 == _app.city_num:
                #self.lb_generals.insert(tk.END, general.profile())
                self.lb_generals.insert("", "end", values=general.profile())
                continue

            if 255 == _app.realm_num and 255 == general.realm:
                #self.lb_generals.insert(tk.END, general.profile())
                self.lb_generals.insert("", "end", values=general.profile())
                continue

            if 254 == _app.city_num and 520 <= general.num and general.city in listup: # 새로운 장수만
                #self.lb_generals.insert(tk.END, general.profile())
                self.lb_generals.insert("", "end", values=general.profile())
                continue            

            if -1 != _app.realm_num:
                if general.realm == _app.realm_num and general.city in listup:
                    #self.lb_generals.insert(tk.END, general.profile())
                    self.lb_generals.insert("", "end", values=general.profile())

        self.focus_num(0)
        self.focus_generals()        
         
    def city_selected(self, event):
        _app = self.parentTab
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

        #self.lb_generals.delete(0, tk.END)
        self.lb_generals.delete(*self.lb_generals.get_children())
        for general in gl.generals:
            if -1 == _app.city_num and (-1 != _app.realm_num and _app.realm_num != general.realm):
                continue
            if -2 == _app.city_num and (520 > general.num or (-1 != _app.realm_num and _app.realm_num != general.realm)):
                continue
            if general.city not in listup:
                continue
            if -1 != _app.realm_num and _app.realm_num != general.realm:
                continue

            #self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
            self.lb_generals.insert("", "end", values=general.profile())

        self.focus_num(0)
        self.focus_generals()

    def build_listup(self, app, parent, nr, nc):
        app.general_selected = None
        gn = len(gl.generals)

        realm_filters=[]
        self.realm_filter = ttk.Combobox(parent, values=realm_filters, width=16, )
        self.realm_filter.pack(side="top", fill="both", pady=(8,0))
        self.realm_filter.bind("<<ComboboxSelected>>", self.realm_selected)

        city_filters=[]
        city_filters.append("도시전체")
        city_filters.append("새로운장수")
        for i, name in enumerate(gl._cityNames_):
            city_filters.append('{0:2}.{1}'.format(i,name))
        self.city_filter = ttk.Combobox(parent, values=city_filters, width=16, )
        self.city_filter.pack(side="top", fill="both", pady=(2,8))  
        self.city_filter.bind("<<ComboboxSelected>>", self.city_selected)

        # 좌측 장수 리스트
        self.frame_listup = tk.LabelFrame(parent, text="", width=10, height=app._height0-48, borderwidth=0, highlightthickness=0)
        self.frame_listup.pack(side="top", pady=0, fill="y")

        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(size=8, weight="normal")
        # str_height = int((app._height0-72)/16)
        # self.lb_generals = tk.Listbox(self.frame_listup, selectmode=tk.EXTENDED, font=fixed_font,
        #                               width=20, height=str_height, 
        #                               highlightthickness=0, relief="flat")
        # self.lb_generals.pack(side="left", pady=2, fill="both", expand=True)
        # self.lb_generals.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        


        # TkFixedFont 가져오기
        #fixed_font = tkfont.nametofont("TkFixedFont")
        #tree_font = fixed_font.copy()
        #tree_font.configure(size=20, weight="normal")
        tree_font = ("굴림체", 9)
        #print("현재 적용된 폰트:", tree_font.actual())

        style = ttk.Style()
        #style.theme_use('default')  # 중요: native 스타일 말고 default 스타일 사용
        #style.configure("Treeview", rowheight=18, font=tree_font)        
        style.configure("Treeview", rowheight=20, font=tree_font, )

        self.columns=("num","realm","name","birth","turned","loyalty","str","int","pol","chr")
        texts=("no.","rlm","name","bth","turn","lty","str","int","pol","chr")
        tree = ttk.Treeview(self.frame_listup, height=20, 
                            style="Treeview", 
                            selectmode='extended', 
                            columns=self.columns, 
                            show="headings", )
        
        tree.pack(side='left',fill="x", expand=True)        
        # tree.heading("num", text="no.")
        # tree.heading("name", text="이름")
        # tree.heading("loyalty", text="충성")
        # tree.heading("realm", text="세력")
        # 헤더 클릭 이벤트에 정렬 함수 연결
        for i, col in enumerate(self.columns):
            tree.heading(col, text=texts[i], command=lambda c=col: self.sort_by_column(c))

        tree.column("num", width=28, anchor="e", stretch=False)
        tree.column("realm", width=26, anchor="e", stretch=False)
        tree.column("name", width=54, anchor="center", stretch=False)
        tree.column("birth", width=26, anchor="e", stretch=False)
        tree.column("turned", width=26, anchor="e", stretch=False)
        tree.column("loyalty", width=26, anchor="e", stretch=False)
        tree.column("str", width=26, anchor="e", stretch=False)
        tree.column("int", width=26, anchor="e", stretch=False)
        tree.column("pol", width=26, anchor="e", stretch=False)
        tree.column("chr", width=26, anchor="e", stretch=False)


        tree.bind("<<TreeviewSelect>>", self.on_selected)       # 선택될 때        
        tree.bind("<Control-a>", self.select_all)
        tree.bind("<Control-A>", self.select_all)  # 대소문자 구분 없이

        self.sort_state = {col: False for col in self.columns}



        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y", pady=2)        
        scrollbar.config(command=tree.yview, width=12)
        
        tree.config(yscrollcommand=scrollbar.set)        
        self.lb_generals = tree


    def select_all(self, event):
        self.lb_generals.selection_set(self.lb_generals.get_children())
        return "break"  # 기본 동작 방지 (예: 다른 위젯으로 포커스 이동)

    # 정렬 함수
    def sort_by_column(self, col):
        items = list(self.lb_generals.get_children())
        values = [(self.lb_generals.set(iid, col), iid) for iid in items]

        # 데이터 타입에 따라 정렬
        try:
            values.sort(key=lambda x: int(x[0]), reverse=self.sort_state[col])
        except ValueError:
            values.sort(key=lambda x: x[0], reverse=self.sort_state[col])

        # 아이템 재배치
        for index, (_, iid) in enumerate(values):
            self.lb_generals.move(iid, '', index)

        # 정렬 방향 반전 저장
        self.sort_state[col] = not self.sort_state[col]