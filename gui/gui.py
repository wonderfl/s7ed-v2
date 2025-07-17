import tkinter as tk
from tkinter import ttk

class OfficerEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("삼국지 VII - 장수 에디터 (전체 GUI 구성)")
        self.create_widgets()

    def create_widgets(self):
        # 좌측 장수 리스트
        self.frame_left = tk.Frame(self.root)
        self.frame_left.grid(row=0, column=0, sticky="nsw", padx=5, pady=0)

        tk.Label(self.frame_left).pack()
        self.listbox = tk.Listbox(self.frame_left, height=36, width=20)
        self.listbox.pack(fill="y")

        for i in range(620):
            self.listbox.insert(tk.END, f"장수 {i:03}")

        # 우측 전체 정보
        self.frame_right = tk.Frame(self.root)
        self.frame_right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.build_right_side(self.frame_right)

        # 하단 푸터/풋바
        #self.footbar = tk.Frame(self.root)
        #self.footbar.pack(side="bottom", fill="x")

    def build_right_side(self, parent):

        _width0 = 268
        def entry_row(frame, labels, width=4):
            for i, text in enumerate(labels):
                tk.Label(frame, text=text).grid(row=0, column=i * 2)
                tk.Entry(frame, width=width ).grid(row=0, column=i * 2 + 1)

        # 기본 설정
        frame_basic = tk.LabelFrame(parent, text="무장 기본 설정", width=_width0, height=72)
        frame_basic.grid(row=0, column=0)
        frame_basic.grid_propagate(False)  # 크기 고정

        frame_b1 = tk.LabelFrame(frame_basic, text="", width=_width0-4, height=24, borderwidth=0, highlightthickness=0)
        frame_b1.grid(row=0, column=0)
        frame_b1.grid_propagate(False)  # 크기 고정        

        frame_b2 = tk.LabelFrame(frame_basic, text="", width=_width0-4, height=24,borderwidth=0, highlightthickness=0)
        frame_b2.grid(row=1, column=0)
        frame_b2.grid_propagate(False)  # 크기 고정                

        entry_row(frame_b1, ["성", "명", "자"])
        tk.Label(frame_b1, text="별명").grid(row=0, column=6)
        tk.Entry(frame_b1, width=6 ).grid(row=0, column=7)

        tk.Label(frame_b2, text="얼굴").grid(row=1, column=0)
        tk.Entry(frame_b2, width=6).grid(row=1, column=1)

        gender_var = tk.StringVar(value="남")
        tk.Label(frame_b2, text="성별").grid(row=1, column=3)
        tk.Radiobutton(frame_b2, text="남", variable=gender_var, value="남").grid(row=1, column=4)
        tk.Radiobutton(frame_b2, text="여", variable=gender_var, value="여").grid(row=1, column=5)
        tk.Checkbutton(frame_b2, text="행동유무").grid(row=1, column=7)

        # 혈연
        frame_family = tk.LabelFrame(parent, text="무장 혈연", width=_width0, height=54)
        frame_family.grid(row=1, column=0)
        frame_family.grid_propagate(False)  # 크기 고정

        for i, label in enumerate(["가문", "부모"]):
            tk.Label(frame_family, text=label).grid(row=0, column=i*3)
            tk.Entry(frame_family, width=6).grid(row=0, column=i*3 + 1)
            tk.Button(frame_family, text="표시").grid(row=0, column=i*3 + 2)

        # 특성
        frame_traits = tk.LabelFrame(parent, text="무장 특성", width=_width0, height=80)
        frame_traits.grid(row=2, column=0)
        frame_traits.grid_propagate(False)  # 크기 고정
        for i, label in enumerate(["무력", "지력", "정치", "매력"]):
            tk.Radiobutton(frame_traits, text=label).grid(row=0, column=i)
        for i, label in enumerate(["장군", "군사", "만능", "평범"]):
            tk.Radiobutton(frame_traits, text=label).grid(row=1, column=i)

        # 능력치
        frame_stats = tk.LabelFrame(parent, text="무장 능력", width=_width0, height=48)
        frame_stats.grid(row=3, column=0)
        frame_stats.grid_propagate(False)  # 크기 고정
        entry_row(frame_stats, ["무력", "지력", "정치", "매력"])

        # 특기
        frame_skills = tk.LabelFrame(parent, text="무장 특기", width=_width0, height=220)
        frame_skills.grid(row=4, column=0)
        frame_skills.grid_propagate(False)  # 크기 고정
        skills = [
            "첩보","발명","조교","상재", "응사","반계","수습","정찰",
            "무쌍","돌격","일기","강행", "수복","수군","화시","난시",
            "선동","신산","허보","천문", "수공","고무","욕설","혈공",
            "귀모","성흔","행동","단련", "의술","점복","평가","부호",
        ]
        for i, skill in enumerate(skills):
            tk.Checkbutton(frame_skills, text=skill).grid(row=i//4, column=i%4, sticky="w")

        # 장비
        frame_equip = tk.LabelFrame(parent, text="무장 장비", width=_width0, height=120)
        frame_equip.grid(row=5, column=0)
        frame_equip.grid_propagate(False)  # 크기 고정
        equips = ["궁", "등갑", "기마", "마갑", "철갑", "노", "연노", "정란", "벽력거", "화포", "코끼리", "목수", "몽충","누선"]
        for i, equip in enumerate(equips):
            tk.Checkbutton(frame_equip, text=equip).grid(row=i//4, column=i%4, sticky="w")

        _width1 = 350
        _width2 = 340

        # 개성
        frame_personality = tk.LabelFrame(parent, text="무장 개성", width=_width1, height=240)
        frame_personality.grid(row=0, column=1, rowspan=4)
        frame_personality.grid_propagate(False)  # 크기 고정

        frame_r1 = tk.LabelFrame(frame_personality, text="", width=_width2, height=112, borderwidth=0, highlightthickness=0)
        frame_r1.grid(row=0, column=0)
        frame_r1.grid_propagate(False)  # 크기 고정

        fields = ["탄생","등장","사관","수명", "성장","상성","야망","의리", "용맹","냉정","명성","공적", "봉록","행동력","병사","훈련", "충성","아이템"]
        for i, field in enumerate(fields):
            tk.Label(frame_r1, text=field).grid(row=i//4, column=(i%4)*2)
            tk.Entry(frame_r1, width=6).grid(row=i//4, column=(i%4)*2 +1)

        frame_r2 = tk.LabelFrame(frame_personality, text="", width=_width2, height=108, borderwidth=0, highlightthickness=0)
        frame_r2.grid(row=1, column=0)
        frame_r2.grid_propagate(False)  # 크기 고정
        for i, label in enumerate(["포획군주", "포획세력", "작적세력"]):
            tk.Label(frame_r2, text=label).grid(row=i+4, column=0)
            tk.Entry(frame_r2, width=8).grid(row=i+4, column=1)
            tk.Button(frame_r2, text="표시").grid(row=i+4, column=2)

        for i, label in enumerate(["포획횟수", "매복기간", "작적기간"]):
            tk.Label(frame_r2, text=label).grid(row=i+4, column=3)
            tk.Entry(frame_r2, width=6).grid(row=i+4, column=4)

        # 경향
        tk.Label(frame_r2, text="인물 경향").grid(row=11, column=0)
        ttk.Combobox(frame_r2, values=["의리 중시형", "이익 중시형", "충성형"], width=12).grid(row=11, column=1, columnspan=2)
        tk.Label(frame_r2, text="전략 경향").grid(row=11, column=3)
        ttk.Combobox(frame_r2, values=["내정형", "군사형", "균형형"], width=12).grid(row=11, column=4, columnspan=2)

        frame_exp = tk.LabelFrame(parent, text="", width=_width1, height=200, borderwidth=0, highlightthickness=0)
        frame_exp.grid(row=4, column=1)
        frame_exp.grid_propagate(False)  # 크기 고정        

        # 단련 경험
        frame_exp1 = tk.LabelFrame(frame_exp, text="무장 경험", width=_width1, height=48)
        frame_exp1.grid(row=0, column=0)
        frame_exp1.grid_propagate(False)  # 크기 고정
        entry_row(frame_exp1, ["무력", "지력", "정치", "매력"])

        # 소속
        frame_affil = tk.LabelFrame(frame_exp, text="무장 소속", width=_width1, height=120)
        frame_affil.grid(row=1, column=0)
        frame_affil.grid_propagate(False)  # 크기 고정

        tk.Label(frame_affil, text="세력").grid(row=0, column=0)
        tk.Entry(frame_affil, width=5).grid(row=0, column=1)
        tk.Button(frame_affil, text="표시").grid(row=0, column=2)

        tk.Label(frame_affil, text="도시").grid(row=0, column=3)
        ttk.Combobox(frame_affil, values=["시상", "허창", "하비", "낙양"], width=12).grid(row=0, column=4, columnspan=2)

        tk.Label(frame_affil, text="장군직").grid(row=1, column=0)
        ttk.Combobox(frame_affil, values=["없음", "도독", "장군", "대장군"], width=12).grid(row=1, column=1, columnspan=2)

        tk.Label(frame_affil, text="계급").grid(row=1, column=3)
        ttk.Combobox(frame_affil, values=["1품관", "2품관", "3품관", "4품관", "5품관"], width=12).grid(row=1, column=4, columnspan=2)

        tk.Label(frame_affil, text="신분").grid(row=2, column=0)
        ttk.Combobox(frame_affil, values=["대기", "포로", "중립"], width=12).grid(row=2, column=1, columnspan=2)
        
        tk.Label(frame_affil, text="등록").grid(row=2, column=3)
        tk.Entry(frame_affil, width=6).grid(row=2, column=4)
        tk.Button(frame_affil, text="표시").grid(row=2, column=5)

        # 설정 버튼
        tk.Button(parent, text="설 정", width=10).grid(row=5, column=1)


if __name__ == "__main__":
    root = tk.Tk()
    app = OfficerEditorApp(root)
    root.mainloop()
