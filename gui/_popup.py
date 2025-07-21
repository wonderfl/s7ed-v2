import tkinter as tk

from . import _realm
from . import _city
from . import _item

# class RealmPopup(tk.Toplevel):
#     _instance = None

#     def __init__(self, parent):
#         super().__init__(parent)

#         self.title("세력 리스트")
#         #self.geometry("420x620")  # ✅ 팝업 창 크기 지정

#         self.rootframe = tk.LabelFrame(self, )
#         self.rootframe.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
#         #self.rootframe.grid_propagate(False) 

#         self.frame_realm = _realm.RealmTab(self.rootframe, 0, 0)

#         #tk.Button(self.rootframe, text="닫기", command=self.on_close).grid(row=0, column=0)

#     def on_close(self):
#         RealmPopup._instance = None
#         self.destroy()


# class CityPopup(tk.Toplevel):
#     _instance = None

#     def __init__(self, parent):
#         super().__init__(parent)

#         self.title("세력 리스트")
#         #self.geometry("420x620")  # ✅ 팝업 창 크기 지정

#         self.rootframe = tk.LabelFrame(self, )
#         self.rootframe.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
#         #self.rootframe.grid_propagate(False) 

#         self.frame_city = _city.CityTab(self.rootframe, 0, 0)

#         #tk.Button(self.rootframe, text="닫기", command=self.on_close).grid(row=0, column=0)

#     def on_close(self):
#         CityPopup._instance = None
#         self.destroy()

class ItemPopup(tk.Toplevel):
    _instance = None

    def __init__(self, parent, close_popup):
        super().__init__(parent)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.close_popup = close_popup 

        self.title("세력/도시/아이템 리스트")

        self.rootframe = tk.LabelFrame(self,  borderwidth=0, highlightthickness=0, )
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame_item = _item.ItemTab(self.rootframe)

    def on_close(self):
        print("on_close ItemPopup")
        #ItemPopup._instance = None
        if self.close_popup:
            self.close_popup()  # ✅ 종료 시 호출자에게 알림

        self.destroy()