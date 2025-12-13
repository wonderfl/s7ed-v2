import tkinter as tk
import tkinter.font as tkfont

import globals as gl

class BasicFrame:
    _width01 = 280
    
    image_height = 120
    image_width = int(image_height*0.8)

    def __init__(self, app, parent, nr, nc):
        self.app = app
        self.rootframe = parent
        self.build_basic(app, parent, nr, nc) # 특기

    def on_enter_num(self, event):
        gn = len(gl.generals)        
        value1 = self.app.num.get()
        try:
            num = int(value1)
            if 0 > num or num >= gn:
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))
            return
        
        self.app.find_general_num(num, True)

    def on_enter_family(self, event):
        gn = len(gl.generals)        
        value1 = self.app.family.get()
        try:
            num = int(value1)
            if 0 > num or num >= gn:
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))
            return
        
        listup = [general for general in gl.generals if num == general.family]
        if 0 >= len(listup):
            print("not found name0: ", value1)
            return
        
        self.app.realod_general_listup(listup)

    def on_enter_parent(self, event):
        value1 = self.app.parents.get()
        if '-' == value1.strip():
            value1 = '65535'
        try:
            num = int(value1)
            if (0 > num or (num >= 2000 and num != 65535)):
                print("overflow ", num)
                return
        except:
            print('error: {0}'.format(value1))
            return

        listup = [general for general in gl.generals if num == general.parent]
        if 0 >= len(listup):
            print("not found parent: ", value1)
            return
        self.app.realod_general_listup(listup)

    def on_enter_name0(self, event):
        value1 = self.app.name0.get()
        listup = [general for general in gl.generals if value1 == general.name0]
        if 0 >= len(listup):
            print("not found name0: ", value1)
            return
        self.app.realod_general_listup(listup)        

    def build_basic(self, app, parent, nr, nc):
        frame_basic = tk.LabelFrame(parent, text="무장 기본 설정", width=self._width01, height=self.image_height+32)
        frame_basic.grid(row=nr, column=nc, pady=(4,0) )
        frame_basic.grid_propagate(False)  # 크기 고정

        frame_b0 = tk.LabelFrame(frame_basic, text="", width=96, height=120,borderwidth=0, highlightthickness=0)
        frame_b0.grid( column=0, row=0, rowspan=3, ipadx=0,ipady=0, pady=(8,0))
        frame_b0.grid_propagate(False)  # 크기 고정
        app.frame_image = frame_b0

        app.canvas = tk.Canvas(app.frame_image, width=self.image_width, height=self.image_height)
        app.canvas.pack()
        app.image_created = None
                
        frame_b1 = tk.LabelFrame(frame_basic, text="", width=self._width01-112, height=60, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=1, sticky='w', padx=(0,0), pady=(4,0))
        frame_b1.grid_propagate(False)  # 크기 고정        

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=self._width01-112, height=20, borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=1, sticky='w', padx=(0,0), pady=(4,0))
        frame_b2.grid_propagate(False)  # 크기 고정 

        frame_b3 = tk.LabelFrame(frame_basic, text="", width=self._width01-112, height=40, borderwidth=0, highlightthickness=0)
        frame_b3.grid(row=2, column=1, sticky='w', padx=(0,0), pady=(8,0))
        frame_b3.grid_propagate(False)  # 크기 고정         

        tk.Label(frame_b1, text="번호",).grid(row=0, column=0,)
        entri0 = tk.Entry(frame_b1, width=4, )
        entri0.grid(row=0, column=1, padx=(0,0))
        entri0.bind("<Return>", lambda event: self.on_enter_num(event))  # Enter 키 입력 시 호출
        app.num=entri0

        tk.Label(frame_b1, text="얼굴").grid(row=0, column=2)
        app.face = tk.Entry(frame_b1, width=4)
        app.face.grid(row=0, column=3)        

        tk.Label(frame_b1, text="가문", width=4,).grid(row=1, column=0, padx=(0,0))
        entri1 = tk.Entry(frame_b1, width=4)
        entri1.grid(row=1, column=1)
        entri1.bind("<Return>", lambda event: self.on_enter_family(event))  # Enter 키 입력 시 호출
        app.family=entri1

        tk.Label(frame_b1, text="부모", width=4,).grid(row=1, column=2, padx=(0,0))
        entri2 = tk.Entry(frame_b1, width=4)
        entri2.grid(row=1, column=3)
        entri2.bind("<Return>", lambda event: self.on_enter_parent(event))  # Enter 키 입력 시 호출
        app.parents=entri2                                

        #entry_row(frame_b1, ["성", "명", "자"])
        tk.Label(frame_b1, text="성").grid(row=2, column=0, padx=(8,0))
        app.name0 = tk.Entry(frame_b1, width=4 )
        app.name0.bind("<Return>", lambda event: self.on_enter_name0(event))  # Enter 키 입력 시 호출
        app.name0.grid(row=2, column=1)

        tk.Label(frame_b1, text="명").grid(row=2, column=2, padx=(8,0))
        app.name1 = tk.Entry(frame_b1, width=4 )
        app.name1.grid(row=2, column=3)

        app.name2 = tk.Entry(frame_b1, width=5 )
        app.name2.grid(row=2, column=5, padx=(0,0))

        tk.Label(frame_b2, text="행동").grid(row=0, column=0, padx=(0,0))
        app.turnv = tk.IntVar()
        app.turned = tk.Checkbutton(frame_b2, text="", variable=app.turnv)
        app.turned.grid(row=0, column=1, padx=(0,0))        

        app.genderv = tk.IntVar()
        tk.Label(frame_b2, text="성별").grid(row=0, column=2, padx=(0,0))
        tk.Radiobutton(frame_b2, text="남", variable=app.genderv, value=0).grid(row=0, column=3, padx=(0,0))
        tk.Radiobutton(frame_b2, text="여", variable=app.genderv, value=1).grid(row=0, column=4, padx=(0,0))

        self.build_traits(frame_b3, 2, 0) # 특성


    def update_radio(self):
        val = self.traitv.get()
        for i, radio in enumerate(self.traits):
            if i == val:
                radio.config(relief="raised", borderwidth=0, bg="white")
            else:
                radio.config(relief="sunken", borderwidth=0, bg="lightgray")

    def build_traits(self, parent, nr, nc):
        #frame_traits = tk.LabelFrame(parent, text="무장 특성", width=self._width01, height=56)
        frame_traits = tk.LabelFrame(parent, text="", width=self._width01-108, height=36)
        frame_traits.grid(row=nr, column=nc, pady=(4,0), ipady=0 )
        frame_traits.grid_propagate(False)  # 크기 고정
        
        self.traits = []
        self.traitv = tk.IntVar()
        for i, label in enumerate(["무력", "지력", "정치", "매력","장군", "군사", "만능", "평범"]):
            radio = tk.Radiobutton(frame_traits, width=6, height=1, 
                                   value=i, text=label, variable=self.traitv,
                                   indicatoron=False, 
                                   command=self.update_radio,
                                   highlightthickness=0, borderwidth=0,
                                   bg="lightgray", )
            radio.grid(row=i//4, column=i%4, padx=(2,0), pady=(2 if i < 4 else 0, 2), sticky='w')
            self.traits.append(radio)