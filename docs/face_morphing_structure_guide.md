# 얼굴 모핑 모듈 구조 가이드

**작성일**: 2026-01-17  
**목적**: 리팩토링된 `utils/face_morphing/` 패키지 구조 이해 및 기능 추가 가이드

## 📁 모듈 구조

```
utils/face_morphing/
├── __init__.py          # 공개 API 제공 (기존 호환성 유지)
├── constants.py         # 상수 및 전역 변수
├── utils.py             # 유틸리티 함수 (마스크 생성)
├── region_extraction.py # 영역 추출 함수 (눈, 입, 코)
├── adjustments.py       # 이미지 조정 함수 (14개)
├── polygon_morphing.py  # 폴리곤 포인트 변형 및 모핑
└── integration.py       # 통합 함수 (apply_all_adjustments)
```

## 🎯 각 모듈의 역할

### 1. `constants.py` (37줄)
**역할**: 상수 및 전역 변수 관리

**포함 내용**:
- OpenCV, scipy, face_landmarks 선택적 import 확인
- Delaunay Triangulation 캐시

**기능 추가 시**:
- 새로운 상수나 전역 변수가 필요하면 여기에 추가

---

### 2. `utils.py` (82줄)
**역할**: 유틸리티 함수 (마스크 생성 및 블렌딩)

**포함 함수**:
- `_sigmoid_blend_mask()`: 시그모이드 블렌딩 마스크
- `_create_blend_mask()`: 블렌딩 마스크 생성

**기능 추가 시**:
- 마스크 관련 유틸리티 함수 추가
- 블렌딩 관련 헬퍼 함수 추가

---

### 3. `region_extraction.py` (348줄)
**역할**: 얼굴 특징 영역 추출 (눈, 입, 코)

**포함 함수**:
- `_get_eye_region()`: 눈 영역 계산
- `_get_mouth_region()`: 입 영역 계산
- `_get_nose_region()`: 코 영역 계산

**기능 추가 시**:
- 새로운 얼굴 영역 추출 함수 추가 (예: 눈썹, 턱선 등)
- 영역 계산 로직 개선

---

### 4. `adjustments.py` (2,049줄)
**역할**: 이미지 조정 함수 (얼굴 특징 직접 조정)

**포함 함수** (14개):
- `adjust_eye_size()`: 눈 크기 조정
- `adjust_eye_spacing()`: 눈 간격 조정
- `adjust_eye_position()`: 눈 위치 조정
- `adjust_nose_size()`: 코 크기 조정
- `adjust_jaw()`: 턱선 조정
- `adjust_face_size()`: 얼굴 크기 조정
- `adjust_mouth_size()`: 입 크기 조정
- `adjust_upper_lip_size()`: 윗입술 크기 조정
- `adjust_lower_lip_size()`: 아래입술 크기 조정
- `adjust_upper_lip_shape()`: 윗입술 모양 조정
- `adjust_lower_lip_shape()`: 아래입술 모양 조정
- `adjust_upper_lip_width()`: 윗입술 너비 조정
- `adjust_lower_lip_width()`: 아래입술 너비 조정
- `adjust_lip_vertical_move()`: 입술 수직 이동 조정

**기능 추가 시**:
- 새로운 얼굴 특징 조정 함수 추가
- 기존 조정 함수 개선
- **주의**: 이 파일이 가장 큼 (2,049줄), 향후 2차 리팩토링 고려

---

### 5. `polygon_morphing.py` (1,731줄)
**역할**: 폴리곤 포인트 변형 및 폴리곤 모핑

