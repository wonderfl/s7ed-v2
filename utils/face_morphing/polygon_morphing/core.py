"""
폴리곤 포인트 변형 및 폴리곤 모핑 모듈

이 모듈은 폴리곤 포인트(랜드마크 + 경계 포인트)를 변형하고,
변형된 포인트를 기반으로 폴리곤(삼각형 메시)을 생성하여 
이미지 모핑을 수행합니다.

개념 정의:
- 랜드마크(Landmark): MediaPipe에서 감지된 얼굴 특징점 좌표 리스트 [(x, y), ...] (참조용)
- 폴리곤 포인트(Polygon Points): 실제 모핑에 사용되는 포인트 (랜드마크 + 경계 포인트)
- 폴리곤(Polygon): 폴리곤 포인트를 꼭짓점으로 하는 삼각형 메시 (Delaunay Triangulation)
- 모핑(Morphing): 원본 폴리곤 포인트를 변형된 폴리곤 포인트로 변환하여 이미지를 변형하는 과정

사용 흐름:
1. 랜드마크 감지 (참조용)
2. 폴리곤 포인트 생성 (랜드마크 + 경계 포인트)
3. 폴리곤 포인트 변형: transform_points_* 함수로 포인트 변형
4. 폴리곤 모핑: morph_face_by_polygons 함수로 변형된 포인트를 사용하여 이미지 변형
"""
from dataclasses import dataclass
import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from ..constants import _cv2_available, _cv2_cuda_available, _scipy_available, _landmarks_available, _delaunay_cache, _delaunay_cache_max_size

# 외부 모듈 import
try:
    import cv2
except ImportError:
    cv2 = None

try:
    from scipy.spatial import Delaunay
except ImportError:
    Delaunay = None

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, LEFT_EYE_INDICES, RIGHT_EYE_INDICES
except ImportError:
    detect_face_landmarks = None
    get_key_landmarks = None
    LEFT_EYE_INDICES = []
    RIGHT_EYE_INDICES = []


from .utils import _get_neighbor_points, _check_triangles_flipped

# 공통 로거 헬퍼 (모듈 전역)
try:
    from utils.logger import print_info, print_warning, print_error, print_debug
except ImportError:  # Fallback: IDE나 테스트 환경에서 logger 미존재 시
    def print_info(module, msg):
        print(f"[{module}] {msg}")

    def print_warning(module, msg):
        print(f"[{module}] WARNING: {msg}")

    def print_error(module, msg):
        print(f"[{module}] ERROR: {msg}")

    def print_debug(module, msg):
        print(f"[{module}] DEBUG: {msg}")


@dataclass
class IrisTransformContext:
    """눈동자 및 랜드마크 준비 결과."""

    original_landmarks_no_iris: List[Tuple[float, float]]
    transformed_landmarks_no_iris: List[Tuple[float, float]]
    original_points_array: np.ndarray
    transformed_points_array: np.ndarray
    iris_indices: Sequence[int]
    selected_point_indices: Optional[List[int]]
    left_iris_center_orig: Optional[Tuple[float, float]]
    right_iris_center_orig: Optional[Tuple[float, float]]
    left_iris_center_trans: Optional[Tuple[float, float]]
    right_iris_center_trans: Optional[Tuple[float, float]]


@dataclass
class DelaunayContext:
    """Delaunay 및 바운딩 박스 준비 결과."""

    img_array: Optional[np.ndarray] = None
    working_img: Optional[np.ndarray] = None
    working_width: int = 0
    working_height: int = 0
    min_x: int = 0
    min_y: int = 0
    max_x: int = 0
    max_y: int = 0
    scale_factor: float = 1.0
    tri: Optional['Delaunay'] = None
    original_points_array: Optional[np.ndarray] = None
    transformed_points_array: Optional[np.ndarray] = None
    min_x_orig_bbox: Optional[int] = None
    min_y_orig_bbox: Optional[int] = None
    max_x_orig_bbox: Optional[int] = None
    max_y_orig_bbox: Optional[int] = None
    cached_bbox: Optional[Tuple[int, int, int, int]] = None


@dataclass
class MorphRenderContext:
    """정변환 렌더링에 필요한 사전 계산 값."""

    bbox_width: int = 0
    bbox_height: int = 0
    bbox_total_pixels: int = 0
    pixel_coords_orig_global: Optional[np.ndarray] = None
    simplex_indices_orig: Optional[np.ndarray] = None
    valid_simplex_indices: Optional[np.ndarray] = None


def _validate_and_prepare_inputs(image, original_landmarks, transformed_landmarks):
    """입력 검증 및 전처리
    Args:
        image: PIL.Image 객체
        original_landmarks: 원본 랜드마크 포인트 리스트
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    
    Returns:
        tuple: (img_array, img_width, img_height) 또는 None (검증 실패 시)
    """
    if not _cv2_available:
        return None
    
    if not _scipy_available:
        print("[얼굴모핑] scipy가 설치되지 않았습니다. Delaunay Triangulation을 사용하려면 'pip install scipy'를 실행하세요.")
        return None
    
    if original_landmarks is None or transformed_landmarks is None:
        return None
    
    if len(original_landmarks) != len(transformed_landmarks):
        return None
        
    # PIL Image를 numpy 배열로 변환
    if image.mode != 'RGB':
        img_rgb = image.convert('RGB')
    else:
        img_rgb = image
    img_array = np.array(img_rgb)
    img_height, img_width = img_array.shape[:2]
    
    return (img_array, img_width, img_height)


def clamp_iris_to_eye_region(iris_center_coord, eye_landmarks, img_width, img_height, 
                             margin_ratio=0.3, clamping_enabled=True):
    """눈동자 중심점을 눈 영역 내로 제한 (형태 보존 클램핑)
    
    Args:
        iris_center_coord: 눈동자 중심점 좌표 (x, y)
        eye_landmarks: 눈 랜드마크 포인트 리스트 [(x, y), ...]
        img_width: 이미지 너비
        img_height: 이미지 높이
        margin_ratio: 눈 영역 마진 비율 (0.0 ~ 1.0, 기본값 0.3)
        clamping_enabled: 클램핑 활성화 여부 (기본값 True)
    
    Returns:
        (x, y): 제한된 눈동자 중심점 좌표
    """
    if not clamping_enabled or not eye_landmarks:
        return iris_center_coord
    
    # 눈 영역 바운딩 박스 계산
    x_coords = [pt[0] if isinstance(pt, tuple) else pt.x * img_width for pt in eye_landmarks]
    y_coords = [pt[1] if isinstance(pt, tuple) else pt.y * img_height for pt in eye_landmarks]
    
    if not x_coords or not y_coords:
        return iris_center_coord
    
    min_x = min(x_coords)
    min_y = min(y_coords)
    max_x = max(x_coords)
    max_y = max(y_coords)
    
    # 눈 중심점 계산
    eye_center_x = (min_x + max_x) / 2
    eye_center_y = (min_y + max_y) / 2
    
    # 눈 크기 계산
    eye_width = max_x - min_x
    eye_height = max_y - min_y
    
    # 동적 마진 계산 (눈 크기에 따라 적응)
    # 눈이 작을수록 마진 비율을 줄여 더 넓은 움직임 허용
    adaptive_margin_ratio = margin_ratio * 0.2 * min(1.0, (eye_width + eye_height) / 200.0)
    margin_x = eye_width * adaptive_margin_ratio
    margin_y = eye_height * adaptive_margin_ratio
    
    # 제한된 영역 계산
    clamped_min_x = max(0, min_x - margin_x)
    clamped_min_y = max(0, min_y - margin_y)
    clamped_max_x = min(img_width, max_x + margin_x)
    clamped_max_y = min(img_height, max_y + margin_y)
    
    # 기본 클램핑
    clamped_x = max(clamped_min_x, min(clamped_max_x, iris_center_coord[0]))
    clamped_y = max(clamped_min_y, min(clamped_max_y, iris_center_coord[1]))
    
    # 형태 보존 클램핑: 눈동자가 눈 영역을 벗어날 경우 부드러운 조정
    # 눈 중심으로부터의 거리 계산
    dist_from_center = math.sqrt((clamped_x - eye_center_x)**2 + (clamped_y - eye_center_y)**2)
    
    # 최대 허용 반경 (눈 크기의 120%까지 허용 - 거의 제한 없음)
    max_allowed_radius = min(eye_width, eye_height) * 1.20
    
    if dist_from_center > max_allowed_radius:
        # 비율에 맞춰 부드럽게 조정 (경계에서 멈추는 대신)
        scale = max_allowed_radius / dist_from_center
        
        # 눈 중심을 기준으로 크기 조절
        adjusted_x = eye_center_x + (clamped_x - eye_center_x) * scale
        adjusted_y = eye_center_y + (clamped_y - eye_center_y) * scale
        
        return (adjusted_x, adjusted_y)
    
    return (clamped_x, clamped_y)


