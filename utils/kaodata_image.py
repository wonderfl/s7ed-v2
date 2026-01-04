"""
Kaodata.s7 파일에서 얼굴 이미지를 읽어오는 유틸리티
"""
import os
import re
import glob
from PIL import Image
import numpy as np

# OpenCV 선택적 import (없어도 동작)
try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False
    print("[얼굴이미지] OpenCV가 설치되지 않았습니다. 얼굴 인식 기능을 사용하려면 'pip install opencv-python'을 실행하세요.")

# globals 모듈 import
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import globals as gl

# 얼굴 이미지 상수
FACE_WIDTH = 96
FACE_HEIGHT = 120
FACE_SIZE = FACE_WIDTH * FACE_HEIGHT  # 11520 bytes (팔레트 모드)

# 기본 Kaodata.s7 파일 경로 (fallback용)
DEFAULT_KAODATA_PATH = 'saves/Kaodata.s7'

# 헤더 크기 (추정)
HEADER_SIZE = 10372

# 전역 변수: 파일 핸들 캐싱
_kaodata_file = None
_kaodata_file_path = None

# 전역 변수: 팔레트 캐싱
_face_palette = None

def get_face_file_path():
    """얼굴 파일 경로를 가져옵니다. 설정되지 않았으면 기본 경로를 반환합니다."""
    if gl._face_file and len(gl._face_file) > 0:
        return gl._face_file
    # 기본 경로 (상대 경로를 절대 경로로 변환)
    default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), DEFAULT_KAODATA_PATH)
    return default_path

def set_face_file_path(file_path):
    """얼굴 파일 경로를 설정합니다."""
    if file_path and os.path.exists(file_path):
        gl._face_file = os.path.abspath(file_path)
        # 파일 핸들도 닫아서 다음에 새 경로로 열리도록 함
        close_kaodata_file()
    else:
        print(f"[얼굴이미지] 파일 경로 설정 실패: {file_path}")

def _load_face_palette():
    """기존 PNG 파일에서 팔레트를 로드합니다."""
    global _face_palette
    
    if _face_palette is not None:
        return _face_palette
    
    # 기존 PNG 파일에서 팔레트 추출
    png_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'palette.png')
    
    try:
        ref_img = Image.open(png_path)
        if ref_img.palette:
            _face_palette = ref_img.palette.palette
            return _face_palette
    except Exception as e:
        print(f"[얼굴이미지] 팔레트 로드 실패: {e}")
    
    # 폴백: 기본 팔레트 (그레이스케일)
    palette_list = []
    for i in range(256):
        palette_list.extend([i, i, i])
    _face_palette = bytes(palette_list)
    return _face_palette

