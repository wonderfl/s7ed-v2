import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import globals as gl

class PersonalityFrame:
    def __init__(self, app, parent, nr, nc):
        self.app = app
        self.rootframe = parent
        self.build_personalities(app, parent, nr, nc) # 특기

    def on_enter_personality(self, event, num):        
        print("enter personality: ", num)
        _selected = self.app.general_selected
        if _selected is None:
            return
        next = num+1
        if next >= len(self.app.personalities):
            next = 0

        value0 = self.app.personalities[num].get()
        try:
            value1 = int(value0)
            if 3 == num: # 수명
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[11]
                data1 = gl.set_bits(data0, value1, 8, 4)
                value0 = gl.get_bits(data0, 8, 4)
                print("수명: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.unpacked[11] = data1
                _selected.lifespan = value1                

            elif 4 == num: # 성장
                if 2 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[11]
                data1 = gl.set_bits(data0, value1, 12, 4)
                value0 = gl.get_bits(data0, 12, 4)
                print("수명: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.unpacked[11] = data1
                _selected.groth = value1

            elif 5 == num: # 상성
                if 150 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                _selected.relations = value1
                _selected.unpacked[43] = value1

            elif 6 == num: # 야망
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 4, 4)
                value0 = gl.get_bits(data0, 4, 4)                
                print("야망: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.ambition = value1
                _selected.unpacked[10] = data1

            elif 7 == num: # 의리
                if 15 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[10]
                value0 = gl.get_bits(data0, 0, 4)
                data1 = gl.set_bits(data0, value1, 0, 4)
                print("의리: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.fidelity = value1
                _selected.unpacked[10] = data1

            elif 8 == num: # 용맹
                if 7 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 11, 3)
                value0 = gl.get_bits(data0, 11, 3)                
                print("용맹: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.valour = value1
                _selected.unpacked[10] = data1

            elif 9 == num: # 냉정
                if 7 < value1:
                    print("error: overflow {0} {1}".format(num, value1))
                    return
                data0 = _selected.unpacked[10]
                data1 = gl.set_bits(data0, value1, 8, 3)
                value0 = gl.get_bits(data0, 8, 3)
                print("냉정: {0:2},{1:2}, [{2}, {3}]".format( value0, value1, format(data0, '016b'), format(data1, '016b'),))
                _selected.composed = value1
                _selected.unpacked[10] = data1

            elif 10 == num: # 명성
                _selected.fame = value1
                _selected.unpacked[6] = value1
            elif 11 == num: # 공적
                _selected.achieve = value1
                _selected.unpacked[5] = value1
            elif 12 == num: # 봉록
                _selected.salary = value1
                _selected.unpacked[40] = value1
            elif 13 == num: # 행동력
                _selected.actions = value1
                _selected.unpacked[20] = value1
            elif 14 == num: # 병사
                _selected.soldier = value1
                _selected.unpacked[7] = value1
            elif 15 == num: # 훈련
                _selected.training = value1
                _selected.unpacked[41] = value1
            elif 16 == num: # 충성
                _selected.loyalty = value1
                _selected.unpacked[37] = value1
            elif 18 == num: # 친밀                
                gl.relations[_selected.num] = value1
            else:
                print("??: on_enter", num, value0)

        except:
            print("error: on_enter", num, value0)
        
        self.app.personalities[next].focus_set()

    def on_selected_health(self, sevent):
        selected_index = self.app.health.current()  # 선택된 항목의 인덱스
        selected_value = self.app.health.get()      # 선택된 텍스트
        print("on_selected_health[ {0}, {1} ]".format(selected_index,selected_value))
        
        _selected = self.app.general_selected
        if _selected is None:
            print("general_selected is None")
            return
        data1 = _selected.unpacked[11] # 건강, 성장,  수명
        injury = selected_index
        value1 = gl.set_bits(data1, injury, 0, 4)
        _selected.unpacked[11] = value1
        _selected.injury = injury

    def on_enter_capture(self, event, num):
        entri = event.widget
        data0 = entri.get()
        print("on_enter_capture: {0}[{1}] ".format(num, data0))

        _selected = self.app.general_selected
        if _selected is None:
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
        
        if 0 == num: # 포획 군주
            _selected.capture_ruler = value
            _selected.unpacked[21] = value
        elif 1 == num: # 매복 세력
            _selected.ambush_realm = value            
            _selected.unpacked[45] = value
        elif 2 == num:
            _selected.operate_realm = value
            _selected.unpacked[47] = value
        elif 3 == num: # 포획 횟수
            _selected.capture_cnt = value
            _selected.unpacked[49] = value
        elif 4 == num:  # 매복 횟수
            _selected.ambush_cnt = value
            _selected.unpacked[44] = value
        elif 5 == num: # 작전 횟수
            _selected.operate_cnt = value
            _selected.unpacked[46] = value

        next = num + 1
        if next >= len(self.app.captures):
            next = 0
        self.app.captures[next].focus_set()


    def on_selected_tendency(self, sevent):
        _index = self.app.tendency.current()  # 선택한 항목의 인덱스
        _value = self.app.tendency.get()      # 선택한 항목의 값
        print("on_selected_tendency[ {0}, {1} ]".format(_index, _value))
        
        _selected = self.app.general_selected
        if _selected is None:
            print("general is None")
            return
        
        data0 = _selected.unpacked[12] # 인물, 전략, 행동, ??
        tendency = _index
        value = gl.get_bits(data0, 4, 4)
        data1 = gl.set_bits(data0, tendency, 4, 4)
        print("{0}[{1:3}][ {2:2}:{3:2}, {4} => {5} ]".format( _selected.fixed, _selected.num, 
            value, tendency, format(data0, '016b'), format(data1,'016b')))

        _selected.unpacked[12] = data1
        _selected.tendency = tendency

    def on_selected_strategy(self, sevent):
        _index = self.app.strategy.current()  # 선택한 항목의 인덱스
        _value = self.app.strategy.get()      # 선택한 항목의 값
        print("on_selected_strategy[ {0}, {1} ]".format(_index, _value))
        
        _selected = self.app.general_selected
        if _selected is None:
            print("general is None")
            return
        
        data0 = _selected.unpacked[12] # 인물, 전략, 행동, ??
        strategy = _index
        value = gl.get_bits(data0, 0, 4)
        data1 = gl.set_bits(data0, strategy, 0, 4)
        print("{0}[{1:3}][ {2:2}:{3:2}, {4} => {5} ]".format(_selected.fixed, _selected.num, 
            value, strategy, format(data0, '016b'), format(data1,'016b')))

        _selected.unpacked[12] = data1
        _selected.strategy = strategy        

    def build_personalities(self, app, parent, nr, nc):        
        frame_personality = tk.LabelFrame(parent, text="무장 개성", width=app._width11, height=260)
        frame_personality.grid(row=0, column=0, pady=(4,0) )
        frame_personality.grid_propagate(False)  # 크기 고정

        frame_r1 = tk.LabelFrame(frame_personality, text="", width=app._width11-4, height=112, borderwidth=0, highlightthickness=0)
        frame_r1.grid(row=0, column=0) 
        frame_r1.grid_propagate(False)  # 크기 고정

        fields = ["탄생","등장","사관","수명", "성장","상성","야망","의리", "용맹","냉정","명성","공적", "봉록","행동력","병사","훈련", "충성","아이템","친밀"]
        for i, field in enumerate(fields):
            tk.Label(frame_r1, text=field).grid(row=i//4, column=(i%4)*2, padx=(4,0), pady=0)
            entri = tk.Entry(frame_r1, width=5, )
            entri.grid(row=i//4, column=(i%4)*2 +1, pady=0)
            entri.bind("<Return>", lambda event, i=i: self.on_enter_personality(event, i))  # Enter 키 입력 시 호출            
            app.personalities.append(entri)

        frame_r2 = tk.LabelFrame(frame_personality, text="", width=app._width11-4, height=30, borderwidth=0, highlightthickness=0)
        frame_r2.grid(row=1, column=0)
        frame_r2.grid_propagate(False)  # 크기 고정

        tk.Label(frame_r2, text="무술우승", ).grid(row=0, column=0, sticky="e", padx=(10,0))
        wins = tk.Entry(frame_r2, width=3)
        wins.grid(row=0, column=1, )
        app.wins.append(wins)

        tk.Label(frame_r2, text="한시우승").grid(row=0, column=4, sticky="e", padx=(8,0))
        wins = tk.Entry(frame_r2, width=3)
        wins.grid(row=0, column=5, )
        app.wins.append(wins)

        tk.Label(frame_r2, text="건강").grid(row=0, column=6, padx=(18,0))
        app.health = ttk.Combobox(frame_r2, values=gl._healthStates_, width=6, )
        app.health.grid(row=0, column=7,)
        app.health.bind("<<ComboboxSelected>>", self.on_selected_health)

        frame_r4 = tk.LabelFrame(frame_personality, text="", width=app._width11-4, height=96, borderwidth=0, highlightthickness=0)
        frame_r4.grid(row=3, column=0)
        frame_r4.grid_propagate(False)  # 크기 고정
        for i, label in enumerate(["포획 군주", "매복 세력", "작적 세력"]):
            tk.Label(frame_r4, text=label).grid(row=i, column=0, sticky="e", padx=2, pady=1)
            tk.Button(frame_r4, text="표시", width=4,borderwidth=0, highlightthickness=0).grid(row=i, column=2, padx=2)
            capture = tk.Entry(frame_r4, width=6)
            capture.grid(row=i, column=1, sticky="we", padx=2, pady=1)
            capture.bind('<Return>', lambda event, i=i: self.on_enter_capture(event, i))
            app.captures.append(capture)

        for i, label in enumerate(["포획 횟수", "매복 기간", "작적 기간"]):
            tk.Label(frame_r4, text=label, ).grid(row=i, column=4, sticky="e", padx=(16,0), pady=1)
            tk.Label(frame_r4, text="" ).grid(row=i, column=6, padx=4, pady=1, )            
            capture = tk.Entry(frame_r4, width=2 )
            capture.grid(row=i, column=5, sticky="we", padx=2, pady=1)
            capture.bind('<Return>', lambda event, i=i: self.on_enter_capture(event, 3+i))
            app.captures.append(capture)

        # 경향
        tk.Label(frame_r4, text="인물 경향").grid(row=4, column=0, sticky="e", padx=2)
        app.tendency = ttk.Combobox(frame_r4, values=gl._tendencies_, width=8, )
        app.tendency.grid(row=4, column=1, columnspan=2, sticky="we", padx=2)
        app.tendency.bind("<<ComboboxSelected>>", self.on_selected_tendency)

        tk.Label(frame_r4, text="전략 경향").grid(row=4, column=4, sticky="e", padx=(16,0))
        app.strategy = ttk.Combobox(frame_r4, values=gl._strategies_, width=8, )
        app.strategy.grid(row=4, column=5, columnspan=2, sticky="we",padx=2)
        app.strategy.bind("<<ComboboxSelected>>", self.on_selected_strategy)