def _prepare_iris_centers(original_landmarks, transformed_landmarks,
                         left_iris_center_coord, right_iris_center_coord,
                         left_iris_center_orig, right_iris_center_orig,
                         img_width, img_height, clamping_enabled=True, margin_ratio=0.3,
                         iris_mapping_method="iris_outline", selected_point_indices_param=None,
                         preserve_selected_indices=False) -> IrisTransformContext:    
    """눈동자 포인트 처리 및 중앙 포인트 준비
    Args:
        original_landmarks: 원본 랜드마크 포인트 리스트
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
        left_iris_center_coord: 왼쪽 눈동자 중앙 포인트 좌표 (변형된)
        right_iris_center_coord: 오른쪽 눈동자 중앙 포인트 좌표 (변형된)
        left_iris_center_orig: 왼쪽 눈동자 중앙 포인트 좌표 (원본)
        right_iris_center_orig: 오른쪽 눈동자 중앙 포인트 좌표 (원본)
        img_width: 이미지 너비
        img_height: 이미지 높이
        clamping_enabled: 눈동자 이동 범위 제한 활성화 여부
        margin_ratio: 눈동자 이동 범위 제한 마진 비율
        iris_mapping_method: 눈동자 맵핑 방법 (iris_outline/eye_landmarks)
        selected_point_indices_param: 선택된 포인트 인덱스 (외부에서 전달)
        preserve_selected_indices: True면 전달된 인덱스를 그대로 사용하고 iris 인덱스를 병합하지 않음
    
    Returns:
        tuple: (original_landmarks_no_iris, transformed_landmarks_no_iris,
                original_points_array, transformed_points_array, iris_indices, final_selected_indices)
    """
    
    # 눈동자 포인트 제거 및 중앙 포인트 추가
    # 1. 랜드마크 길이 확인
    original_len = len(original_landmarks) if original_landmarks else 0
    transformed_len = len(transformed_landmarks) if transformed_landmarks else 0
    
    # 디버깅: 랜드마크 길이 확인
    try:
        from utils.logger import print_info, print_warning
    except ImportError:
        def print_info(module, msg):
            print(f"[{module}] {msg}")
        def print_warning(module, msg):
            print(f"[{module}] WARNING: {msg}")
    
    print_info("얼굴모핑", f"_prepare_iris_centers: original_landmarks 길이={original_len}, transformed_landmarks 길이={transformed_len}")
    
    # 2. 길이 불일치 경고
    if original_len != transformed_len:
        print_warning("얼굴모핑", f"랜드마크 길이 불일치: original={original_len}, transformed={transformed_len}")
    
    # 3. 눈동자 인덱스 가져오기
    try:
        from .region_extraction import get_iris_indices
        left_iris_indices, right_iris_indices = get_iris_indices()
        # contour 인덱스 (8개)
        iris_contour_indices = set(left_iris_indices + right_iris_indices)
        # 중심점 인덱스 (2개): 468(왼쪽), 473(오른쪽)
        iris_center_indices = {468, 473}
        # 모든 눈동자 포인트 인덱스 (10개)
        iris_indices = iris_contour_indices | iris_center_indices
    except ImportError:
        # 폴백: 하드코딩된 인덱스 사용
        # 실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472]
        left_iris_indices = [474, 475, 476, 477]
        right_iris_indices = [469, 470, 471, 472]
        iris_contour_indices = set(left_iris_indices + right_iris_indices)
        iris_center_indices = {468, 473}
        iris_indices = iris_contour_indices | iris_center_indices
    
    # 4. 눈동자 포인트 제거 (길이에 따라 조건부 처리)
    if original_len == 478:
        # 478개인 경우: 인덱스로 눈동자 포인트 제거
        original_landmarks_no_iris = [pt for i, pt in enumerate(original_landmarks) if i not in iris_indices]
        print_info("얼굴모핑", f"original_landmarks(478개)에서 눈동자 포인트 제거: {len(original_landmarks_no_iris)}개로 변환")
    elif original_len == 468:
        # 468개인 경우: 이미 눈동자 포인트가 제거된 상태이므로 그대로 사용
        original_landmarks_no_iris = list(original_landmarks)
        print_info("얼굴모핑", f"original_landmarks(468개)는 이미 눈동자 포인트가 제거된 상태")
    else:
        # 예상치 못한 길이: 경고 후 그대로 사용
        print_warning("얼굴모핑", f"original_landmarks의 예상치 못한 길이: {original_len} (예상: 468 또는 478)")
        original_landmarks_no_iris = list(original_landmarks)
    
    if transformed_len == 478:
        # 478개인 경우: 인덱스로 눈동자 포인트 제거
        transformed_landmarks_no_iris = [pt for i, pt in enumerate(transformed_landmarks) if i not in iris_indices]
        print_info("얼굴모핑", f"transformed_landmarks(478개)에서 눈동자 포인트 제거: {len(transformed_landmarks_no_iris)}개로 변환")
    elif transformed_len == 468:
        # 468개인 경우: 이미 눈동자 포인트가 제거된 상태이므로 그대로 사용
        transformed_landmarks_no_iris = list(transformed_landmarks)
        print_info("얼굴모핑", f"transformed_landmarks(468개)는 이미 눈동자 포인트가 제거된 상태")
    else:
        # 예상치 못한 길이: 경고 후 그대로 사용
        print_warning("얼굴모핑", f"transformed_landmarks의 예상치 못한 길이: {transformed_len} (예상: 468 또는 478)")
        transformed_landmarks_no_iris = list(transformed_landmarks)
    
    # 디버깅: 최종 길이 확인
    print_info("얼굴모핑", f"_prepare_iris_centers 결과: original_no_iris={len(original_landmarks_no_iris)}개, transformed_no_iris={len(transformed_landmarks_no_iris)}개")
    
    # 3. 중앙 포인트 계산 또는 전달된 좌표 사용
    # 전달된 좌표는 사용자 관점이므로 MediaPipe 관점으로 변환 필요
    # 원본 랜드마크를 tuple 형태로 변환 (원본 중앙 포인트 계산용)
    original_landmarks_tuple = []
    for i, pt in enumerate(original_landmarks):
        if isinstance(pt, tuple):
            original_landmarks_tuple.append(pt)
        elif hasattr(pt, 'x') and hasattr(pt, 'y'):
            original_landmarks_tuple.append((pt.x * img_width, pt.y * img_height))
        else:
            original_landmarks_tuple.append(pt)
    
    transformed_landmarks_tuple = []
    for i, pt in enumerate(transformed_landmarks):
        if isinstance(pt, tuple):
            transformed_landmarks_tuple.append(pt)
        elif hasattr(pt, 'x') and hasattr(pt, 'y'):
            transformed_landmarks_tuple.append((pt.x * img_width, pt.y * img_height))
        else:
            transformed_landmarks_tuple.append(pt)
    
    # 중앙 포인트 계산 함수 정의
    def _calculate_iris_centers_from_contour(landmarks_tuple, left_iris_indices, right_iris_indices, img_w, img_h):
        """contour 포인트의 평균으로 중앙 포인트 계산 (IRIS_OUTLINE 방식)"""
        # 왼쪽 눈동자 중앙 포인트 계산
        left_iris_points = []
        for idx in left_iris_indices:
            if idx < len(landmarks_tuple):
                pt = landmarks_tuple[idx]
                if isinstance(pt, tuple):
                    left_iris_points.append(pt)
                elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                    left_iris_points.append((pt.x * img_w, pt.y * img_h))
        
        # 오른쪽 눈동자 중앙 포인트 계산
        right_iris_points = []
        for idx in right_iris_indices:
            if idx < len(landmarks_tuple):
                pt = landmarks_tuple[idx]
                if isinstance(pt, tuple):
                    right_iris_points.append(pt)
                elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                    right_iris_points.append((pt.x * img_w, pt.y * img_h))
        
        # 평균 계산
        if left_iris_points:
            left_center = (sum(p[0] for p in left_iris_points) / len(left_iris_points),
                          sum(p[1] for p in left_iris_points) / len(left_iris_points))
        else:
            left_center = None
            
        if right_iris_points:
            right_center = (sum(p[0] for p in right_iris_points) / len(right_iris_points),
                           sum(p[1] for p in right_iris_points) / len(right_iris_points))
        else:
            right_center = None
            
        return left_center, right_center
    
    def _calculate_iris_centers_from_eye_landmarks(landmarks_tuple, img_w, img_h):
        """눈 랜드마크 기반 중앙 포인트 계산 (EYE_LANDMARKS 방식)"""
        # 468개 랜드마크 구조에 맞는 눈 랜드마크 인덱스 사용
        LEFT_EYE_INDICES_468 = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        RIGHT_EYE_INDICES_468 = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        # 왼쪽 눈 랜드마크 중앙 계산
        left_eye_points = []
        for idx in LEFT_EYE_INDICES_468:
            if idx < len(landmarks_tuple):
                pt = landmarks_tuple[idx]
                if isinstance(pt, tuple):
                    left_eye_points.append(pt)
                elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                    left_eye_points.append((pt.x * img_w, pt.y * img_h))
        
        # 오른쪽 눈 랜드마크 중앙 계산
        right_eye_points = []
        for idx in RIGHT_EYE_INDICES_468:
            if idx < len(landmarks_tuple):
                pt = landmarks_tuple[idx]
                if isinstance(pt, tuple):
                    right_eye_points.append(pt)
                elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                    right_eye_points.append((pt.x * img_w, pt.y * img_h))
        
        # 평균 계산
        if left_eye_points:
            left_center = (sum(p[0] for p in left_eye_points) / len(left_eye_points),
                          sum(p[1] for p in left_eye_points) / len(left_eye_points))
        else:
            left_center = None
            
        if right_eye_points:
            right_center = (sum(p[0] for p in right_eye_points) / len(right_eye_points),
                           sum(p[1] for p in right_eye_points) / len(right_eye_points))
        else:
            right_center = None
            
        return left_center, right_center
    
    # 디버깅: 전달된 중앙 포인트 좌표 확인
    try:
        from utils.logger import print_info
    except ImportError:
        def print_info(module, msg):
            print(f"[{module}] {msg}")
    
    print_info("얼굴모핑", f"morph_face_by_polygons 호출: left_iris_center_coord={left_iris_center_coord}, right_iris_center_coord={right_iris_center_coord}")
    print_info("얼굴모핑", f"원본 중앙 포인트: left_orig={left_iris_center_orig}, right_orig={right_iris_center_orig}")
    print_info("얼굴모핑", f"맵핑 방법: {iris_mapping_method}")
    
    # 맵핑 방법에 따라 원본 중앙 포인트 계산
    if left_iris_center_orig is None or right_iris_center_orig is None:
        if iris_mapping_method == "eye_landmarks":
            # 눈 랜드마크 기반 계산
            calculated_left_orig, calculated_right_orig = _calculate_iris_centers_from_eye_landmarks(
                original_landmarks_tuple, img_width, img_height
            )
            print_info("얼굴모핑", f"[EYE_LANDMARKS] 계산된 원본 중앙: left={calculated_left_orig}, right={calculated_right_orig}")
            if left_iris_center_orig is None:
                left_iris_center_orig = calculated_left_orig
            if right_iris_center_orig is None:
                right_iris_center_orig = calculated_right_orig
        else:
            # 기본 방식 (iris_outline): 눈동자 외곽선 기반 계산
            # 정확한 눈동자 외곽선 4개 포인트만 사용
            left_iris_indices = [474, 475, 476, 477]  # 왼쪽 눈동자 외곽선
            right_iris_indices = [469, 470, 471, 472]  # 오른쪽 눈동자 외곽선
            
            calculated_left_orig, calculated_right_orig = _calculate_iris_centers_from_contour(
                original_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height
            )
            print_info("얼굴모핑", f"[IRIS_OUTLINE] 계산된 원본 중앙: left={calculated_left_orig}, right={calculated_right_orig}")
            if left_iris_center_orig is None:
                left_iris_center_orig = calculated_left_orig
            if right_iris_center_orig is None:
                right_iris_center_orig = calculated_right_orig
    
    print_info("얼굴모핑", f"[최종] 사용된 원본 중앙: left={left_iris_center_orig}, right={right_iris_center_orig}")
    
    # 맵핑 방법에 따라 변형할 랜드마크 인덱스 결정 (선택적 변형과 무관하게 항상 적용)
    iris_mapping_indices = []
    if iris_mapping_method == "eye_landmarks":
        # 눈 랜드마크 전체 포함 (468개 랜드마크 구조에 맞는 인덱스만 사용)
        LEFT_EYE_INDICES_468 = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        RIGHT_EYE_INDICES_468 = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        iris_mapping_indices = LEFT_EYE_INDICES_468 + RIGHT_EYE_INDICES_468
        print_info("얼굴모핑", f"[EYE_LANDMARKS] 변형 인덱스: {len(iris_mapping_indices)}개 (왼쪽{len(LEFT_EYE_INDICES_468)}+오른쪽{len(RIGHT_EYE_INDICES_468)})")
    else:
        # 눈동자 외곽선만 포함 (진짜 눈동자 외곽선 4개 포인트만 사용)
        # 468개 구조에서 눈동자 외곽선에 가장 가까운 인덱스들
        LEFT_EYE_INDICES_468 = [33, 133, 145, 246]  # 왼쪽 눈동자 외곽선 4개
        RIGHT_EYE_INDICES_468 = [362, 398, 384, 263]  # 오른쪽 눈동자 외곽선 4개
        iris_mapping_indices = LEFT_EYE_INDICES_468 + RIGHT_EYE_INDICES_468
        print_info("얼굴모핑", f"[IRIS_OUTLINE] 변형 인덱스: {len(iris_mapping_indices)}개 (왼쪽{len(LEFT_EYE_INDICES_468)}+오른쪽{len(RIGHT_EYE_INDICES_468)})")
    
    final_selected_indices = selected_point_indices_param
    if preserve_selected_indices and final_selected_indices:
        # 전달된 인덱스를 그대로 사용 (순서 유지)
        final_selected_indices = list(dict.fromkeys(final_selected_indices))
        print_info("얼굴모핑", f"[DEBUG] preserve_selected_indices 적용: 전달된 인덱스 {len(final_selected_indices)}개만 사용")
    else:
        # selected_point_indices_param가 None이거나 비어있으면 iris_mapping_indices를 사용
        if final_selected_indices is None or len(final_selected_indices) == 0:
            final_selected_indices = iris_mapping_indices
            print_info("얼굴모핑", f"[DEBUG] selected_point_indices_param가 None이어서 iris_mapping_indices로 대체: {len(iris_mapping_indices)}개")
        else:
            # 기존 selected_point_indices_param와 병합 (중복 제거)
            merged_indices = set(final_selected_indices)
            merged_indices.update(iris_mapping_indices)
            final_selected_indices = list(merged_indices)
            print_info("얼굴모핑", f"[DEBUG] 기존 인덱스와 iris_mapping_indices 병합: {len(final_selected_indices)}개")
    
    selected_point_indices_param = final_selected_indices
    print_info("얼굴모핑", f"[DEBUG] 최종 selected_point_indices_param: {selected_point_indices_param[:10]}... (총 {len(selected_point_indices_param)}개)")
    
    # 선택된 포인트가 없으면 전체 변형 사용
    if not selected_point_indices_param:
        selected_point_indices_param = None
        print_info("얼굴모핑", f"[DEBUG] 선택된 포인트 없음, 전체 변형 사용")
    
    if left_iris_center_coord is not None and right_iris_center_coord is not None:
        # 전달된 좌표는 변형된 중앙 포인트 (드래그로 변경된 좌표)
        print_info("얼굴모핑", "중앙 포인트 사용: 변형 좌표가 전달됨")
        # morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저 (len-2), MediaPipe RIGHT_IRIS 나중 (len-1)
        # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
        # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
        # 따라서: 사용자 왼쪽 = MediaPipe LEFT_IRIS, 사용자 오른쪽 = MediaPipe RIGHT_IRIS
        left_iris_center_trans = left_iris_center_coord  # 변형된 중앙 포인트 (사용자 왼쪽 = MediaPipe LEFT_IRIS)
        right_iris_center_trans = right_iris_center_coord  # 변형된 중앙 포인트 (사용자 오른쪽 = MediaPipe RIGHT_IRIS)
        
        # 클램핑 적용: 눈 영역 내로 제한
        if clamping_enabled:
            try:
                from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
                # 왼쪽 눈 랜드마크 추출
                left_eye_landmarks = []
                for idx in LEFT_EYE_INDICES:
                    if idx < len(transformed_landmarks_tuple):
                        pt = transformed_landmarks_tuple[idx]
                        if isinstance(pt, tuple):
                            left_eye_landmarks.append(pt)
                        elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                            left_eye_landmarks.append((pt.x * img_width, pt.y * img_height))
                
                # 오른쪽 눈 랜드마크 추출
                right_eye_landmarks = []
                for idx in RIGHT_EYE_INDICES:
                    if idx < len(transformed_landmarks_tuple):
                        pt = transformed_landmarks_tuple[idx]
                        if isinstance(pt, tuple):
                            right_eye_landmarks.append(pt)
                        elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                            right_eye_landmarks.append((pt.x * img_width, pt.y * img_height))
                
                # 클램핑 적용
                if left_eye_landmarks:
                    left_iris_center_trans = clamp_iris_to_eye_region(
                        left_iris_center_trans, left_eye_landmarks, img_width, img_height,
                        margin_ratio=margin_ratio, clamping_enabled=clamping_enabled
                    )
                if right_eye_landmarks:
                    right_iris_center_trans = clamp_iris_to_eye_region(
                        right_iris_center_trans, right_eye_landmarks, img_width, img_height,
                        margin_ratio=margin_ratio, clamping_enabled=clamping_enabled
                    )
            except ImportError:
                # LEFT_EYE_INDICES, RIGHT_EYE_INDICES를 가져올 수 없으면 클램핑 건너뜀
                pass
        
        # 원본 중앙 포인트: 파라미터로 전달된 값이 있으면 사용, 없으면 계산 시도
        if left_iris_center_orig is None or right_iris_center_orig is None:
            # original_landmarks에서 계산 시도 (468개 구조에서는 실패할 수 있음)
            calculated_left_orig, calculated_right_orig = _calculate_iris_centers_from_contour(
                original_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height)
            if left_iris_center_orig is None:
                left_iris_center_orig = calculated_left_orig
            if right_iris_center_orig is None:
                right_iris_center_orig = calculated_right_orig
            
            # 계산 실패 시 변형된 중앙 포인트를 원본으로 사용 (폴백)
            if left_iris_center_orig is None:
                left_iris_center_orig = left_iris_center_trans
            if right_iris_center_orig is None:
                right_iris_center_orig = right_iris_center_trans
        
        # 원본 중앙 포인트 좌표가 현재 이미지 크기를 벗어나면 스케일링 및 오프셋 조정 필요
        # 원본 랜드마크의 좌표 범위를 확인하여 원본 이미지 크기 및 오프셋 추정
        if left_iris_center_orig is not None and right_iris_center_orig is not None:
            if original_landmarks_tuple:
                # 원본 랜드마크의 최소/최대 좌표로 원본 이미지 크기 및 오프셋 추정
                min_x_orig = min(pt[0] for pt in original_landmarks_tuple)
                min_y_orig = min(pt[1] for pt in original_landmarks_tuple)
                max_x_orig = max(pt[0] for pt in original_landmarks_tuple)
                max_y_orig = max(pt[1] for pt in original_landmarks_tuple)
                
                # 원본 이미지 크기 추정 (랜드마크 범위 + 여유)
                margin = 10
                orig_img_width = max(max_x_orig - min_x_orig + margin * 2, img_width)
                orig_img_height = max(max_y_orig - min_y_orig + margin * 2, img_height)
                
                # 오프셋 계산 (원본 랜드마크의 최소 좌표가 0이 아닌 경우)
                offset_x = min_x_orig - margin if min_x_orig > margin else 0
                offset_y = min_y_orig - margin if min_y_orig > margin else 0
                
                # 중심점이 이미지 범위 안에 있는지 확인
                left_in_bounds = (0 <= left_iris_center_orig[0] <= img_width and 0 <= left_iris_center_orig[1] <= img_height)
                right_in_bounds = (0 <= right_iris_center_orig[0] <= img_width and 0 <= right_iris_center_orig[1] <= img_height)
                
                # 원본 중심점이 현재 이미지 크기를 벗어나는지 확인
                # 중요: 중심점이 이미지 범위 안에 있으면 스케일링 불필요!
                needs_adjustment = (not left_in_bounds or not right_in_bounds or
                                   abs(orig_img_width - img_width) > 1.0 or abs(orig_img_height - img_height) > 1.0)
                
                if needs_adjustment and orig_img_width > 0 and orig_img_height > 0:
                    # 스케일 비율 계산
                    scale_x = img_width / orig_img_width
                    scale_y = img_height / orig_img_height
                    
                    # 원본 중심점: 오프셋 적용 후 스케일링 (원본 이미지 좌표계 -> 현재 이미지 좌표계)
                    left_iris_center_orig_offset = (left_iris_center_orig[0] - offset_x, left_iris_center_orig[1] - offset_y)
                    right_iris_center_orig_offset = (right_iris_center_orig[0] - offset_x, right_iris_center_orig[1] - offset_y)
                    left_iris_center_orig_scaled = (left_iris_center_orig_offset[0] * scale_x, left_iris_center_orig_offset[1] * scale_y)
                    right_iris_center_orig_scaled = (right_iris_center_orig_offset[0] * scale_x, right_iris_center_orig_offset[1] * scale_y)
                    
                    # 변형된 중심점도 동일한 좌표계로 맞춤 (원본과 같은 변환 적용)
                    # 중요: 원본과 변형된 중심점이 같은 좌표계를 사용해야 Delaunay Triangulation이 정상 작동
                    left_iris_center_trans_offset = (left_iris_center_trans[0] - offset_x, left_iris_center_trans[1] - offset_y)
                    right_iris_center_trans_offset = (right_iris_center_trans[0] - offset_x, right_iris_center_trans[1] - offset_y)
                    left_iris_center_trans_scaled = (left_iris_center_trans_offset[0] * scale_x, left_iris_center_trans_offset[1] * scale_y)
                    right_iris_center_trans_scaled = (right_iris_center_trans_offset[0] * scale_x, right_iris_center_trans_offset[1] * scale_y)
                    
                    left_iris_center_orig = left_iris_center_orig_scaled
                    right_iris_center_orig = right_iris_center_orig_scaled
                    left_iris_center_trans = left_iris_center_trans_scaled
                    right_iris_center_trans = right_iris_center_trans_scaled
            else:
                # original_landmarks_tuple이 없으면 스케일링만 수행 (오프셋 없음)
                # 원본 중심점이 현재 이미지 크기를 벗어나는지 확인
                needs_scaling = (left_iris_center_orig[0] > img_width or left_iris_center_orig[1] > img_height or
                                right_iris_center_orig[0] > img_width or right_iris_center_orig[1] > img_height)
                
                if needs_scaling:
                    # 원본 이미지 크기를 중심점 좌표로 추정
                    max_x_orig = max(left_iris_center_orig[0], right_iris_center_orig[0])
                    max_y_orig = max(left_iris_center_orig[1], right_iris_center_orig[1])
                    orig_img_width = max(max_x_orig * 1.1, img_width)
                    orig_img_height = max(max_y_orig * 1.1, img_height)
                    
                    if orig_img_width > 0 and orig_img_height > 0:
                        # 스케일 비율 계산
                        scale_x = img_width / orig_img_width
                        scale_y = img_height / orig_img_height
                        
                        # 원본 중심점 좌표를 현재 이미지 크기에 맞게 스케일링
                        left_iris_center_orig_scaled = (left_iris_center_orig[0] * scale_x, left_iris_center_orig[1] * scale_y)
                        right_iris_center_orig_scaled = (right_iris_center_orig[0] * scale_x, right_iris_center_orig[1] * scale_y)
                        
                        left_iris_center_orig = left_iris_center_orig_scaled
                        right_iris_center_orig = right_iris_center_orig_scaled
    else:
        # 파라미터로 전달되지 않은 경우: 계산으로 중앙 포인트 구하기
        print_info("얼굴모핑", "중앙 포인트 계산: 파라미터로 전달되지 않아 계산으로 구함")
        left_iris_center_orig, right_iris_center_orig = _calculate_iris_centers_from_contour(
            original_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height)
        left_iris_center_trans, right_iris_center_trans = _calculate_iris_centers_from_contour(
            transformed_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height)
        print_info("얼굴모핑", f"계산된 중앙 포인트: 원본 left={left_iris_center_orig}, right={right_iris_center_orig}")
        print_info("얼굴모핑", f"계산된 중앙 포인트: 변형 left={left_iris_center_trans}, right={right_iris_center_trans}")
    
    # 4. 중앙 포인트 추가 (morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저, MediaPipe RIGHT_IRIS 나중)
    if left_iris_center_orig is not None and right_iris_center_orig is not None:
        # landmarks[468] = LEFT_EYE_INDICES에서 계산된 중심
        # landmarks[469] = RIGHT_EYE_INDICES에서 계산된 중심
        original_landmarks_no_iris.append(left_iris_center_orig)   # landmarks[468]
        original_landmarks_no_iris.append(right_iris_center_orig)  # landmarks[469]
        transformed_landmarks_no_iris.append(left_iris_center_trans)
        transformed_landmarks_no_iris.append(right_iris_center_trans)
        
        # 중앙 포인트 이동 거리 계산 (중앙 포인트가 실제로 변경되었을 때만 로그 출력)
        left_displacement = np.sqrt((left_iris_center_trans[0] - left_iris_center_orig[0])**2 + 
                                   (left_iris_center_trans[1] - left_iris_center_orig[1])**2)
        right_displacement = np.sqrt((right_iris_center_trans[0] - right_iris_center_orig[0])**2 + 
                                    (right_iris_center_trans[1] - right_iris_center_orig[1])**2)
    
    # 이미지 경계 포인트 추가 (Delaunay Triangulation을 위해)
    # 경계 포인트: 4개 모서리
    # 경계 포인트는 바운딩 박스 경계 근처의 픽셀이 삼각형을 찾을 수 있도록 필요
    margin = 10
    boundary_points = [
        (-margin, -margin),  # 왼쪽 위
        (img_width + margin, -margin),  # 오른쪽 위
        (img_width + margin, img_height + margin),  # 오른쪽 아래
        (-margin, img_height + margin)  # 왼쪽 아래
    ]
    
    # 모든 포인트 결합 (변환된 랜드마크 + 경계)
    all_original_points = list(original_landmarks_no_iris) + boundary_points
    all_transformed_points = list(transformed_landmarks_no_iris) + boundary_points
    
    # numpy 배열로 변환
    original_points_array = np.array(all_original_points, dtype=np.float32)
    transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
    
    # 포인트 이동 거리 검증: 너무 많이 이동한 포인트가 있는지 확인
    # 중앙 포인트를 포함한 전체 랜드마크 확인
    max_displacement = 0.0
    max_displacement_idx = -1
    landmarks_count_for_check = len(original_landmarks_no_iris)  # 중앙 포인트 포함
    
    # 이동 거리 상세 로그 (중앙 포인트 포함)
    displacement_details = []
    for i in range(landmarks_count_for_check):
        if i < len(original_landmarks_no_iris) and i < len(transformed_landmarks_no_iris):
            orig_pt = original_landmarks_no_iris[i]
            trans_pt = transformed_landmarks_no_iris[i]
            displacement = np.sqrt((trans_pt[0] - orig_pt[0])**2 + (trans_pt[1] - orig_pt[1])**2)
            if displacement > max_displacement:
                max_displacement = displacement
                max_displacement_idx = i
    
    # 이미지 대각선 길이의 30%를 초과하면 경고
    image_diagonal = np.sqrt(img_width**2 + img_height**2)
    max_allowed_displacement = image_diagonal * 0.3
    
    if max_displacement > max_allowed_displacement:
        # 과도하게 이동한 포인트를 제한 (허용치의 1.2배까지만 허용)
        # 중앙 포인트를 포함한 전체 랜드마크에 대해 제한 적용
        if max_displacement > max_allowed_displacement * 1.2:
            scale_factor_limit = max_allowed_displacement * 1.2 / max_displacement
            for i in range(len(original_landmarks_no_iris)):
                if i < len(original_landmarks_no_iris) and i < len(transformed_landmarks_no_iris):
                    orig_pt = original_landmarks_no_iris[i]
                    trans_pt = transformed_landmarks_no_iris[i]
                    displacement = np.sqrt((trans_pt[0] - orig_pt[0])**2 + (trans_pt[1] - orig_pt[1])**2)
                    if displacement > max_allowed_displacement * 1.2:
                        # 이동 거리를 제한
                        dx = trans_pt[0] - orig_pt[0]
                        dy = trans_pt[1] - orig_pt[1]
                        limited_dx = dx * scale_factor_limit
                        limited_dy = dy * scale_factor_limit
                        transformed_landmarks_no_iris[i] = (orig_pt[0] + limited_dx, orig_pt[1] + limited_dy)
            
            # 제한된 랜드마크로 배열 재생성 (중앙 포인트 포함)
            all_transformed_points = list(transformed_landmarks_no_iris) + boundary_points
            transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
    
    return IrisTransformContext(
        original_landmarks_no_iris=original_landmarks_no_iris,
        transformed_landmarks_no_iris=transformed_landmarks_no_iris,
        original_points_array=original_points_array,
        transformed_points_array=transformed_points_array,
        iris_indices=tuple(iris_indices),
        selected_point_indices=selected_point_indices_param,
        left_iris_center_orig=left_iris_center_orig,
        right_iris_center_orig=right_iris_center_orig,
        left_iris_center_trans=left_iris_center_trans,
        right_iris_center_trans=right_iris_center_trans,
    )


