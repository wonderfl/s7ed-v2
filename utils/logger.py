"""
통합 로깅 시스템
모든 모듈에서 사용할 수 있는 통합 로거 제공
기존 print(f"[모듈] ...") 형식과 호환되는 래퍼 함수 제공
색상 출력 지원 (colorama 사용, Windows 호환)
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# colorama 색상 지원 (선택적)
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # Windows에서 자동 초기화
    COLORAMA_AVAILABLE = True
except ImportError:
    # colorama가 없으면 색상 코드를 빈 문자열로 대체
    COLORAMA_AVAILABLE = False
    class Fore:
        BLACK = ''
        RED = ''
        GREEN = ''
        YELLOW = ''
        BLUE = ''
        MAGENTA = ''
        CYAN = ''
        WHITE = ''
        RESET = ''
    class Back:
        BLACK = ''
        RED = ''
        GREEN = ''
        YELLOW = ''
        BLUE = ''
        MAGENTA = ''
        CYAN = ''
        WHITE = ''
        RESET = ''
    class Style:
        DIM = ''
        NORMAL = ''
        BRIGHT = ''
        RESET_ALL = ''

# 로그 레벨 매핑
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 전역 로거 딕셔너리 (모듈별 로거 캐싱)
_loggers = {}

# 로깅 설정
_logging_config = {
    'level': 'INFO',
    'file_enabled': False,
    'file_path': 'logs/s7ed.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}


def _get_log_format():
    """로그 포맷 반환"""
    return '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'


def _get_date_format():
    """날짜 포맷 반환"""
    return '%Y-%m-%d %H:%M:%S'


def _ensure_log_directory(log_file_path):
    """로그 파일 디렉토리가 없으면 생성"""
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"[로거] 로그 디렉토리 생성 실패 ({log_dir}): {e}")


def configure_logging(level='INFO', file_enabled=False, file_path='logs/s7ed.log'):
    """로깅 설정
    
    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_enabled: 파일 로그 저장 여부
        file_path: 로그 파일 경로
    """
    global _logging_config
    _logging_config['level'] = level
    _logging_config['file_enabled'] = file_enabled
    _logging_config['file_path'] = file_path
    
    # 모든 기존 로거 재설정
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    for logger in _loggers.values():
        logger.setLevel(log_level)
        # 기존 핸들러 제거
        logger.handlers.clear()
        _setup_handlers(logger, file_enabled, file_path)


def _setup_handlers(logger, file_enabled, file_path):
    """로거에 핸들러 설정
    
    Args:
        logger: 설정할 로거
        file_enabled: 파일 로그 저장 여부
        file_path: 로그 파일 경로
    """
    log_level = LOG_LEVELS.get(_logging_config['level'].upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 포맷터 생성
    formatter = logging.Formatter(_get_log_format(), _get_date_format())
    
    # 콘솔 핸들러 (항상 추가)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (설정된 경우에만 추가)
    if file_enabled:
        try:
            _ensure_log_directory(file_path)
            # RotatingFileHandler 사용 (파일 크기 제한 및 로테이션)
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=_logging_config['max_bytes'],
                backupCount=_logging_config['backup_count'],
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"[로거] 파일 핸들러 설정 실패: {e}")


def get_logger(module_name: str) -> logging.Logger:
    """모듈별 로거 반환 (캐싱)
    
    Args:
        module_name: 모듈 이름 (예: '설정', '얼굴랜드마크', '얼굴추출' 등)
        
    Returns:
        logging.Logger: 설정된 로거
    """
    # 이미 생성된 로거가 있으면 반환
    if module_name in _loggers:
        return _loggers[module_name]
    
    # 새 로거 생성
    logger = logging.getLogger(module_name)
    log_level = LOG_LEVELS.get(_logging_config['level'].upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 핸들러 설정
    _setup_handlers(logger, _logging_config['file_enabled'], _logging_config['file_path'])
    
    # 캐싱
    _loggers[module_name] = logger
    
    return logger


def log_error(module_name: str, message: str, exception: Optional[Exception] = None):
    """에러 로깅 헬퍼 함수 (기존 print(f"[모듈] ...") 형식과 호환)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        exception: 예외 객체 (선택)
    """
    logger = get_logger(module_name)
    if exception:
        logger.error(f"{message}: {exception}", exc_info=True)
    else:
        logger.error(message)


def log_warning(module_name: str, message: str):
    """경고 로깅 헬퍼 함수
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    logger.warning(message)


def log_info(module_name: str, message: str):
    """정보 로깅 헬퍼 함수
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    logger.info(message)


def log_debug(module_name: str, message: str):
    """디버그 로깅 헬퍼 함수
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    logger.debug(message)


# 기존 print(f"[모듈] ...") 형식과 호환되는 함수
def print_log(module_name: str, message: str, level: str = 'INFO'):
    """기존 print(f"[모듈] ...") 형식과 호환되는 로깅 함수
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        level: 로그 레벨 (기본: INFO)
    """
    logger = get_logger(module_name)
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.log(log_level, message)


# ========== 색상 출력 함수 ==========

def _get_color_for_level(level: str) -> str:
    """로그 레벨에 따른 색상 코드 반환
    
    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        색상 코드 문자열
    """
    if not COLORAMA_AVAILABLE:
        return ''
    
    level_upper = level.upper()
    color_map = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    return color_map.get(level_upper, '')


def print_colored(module_name: str, message: str, level: str = 'INFO', use_color: bool = True):
    """색상이 적용된 print 함수 (기존 print(f"[모듈] ...") 형식과 호환)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_color: 색상 사용 여부 (기본: True)
        
    Examples:
        print_colored("얼굴편집", "드래그 시작: 랜드마크 인덱스 285", "INFO")
        print_colored("얼굴모핑", "에러 발생", "ERROR")
    """
    color = _get_color_for_level(level) if use_color and COLORAMA_AVAILABLE else ''
    reset = Fore.RESET if use_color and COLORAMA_AVAILABLE else ''
    
    # 기존 형식: [모듈] 메시지
    formatted_message = f"{color}[{module_name}] {message}{reset}"
    
    # 로거에도 기록 (색상 없이)
    logger = get_logger(module_name)
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.log(log_level, message)
    
    # 콘솔에 색상 출력
    print(formatted_message, file=sys.stdout if level.upper() != 'ERROR' else sys.stderr)


def print_error(module_name: str, message: str, exception: Optional[Exception] = None):
    """에러 출력 (빨간색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        exception: 예외 객체 (선택)
    """
    if exception:
        full_message = f"{message}: {exception}"
        print_colored(module_name, full_message, 'ERROR')
        log_error(module_name, message, exception)
    else:
        print_colored(module_name, message, 'ERROR')
        log_error(module_name, message)


def print_warning(module_name: str, message: str):
    """경고 출력 (노란색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    print_colored(module_name, message, 'WARNING')
    log_warning(module_name, message)


def print_info(module_name: str, message: str):
    """정보 출력 (초록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    print_colored(module_name, message, 'INFO')
    log_info(module_name, message)


def print_debug(module_name: str, message: str):
    """디버그 출력 (청록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    print_colored(module_name, message, 'DEBUG')
    log_debug(module_name, message)
