import re

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from PIL import Image, ImageTk

import globals as gl
from . import _city
from . import _realm
from . import _popup

from . import char_basic as basic
from . import gui

from commands import files

class GeneralTab:

    _width00 = 284
    _width01 = 280

    _width10 = 328
    _width11 = 320

    _height0 = 520

    realm_num = -1
    city_num = -1

    image_height = 100
    image_width = int(image_height*0.8)

    skills=[]
    skillv=[]
    equips=[]
    equipv=[]

    stats=[]
    trains=[]

    wins=[]
    captures=[]
    personalities=[]

    def __init__(self, tab):
        self.rootframe = tk.Frame(tab)
        self.rootframe.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.build_tab_general(self.rootframe, 0, 0)
        return
    
    def listup_generals(self):        
        self.general_selected = None

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

        self.city_filter.set("도시전체")

        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))

        _num = gl._player_num

        self.lb_generals.focus_set()
        self.lb_generals.selection_clear(_num, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(_num)               # index 위치 선택
        self.lb_generals.activate(_num)                    # 키보드 포커스 이동
        self.lb_generals.see(_num)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")

        if _popup.ItemPopup._instance is not None:
            print("listup_items")
            _popup.ItemPopup._instance.frame_item.listup_items()

    def refresh_general(self, selected ):
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

        self.num.delete(0, tk.END)
        self.num.insert(0, selected.num)

        self.family.delete(0, tk.END)
        self.family.insert(0, selected.family)

        self.parents.delete(0, tk.END)        
        parent = selected.parent
        if 65535 == parent:
            parent = ' -'
        self.parents.insert(0, parent)

        _png = 'gui/png/face{0:03}.png'.format(selected.faceno)

        _image00 = Image.open(_png)  # 파일명 경로 지정  
        _resized = _image00.resize((self.image_width,self.image_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(_resized)        

        #face_label = tk.Label(frame_b0, width=96, height=120, )
        #face_label.grid(row=0, column=0, padx=(4,4))
        #canvas = tk.Canvas(self.frame_image, width=_resized.width, height=_resized.height)
        #canvas.pack()
        if self.image_created:
            self.canvas.delete(self.image_created)
        self.image_created = self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

        self.traitv.set(selected.job)        
        
        for i in range(32):
            self.skillv[i].set(gl.bit32from(selected.props, i, 1))
        for i in range(14):
            self.equipv[i].set(gl.bit16from2(selected.equips, i, 1))

        stats=[selected.str,selected.int,selected.pol,selected.chr]
        for i, stat in enumerate(stats):
            self.stats[i].delete(0, tk.END)
            self.stats[i].insert(0, stat)

        trains=[selected.str1,selected.int1,selected.pol1,selected.chr1]
        for i, exp in enumerate(trains):
            self.trains[i].delete(0, tk.END)
            self.trains[i].insert(0, exp)

        relation = gl.relations[selected.num] if 0 <= selected.num and selected.num < len(gl.generals) else 0
        #relation = relation if relation < 100 else 100
        #fields = ["탄생","등장","사관","수명", "성장","상성","야망","의리", "용맹","냉정","명성","공적", "봉록","행동력","병사","훈련", "충성","아이템"]
        self.personalities_value=[
            selected.birthyear, selected.appearance, selected.employment, selected.lifespan,
            selected.growth, selected.relation, selected.ambition, selected.fidelity,
            selected.valour, selected.composed, selected.fame, selected.achieve,
            selected.salary, selected.actions, selected.soldier, selected.training,
            selected.loyalty, selected.item, relation
        ]
        for i, value in enumerate(self.personalities_value):
            self.personalities[i].delete(0, tk.END)
            self.personalities[i].insert(0, value)

        wins=[ selected.wins1, selected.wins2]
        for i, win in enumerate(wins):
            self.wins[i].delete(0, tk.END)
            self.wins[i].insert(0, win)
        self.health.set(gl._healthStates_[ selected.injury if 8 > selected.injury else 0])

        captures=[selected.capture_ruler, selected.ambush_realm,selected.operate_realm, selected.capture_cnt, selected.ambush_cnt,selected.operate_cnt]
        for i, value in enumerate(captures):
            self.captures[i].delete(0, tk.END)
            if 65535 == value or 255 == value:
                value = ' -'
            self.captures[i].insert(0, value)
        
        self.tendency.set(gl._tendencies_[ selected.tendency if 4 > selected.tendency else 0])
        self.strategy.set(gl._strategies_[ selected.strategy if 7 > selected.strategy else 0])

        self.realm.delete(0, tk.END)
        self.realm.insert(0, selected.realm)

        self.city.set(gl._cityNames_[ selected.city if 54 > selected.city else 54])
        self.state.set(gl._stateNames2[ selected.state if 7 > selected.state else 7])
        self.rank.set(gl._rankNames_[ selected.rank if 4 > selected.rank else 4])

        self.colleague.delete(0, tk.END)
        self.colleague.insert(0, selected.colleague)          

    def on_selected_general(self, index, value):
        #print(f"선택된 항목 처리: {value}")
        self.general_selected = None

        gn = len(gl.generals)
        values = [p for p in re.split(r'[ .,]', value) if p]
        
        _num = int(values[0])
        if 0 > _num or _num >= gn:
            print(f"잘못된 정보입니다: {index}, {value}, {_num}")
            return

        selected = gl.generals[_num]
        if selected.name != values[1]:
            print(f"잘못된 이름입니다: {index}, {value}, {values}")
            return        
        self.general_selected = selected

        self.refresh_general(selected)
        
    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            #print(f"[선택] {index}: {value}")
            # 선택시 호출할 함수
            self.on_selected_general(index, value)

    def entry_row(self, frame, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2)
            tk.Entry(frame, width=width ).grid(row=0, column=i * 2 + 1)

    def append_entries(self, frame, entries, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2)
            entry = tk.Entry(frame, width=width )
            entry.grid(row=0, column=i * 2 + 1)
            entries.append(entry)\
            
    def on_enter_num(self, event):
        gn = len(gl.generals)        
        value1 = self.num.get()
        try:
            num = int(value1)
            if 0 > num or num >= gn:
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))            
            
        #selected = gl.generals[num]
        strkey = " {0:3}. ".format(num)

        items = self.lb_generals.get(0, tk.END)
        found = 0
        for i, item in enumerate(items):
            if strkey not in item:
                continue
            found = i
            break
        print("found:", found, strkey)

        self.lb_generals.selection_clear(0, tk.END)   # 기존 선택 해제
        self.lb_generals.selection_set(found)         # index 위치 선택
        self.lb_generals.activate(found)              # 키보드 포커스 이동
        self.lb_generals.see(found)                   # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")
        self.lb_generals.focus_set()

    def on_enter_family(self, event):
        gn = len(gl.generals)        
        value1 = self.family.get()
        try:
            num = int(value1)
            if 0 > num or num >= gn:
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))            
            
        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if num != general.family:
                continue
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))            

        #self.lb_generals.focus_set()
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(0)               # index 위치 선택
        self.lb_generals.activate(0)                    # 키보드 포커스 이동
        self.lb_generals.see(0)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")

    def on_enter_name0(self, event):
        gn = len(gl.generals)        
        value1 = self.name0.get()

        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if value1 != general.name0:
                continue
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))            

        #self.lb_generals.focus_set()
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(0)               # index 위치 선택
        self.lb_generals.activate(0)                    # 키보드 포커스 이동
        self.lb_generals.see(0)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")        

    def on_enter_parent(self, event):
        gn = len(gl.generals)        
        value1 = self.parents.get()
        try:
            num = int(value1)
            if num > 65535:
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))            
            
        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if num != general.parent:
                continue
            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))            

        #self.lb_generals.focus_set()
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(0)               # index 위치 선택
        self.lb_generals.activate(0)                    # 키보드 포커스 이동
        self.lb_generals.see(0)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")                


    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="무장 기본 설정", width=self._width01, height=self.image_height+38)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정

        frame_b0 = tk.LabelFrame(frame_basic, text="", )#borderwidth=0, highlightthickness=0)
        frame_b0.grid(row=0, column=0, rowspan=3, ipadx=0,ipady=0, pady=(8,0))
        frame_b0.grid_propagate(False)  # 크기 고정
        self.frame_image = frame_b0

        self.canvas = tk.Canvas(self.frame_image, width=self.image_width, height=self.image_height)
        self.canvas.pack()
        self.image_created = None
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-96, height=64, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=1, padx=(4,0))
        frame_b1.grid_propagate(False)  # 크기 고정        

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-96, height=30, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=1, padx=(4,0), pady=(0,0))
        frame_b2.grid_propagate(False)  # 크기 고정 

        tk.Label(frame_b1, text="번호",).grid(row=0, column=0,)
        entri0 = tk.Entry(frame_b1, width=4, )
        entri0.grid(row=0, column=1, padx=(0,0))
        entri0.bind("<Return>", lambda event: self.on_enter_num(event))  # Enter 키 입력 시 호출
        self.num=entri0

        tk.Label(frame_b1, text="얼굴").grid(row=0, column=2)
        self.face = tk.Entry(frame_b1, width=4)
        self.face.grid(row=0, column=3)        

        tk.Label(frame_b1, text="가문", width=4,).grid(row=1, column=0, padx=(0,0))
        entri1 = tk.Entry(frame_b1, width=4)
        entri1.grid(row=1, column=1)
        entri1.bind("<Return>", lambda event: self.on_enter_family(event))  # Enter 키 입력 시 호출
        self.family=entri1

        tk.Label(frame_b1, text="부모", width=4,).grid(row=1, column=2, padx=(0,0))
        entri2 = tk.Entry(frame_b1, width=4)
        entri2.grid(row=1, column=3)
        entri2.bind("<Return>", lambda event: self.on_enter_parent(event))  # Enter 키 입력 시 호출
        self.parents=entri2                                

        #entry_row(frame_b1, ["성", "명", "자"])
        tk.Label(frame_b1, text="성").grid(row=2, column=0, padx=(8,0))
        self.name0 = tk.Entry(frame_b1, width=4 )
        self.name0.bind("<Return>", lambda event: self.on_enter_name0(event))  # Enter 키 입력 시 호출
        self.name0.grid(row=2, column=1)

        tk.Label(frame_b1, text="명").grid(row=2, column=2, padx=(8,0))
        self.name1 = tk.Entry(frame_b1, width=4 )
        self.name1.grid(row=2, column=3)

        #tk.Label(frame_b1, text="자").grid(row=1, column=4, padx=(8,0))
        self.name2 = tk.Entry(frame_b1, width=5 )
        self.name2.grid(row=2, column=5, padx=(0,0))


        #tk.Label(frame_b1, text="별명").grid(row=0, column=8)
        #tk.Entry(frame_b1, width=6 ).grid(row=0, column=11)

        tk.Label(frame_b2, text="행동").grid(row=0, column=0)
        self.turnv = tk.IntVar()
        self.turned = tk.Checkbutton(frame_b2, text="", variable=self.turnv)
        self.turned.grid(row=0, column=1, padx=(0,0))        

        self.genderv = tk.IntVar()
        tk.Label(frame_b2, text="성별").grid(row=0, column=2, padx=(2,0))
        tk.Radiobutton(frame_b2, text="남", variable=self.genderv, value=0).grid(row=0, column=3)
        tk.Radiobutton(frame_b2, text="여", variable=self.genderv, value=1).grid(row=0, column=4)
        


    # def build_family(self, parent, nr, nc):
    #     frame_family = tk.LabelFrame(parent, text="무장 혈연", width=self._width01, height=44)
    #     frame_family.grid(row=nr, column=nc, pady=(4,0) )
    #     frame_family.grid_propagate(False)  # 크기 고정

    #     tk.Label(frame_family, text="가문", width=4,).grid(row=0, column=0, padx=(2,0))
    #     entri1 = tk.Entry(frame_family, width=4)
    #     entri1.grid(row=0, column=1)
    #     tk.Button(frame_family, text="표시", width=3, borderwidth=0, highlightthickness=0).grid(row=0, column=2)
    #     self.family=entri1

    #     tk.Label(frame_family, text="부모", width=4,).grid(row=0, column=3, padx=(4,0))
    #     entri2 = tk.Entry(frame_family, width=5)
    #     entri2.grid(row=0, column=4)
    #     tk.Button(frame_family, text="표시", width=3, borderwidth=0, highlightthickness=0).grid(row=0, column=5)
    #     self.parents=entri2

    def build_stats(self, parent, nr, nc):
        frame_stats = tk.LabelFrame(parent, text="무장 능력", width=self._width01, height=44)
        frame_stats.grid(row=nr, column=nc, pady=(4,0) )
        frame_stats.grid_propagate(False)  # 크기 고정

        self.append_entries(frame_stats, self.stats, ["무력", "지력", "정치", "매력"], width=4)
        for i, entri in enumerate(self.stats):
            entri.bind("<Return>", lambda event, i=i: self.on_enter_stats(event, i))  # Enter 키 입력 시 호출

    def on_enter_stats(self, event, num):

        if self.general_selected is None:
            return
        if 0 > num or num > 3:
            return
        
        ix = 29 + num
        value0 = self.stats[num].get()
        
        print('stats: {0}, {1}'.format(num, value0))
        try:
            value1 = int(value0)            
            self.general_selected.unpacked[ix] = value1
            
            self.general_selected.str = self.general_selected.unpacked[29]
            self.general_selected.int = self.general_selected.unpacked[30]
            self.general_selected.pol = self.general_selected.unpacked[31]
            self.general_selected.chr = self.general_selected.unpacked[32]

        except:
            print('error: {0}, {1}'.format(num, value0))

    def build_traits(self, parent, nr, nc):
        frame_traits = tk.LabelFrame(parent, text="무장 특성", width=self._width01, height=64)
        frame_traits.grid(row=nr, column=nc, pady=(4,0) )
        frame_traits.grid_propagate(False)  # 크기 고정
        
        self.traitv = tk.IntVar()
        for i, label in enumerate(["무력", "지력", "정치", "매력","장군", "군사", "만능", "평범"]):
            tk.Radiobutton(frame_traits, text=label, variable=self.traitv, value=i, width=6, height=1, highlightthickness=0, borderwidth=0).grid(row=i//4, column=i%4)                
    
    def on_check_skills(self, pos):
        if self.general_selected is None:
            return
        selected = self.general_selected
        value = self.skillv[pos].get()
        data0 = selected.props
        data1 = gl.set_bits(data0, value, pos, 1)

        print('{0}[{1}]: {2:2}[ {3}, {4} ] '.format(selected.num, selected.name, pos, format(data0, '032b'), format(data1, '032b')))
        selected.props = data1
        selected.unpacked[0] = data1

    def on_check_equips(self, pos):
        if self.general_selected is None:
            return
        selected = self.general_selected
        value = self.equipv[pos].get()
        data0 = selected.equips
        data1 = gl.set_bits(data0, value, pos, 1)

        print('{0}[{1}]: {2:2}[ {3}, {4} ] '.format(selected.num, selected.name, pos, format(data0, '016b'), format(data1, '016b')))
        selected.equips = data1
        selected.unpacked[16] = data1        

    def build_skills(self, parent, nr, nc):
        frame_skills = tk.LabelFrame(parent, text="무장 특기", width=self._width01, height=152)
        frame_skills.grid(row=nr, column=nc, pady=(4,0) )
        frame_skills.grid_propagate(False)  # 크기 고정

        frame_skill_box = tk.LabelFrame(frame_skills, text="", width=self._width01-4, height=124, borderwidth=0, highlightthickness=0)
        frame_skill_box.grid(row=0, column=0, pady=(4, 0))
        frame_skill_box.grid_propagate(False)  # 크기 고정        
        
        smallfont = tkfont.Font(family="맑은 고딕", size=8)
        for i, name in enumerate(gl._propNames_):
            var = tk.IntVar()
            checked = tk.Checkbutton(frame_skill_box, text=name, font=smallfont, variable=var, anchor="w", width=6, height=1, 
                                        highlightthickness=0, borderwidth=0,
                                        command=lambda i=i: self.on_check_skills(i))
            checked.grid(row=i//4, column=i%4, sticky="w", padx=(8,0),pady=0,ipady=0)
            self.skills.append(checked)
            self.skillv.append(var)

    def build_equips(self, parent, nr, nc):        
        frame_equip = tk.LabelFrame(self.frame_1, text="무장 장비", width=self._width01, height=92)
        frame_equip.grid(row=nr, column=nc, rowspan=2, pady=(4,0) )
        frame_equip.grid_propagate(False)  # 크기 고정
        
        frame_equip_box = tk.LabelFrame(frame_equip, text="", width=self._width01-4, height=68, borderwidth=0, highlightthickness=0)
        frame_equip_box.grid(row=0, column=0, pady=(4, 0))
        frame_equip_box.grid_propagate(False)  # 크기 고정        

        equips = ["궁", "등갑", "기마", "마갑", "철갑", "노", "연노", "정란", "벽력거", "화포", "코끼리", "목수", "몽충","누선",]
        smallfont = tkfont.Font(family="맑은 고딕", size=8)
        for i, equip in enumerate(equips):            
            var = tk.IntVar()
            checked = tk.Checkbutton(frame_equip_box, text=equip, font=smallfont, variable=var, anchor="w", width=6, height=1,
                                      highlightthickness=0, borderwidth=0,
                                      command=lambda i=i: self.on_check_equips(i))

            checked.grid(row=i//4, column=i%4, sticky="w", padx=(8,0),pady=0,ipady=0)
            self.equips.append(checked)
            self.equipv.append(var)

    def on_enter_personality(self, event, num):        
        print("enter personality: ", num)
        if self.general_selected is None:
            return
        next = num+1
        if next >= len(self.personalities):
            next = 0

        value0 = self.personalities[num].get()
        try:
            value1 = int(value0)
            if 3 == num: # 수명
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[11]
                data1 = gl.set_bits(data0, value1, 8, 4)
                value0 = gl.get_bits(data0, 8, 4)
                print("수명: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.unpacked[11] = data1
                self.general_selected.lifespan = value1                

            elif 4 == num: # 성장
                #.특성: 0123 0011 3 매력, 
                #.건강: 4567 0000
                #.성장: 89AB 0010 
                #.수명: CDEF 0111 
                if 2 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[11]
                data1 = gl.set_bits(data0, value1, 12, 4)
                value0 = gl.get_bits(data0, 12, 4)
                print("수명: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.unpacked[11] = data1
                self.general_selected.groth = value1

            elif 5 == num: # 상성
                if 150 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                self.general_selected.salary = value1
                self.general_selected.unpacked[43] = value1

            elif 6 == num: # 야망
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 4, 4)
                value0 = gl.get_bits(data0, 4, 4)                
                print("야망: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.ambition = value1
                self.general_selected.unpacked[10] = data1

            elif 7 == num: # 의리
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[10]
                value0 = gl.get_bits(data0, 0, 4)
                data1 = gl.set_bits(data0, value1, 0, 4)
                print("의리: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.fidelity = value1
                self.general_selected.unpacked[10] = data1

            elif 8 == num: # 용맹
                #.야망: 0123 1100
                #.의리: 4567 1111
                #.성별: 89 00
                #.용맹: ABC 101
                #.냉정: DEF 101
                if 7 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 11, 3)
                value0 = gl.get_bits(data0, 11, 3)                
                print("용맹: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.valour = value1
                self.general_selected.unpacked[10] = data1

            elif 9 == num: # 냉정
                if 7 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = self.general_selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 8, 3)
                value0 = gl.get_bits(data0, 8, 3)
                print("냉정: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                self.general_selected.composed = value1
                self.general_selected.unpacked[10] = data1

            elif 10 == num: # 명성
                self.general_selected.fame = value1
                self.general_selected.unpacked[6] = value1
            elif 11 == num: # 공적
                self.general_selected.achieve = value1
                self.general_selected.unpacked[5] = value1
            elif 12 == num: # 봉록
                self.general_selected.salary = value1
                self.general_selected.unpacked[40] = value1
            elif 13 == num: # 행동력
                self.general_selected.actions = value1
                self.general_selected.unpacked[20] = value1
            elif 14 == num: # 병사
                self.general_selected.soldier = value1
                self.general_selected.unpacked[7] = value1
            elif 15 == num: # 훈련
                self.general_selected.training = value1
                self.general_selected.unpacked[41] = value1
            elif 16 == num: # 충성
                self.general_selected.loyalty = value1
                self.general_selected.unpacked[37] = value1
            elif 18 == num: # 친밀                
                gl.relations[self.general_selected.num] = value1
            else:
                print("??: on_enter", num, value0)

        except:
            print("error: on_enter", num, value0)
        
        self.personalities[next].focus_set()

    def on_selected_health(self, sevent):
        selected_index = self.health.current()  # 선택된 항목의 인덱스
        selected_value = self.health.get()      # 선택된 텍스트
        print("on_selected_health[ {0}, {1} ]".format(selected_index,selected_value))
        
        if self.general_selected is None:
            print("general_selected is None")
            return
        data1 = self.general_selected.unpacked[11] # 건강, 성장,  수명
        injury = selected_index
        value1 = gl.set_bits(data1, injury, 0, 4)
        self.general_selected.unpacked[11] = value1
        self.general_selected.injury = injury

    def on_enter_capture(self, event, num):
        entri = event.widget
        data0 = entri.get()
        print("on_enter_capture: {0}[{1}] ".format(num, data0))

        if self.general_selected is None:
            print("error: selected None: {0}[{1}] ".format(num, data0))
            return
        
        try:
            if '-' == data0.strip():
                if 0 == num:
                    value = 65535
                elif num in (1,2):
                    value = 255
                else:
                    value = 0
            else:
                value = int(data0)
        except:
            print("error: {0}", num)
            return
        
        selected = self.general_selected        
        if 0 == num: # 포획 군주
            selected.capture_ruler = value
            selected.unpacked[21] = value
        elif 1 == num: # 매복 세력
            selected.ambush_realm = value            
            selected.unpacked[45] = value
        elif 2 == num:
            selected.operate_realm = value
            selected.unpacked[47] = value
        elif 3 == num: # 포획 횟수
            selected.capture_cnt = value
            selected.unpacked[49] = value
        elif 4 == num:  # 매복 횟수
            selected.ambush_cnt = value
            selected.unpacked[44] = value
        elif 5 == num: # 작전 횟수
            selected.operate_cnt = value
            selected.unpacked[46] = value

        next = num + 1
        if next >= len(self.captures):
            next = 0
        self.captures[next].focus_set()

    def build_personalities(self, parent, nr, nc):        
        frame_personality = tk.LabelFrame(parent, text="무장 개성", width=self._width11, height=260)
        frame_personality.grid(row=0, column=0, pady=(4,0) )
        frame_personality.grid_propagate(False)  # 크기 고정

        frame_r1 = tk.LabelFrame(frame_personality, text="", width=self._width11-4, height=112, borderwidth=0, highlightthickness=0)
        frame_r1.grid(row=0, column=0) 
        frame_r1.grid_propagate(False)  # 크기 고정

        fields = ["탄생","등장","사관","수명", "성장","상성","야망","의리", "용맹","냉정","명성","공적", "봉록","행동력","병사","훈련", "충성","아이템","친밀"]
        for i, field in enumerate(fields):
            tk.Label(frame_r1, text=field).grid(row=i//4, column=(i%4)*2, padx=(4,0), pady=0)
            entri = tk.Entry(frame_r1, width=5, )
            entri.grid(row=i//4, column=(i%4)*2 +1, pady=0)
            entri.bind("<Return>", lambda event, i=i: self.on_enter_personality(event, i))  # Enter 키 입력 시 호출            
            self.personalities.append(entri)

        frame_r2 = tk.LabelFrame(frame_personality, text="", width=self._width11-4, height=30, borderwidth=0, highlightthickness=0)
        frame_r2.grid(row=1, column=0)
        frame_r2.grid_propagate(False)  # 크기 고정

        tk.Label(frame_r2, text="무술우승", ).grid(row=0, column=0, sticky="e", padx=(10,0))
        wins = tk.Entry(frame_r2, width=3)
        wins.grid(row=0, column=1, )
        self.wins.append(wins)

        tk.Label(frame_r2, text="한시우승").grid(row=0, column=4, sticky="e", padx=(8,0))
        wins = tk.Entry(frame_r2, width=3)
        wins.grid(row=0, column=5, )
        self.wins.append(wins)

        tk.Label(frame_r2, text="건강").grid(row=0, column=6, padx=(18,0))
        self.health = ttk.Combobox(frame_r2, values=gl._healthStates_, width=6, )
        self.health.grid(row=0, column=7,)
        self.health.bind("<<ComboboxSelected>>", self.on_selected_health)

        #frame_r3 = tk.LabelFrame(frame_personality, text="", width=self._width11-4, height=0, borderwidth=0, highlightthickness=0)
        #frame_r3.grid(row=2, column=0, pady=0)
        #frame_r3.grid_propagate(False)  # 크기 고정

        frame_r4 = tk.LabelFrame(frame_personality, text="", width=self._width11-4, height=96, borderwidth=0, highlightthickness=0)
        frame_r4.grid(row=3, column=0)
        frame_r4.grid_propagate(False)  # 크기 고정
        for i, label in enumerate(["포획 군주", "매복 세력", "작적 세력"]):
            tk.Label(frame_r4, text=label).grid(row=i, column=0, sticky="e", padx=2, pady=1)
            tk.Button(frame_r4, text="표시", width=4,borderwidth=0, highlightthickness=0).grid(row=i, column=2, padx=2)
            capture = tk.Entry(frame_r4, width=6)
            capture.grid(row=i, column=1, sticky="we", padx=2, pady=1)
            capture.bind('<Return>', lambda event, i=i: self.on_enter_capture(event, i))
            self.captures.append(capture)

        for i, label in enumerate(["포획 횟수", "매복 기간", "작적 기간"]):
            tk.Label(frame_r4, text=label, ).grid(row=i, column=4, sticky="e", padx=(16,0), pady=1)
            tk.Label(frame_r4, text="" ).grid(row=i, column=6, padx=4, pady=1, )            
            capture = tk.Entry(frame_r4, width=2 )
            capture.grid(row=i, column=5, sticky="we", padx=2, pady=1)
            capture.bind('<Return>', lambda event, i=i: self.on_enter_capture(event, 3+i))
            self.captures.append(capture)

        # 경향
        tk.Label(frame_r4, text="인물 경향").grid(row=4, column=0, sticky="e", padx=2)
        self.tendency = ttk.Combobox(frame_r4, values=gl._tendencies_, width=8, )
        self.tendency.grid(row=4, column=1, columnspan=2, sticky="we", padx=2)
        self.tendency.bind("<<ComboboxSelected>>", self.on_selected_tendency)

        tk.Label(frame_r4, text="전략 경향").grid(row=4, column=4, sticky="e", padx=(16,0))
        self.strategy = ttk.Combobox(frame_r4, values=gl._strategies_, width=8, )
        self.strategy.grid(row=4, column=5, columnspan=2, sticky="we",padx=2)
        self.strategy.bind("<<ComboboxSelected>>", self.on_selected_strategy)

    #value2 = self.unpacked[12]
    #.인물: 0123 0000
    #.전략: 4567 0011
    #.행동: 89AB 0000
    #.???: CDEF 0000
    #self.tendency   = gl.bit16from(value2, 8, 4) # 인물경향
    #self.strategy   = gl.bit16from(value2,12, 4) # 전략경향
    #self.turned     = gl.bit16from(value2, 0, 1)
    #self.opposite   = gl.bit16from(value2, 4, 4)

    def on_selected_tendency(self, sevent):
        _index = self.tendency.current()  # 선택한 항목의 인덱스
        _value = self.tendency.get()      # 선택한 항목의 값
        print("on_selected_tendency[ {0}, {1} ]".format(_index, _value))
        
        if self.general_selected is None:
            print("general is None")
            return
        _selected = self.general_selected

        data0 = _selected.unpacked[12] # 인물, 전략, 행동, ??
        tendency = _index
        value = gl.get_bits(data0, 4, 4)
        data1 = gl.set_bits(data0, tendency, 4, 4)
        print("{0}[{1:3}][ {2:2}:{3:2}, {4} => {5} ]".format( _selected.fixed, _selected.num, 
            value, tendency, format(data0, '016b'), format(data1,'016b')))

        _selected.unpacked[12] = data1
        _selected.tendency = tendency

    def on_selected_strategy(self, sevent):
        _index = self.strategy.current()  # 선택한 항목의 인덱스
        _value = self.strategy.get()      # 선택한 항목의 값
        print("on_selected_strategy[ {0}, {1} ]".format(_index, _value))
        
        if self.general_selected is None:
            print("general is None")
            return
        _selected = self.general_selected

        data0 = _selected.unpacked[12] # 인물, 전략, 행동, ??
        strategy = _index
        value = gl.get_bits(data0, 0, 4)
        data1 = gl.set_bits(data0, strategy, 0, 4)
        print("{0}[{1:3}][ {2:2}:{3:2}, {4} => {5} ]".format(_selected.fixed, _selected.num, 
            value, strategy, format(data0, '016b'), format(data1,'016b')))

        _selected.unpacked[12] = data1
        _selected.strategy = strategy

    def on_enter_realm(self, event):
        print("enter realm..")
        if self.general_selected is None:
            return
        
        entri = event.widget
        try:
            value = int(entri.get())
            if 0 > value or value > 255:
                print("error: overflow.. ", value)
                return
            self.general_selected.realm = value
            self.general_selected.unpacked[27] = value
        except:
            print("error:..")
        
    def on_combo_state_selected(self, event):
        selected_index = self.state.current()  # 선택된 항목의 인덱스
        selected_value = self.state.get()      # 선택된 텍스트

        print(f"{selected_index}: {selected_value}")

        #state = self.unpacked[26]
        self.general_selected.state = selected_index
        self.general_selected.unpacked[26] = selected_index


    def build_experiences(self, parent, nr, nc):
        frame_exp = tk.LabelFrame(parent, text="", width=self._width11, height=144, borderwidth=0, highlightthickness=0, )
        frame_exp.grid(row=3, column=0, )
        frame_exp.grid_propagate(False)  # 크기 고정        

        # 단련 경험
        frame_exp1 = tk.LabelFrame(frame_exp, text="무장 경험", width=self._width11-4, height=44, )
        frame_exp1.grid(row=0, column=0, pady=(4,0) )
        frame_exp1.grid_propagate(False)  # 크기 고정
        self.append_entries(frame_exp1, self.trains, ["무력", "지력", "정치", "매력"])

        # 소속
        frame_affil = tk.LabelFrame(frame_exp, text="무장 소속", width=self._width11-4, height=88)
        frame_affil.grid(row=1, column=0, pady=(4,0) )
        frame_affil.grid_propagate(False)  # 크기 고정

        tk.Label(frame_affil, text="세력").grid(row=0, column=0)
        self.realm = tk.Entry(frame_affil, width=5)
        self.realm.grid(row=0, column=1)
        self.realm.bind("<Return>", self.on_enter_realm)  # Enter 키 입력 시 호출            
        tk.Button(frame_affil, text="표시",borderwidth=0, highlightthickness=0).grid(row=0, column=2)

        tk.Label(frame_affil, text="도시").grid(row=0, column=3, padx=(16,0))
        self.city = ttk.Combobox(frame_affil, values=gl._cityNames_, width=8, )
        self.city.grid(row=0, column=4, columnspan=2, padx=(3,0))

        tk.Label(frame_affil, text="장군직").grid(row=1, column=0)
        ttk.Combobox(frame_affil, values=["없음", "도독", "장군", "대장군"], width=8, ).grid(row=1, column=1, columnspan=2, padx=(3,0))

        tk.Label(frame_affil, text="계급").grid(row=1, column=3, padx=(16,0))
        self.rank = ttk.Combobox(frame_affil, values=gl._rankNames_, width=8, )
        self.rank.grid(row=1, column=4, columnspan=2, padx=(3,0))

        tk.Label(frame_affil, text="신분").grid(row=2, column=0,)
        self.state = ttk.Combobox(frame_affil, values=gl._stateNames2, width=8, )
        self.state.grid(row=2, column=1, columnspan=2, padx=(3,0))
        self.state.bind("<<ComboboxSelected>>", self.on_combo_state_selected)
        
        tk.Label(frame_affil, text="동료").grid(row=2, column=3, padx=(16,0))
        self.colleague = tk.Entry(frame_affil, width=6)
        self.colleague.grid(row=2, column=4, padx=(2,0))
        tk.Button(frame_affil, text="표시", borderwidth=0, highlightthickness=0).grid(row=2, column=5)

    def realm_selected(self, event):
        self.general_selected = None

        selected = self.realm_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]

        city_filters = []
        self.realm_num = -1
        if '세력전체' != values[0]:
            if '세력없음' == values[0]:
                self.realm_num = 255
            else:
                self.realm_num = int(values[0]) # 세력 넘버
                city_filters.append("세력전체")

        if -1 == self.realm_num or 254 <= self.realm_num:
            city_filters.append("도시전체")
        
        city_filters.append("새로운장수")
        listup=[]
        self.city_num = -1
        for i, city in enumerate(gl.cities):
            if self.realm_num != -1 and city.realm != self.realm_num:
                continue
            city_filters.append('{0:3}. {1}'.format(city.num,city.name))
            listup.append(city.num)

        self.city_filter['values'] = city_filters
        self.city_filter.set("세력전체")
        if -1 == self.realm_num or 255 == self.realm_num:
            self.city_filter.set("도시전체")

        #print('filter: {}, {}'.format(self.realm_num, self.city_num))
        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if -1 == self.realm_num and -1 == self.city_num:
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue

            if 255 == self.realm_num and 255 == general.realm:
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue

            if 254 == self.city_num and 520 <= general.num and general.city in listup: # 새로운 장수만
                self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))
                continue            

            if -1 != self.realm_num:
                if general.realm == self.realm_num and general.city in listup:
                    self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))

        self.lb_generals.focus_set()
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(0)               # index 위치 선택
        self.lb_generals.activate(0)                    # 키보드 포커스 이동
        self.lb_generals.see(0)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")                    
         
    def city_selected(self, event):
        self.general_selected = None
        selected = self.city_filter.get()
        values = [p for p in re.split(r'[ .,]', selected) if p]        
        filters = []
        self.city_num = -1
        if '세력전체' != values[0] and '도시전체' != values[0]:
            if '새로운장수' == values[0]:
                self.city_num = -2
            else:
                self.city_num = int(values[0]) # 세력 넘버
            filters.append("세력전체")

        listup=[]
        for i, city in enumerate(gl.cities):
            if 0 <= self.city_num and ( -1 != self.realm_num and city.realm != self.realm_num):
                continue
            if 0 <= self.city_num and city.num != self.city_num:
                continue            
            filters.append('{0:3}. {1}'.format(city.num,city.name))
            listup.append(city.num)                    

        print('city selected: 세력[ {0} ], 도시[ {1}, {2} ]'.format(self.realm_num, self.city_num, len(listup)))

        self.lb_generals.delete(0, tk.END)
        for general in gl.generals:
            if -1 == self.city_num and (-1 != self.realm_num and self.realm_num != general.realm):
                continue
            if -2 == self.city_num and (520 > general.num or (-1 != self.realm_num and self.realm_num != general.realm)):
                continue
            if general.city not in listup:
                continue
            if -1 != self.realm_num and self.realm_num != general.realm:
                continue

            self.lb_generals.insert(tk.END, " {0:3}. {1}".format(general.num, general.name))

        self.lb_generals.focus_set()
        self.lb_generals.selection_clear(0, tk.END)     # 기존 선택 해제
        self.lb_generals.selection_set(0)               # index 위치 선택
        self.lb_generals.activate(0)                    # 키보드 포커스 이동
        self.lb_generals.see(0)                         # 해당 항목이 보이도록 스크롤
        self.lb_generals.event_generate("<<ListboxSelect>>")                

    def build_listup(self, parent, nr, nc):

        self.general_selected = None
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
        self.frame_listup = tk.LabelFrame(parent, text="", width=100, height=self._height0-48, ) #borderwidth=0, highlightthickness=0)
        self.frame_listup.pack(side="top", pady=0, fill="y")

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_listup, orient="vertical")
        scrollbar.pack(side="right", fill="y", pady=2)

        str_height = int((self._height0-72)/16)
        self.lb_generals = tk.Listbox(self.frame_listup, selectmode=tk.EXTENDED,
                                      width=12, height=str_height, 
                                      highlightthickness=0, relief="flat")
        self.lb_generals.pack(side="left", pady=2, fill="both", expand=True)
        self.lb_generals.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_generals.yview)
        self.lb_generals.config(yscrollcommand=scrollbar.set)        

    def build_tab_general(self, parent, nr, nc):

        self.frame_general = tk.LabelFrame(parent, text="", width= (128+self._width00+self._width10), height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_general.grid(row=nr, column=nc, rowspan=2, padx=(4,0))
        self.frame_general.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(self.frame_general, text="", width=100, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        self.build_listup(self.frame_0, 0, 0)

        self.frame_1 = tk.LabelFrame(self.frame_general, text="", width=self._width00, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정

        self.build_basic(self.frame_1, 0, 0) # 기본 설정
        #self.build_family(self.frame_1, 1, 0) # 혈연
        self.build_traits(self.frame_1, 2, 0) # 특성

        self.build_stats(self.frame_1, 3, 0) # 능력치
        self.build_skills(self.frame_1, 4, 0) # 특기
        self.build_equips(self.frame_1, 5, 0) # 장비

        self.frame_2 = tk.LabelFrame(self.frame_general, text="", width=self._width10, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_2.grid(row=0, column=2, padx=(4,0))
        self.frame_2.grid_propagate(False)  # 크기 고정

        self.build_personalities(self.frame_2, 0, 0) # 개성
        self.build_experiences(self.frame_2, 3, 0) # 경험치

        # 설정 버튼
        #tk.Button(self.frame_2, text="설 정", width=10, command=lambda: self.show_realm_popup() ).grid(row=6, column=0)

        self.listup_generals()
        self.popup_frame = tk.LabelFrame(self.frame_general, text="", width=self._width00, height=self._height0, borderwidth=0, highlightthickness=0)

        ### for test..
        self.frame_test = tk.LabelFrame(self.frame_2, text="", width=self._width11, height=64, borderwidth=0, highlightthickness=0)
        self.frame_test.grid(row=4, column=0, padx=(0,0), pady=4)
        self.frame_test.grid_propagate(False)  # 크기 고정

        test1 = tk.LabelFrame(self.frame_test, text="", width=104, height=45, )#borderwidth=0, highlightthickness=0)
        test1.grid(row=0, column=0, rowspan=2, padx=(0,0))
        test1.grid_propagate(False)  # 크기 고정
        #tk.Button(test1, text="Reset Turn", width=12, height=1, relief="flat", #bd=0,
        #          command=lambda: self.reset_turn() ).grid(row=0, column=0)
        tk.Button(test1, text="ADD(충성,친밀)", width=12, height=2, relief="flat", #bd=0,
                  command=lambda: self.refill_list() ).grid(row=0, column=0)

        # test2 = tk.LabelFrame(self.frame_test, text="", width=98, height=30, )#borderwidth=0, highlightthickness=0)
        # test2.grid(row=1, column=0, padx=(0,0), pady=(2,0))
        # test2.grid_propagate(False)  # 크기 고정
        # tk.Button(test2, text="Reset List", width=12, height=1, relief="flat", #bd=0,
        #          command=lambda: self.reset_list() ).grid(row=0, column=0)
        
        test3 = tk.LabelFrame(self.frame_test, text="", width=104, height=45, )#borderwidth=0, highlightthickness=0)
        test3.grid(row=0, column=1, rowspan=2,  padx=(4,0))
        test3.grid_propagate(False)  # 크기 고정
        tk.Button(test3, text="FULL(행동,훈련)", width=12, height=2, relief="flat", #bd=0,
                  command=lambda: self.reset_list()).grid(row=0, column=0)
        
        test4 = tk.LabelFrame(self.frame_test, text="", width=98, height=45, )#borderwidth=0, highlightthickness=0)
        test4.grid(row=0, column=2, rowspan=2, padx=(4,0))
        test4.grid_propagate(False)  # 크기 고정
        tk.Button(test4, text="Save(장수)", width=12, height=2, relief="flat", #bd=0,
                  command=lambda: self.save_general_selected() ).grid(row=0, column=0)        

    def save_general_selected(self):
        gn = len(gl.generals)
        
        _indices = self.lb_generals.curselection()
        _items = [self.lb_generals.get(i) for i in _indices]
        
        count = 0
        print("save: {0}".format(gl._loading_file))
        for item in _items:
            values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(values[0])
            if 0 > _num or _num >= gn:
                continue

            selected = gl.generals[_num]
            files.test_save_general_selected(gl._loading_file, count+1, selected, True)
            count = count + 1

        self.lb_generals.focus_set()
        print('save_general_selected: {0:3} / {1}'.format(count, len(_items)))        

    def test_file(self):
        print("tset_file..")
        #files.test_save_file('data.txt')
        files.test_save_generals('save generals')

    def reset_turn(self):
        indices = self.lb_generals.curselection()
        if indices:
            gn = len(gl.generals)
            item = self.lb_generals.get(indices[0])
            values = [p for p in re.split(r'[ .,]', item) if p]

            _num = int(values[0])
            if 0 <= _num and _num < gn:
                selected = gl.generals[_num]

                value0 = selected.unpacked[12]
                value1 = selected.unpacked[20]                

                selected.set_turns(0)
                selected.turned = gl.bit16from(selected.unpacked[12], 0, 1)
                selected.unpacked[20] = 200
                selected.actions = selected.unpacked[20]
                if 0 < selected.unpacked[7]:        # 병사
                    selected.unpacked[41] = 100     # 훈련
                    selected.training = selected.unpacked[41]

                value2 = selected.unpacked[12]
                value3 = selected.unpacked[20]

                print("{0} [{1:X},{2:X}] => [{3:X},{4:X}]".format(selected.name, value0, value1, value2, value3))
                #value0 = selected.unpacked[12]
                #selected.unpacked[12] = gl.set_bits(value0, 0, 15, 1)

    def refill_general(self, count, selected):
        data0 = selected.unpacked[37] # 충성
        data1 = selected.unpacked[11] # 건강, 성장,  수명
        data2 = selected.unpacked[20] # 행동력
        data3 = gl.relations[selected.num]

        value0 = data0 + 5
        if 96 <= value0:
            value0 = selected.unpacked[37]
        else:
            selected.unpacked[37] = value0
        selected.loyalty = value0

        injury = gl.get_bits(data1, 0, 4)
        if 0 < injury: # 아픈 경우
            injury = injury - 1
        value1 = gl.set_bits(data1, injury, 0, 4)
        selected.unpacked[11] = value1
        selected.injury = injury

        value2 = data2 + 50
        if 200 < value2:
            value2 = 200
        selected.unpacked[20] = value2
        selected.actions = value2

        value3 = data3 + 10
        if 100 <= value3:
            value3 = gl.relations[selected.num]
        gl.relations[selected.num] = value3

        if data0 == value0 and data1 == value1 and data2 == value2 and data3 == value3:
            return False
        
        print("{0:3}. {1}[{2:3}][ {3:3} {4:4x} {5:3} {6:3} ]".format(count, selected.fixed, selected.num, value0, value1, value2, value3) + 
                ("[ {0:2}, {1}, {2} ]".format( injury, format(data1, '016b'), format(value1, '016b')) if data1 != value1 else "") )        
        return True
        

    def refill_list(self):
        # _realm = self.realm_filter.get()
        # _city = self.city_filter.get()
        # if _realm =='세력전체' and _city == '도시전체':
        #     print("세력이나, 도시를 선택해주세요..")
        #     return

        gn = len(gl.generals)
        
        count = 0
        #items = list(self.lb_generals.get(0, tk.END))
        _realm = gl.generals[gl._player_num].realm
        _indices = self.lb_generals.curselection()
        _items = [self.lb_generals.get(i) for i in _indices]        
        for item in _items:
            values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(values[0])
            if 0 > _num or _num >= gn:
                continue
            
            selected = gl.generals[_num]
            if 255 == selected.realm:
                continue
            if _realm != selected.realm:
                continue
            if False == self.refill_general(count+1, selected):
                continue
            count = count + 1
            
        print('refill: {0:3} / {1}'.format(count, len(_items)))
        self.refresh_general(self.general_selected)                

    def reset_general(self, count, selected):
        value0 = selected.unpacked[12]
        value1 = selected.unpacked[20]
                    
        selected.set_turns(0)
        selected.turned = gl.bit16from(selected.unpacked[12], 0, 1)
        selected.unpacked[20] = 200
        selected.actions = selected.unpacked[20]
        #selected.unpacked[37] = 100            # 충성
        if 0 < selected.unpacked[7]:            # 병사
            selected.unpacked[41] = 100         # 훈련
            selected.training = selected.unpacked[41]
        
        value2 = selected.unpacked[12]
        value3 = selected.unpacked[20]
        print("{0:3}. {1}[{2:3}][ {3:4X},{4:4X} => {5:4X},{6:4X} ]".format(count, selected.fixed, selected.num, value0, value1, value2, value3))        

    def reset_list(self):
        # _realm = self.realm_filter.get()
        # _city = self.city_filter.get()
        # if _realm =='세력전체' and _city == '도시전체':
        #     print("세력이나, 도시를 선택해주세요..")
        #     return
        
        gn = len(gl.generals)
        count = 0

        #items = list(self.lb_generals.get(0, tk.END))
        _realm = gl.generals[gl._player_num].realm
        _indices = self.lb_generals.curselection()
        _items = [self.lb_generals.get(i) for i in _indices]
        for item in _items:
            values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(values[0])
            if 0 > _num or _num >= gn:
                continue

            selected = gl.generals[_num]
            if 255 == selected.realm:
                continue            
            if _realm != selected.realm:
                continue

            self.reset_general(count+1, selected)
            count = count + 1

        print('release: {0} / {1}'.format(count, len(_items)))
        self.refresh_general(self.general_selected)

    def close_popup(self):
        print("close_popup")
        _popup.ItemPopup._instance = None

    def show_popup(self):
        print("show_popup")
        #if _popup.RealmPopup._instance is None or not _popup.RealmPopup._instance.winfo_exists():
        #    _popup.RealmPopup._instance = _popup.RealmPopup(self.popup_frame)
        #else:
        #    _popup.RealmPopup._instance.lift()

        #if _popup.CityPopup._instance is None or not _popup.CityPopup._instance.winfo_exists():
        #    _popup.CityPopup._instance = _popup.CityPopup(self.popup_frame)
        #else:
        #    _popup.CityPopup._instance.lift()

        if _popup.ItemPopup._instance is None or not _popup.ItemPopup._instance.winfo_exists():
            _popup.ItemPopup._instance = _popup.ItemPopup(self.popup_frame, self.close_popup)
            #print("set itemPopup: ",_popup.ItemPopup._instance)
        else:
            _popup.ItemPopup._instance.lift()
    