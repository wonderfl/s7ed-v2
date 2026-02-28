"""
유틸리티 함수 모듈
마스크 생성 및 블렌딩 관련 유틸리티 함수
"""
import numpy as np

from .constants import _cv2_available

# cv2는 constants에서 import됨
try:
    import cv2
except ImportError:
    cv2 = None


def _sigmoid_blend_mask(mask, steepness=10.0):
    """
    시그모이드 함수를 사용하여 마스크를 부드럽게 블렌딩합니다.
    
    Args:
        mask: 마스크 배열 (0.0 ~ 1.0 범위)
        steepness: 시그모이드 함수의 경사도 (기본값: 10.0, 높을수록 더 급격한 변화)
    
    Returns:
        블렌딩된 마스크 (0.0 ~ 1.0 범위)
    """
    # 시그모이드 함수: 1 / (1 + exp(-steepness * (x - 0.5)))
    # x를 0~1 범위로 정규화하고, 0.5를 중심으로 시그모이드 적용
    normalized = (mask / 255.0) if mask.dtype == np.uint8 else mask
    sigmoid_mask = 1.0 / (1.0 + np.exp(-steepness * (normalized - 0.5)))
    return sigmoid_mask


def _create_blend_mask(width, height, mask_type='ellipse', mask_size=None, steepness=5.0):
    """
    블렌딩용 마스크를 생성합니다 (개선된 버전: 시그모이드 함수 기반)
    
    Args:
        width: 마스크 너비
        height: 마스크 높이
        mask_type: 마스크 타입 ('ellipse' 또는 'rect', 기본값: 'ellipse')
        mask_size: 마스크 크기 (None이면 자동 계산)
        steepness: 시그모이드 함수의 경사도 (기본값: 10.0)
    
    Returns:
        블렌딩 마스크 (0.0 ~ 1.0 범위, float32)
    """
    if not _cv2_available:
        # OpenCV가 없으면 단순 마스크 반환
        return np.ones((height, width), dtype=np.float32)
    
    if mask_size is None:
        # 영역 크기에 비례한 동적 마스크 크기 계산
        mask_size = max(15, min(width, height) // 4)
        # 홀수로 만들기 (가우시안 블러를 위해)
        if mask_size % 2 == 0:
            mask_size += 1
    
    if mask_type == 'ellipse':
        # 타원형 마스크 생성
        center_x = width // 2
        center_y = height // 2
        # 타원의 반지름 (경계에서 약간 안쪽으로)
        radius_x = max(1, width // 2 - mask_size // 3)
        radius_y = max(1, height // 2 - mask_size // 3)
        
        # 타원형 마스크 생성
        y_grid, x_grid = np.ogrid[:height, :width]
        ellipse_mask = ((x_grid - center_x) / radius_x)**2 + ((y_grid - center_y) / radius_y)**2 <= 1.0
        mask = (ellipse_mask.astype(np.uint8) * 255)
    else:
        # 사각형 마스크 생성
        mask = np.ones((height, width), dtype=np.uint8) * 255
    
    # 가우시안 블러로 마스크 부드럽게 (동적 크기 사용)
    mask = cv2.GaussianBlur(mask, (mask_size, mask_size), 0)
    
    # 시그모이드 함수를 사용하여 더 부드러운 블렌딩
    mask_blended = _sigmoid_blend_mask(mask, steepness)
    
    return mask_blended.astype(np.float32)
