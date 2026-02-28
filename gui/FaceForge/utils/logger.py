"""
통합 로깅 시스템
모든 모듈에서 사용할 수 있는 통합 로거 제공
기존 print(f"[모듈] ...") 형식과 호환되는 래퍼 함수 제공
색상 출력 지원 (colorama 사용, Windows 호환)
"""
import logging
import os
import datetime
import sys
from pathlib import Path
from typing import Optional

# colorama 색상 지원 (선택적)
try:
    from colorama import init, Fore, Back, Style
    # Windows에서 밝은 색상이 제대로 표시되도록 convert=True 사용
    init(autoreset=True, convert=True, strip=False)  # Windows에서 자동 초기화 및 ANSI 변환
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

# 로깅 설정이 초기화되었는지 여부
_logging_initialized = False

# 로깅 설정
_logging_config = {
    'level': 'INFO',  # 출력 레벨 (하위 호환성을 위해 유지)
    'output_level': 'INFO',  # 출력 레벨
    'file_enabled': False,
    'file_path': 'logs/s7ed.log',
    'log_level': 'INFO',  # 파일 로그 레벨 (기본값: output_level과 동일)
    'log_format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'colors': {  # 레벨별 색상 설정
        'DEBUG': 'CYAN',
        'INFO': 'GREEN+BRIGHT',
        'WARNING': 'YELLOW',
        'ERROR': 'RED+BRIGHT',
        'CRITICAL': 'MAGENTA+BRIGHT'
    },
    'rotation_type': 'size',  # 'size' 또는 'date' (기본값: size)
    'max_bytes': 10 * 1024 * 1024,  # 10MB (rotation_type='size'일 때 사용)
    'backup_count': 5,  # 백업 파일 개수 (rotation_type='size'일 때 사용)
    'rotation_when': 'midnight',  # 날짜별 로테이션 시점 ('S', 'M', 'H', 'D', 'W0'-'W6', 'midnight')
    'rotation_interval': 1,  # 로테이션 간격 (rotation_type='date'일 때 사용)
    'filename_date': None,  # 날짜별 파일명 패턴 (예: '%Y-%m-%d', None이면 TimedRotatingFileHandler 기본 형식 사용)
    'filename_prefix': None  # 파일명 접두사 (예: 'app_', None이면 기본 파일명 사용)
}


def _get_log_format():
    """로그 포맷 반환"""
    return _logging_config.get('log_format', '%(asctime)s [%(levelname)s] [%(name)s] %(message)s')


def _get_date_format():
    """날짜 포맷 반환"""
    date_format = _logging_config.get('date_format', '%Y-%m-%d %H:%M:%S')
    # None, 빈 문자열, "none" (대소문자 구분 없음)이면 None 반환 (날짜 출력 안함)
    if date_format is None:
        return None
    if isinstance(date_format, str):
        date_format_stripped = date_format.strip().upper()
        if date_format_stripped == '' or date_format_stripped == 'NONE':
            return None
    return date_format


class MillisecondFormatter(logging.Formatter):
    """밀리초를 지원하는 커스텀 포맷터"""
    def formatTime(self, record, datefmt=None):
        """밀리초를 포함한 시간 포맷"""
        import datetime
        import re
        ct = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            # %f, %3f, %.3f 같은 형식을 밀리초로 변환
            # %3f 또는 %.3f -> 3자리 밀리초, %f -> 기본 3자리 밀리초
            pattern = r'%\.?(\d*)f'
            
            # 모든 매치를 찾아서 변환
            microseconds = ct.microsecond
            milliseconds = microseconds // 1000
            
            def replace_milliseconds(match):
                width_str = match.group(1)
                if width_str:
                    width = int(width_str)
                    # 지정된 자리수로 포맷 (최대 3자리)
                    width = min(width, 3)
                    return f'{milliseconds:0{width}d}'
                else:
                    # 기본 3자리
                    return f'{milliseconds:03d}'
            
            # %f 또는 %3f 형식을 밀리초로 변환
            datefmt = re.sub(pattern, replace_milliseconds, datefmt)
            
            # 나머지 strftime 형식 처리
            return ct.strftime(datefmt)
        else:
            t = ct.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
            return s


