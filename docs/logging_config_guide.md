# 로그 설정 가이드

**작성 일시**: 2026-01-20  
**설정 파일**: `logging.json`

## 개요

로그 설정은 `logging.json` 파일에서 관리됩니다. 이 파일이 없으면 기본값이 사용됩니다.

**중요**: 파일 로그 활성화 여부는 `log_level` 설정으로 제어됩니다.
- `log_level`이 유효한 레벨 값(`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`)이면 → 파일 로그 활성화
- `log_level`이 없거나 `null`, 빈 문자열(`""`), 공백만 있거나, `"None"` (대소문자 구분 없음)이면 → 파일 로그 비활성화

파일 로그를 저장하지 않으려면 `logging.json` 파일을 삭제하거나, `log_level`을 제거하거나 `null`, `""`, `"None"` 등으로 설정하세요.

## 설정 파일 위치

- **주 설정 파일**: `logging.json` (프로젝트 루트)
- **하위 호환성**: `config.json`의 `logging` 섹션도 지원 (자동 마이그레이션)

## 설정 항목 설명

### 기본 설정

#### `level` (하위 호환성용)
- **타입**: 문자열
- **기본값**: `"INFO"`
- **설명**: 출력 레벨 (하위 호환성을 위해 유지됨)
- **값**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **참고**: `output_level` 사용 권장

#### `output_level`
- **타입**: 문자열
- **기본값**: `"INFO"`
- **설명**: 콘솔/화면 출력 레벨
- **값**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **예시**: `"INFO"` → INFO 이상 레벨만 화면에 출력

