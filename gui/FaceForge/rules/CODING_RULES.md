# FaceForge 작업 룰 & 코딩 컨벤션

MediaPipe + PIL + Tkinter 기반 FaceForge 프로젝트에서 일관된 품질을 유지하기 위한 규칙입니다. React/FastAPI 등으로 확장할 때도 재사용할 수 있도록 모듈화 지향 원칙을 포함합니다.

---

## 1. 기본 원칙

1. **모듈화**: UI, 이미지 처리, MediaPipe 로직을 서로 다른 모듈로 분리합니다.
2. **가독성 우선**: PEP 8과 Google Python Style Guide를 기본으로 합니다.
3. **API 전환 대비**: 얼굴 처리 로직은 GUI와 분리해 `services/`, `core/` 모듈에 배치합니다.
4. **상태 최소화**: Tkinter 위젯 상태는 클래스 멤버 변수로 관리하고, 글로벌 상태는 금지합니다.

---

## 2. 디렉터리 구조 권장안

```
FaceForge/
├─ main.py                 # Tkinter 엔트리 포인트
├─ requirements.txt
├─ README.md
├─ CODING_RULES.md
├─ faceforge/
│  ├─ __init__.py
│  ├─ ui/                 # Tkinter 뷰/컨트롤러
│  ├─ services/           # MediaPipe, PIL 로직
│  ├─ models/             # 데이터 구조, DTO
│  ├─ utils/              # 공용 함수
│  └─ config.py           # 설정, 경로
└─ tests/                 # 서비스/유틸 단위 테스트
```

> 아직 폴더가 없다면 작업하면서 위 구조로 확장해주세요.

---

## 3. Python 코드 스타일

| 항목 | 규칙 |
|------|------|
| 들여쓰기 | 스페이스 4칸, 탭 금지 |
| 최대 줄 길이 | 주석/문자열 포함 100자 |
| 문자열 | 사용자 노출 문자열은 f-string 사용, 다국어 지원 대비 상수 분리 |
| 타입 힌트 | 함수 시그니처 및 반환 타입 필수 (`-> None` 포함) |
| Docstring | public 함수/클래스에 Google 스타일 docstring 사용 |
| 임포트 | 표준 → 서드파티 → 로컬 순, 알파벳 정렬 |
| 에러 처리 | 사용자 메시지는 `messagebox`, 내부 로그는 `logging` 모듈 |

예시:
```python
from faceforge.services.detector import FaceDetector

class FaceController:
    """Tkinter 이벤트와 얼굴 처리 서비스를 연결하는 컨트롤러."""

    def __init__(self, detector: FaceDetector) -> None:
        self.detector = detector
```

---

## 4. Tkinter UI 규칙

1. **MVC-ish 구조**: UI는 이벤트만 받고, 실제 처리는 서비스에 위임합니다.
2. **위젯 생성 함수 분리**: `create_toolbar()`, `create_canvas()`처럼 영역별 메서드 사용.
3. **상태 변수**: `tk.StringVar`, `tk.BooleanVar`를 사용하고 네이밍은 `self.xxx_var`.
4. **레이아웃**: 동일 프레임 내에서 `pack`과 `grid` 혼용 금지.
5. **비동기 작업**: 장시간 처리 시 `threading`+`queue` 사용, UI 스레드는 block 금지.

---

## 5. MediaPipe + PIL 처리 룰

1. **색상 공간**: PIL 이미지는 RGB, MediaPipe 입력은 numpy array(BGR) 요구 → 변환 함수 작성.
2. **리소스 관리**: MediaPipe `FaceMesh`는 싱글톤 서비스로 재사용, 매 요청마다 생성 금지.
3. **데이터 클래스**: 랜드마크, 변형 파라미터는 `@dataclass` 로 정의하여 명시적 관리.
4. **오류 전파**: MediaPipe 실패 시 사용자에게 친절한 메시지 제공 + 내부 로그 남김.
5. **성능**: 불필요한 전체 해상도 처리 지양, 미리보기용 다운스케일 후 좌표 매핑.

예시 함수 네이밍:
- `convert_pil_to_mediapipe(image: Image.Image) -> np.ndarray`
- `apply_morph(image: Image.Image, landmarks: LandmarkSet, params: MorphParams) -> Image.Image`

---

## 6. 로깅 & 에러 처리

- `logging` 기본 설정은 `faceforge/utils/logging.py`에서 구성.
- 레벨 규칙: 사용자 오류 → `warning`, 시스템 오류 → `error`.
- 예외는 서비스 레이어에서 처리 후 사용자 친화적 메시지로 재가공.

---

## 7. 테스트 & 검증

| 구분 | 방법 |
|------|------|
| 유닛 테스트 | `pytest` 권장, `tests/services/test_detector.py` 등 |
| UI 테스트 | 수동 체크리스트 (로드 → 감지 → 저장) 유지 |
| 데이터 | 테스트용 샘플 이미지는 `tests/assets/` 에 저장 |

테스트 커맨드 예시:
```bash
pytest tests/services -q
```

---

## 8. Git & 작업 흐름

1. **브랜치**: `main` 보호, 기능별 `feature/<topic>` 브랜치 사용.
2. **커밋 메시지**: `feat:`, `fix:`, `refactor:`, `docs:` 프리픽스 사용.
3. **PR 체크리스트**:
   - [ ] 코드 스타일 검사 완료 (예: `ruff`, `black`)
   - [ ] 영향 영역 테스트 수행
   - [ ] 사용자 메시지/번역 점검
4. **릴리스 태그**: `vMAJOR.MINOR.PATCH` (예: `v0.1.0`).

---

## 9. 추후 API 서버 전환 가이드

- 얼굴 처리 서비스는 UI 의존성 없이 순수 함수 형태로 유지.
- I/O 포맷을 JSON-serializable 구조로 설계 (예: `dict` or `pydantic` 모델).
- Tkinter 전용 로직은 `faceforge/ui/` 폴더에만 위치시키고, 나머지 코드는 공유 모듈화.

---

## 10. 문서화 원칙

- 변경 시 `README.md`와 본 문서를 최신 상태로 유지합니다.
- 중요한 결정은 `docs/DECISIONS.md`에 기록해 히스토리 추적.

이 규칙을 기반으로 작업하면, 추후 React/FastAPI로 확장하거나 AI 기능을 추가할 때도 안정적으로 전환할 수 있습니다.