**포함 함수**:
- **포인트 변형 함수** (9개):
  - `transform_points_for_eye_size()`: 눈 크기 조정을 포인트 변형으로 변환
  - `transform_points_for_nose_size()`: 코 크기 조정을 포인트 변형으로 변환
  - `transform_points_for_jaw()`: 턱선 조정을 포인트 변형으로 변환
  - `transform_points_for_face_size()`: 얼굴 크기 조정을 포인트 변형으로 변환
  - `transform_points_for_mouth_size()`: 입 크기 조정을 포인트 변형으로 변환
  - `transform_points_for_eye_position()`: 눈 위치 조정을 포인트 변형으로 변환
  - `transform_points_for_lip_shape()`: 입술 모양 조정을 포인트 변형으로 변환
  - `transform_points_for_lip_width()`: 입술 너비 조정을 포인트 변형으로 변환
  - `transform_points_for_lip_vertical_move()`: 입술 수직 이동 조정을 포인트 변형으로 변환

- **포인트 이동 함수** (2개):
  - `move_point_group()`: 랜드마크 그룹 이동
  - `move_points()`: 특정 포인트 이동 (주변 영향 포함)

- **모핑 함수** (1개):
  - `morph_face_by_polygons()`: Delaunay Triangulation 기반 이미지 모핑

**기능 추가 시**:
- 새로운 포인트 변형 함수 추가 (예: `transform_points_for_eyebrow_*`)
- 포인트 이동 로직 개선
- 모핑 알고리즘 개선

---

### 6. `integration.py` (390줄)
**역할**: 통합 함수 (모든 얼굴 특징 보정을 한 번에 적용)

**포함 함수**:
- `apply_all_adjustments()`: 모든 얼굴 특징 보정을 한 번에 적용

**기능 추가 시**:
- 새로운 조정 파라미터 추가
- 조정 순서 최적화
- 성능 개선

---

### 7. `__init__.py` (124줄)
**역할**: 공개 API 제공 (기존 호환성 유지)

**포함 내용**:
- 모든 공개 함수를 import하여 제공
- `__all__` 리스트로 공개 API 명시

**기능 추가 시**:
- 새로운 공개 함수를 `__all__`에 추가
- import 문 추가

---

## 🔍 기능 추가 가이드

### 시나리오별 추가 위치

#### 1. 새로운 얼굴 특징 조정 기능 추가
**예**: 눈썹 두께 조정

**추가 위치**:
1. `adjustments.py`: `adjust_eyebrow_thickness()` 함수 추가
2. `polygon_morphing.py`: `transform_points_for_eyebrow_thickness()` 함수 추가 (랜드마크 변형 모드용)
3. `integration.py`: `apply_all_adjustments()`에 파라미터 및 호출 추가
4. `__init__.py`: 공개 API에 추가

**코드 예시**:
```python
# adjustments.py
def adjust_eyebrow_thickness(image, eyebrow_thickness_ratio=1.0, landmarks=None):
    """눈썹 두께 조정"""
    # 구현...
    pass

# polygon_morphing.py
def transform_points_for_eyebrow_thickness(landmarks, eyebrow_thickness_ratio=1.0):
    """눈썹 두께 조정을 포인트 변형으로 변환"""
    # 구현...
    pass
```

---

#### 2. 새로운 영역 추출 기능 추가
**예**: 볼 영역 추출

**추가 위치**:
1. `region_extraction.py`: `_get_cheek_region()` 함수 추가
2. `adjustments.py` 또는 다른 모듈에서 사용

**코드 예시**:
```python
# region_extraction.py
def _get_cheek_region(key_landmarks, img_width, img_height, cheek='left', landmarks=None):
    """볼 영역 계산"""
    # 구현...
    pass
```

---

#### 3. 새로운 유틸리티 함수 추가
**예**: 새로운 블렌딩 알고리즘

**추가 위치**:
1. `utils.py`: 새로운 함수 추가
2. 필요한 모듈에서 import하여 사용

**코드 예시**:
```python
# utils.py
def _create_gaussian_blend_mask(width, height, sigma=5.0):
    """가우시안 블렌딩 마스크 생성"""
    # 구현...
    pass
```

---

#### 4. 모핑 알고리즘 개선
**예**: 성능 최적화 또는 새로운 모핑 방식

