import re

import tkinter as tk
from tkinter import ttk

import globals as gl

class RealmTab:
    _width00 = 160
    _width01 = 156

    _height0 = 96
    _height1 = 88

    def __init__(self, tab, nr, nc):
        self.rootframe = tab
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.build_tab_realm(self.rootframe, nr, nc)

    def listup_realms(self):
        gn = len(gl.generals)        
        self.lb_realms.delete(0, tk.END)
        for realm in gl.realms:
            if 0 > realm.ruler or realm.ruler >= gn:
                continue
            ruler_name = "{0:2}. {1}".format( realm.num, gl.generals[realm.ruler].name)
            self.lb_realms.insert(tk.END, ruler_name)

    def realm_selected(self, index, value):
        rn = len(gl.realms)
        values = [p for p in re.split(r'[ .,]', value) if p]
        if( 2>len(values)):
            print(f"잘못된 세력 정보입니다: {index}[ {values} ], 전체 세력: {rn}")
            return
        
        _num = int(values[0])
        if 0 > _num or _num >= rn:
            print(f"잘못된 세력 정보입니다: {index}[ {values[0]}, {values[1]} ], 전체 세력: {rn}")
            return
        
        realm = gl.realms[_num]
        ruler_name = '  - '
        gn = len(gl.generals)
        if 0 <= realm.ruler and realm.ruler < gn:
            ruler = gl.generals[realm.ruler]
            ruler_name = ruler.name
            name = values[1]
            if ruler.name != name or realm.num != _num:
                print(f"잘못된 세력 정보입니다:  {index}[ {values[0]}, {values[1]} ],  {realm.num}:{ruler.name}")
                return
        staff_name = gl.generals[realm.staff].name if 0 <= realm.staff and realm.staff < gn else '  - '

        self.realm_num.config(text='{0}'.format(realm.num))
        self.realm_name.delete(0, tk.END)
        self.realm_name.insert(0, '{0}'.format(realm.name))

        self.ruler_name.config(text='{0}'.format(ruler_name))
        self.ruler_num.delete(0, tk.END)
        self.ruler_num.insert(0, '{0}'.format(realm.ruler))

        self.staff_name.config(text='{0}'.format(staff_name))
        self.staff_num.delete(0, tk.END)
        self.staff_num.insert(0, '{0}'.format(realm.staff))        
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            self.realm_selected(index, value)

    def build_basic(self, parent, nr, nc):
        # 기본 설정
        frame_basic = tk.LabelFrame(parent, text="세력 기본 설정", width=self._width01, height=self._height1)
        frame_basic.grid(row=nr, column=nc, )
        frame_basic.grid_propagate(False)  # 크기 고정

        tk.Label(frame_basic, text="세력:", width=4, anchor="e" ).grid(row=0, column=0, padx=(8,0))
        self.realm_num = tk.Label(frame_basic, text="", width=5, anchor="e" )
        self.realm_num.grid(row=0, column=1, padx=(8,0))
        self.realm_name = tk.Entry(frame_basic, width=6 )
        self.realm_name.grid(row=0, column=2, padx=(4,0))

        tk.Label(frame_basic, text="주군:", width=4, anchor="e" ).grid(row=1, column=0, padx=(8,0))
        self.ruler_name = tk.Label(frame_basic, text="-", width=5, anchor="e" )
        self.ruler_name.grid(row=1, column=1, padx=(8,0))
        self.ruler_num = tk.Entry(frame_basic, width=6 )
        self.ruler_num.grid(row=1, column=2, padx=(4,0))

        tk.Label(frame_basic, text="참모:", width=4, anchor="e" ).grid(row=2, column=0, padx=(8,0))
        self.staff_name = tk.Label(frame_basic, text="-", width=5, anchor="e" )
        self.staff_name.grid(row=2, column=1, padx=(8,0))
        self.staff_num = tk.Entry(frame_basic, width=6 )
        self.staff_num.grid(row=2, column=2, padx=(4,0))

    def build_tab_realm(self, parent, nr, nc):
        print("build tab")
        self.frame_realm = tk.LabelFrame(parent, text="", width=self._width00+100, height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_realm.grid(row=nr, column=nc, padx=(4,0))
        self.frame_realm.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_20 = tk.LabelFrame(self.frame_realm, text="", width=80, height=self._height0-8, )
        self.frame_20.grid(row=0, column=0, padx=(4,0))
        self.frame_20.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_20, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        listbox_height = int((self._height0-8)/16)
        self.lb_realms = tk.Listbox(self.frame_20, height=listbox_height, width=10, highlightthickness=0, relief="flat")
        self.lb_realms.pack(side="left", fill="both", expand=True)
        self.lb_realms.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_realms.yview)
        self.lb_realms.config(yscrollcommand=scrollbar.set)
        gn = len(gl.generals)
        for realm in gl.realms:
            if 0 > realm.ruler or realm.ruler >= gn:
                continue
            ruler_name = "{0:2}. {1}".format( realm.num, gl.generals[realm.ruler].name)
            self.lb_realms.insert(tk.END, ruler_name)

        frame_1 = tk.LabelFrame(self.frame_realm, text="", width=self._width00, height=self._height1, borderwidth=0, highlightthickness=0)
        frame_1.grid(row=0, column=1, padx=(4,0))
        frame_1.grid_propagate(False)  # 크기 고정

        self.build_basic(frame_1, 0, 0)

        print("build realm")
        