def _ensure_log_directory(log_file_path):
    """로그 파일 디렉토리가 없으면 생성"""
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"[로거] 로그 디렉토리 생성 실패 ({log_dir}): {e}")


def configure_logging(level='INFO', file_enabled=False, file_path='logs/s7ed.log', 
                     log_level=None, output_level=None, log_format=None, date_format='__NOT_SET__',
                     colors=None, rotation_type=None, max_bytes=None, backup_count=None,
                     rotation_when=None, rotation_interval=None, filename_date=None,
                     filename_prefix=None):
    """로깅 설정
    
    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL) - 하위 호환성용
        file_enabled: 파일 로그 저장 여부
        file_path: 로그 파일 경로
        log_level: 파일 로그 레벨 (None이면 output_level과 동일)
        output_level: 출력 레벨 (None이면 level 사용)
        log_format: 로그 포맷 문자열 (None이면 기본값 사용)
        date_format: 날짜 포맷 문자열 (None이면 기본값 사용)
        colors: 레벨별 색상 설정 딕셔너리 (None이면 기본값 사용)
        rotation_type: 로테이션 타입 ('size' 또는 'date', None이면 기본값 사용)
        max_bytes: 최대 파일 크기 (rotation_type='size'일 때 사용, None이면 기본값 사용)
        backup_count: 백업 파일 개수 (rotation_type='size'일 때 사용, None이면 기본값 사용)
        rotation_when: 날짜별 로테이션 시점 ('S', 'M', 'H', 'D', 'W0'-'W6', 'midnight', None이면 기본값 사용)
        rotation_interval: 로테이션 간격 (rotation_type='date'일 때 사용, None이면 기본값 사용)
        filename_date: 날짜별 파일명 패턴 (예: '%Y-%m-%d', None이면 TimedRotatingFileHandler 기본 형식 사용)
        filename_prefix: 파일명 접두사 (예: 'app_', None이면 기본 파일명 사용)
    """
    global _logging_config
    
    # output_level이 지정되지 않으면 level 사용 (하위 호환성)
    if output_level is None:
        output_level = level
    
    _logging_config['level'] = output_level  # 하위 호환성 유지
    _logging_config['output_level'] = output_level
    _logging_config['file_enabled'] = file_enabled
    _logging_config['file_path'] = file_path
    
    # log_level이 지정되지 않으면 output_level과 동일하게 설정
    if log_level is None:
        log_level = output_level
    _logging_config['log_level'] = log_level
    
    # log_format이 지정되면 업데이트
    if log_format is not None:
        _logging_config['log_format'] = log_format
    
    # date_format 업데이트
    if date_format != '__NOT_SET__':
        # None이어도 명시적으로 설정하여 빈 문자열 제거
        _logging_config['date_format'] = date_format
    
    # colors가 지정되면 업데이트
    if colors is not None:
        _logging_config['colors'] = colors
    
    # rotation_type이 지정되면 업데이트
    if rotation_type is not None:
        _logging_config['rotation_type'] = rotation_type
    
    # max_bytes가 지정되면 업데이트
    if max_bytes is not None:
        _logging_config['max_bytes'] = max_bytes
    
    # backup_count가 지정되면 업데이트
    if backup_count is not None:
        _logging_config['backup_count'] = backup_count
    
    # rotation_when이 지정되면 업데이트
    if rotation_when is not None:
        _logging_config['rotation_when'] = rotation_when
    
    # rotation_interval이 지정되면 업데이트
    if rotation_interval is not None:
        _logging_config['rotation_interval'] = rotation_interval
    
    # filename_date가 지정되면 업데이트
    if filename_date is not None:
        _logging_config['filename_date'] = filename_date
    
    # filename_prefix가 지정되면 업데이트
    if filename_prefix is not None:
        _logging_config['filename_prefix'] = filename_prefix
    
    # 모든 기존 로거 재설정 (설정을 읽은 후 적용)
    output_log_level = LOG_LEVELS.get(output_level.upper(), logging.INFO)
    for logger in list(_loggers.values()):  # 리스트로 복사하여 안전하게 순회
        logger.setLevel(output_log_level)
        # 기존 핸들러 제거
        logger.handlers.clear()
        _setup_handlers(logger, file_enabled, file_path)
    
    # 로깅 초기화 완료 표시
    global _logging_initialized
    _logging_initialized = True