def _create_delaunay_triangulation(original_points_array):
    """Delaunay Triangulation 생성 및 캐싱
    
    Args:
        original_points_array: 원본 포인트 배열 (numpy array)
    
    Returns:
        tri: Delaunay Triangulation 객체
    """
    # Delaunay Triangulation 캐싱 (성능 최적화)
    # 랜드마크 포인트의 해시를 키로 사용
    cache_key = hash(tuple(map(tuple, original_points_array)))
    
    if cache_key in _delaunay_cache:
        tri = _delaunay_cache[cache_key]
    else:
        # scipy.spatial.Delaunay를 사용한 Delaunay Triangulation
        tri = Delaunay(original_points_array)
        
        # 캐시 크기 제한 (LRU 방식)
        if len(_delaunay_cache) >= _delaunay_cache_max_size:
            # 가장 오래된 항목 제거 (간단하게 첫 번째 항목 제거)
            oldest_key = next(iter(_delaunay_cache))
            del _delaunay_cache[oldest_key]
        
        _delaunay_cache[cache_key] = tri
    
    return tri


def _check_and_fix_flipped_triangles(original_points_array, transformed_points_array, tri, original_landmarks_no_iris):
    """뒤집힌 삼각형 검사 및 수정
    
    Args:
        original_points_array: 원본 포인트 배열
        transformed_points_array: 변형된 포인트 배열 (수정될 수 있음)
        tri: Delaunay Triangulation 객체
        original_landmarks_no_iris: 원본 랜드마크 (경계 포인트 제외, 중앙 포인트 포함)
    
    Returns:
        transformed_points_array: 수정된 변형된 포인트 배열
    """
    # 뒤집힌 삼각형 검사 및 변형 조정 (스케일 조정 전에 수행)
    # 눈 랜드마크는 항상 완전히 변형하고, 문제가 있는 주변 포인트만 선택적으로 조정
    from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
    
    # 눈 랜드마크 인덱스 (변형 강도 조정 대상에서 제외)
    eye_indices_set = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
    # 경계 포인트도 제외 (경계 포인트는 항상 원본 유지)
    boundary_start_idx = len(original_landmarks_no_iris)
    boundary_indices_set = set(range(boundary_start_idx, len(original_points_array)))
    # 중심점 인덱스 (468, 469) - 뒤집힌 삼각형 복원에서 제외
    iris_center_indices_set = {len(original_landmarks_no_iris) - 2, len(original_landmarks_no_iris) - 1}
    protected_indices = eye_indices_set | boundary_indices_set | iris_center_indices_set
    
    # 뒤집힌 삼각형 검사 (반복 검사 제거: 사용자가 폴리곤에서 이미 확인하고 수정했을 것으로 가정)
    # 단순히 뒤집힌 삼각형이 있는지 확인하고 경고만 출력
    flipped_count, flipped_indices, problematic_point_indices, neighbor_point_indices = _check_triangles_flipped(original_points_array, transformed_points_array, tri)
    
    if flipped_count > 0:
        # 뒤집힌 삼각형이 있으면 문제 포인트를 원본으로 복원 (눈 랜드마크, 중심점, 경계 포인트는 제외)
        restored_count = 0
        skipped_iris_centers = []
        for point_idx in problematic_point_indices:
            if point_idx not in protected_indices and point_idx < len(original_points_array):
                transformed_points_array[point_idx] = original_points_array[point_idx].copy()
                restored_count += 1
            elif point_idx in iris_center_indices_set:
                skipped_iris_centers.append(point_idx)        

    return transformed_points_array