# 얼굴 이미지 팔레트 (256색 RGB)
FACE_PALETTE = bytes([
      0,   0,   0,  16,  16,   8,  24,  16,  16,  24,  24,  16,  24,  24,  24,  32,
     32,  24,  32,  32,  32,  48,  32,  16,  42,  32,  24,  42,  48,  56,  42,  42,
     42,  48,  42,  32,  64,  42,  24,  42,  48,  56,  56,  48,  32,  48,  48,  48,
     64,  56,  48,  72,  48,  32,  56,  56,  56,  72,  56,  48,  64,  56,  48,  96,
     48,  24,  64,  64,  64,  80,  64,  48,  88,  56,  42,  56,  72,  72,  72,  72,
     64,  80,  72,  64,  88,  72,  56,  96,  72,  48, 104,  72,  42, 132,  64,  42,
    104,  64,  80,  88,  80,  64,  72,  80,  88,  72,  88,  64,  96,  80,  64,  64,
     88, 112, 104,  80,  56,  88,  80,  80,  96,  88,  72, 112,  88,  32, 136,  72,
     48, 112,  80,  64,  96,  88,  88, 104,  88,  72,  88, 104,  72, 164,  72,  32,
    104,  96,  72, 112,  80, 104,  96,  96,  88,  88,  96, 104, 120,  96,  64, 112,
     96,  72,  72, 112, 112, 104, 104,  96, 144,  88,  64,  96, 112,  88,  96, 104,
    112, 120,  96, 112, 120, 104,  80, 128,  96,  72, 120, 104,  64, 112, 104, 104,
    144, 104,  32, 176,  88,  56, 120, 112,  96,  96, 120, 104, 112, 112, 104, 104,
    112, 128, 128, 112,  88, 160,  96,  72, 120, 120,  80, 136, 112,  64, 144, 104,
     80, 136, 112,  88, 120, 120, 104, 120, 120, 120, 136, 112, 136, 112, 120, 128,
    112, 132, 104,  96, 136, 148, 160, 112,  80, 148, 120,  56, 156, 120,  88, 136,
    120, 104, 148, 120,  96, 132, 132, 120, 160, 120,  40, 188, 104,  72, 132, 140,
    104, 120, 132, 148, 148, 132,  96, 160, 132,  96, 172, 120,  88, 140, 134, 123,
    132, 134, 132, 173, 142,  66, 156, 142,  82, 156, 134, 107, 156, 134, 148, 132,
    150, 148, 181, 134,  99, 173, 134,  99, 140, 142, 140, 148, 142, 132, 140, 158,
    115, 206, 121,  99, 165, 142, 115, 173, 142, 115, 123, 150, 181, 189, 150,  49,
    140, 150, 156, 181, 142, 107, 156, 150, 132, 148, 150, 148, 173, 150, 107, 181,
    158,  74, 165, 150, 165, 173, 150, 123, 181, 150, 115, 148, 158, 173, 189, 150,
    107, 156, 158, 156, 181, 158, 123, 165, 158, 140, 156, 166, 132, 189, 150, 148,
    189, 158, 115, 181, 166,  99, 165, 166, 156, 206, 150, 107, 222, 142, 115, 181,
    158, 132, 140, 174, 173, 189, 158, 123, 156, 166, 165, 198, 158, 115, 198, 166,
     74, 173, 166, 148, 173, 166, 173, 189, 166, 140, 214, 158, 115, 173, 174, 132,
    206, 166, 123, 198, 166, 132, 181, 166, 148, 156, 174, 181, 173, 174, 165, 198,
    174, 140, 189, 174, 123, 222, 166, 115, 214, 166, 123, 206, 166, 140, 181, 182,
    165, 198, 174, 148, 206, 174, 132, 181, 182, 181, 148, 190, 214, 165, 182, 189,
    206, 182,  90, 222, 174, 123, 231, 174, 123, 189, 182, 173, 181, 190, 156, 214,
    174, 140, 206, 182, 148, 222, 182, 132, 206, 190, 132, 189, 190, 189, 198, 190,
    165, 214, 182, 181, 214, 182, 156, 222, 182, 148, 239, 182, 123, 181, 199, 206,
    231, 182, 140, 198, 190, 189, 222, 199, 115, 231, 190, 148, 206, 199, 173, 239,
    190, 132, 198, 199, 189, 222, 190, 165, 189, 207, 173, 239, 190, 148, 173, 207,
    222, 231, 190, 156, 222, 199, 148, 198, 207, 214, 206, 207, 198, 214, 199, 181,
    247, 199, 140, 239, 199, 156, 231, 199, 173, 247, 199, 148, 239, 199, 165, 206,
    207, 206, 198, 215, 198, 214, 207, 189, 222, 207, 181, 239, 207, 181, 222, 207,
    214, 247, 207, 165, 247, 207, 156, 231, 207, 198, 189, 223, 231, 222, 215, 198,
    206, 215, 231, 214, 215, 214, 239, 215, 140, 239, 215, 189, 247, 215, 181, 206,
    231, 206, 255, 215, 165, 231, 215, 214, 231, 223, 189, 222, 223, 214, 222, 223,
    222, 247, 215, 189, 222, 231, 198, 206, 231, 239, 255, 223, 189, 214, 231, 239,
    239, 223, 214, 247, 223, 206, 231, 231, 222, 255, 223, 198, 222, 239, 214, 247,
    231, 214, 231, 231, 222, 247, 231, 181, 222, 239, 239, 255, 231, 206, 231, 239,
    222, 231, 239, 239, 247, 231, 222, 255, 231, 214, 255, 247, 148, 239, 239, 231,
    247, 239, 206, 255, 239, 222, 247, 239, 222, 239, 239, 239, 231, 247, 247, 247,
    239, 239, 255, 247, 198, 255, 239, 231, 247, 247, 231, 247, 247, 247, 255, 247,
    222, 255, 247, 239, 247, 247, 247, 255, 255, 239, 255, 255, 247, 255, 255, 255,
])

def get_face_image(faceno):
    """
    Kaodata.s7 파일에서 얼굴 번호에 해당하는 이미지를 읽어옵니다.
    
    Args:
        faceno: 얼굴 번호 (0~647)
    
    Returns:
        PIL.Image.Image: 얼굴 이미지 (96x120, 팔레트 모드)
    
    Raises:
        FileNotFoundError: Kaodata.s7 파일을 찾을 수 없을 때
        ValueError: faceno가 범위를 벗어날 때
        IOError: 파일 읽기 실패 시
    """
    global _kaodata_file, _kaodata_file_path
    
    if faceno < 0 or faceno >= 648:
        raise ValueError(f"얼굴 번호는 0~647 사이여야 합니다. (입력: {faceno})")
    
    # 파일 경로 확인
    file_path = get_face_file_path()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Kaodata.s7 파일을 찾을 수 없습니다: {file_path}")
    
    # 파일 핸들 재사용 또는 새로 열기
    if _kaodata_file_path != file_path or _kaodata_file is None:
        if _kaodata_file is not None:
            _kaodata_file.close()
        _kaodata_file = open(file_path, 'rb')
        _kaodata_file_path = file_path
    
    # 얼굴 데이터 위치 계산
    offset = HEADER_SIZE + (faceno * FACE_SIZE)
    
    try:
        _kaodata_file.seek(offset)
        face_data = _kaodata_file.read(FACE_SIZE)
        
        if len(face_data) != FACE_SIZE:
            raise IOError(f"얼굴 데이터를 읽지 못했습니다. (요청: {FACE_SIZE}, 읽음: {len(face_data)})")
        
        # 팔레트 모드 이미지 생성
        img = Image.frombytes('P', (FACE_WIDTH, FACE_HEIGHT), face_data)
        
        # 게임 팔레트 적용
        #palette_data = _load_face_palette()
        #img.putpalette(palette_data)

        img.putpalette(FACE_PALETTE)
        
        return img
        
    except Exception as e:
        raise IOError(f"얼굴 이미지 읽기 실패 (faceno: {faceno}): {e}")

