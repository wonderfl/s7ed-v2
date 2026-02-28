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
SETTINGS_FILE = 'settings.json'
LOGGINGS_FILE = 'loggings.json'

DEBUG_SETTINGS = False

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

def load_settings(panel):
    """설정 파일을 불러옵니다."""

    if DEBUG_SETTINGS:
        print("load_settings", f"face_edit_dir: {panel.face_edit_dir}")    
   
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        if DEBUG_SETTINGS:
            print("load_settings", f"settings:{settings}")
            
        # 기본 설정값 적용
        if 'face_edit_dir' in settings:
            panel.face_edit_dir = settings['face_edit_dir']
        if 'face_file' in settings:
            panel._face_file = settings['face_file']                    
        if 'loading_file' in settings:
            panel._loading_file = settings['loading_file']
        if 'save_file_dir' in settings:
            panel._save_file_dir = settings['save_file_dir']

        if DEBUG_SETTINGS:
            print("load_settings", f"load: face_edit_dir: {panel.face_edit_dir}")
        
        # 새로운 설정 항목 (기존 호환성 유지)
        if 'window' in settings:
            if not hasattr(panel, '_window_config'):
                panel._window_config = {}
            panel._window_config.update(config['window'])
        
        if 'recent_files' in settings:
            if not hasattr(panel, '_recent_files'):
                panel._recent_files = []
            # 최대 10개로 제한
            panel._recent_files = config['recent_files'][:10]


            
    except Exception as e:
        _get_logger().error(f"설정 파일 로드 실패: {e}")

def save_settings(panel):
    """설정 파일에 저장합니다."""    
    try:
        if DEBUG_SETTINGS:
            print("save_settings", f"face_edit_dir: {panel.face_edit_dir}")

        # 기존 설정 로드 (다른 설정 유지)
        settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except Exception as e:
                _get_logger().warning(f"설정 파일 로드 실패 (손상된 파일 무시): {e}")

        if DEBUG_SETTINGS:
            print("save_settings", f"settings: {settings}")

        # 기본 설정값 저장
        if hasattr(panel, 'face_edit_dir'):
            settings['face_edit_dir'] = panel.face_edit_dir        
        if hasattr(panel, '_face_file'):
            settings['face_file'] = panel._face_file
        if hasattr(panel, '_loading_file'):
            settings['loading_file'] = panel._loading_file            
        if hasattr(panel, '_save_file_dir'):
            settings['save_file_dir'] = panel._save_file_dir
        
        # 새로운 설정 항목 저장
        if hasattr(panel, '_window_config') and panel._window_config:
            settings['window'] = panel._window_config
        
        if hasattr(panel, '_recent_files') and panel._recent_files:
            # 최대 10개로 제한
            settings['recent_files'] = panel._recent_files[:10]
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        print(f"설정 파일 저장: {settings}")
            
    except Exception as e:
        _get_logger().error(f"설정 파일 저장 실패: {e}")


def add_recent_file(panel, file_path):
    """최근 파일 목록에 추가합니다.
    
    Args:
        file_path: 파일 경로
    """
    if not hasattr(self, '_recent_files'):
        panel._recent_files = []
    
    # 이미 있으면 제거
    if file_path in panel._recent_files:
        panel._recent_files.remove(file_path)
    
    # 맨 앞에 추가
    panel._recent_files.insert(0, file_path)
    
    # 최대 10개로 제한
    panel._recent_files = panel._recent_files[:10]
    
    # 자동 저장
    save_settings(panel)


def get_recent_files():
    """최근 파일 목록을 반환합니다.
    
    Returns:
        list: 최근 파일 경로 리스트
    """
   
    if not hasattr(self, '_recent_files'):
        self._recent_files = []
    
    return self._recent_files.copy()


def save_window_config(x, y, width, height):
    """윈도우 위치 및 크기를 저장합니다.
    
    Args:
        x: 윈도우 X 위치
        y: 윈도우 Y 위치
        width: 윈도우 너비
        height: 윈도우 높이
    """
    if not hasattr(self, '_window_config'):
        self._window_config = {}
    
    self._window_config['x'] = x
    self._window_config['y'] = y
    self._window_config['width'] = width
    self._window_config['height'] = height
    
    # 자동 저장
    save_config()


def load_window_config():
    """윈도우 위치 및 크기를 불러옵니다.
    
    Returns:
        dict: 윈도우 설정 딕셔너리 (x, y, width, height) 또는 None
    """
    if hasattr(self, '_window_config') and self._window_config:
        return self._window_config.copy()
    
    return None


