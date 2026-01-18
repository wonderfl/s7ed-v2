# 랜드마크 상태 관리 분석 문서

**작성 일시**: 2026-01-18 15:21  
**목적**: 랜드마크 관련 데이터의 현재 상태 및 수정 위치 분석

## 1. 랜드마크 변수 정의

### 1.1 주요 변수
- `original_landmarks`: 원본 랜드마크 (읽기 전용, 초기 감지 시 설정)
- `face_landmarks`: 현재 편집된 랜드마크 (표시용)
- `transformed_landmarks`: 변형된 랜드마크 (apply_editing에서 계산)
- `custom_landmarks`: 사용자 수정 랜드마크 (드래그, 슬라이더 등으로 수정)

### 1.2 중앙 포인트 좌표
- `_left_iris_center_coord`: 왼쪽 눈동자 중앙 포인트 좌표 (tuple)
- `_right_iris_center_coord`: 오른쪽 눈동자 중앙 포인트 좌표 (tuple)

## 2. custom_landmarks 수정 위치 상세

### 2.1 polygon_drag_handler.py (2곳)

#### 위치 1: `on_polygon_drag_start` (80줄)
```python
if self.face_landmarks is not None:
    self.custom_landmarks = list(self.face_landmarks)
else:
    self.custom_landmarks = list(landmarks) if landmarks else None
```
**목적**: 드래그 시작 시 초기화  
**조건**: `custom_landmarks`가 None일 때  
**우선순위**: `face_landmarks` > `landmarks`

#### 위치 2: 없음 (이전에 있었던 것으로 보임)

### 2.2 morphing.py (5곳)

#### 위치 1: `update_polygons_only` (611줄)
```python
self.custom_landmarks = list(transformed)
```
**목적**: 폴리곤만 업데이트할 때  
**조건**: `use_landmark_warping`이 True일 때

#### 위치 2: `_apply_common_sliders_to_landmarks` (1457줄)
```python
self.custom_landmarks = final_landmarks
```
**목적**: 공통 슬라이더로 랜드마크 변환 후 업데이트  
**조건**: 고급 모드에서 슬라이더 적용 시

#### 위치 3: `reset_morphing` (1668줄)
```python
self.custom_landmarks = list(self.original_landmarks)
```
**목적**: 초기화 - 원본으로 복원  
**조건**: 리셋 버튼 클릭 시

#### 위치 4: `reset_morphing` (1672줄)
```python
self.custom_landmarks = list(self.face_landmarks)
```
**목적**: 초기화 - face_landmarks로 복원 (폴백)  
**조건**: `original_landmarks`가 없을 때

#### 위치 5: `apply_editing` (1852줄)
```python
if has_size_change:
    self.custom_landmarks = list(transformed_landmarks)
# 사이즈 변경이 없으면 기존 custom_landmarks 유지
```
**목적**: 사이즈 변경 시 업데이트  
**조건**: 사이즈 변경이 있을 때만

### 2.3 polygon_renderer.py (1곳)

#### 위치 1: `_draw_landmark_polygons` (46줄)
```python
self.custom_landmarks = list(landmarks)
```
**목적**: 렌더링 시 초기화  
**조건**: `custom_landmarks`가 None일 때

### 2.4 __init__.py (4곳)

#### 위치 1: 초기화 (196줄)
```python
self.custom_landmarks = None
```
**목적**: 초기값 설정

#### 위치 2: `on_use_landmark_warping_changed` (704줄)
```python
self.custom_landmarks = list(transformed)
```
**목적**: 랜드마크 워핑 활성화 시

#### 위치 3: `on_use_landmark_warping_changed` (721줄)
```python
self.custom_landmarks = None
```
**목적**: 랜드마크 워핑 비활성화 시

#### 위치 4: `on_use_landmark_warping_changed` (762줄, 778줄)
```python
self.custom_landmarks = list(transformed)  # 활성화 시
self.custom_landmarks = None  # 비활성화 시
```
**목적**: 랜드마크 워핑 토글 시

