import tkinter as tk
from tkinter import ttk

import globals as gl
from . import _realm
from . import _realm



class GeneralTab:

    _width00 = 276
    _width01 = 272
    _height0 = 540

    _width10 = 328
    _width11 = 320

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
        self.build_tab_general(self.rootframe)
        return

    def general_selected(self, index, value):
        #print(f"선택된 항목 처리: {value}")
        selected = gl.generals[index]
        if selected.name != value:
            print(f"잘못된 정보입니다: {index}, {value}")
            return
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
        self.parents.insert(0, selected.parent)

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
        personalities=[
            selected.birthyear, selected.appearance, selected.employment, selected.lifespan,
            selected.growth, selected.relation, selected.ambition, selected.fidelity,
            selected.valour, selected.composed, selected.fame, selected.achieve,
            selected.salary, selected.actions, selected.soldier, selected.training,
            selected.loyalty, selected.item, relation
        ]
        for i, value in enumerate(personalities):
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

    def on_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            value = widget.get(index).strip()
            #print(f"[선택] {index}: {value}")
            # 선택시 호출할 함수
            self.general_selected(index, value)

    def entry_row(self, frame, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2)
            tk.Entry(frame, width=width ).grid(row=0, column=i * 2 + 1)

    def append_entries(self, frame, entries, labels, width=4):
        for i, text in enumerate(labels):
            tk.Label(frame, text=text).grid(row=0, column=i * 2)
            entry = tk.Entry(frame, width=width )
            entry.grid(row=0, column=i * 2 + 1)
            entries.append(entry)

    def build_basic(self, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="무장 기본 설정", width=self._width01, height=72)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0)
        frame_b1.grid_propagate(False)  # 크기 고정        

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=0)
        frame_b2.grid_propagate(False)  # 크기 고정                

        #entry_row(frame_b1, ["성", "명", "자"])
        tk.Label(frame_b1, text="성").grid(row=0, column=0)
        self.name0 = tk.Entry(frame_b1, width=4 )
        self.name0.grid(row=0, column=1)

        tk.Label(frame_b1, text="명").grid(row=0, column=2)
        self.name1 = tk.Entry(frame_b1, width=4 )
        self.name1.grid(row=0, column=3)

        tk.Label(frame_b1, text="자").grid(row=0, column=4)
        self.name2 = tk.Entry(frame_b1, width=4 )
        self.name2.grid(row=0, column=5)

        tk.Label(frame_b1, text="별명").grid(row=0, column=6)
        tk.Entry(frame_b1, width=8 ).grid(row=0, column=7)                        

        tk.Label(frame_b2, text="얼굴").grid(row=1, column=0)
        self.face = tk.Entry(frame_b2, width=4)
        self.face.grid(row=1, column=1)

        self.genderv = tk.IntVar()
        tk.Label(frame_b2, text="성별").grid(row=1, column=3)
        tk.Radiobutton(frame_b2, text="남", variable=self.genderv, value=0).grid(row=1, column=4)
        tk.Radiobutton(frame_b2, text="여", variable=self.genderv, value=1).grid(row=1, column=5)
        
        var = tk.IntVar()
        self.turned = tk.Checkbutton(frame_b2, text="행동유무", variable=var)
        self.turned.grid(row=1, column=7)
        self.turnv = var

    def build_family(self, parent, nr, nc):
        frame_family = tk.LabelFrame(parent, text="무장 혈연", width=self._width01, height=54)
        frame_family.grid(row=nr, column=nc, pady=(4,0) )
        frame_family.grid_propagate(False)  # 크기 고정

        entri0 = tk.Entry(frame_family, width=4, )
        entri0.grid(row=0, column=0, padx=(4,0))
        self.num=entri0
        tk.Label(frame_family, text=".",).grid(row=0, column=1,)

        tk.Label(frame_family, text="가문", width=4,).grid(row=0, column=2, padx=(2,0))
        entri1 = tk.Entry(frame_family, width=4)
        entri1.grid(row=0, column=3)
        tk.Button(frame_family, text="표시", width=3, borderwidth=0, highlightthickness=0).grid(row=0, column=4)
        self.family=entri1

        tk.Label(frame_family, text="부모", width=4,).grid(row=0, column=5, padx=(4,0))
        entri2 = tk.Entry(frame_family, width=5)
        entri2.grid(row=0, column=6)
        tk.Button(frame_family, text="표시", width=3, borderwidth=0, highlightthickness=0).grid(row=0, column=7)
        self.parents=entri2

    def build_stats(self, parent, nr, nc):
        frame_stats = tk.LabelFrame(parent, text="무장 능력", width=self._width01, height=48)
        frame_stats.grid(row=nr, column=nc, pady=(4,0) )
        frame_stats.grid_propagate(False)  # 크기 고정

        self.append_entries(frame_stats, self.stats, ["무력", "지력", "정치", "매력"],  width=4)

    def build_traits(self, parent, nr, nc):
        frame_traits = tk.LabelFrame(parent, text="무장 특성", width=self._width01, height=64)
        frame_traits.grid(row=nr, column=nc, pady=(4,0) )
        frame_traits.grid_propagate(False)  # 크기 고정
        
        self.traitv = tk.IntVar()
        for i, label in enumerate(["무력", "지력", "정치", "매력","장군", "군사", "만능", "평범"]):
            tk.Radiobutton(frame_traits, text=label, variable=self.traitv, value=i, width=6, height=1, highlightthickness=0, borderwidth=0).grid(row=i//4, column=i%4)                

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

    def build_equips(self, parent, nr, nc):        
        frame_equip = tk.LabelFrame(self.frame_1, text="무장 장비", width=self._width01, height=100)
        frame_equip.grid(row=nr, column=nc, rowspan=2, pady=(4,0) )
        frame_equip.grid_propagate(False)  # 크기 고정
        equips = ["궁", "등갑", "기마", "마갑", "철갑", "노", "연노", "정란", "벽력거", "화포", "코끼리", "목수", "몽충","누선",]
        for i, equip in enumerate(equips):            
            var = tk.IntVar()
            checked = tk.Checkbutton(frame_equip, text=equip, width=5, height=1, highlightthickness=0, borderwidth=0, anchor="w",variable=var )
            checked.grid(row=i//4, column=i%4, sticky="w", padx=(8,0),pady=0,ipady=0)
            self.equips.append(checked)
            self.equipv.append(var)

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
            entri = tk.Entry(frame_r1, width=5,)
            entri.grid(row=i//4, column=(i%4)*2 +1, pady=0)
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
            self.captures.append(capture)

        for i, label in enumerate(["포획 횟수", "매복 기간", "작적 기간"]):
            tk.Label(frame_r4, text=label, ).grid(row=i, column=4, sticky="e", padx=(16,0), pady=1)
            tk.Label(frame_r4, text="" ).grid(row=i, column=6, padx=4, pady=1, )            
            capture = tk.Entry(frame_r4, width=2 )
            capture.grid(row=i, column=5, sticky="we", padx=2, pady=1)
            self.captures.append(capture)

        # 경향
        tk.Label(frame_r4, text="인물 경향").grid(row=4, column=0, sticky="e", padx=2)
        self.tendency = ttk.Combobox(frame_r4, values=gl._tendencies_, width=8, )
        self.tendency.grid(row=4, column=1, columnspan=2, sticky="we", padx=2)
        tk.Label(frame_r4, text="전략 경향").grid(row=4, column=4, sticky="e", padx=(16,0))
        self.strategy = ttk.Combobox(frame_r4, values=gl._strategies_, width=8, )
        self.strategy.grid(row=4, column=5, columnspan=2, sticky="we",padx=2)

    def build_experiences(self, parent, nr, nc):
        frame_exp = tk.LabelFrame(parent, text="", width=self._width11, height=180, borderwidth=0, highlightthickness=0) #borderwidth=0, highlightthickness=0
        frame_exp.grid(row=3, column=0, )
        frame_exp.grid_propagate(False)  # 크기 고정        

        # 단련 경험
        frame_exp1 = tk.LabelFrame(frame_exp, text="무장 경험", width=self._width11, height=48, )
        frame_exp1.grid(row=0, column=0, pady=(4,0) )
        frame_exp1.grid_propagate(False)  # 크기 고정
        self.append_entries(frame_exp1, self.trains, ["무력", "지력", "정치", "매력"])

        # 소속
        frame_affil = tk.LabelFrame(frame_exp, text="무장 소속", width=self._width11, height=96)
        frame_affil.grid(row=1, column=0, pady=(4,0) )
        frame_affil.grid_propagate(False)  # 크기 고정

        tk.Label(frame_affil, text="세력").grid(row=0, column=0)
        self.realm = tk.Entry(frame_affil, width=5)
        self.realm.grid(row=0, column=1)
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
        
        tk.Label(frame_affil, text="동료").grid(row=2, column=3, padx=(16,0))
        self.colleague = tk.Entry(frame_affil, width=6)
        self.colleague.grid(row=2, column=4, padx=(2,0))
        tk.Button(frame_affil, text="표시", borderwidth=0, highlightthickness=0).grid(row=2, column=5)

    def build_tab_general(self, parent):
        # 좌측 장수 리스트
        self.frame_0 = tk.LabelFrame(parent, text="", width=100, height=self._height0,)
        self.frame_0.grid(row=0, column=0, padx=(4,0))
        self.frame_0.grid_propagate(False)  # 크기 고정

        # Scrollbar 연결
        scrollbar = tk.Scrollbar(self.frame_0, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.lb_generals = tk.Listbox(self.frame_0, height=33, width=10,  highlightthickness=0,relief="flat")
        self.lb_generals.pack(side="left", fill="both", expand=True)
        self.lb_generals.bind("<<ListboxSelect>>", self.on_selected)       # 선택될 때
        scrollbar.config(command=self.lb_generals.yview)
        self.lb_generals.config(yscrollcommand=scrollbar.set)
        for general in gl.generals:
            self.lb_generals.insert(tk.END, " {0}".format(general.name))

        self.frame_1 = tk.LabelFrame(parent, text="", width=self._width00, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_1.grid(row=0, column=1, padx=(4,0))
        self.frame_1.grid_propagate(False)  # 크기 고정

        self.build_basic(self.frame_1, 0, 0) # 기본 설정
        self.build_family(self.frame_1, 1, 0) # 혈연
        self.build_traits(self.frame_1, 2, 0) # 특성

        self.build_stats(self.frame_1, 3, 0) # 능력치
        self.build_skills(self.frame_1, 4, 0) # 특기
        self.build_equips(self.frame_1, 5, 0) # 장비


        self.frame_2 = tk.LabelFrame(parent, text="", width=self._width10, height=self._height0, borderwidth=0, highlightthickness=0)
        self.frame_2.grid(row=0, column=2, padx=(4,0))
        self.frame_2.grid_propagate(False)  # 크기 고정

        self.build_personalities(self.frame_2, 0, 0) # 개성
        self.build_experiences(self.frame_2, 3, 0) # 경험치

        # 설정 버튼
        tk.Button(self.frame_2, text="설 정", width=10).grid(row=4, column=0)