def _calculate_landmark_bounding_box(landmarks, img_width, img_height, padding_ratio=0.3, exclude_indices=None):
    """랜드마크 바운딩 박스 계산
    
    Args:
        landmarks: 랜드마크 포인트 리스트 (얼굴 전체 랜드마크)
        img_width: 이미지 너비
        img_height: 이미지 높이
        padding_ratio: 패딩 비율 (기본 30%, 변형 시 확장 고려)
        exclude_indices: 제외할 인덱스 집합 (복사본 생성 없이 필터링)
    
    Returns:
        (min_x, min_y, max_x, max_y): 바운딩 박스 좌표 또는 None
    """
    if not landmarks:
        return None
    
    # 랜드마크 좌표 추출 (복사본 생성 없이 인덱스로 직접 접근)
    x_coords = []
    y_coords = []
    exclude_set = exclude_indices if exclude_indices is not None else set()
    for i, pt in enumerate(landmarks):
        if i in exclude_set:
            continue
        if isinstance(pt, tuple) and len(pt) >= 2:
            x_coords.append(pt[0])
            y_coords.append(pt[1])
        elif hasattr(pt, 'x') and hasattr(pt, 'y'):
            x_coords.append(pt.x * img_width)
            y_coords.append(pt.y * img_height)
    
    if not x_coords or not y_coords:
        return None
    
    min_x = max(0, int(min(x_coords)))
    min_y = max(0, int(min(y_coords)))
    max_x = min(img_width, int(max(x_coords)))
    max_y = min(img_height, int(max(y_coords)))
    
    # 패딩 추가 (변형 시 영역 확장 고려, 얼굴 전체 포함을 위해 30%로 증가)
    width = max_x - min_x
    height = max_y - min_y
    padding_x = int(width * padding_ratio)
    padding_y = int(height * padding_ratio)
    
    min_x = max(0, min_x - padding_x)
    min_y = max(0, min_y - padding_y)
    max_x = min(img_width, max_x + padding_x)
    max_y = min(img_height, max_y + padding_y)
    
    return (min_x, min_y, max_x, max_y)    