### 2.5 file.py (1곳)

#### 위치 1: `load_image` (194줄)
```python
self.custom_landmarks = None
```
**목적**: 새 이미지 로드 시 초기화

## 3. 변환 순서 플로우

### 3.1 일반적인 편집 플로우
```
1. 이미지 로드
   → original_landmarks 감지
   → custom_landmarks = None

2. 슬라이더 조정 (고급 모드)
   → _apply_common_sliders_to_landmarks 호출
   → custom_landmarks 변환
   → morph_face_by_polygons 호출

3. apply_editing 호출
   → transformed_landmarks 계산 (사이즈 변경)
   → custom_landmarks 업데이트 (사이즈 변경이 있을 때만)
   → morph_face_by_polygons 호출
```

### 3.2 드래그 플로우
```
1. 드래그 시작
   → on_polygon_drag_start
   → custom_landmarks 초기화 (face_landmarks 또는 landmarks)

2. 드래그 중
   → on_polygon_drag
   → custom_landmarks[idx] 업데이트

3. 드래그 종료
   → on_polygon_drag_end
   → apply_polygon_drag_final 호출
   → _apply_common_sliders 호출 (custom_landmarks 변환)
   → morph_face_by_polygons 호출
```

### 3.3 문제가 되는 순서
```
문제 시나리오:
1. _apply_common_sliders_to_landmarks 호출
   → custom_landmarks 변환 (예: size=1.01)

2. apply_editing 호출
   → 사이즈 변경 없음 (left_ratio=1.0, right_ratio=1.0)
   → custom_landmarks 유지 (정상)

3. 하지만 apply_polygon_drag_final에서 확인
   → custom_landmarks가 원본과 같다고 판단
   → "변형된 랜드마크가 없습니다!" 경고
```

## 4. 의존성 관계

### 4.1 변수 간 의존성
```
original_landmarks (원본)
    ↓
face_landmarks (초기 편집)
    ↓
transformed_landmarks (사이즈 변경)
    ↓
custom_landmarks (최종 사용자 수정)
```

### 4.2 함수 호출 의존성
```
apply_editing
    ├─ transform_points_for_eye_size (사이즈 변경)
    ├─ _apply_common_sliders
    │   └─ _apply_common_sliders_to_landmarks (랜드마크 변환)
    └─ morph_face_by_polygons (이미지 변환)

apply_polygon_drag_final
    ├─ _apply_common_sliders
    │   └─ _apply_common_sliders_to_landmarks (랜드마크 변환)
    └─ morph_face_by_polygons (이미지 변환)
```

## 5. 주요 문제점

### 5.1 덮어쓰기 문제
- `apply_editing`에서 `custom_landmarks`를 `transformed_landmarks`로 덮어쓰는 경우
- 사이즈 변경이 없어도 덮어쓰는 경우 (이미 수정됨)

### 5.2 순서 문제
- `apply_polygon_drag_final`에서 `morph_face_by_polygons`를 먼저 호출
- 그 다음 `_apply_common_sliders` 호출
- 변환되지 않은 랜드마크로 이미지 변환됨

### 5.3 상태 불일치
- `custom_landmarks`와 `_left_iris_center_coord`, `_right_iris_center_coord` 불일치 가능
- 중앙 포인트는 좌표 기반, 랜드마크는 인덱스 기반

## 6. 개선 방향

### 6.1 중앙화
- 모든 랜드마크 상태를 `LandmarkManager`에서 관리
- 단일 진실 공급원(Single Source of Truth) 원칙 적용

### 6.2 명확한 인터페이스
- `get_custom_landmarks()`: 현재 사용자 수정 랜드마크 반환
- `apply_transform()`: 변환 적용
- `reset()`: 초기화

### 6.3 상태 추적
- 변경 이력 추적 (선택사항)
- 디버깅을 위한 로그
