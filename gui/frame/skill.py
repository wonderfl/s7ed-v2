import tkinter as tk
import tkinter.font as tkfont

import globals as gl

class SkillFrame:
    _width01 = 280

    def __init__(self, app, parent, nr, nc):
      self.app = app
      self.build_skills(app, parent, nr, nc) # 특기
        
    def on_check_skills(self, pos):
        if self.app.general_selected is None:
            return
        selected = self.app.general_selected
        value = self.app.skillv[pos].get()
        data0 = selected.props
        data1 = gl.set_bits(data0, value, pos, 1)

        print('{0}[{1}]: {2:2}[ {3}, {4} ] '.format(selected.num, selected.name, pos, format(data0, '032b'), format(data1, '032b')))
        selected.props = data1
        selected.unpacked[0] = data1

    def build_skills(self, app, parent, nr, nc):
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
            app.skills.append(checked)
            app.skillv.append(var)