def _prepare_delaunay_context(*, img_array, img_width, img_height,
                              iris_ctx: IrisTransformContext,
                              cached_original_bbox=None) -> DelaunayContext:
    """Create Delaunay triangulation and working image context."""

    ctx = DelaunayContext(
        img_array=img_array,
        working_img=img_array,
        working_width=img_width,
        working_height=img_height,
        scale_factor=1.0,
        original_points_array=iris_ctx.original_points_array,
        transformed_points_array=iris_ctx.transformed_points_array,
        cached_bbox=cached_original_bbox,
    )

    ctx.tri = _create_delaunay_triangulation(ctx.original_points_array)

    original_landmarks_no_iris = iris_ctx.original_landmarks_no_iris
    transformed_landmarks_no_iris = iris_ctx.transformed_landmarks_no_iris

    if cached_original_bbox is not None:
        bbox_orig = cached_original_bbox
    else:
        bbox_orig = _calculate_landmark_bounding_box(original_landmarks_no_iris, img_width, img_height, padding_ratio=0.5)

    bbox_trans = _calculate_landmark_bounding_box(transformed_landmarks_no_iris, img_width, img_height, padding_ratio=0.5)

    if bbox_orig and bbox_trans:
        min_x = min(bbox_orig[0], bbox_trans[0])
        min_y = min(bbox_orig[1], bbox_trans[1])
        max_x = max(bbox_orig[2], bbox_trans[2])
        max_y = max(bbox_orig[3], bbox_trans[3])
        try:
            print_info("얼굴모핑", f"bbox_orig={bbox_orig}, bbox_trans={bbox_trans}")
        except NameError:
            pass

        ctx.min_x_orig_bbox = min_x
        ctx.min_y_orig_bbox = min_y
        ctx.max_x_orig_bbox = max_x
        ctx.max_y_orig_bbox = max_y

        bbox_width = max_x - min_x
        bbox_height = max_y - min_y
        bbox_max_dimension = max(bbox_width, bbox_height)

        max_dimension = 1000
        scale_factor = 1.0
        working_img = img_array
        working_width = img_width
        working_height = img_height

        if bbox_max_dimension > max_dimension:
            scale_factor = max_dimension / bbox_max_dimension
            working_width = int(img_width * scale_factor)
            working_height = int(img_height * scale_factor)
            if _cv2_cuda_available:
                try:
                    gpu_img = cv2.cuda_GpuMat()
                    gpu_img.upload(img_array)
                    gpu_resized = cv2.cuda.resize(gpu_img, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
                    working_img = gpu_resized.download()
                except Exception:
                    working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
            else:
                working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)

            original_points_array_scaled = ctx.original_points_array * scale_factor
            transformed_points_array_scaled = ctx.transformed_points_array * scale_factor
            ctx.tri = Delaunay(original_points_array_scaled)
            ctx.original_points_array = original_points_array_scaled
            ctx.transformed_points_array = transformed_points_array_scaled

            min_x = int(min_x * scale_factor)
            min_y = int(min_y * scale_factor)
            max_x = int(max_x * scale_factor)
            max_y = int(max_y * scale_factor)
        ctx.scale_factor = scale_factor
        ctx.working_img = working_img
        ctx.working_width = working_width
        ctx.working_height = working_height
        ctx.min_x = min_x
        ctx.min_y = min_y
        ctx.max_x = max_x
        ctx.max_y = max_y
    else:
        ctx.min_x = 0
        ctx.min_y = 0
        ctx.max_x = img_width
        ctx.max_y = img_height
        ctx.min_x_orig_bbox = 0
        ctx.min_y_orig_bbox = 0
        ctx.max_x_orig_bbox = img_width
        ctx.max_y_orig_bbox = img_height

        max_dimension = 1024
        scale_factor = 1.0
        working_img = img_array
        working_width = img_width
        working_height = img_height

        if max(img_width, img_height) > max_dimension:
            scale_factor = max_dimension / max(img_width, img_height)
            working_width = int(img_width * scale_factor)
            working_height = int(img_height * scale_factor)
            if _cv2_cuda_available:
                try:
                    gpu_img = cv2.cuda_GpuMat()
                    gpu_img.upload(img_array)
                    gpu_resized = cv2.cuda.resize(gpu_img, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
                    working_img = gpu_resized.download()
                except Exception:
                    working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
            else:
                working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)

            original_points_array_scaled = ctx.original_points_array * scale_factor
            transformed_points_array_scaled = ctx.transformed_points_array * scale_factor
            ctx.tri = Delaunay(original_points_array_scaled)
            ctx.original_points_array = original_points_array_scaled
            ctx.transformed_points_array = transformed_points_array_scaled

            ctx.max_x = working_width
            ctx.max_y = working_height

        ctx.scale_factor = scale_factor
        ctx.working_img = working_img
        ctx.working_width = working_width
        ctx.working_height = working_height

    return ctx


