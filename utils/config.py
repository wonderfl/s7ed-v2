"""
설정 파일 저장/로드 유틸리티
"""
import os
import json

# 로거 import (순환 참조 방지를 위해 함수 내부에서 import)
_logger = None

def _get_logger():
    """로거 가져오기 (지연 로딩)"""
    global _logger
    if _logger is None:
        from utils.logger import get_logger
        _logger = get_logger('설정')
    return _logger

# 설정 파일 경로
CONFIG_FILE = 'config.json'


def _get_parameters_dir(image_path):
    """이미지 파일이 있는 디렉토리의 parameters 폴더 경로 반환"""
    image_dir = os.path.dirname(image_path)
    parameters_dir = os.path.join(image_dir, 'parameters')
    # parameters 폴더가 없으면 생성
    if not os.path.exists(parameters_dir):
        try:
            os.makedirs(parameters_dir, exist_ok=True)
        except Exception as e:
            _get_logger().error(f"parameters 폴더 생성 실패: {e}")
    return parameters_dir


def _get_parameters_filename(image_path):
    """이미지 파일명을 기반으로 파라미터 파일명 생성"""
    # 이미지 파일명 (확장자 포함)
    image_filename = os.path.basename(image_path)
    # 파라미터 파일명: {이미지파일명}.s7ed.json
    params_filename = f"{image_filename}.s7ed.json"
    return params_filename

def load_config():
    """설정 파일을 불러옵니다."""
    import globals as gl
    
    if not os.path.exists(CONFIG_FILE):
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 기본 설정값 적용
        if 'loading_file' in config:
            gl._loading_file = config['loading_file']
        if 'face_file' in config:
            gl._face_file = config['face_file']
        if 'png_dir' in config:
            gl._png_dir = config['png_dir']
        if 'save_file_dir' in config:
            gl._save_file_dir = config['save_file_dir']
        if 'face_extract_dir' in config:
            gl._face_extract_dir = config['face_extract_dir']
        
        # 새로운 설정 항목 (기존 호환성 유지)
        if 'window' in config:
            if not hasattr(gl, '_window_config'):
                gl._window_config = {}
            gl._window_config.update(config['window'])
        
        if 'recent_files' in config:
            if not hasattr(gl, '_recent_files'):
                gl._recent_files = []
            # 최대 10개로 제한
            gl._recent_files = config['recent_files'][:10]
            
    except Exception as e:
        _get_logger().error(f"설정 파일 로드 실패: {e}")

def save_config():
    """설정 파일에 저장합니다."""
    import globals as gl
    
    try:
        # 기존 설정 로드 (다른 설정 유지)
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                _get_logger().warning(f"설정 파일 로드 실패 (손상된 파일 무시): {e}")
        
        # 기본 설정값 저장
        if hasattr(gl, '_loading_file'):
            config['loading_file'] = gl._loading_file
        if hasattr(gl, '_face_file'):
            config['face_file'] = gl._face_file
        if hasattr(gl, '_png_dir'):
            config['png_dir'] = gl._png_dir
        if hasattr(gl, '_save_file_dir'):
            config['save_file_dir'] = gl._save_file_dir
        if hasattr(gl, '_face_extract_dir'):
            config['face_extract_dir'] = gl._face_extract_dir
        
        # 새로운 설정 항목 저장
        if hasattr(gl, '_window_config') and gl._window_config:
            config['window'] = gl._window_config
        
        if hasattr(gl, '_recent_files') and gl._recent_files:
            # 최대 10개로 제한
            config['recent_files'] = gl._recent_files[:10]
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        _get_logger().error(f"설정 파일 저장 실패: {e}")


def add_recent_file(file_path):
    """최근 파일 목록에 추가합니다.
    
    Args:
        file_path: 파일 경로
    """
    import globals as gl
    
    if not hasattr(gl, '_recent_files'):
        gl._recent_files = []
    
    # 이미 있으면 제거
    if file_path in gl._recent_files:
        gl._recent_files.remove(file_path)
    
    # 맨 앞에 추가
    gl._recent_files.insert(0, file_path)
    
    # 최대 10개로 제한
    gl._recent_files = gl._recent_files[:10]
    
    # 자동 저장
    save_config()