def _setup_handlers(logger, file_enabled, file_path):
    """로거에 핸들러 설정
    
    Args:
        logger: 설정할 로거
        file_enabled: 파일 로그 저장 여부
        file_path: 로그 파일 경로
    """
    output_log_level = LOG_LEVELS.get(_logging_config['output_level'].upper(), logging.INFO)
    log_file_level = LOG_LEVELS.get(_logging_config['log_level'].upper(), logging.INFO)
    logger.setLevel(output_log_level)
    
    # 포맷터 생성 (밀리초 지원)
    date_format = _get_date_format()
    log_format = _get_log_format()
    
    # date_format이 None이면 log_format에서 날짜 부분 제거
    if date_format is None:
        # %(asctime)s 및 앞뒤 공백 제거 (%는 정규식에서 특수문자이므로 이스케이프 필요)
        import re
        log_format = re.sub(r'%\(asctime\)s\s*', '', log_format)
        log_format = re.sub(r'\s+', ' ', log_format).strip()  # 연속된 공백 정리
        formatter = logging.Formatter(log_format, datefmt=None)
    else:
        import re
        # %f, %3f, %.3f 등 밀리초 형식 감지
        if re.search(r'%\.?\d*f', date_format):
            # 밀리초가 포함된 경우 커스텀 포맷터 사용
            formatter = MillisecondFormatter(log_format, date_format)
        else:
            formatter = logging.Formatter(log_format, date_format)
    
    # 출력 핸들러 (항상 추가)
    output_handler = logging.StreamHandler()
    output_handler.setLevel(output_log_level)
    output_handler.setFormatter(formatter)
    logger.addHandler(output_handler)
    
    # 파일 핸들러 (설정된 경우에만 추가)
    if file_enabled:
        try:
            _ensure_log_directory(file_path)
            rotation_type = _logging_config.get('rotation_type', 'size')
            
            # 파일명 생성 (prefix, pattern 적용)
            log_dir = os.path.dirname(file_path) or '.'
            base_name = os.path.basename(file_path)
            
            # 확장자 분리
            if '.' in base_name:
                name_part, ext_part = base_name.rsplit('.', 1)
                ext_part = '.' + ext_part
            else:
                name_part = base_name
                ext_part = ''
            
            # prefix 적용
            filename_prefix = _logging_config.get('filename_prefix', None)
            if filename_prefix:
                name_part = f"{filename_prefix}{name_part}"
            
            # 날짜 패턴 적용 (rotation_type='date'이고 패턴이 지정된 경우)
            rotation_type = _logging_config.get('rotation_type', 'size')
            filename_date = _logging_config.get('filename_date', None)
            
            if rotation_type == 'date' and filename_date:
                from datetime import datetime
                date_str = datetime.now().strftime(filename_date)
                final_name = f"{name_part}_{date_str}{ext_part}"
            else:
                final_name = f"{name_part}{ext_part}"
            
            final_file_path = os.path.join(log_dir, final_name)
            
            if rotation_type == 'date':
                # TimedRotatingFileHandler 사용 (날짜별 로테이션)
                from logging.handlers import TimedRotatingFileHandler
                rotation_when = _logging_config.get('rotation_when', 'midnight')
                rotation_interval = _logging_config.get('rotation_interval', 1)
                backup_count = _logging_config.get('backup_count', 5)
                
                file_handler = TimedRotatingFileHandler(
                    final_file_path,
                    when=rotation_when,
                    interval=rotation_interval,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            else:
                # RotatingFileHandler 사용 (파일 크기 제한 및 로테이션)
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    final_file_path,
                    maxBytes=_logging_config.get('max_bytes', 10 * 1024 * 1024),
                    backupCount=_logging_config.get('backup_count', 5),
                    encoding='utf-8'
                )
            
            file_handler.setLevel(log_file_level)  # 파일 로그 레벨 사용
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
    output_log_level = LOG_LEVELS.get(_logging_config['output_level'].upper(), logging.INFO)
    logger.setLevel(output_log_level)
    
    # 핸들러 설정 (최신 설정 사용)
    _setup_handlers(logger, _logging_config['file_enabled'], _logging_config['file_path'])
    
    # 캐싱
    _loggers[module_name] = logger
    
    return logger


