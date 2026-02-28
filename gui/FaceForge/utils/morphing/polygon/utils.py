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


def _get_neighbor_points(tri, point_idx):
    """
    Delaunay Triangulation에서 특정 포인트와 연결된 이웃 포인트들을 찾습니다.
    
    Args:
        tri: Delaunay Triangulation 객체
        point_idx: 포인트 인덱스
    
    Returns:
        neighbor_indices: 이웃 포인트 인덱스 집합
    """
    neighbor_indices = set()
    
    # 해당 포인트를 포함하는 모든 삼각형 찾기
    for simplex in tri.simplices:
        if point_idx in simplex:
            # 이 삼각형의 다른 포인트들을 이웃으로 추가
            for idx in simplex:
                if idx != point_idx:
                    neighbor_indices.add(idx)
    
    return neighbor_indices




def _check_triangles_flipped(original_points, transformed_points, tri):
    """
    변형된 랜드마크에서 뒤집힌 삼각형이 있는지 확인합니다.
    
    Args:
        original_points: 원본 랜드마크 포인트 배열
        transformed_points: 변형된 랜드마크 포인트 배열
        tri: Delaunay Triangulation 객체
    
    Returns:
        flipped_count: 뒤집힌 삼각형 개수
        flipped_indices: 뒤집힌 삼각형 인덱스 리스트
        problematic_point_indices: 뒤집힌 삼각형에 포함된 문제가 있는 랜드마크 포인트 인덱스 집합
        neighbor_point_indices: 문제 포인트와 연결된 이웃 포인트 인덱스 집합
    """
    flipped_count = 0
    flipped_indices = []
    problematic_point_indices = set()
    
    for simplex_idx, simplex in enumerate(tri.simplices):
        # 원본 삼각형의 3개 포인트
        pt1_orig = original_points[simplex[0]]
        pt2_orig = original_points[simplex[1]]
        pt3_orig = original_points[simplex[2]]
        
        # 변형된 삼각형의 3개 포인트
        pt1_trans = transformed_points[simplex[0]]
        pt2_trans = transformed_points[simplex[1]]
        pt3_trans = transformed_points[simplex[2]]
        
        # 외적 계산
        v1_orig = pt2_orig - pt1_orig
        v2_orig = pt3_orig - pt1_orig
        cross_product_orig = v1_orig[0] * v2_orig[1] - v1_orig[1] * v2_orig[0]
        
        v1_trans = pt2_trans - pt1_trans
        v2_trans = pt3_trans - pt1_trans
        cross_product_trans = v1_trans[0] * v2_trans[1] - v1_trans[1] * v2_trans[0]
        
        # 뒤집혔는지 확인 (외적의 부호가 바뀌면 뒤집힘)
        if cross_product_orig * cross_product_trans < 0:
            flipped_count += 1
            flipped_indices.append(simplex_idx)
            # 이 삼각형의 모든 포인트를 문제가 있는 포인트로 표시
            problematic_point_indices.add(simplex[0])
            problematic_point_indices.add(simplex[1])
            problematic_point_indices.add(simplex[2])
    
    # 문제 포인트와 연결된 이웃 포인트들도 찾기
    neighbor_point_indices = set()
    for point_idx in problematic_point_indices:
        neighbors = _get_neighbor_points(tri, point_idx)
        neighbor_point_indices.update(neighbors)
    
    # 문제 포인트 자체는 이웃에서 제외 (중복 방지)
    neighbor_point_indices -= problematic_point_indices
    
    return flipped_count, flipped_indices, problematic_point_indices, neighbor_point_indices




