"""
얼굴 추출 패널 - 저장 기능 Mixin
이미지 저장 관련 기능을 담당
"""
import os
import re
import tkinter as tk
from tkinter import messagebox

import utils.kaodata_image as kaodata_image


class SaveManagerMixin:
    """저장 기능 Mixin"""
    
    def save_image(self):
        """이미지를 Kaodata.s7에 저장 (나중에 사용 예정)"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "얼굴을 추출할 수 없습니다.")
            return
        
        if self.face_entry is None:
            messagebox.showwarning("경고", "저장 위치 기능이 비활성화되어 있습니다.")
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
            filename = os.path.basename(self.current_image_path) if self.current_image_path else "이미지"
            result = messagebox.askyesno(
                "확인",
                f"추출된 얼굴 이미지를 얼굴 번호 {faceno}에 저장하시겠습니까?\n\n기존 이미지는 덮어씌워집니다."
            )
            
            if not result:
                return
            
            # 저장
            kaodata_image.save_face_image(faceno, self.extracted_image)
            
            # 완료 메시지는 messagebox로 표시되므로 상태 라벨에는 표시하지 않음
            # self.status_label.config(
            #     text=f"저장 완료: 얼굴 번호 {faceno}에 저장되었습니다.",
            #     fg="green"
            # )
            
            messagebox.showinfo("완료", f"얼굴 번호 {faceno}에 저장되었습니다.")
            
        except ValueError:
            messagebox.showerror("에러", "얼굴 번호는 숫자여야 합니다.")
        except Exception as e:
            messagebox.showerror("에러", f"저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def save_extracted_png(self):
        """추출된 이미지(팔레트 적용 전)를 PNG 파일로 저장"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            png_filename = f"{base_name}_extracted.png"
            
            # 저장 폴더 경로 결정 (설정된 폴더가 있으면 사용, 없으면 선택하거나 원본 이미지와 같은 디렉토리의 faces 폴더)
            faces_dir = self._get_or_select_extract_folder()
            if not faces_dir:
                # 사용자가 취소한 경우, 원본 이미지와 같은 디렉토리의 faces 폴더 사용
                original_dir = os.path.dirname(self.current_image_path)
                faces_dir = os.path.join(original_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (추출된 원본 이미지)
            self.extracted_image.save(file_path, "PNG")
            
            # 완료 메시지는 상태 라벨에 표시하지 않음 (에러/경고만 표시)
            # self.status_label.config(
            #     text=f"원본 저장 완료: {png_filename} (faces 폴더)",
            #     fg="green"
            # )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def save_png(self):
        """팔레트 적용된 이미지를 PNG 파일로 저장 (faces 폴더에 원본 파일명으로)"""
        if self.extracted_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
        
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        # 팔레트 적용 여부 확인
        if not self.use_palette.get() or self.palette_applied_image is None:
            messagebox.showwarning("경고", "팔레트가 적용되지 않았습니다. '원본 저장' 버튼을 사용하세요.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            # 앞부분의 영문자와 '_' 제거 (예: ABC_something -> something)
            base_name = re.sub(r'^[A-Za-z]+_', '', base_name)
            png_filename = f"{base_name}_s7.png"
            
            # 저장 폴더 경로 결정 (설정된 폴더가 있으면 사용, 없으면 선택하거나 원본 이미지와 같은 디렉토리의 faces 폴더)
            extract_dir = self._get_or_select_extract_folder()
            if not extract_dir:
                # 사용자가 취소한 경우, 원본 이미지와 같은 디렉토리의 faces 폴더 사용
                extract_dir = os.path.dirname(self.current_image_path)
                
            faces_dir = os.path.join(extract_dir, "faces")
            
            # faces 폴더가 없으면 생성
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # 파일 경로
            file_path = os.path.join(faces_dir, png_filename)
            
            # PNG로 저장 (팔레트 적용된 이미지)
            self.palette_applied_image.save(file_path, "PNG")
            
            # 이미지별 파라미터 저장
            self._save_image_params(self.current_image_path)
            
            # 완료 메시지는 상태 라벨에 표시하지 않음 (에러/경고만 표시)
            # self.status_label.config(
            #     text=f"PNG 저장 완료: {png_filename} (faces 폴더)",
            #     fg="green"
            # )
        
        except Exception as e:
            messagebox.showerror("에러", f"PNG 저장 실패:\n{e}")
            self.status_label.config(text=f"에러: {e}", fg="red")
    
    def delete_png(self):
        """팔레트 적용된 PNG 파일과 파라미터 파일 삭제"""
        if not self.current_image_path:
            messagebox.showwarning("경고", "원본 이미지 경로가 없습니다.")
            return
        
        try:
            # 원본 이미지 파일명 가져오기
            original_filename = os.path.basename(self.current_image_path)
            base_name = os.path.splitext(original_filename)[0]
            # 앞부분의 영문자와 '_' 제거 (예: ABC_something -> something)
            base_name = re.sub(r'^[A-Za-z]+_', '', base_name)
            png_filename = f"{base_name}_s7.png"
            
            # 저장 폴더 경로 결정 (설정된 폴더가 있으면 사용, 없으면 원본 이미지와 같은 디렉토리)
            extract_dir = self._get_or_select_extract_folder()
            if not extract_dir:
                # 사용자가 취소한 경우, 원본 이미지와 같은 디렉토리 사용
                extract_dir = os.path.dirname(self.current_image_path)
            
            faces_dir = os.path.join(extract_dir, "faces")
            png_file_path = os.path.join(faces_dir, png_filename)
            
            # 파라미터 파일 경로 (parameters 폴더 내)
            import utils.config as config_util
            parameters_dir = config_util._get_parameters_dir(self.current_image_path)
            params_filename = config_util._get_parameters_filename(self.current_image_path)
            params_file_path = os.path.join(parameters_dir, params_filename)
            
            # 삭제할 파일 목록 확인
            files_to_delete = []
            if os.path.exists(png_file_path):
                files_to_delete.append(("PNG 파일", png_file_path))
            if os.path.exists(params_file_path):
                files_to_delete.append(("파라미터 파일", params_file_path))
            
            if not files_to_delete:
                messagebox.showinfo("알림", "삭제할 파일이 없습니다.")
                return
            
            # 확인 대화상자
            file_list = "\n".join([f"- {name}: {os.path.basename(path)}" for name, path in files_to_delete])
            result = messagebox.askyesno(
                "확인",
                f"다음 파일들을 삭제하시겠습니까?\n\n{file_list}"
            )
            
            if not result:
                return
            
            # 파일 삭제
            deleted_count = 0
            for name, file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    messagebox.showerror("에러", f"{name} 삭제 실패:\n{e}")
            
            if deleted_count > 0:
                # 파라미터 상태 라벨 업데이트
                if hasattr(self, 'params_status_label'):
                    self.params_status_label.config(text="[파라미터 없음]", fg="gray")
                
                # 삭제 버튼 상태 업데이트
                if hasattr(self, 'btn_delete_png'):
                    self.btn_delete_png.config(state=tk.DISABLED)
                
                messagebox.showinfo("완료", f"{deleted_count}개 파일이 삭제되었습니다.")
        
        except Exception as e:
            messagebox.showerror("에러", f"삭제 실패:\n{e}")
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"에러: {e}", fg="red")