def get_recent_files():
    """최근 파일 목록을 반환합니다.
    
    Returns:
        list: 최근 파일 경로 리스트
    """
    import globals as gl
    
    if not hasattr(gl, '_recent_files'):
        gl._recent_files = []
    
    return gl._recent_files.copy()


def save_window_config(x, y, width, height):
    """윈도우 위치 및 크기를 저장합니다.
    
    Args:
        x: 윈도우 X 위치
        y: 윈도우 Y 위치
        width: 윈도우 너비
        height: 윈도우 높이
    """
    import globals as gl
    
    if not hasattr(gl, '_window_config'):
        gl._window_config = {}
    
    gl._window_config['x'] = x
    gl._window_config['y'] = y
    gl._window_config['width'] = width
    gl._window_config['height'] = height
    
    # 자동 저장
    save_config()


def load_window_config():
    """윈도우 위치 및 크기를 불러옵니다.
    
    Returns:
        dict: 윈도우 설정 딕셔너리 (x, y, width, height) 또는 None
    """
    import globals as gl
    
    if hasattr(gl, '_window_config') and gl._window_config:
        return gl._window_config.copy()
    
    return None

def load_face_extract_params(image_path):
    """이미지별 팔레트 추출 파라미터를 불러옵니다.
    
    Args:
        image_path: 원본 이미지 파일 경로
        
    Returns:
        dict: 파라미터 딕셔너리, 파일이 없거나 오류 시 None
    """
    if not image_path:
        return None
    
    # 설정 파일 경로 생성: parameters 폴더 내
    parameters_dir = _get_parameters_dir(image_path)
    params_filename = _get_parameters_filename(image_path)
    config_path = os.path.join(parameters_dir, params_filename)
    
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
        return params
    except Exception as e:
        _get_logger().error(f"이미지별 설정 파일 로드 실패 ({config_path}): {e}")
        return None

def save_face_extract_params(image_path, params):
    """이미지별 팔레트 추출 파라미터를 저장합니다.
    
    Args:
        image_path: 원본 이미지 파일 경로
        params: 파라미터 딕셔너리
    """
    if not image_path:
        return
    
    # 설정 파일 경로 생성: parameters 폴더 내
    parameters_dir = _get_parameters_dir(image_path)
    params_filename = _get_parameters_filename(image_path)
    config_path = os.path.join(parameters_dir, params_filename)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _get_logger().error(f"이미지별 설정 파일 저장 실패 ({config_path}): {e}")


def load_logging_config():
    """로깅 설정을 불러와서 로거에 적용합니다."""
    if not os.path.exists(CONFIG_FILE):
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 로깅 설정이 있으면 적용
        if 'logging' in config:
            logging_config = config['logging']
            level = logging_config.get('level', 'INFO')
            file_enabled = logging_config.get('file_enabled', False)
            file_path = logging_config.get('file_path', 'logs/s7ed.log')
            
            from utils.logger import configure_logging
            configure_logging(level=level, file_enabled=file_enabled, file_path=file_path)
    except Exception as e:
        _get_logger().error(f"로깅 설정 로드 실패: {e}")


def save_logging_config(level='INFO', file_enabled=False, file_path='logs/s7ed.log'):
    """로깅 설정을 저장합니다.
    
    Args:
        level: 로그 레벨
        file_enabled: 파일 로그 저장 여부
        file_path: 로그 파일 경로
    """
    import globals as gl
    
    try:
        # 기존 설정 로드
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 로깅 설정 추가/업데이트
        config['logging'] = {
            'level': level,
            'file_enabled': file_enabled,
            'file_path': file_path
        }
        
        # 기존 설정도 함께 저장
        if hasattr(gl, '_loading_file'):
            config['loading_file'] = gl._loading_file
        if hasattr(gl, '_face_file'):
            config['face_file'] = gl._face_file
        if hasattr(gl, '_png_dir'):
            config['png_dir'] = gl._png_dir
        if hasattr(gl, '_save_file_dir'):
            config['save_file_dir'] = gl._save_file_dir
        if hasattr(gl, '_face_extract_dir'):
            config['face_extract_dir'] = gl._face_extract_dir
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _get_logger().error(f"로깅 설정 저장 실패: {e}")