def log_error(module_name: str, message: str, exception: Optional[Exception] = None):
    """에러 로깅 헬퍼 함수 (파일 로그용만, 콘솔 출력 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        exception: 예외 객체 (선택)
    """
    logger = get_logger(module_name)
    # 파일 핸들러만 사용하여 기록 (콘솔 핸들러는 건너뛰기)
    from logging.handlers import RotatingFileHandler
    file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    
    if file_handlers:
        # LogRecord 생성 (포맷터가 제대로 적용되도록)
        if exception:
            record = logger.makeRecord(
                logger.name, logging.ERROR, "", 0,
                f"{message}: {exception}", (), exception, exc_info=True
            )
        else:
            record = logger.makeRecord(
                logger.name, logging.ERROR, "", 0,
                message, (), None
            )
        
        # 파일 핸들러에만 기록
        for handler in file_handlers:
            handler.emit(record)


def log_warning(module_name: str, message: str):
    """경고 로깅 헬퍼 함수 (파일 로그용만, 콘솔 출력 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    # 파일 핸들러만 사용하여 기록 (콘솔 핸들러는 건너뛰기)
    from logging.handlers import RotatingFileHandler
    file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    
    if file_handlers:
        record = logger.makeRecord(
            logger.name, logging.WARNING, "", 0,
            message, (), None
        )
        for handler in file_handlers:
            handler.emit(record)


def log_info(module_name: str, message: str):
    """정보 로깅 헬퍼 함수 (파일 로그용만, 콘솔 출력 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    # 파일 핸들러만 사용하여 기록 (콘솔 핸들러는 건너뛰기)
    from logging.handlers import RotatingFileHandler
    file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    
    if file_handlers:
        record = logger.makeRecord(
            logger.name, logging.INFO, "", 0,
            message, (), None
        )
        for handler in file_handlers:
            handler.emit(record)


def log_debug(module_name: str, message: str):
    """디버그 로깅 헬퍼 함수 (파일 로그용만, 콘솔 출력 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    logger = get_logger(module_name)
    # 파일 핸들러만 사용하여 기록 (콘솔 핸들러는 건너뛰기)
    from logging.handlers import RotatingFileHandler
    file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    
    if file_handlers:
        record = logger.makeRecord(
            logger.name, logging.DEBUG, "", 0,
            message, (), None
        )
        for handler in file_handlers:
            handler.emit(record)


# 파일 로그 전용 함수
def log_file(module_name: str, message: str, level: str = 'INFO'):
    """파일에만 로그를 기록하는 함수 (콘솔 출력 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        level: 로그 레벨 (기본: INFO)
    """
    logger = get_logger(module_name)
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.log(log_level, message)


# ========== 색상 출력 함수 ==========

def _is_windows_terminal():
    """Windows Terminal인지 확인"""
    return os.environ.get('WT_SESSION') is not None or os.environ.get('TERM_PROGRAM') == 'vscode'


def _parse_color_string(color_str: str) -> str:
    """색상 문자열을 colorama 코드로 변환
    
    Args:
        color_str: 색상 문자열 (예: "GREEN+BRIGHT", "CYAN", "RED+BRIGHT")
        
    Returns:
        colorama 색상 코드 문자열
    """
    if not COLORAMA_AVAILABLE or not color_str:
        return ''
    
    parts = color_str.upper().split('+')
    color_name = parts[0].strip()
    style_name = parts[1].strip() if len(parts) > 1 else None
    
    # BRIGHT 스타일이 있으면 밝은 색상으로 매핑
    if style_name == 'BRIGHT':
        # 항상 LIGHT*_EX를 우선 사용 (더 밝게 표시됨)
        try:
            bright_color_map_ex = {
                'BLACK': Fore.LIGHTBLACK_EX,
                'RED': Fore.LIGHTRED_EX,
                'GREEN': Fore.LIGHTGREEN_EX,  # 밝은 녹색
                'YELLOW': Fore.LIGHTYELLOW_EX,
                'BLUE': Fore.LIGHTBLUE_EX,
                'MAGENTA': Fore.LIGHTMAGENTA_EX,
                'CYAN': Fore.LIGHTCYAN_EX,  # 밝은 하늘색
                'WHITE': Fore.LIGHTWHITE_EX,
            }
            if color_name in bright_color_map_ex:
                return bright_color_map_ex[color_name]
        except AttributeError:
            pass
        
        # 폴백: Style.BRIGHT 사용
        bright_color_map = {
            'BLACK': Fore.BLACK + Style.BRIGHT,
            'RED': Fore.RED + Style.BRIGHT,
            'GREEN': Fore.GREEN + Style.BRIGHT,
            'YELLOW': Fore.YELLOW + Style.BRIGHT,
            'BLUE': Fore.BLUE + Style.BRIGHT,
            'MAGENTA': Fore.MAGENTA + Style.BRIGHT,
            'CYAN': Fore.CYAN + Style.BRIGHT,
            'WHITE': Fore.WHITE + Style.BRIGHT,
        }
        return bright_color_map.get(color_name, Fore.WHITE + Style.BRIGHT)
    
    # 밝은 색상 상수 직접 지원 (예: "LIGHTCYAN_EX", "LIGHTGREEN_EX")
    if color_name.endswith('_EX'):
        try:
            bright_color_map_ex = {
                'LIGHTBLACK_EX': Fore.LIGHTBLACK_EX,
                'LIGHTRED_EX': Fore.LIGHTRED_EX,
                'LIGHTGREEN_EX': Fore.LIGHTGREEN_EX,
                'LIGHTYELLOW_EX': Fore.LIGHTYELLOW_EX,
                'LIGHTBLUE_EX': Fore.LIGHTBLUE_EX,
                'LIGHTMAGENTA_EX': Fore.LIGHTMAGENTA_EX,
                'LIGHTCYAN_EX': Fore.LIGHTCYAN_EX,  # 밝은 하늘색
                'LIGHTWHITE_EX': Fore.LIGHTWHITE_EX,
            }
            if color_name in bright_color_map_ex:
                return bright_color_map_ex[color_name]
        except AttributeError:
            pass
    
    # 일반 색상 매핑
    fore_map = {
        'BLACK': Fore.BLACK,
        'RED': Fore.RED,
        'GREEN': Fore.GREEN,
        'YELLOW': Fore.YELLOW,
        'BLUE': Fore.BLUE,
        'MAGENTA': Fore.MAGENTA,
        'CYAN': Fore.CYAN,
        'WHITE': Fore.WHITE,
    }
    
    # Style 매핑 (BRIGHT 제외)
    style_map = {
        'DIM': Style.DIM,
        'NORMAL': Style.NORMAL,
    }
    
    color_code = fore_map.get(color_name, '')
    if style_name and style_name in style_map:
        color_code += style_map[style_name]
    
    return color_code


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
    
    # 설정 파일에서 색상 가져오기
    colors = _logging_config.get('colors', {})
    color_str = colors.get(level_upper)
    
    if color_str:
        return _parse_color_string(color_str)
    
    # 기본값 (설정 파일에 없을 경우)
    default_color_map = {
        'PRN': Fore.WHITE,
        'LOG': Fore.YELLOW,
        'MEMO': Fore.MAGENTA,
        'DEBUG': Fore.CYAN + Style.BRIGHT,
        'INFO': Fore.GREEN + Style.BRIGHT,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED + Style.BRIGHT,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT,
    }
    return default_color_map.get(level_upper, '')


def log_output(module_name: str, message: str, level: str = 'INFO', use_color: bool = True):
    """콘솔에만 색상 출력하는 함수 (파일 기록 없음)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_color: 색상 사용 여부 (기본: True)
        
    Examples:
        log_output("얼굴편집", "드래그 시작: 랜드마크 인덱스 285", "INFO")
        log_output("얼굴모핑", "에러 발생", "ERROR")
    """
    color = _get_color_for_level(level) if use_color and COLORAMA_AVAILABLE else ''
    reset = Fore.RESET if use_color and COLORAMA_AVAILABLE else ''
    clock = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # 기존 형식: [모듈] 메시지
    formatted_message = f"{color}[{clock}][{module_name}] {message}{reset}"
    
    # 콘솔에 색상 출력만 (파일 기록 없음)
    print(formatted_message, file=sys.stdout if level.upper() != 'ERROR' else sys.stderr)


def error(module_name: str, message: str, exception: Optional[Exception] = None):
    """에러 출력 (밝은 빨간색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        exception: 예외 객체 (선택)
    """
    if exception:
        full_message = f"{message}: {exception}"
        log_output(module_name, full_message, 'ERROR')
        # 파일 로그가 활성화된 경우에만 기록
        if _logging_config['file_enabled']:
            log_error(module_name, message, exception)
    else:
        log_output(module_name, message, 'ERROR')
        # 파일 로그가 활성화된 경우에만 기록
        if _logging_config['file_enabled']:
            log_error(module_name, message)


def warning(module_name: str, message: str):
    """경고 출력 (일반 노란색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'WARNING')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_warning(module_name, message)


def info(module_name: str, message: str):
    """정보 출력 (밝은 녹색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'INFO')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_info(module_name, message)


def debug(module_name: str, message: str):
    """디버그 출력 (청록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'DEBUG')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_debug(module_name, message)

def log(module_name: str, message: str):
    """디버그 출력 (청록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'LOG')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_debug(module_name, message)

def memo(module_name: str, message: str):
    """디버그 출력 (청록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'MEMO')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_debug(module_name, message)                        

def prn(module_name: str, message: str):
    """디버그 출력 (청록색)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
    """
    log_output(module_name, message, 'PRN')
    # 파일 로그가 활성화된 경우에만 기록
    if _logging_config['file_enabled']:
        log_debug(module_name, message)                


def output(module_name: str, message: str, color: Optional[str] = None):
    """레벨 없이 출력하는 함수 (색상 선택 가능)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        color: 색상 (None이면 색상 없음, "GREEN", "RED", "YELLOW" 등 지정 가능)
        
    Examples:
        output("시스템", "일반 메시지")  # 색상 없음
        output("시스템", "성공 메시지", "GREEN")  # 녹색
        output("시스템", "경고 메시지", "YELLOW")  # 노란색
    """
    if color and COLORAMA_AVAILABLE:
        color_code = _parse_color_string(color)
        reset = Fore.RESET
        formatted_message = f"{color_code}[{module_name}] {message}{reset}"
    else:
        formatted_message = f"[{module_name}] {message}"
    
    print(formatted_message)

def console(module_name: str, message: str, color: Optional[str] = None):
    """레벨 없이 출력하는 함수 (색상 선택 가능)
    
    Args:
        module_name: 모듈 이름
        message: 메시지
        color: 색상 (None이면 색상 없음, "GREEN", "RED", "YELLOW" 등 지정 가능)
        
    Examples:
        output("시스템", "일반 메시지")  # 색상 없음
        output("시스템", "성공 메시지", "GREEN")  # 녹색
        output("시스템", "경고 메시지", "YELLOW")  # 노란색
    """
    if color and COLORAMA_AVAILABLE:
        color_code = _parse_color_string(color)
        reset = Fore.RESET
        formatted_message = f"{color_code}[{module_name}] {message}{reset}"
    else:
        formatted_message = f"[{module_name}] {message}"
    
    print(formatted_message)    


# 별칭 (하위 호환성 및 짧은 이름 지원)
err = error  # error()와 err() 둘 다 사용 가능
warn = warning
dbg = debug

# 하위 호환성을 위한 별칭 (기존 print_* 함수명)
print_error = error
print_warning = warning
print_info = info
print_debug = debug
print_colored = log_output  # 하위 호환성
print_log = log_file  # 하위 호환성

# 추가 별칭
colored = log_output  # 하위 호환성
print_output = output  # 레벨 없이 출력
