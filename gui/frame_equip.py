import tkinter as tk
import tkinter.font as tkfont

import globals as gl

class EquipFrame:
    _width01 = 280

    def __init__(self, app, parent, nr, nc):
      self.app = app
      self.build_equips(app, parent, nr, nc) # 특기

    def on_check_equips(self, pos):
        if self.app.general_selected is None:
            return
        selected = self.app.general_selected
        value = self.app.equipv[pos].get()
        data0 = selected.equips
        data1 = gl.set_bits(data0, value, pos, 1)

        print('{0}[{1}]: {2:2}[ {3}, {4} ] '.format(selected.num, selected.name, pos, format(data0, '016b'), format(data1, '016b')))
        selected.equips = data1
        selected.unpacked[16] = data1      

    def build_equips(self, app, parent, nr, nc):        
        frame_equip = tk.LabelFrame(parent, text="무장 장비", width=self._width01, height=92)
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
            app.equips.append(checked)
            app.equipv.append(var)      