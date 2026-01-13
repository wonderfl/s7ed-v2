import re

import tkinter as tk
import tkinter.font as tkfont

from tkinter import ttk
from PIL import Image, ImageTk

import globals as gl
from . import _city
from . import _realm
from . import _popup
from .frame import listup as _listup
from .frame import basic as _basic
from .frame import skill as _skill
from .frame import equip as _equip
from .frame import personality as _personality
from .frame import button as _button
from . import update

from . import gui

from commands import files
from utils import kaodata_image

class GeneralTab:

    _width00 = 284
    _width01 = 280

    _width10 = 328
    _width11 = 320

    _height0 = 496

    realm_num = -1
    city_num = -1

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
        self.listupFrame.listup_generals()

        _num = gl._player_num
        self.focus_num(_num, True)      

        if _popup.FramePopup._instance is not None:
            print("listup_tabs")
            _popup.FramePopup._instance.listup_tabs()

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
        
        try:
            #_png = 'gui/png/face{0:03}.png'.format(selected.faceno)
            #_image00 = Image.open(_png)
            # Kaodata.s7 파일에서 얼굴 이미지 읽기 시도
            _image00 = kaodata_image.get_face_image(selected.faceno)
        except Exception as e:
            print(f"[얼굴이미지] Kaodata.s7 읽기 실패 (faceno: {selected.faceno}): {e}")
            # 폴백: 기존 PNG 파일 사용
            _png = 'gui/png/face{0:03}.png'.format(selected.faceno)
            try:
                _image00 = Image.open(_png)
            except Exception as e2:
                print(f"[얼굴이미지] PNG 파일 읽기 실패 (faceno: {selected.faceno}): {e2}")
                # 기본 이미지 생성 (에러 방지)
                _image00 = Image.new('RGB', (96, 120), color='gray')
        
        iw = int(_basic.BasicFrame.image_width*0.99)
        ih = int(_basic.BasicFrame.image_height*0.99)
        _resized = _image00.resize(( iw, ih), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(_resized)

        if self.image_created:
            self.canvas.delete(self.image_created)
        # Canvas 중앙에 이미지 배치
        self.image_created = self.canvas.create_image(2, 2, anchor='nw', image=self.tk_image)      

        self.basicFrame.traitv.set(selected.job)        
        
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
        self.state.set(gl._stateName2[ selected.state if 7 > selected.state else 7])
        self.rank.set(gl._rankNames_[ selected.rank if 4 > selected.rank else 4])

        self.colleague.delete(0, tk.END)
        self.colleague.insert(0, selected.colleague if 65535 != selected.colleague else ' -')

        self.prev.config(text='{0}'.format('#'))
        for general in gl.generals:
            if general.colleague == selected.num:                
                self.prev.config(text='{0}'.format(general.num))

    def entry_row(self, frame, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2)
            tk.Entry(frame, width=width ).grid(row=0, column=i * 2 + 1)

    def append_entries(self, frame, entries, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2, padx=(4,0), pady=(4,0))
            entry = tk.Entry(frame, width=width )
            entry.grid(row=0, column=i * 2 + 1, pady=(4,0))
            entries.append(entry)\

    def items(self):
        return self.listupFrame.items()

    def find_general_num(self, num, now=False):        
        found = self.listupFrame.find_item_num(num)
        if -1 == found:
            return
        self.listupFrame.focus_num(found, now)        

    def focus_num(self, num, now=False):
        self.listupFrame.focus_num(num, now)

    def realod_general_listup(self, listup):
        self.listupFrame.reload_listup(listup)

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
        frame_traits = tk.LabelFrame(parent, text="무장 특성", width=self._width01, height=56)
        frame_traits.grid(row=nr, column=nc, pady=(4,0), ipady=0 )
        frame_traits.grid_propagate(False)  # 크기 고정
        
        self.traitv = tk.IntVar()
        for i, label in enumerate(["무력", "지력", "정치", "매력","장군", "군사", "만능", "평범"]):
            radio = tk.Radiobutton(frame_traits, text=label,  variable=self.traitv, value=i, highlightthickness=0, borderwidth=0)
            radio.grid(row=i//4, column=i%4, pady=(4 if i<=4 else 0, 0), padx=(8,0), sticky='w')

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

    def on_enter_colleague(self, event):
        print("enter colleague..")
        if self.general_selected is None:
            return
        gn = len(gl.generals)
        city = self.general_selected.city
        entri = event.widget
        try:
            data0 = entri.get()
            if '-' == data0.strip():
                value = 65535
                self.general_selected.colleague = value
                self.general_selected.unpacked[15] = value
                return

            value = int(data0)
            if 0 > value or value > gn:
                print("error: overflow.. ", value)
                return
            
            if city != gl.generals[value].city:
                print("error: not colleague.. ", value)
                return            

            #self.general_selected.colleague = value
            #self.general_selected.unpacked[15] = value
        except:
            print("error:..")            
        
    def on_combo_rank_selected(self, event):
        selected_index = self.rank.current()  # 선택된 항목의 인덱스
        selected_value = self.rank.get()      # 선택된 텍스트

        print(f"{selected_index}: {selected_value}")

        self.general_selected.rank = selected_index
        self.general_selected.unpacked[39] = selected_index

    def on_combo_state_selected(self, event):
        selected_index = self.state.current()  # 선택된 항목의 인덱스
        selected_value = self.state.get()      # 선택된 텍스트

        print(f"{selected_index}: {selected_value}")

        self.general_selected.state = selected_index
        self.general_selected.unpacked[26] = selected_index        

    def on_combo_city_selected(self, event):
        selected_index = self.city.current()  # 선택된 항목의 인덱스
        selected_value = self.city.get()      # 선택된 텍스트

        print(f"{selected_index}: {selected_value}")

        #self.general_selected.city = selected_index
        #self.general_selected.unpacked[28] = selected_index

        #nc = self.general_selected.city
        #gl.cities[nc].governor = self.general_selected.num
        #gl.cities[nc].unpacked[3] = self.general_selected.num
        #governor = self



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
        self.city.bind("<<ComboboxSelected>>", self.on_combo_city_selected)

        tk.Label(frame_affil, text="장군직").grid(row=1, column=0)
        ttk.Combobox(frame_affil, values=["없음", "도독", "장군", "대장군"], width=8, ).grid(row=1, column=1, columnspan=2, padx=(3,0))

        tk.Label(frame_affil, text="계급").grid(row=1, column=3, padx=(16,0))
        self.rank = ttk.Combobox(frame_affil, values=gl._rankNames_, width=8, )
        self.rank.grid(row=1, column=4, columnspan=2, padx=(3,0))
        self.rank.bind("<<ComboboxSelected>>", self.on_combo_rank_selected)

        tk.Label(frame_affil, text="신분").grid(row=2, column=0,)
        self.state = ttk.Combobox(frame_affil, values=gl._stateName2, width=8, )
        self.state.grid(row=2, column=1, columnspan=2, padx=(3,0))
        self.state.bind("<<ComboboxSelected>>", self.on_combo_state_selected)
        
        tk.Label(frame_affil, text="동료").grid(row=2, column=3, padx=(16,0))
        self.colleague = tk.Entry(frame_affil, width=5)
        self.colleague.grid(row=2, column=4, padx=(4,0))
        self.colleague.bind("<Return>", self.on_enter_colleague)  # Enter 키 입력 시 호출
        
        #tk.Button(frame_affil, text="표시", borderwidth=0, highlightthickness=0).grid(row=2, column=5)
        self.prev = tk.Label(frame_affil, text="-", width=5, )#borderwidth=2, relief="solid")
        self.prev.grid(row=2, column=5, padx=(0,0))



    def build_tab_general(self, parent, nr, nc):
        self.frame_general = tk.LabelFrame(parent, text="", width= (312+self._width00+self._width10), height=self._height0, borderwidth=0, highlightthickness=0, )
        self.frame_general.grid(row=nr, column=nc, rowspan=2, padx=(4,0))
        self.frame_general.grid_propagate(False)  # 크기 고정

        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(self.frame_general, text="", width=100, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        self.listupFrame = _listup.ListupFrame(self, self.frame_0, 0, 0)

        self.frame_1 = tk.LabelFrame(self.frame_general, text="", width=self._width00, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정

        self.basicFrame = _basic.BasicFrame(self, self.frame_1, 0, 0)        
        #self.build_traits(self.frame_1, 2, 0) # 특성
        self.build_stats(self.frame_1, 2, 0) # 능력치
        self.skillFrame = _skill.SkillFrame(self, self.frame_1, 3, 0)
        self.equipFrame = _equip.EquipFrame(self, self.frame_1, 4, 0)

        self.frame_2 = tk.LabelFrame(self.frame_general, text="", width=self._width10, height=self._height0-4, borderwidth=0, highlightthickness=0)
        self.frame_2.grid(row=0, column=2, padx=(4,0))
        self.frame_2.grid_propagate(False)  # 크기 고정

        self.personalityFrame = _personality.PersonalityFrame(self, self.frame_2, 0, 0) # 개성
        self.build_experiences(self.frame_2, 3, 0) # 경험치

        self.buttonFrame = _button.ButtonFrame(self, self.frame_2, )

        self.listup_generals()
        self.popup_frame = tk.LabelFrame(self.frame_general, text="", width=self._width00, height=self._height0, borderwidth=0, highlightthickness=0)

    def save_general_selected(self):
        print("save: {0}".format(gl._loading_file))
        gl._is_saving = True
        
        gn = len(gl.generals)
        count = 0        

        _items = self.listupFrame.selections()
        if 0 >= len(_items) and self.general_selected:
            files.test_save_general_selected(gl._loading_file, count+1, self.general_selected, True)
            count = count + 1

        for item in _items:
            #values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(item[0])
            if 0 > _num or _num >= gn:
                continue

            selected = gl.generals[_num]
            files.test_save_general_selected(gl._loading_file, count+1, selected, True)
            count = count + 1

        self.listupFrame.focus_generals()
        print('save_general_selected: {0:3} / {1}'.format(count, len(_items)))        

    def test_file(self):
        print("tset_file..")
        #files.test_save_file('data.txt')
        files.test_save_generals('save generals')

    def refill_result_list(self, str, call):
        gn = len(gl.generals)
        if 0 > gl._player_num or gl._player_num >= gn:
            print("error: realms index out of range: ", gl._player_num)
            return
        
        count = 0
        _realm = gl.generals[gl._player_num].realm
        
        _items = _items = self.listupFrame.selections()
        for item in _items:
            #values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(item[0])
            if 0 > _num or _num >= gn:
                continue
            
            selected = gl.generals[_num]
            if 255 == selected.realm:
                continue
            if _realm != selected.realm:
                continue
            res = call(count+1, selected)
            if False == res:
                continue
            
            count = count + 1
            
        print('refill {0}: {1:3} / {2}'.format(str, count, len(_items)))
        self.refresh_general(self.general_selected)
    
    def refill_request_list(self, str, call):

        gn = len(gl.generals)
        
        count = 0
        _realm = gl.generals[gl._player_num].realm
        
        _items = self.listupFrame.selections()
        for item in _items:
            #values = [p for p in re.split(r'[ .,]', item) if p]            
            _num = int(item[0])
            if 0 > _num or _num >= gn:
                continue

            selected = gl.generals[_num]
            if 255 == selected.realm:
                continue
            if _realm != selected.realm:
                continue

            call(count+1, selected)
            count = count + 1

        print('refill {0}: {1} / {2}'.format(str, count, len(_items)))
        self.refresh_general(self.general_selected)        

    def refill_all_list(self, str, call):

        gn = len(gl.generals)
        
        count = 0
        _realm = gl.generals[gl._player_num].realm
        
        _items = self.listupFrame.selections()
        for item in _items:
            #values = [p for p in re.split(r'[ .,]', item) if p]
            
            _num = int(item[0])
            if 0 > _num or _num >= gn:
                continue
            selected = gl.generals[_num]
            call(count+1, selected)
            count = count + 1

        print('refill {0}: {1} / {2}'.format(str, count, len(_items)))
        self.refresh_general(self.general_selected)

    def close_popup(self):
        print("close_popup")
        _popup.FramePopup._instance = None

    def show_popup(self):
        print("show_popup")

        if _popup.FramePopup._instance is None or not _popup.FramePopup._instance.winfo_exists():
            _popup.FramePopup._instance = _popup.FramePopup(self.popup_frame, self.close_popup)
        else:
            _popup.FramePopup._instance.lift()
    