def load_logging_config():
    """로깅 설정을 불러와서 로거에 적용합니다.
    logging.json 파일이 있고 log_level이 설정되어 있으면 파일 로그를 활성화합니다.
    log_level이 없거나 null이면 파일 로그를 비활성화합니다.
    config.json의 logging 섹션은 하위 호환성을 위해 지원합니다.
    """
    logging_config = None
    
    # 1. 별도 로그 설정 파일 확인
    if os.path.exists(LOGGING_CONFIG_FILE):
        try:
            with open(LOGGING_CONFIG_FILE, 'r', encoding='utf-8') as f:
                logging_config = json.load(f)
        except Exception as e:
            # 로거 초기화 전이므로 print 사용
            print(f"[설정] 로그 설정 파일 로드 실패 ({LOGGING_CONFIG_FILE}): {e}")
            # JSON 파싱 실패 시 기본값 사용 (파일 로그 비활성화)
            logging_config = None
    
    # 2. config.json의 logging 섹션 확인 (하위 호환성)
    if logging_config is None and os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'logging' in config:
                logging_config = config['logging']
        except Exception as e:
            # 로거 초기화 전이므로 print 사용
            print(f"[설정] 설정 파일 로드 실패 ({SETTINGS_FILE}): {e}")
            return
    
    # 3. 설정이 없으면 기본값 사용 (파일 로그 비활성화)
    if logging_config is None:
        # 기본 설정만 적용 (파일 로그 비활성화)
        from utils.logger import configure_logging
        configure_logging(
            level='INFO',
            file_enabled=False,
            file_path='logs/s7ed.log',
            output_level='INFO'
        )
        return
    
    try:
        # 하위 호환성: level이 있으면 사용, 없으면 output_level 사용
        level = logging_config.get('level', None)
        output_level = logging_config.get('output_level', None)
        if output_level is None:
            output_level = level if level is not None else 'INFO'
        
        file_path = logging_config.get('file_path', 'logs/s7ed.log')
        # 하위 호환성: file_level이 있으면 사용, 없으면 log_level 사용
        log_level = logging_config.get('log_level', None)  # 키가 없으면 None 반환
        if log_level is None:
            log_level = logging_config.get('file_level', None)  # 하위 호환성
        
        # log_level이 정의되지 않았거나(null), null, 빈 문자열, 공백만 있으면 파일 로그 비활성화
        # log_level이 유효한 값이면 파일 로그 활성화
        if log_level is None:
            # 정의되지 않음, null, 또는 키가 없는 경우
            file_enabled = False
        elif isinstance(log_level, str):
            log_level_stripped = log_level.strip().upper()
            # 빈 문자열, 공백만 있거나, "None" (대소문자 구분 없음)이면 비활성화
            if log_level_stripped == '' or log_level_stripped == 'NONE':
                file_enabled = False
            else:
                # 유효한 로그 레벨인지 확인 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
                file_enabled = log_level_stripped in valid_levels
        else:
            # 그 외의 경우는 비활성화 (예상치 못한 타입)
            file_enabled = False
        log_format = logging_config.get('log_format', None)  # None이면 기본값 사용
        date_format = logging_config.get('date_format', None)  # None이면 기본값 사용
        # 빈 문자열, "none" (대소문자 구분 없음)이면 None으로 변환
        if date_format is not None and isinstance(date_format, str):
            date_format_stripped = date_format.strip().upper()
            if date_format_stripped == '' or date_format_stripped == 'NONE':
                date_format = None
        colors = logging_config.get('colors', None)  # None이면 기본값 사용
        rotation_type = logging_config.get('rotation_type', None)  # None이면 기본값 사용
        max_bytes = logging_config.get('max_bytes', None)  # None이면 기본값 사용
        backup_count = logging_config.get('backup_count', None)  # None이면 기본값 사용
        rotation_when = logging_config.get('rotation_when', None)  # None이면 기본값 사용
        rotation_interval = logging_config.get('rotation_interval', None)  # None이면 기본값 사용
        filename_date = logging_config.get('filename_date', None)  # None이면 기본값 사용
        filename_prefix = logging_config.get('filename_prefix', None)  # None이면 기본값 사용
        
        from utils.logger import configure_logging
        configure_logging(
            level=level if level is not None else output_level,  # 하위 호환성
            file_enabled=file_enabled,  # logging.json 파일 존재 여부로 결정됨
            file_path=file_path,
            log_level=log_level,
            output_level=output_level,
            log_format=log_format,
            date_format=date_format,
            colors=colors,
            rotation_type=rotation_type,
            max_bytes=max_bytes,
            backup_count=backup_count,
            rotation_when=rotation_when,
            rotation_interval=rotation_interval,
            filename_date=filename_date,
            filename_prefix=filename_prefix
        )
    except Exception as e:
        # 로거 초기화 전이므로 print 사용
        print(f"[설정] 로깅 설정 적용 실패: {e}")


