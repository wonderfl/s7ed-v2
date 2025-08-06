import tkinter as tk

from . import _realm
from . import _city
from . import _item


class FramePopup(tk.Toplevel):
    _instance = None

    def __init__(self, parent, close_popup):
        super().__init__(parent)
        

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.close_popup = close_popup 

        self.title("세력/도시/아이템 리스트")

        self.rootframe = tk.LabelFrame(self,  borderwidth=0, highlightthickness=0, )
        self.rootframe.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.resizable(False, False)

        self.itemTab = _item.ItemTab(self.rootframe)
        self.realmTab = _realm.RealmTab(self.itemTab.rootframe, 0, 0)
        self.cityTab = _city.CityTab(self.itemTab.rootframe, 1, 0)

    def listup_tabs(self):
        self.itemTab.listup_items()
        self.realmTab.listup_realms()
        self.cityTab.listup_cities()                

    def on_close(self):
        print("on_close FramePopup")
        if self.close_popup:
            self.close_popup()  # ✅ 종료 시 호출자에게 알림

        self.destroy()