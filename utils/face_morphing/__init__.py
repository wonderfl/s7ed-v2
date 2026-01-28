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

# 공개 API 제공 (기존 호환성 유지)
from .constants import (
    _cv2_available,
    _cv2_cuda_available,
    _scipy_available,
    _landmarks_available,
    _delaunay_cache,
    _delaunay_cache_max_size
)

from .utils import (
    _sigmoid_blend_mask,
    _create_blend_mask
)

from .region_extraction import (
    _get_eye_region,
    _get_mouth_region,
    _get_nose_region
)

from .adjustments import (
    adjust_eye_size,
    adjust_eye_spacing,
    adjust_eye_position,
    adjust_nose_size,
    adjust_jaw,
    adjust_face_size,
    adjust_mouth_size,
    adjust_upper_lip_size,
    adjust_lower_lip_size,
    adjust_upper_lip_shape,
    adjust_lower_lip_shape,
    adjust_upper_lip_width,
    adjust_lower_lip_width,
    adjust_lip_vertical_move
)

from .polygon_morphing import (
    transform_points_for_eye_size,
    transform_points_for_eye_size_centered,
    transform_points_for_nose_size,
    transform_points_for_jaw,
    transform_points_for_face_size,
    transform_points_for_mouth_size,
    transform_points_for_eye_position,
    transform_points_for_lip_shape,
    transform_points_for_lip_width,
    transform_points_for_lip_vertical_move,
    move_point_group,
    move_points,
    morph_face_by_polygons
)

from .integration import (
    apply_all_adjustments
)

__all__ = [
    # 상수
    '_cv2_available',
    '_cv2_cuda_available',
    '_scipy_available',
    '_landmarks_available',
    '_delaunay_cache',
    '_delaunay_cache_max_size',
    # 유틸리티
    '_sigmoid_blend_mask',
    '_create_blend_mask',
    # 영역 추출
    '_get_eye_region',
    '_get_mouth_region',
    '_get_nose_region',
    # 이미지 조정
    'adjust_eye_size',
    'adjust_eye_spacing',
    'adjust_eye_position',
    'adjust_nose_size',
    'adjust_jaw',
    'adjust_face_size',
    'adjust_mouth_size',
    'adjust_upper_lip_size',
    'adjust_lower_lip_size',
    'adjust_upper_lip_shape',
    'adjust_lower_lip_shape',
    'adjust_upper_lip_width',
    'adjust_lower_lip_width',
    'adjust_lip_vertical_move',
    # 폴리곤 포인트 변형 및 모핑
    'transform_points_for_eye_size',
    'transform_points_for_eye_size_centered',
    'transform_points_for_nose_size',
    'transform_points_for_jaw',
    'transform_points_for_face_size',
    'transform_points_for_mouth_size',
    'transform_points_for_eye_position',
    'transform_points_for_lip_shape',
    'transform_points_for_lip_width',
    'transform_points_for_lip_vertical_move',
    'move_point_group',
    'move_points',
    'morph_face_by_polygons',
    # 통합
    'apply_all_adjustments',
]
