"""
Kaodata.s7 파일에서 얼굴 이미지를 읽어오는 유틸리티
"""
import os
import re
import glob
from PIL import Image

# 얼굴 이미지 상수
FACE_WIDTH = 96
FACE_HEIGHT = 120
FACE_SIZE = FACE_WIDTH * FACE_HEIGHT  # 11520 bytes (팔레트 모드)

# Kaodata.s7 파일 경로
KAODATA_PATH = 'saves/Kaodata.s7'

# 헤더 크기 (추정)
HEADER_SIZE = 10372

# 전역 변수: 파일 핸들 캐싱
_kaodata_file = None
_kaodata_file_path = None

# 전역 변수: 팔레트 캐싱
_face_palette = None

# 전역 변수: PNG 디렉토리 경로 (마지막 사용 경로 기억)
_png_dir = None

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
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), KAODATA_PATH)
    
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
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), KAODATA_PATH)
    
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

def get_png_dir():
    """
    저장된 PNG 디렉토리 경로를 반환합니다.
    
    Returns:
        str: PNG 디렉토리 경로 (설정되지 않았으면 기본값 'gui/png' 반환)
    """
    global _png_dir
    
    if _png_dir is not None:
        return _png_dir
    
    # 기본값 반환
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gui/png')

def set_png_dir(png_dir):
    """
    PNG 디렉토리 경로를 설정합니다.
    
    Args:
        png_dir: PNG 디렉토리 경로 (None이면 기본값으로 리셋)
    """
    global _png_dir
    
    if png_dir is None:
        _png_dir = None
    else:
        # 절대 경로로 변환
        if not os.path.isabs(png_dir):
            png_dir = os.path.abspath(png_dir)
        _png_dir = png_dir

def save_face_from_png(png_path, faceno):
    """
    PNG 파일을 읽어서 Kaodata.s7 파일의 지정된 얼굴 번호 위치에 저장합니다.
    
    Args:
        png_path: PNG 파일 경로
        faceno: 저장할 얼굴 번호 (0~647)
    
    Raises:
        FileNotFoundError: PNG 파일을 찾을 수 없을 때
        ValueError: faceno가 범위를 벗어날 때
        IOError: 파일 읽기/쓰기 실패 시
    
    Example:
        # face000.png 파일을 얼굴 번호 10에 저장
        save_face_from_png('gui/png/face000.png', 10)
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
        
        # Kaodata.s7에 저장
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