def _build_pixel_coordinate_map(ctx: DelaunayContext) -> MorphRenderContext:
    """Pre-compute pixel coordinate grids and simplex indices."""

    render_ctx = MorphRenderContext()
    if ctx.tri is None:
        return render_ctx

    bbox_width = ctx.max_x - ctx.min_x
    bbox_height = ctx.max_y - ctx.min_y
    render_ctx.bbox_width = bbox_width
    render_ctx.bbox_height = bbox_height
    bbox_total_pixels = bbox_width * bbox_height
    render_ctx.bbox_total_pixels = bbox_total_pixels

    y_coords_orig, x_coords_orig = np.mgrid[ctx.min_y:ctx.max_y, ctx.min_x:ctx.max_x]
    pixel_coords_orig_global = np.column_stack([x_coords_orig.ravel(), y_coords_orig.ravel()])
    render_ctx.pixel_coords_orig_global = pixel_coords_orig_global

    chunk_size = 100000
    if bbox_total_pixels > chunk_size:
        simplex_indices_orig = np.full(bbox_total_pixels, -1, dtype=np.int32)
        for chunk_start in range(0, bbox_total_pixels, chunk_size):
            chunk_end = min(chunk_start + chunk_size, bbox_total_pixels)
            chunk_coords = pixel_coords_orig_global[chunk_start:chunk_end]
            simplex_indices_orig[chunk_start:chunk_end] = ctx.tri.find_simplex(chunk_coords)
    else:
        simplex_indices_orig = ctx.tri.find_simplex(pixel_coords_orig_global)

    render_ctx.simplex_indices_orig = simplex_indices_orig
    render_ctx.valid_simplex_indices = np.unique(simplex_indices_orig[simplex_indices_orig >= 0])

    return render_ctx