def save_face_image(faceno, image):
    """
    Kaodata.s7 파일에 얼굴 번호에 해당하는 이미지를 저장합니다.
    
    Args:
        faceno: 얼굴 번호 (0~647)
        image: PIL.Image.Image 객체 (96x120 크기 권장, 다른 크기는 자동 리사이즈)
    
    Raises:
        FileNotFoundError: Kaodata.s7 파일을 찾을 수 없을 때
        ValueError: faceno가 범위를 벗어나거나 이미지가 유효하지 않을 때
        IOError: 파일 쓰기 실패 시
    """
    if faceno < 0 or faceno >= 648:
        raise ValueError(f"얼굴 번호는 0~647 사이여야 합니다. (입력: {faceno})")
    
    if image is None:
        raise ValueError("이미지가 None입니다.")
    
    # 파일 경로 확인
    file_path = get_face_file_path()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Kaodata.s7 파일을 찾을 수 없습니다: {file_path}")
    
    try:
        # 이미지 준비
        # 1. 크기 확인 및 리사이즈
        if image.size != (FACE_WIDTH, FACE_HEIGHT):
            img_resized = image.resize((FACE_WIDTH, FACE_HEIGHT), Image.LANCZOS)
        else:
            img_resized = image.copy()
        
        # 2. 팔레트 모드로 변환
        if img_resized.mode != 'P':
            # RGB/RGBA를 팔레트 모드로 변환
            # 먼저 팔레트를 적용한 상태로 변환
            img_palette = img_resized.quantize(palette=Image.new('P', (1, 1)))
            # 게임 팔레트 적용
            img_palette.putpalette(FACE_PALETTE)
        else:
            img_palette = img_resized
            # 팔레트가 다를 수 있으므로 게임 팔레트로 교체
            img_palette.putpalette(FACE_PALETTE)
        
        # 3. 바이트 데이터 추출
        face_data = bytearray(img_palette.tobytes())
        cnt = 0
        for i in range(len(face_data)):
            if 0 == face_data[i]:
                face_data[i] = 1
                cnt += 1
        print(f"face_data: {len(face_data)}, 0: {cnt}")
        

        if len(face_data) != FACE_SIZE:
            raise IOError(f"이미지 데이터 크기가 맞지 않습니다. (요청: {FACE_SIZE}, 실제: {len(face_data)})")
        
        # 4. 파일 쓰기 (읽기 모드로 열린 파일이 있으면 닫기)
        global _kaodata_file, _kaodata_file_path
        if _kaodata_file is not None:
            _kaodata_file.close()
            _kaodata_file = None
            _kaodata_file_path = None
        
        # 5. 쓰기 모드로 파일 열기
        with open(file_path, 'r+b') as f:
            offset = HEADER_SIZE + (faceno * FACE_SIZE)
            f.seek(offset)
            written = f.write(face_data)
            
            if written != FACE_SIZE:
                raise IOError(f"이미지 데이터를 모두 쓰지 못했습니다. (요청: {FACE_SIZE}, 쓴 크기: {written})")
        
        # 6. 파일 핸들 재생성 (읽기용)
        _kaodata_file = open(file_path, 'rb')
        _kaodata_file_path = file_path
        
    except Exception as e:
        raise IOError(f"얼굴 이미지 저장 실패 (faceno: {faceno}): {e}")

def convert_to_palette_colors(image, palette=FACE_PALETTE, method='quantize', dither=False, smooth=True):
    """
    RGB/RGBA 이미지를 팔레트 색상에 맞춰 변환합니다.
    
    Args:
        image: PIL.Image.Image 객체 (RGB, RGBA, 또는 P 모드)
        palette: 팔레트 데이터 (기본값: FACE_PALETTE)
        method: 변환 방법 ('nearest', 'quantize', 'dither')
            - 'nearest': 가장 가까운 색으로 직접 매핑 (빠르지만 거칠 수 있음)
            - 'quantize': PIL의 quantize() 사용 (기본값, 균형잡힌 결과)
            - 'dither': 디더링 적용 (부드럽지만 느릴 수 있음)
        dither: 디더링 적용 여부 (method='quantize'일 때만 사용)
        smooth: 변환 전 이미지 부드럽게 처리 여부 (기본값: True)
    
    Returns:
        PIL.Image.Image: 팔레트 모드 이미지 (P 모드)
    
    Raises:
        ValueError: 잘못된 method 값일 때
        IOError: 변환 실패 시
    """
    if image is None:
        raise ValueError("이미지가 None입니다.")
    
    try:
        # 이미지 복사
        img = image.copy()
        
        # 이미 팔레트 모드인 경우
        if img.mode == 'P':
            # 팔레트만 교체
            img.putpalette(palette)
            return img
        
        # RGB 모드로 확실히 변환 (이미 전처리된 이미지가 들어온다고 가정)
        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                # 알파 채널이 있는 경우 배경을 검은색으로 설정
                background = Image.new('RGB', img.size, (0, 0, 0))
                background.paste(img, mask=img.split()[3])  # 알파 채널을 마스크로 사용
                img = background
            else:
                # 다른 모드는 RGB로 변환
                img = img.convert('RGB')
        
        # 부드럽게 처리 (색상 일관성 향상, 잡티 제거)
        # 주의: 블러를 너무 강하게 하면 이미지가 어두워질 수 있음
        # if smooth:
        #     from PIL import ImageFilter
        #     # 약간의 가우시안 블러 적용 (부드럽게 하되 디테일 유지)
        #     img = img.filter(ImageFilter.GaussianBlur(radius=0.3))
        
        # 변환 방법에 따라 처리
        if method == 'nearest':
            # 가장 가까운 색으로 직접 매핑
            # numpy를 사용하여 빠르게 처리
            try:
                import numpy as np
                
                # 이미지를 numpy 배열로 변환
                img_array = np.array(img)
                height, width = img_array.shape[:2]
                
                # 팔레트 색상 배열 생성 (256 x 3)
                palette_array = np.array(list(palette)).reshape(256, 3)
                
                # 각 픽셀에 대해 가장 가까운 팔레트 색상 찾기
                # 유클리드 거리 계산 (가중치 적용: 인간 눈은 녹색에 더 민감)
                img_flat = img_array.reshape(-1, 3).astype(np.float32)
                palette_float = palette_array.astype(np.float32)
                
                # 가중치 적용 (R: 0.3, G: 0.59, B: 0.11 - 인간 눈의 민감도)
                weights = np.array([0.3, 0.59, 0.11])
                img_weighted = img_flat * weights
                palette_weighted = palette_float * weights
                
                # 가중 유클리드 거리 계산
                distances = np.sqrt(((img_weighted[:, np.newaxis, :] - palette_weighted[np.newaxis, :, :]) ** 2).sum(axis=2))
                nearest_indices = np.argmin(distances, axis=1)
                
                # 팔레트 모드 이미지 생성
                palette_indices = nearest_indices.reshape(height, width)
                img_palette = Image.fromarray(palette_indices.astype(np.uint8), mode='P')
                # 게임 팔레트 적용
                img_palette.putpalette(palette)
                
                return img_palette
            except ImportError:
                # numpy가 없으면 quantize 방식으로 폴백
                print("[얼굴이미지] numpy가 없어 quantize 방식으로 폴백합니다.")
                method = 'quantize'
        
        if method == 'quantize':
            # PIL의 quantize() 사용
            # save_face_image()와 정확히 동일한 방식 사용
            # 빈 팔레트로 먼저 양자화한 후 게임 팔레트 적용
            img_palette = img.quantize(palette=Image.new('P', (1, 1)), dither=Image.Dither.NONE)
            # 게임 팔레트 적용
            img_palette.putpalette(palette)
            
            return img_palette
        
        elif method == 'dither':
            # 디더링 적용 (Floyd-Steinberg) - 부드러운 전환
            # save_face_image() 방식에 디더링만 추가
            img_palette = img.quantize(palette=Image.new('P', (1, 1)), dither=Image.Dither.FLOYDSTEINBERG)
            # 게임 팔레트 적용
            img_palette.putpalette(palette)
            return img_palette
        
        else:
            raise ValueError(f"지원하지 않는 변환 방법입니다: {method} (지원: 'nearest', 'quantize', 'dither')")
    
    except Exception as e:
        raise IOError(f"팔레트 변환 실패: {e}")

