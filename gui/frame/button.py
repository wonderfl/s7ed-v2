import re

import tkinter as tk

from .. import _general
from .. import update

class ButtonFrame:
    _width = 96
    _height = 32

    def __init__(self, tab, frame ):
        self.rootframe = frame
        self.parentTab = tab
        self.build_frame_button(frame, tab._width11)

    def create_button(self, parent, name, call, nr, nc, width, height):

        _w12 = int(width)
        _w16 = int(_w12*7)
        _h02 = int(height)
        _h16 = int(_h02*14)
        #print("create button: {0}, {1} [ {2}, {3} ]".format( self._height, height, _h02, _h16,))

        test1 = tk.LabelFrame(parent, text="", width=_w16, height=_h16, )#borderwidth=0, highlightthickness=0,)
        test1.grid(row=nr, column=nc, rowspan=height, padx=(1,1), pady=(1,1), ipady= 0, sticky='nw')
        test1.grid_propagate(False)  # 크기 고정
        test1.rowconfigure(0, weight=1)
        test1.columnconfigure(0, weight=1)
        button = tk.Button(test1, text=name, width=_w12, height=_h02, 
                  command=call, #bd=0,
                  #relief="solid", 
                  relief="flat",
                  borderwidth = 1, 
                  highlightthickness=0
                )
        button.grid(row=0, column=0, padx=0, pady=0, sticky="nsew" )

    def build_frame_button(self, parent, width):
        frame = tk.LabelFrame(parent, text="", width=width, height=100, borderwidth=0, highlightthickness=0)
        frame.grid(row=4, column=0, padx=(0,0), pady=4)
        frame.grid_propagate(False)  # 크기 고정
        
        self.frame_button = frame

        self.create_button(frame, "훈련:100",
            lambda: self.parentTab.refill_request_list("훈련", update.refill_soldiers_training), 0, 0, 9, 3)
        self.create_button(frame, "충성: +5", 
            lambda: self.parentTab.refill_result_list("충성", update.refill_general_loyalty), 0, 1, 9, 3)
        self.create_button(frame, "행동:200", 
            lambda: self.parentTab.refill_request_list("행동", update.refill_general_actions), 0, 2, 9, 3)

        self.create_button(frame, "병사:+500", 
            lambda: self.parentTab.refill_result_list("병사", update.refill_general_soldiers), 3, 0, 9, 3)
        self.create_button(frame, "친밀: +10", 
            lambda: self.parentTab.refill_result_list("친밀", update.refill_general_relation), 3, 1, 9, 3)        
        self.create_button(frame, "포획:00", 
            lambda: self.parentTab.refill_all_list("포획", update.refill_general_captures), 3, 2, 9, 3)

        self.create_button(frame, "저장:선택장수", 
            lambda: self.parentTab.save_general_selected(), 0, 3, 17, 6)