#### `log_level`
- **타입**: 문자열 또는 `null`
- **기본값**: 없음 (설정하지 않으면 파일 로그 비활성화)
- **설명**: 파일 로그 레벨. 유효한 레벨 값이 설정되어 있으면 파일 로그가 활성화됩니다.
- **값**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`, 또는 `null`, `""`, `"None"` (대소문자 구분 없음)
- **예시**: 
  - `"WARNING"` → WARNING 이상 레벨만 파일에 기록 (파일 로그 활성화)
  - `null`, `""`, `"None"`, `"none"`, `"NONE"`, 공백만 있거나 설정하지 않음 → 파일 로그 비활성화
- **참고**: `log_level`이 유효한 레벨 값(`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`)으로 설정되어 있어야 파일 로그가 활성화됩니다. `logging.json` 파일이 있어도 `log_level`이 없거나 `null`, 빈 문자열(`""`), `"None"` (대소문자 구분 없음), 공백만 있으면 파일 로그는 비활성화됩니다.

#### `file_path`
- **타입**: 문자열
- **기본값**: `"logs/s7ed.log"`
- **설명**: 로그 파일 경로
- **예시**: `"logs/s7ed.log"`, `"logs/app.log"`

### 로그 메시지 형식

#### `log_format`
- **타입**: 문자열
- **기본값**: `"%(asctime)s [%(levelname)s] [%(name)s] %(message)s"`
- **설명**: 로그 메시지 포맷 문자열
- **사용 가능한 변수**:
  - `%(asctime)s`: 날짜/시간
  - `%(levelname)s`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - `%(name)s`: 모듈 이름
  - `%(message)s`: 로그 메시지
  - `%(filename)s`: 파일명
  - `%(lineno)d`: 라인 번호
  - `%(funcName)s`: 함수명
- **예시**: 
  - `"%(asctime)s [%(levelname)s] [%(name)s] %(message)s"`
  - `"%(asctime)s - %(levelname)s - %(message)s"`

#### `date_format`
- **타입**: 문자열
- **기본값**: `"%Y-%m-%d %H:%M:%S"`
- **설명**: 날짜/시간 포맷 문자열 (`log_format`의 `%(asctime)s`에 사용)
- **사용 가능한 형식**:
  - `%Y`: 4자리 연도 (예: 2026)
  - `%m`: 월 (01-12)
  - `%d`: 일 (01-31)
  - `%H`: 시간 (00-23)
  - `%M`: 분 (00-59)
  - `%S`: 초 (00-59)
- **예시**:
  - `"%Y-%m-%d %H:%M:%S"` → `2026-01-20 14:30:25`
  - `"%Y%m%d_%H%M%S"` → `20260120_143025`

### 색상 설정

#### `colors`
- **타입**: 객체 (딕셔너리)
- **기본값**: 
  ```json
  {
    "DEBUG": "CYAN",
    "INFO": "GREEN+BRIGHT",
    "WARNING": "YELLOW",
    "ERROR": "RED+BRIGHT",
    "CRITICAL": "MAGENTA+BRIGHT"
  }
  ```
- **설명**: 레벨별 콘솔 출력 색상 설정
- **형식**: `"COLOR"` 또는 `"COLOR+STYLE"`
- **지원 색상**: `BLACK`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `WHITE`
- **지원 스타일**: `DIM`, `NORMAL`, `BRIGHT`
- **예시**:
  - `"CYAN"`: 청록색
  - `"GREEN+BRIGHT"`: 밝은 녹색
  - `"RED+BRIGHT"`: 밝은 빨간색

### 로그 파일 로테이션

#### `rotation_type`
- **타입**: 문자열
- **기본값**: `"size"`
- **설명**: 로그 파일 로테이션 타입
- **값**: 
  - `"size"`: 파일 크기 기반 로테이션
  - `"date"`: 날짜별 로테이션

#### `max_bytes` (rotation_type='size'일 때 사용)
- **타입**: 숫자
- **기본값**: `10485760` (10MB)
- **설명**: 최대 파일 크기 (바이트 단위)
- **예시**: `10485760` (10MB), `52428800` (50MB)

#### `backup_count`
- **타입**: 숫자
- **기본값**: `5`
- **설명**: 백업 파일 개수 (오래된 파일은 자동 삭제)
- **예시**: `5` → 최신 파일 + 백업 5개 유지

#### `rotation_when` (rotation_type='date'일 때 사용)
- **타입**: 문자열
- **기본값**: `"midnight"`
- **설명**: 날짜별 로테이션 시점
- **값**:
  - `"S"`: 초 단위
  - `"M"`: 분 단위
  - `"H"`: 시간 단위
  - `"D"`: 일 단위
  - `"W0"`~`"W6"`: 주 단위 (0=월요일, 6=일요일)
  - `"midnight"`: 자정

#### `rotation_interval` (rotation_type='date'일 때 사용)
- **타입**: 숫자
- **기본값**: `1`
- **설명**: 로테이션 간격
- **예시**: 
  - `rotation_when="H"`, `rotation_interval=1` → 매시간
  - `rotation_when="D"`, `rotation_interval=7` → 7일마다

#### `filename_date` (rotation_type='date'일 때 사용)
- **타입**: 문자열 또는 `null`
- **기본값**: `null`
- **설명**: 날짜별 파일명 패턴 (Python datetime 형식)
- **사용 가능한 형식**: `%Y`, `%m`, `%d`, `%H`, `%M`, `%S` 등
- **예시**:
  - `"%Y-%m-%d"` → `s7ed_2026-01-20.log`
  - `"%Y%m%d"` → `s7ed_20260120.log`
  - `"%Y-%m-%d_%H%M%S"` → `s7ed_2026-01-20_143025.log`
- **참고**: `null`이면 `TimedRotatingFileHandler` 기본 형식 사용

#### `filename_prefix`
- **타입**: 문자열 또는 `null`
- **기본값**: `null`
- **설명**: 파일명 접두사
- **예시**:
  - `"app_"` → `app_s7ed.log`
  - `"s7ed_"` → `s7ed_s7ed.log`
- **참고**: `filename_date`와 함께 사용 가능

## 설정 파일 예시

### 기본 설정 (파일 로그 비활성화)
파일 로그를 저장하지 않으려면 `log_level`을 설정하지 않거나 `null`, 빈 문자열(`""`)로 설정하세요:
```json
{
  "output_level": "INFO"
}
```

또는 `log_level`을 명시적으로 `null` 또는 빈 문자열로 설정:
```json
{
  "output_level": "INFO",
  "log_level": null
}
```

또는:
```json
{
  "output_level": "INFO",
  "log_level": ""
}
```

### 기본 설정 (파일 로그 활성화)
파일 로그를 활성화하려면 `log_level`을 설정하세요:
```json
{
  "output_level": "INFO",
  "log_level": "INFO",
  "file_path": "logs/s7ed.log"
}
```

### 파일 크기 기반 로테이션
```json
{
  "output_level": "INFO",
  "log_level": "WARNING",
  "file_path": "logs/s7ed.log",
  "rotation_type": "size",
  "max_bytes": 10485760,
  "backup_count": 5
}
```

### 날짜별 로테이션 (매일 자정)
```json
{
  "output_level": "INFO",
  "log_level": "WARNING",
  "file_path": "logs/s7ed.log",
  "rotation_type": "date",
  "rotation_when": "midnight",
  "rotation_interval": 1,
  "backup_count": 30,
  "filename_date": "%Y-%m-%d",
  "filename_prefix": "app_"
}
```

### 커스텀 색상 설정
```json
{
  "output_level": "DEBUG",
  "log_level": "INFO",
  "file_path": "logs/s7ed.log",
  "colors": {
    "DEBUG": "BLUE",
    "INFO": "GREEN",
    "WARNING": "YELLOW+BRIGHT",
    "ERROR": "RED+BRIGHT",
    "CRITICAL": "MAGENTA"
  }
}
```

### 전체 설정 예시
```json
{
  "level": "INFO",
  "output_level": "INFO",
  "log_level": "WARNING",
  "file_path": "logs/s7ed.log",
  "log_format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
  "date_format": "%Y-%m-%d %H:%M:%S",
  "colors": {
    "DEBUG": "CYAN",
    "INFO": "GREEN+BRIGHT",
    "WARNING": "YELLOW",
    "ERROR": "RED+BRIGHT",
    "CRITICAL": "MAGENTA+BRIGHT"
  },
  "rotation_type": "date",
  "rotation_when": "midnight",
  "rotation_interval": 1,
  "backup_count": 30,
  "filename_date": "%Y-%m-%d",
  "filename_prefix": "app_"
}
```

## 파일명 생성 예시

### 기본 파일명
- `file_path`: `"logs/s7ed.log"`
- 결과: `logs/s7ed.log`

### Prefix만 사용
- `file_path`: `"logs/s7ed.log"`
- `filename_prefix`: `"app_"`
- 결과: `logs/app_s7ed.log`

### 날짜 패턴만 사용
- `file_path`: `"logs/s7ed.log"`
- `filename_date`: `"%Y-%m-%d"`
- 결과: `logs/s7ed_2026-01-20.log`

### Prefix + 날짜 패턴
- `file_path`: `"logs/s7ed.log"`
- `filename_prefix`: `"app_"`
- `filename_date`: `"%Y-%m-%d"`
- 결과: `logs/app_s7ed_2026-01-20.log`

## 로그 레벨 우선순위

1. `CRITICAL` (최고)
2. `ERROR`
3. `WARNING`
4. `INFO`
5. `DEBUG` (최저)

설정한 레벨 이상의 로그만 출력/기록됩니다.

## 주의사항

1. **파일 경로**: 상대 경로는 프로젝트 루트 기준입니다.
2. **날짜 패턴**: `rotation_type='date'`일 때만 `filename_date`가 적용됩니다.
3. **색상**: Windows에서는 `colorama` 패키지가 필요합니다.
4. **하위 호환성**: `config.json`의 `logging` 섹션도 지원하지만, `logging.json` 사용을 권장합니다.