def get_png_dir():
    """
    저장된 PNG 디렉토리 경로를 반환합니다.
    
    Returns:
        str: PNG 디렉토리 경로 (설정되지 않았으면 기본값 'gui/png' 반환)
    """
    if gl._png_dir and len(gl._png_dir) > 0:
        return gl._png_dir
    
    # 기본값 반환
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gui/png')

def set_png_dir(png_dir):
    """
    PNG 디렉토리 경로를 설정합니다.
    
    Args:
        png_dir: PNG 디렉토리 경로 (None이면 기본값으로 리셋)
    """
    if png_dir is None:
        gl._png_dir = ""
    else:
        # 절대 경로로 변환
        if not os.path.isabs(png_dir):
            png_dir = os.path.abspath(png_dir)
        gl._png_dir = png_dir

def _resize_with_aspect_ratio(image, target_size):
    """
    비율을 유지하면서 이미지를 목표 크기에 맞춥니다.
    여백은 검은색으로 채웁니다.
    
    Args:
        image: PIL.Image 객체
        target_size: (width, height) 튜플
    
    Returns:
        PIL.Image: 리사이즈된 이미지 (target_size 크기)
    """
    target_width, target_height = target_size
    original_width, original_height = image.size
    
    # 목표 비율과 원본 비율 계산
    target_ratio = target_width / target_height
    original_ratio = original_width / original_height
    
    # 비율에 맞춰 리사이즈할 크기 계산
    if original_ratio > target_ratio:
        # 원본이 더 넓음 -> 높이에 맞춤
        new_height = target_height
        new_width = int(original_width * (target_height / original_height))
    else:
        # 원본이 더 높음 -> 너비에 맞춤
        new_width = target_width
        new_height = int(original_height * (target_width / original_width))
    
    # 이미지 리사이즈
    resized = image.resize((new_width, new_height), Image.LANCZOS)
    
    # 96x120 크기의 검은색 배경 이미지 생성
    result = Image.new('RGB', (target_width, target_height), (0, 0, 0))
    
    # 중앙에 배치
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    
    # RGBA 모드면 알파 채널 처리
    if resized.mode == 'RGBA':
        result.paste(resized, (x_offset, y_offset), resized)
    else:
        result.paste(resized, (x_offset, y_offset))
    
    return result