def _apply_forward_transforms(*,
                              delaunay_ctx: DelaunayContext,
                              render_ctx: MorphRenderContext,
                              blend_ratio: float):
    """Apply forward affine transforms over the bounding box pixels."""

    if render_ctx.pixel_coords_orig_global is None or render_ctx.simplex_indices_orig is None:
        return (
            delaunay_ctx.working_img.copy().astype(np.float32),
            np.ones((delaunay_ctx.working_height, delaunay_ctx.working_width), dtype=np.float32),
            np.zeros((delaunay_ctx.working_height, delaunay_ctx.working_width), dtype=np.bool_),
            0,
            0,
        )

    working_img = delaunay_ctx.working_img
    working_width = delaunay_ctx.working_width
    working_height = delaunay_ctx.working_height
    min_x = delaunay_ctx.min_x
    min_y = delaunay_ctx.min_y
    bbox_width = render_ctx.bbox_width

    result = working_img.copy().astype(np.float32)
    result_count = np.ones((working_height, working_width), dtype=np.float32)
    transformed_mask = np.zeros((working_height, working_width), dtype=np.bool_)

    pixel_coords_orig_global = render_ctx.pixel_coords_orig_global
    simplex_indices_orig = render_ctx.simplex_indices_orig
    valid_simplex_indices = render_ctx.valid_simplex_indices
    if valid_simplex_indices is None:
        valid_simplex_indices = []

    original_points_array = delaunay_ctx.original_points_array
    transformed_points_array = delaunay_ctx.transformed_points_array
    tri = delaunay_ctx.tri

    total_pixels_processed = 0
    pixels_out_of_bounds = 0

    for simplex_idx in valid_simplex_indices:
        simplex = tri.simplices[simplex_idx]
        pixel_mask = (simplex_indices_orig == simplex_idx)
        if not np.any(pixel_mask):
            continue

        pt1_orig = original_points_array[simplex[0]]
        pt2_orig = original_points_array[simplex[1]]
        pt3_orig = original_points_array[simplex[2]]
        pt1_trans = transformed_points_array[simplex[0]]
        pt2_trans = transformed_points_array[simplex[1]]
        pt3_trans = transformed_points_array[simplex[2]]

        src_triangle = np.array([pt1_orig, pt2_orig, pt3_orig], dtype=np.float32)
        dst_triangle = np.array([pt1_trans, pt2_trans, pt3_trans], dtype=np.float32)

        v1 = dst_triangle[1] - dst_triangle[0]
        v2 = dst_triangle[2] - dst_triangle[0]
        cross_product = v1[0] * v2[1] - v1[1] * v2[0]
        triangle_area = abs(cross_product) / 2.0

        v1_orig = src_triangle[1] - src_triangle[0]
        v2_orig = src_triangle[2] - src_triangle[0]
        cross_product_orig = v1_orig[0] * v2_orig[1] - v1_orig[1] * v2_orig[0]
        triangle_area_orig = abs(cross_product_orig) / 2.0

        iris_indices = {468, 469, 470, 471, 472, 473, 474, 475, 476, 477}
        is_iris_triangle = any(idx in iris_indices for idx in simplex)
        is_flipped = (cross_product * cross_product_orig < 0)

        if is_iris_triangle:
            area_threshold = 0.0
        elif triangle_area_orig < 10.0:
            area_threshold = 0.05
        else:
            area_threshold = 0.02

        if is_flipped:
            dst_triangle = src_triangle.copy()
        elif area_threshold > 0 and (triangle_area < triangle_area_orig * area_threshold or triangle_area < 1.0):
            if not (is_iris_triangle and triangle_area_orig > 0.5 and triangle_area > 0.5):
                dst_triangle = src_triangle.copy()

        min_area_threshold = 0.5 if is_iris_triangle else 0.1
        if triangle_area_orig < min_area_threshold or triangle_area < min_area_threshold:
            if not is_iris_triangle or triangle_area_orig < 0.5:
                dst_triangle = src_triangle.copy()

        dist12 = np.linalg.norm(dst_triangle[1] - dst_triangle[0])
        dist13 = np.linalg.norm(dst_triangle[2] - dst_triangle[0])
        dist23 = np.linalg.norm(dst_triangle[2] - dst_triangle[1])
        min_side_length = min(dist12, dist13, dist23)
        if min_side_length < 0.5:
            dst_triangle = src_triangle.copy()

        try:
            M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)
            det = M_forward[0, 0] * M_forward[1, 1] - M_forward[0, 1] * M_forward[1, 0]
            if abs(det) < 1e-6:
                dst_triangle = src_triangle.copy()
                M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)
        except Exception:
            dst_triangle = src_triangle.copy()
            M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)

        triangle_pixels_orig = pixel_coords_orig_global[pixel_mask]
        ones = np.ones((len(triangle_pixels_orig), 1), dtype=np.float32)
        triangle_pixels_orig_homogeneous = np.hstack([triangle_pixels_orig, ones])
        transformed_coords = (M_forward @ triangle_pixels_orig_homogeneous.T).T

        pixel_indices_bbox = np.where(pixel_mask)[0]
        if len(pixel_indices_bbox) == 0:
            continue

        orig_y_coords_bbox = pixel_indices_bbox // bbox_width
        orig_x_coords_bbox = pixel_indices_bbox % bbox_width
        orig_y_coords = orig_y_coords_bbox + min_y
        orig_x_coords = orig_x_coords_bbox + min_x

        trans_x = transformed_coords[:, 0]
        trans_y = transformed_coords[:, 1]
        x0 = np.floor(trans_x).astype(np.int32)
        y0 = np.floor(trans_y).astype(np.int32)
        x1 = x0 + 1
        y1 = y0 + 1
        fx = trans_x - x0.astype(np.float32)
        fy = trans_y - y0.astype(np.float32)
        w00 = (1 - fx) * (1 - fy)
        w01 = (1 - fx) * fy
        w10 = fx * (1 - fy)
        w11 = fx * fy
        pixel_values = working_img[orig_y_coords, orig_x_coords].astype(np.float32)

        valid_00 = (y0 >= 0) & (y0 < working_height) & (x0 >= 0) & (x0 < working_width)
        valid_01 = (y1 >= 0) & (y1 < working_height) & (x0 >= 0) & (x0 < working_width)
        valid_10 = (y0 >= 0) & (y0 < working_height) & (x1 >= 0) & (x1 < working_width)
        valid_11 = (y1 >= 0) & (y1 < working_height) & (x1 >= 0) & (x1 < working_width)

        def _accumulate(mask, xs, ys, weights):
            if mask.size == 0:
                return
            y_valid = ys[mask]
            x_valid = xs[mask]
            weight_valid = weights[mask]
            pixel_vals = pixel_values[mask]
            weighted_vals = pixel_vals * weight_valid[:, np.newaxis]
            np.add.at(result, (y_valid, x_valid), weighted_vals)
            np.add.at(result_count, (y_valid, x_valid), weight_valid)
            transformed_mask[y_valid, x_valid] = True

        _accumulate(np.where(valid_00)[0], x0, y0, w00)
        _accumulate(np.where(valid_01)[0], x0, y1, w01)
        _accumulate(np.where(valid_10)[0], x1, y0, w10)
        _accumulate(np.where(valid_11)[0], x1, y1, w11)

        out_of_bounds_mask = (trans_x < 0) | (trans_x >= working_width) | (trans_y < 0) | (trans_y >= working_height)
        out_of_bounds_indices = np.where(out_of_bounds_mask)[0]
        if len(out_of_bounds_indices) > 0:
            trans_x_clipped = np.clip(trans_x[out_of_bounds_indices], 0, working_width - 1).astype(np.int32)
            trans_y_clipped = np.clip(trans_y[out_of_bounds_indices], 0, working_height - 1).astype(np.int32)
            out_of_bounds_weight = 0.3
            pixel_values_oob = pixel_values[out_of_bounds_indices]
            weighted_values_oob = pixel_values_oob * out_of_bounds_weight
            np.add.at(result, (trans_y_clipped, trans_x_clipped), weighted_values_oob)
            np.add.at(result_count, (trans_y_clipped, trans_x_clipped), out_of_bounds_weight)
            pixels_out_of_bounds += len(out_of_bounds_indices)

        total_pixels_processed += len(pixel_indices_bbox)

    return result, result_count, transformed_mask, total_pixels_processed, pixels_out_of_bounds


def _compose_result_image(*,
                          delaunay_ctx: DelaunayContext,
                          result: np.ndarray,
                          result_count: np.ndarray,
                          transformed_mask: np.ndarray,
                          blend_ratio: float) -> Image.Image:
    """Normalize, fill, upsample and blend to create the final PIL image."""

    img_array = delaunay_ctx.img_array
    working_img = delaunay_ctx.working_img
    scale_factor = delaunay_ctx.scale_factor
    min_x = delaunay_ctx.min_x
    min_y = delaunay_ctx.min_y
    max_x = delaunay_ctx.max_x
    max_y = delaunay_ctx.max_y
    min_x_orig_bbox = delaunay_ctx.min_x_orig_bbox
    min_y_orig_bbox = delaunay_ctx.min_y_orig_bbox
    max_x_orig_bbox = delaunay_ctx.max_x_orig_bbox
    max_y_orig_bbox = delaunay_ctx.max_y_orig_bbox

    blend_ratio = max(0.0, min(1.0, blend_ratio))
    result_count_safe = np.maximum(result_count, 1e-6)
    result_normalized = result / result_count_safe[:, :, np.newaxis]

    if blend_ratio == 1.0:
        transformed_pixel_mask = (result_count > 1.0 + 1e-6)
        if np.any(transformed_pixel_mask):
            mask_3d = transformed_pixel_mask[:, :, np.newaxis]
            working_img_float = working_img.astype(np.float32)
            result_count_float = result_count[:, :, np.newaxis]
            result_count_minus_one = np.maximum(result_count_float - 1.0, 1e-6)
            transformed_only = (result_normalized * result_count_float - working_img_float) / result_count_minus_one
            result_normalized = np.where(mask_3d, transformed_only, working_img_float)

    result_final = result_normalized.astype(np.uint8)
    empty_mask = (result_count < 1e-6)
    if np.any(empty_mask):
        empty_ratio = np.sum(empty_mask) / (result_count.size)
        if _cv2_available and empty_ratio < 0.5:
            empty_mask_uint8 = (empty_mask * 255).astype(np.uint8)
            result_final = cv2.inpaint(result_final, empty_mask_uint8, 3, cv2.INPAINT_TELEA)
        else:
            result_final[empty_mask] = working_img[empty_mask]

    if scale_factor < 1.0 and min_x_orig_bbox is not None:
        result_full = img_array.copy().astype(np.float32)
        bbox_result = result_final[min_y:max_y, min_x:max_x].copy()
        bbox_result_height, bbox_result_width = bbox_result.shape[:2]
        min_x_orig = max(0, min_x_orig_bbox)
        min_y_orig = max(0, min_y_orig_bbox)
        max_x_orig = min(img_array.shape[1], max_x_orig_bbox)
        max_y_orig = min(img_array.shape[0], max_y_orig_bbox)
        bbox_width_orig = max_x_orig - min_x_orig
        bbox_height_orig = max_y_orig - min_y_orig
        if bbox_width_orig > 0 and bbox_height_orig > 0:
            bbox_result_upscaled = cv2.resize(
                bbox_result,
                (bbox_width_orig, bbox_height_orig),
                interpolation=cv2.INTER_LINEAR,
            )
            result_full[min_y_orig:max_y_orig, min_x_orig:max_x_orig] = bbox_result_upscaled.astype(np.float32)
        result_final = result_full.astype(np.uint8)

    if blend_ratio == 0.0:
        result_final = img_array.copy()
    elif 0.0 < blend_ratio < 1.0:
        if result_final.shape[:2] != img_array.shape[:2]:
            result_final = cv2.resize(result_final, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_LINEAR)
        result_float = result_final.astype(np.float32)
        img_array_float = img_array.astype(np.float32)
        result_final = (img_array_float * (1.0 - blend_ratio) + result_float * blend_ratio).astype(np.uint8)
    else:
        if result_final.shape[:2] != img_array.shape[:2]:
            result_final = cv2.resize(result_final, (img_array.shape[1], img_array.shape[0]), interpolation=cv2.INTER_LINEAR)

    return Image.fromarray(result_final)

