"""
얼굴 추출 패널 - 파라미터 관리 Mixin
이미지별 파라미터 로드/저장 관련 기능을 담당
"""
import os
import tkinter as tk

import utils.config as config


class ParameterManagerMixin:
    """파라미터 관리 기능 Mixin"""
    
    def _load_image_params(self, image_path):
        """이미지별 파라미터를 불러와서 적용"""
        if not image_path:
            # 파라미터 파일 상태 업데이트
            if hasattr(self, 'params_status_label'):
                self.params_status_label.config(text="", fg="gray")
            # 삭제 버튼 비활성화
            if hasattr(self, 'btn_delete_png'):
                self.btn_delete_png.config(state=tk.DISABLED)
            return
        
        # 파라미터 파일 존재 여부 확인 (parameters 폴더 내)
        import utils.config as config_util
        parameters_dir = config_util._get_parameters_dir(image_path)
        params_filename = config_util._get_parameters_filename(image_path)
        config_path = os.path.join(parameters_dir, params_filename)
        params_exists = os.path.exists(config_path)
        
        # 파라미터 파일 상태 표시
        if hasattr(self, 'params_status_label'):
            if params_exists:
                self.params_status_label.config(text="[파라미터 있음]", fg="green")
            else:
                self.params_status_label.config(text="[파라미터 없음]", fg="gray")
        
        # 삭제 버튼 상태 업데이트
        if hasattr(self, 'btn_delete_png'):
            if params_exists:
                self.btn_delete_png.config(state=tk.NORMAL)
            else:
                self.btn_delete_png.config(state=tk.DISABLED)
        
        params = config.load_face_extract_params(image_path)
        if not params:
            return
        
        try:
            # 팔레트 설정
            if 'palette_method' in params:
                self.palette_method.set(params['palette_method'])
            if 'use_palette' in params:
                self.use_palette.set(params['use_palette'])
            
            # 위치/배율 설정
            if 'crop_scale' in params:
                self.crop_scale.set(params['crop_scale'])
            if 'center_offset_x' in params:
                self.center_offset_x.set(params['center_offset_x'])
            if 'center_offset_y' in params:
                self.center_offset_y.set(params['center_offset_y'])
            
            # 이미지 조정 설정
            if 'brightness' in params:
                self.brightness.set(params['brightness'])
            if 'contrast' in params:
                self.contrast.set(params['contrast'])
            if 'saturation' in params:
                self.saturation.set(params['saturation'])
            if 'color_temp' in params:
                self.color_temp.set(params['color_temp'])
            if 'hue' in params:
                self.hue.set(params['hue'])
            if 'sharpness' in params:
                self.sharpness.set(params['sharpness'])
            if 'exposure' in params:
                self.exposure.set(params['exposure'])
            if 'equalize' in params:
                self.equalize.set(params['equalize'])
            if 'gamma' in params:
                self.gamma.set(params['gamma'])
            if 'vibrance' in params:
                self.vibrance.set(params['vibrance'])
            if 'clarity' in params:
                self.clarity.set(params['clarity'])
            if 'dehaze' in params:
                self.dehaze.set(params['dehaze'])
            if 'tint' in params:
                self.tint.set(params['tint'])
            if 'noise_reduction' in params:
                self.noise_reduction.set(params['noise_reduction'])
            if 'vignette' in params:
                self.vignette.set(params['vignette'])
            
            # 수동 영역 설정
            if 'use_manual_region' in params:
                self.use_manual_region.set(params['use_manual_region'])
            if 'manual_x' in params:
                self.manual_x.set(params['manual_x'])
            if 'manual_y' in params:
                self.manual_y.set(params['manual_y'])
            if 'manual_w' in params:
                self.manual_w.set(params['manual_w'])
            if 'manual_h' in params:
                self.manual_h.set(params['manual_h'])
            
            # 실제 사용된 얼굴 영역 (수동이든 자동이든)
            if all(key in params for key in ['face_region_x', 'face_region_y', 'face_region_w', 'face_region_h']):
                if params['face_region_x'] is not None and params['face_region_y'] is not None and \
                   params['face_region_w'] is not None and params['face_region_h'] is not None:
                    self.detected_face_region = (
                        params['face_region_x'],
                        params['face_region_y'],
                        params['face_region_w'],
                        params['face_region_h']
                    )
            
            # 수동 영역 설정 UI 업데이트 (체크박스 상태 및 입력 필드 활성화/비활성화)
            # extract_face는 load_image에서 호출되므로 여기서는 UI만 업데이트
            if 'use_manual_region' in params:
                # 체크박스는 변수 설정만으로 자동 반영됨
                # 입력 필드 활성화/비활성화는 on_manual_region_toggle에서 처리되지만,
                # 이미지가 로드되기 전이므로 여기서는 불필요 (load_image에서 extract_face 호출 후 처리됨)
                pass
            
            # UI 업데이트 콜백 호출
            # 이미지 조정 슬라이더 라벨 업데이트
            if hasattr(self, '_label_mapping'):
                for key, (var, label, formatter) in self._label_mapping.items():
                    if key in params:
                        label.config(text=formatter(var.get()))
            
            # 위치/배율 설정 UI 업데이트 (라벨만, extract_face는 load_image에서 호출)
            if 'crop_scale' in params or 'center_offset_x' in params or 'center_offset_y' in params:
                if hasattr(self, 'scale_label'):
                    scale_value = self.crop_scale.get()
                    self.scale_label.config(text=f"{int(scale_value * 100)}%")
                if hasattr(self, 'offset_x_label'):
                    offset_x = self.center_offset_x.get()
                    self.offset_x_label.config(text=str(offset_x))
                if hasattr(self, 'offset_y_label'):
                    offset_y = self.center_offset_y.get()
                    self.offset_y_label.config(text=str(offset_y))
            
            # 팔레트 설정 UI는 변수 설정만으로 자동 반영됨 (체크박스, 콤보박스)
            # 팔레트 미리보기는 extract_face 후에 update_palette_preview에서 처리됨
            
        except Exception as e:
            print(f"[얼굴추출] 파라미터 로드 실패: {e}")
    
    def _save_image_params(self, image_path):
        """현재 파라미터를 이미지별 설정 파일로 저장"""
        if not image_path:
            return
        
        try:
            # numpy 타입을 기본 Python 타입으로 변환하는 헬퍼 함수
            def to_python_type(value):
                """numpy 타입을 기본 Python 타입으로 변환"""
                import numpy as np
                if isinstance(value, (np.integer, np.int32, np.int64)):
                    return int(value)
                elif isinstance(value, (np.floating, np.float32, np.float64)):
                    return float(value)
                elif isinstance(value, np.ndarray):
                    return value.tolist()
                else:
                    return value
            
            params = {
                # 팔레트 설정
                'palette_method': str(self.palette_method.get()),
                'use_palette': bool(self.use_palette.get()),
                
                # 위치/배율 설정
                'crop_scale': float(self.crop_scale.get()),
                'center_offset_x': int(self.center_offset_x.get()),
                'center_offset_y': int(self.center_offset_y.get()),
                
                # 이미지 조정 설정
                'brightness': float(self.brightness.get()),
                'contrast': float(self.contrast.get()),
                'saturation': float(self.saturation.get()),
                'color_temp': float(self.color_temp.get()),
                'hue': float(self.hue.get()),
                'sharpness': float(self.sharpness.get()),
                'exposure': float(self.exposure.get()),
                'equalize': float(self.equalize.get()),
                'gamma': float(self.gamma.get()),
                'vibrance': float(self.vibrance.get()),
                'clarity': float(self.clarity.get()),
                'dehaze': float(self.dehaze.get()),
                'tint': float(self.tint.get()),
                'noise_reduction': float(self.noise_reduction.get()),
                'vignette': float(self.vignette.get()),
                
                # 수동 영역 사용 여부 및 좌표
                'use_manual_region': bool(self.use_manual_region.get()),
                'manual_x': int(self.manual_x.get()),
                'manual_y': int(self.manual_y.get()),
                'manual_w': int(self.manual_w.get()),
                'manual_h': int(self.manual_h.get()),
                
                # 실제 사용된 얼굴 영역 (수동이든 자동이든)
                'face_region_x': to_python_type(self.detected_face_region[0]) if self.detected_face_region else None,
                'face_region_y': to_python_type(self.detected_face_region[1]) if self.detected_face_region else None,
                'face_region_w': to_python_type(self.detected_face_region[2]) if self.detected_face_region else None,
                'face_region_h': to_python_type(self.detected_face_region[3]) if self.detected_face_region else None,
            }
            
            config.save_face_extract_params(image_path, params)
            
            # 파라미터 파일 상태 업데이트
            if hasattr(self, 'params_status_label'):
                self.params_status_label.config(text="[파라미터 있음]", fg="green")
            
            # 삭제 버튼 활성화
            if hasattr(self, 'btn_delete_png'):
                self.btn_delete_png.config(state=tk.NORMAL)
        except Exception as e:
            print(f"[얼굴추출] 파라미터 저장 실패: {e}")