**추가 위치**:
1. `polygon_morphing.py`: `morph_face_by_polygons()` 함수 개선
2. 또는 새로운 모핑 함수 추가

---

## 📝 사용 예시

### 기존 코드 (리팩토링 전과 동일하게 동작)
```python
import utils.face_morphing as face_morphing

# 기존 방식 그대로 사용 가능
result = face_morphing.adjust_eye_size(image, eye_size_ratio=1.5)
result = face_morphing.transform_points_for_eye_size(landmarks, eye_size_ratio=1.5)
result = face_morphing.apply_all_adjustments(image, eye_size=1.5)
```

### 새로운 기능 추가 후 사용
```python
import utils.face_morphing as face_morphing

# 새로 추가한 함수 사용
result = face_morphing.adjust_eyebrow_thickness(image, eyebrow_thickness_ratio=1.2)
```

---

## 🎨 GUI에서 사용하는 방법

### 현재 사용 위치
- `gui/face_edit/morphing.py`: `MorphingManagerMixin`에서 사용
- `gui/face_edit/__init__.py`: `FaceEditPanel`에서 사용

### GUI에 새 기능 추가 시
1. `gui/face_edit/morphing.py`에 UI 추가
2. `utils.face_morphing`에서 새 함수 import
3. 슬라이더나 버튼 이벤트에서 호출

**예시**:
```python
# gui/face_edit/morphing.py
import utils.face_morphing as face_morphing

def _create_eyebrow_tab(self, notebook):
    # 눈썹 두께 슬라이더 추가
    eyebrow_thickness_var = tk.DoubleVar(value=1.0)
    slider = tk.Scale(..., variable=eyebrow_thickness_var)
    
    def on_eyebrow_thickness_change():
        ratio = eyebrow_thickness_var.get()
        result = face_morphing.adjust_eyebrow_thickness(
            self.current_image, 
            eyebrow_thickness_ratio=ratio
        )
        # 결과 표시...
```

---

## 🔧 코드 탐색 팁

### 1. 함수 찾기
```bash
# 특정 함수 검색
grep -r "def adjust_eye_size" utils/face_morphing/

# 함수 사용처 찾기
grep -r "adjust_eye_size" gui/
```

### 2. 모듈 구조 확인
```python
# 공개 API 확인
import utils.face_morphing as fm
print(dir(fm))  # 사용 가능한 함수 목록

# 모듈 구조 확인
import utils.face_morphing
print(utils.face_morphing.__all__)  # 공개 API 목록
```

### 3. 의존성 확인
- `adjustments.py` → `region_extraction.py`, `utils.py`, `constants.py` 사용
- `polygon_morphing.py` → `constants.py` 사용
- `integration.py` → `adjustments.py`, `polygon_morphing.py` 사용

---

## ⚠️ 주의사항

1. **기존 호환성 유지**: `utils/face_morphing.py`가 새 패키지로 리다이렉트하므로 기존 코드는 수정 불필요
2. **공개 API**: `__init__.py`의 `__all__`에 추가해야 외부에서 사용 가능
3. **함수 이름 규칙**: 
   - 이미지 조정: `adjust_*`
   - 포인트 변형: `transform_points_for_*`
   - 포인트 이동: `move_point_*` 또는 `move_points`
4. **예외 처리**: 작업룰 8번 준수 (모든 예외는 로그 출력)

---

## 📚 참고 자료

- 작업 계획서: `specs/task260117_1842.md`
- 기존 리팩토링 사례: `gui/face_extract/` (Mixin 패턴)

---

## 💡 다음 단계

1. **기능 추가 계획 수립**: 어떤 기능을 추가할지 명확히 정의
2. **모듈 선택**: 위 가이드를 참고하여 적절한 모듈 선택
3. **함수 작성**: 기존 함수를 참고하여 일관된 스타일 유지
4. **테스트**: 새 기능 테스트 및 기존 기능 회귀 테스트
5. **문서화**: 함수 docstring 작성 및 필요시 가이드 업데이트