def morph_face_by_polygons(image, original_landmarks, transformed_landmarks, selected_point_indices=None,
                           left_iris_center_coord=None, right_iris_center_coord=None,
                           left_iris_center_orig=None, right_iris_center_orig=None,
                           cached_original_bbox=None, blend_ratio=1.0,
                           clamping_enabled=True, margin_ratio=0.3, iris_center_only=False,
                           iris_mapping_method="iris_outline"):
    """
    Delaunay Triangulation을 사용하여 폴리곤(랜드마크 포인트) 기반 얼굴 변형을 수행합니다.
    뒤집힌 삼각형이 발생하면 변형을 점진적으로 줄여서 재시도합니다.
    
    Args:
        image: PIL.Image 객체
        original_landmarks: 원본 랜드마크 포인트 리스트 [(x, y), ...] (폴리곤의 꼭짓점)
        transformed_landmarks: 변형된 랜드마크 포인트 리스트 [(x, y), ...] (변형된 폴리곤의 꼭짓점)
        selected_point_indices: 선택한 포인트 인덱스 리스트 (인덱스 기반 직접 매핑을 위해, None이면 전체 사용)
        left_iris_center_coord: 왼쪽 눈동자 중앙 포인트 좌표 (변형된, 선택적, 사용자 관점)
        right_iris_center_coord: 오른쪽 눈동자 중앙 포인트 좌표 (변형된, 선택적, 사용자 관점)
        left_iris_center_orig: 왼쪽 눈동자 중앙 포인트 좌표 (원본, 선택적, 사용자 관점)
        right_iris_center_orig: 오른쪽 눈동자 중앙 포인트 좌표 (원본, 선택적, 사용자 관점)
        cached_original_bbox: 캐시된 원본 바운딩 박스 (선택적)
        blend_ratio: 블렌딩 비율 (0.0 ~ 1.0, 기본값: 1.0)
        clamping_enabled: 눈동자 이동 범위 제한 활성화 여부 (기본값: True)
        margin_ratio: 눈동자 이동 범위 제한 마진 비율 (기본값: 0.3)
        iris_center_only: 눈동자 중심점만 드래그 플래그 (기본값: False)
        iris_mapping_method: 눈동자 맵핑 방법 (iris_outline/eye_landmarks, 기본값: "iris_outline")
    
    Returns:
        PIL.Image: 변형된 이미지
    """

    try:        
        # 입력 검증 및 전처리
        validation_result = _validate_and_prepare_inputs(image, original_landmarks, transformed_landmarks)
        if validation_result is None:
            return image

        img_array, img_width, img_height = validation_result

        # 눈동자 포인트 처리 및 중앙 포인트 준비
        iris_ctx = _prepare_iris_centers(
            original_landmarks, transformed_landmarks,
            left_iris_center_coord, right_iris_center_coord,
            left_iris_center_orig, right_iris_center_orig,
            img_width, img_height,
            clamping_enabled=clamping_enabled, margin_ratio=margin_ratio,
            iris_mapping_method=iris_mapping_method,
            selected_point_indices_param=selected_point_indices,
            preserve_selected_indices=bool(selected_point_indices)
        )
        original_landmarks_no_iris = iris_ctx.original_landmarks_no_iris
        transformed_landmarks_no_iris = iris_ctx.transformed_landmarks_no_iris
        original_points_array = iris_ctx.original_points_array
        transformed_points_array = iris_ctx.transformed_points_array
        selected_point_indices = iris_ctx.selected_point_indices
        try:
            if selected_point_indices:
                selected_sample = list(selected_point_indices)[:5]
                used_orig = []
                used_trans = []
                for idx in selected_sample:
                    if idx < len(original_landmarks_no_iris) and idx < len(transformed_landmarks_no_iris):
                        used_orig.append(original_landmarks_no_iris[idx])
                        used_trans.append(transformed_landmarks_no_iris[idx])
                print_info("얼굴모핑", f"사용 인덱스 샘플: {selected_sample}")
                print_info("얼굴모핑", f"사용 원본 좌표 샘플: {used_orig}")
                print_info("얼굴모핑", f"사용 변형 좌표 샘플: {used_trans}")
        except NameError:
            print_error("얼굴모핑", f"모핑 샘플 Not found..")
            pass
        
        delaunay_ctx = _prepare_delaunay_context(
            img_array=img_array,
            img_width=img_width,
            img_height=img_height,
            iris_ctx=iris_ctx,
            cached_original_bbox=cached_original_bbox,
        )
        transformed_points_array = _check_and_fix_flipped_triangles(
            delaunay_ctx.original_points_array,
            delaunay_ctx.transformed_points_array,
            delaunay_ctx.tri,
            original_landmarks_no_iris,
        )
        delaunay_ctx.transformed_points_array = transformed_points_array

        render_ctx = _build_pixel_coordinate_map(delaunay_ctx)

        original_points_array = delaunay_ctx.original_points_array
        transformed_points_array = delaunay_ctx.transformed_points_array

        # 변형된 랜드마크와 원본 랜드마크의 차이 확인 (벡터화)
        landmarks_count = len(original_landmarks_no_iris)
        if landmarks_count > 0 and original_points_array is not None and transformed_points_array is not None:
            orig_pts = original_points_array[:landmarks_count]
            trans_pts = transformed_points_array[:landmarks_count]
            diffs = np.sqrt(np.sum((trans_pts - orig_pts)**2, axis=1))
            max_diff = np.max(diffs)
            changed_count = np.sum(diffs > 0.1)
        else:
            max_diff = 0.0
            changed_count = 0
        try:
            print_info("얼굴모핑", f"변형 진행 (max_diff={max_diff:.3f}, changed_count={changed_count})")
        except NameError:
            print(f"[얼굴모핑] 변형 진행 (max_diff={max_diff:.3f}, changed_count={changed_count})")

        try:
            print_info("얼굴모핑", f"[DEBUG] 선택적 변형 건너뛰고 전체 변형 사용")
        except NameError:
            print(f"[얼굴모핑] [DEBUG] 선택적 변형 건너뛰고 전체 변형 사용")
        try:
            print_info("얼굴모핑", f"[DEBUG] 최종 selected_point_indices: {len(selected_point_indices)}개 포인트 사용")
        except NameError:
            print(f"[얼굴모핑] [DEBUG] 최종 selected_point_indices: {len(selected_point_indices)}개 포인트 사용")

        result, result_count, transformed_mask, total_pixels_processed, pixels_out_of_bounds = _apply_forward_transforms(
            delaunay_ctx=delaunay_ctx,
            render_ctx=render_ctx,
            blend_ratio=blend_ratio,
        )
        try:
            print_info(
                "얼굴모핑",
                f"정변환 적용 완료: 처리 픽셀={total_pixels_processed}, 범위 초과 픽셀={pixels_out_of_bounds}"
            )
        except NameError:
            pass

        final_image = _compose_result_image(
            delaunay_ctx=delaunay_ctx,
            result=result,
            result_count=result_count,
            transformed_mask=transformed_mask,
            blend_ratio=blend_ratio,
        )

        return final_image

    except Exception as e:
        print_error("얼굴모핑", f"모핑 실패: {e}")
        return image
