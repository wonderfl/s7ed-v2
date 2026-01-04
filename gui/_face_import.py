"""
PNG 파일을 읽어서 Kaodata.s7에 저장하는 패널
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

import utils.kaodata_image as kaodata_image
import gui.frame_basic as _basic

class FaceImportPanel(tk.Toplevel):
    """PNG 파일을 읽어서 Kaodata.s7에 저장하는 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("얼굴 이미지 가져오기")
        self.resizable(False, False)
        
        # 현재 선택된 이미지
        self.current_image = None
        self.current_image_path = None
        self.tk_image = None
        self.image_created = None
        
        self.create_widgets()
        
        # 창 닫기 이벤트
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 파일 선택 프레임
        file_frame = tk.LabelFrame(main_frame, text="PNG 파일 선택", padx=5, pady=5)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_path_label = tk.Label(file_frame, text="파일을 선택하세요", width=40, anchor="w")
        self.file_path_label.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_browse = tk.Button(file_frame, text="찾아보기...", command=self.browse_file, width=12)
        btn_browse.pack(side=tk.LEFT)
        
        # 이미지 미리보기 프레임 (2개 이미지 나란히 표시)
        preview_frame = tk.LabelFrame(main_frame, text="미리보기", padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 좌측: 새로 가져올 이미지
        left_frame = tk.Frame(preview_frame)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(left_frame, text="새 이미지", font=("", 9)).pack()
        self.canvas_new = tk.Canvas(
            left_frame, 
            width=_basic.BasicFrame.image_width *2, 
            height=_basic.BasicFrame.image_height*2,
            bg="gray"
        )
        self.canvas_new.pack(padx=5, pady=5)
        self.tk_image_new = None
        self.image_created_new = None
        
        # 우측: 현재 저장된 이미지
        right_frame = tk.Frame(preview_frame)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(right_frame, text="현재 이미지", font=("", 9)).pack()
        self.canvas_current = tk.Canvas(
            right_frame, 
            width=_basic.BasicFrame.image_width *2, 
            height=_basic.BasicFrame.image_height*2,
            bg="gray"
        )
        self.canvas_current.pack(padx=5, pady=5)
        self.tk_image_current = None
        self.image_created_current = None
        
        # 얼굴 번호 입력 프레임
        face_frame = tk.LabelFrame(main_frame, text="저장 위치", padx=5, pady=5)
        face_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(face_frame, text="얼굴 번호:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.face_entry = tk.Entry(face_frame, width=10)
        self.face_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.face_entry.insert(0, "0")
        self.face_entry.bind("<Return>", lambda e: self.save_image())
        self.face_entry.bind("<KeyRelease>", lambda e: self.update_current_preview())
        
        tk.Label(face_frame, text="(0~647)", fg="gray").pack(side=tk.LEFT)
        
        # 얼굴 인식 옵션 체크박스
        self.use_face_detection = tk.BooleanVar()
        self.use_face_detection.set(False)
        face_detection_check = tk.Checkbutton(
            face_frame, 
            text="얼굴 인식 사용", 
            variable=self.use_face_detection,
            command=self.on_face_detection_toggle
        )
        face_detection_check.pack(side=tk.LEFT, padx=(20, 0))
        
        # 버튼 프레임
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        btn_save = tk.Button(button_frame, text="저장", command=self.save_image, width=12, bg="#4CAF50", fg="white")
        btn_save.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_close = tk.Button(button_frame, text="닫기", command=self.on_close, width=12)
        btn_close.pack(side=tk.LEFT)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="준비됨", fg="gray", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(5, 0))
    
    def browse_file(self):
        """파일 선택 대화상자"""
        # 저장된 PNG 디렉토리 경로 가져오기
        initial_dir = kaodata_image.get_png_dir()
        if not os.path.exists(initial_dir):
            initial_dir = None
        
        file_path = filedialog.askopenfilename(
            title="PNG 파일 선택",
            filetypes=[("PNG 파일", "*.png"), ("모든 파일", "*.*")],
            initialdir=initial_dir
        )
        
        if file_path:
            # 선택한 파일의 디렉토리 경로 저장
            png_dir = os.path.dirname(file_path)
            kaodata_image.set_png_dir(png_dir)
            # 설정 파일에 저장
            import utils.config as config
            config.save_config()
            
            self.load_image(file_path)
    
    def load_image(self, file_path):
        """이미지 로드 및 미리보기"""
        try:
            # 이미지 읽기
            img = Image.open(file_path)
            
            # 이미지 저장
            self.current_image = img
            self.current_image_path = file_path
            
            # 파일명 표시
            filename = os.path.basename(file_path)
            self.file_path_label.config(text=filename)
            
            # 미리보기 표시
            self.show_preview(img)
            
            self.status_label.config(text=f"이미지 로드 완료: {filename}", fg="green")
            
        except Exception as e:
            messagebox.showerror("에러", f"이미지를 읽을 수 없습니다:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def show_preview(self, image):
        """새 이미지 미리보기 표시"""
        # 얼굴 인식이 켜져 있으면 얼굴 영역 추출
        preview_image = image
        if self.use_face_detection.get():
            try:
                preview_image = kaodata_image.extract_face_region(image.copy())
            except ValueError as e:
                # 얼굴을 찾을 수 없는 경우
                self.status_label.config(text=f"경고: {str(e)}", fg="orange")
                preview_image = image  # 원본 이미지 표시
            except Exception as e:
                print(f"[얼굴이미지] 미리보기 얼굴 추출 실패: {e}")
                self.status_label.config(text=f"에러: {e}", fg="red")
                preview_image = image  # 원본 이미지 표시
        
        # 이미지 리사이즈
        preview_size = (_basic.BasicFrame.image_width *2, _basic.BasicFrame.image_height*2)
        resized = preview_image.resize(preview_size, Image.LANCZOS)
        
        # PhotoImage로 변환
        self.tk_image_new = ImageTk.PhotoImage(resized)
        
        # Canvas에 표시
        if self.image_created_new:
            self.canvas_new.delete(self.image_created_new)
        
        self.image_created_new = self.canvas_new.create_image(
            _basic.BasicFrame.image_width,
            _basic.BasicFrame.image_height,
            image=self.tk_image_new
        )
        
        # 현재 이미지도 업데이트
        self.update_current_preview()
    
    def on_face_detection_toggle(self):
        """얼굴 인식 체크박스 토글 시 미리보기 업데이트"""
        if self.current_image is not None:
            self.show_preview(self.current_image)
    
    def update_current_preview(self):
        """현재 저장된 이미지 미리보기 업데이트"""
        try:
            faceno_str = self.face_entry.get().strip()
            if not faceno_str:
                # 얼굴 번호가 없으면 빈 화면
                if self.image_created_current:
                    self.canvas_current.delete(self.image_created_current)
                return
            
            faceno = int(faceno_str)
            
            if faceno < 0 or faceno >= 648:
                # 범위를 벗어나면 빈 화면
                if self.image_created_current:
                    self.canvas_current.delete(self.image_created_current)
                return
            
            # Kaodata.s7에서 현재 이미지 읽기
            current_img = kaodata_image.get_face_image(faceno)
            
            # 이미지 리사이즈
            preview_size = (_basic.BasicFrame.image_width *2, _basic.BasicFrame.image_height*2)
            resized = current_img.resize(preview_size, Image.LANCZOS)
            
            # PhotoImage로 변환
            self.tk_image_current = ImageTk.PhotoImage(resized)
            
            # Canvas에 표시
            if self.image_created_current:
                self.canvas_current.delete(self.image_created_current)
            
            self.image_created_current = self.canvas_current.create_image(
                _basic.BasicFrame.image_width,
                _basic.BasicFrame.image_height,
                image=self.tk_image_current
            )
            
        except ValueError:
            # 숫자가 아니면 빈 화면
            if self.image_created_current:
                self.canvas_current.delete(self.image_created_current)
        except Exception as e:
            # 에러 발생 시 빈 화면
            if self.image_created_current:
                self.canvas_current.delete(self.image_created_current)
            print(f"[얼굴이미지] 현재 이미지 읽기 실패: {e}")
    
    def save_image(self):
        """이미지를 Kaodata.s7에 저장"""
        if self.current_image is None:
            messagebox.showwarning("경고", "먼저 PNG 파일을 선택하세요.")
            return
        
        try:
            # 얼굴 번호 확인
            faceno_str = self.face_entry.get().strip()
            if not faceno_str:
                messagebox.showwarning("경고", "얼굴 번호를 입력하세요.")
                return
            
            faceno = int(faceno_str)
            
            if faceno < 0 or faceno >= 648:
                messagebox.showerror("에러", "얼굴 번호는 0~647 사이여야 합니다.")
                return
            
            # 확인 대화상자
            filename = os.path.basename(self.current_image_path)
            result = messagebox.askyesno(
                "확인",
                f"'{filename}' 파일을 얼굴 번호 {faceno}에 저장하시겠습니까?\n\n기존 이미지는 덮어씌워집니다."
            )
            
            if not result:
                return
            
            # 저장 (얼굴 인식 옵션 적용)
            use_detection = self.use_face_detection.get()
            try:
                kaodata_image.save_face_from_png(self.current_image_path, faceno, use_face_detection=use_detection)
            except ValueError as e:
                # 얼굴을 찾을 수 없는 경우
                messagebox.showerror("얼굴 인식 실패", f"{str(e)}\n\n얼굴 인식 체크박스를 해제하고 다시 시도하세요.")
                return
            
            # 현재 이미지 미리보기 업데이트
            self.update_current_preview()
            
            self.status_label.config(
                text=f"저장 완료: 얼굴 번호 {faceno}에 저장되었습니다.",
                fg="green"
            )
            
            messagebox.showinfo("완료", f"얼굴 번호 {faceno}에 저장되었습니다.")
            
        except ValueError:
            messagebox.showerror("에러", "얼굴 번호는 숫자여야 합니다.")
        except Exception as e:
            messagebox.showerror("에러", f"저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def on_close(self):
        """창 닫기"""
        self.destroy()

def show_face_import_panel(parent=None):
    """얼굴 이미지 가져오기 패널 표시"""
    panel = FaceImportPanel(parent)
    panel.transient(parent)  # 부모 창에 종속
    # grab_set() 제거: 다른 창과 함께 사용 가능하도록 비모달로 설정
    return panel