def save_logging_config(level='INFO', file_path='logs/s7ed.log',
                        log_level=None, output_level=None, log_format=None, date_format=None,
                        colors=None, rotation_type=None, max_bytes=None, backup_count=None,
                        rotation_when=None, rotation_interval=None, filename_date=None,
                        filename_prefix=None):
    """로깅 설정을 별도 파일(logging.json)에 저장합니다.
    logging.json 파일이 생성되면 자동으로 파일 로그가 활성화됩니다.
    
    Args:
        level: 로그 레벨 (하위 호환성용)
        file_path: 로그 파일 경로
        log_level: 파일 로그 레벨 (None이면 output_level과 동일)
        output_level: 출력 레벨 (None이면 level 사용)
        log_format: 로그 포맷 문자열 (None이면 기본값 사용)
        date_format: 날짜 포맷 문자열 (None이면 기본값 사용)
        colors: 레벨별 색상 설정 딕셔너리 (None이면 기본값 사용)
        rotation_type: 로테이션 타입 ('size' 또는 'date', None이면 기본값 사용)
        max_bytes: 최대 파일 크기 (rotation_type='size'일 때 사용, None이면 기본값 사용)
        backup_count: 백업 파일 개수 (None이면 기본값 사용)
        rotation_when: 날짜별 로테이션 시점 (None이면 기본값 사용)
        rotation_interval: 로테이션 간격 (None이면 기본값 사용)
        filename_date: 날짜별 파일명 패턴 (예: '%Y-%m-%d', None이면 기본값 사용)
        filename_prefix: 파일명 접두사 (예: 'app_', None이면 기본값 사용)
    """
    try:
        # 기존 설정 로드 (있는 경우)
        logging_config = {}
        if os.path.exists(LOGGING_CONFIG_FILE):
            try:
                with open(LOGGING_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    logging_config = json.load(f)
            except Exception as e:
                _get_logger().warning(f"기존 로그 설정 파일 로드 실패 (새로 생성): {e}")
        
        # output_level이 지정되지 않으면 level 사용
        if output_level is None:
            output_level = level
        
        # 로깅 설정 업데이트
        logging_config['level'] = level  # 하위 호환성 유지
        logging_config['output_level'] = output_level
        # file_enabled는 제거: logging.json 파일이 존재하면 자동으로 파일 로그 활성화
        logging_config['file_path'] = file_path
        
        # log_level이 지정되면 추가
        if log_level is not None:
            logging_config['log_level'] = log_level
        
        # log_format이 지정되면 추가
        if log_format is not None:
            logging_config['log_format'] = log_format
        
        # date_format이 지정되면 추가
        if date_format is not None:
            logging_config['date_format'] = date_format
        
        # colors가 지정되면 추가
        if colors is not None:
            logging_config['colors'] = colors
        
        # rotation_type이 지정되면 추가
        if rotation_type is not None:
            logging_config['rotation_type'] = rotation_type
        
        # max_bytes가 지정되면 추가
        if max_bytes is not None:
            logging_config['max_bytes'] = max_bytes
        
        # backup_count가 지정되면 추가
        if backup_count is not None:
            logging_config['backup_count'] = backup_count
        
        # rotation_when이 지정되면 추가
        if rotation_when is not None:
            logging_config['rotation_when'] = rotation_when
        
        # rotation_interval이 지정되면 추가
        if rotation_interval is not None:
            logging_config['rotation_interval'] = rotation_interval
        
        # filename_date가 지정되면 추가
        if filename_date is not None:
            logging_config['filename_date'] = filename_date
        
        # filename_prefix가 지정되면 추가
        if filename_prefix is not None:
            logging_config['filename_prefix'] = filename_prefix
        
        # 별도 파일에 저장
        with open(LOGGING_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logging_config, f, ensure_ascii=False, indent=2)

    except Exception as e:
        _get_logger().error(f"로깅 설정 저장 실패: {e}")