def extract_face_region(image, crop_scale=2.0, center_offset_x=0, center_offset_y=0, manual_region=None, return_face_region=False):
    """
    이미지에서 얼굴 영역을 추출합니다. (OpenCV 사용)
    
    디버그: 함수 호출 추적
    
    Args:
        image: PIL.Image 객체
        crop_scale: 크롭 영역 크기 비율 (얼굴 크기의 배수, 기본값: 2.0)
        center_offset_x: 중심점 X 오프셋 (픽셀 단위, 기본값: 0)
        center_offset_y: 중심점 Y 오프셋 (픽셀 단위, 기본값: 0)
        manual_region: 수동 영역 지정 (x, y, width, height) 튜플 또는 None
        return_face_region: True일 경우 (이미지, 얼굴영역) 튜플 반환, False일 경우 이미지만 반환
    
    Returns:
        PIL.Image 또는 (PIL.Image, (x, y, w, h)): 얼굴 영역이 크롭된 이미지 (얼굴을 찾지 못하면 에러 발생)
        return_face_region=True일 경우 (이미지, 얼굴영역) 튜플 반환
    
    Note:
        OpenCV가 설치되지 않았으면 원본 이미지를 반환합니다.
        manual_region이 지정되면 자동 감지를 건너뛰고 지정된 영역을 사용합니다.
    """
    if not _cv2_available:
        print("[얼굴이미지] OpenCV가 없어 얼굴 인식을 건너뜁니다.")
        return image
    
    try:
        # PIL Image를 numpy 배열로 변환
        img_array = np.array(image)
        
        # RGBA를 RGB로 변환 (필요한 경우)
        if len(img_array.shape) == 3 and img_array.shape[2] == 4:
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        elif image.mode == 'RGB':
            img_rgb = img_array
        else:
            # 그레이스케일 등은 RGB로 변환
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        
        # 이미지 크기 (먼저 정의)
        img_height, img_width = img_rgb.shape[:2]
        
        # 디버그: 함수 호출 추적
        import traceback
        if manual_region is not None:
            print(f"[얼굴이미지] DEBUG: extract_face_region 호출됨 (수동 영역 모드)")
            print(f"[얼굴이미지] DEBUG: 호출 스택:")
            for line in traceback.format_stack()[-3:-1]:
                print(f"[얼굴이미지] DEBUG: {line.strip()}")
        else:
            print(f"[얼굴이미지] DEBUG: extract_face_region 호출됨 (자동 감지 모드)")
        
        # 수동 영역이 지정된 경우 자동 감지 건너뛰기
        if manual_region is not None:
            x, y, w, h = manual_region
            # 영역이 이미지 범위를 벗어나지 않도록 조정
            x = max(0, min(x, img_width - 1))
            y = max(0, min(y, img_height - 1))
            w = max(1, min(w, img_width - x))
            h = max(1, min(h, img_height - y))
            
            print(f"[얼굴이미지] 수동 영역 사용: 위치=({x}, {y}), 크기=({w}, {h})")
            
            # 수동 영역을 얼굴로 간주하고 크롭
            # X축은 얼굴 중심, Y축은 눈높이 추정
            face_center_x = x + w // 2
            # 수동 영역의 상단에서 얼굴 높이의 약 1/3 지점을 눈높이로 추정
            # (자동 감지 모드에서 눈을 찾지 못한 경우와 동일한 기준)
            estimated_eye_y = y + h // 3
            
            # 목표 비율 (96:120 = 0.8)
            target_ratio = FACE_WIDTH / FACE_HEIGHT  # 96/120 = 0.8
            
            # 얼굴 영역을 중심으로 96:120 비율로 크롭할 크기 계산
            if w / h > target_ratio:
                crop_height = int(h * crop_scale)
                crop_width = int(crop_height * target_ratio)
            else:
                crop_width = int(w * crop_scale)
                crop_height = int(crop_width / target_ratio)
            
            # 크롭 영역 좌표 계산
            # Y축은 눈높이 추정값 사용 (자동 감지와 동일한 기준)
            crop_center_x = face_center_x + center_offset_x
            crop_center_y = estimated_eye_y + center_offset_y
            x_start = crop_center_x - crop_width // 2
            y_start = crop_center_y - crop_height // 2
            
            # 경계 조정
            if crop_width > img_width:
                crop_width = img_width
                crop_height = int(crop_width / target_ratio)
            if crop_height > img_height:
                crop_height = img_height
                crop_width = int(crop_height * target_ratio)
            
            x_start = max(0, min(x_start, img_width - crop_width))
            y_start = max(0, min(y_start, img_height - crop_height))
            
            x_end = x_start + crop_width
            y_end = y_start + crop_height
            
            # 크롭
            face_region = img_rgb[y_start:y_end, x_start:x_end]
            face_image = Image.fromarray(face_region)
            
            print(f"[얼굴이미지] 크롭 영역: ({x_start}, {y_start}) ~ ({x_end}, {y_end})")
            
            # 얼굴 영역 좌표 반환 여부 확인
            if return_face_region:
                # 수동 영역을 사용할 때는 원본 manual_region을 반환 (테두리 표시용)
                # 실제 크롭 영역은 draw_actual_crop_region에서 계산됨
                return face_image, manual_region
            else:
                return face_image
        
        # 그레이스케일로 변환 (얼굴 인식용)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        
        # 감지된 얼굴 영역 저장용 변수
        detected_face_region = None
        
        # 얼굴 감지 (먼저 시도)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = []
        face_detected = False
        x, y, w, h = None, None, None, None
        eye_center_y = None
        face_center_x = None
        
        if not face_cascade.empty():
            # 얼굴 감지 (더 민감하게 설정)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,  # 5 -> 3으로 낮춰서 더 많이 감지
                minSize=(20, 20)  # 30 -> 20으로 낮춰서 작은 얼굴도 감지
            )
        
        # 눈 감지 분류기 로드
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        eyes_detected = False
        
        # 얼굴을 찾은 경우
        if len(faces) > 0:
            print(f"[얼굴이미지] {len(faces)}개의 얼굴 감지됨")
            
            # 가장 큰 얼굴 선택 (여러 얼굴이 있는 경우)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            detected_face_region = (x, y, w, h)  # 감지된 얼굴 영역 저장
            
            print(f"[얼굴이미지] 선택된 얼굴: 위치=({x}, {y}), 크기=({w}, {h})")
            
            # 얼굴 영역 내에서 눈 감지 (더 정확함)
            if not eye_cascade.empty():
                roi_gray = gray[y:y+h, x:x+w]
                eyes = eye_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(10, 10)
                )
                
                if len(eyes) >= 2:
                    # 두 눈의 중심점 계산
                    eye_centers = []
                    for (ex, ey, ew, eh) in eyes:
                        eye_center_x = x + ex + ew // 2
                        eye_center_y = y + ey + eh // 2
                        eye_centers.append((eye_center_x, eye_center_y))
                    
                    # 두 눈의 Y 좌표 중 더 작은 값
                    eye_centers_y = [ec[1] for ec in eye_centers]
                    eye_center_y = min(eye_centers_y)
                    
                    # 얼굴 중심 X 좌표
                    face_center_x = x + w // 2
                    
                    print(f"[얼굴이미지] {len(eyes)}개의 눈 감지됨")
                    for i, (ex, ey, ew, eh) in enumerate(eyes):
                        eye_abs_x = x + ex
                        eye_abs_y = y + ey
                        print(f"[얼굴이미지] 눈 {i+1}: 위치=({eye_abs_x}, {eye_abs_y}), 크기=({ew}, {eh})")
                    print(f"[얼굴이미지] 눈높이: {eye_center_y}, 얼굴 중심 X: {face_center_x}")
                    
                    # Y축은 눈높이, X축은 얼굴 중심 기준으로 중심점 설정
                    crop_center_x = face_center_x + center_offset_x
                    crop_center_y = eye_center_y + center_offset_y
                else:
                    # 눈을 찾지 못하면 얼굴 중심점 사용
                    print(f"[얼굴이미지] 눈을 찾을 수 없어 얼굴 중심점 사용 (감지된 눈: {len(eyes)}개)")
                    face_center_x = x + w // 2
                    face_center_y = y + h // 2
                    crop_center_x = face_center_x + center_offset_x
                    crop_center_y = face_center_y + center_offset_y
            else:
                # 눈 감지 분류기를 로드할 수 없으면 얼굴 중심점 사용
                print("[얼굴이미지] 눈 감지 분류기를 로드할 수 없어 얼굴 중심점 사용")
                face_center_x = x + w // 2
                face_center_y = y + h // 2
                crop_center_x = face_center_x + center_offset_x
                crop_center_y = face_center_y + center_offset_y
        
        # 얼굴을 못 찾은 경우 - 전체 이미지에서 눈 감지 시도 (fallback)
        elif not eye_cascade.empty():
            print("[얼굴이미지] 얼굴을 찾지 못해 전체 이미지에서 눈 감지 시도")
            eyes = eye_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(10, 10)
            )
            
            if len(eyes) >= 2:
                eyes_detected = True
                # 두 눈의 중심점 계산
                eye_centers = []
                for (ex, ey, ew, eh) in eyes:
                    eye_center_x = ex + ew // 2
                    eye_center_y = ey + eh // 2
                    eye_centers.append((eye_center_x, eye_center_y))
                
                # 두 눈의 Y 좌표 중 더 작은 값 (Y 좌표가 작을수록 위쪽)
                eye_centers_y = [ec[1] for ec in eye_centers]
                eye_center_y = min(eye_centers_y)
                
                # 두 눈의 X 좌표 평균 (얼굴 중심 X 추정)
                eye_centers_x = [ec[0] for ec in eye_centers]
                face_center_x = sum(eye_centers_x) // len(eye_centers_x)
                
                # 눈 간격을 기반으로 얼굴 크기 추정 (일반적으로 눈 간격의 2.5~3배가 얼굴 너비)
                eye_distance = abs(eye_centers[0][0] - eye_centers[1][0])
                estimated_face_width = int(eye_distance * 2.5)
                estimated_face_height = int(estimated_face_width * 1.25)  # 얼굴은 보통 세로가 더 김
                
                # 얼굴 영역 추정
                x = max(0, face_center_x - estimated_face_width // 2)
                y = max(0, eye_center_y - estimated_face_height // 3)  # 눈은 얼굴 상단 1/3 지점
                w = min(img_width - x, estimated_face_width)
                h = min(img_height - y, estimated_face_height)
                detected_face_region = (x, y, w, h)  # 감지된 얼굴 영역 저장
                
                print(f"[얼굴이미지] 전체 이미지에서 {len(eyes)}개의 눈 감지됨")
                for i, (ex, ey, ew, eh) in enumerate(eyes):
                    print(f"[얼굴이미지] 눈 {i+1}: 위치=({ex}, {ey}), 크기=({ew}, {eh})")
                print(f"[얼굴이미지] 눈높이: {eye_center_y}, 추정 얼굴 중심 X: {face_center_x}")
                print(f"[얼굴이미지] 추정 얼굴 영역: 위치=({x}, {y}), 크기=({w}, {h})")
                
                # Y축은 눈높이, X축은 얼굴 중심 기준으로 중심점 설정
                crop_center_x = face_center_x + center_offset_x
                crop_center_y = eye_center_y + center_offset_y
            else:
                # 얼굴도 눈도 못 찾은 경우
                print(f"[얼굴이미지] 얼굴과 눈을 모두 찾을 수 없습니다. 이미지 크기: {image.size}")
                raise ValueError("얼굴과 눈을 모두 찾을 수 없습니다. 얼굴 인식 체크박스를 해제하거나 다른 이미지를 사용하세요.")
        else:
            # 얼굴도 눈도 못 찾은 경우
            print(f"[얼굴이미지] 얼굴과 눈을 모두 찾을 수 없습니다. 이미지 크기: {image.size}")
            raise ValueError("얼굴과 눈을 모두 찾을 수 없습니다. 얼굴 인식 체크박스를 해제하거나 다른 이미지를 사용하세요.")
        
        # 목표 비율 (96:120 = 0.8)
        target_ratio = FACE_WIDTH / FACE_HEIGHT  # 96/120 = 0.8
        
        # 이미지 크기
        img_height, img_width = img_rgb.shape[:2]
        
        # 얼굴 영역을 중심으로 96:120 비율로 크롭할 크기 계산
        # 얼굴 크기(w, h)를 기준으로 더 큰 쪽을 사용하여 크롭 영역 결정
        # 얼굴이 더 넓으면 높이 기준, 더 높으면 너비 기준
        # 항상 96:120 비율을 유지
        if w / h > target_ratio:
            # 얼굴이 더 넓음 -> 높이를 기준으로 크롭
            crop_height = int(h * crop_scale)  # 사용자 지정 비율 사용
            crop_width = int(crop_height * target_ratio)  # 96:120 비율 유지
        else:
            # 얼굴이 더 높음 -> 너비를 기준으로 크롭
            crop_width = int(w * crop_scale)  # 사용자 지정 비율 사용
            crop_height = int(crop_width / target_ratio)  # 96:120 비율 유지
        
        # 96:120 비율 보장 (반올림 오차 보정)
        actual_ratio = crop_width / crop_height if crop_height > 0 else target_ratio
        if abs(actual_ratio - target_ratio) > 0.01:  # 1% 이상 차이나면 보정
            if w / h > target_ratio:
                crop_width = int(crop_height * target_ratio)
            else:
                crop_height = int(crop_width / target_ratio)
        
        # 크롭 영역 좌표 계산 (눈높이 또는 얼굴 중심 + 오프셋 기준)
        # crop_center_x, crop_center_y는 위에서 이미 계산됨
        x_start = crop_center_x - crop_width // 2
        y_start = crop_center_y - crop_height // 2
        
        # 경계를 벗어난 경우 조정 (크롭 영역을 이미지 내부로 이동)
        # 단, 96:120 비율은 절대 유지
        # 먼저 크롭 영역이 이미지 크기를 초과하는지 확인하고 조정
        if crop_width > img_width:
            crop_width = img_width
            crop_height = int(crop_width / target_ratio)  # 96:120 비율 유지
        if crop_height > img_height:
            crop_height = img_height
            crop_width = int(crop_height * target_ratio)  # 96:120 비율 유지
        
        # 크롭 영역 좌표 재계산 (눈높이 또는 얼굴 중심 + 오프셋 기준)
        # crop_center_x, crop_center_y는 위에서 이미 계산됨
        x_start = crop_center_x - crop_width // 2
        y_start = crop_center_y - crop_height // 2
        
        # 경계를 벗어난 경우 중심점을 조정 (96:120 비율은 유지)
        if x_start < 0:
            x_start = 0
        elif x_start + crop_width > img_width:
            x_start = img_width - crop_width
        
        if y_start < 0:
            y_start = 0
        elif y_start + crop_height > img_height:
            y_start = img_height - crop_height
        
        # 최종 크롭 영역
        x_end = x_start + crop_width
        y_end = y_start + crop_height
        
        # 최종 비율 확인 (96:120 비율 보장)
        if crop_height > 0:
            final_ratio = crop_width / crop_height
            if abs(final_ratio - target_ratio) > 0.001:  # 0.1% 이상 차이나면 경고
                print(f"[얼굴이미지] 경고: 크롭 비율이 목표 비율과 다릅니다. (실제: {final_ratio:.3f}, 목표: {target_ratio:.3f})")
        
        print(f"[얼굴이미지] 원본 이미지 크기: {img_width}x{img_height}")
        print(f"[얼굴이미지] 크롭 크기: {crop_width}x{crop_height} (비율: {crop_width/crop_height:.3f}, 목표: {target_ratio:.3f})")
        print(f"[얼굴이미지] 크롭 영역: ({x_start}, {y_start}) ~ ({x_end}, {y_end})")
        
        # 얼굴 영역 크롭
        face_region = img_rgb[y_start:y_end, x_start:x_end]
        
        if face_region.size == 0:
            raise ValueError(f"크롭된 영역이 비어있습니다. 크롭 영역: ({x_start}, {y_start}) ~ ({x_end}, {y_end})")
        
        # numpy 배열을 PIL Image로 변환
        face_image = Image.fromarray(face_region)
        
        print(f"[얼굴이미지] 얼굴 영역 추출 완료: {face_image.size} (원본: {image.size})")
        
        # 얼굴 영역 좌표 반환 여부 확인
        if return_face_region:
            return face_image, detected_face_region
        else:
            return face_image
        
    except ValueError as e:
        # 얼굴을 찾을 수 없는 경우는 에러를 다시 발생시킴
        print(f"[얼굴이미지] 얼굴 추출 실패: {e}")
        raise
    except Exception as e:
        print(f"[얼굴이미지] 얼굴 추출 실패: {e}")
        print(f"[얼굴이미지] 예외 타입: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"얼굴 추출 중 오류 발생: {e}")

def save_face_from_png(png_path, faceno, use_face_detection=False):
    """
    PNG 파일을 읽어서 Kaodata.s7 파일의 지정된 얼굴 번호 위치에 저장합니다.
    
    Args:
        png_path: PNG 파일 경로
        faceno: 저장할 얼굴 번호 (0~647)
        use_face_detection: 얼굴 인식을 사용할지 여부 (기본값: False)
                          True일 경우 얼굴 영역만 추출하여 저장합니다.
                          OpenCV가 없으면 자동으로 False로 동작합니다.
    
    Raises:
        FileNotFoundError: PNG 파일을 찾을 수 없을 때
        ValueError: faceno가 범위를 벗어날 때
        IOError: 파일 읽기/쓰기 실패 시
    
    Example:
        # face000.png 파일을 얼굴 번호 10에 저장 (기본 방식)
        save_face_from_png('gui/png/face000.png', 10)
        
        # 얼굴 인식 사용
        save_face_from_png('gui/png/face000.png', 10, use_face_detection=True)
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG 파일을 찾을 수 없습니다: {png_path}")
    
    if faceno < 0 or faceno >= 648:
        raise ValueError(f"얼굴 번호는 0~647 사이여야 합니다. (입력: {faceno})")
    
    try:
        # PNG 이미지 읽기
        img = Image.open(png_path)
        
        # 파일이 있는 디렉토리 경로 저장
        png_dir = os.path.dirname(os.path.abspath(png_path))
        set_png_dir(png_dir)
        
        # 얼굴 인식 사용 시 얼굴 영역 추출
        if use_face_detection:
            img = extract_face_region(img)
        
        # Kaodata.s7에 저장 (리사이즈 및 팔레트 적용은 save_face_image에서 처리)
        save_face_image(faceno, img)
        
    except Exception as e:
        raise IOError(f"PNG 파일 저장 실패 ({png_path} -> faceno: {faceno}): {e}")

def import_faces_from_png(png_dir=None, pattern='face*.png', verbose=True):
    """
    편집한 PNG 파일들을 Kaodata.s7 파일에 반영합니다.
    
    Args:
        png_dir: PNG 파일이 있는 디렉토리 경로 (None이면 저장된 경로 또는 기본값 'gui/png' 사용)
        pattern: 파일명 패턴 (기본값: 'face*.png')
        verbose: 진행 상황 출력 여부
    
    Returns:
        dict: {'success': 성공 개수, 'failed': 실패 개수, 'errors': 에러 리스트}
    
    Raises:
        FileNotFoundError: PNG 디렉토리를 찾을 수 없을 때
    """
    if png_dir is None:
        png_dir = get_png_dir()
    else:
        # 절대 경로로 변환하고 저장
        if not os.path.isabs(png_dir):
            png_dir = os.path.abspath(png_dir)
        set_png_dir(png_dir)
    
    if not os.path.exists(png_dir):
        raise FileNotFoundError(f"PNG 디렉토리를 찾을 수 없습니다: {png_dir}")
    
    # PNG 파일 목록 찾기
    pattern_path = os.path.join(png_dir, pattern)
    png_files = glob.glob(pattern_path)
    
    if not png_files:
        if verbose:
            print(f"[얼굴이미지] PNG 파일을 찾을 수 없습니다: {pattern_path}")
        return {'success': 0, 'failed': 0, 'errors': []}
    
    # 파일명에서 얼굴 번호 추출 (face000.png -> 0)
    face_pattern = re.compile(r'face(\d+)\.png', re.IGNORECASE)
    
    results = {'success': 0, 'failed': 0, 'errors': []}
    
    if verbose:
        print(f"[얼굴이미지] {len(png_files)}개의 PNG 파일 발견")
        print(f"[얼굴이미지] Kaodata.s7에 반영 시작...")
    
    for png_file in sorted(png_files):
        try:
            # 파일명에서 얼굴 번호 추출
            filename = os.path.basename(png_file)
            match = face_pattern.match(filename)
            
            if not match:
                error_msg = f"파일명 형식이 올바르지 않습니다: {filename}"
                results['errors'].append(error_msg)
                results['failed'] += 1
                if verbose:
                    print(f"  [실패] {filename}: {error_msg}")
                continue
            
            faceno = int(match.group(1))
            
            if faceno < 0 or faceno >= 648:
                error_msg = f"얼굴 번호가 범위를 벗어났습니다: {faceno}"
                results['errors'].append(f"{filename}: {error_msg}")
                results['failed'] += 1
                if verbose:
                    print(f"  [실패] {filename}: {error_msg}")
                continue
            
            # PNG 이미지 읽기
            img = Image.open(png_file)
            
            # Kaodata.s7에 저장
            save_face_image(faceno, img)
            
            results['success'] += 1
            if verbose:
                print(f"  [성공] {filename} -> 얼굴 번호 {faceno}")
                
        except Exception as e:
            error_msg = f"{os.path.basename(png_file)}: {str(e)}"
            results['errors'].append(error_msg)
            results['failed'] += 1
            if verbose:
                print(f"  [실패] {os.path.basename(png_file)}: {e}")
    
    if verbose:
        print(f"\n[얼굴이미지] 완료: 성공 {results['success']}개, 실패 {results['failed']}개")
        if results['errors']:
            print("\n에러 목록:")
            for error in results['errors']:
                print(f"  - {error}")
    
    return results

def close_kaodata_file():
    """Kaodata.s7 파일 핸들을 닫습니다."""
    global _kaodata_file, _kaodata_file_path
    if _kaodata_file is not None:
        _kaodata_file.close()
        _kaodata_file = None
        _kaodata_file_path = None

