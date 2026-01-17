"""
얼굴 특징 보정 모듈
랜드마크 포인트를 기반으로 얼굴의 특징을 변형합니다.
"""
import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2
    _cv2_available = True
    # OpenCV CUDA 지원 확인
    _cv2_cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
except ImportError:
    _cv2_available = False
    _cv2_cuda_available = False
except AttributeError:
    # OpenCV가 CUDA 지원 없이 빌드된 경우
    _cv2_cuda_available = False

try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, is_available as landmarks_available
    _landmarks_available = landmarks_available()
except ImportError:
    _landmarks_available = False

# Delaunay Triangulation 캐시 (성능 최적화)
_delaunay_cache = {}
_delaunay_cache_max_size = 5  # 최대 캐시 크기


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


def _get_eye_region(key_landmarks, img_width, img_height, eye='left', landmarks=None, padding_ratio=None, offset_x=None, offset_y=None):
    """
    눈 영역을 계산합니다 (랜드마크 포인트를 사용하여 정확하게 계산, 개선된 버전: 표준편차 기반 동적 패딩)
    
    Args:
        key_landmarks: 주요 랜드마크 딕셔너리
        img_width: 이미지 너비
        img_height: 이미지 높이
        eye: 'left' 또는 'right'
        landmarks: 랜드마크 포인트 리스트
        padding_ratio: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 자동 계산, 기본값: 0.3)
        offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
        offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
    
    Returns:
        (x1, y1, x2, y2), eye_center: 눈 영역 좌표와 중심점
    """
    # 기본값 설정 (None이면 기본값 사용)
    if padding_ratio is None:
        padding_ratio = 0.3
    if offset_x is None:
        offset_x = 0.0
    if offset_y is None:
        offset_y = 0.0
    if eye == 'left':
        eye_center = key_landmarks['left_eye']
        # MediaPipe Face Mesh의 왼쪽 눈 인덱스
        EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    else:
        eye_center = key_landmarks['right_eye']
        # MediaPipe Face Mesh의 오른쪽 눈 인덱스
        EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    
    # 랜드마크 포인트가 있으면 정확한 눈 영역 계산
    if landmarks is not None and len(landmarks) >= 468:
        eye_points = [landmarks[i] for i in EYE_INDICES if i < len(landmarks)]
        if eye_points:
            # 눈 포인트들의 경계 계산
            x_coords = [p[0] for p in eye_points]
            y_coords = [p[1] for p in eye_points]
            
            min_x = int(min(x_coords))
            max_x = int(max(x_coords))
            min_y = int(min(y_coords))
            max_y = int(max(y_coords))
            
            # 개선: 표준편차 기반 동적 패딩 계산
            # 눈 영역의 가로/세로 크기 (모든 포인트를 포함하는 최소 영역)
            eye_width = max_x - min_x
            eye_height = max_y - min_y
            
            # 직사각형 영역: 눈을 모두 포함하되, 가로/세로 비율을 조정
            # 최소 크기를 기준으로 하되, 눈의 실제 크기를 고려
            # 가로가 세로보다 크면 세로를 늘려서 비율을 조정 (최대 1.5:1 비율)
            # 세로가 가로보다 크면 가로를 늘려서 비율을 조정
            max_dimension = max(eye_width, eye_height)
            min_dimension = min(eye_width, eye_height)
            
            # 비율 조정: 최대 1.5:1 비율로 제한 (너무 길쭉하지 않게)
            if eye_width > eye_height:
                # 가로가 더 긴 경우: 세로를 늘려서 비율 조정
                target_height = max(eye_height, eye_width / 1.5)
                target_width = eye_width
            else:
                # 세로가 더 긴 경우: 가로를 늘려서 비율 조정
                target_width = max(eye_width, eye_height / 1.5)
                target_height = eye_height
            
            if len(x_coords) > 1:
                mean_x = sum(x_coords) / len(x_coords)
                mean_y = sum(y_coords) / len(y_coords)
                std_x = (sum((x - mean_x) ** 2 for x in x_coords) / len(x_coords)) ** 0.5
                std_y = (sum((y - mean_y) ** 2 for y in y_coords) / len(y_coords)) ** 0.5
                
                # 표준편차를 기반으로 동적 패딩 계산
                # 눈 포인트를 모두 포함하기 위해 더 큰 패딩 적용
                # 최소 패딩: 크기의 20%, 표준편차의 2배 중 큰 값
                base_padding_x = max(target_width * 0.2, std_x * 2.0)
                base_padding_y = max(target_height * 0.2, std_y * 2.0)
                padding_x = int(base_padding_x * padding_ratio)
                padding_y = int(base_padding_y * padding_ratio)
            else:
                # 포인트가 부족한 경우 기본 계산 (더 큰 패딩)
                padding_x = int(target_width * max(0.2, padding_ratio))
                padding_y = int(target_height * max(0.2, padding_ratio))
            
            # 눈 중심점에 오프셋 적용
            offset_eye_center_x = eye_center[0] + offset_x
            offset_eye_center_y = eye_center[1] + offset_y
            
            # 오프셋이 적용된 중심점 기준으로 직사각형 영역 계산
            center_x = (min_x + max_x) / 2 + offset_x
            center_y = (min_y + max_y) / 2 + offset_y
            
            # 직사각형 영역 계산 (조정된 가로/세로 비율 사용, 충분한 패딩)
            half_width = target_width / 2 + padding_x
            half_height = target_height / 2 + padding_y
            x1 = max(0, int(center_x - half_width))
            y1 = max(0, int(center_y - half_height))
            x2 = min(img_width, int(center_x + half_width))
            y2 = min(img_height, int(center_y + half_height))
            
            # 최종 확인: 모든 눈 포인트가 영역 안에 있는지 확인하고, 없으면 영역 확장
            for point in eye_points:
                px, py = point
                if px < x1:
                    x1 = max(0, px - padding_x)
                if px > x2:
                    x2 = min(img_width, px + padding_x)
                if py < y1:
                    y1 = max(0, py - padding_y)
                if py > y2:
                    y2 = min(img_height, py + padding_y)
            
            # 오프셋이 적용된 중심점 반환
            offset_eye_center = (int(offset_eye_center_x), int(offset_eye_center_y))
            return (x1, y1, x2, y2), offset_eye_center
    
    # 랜드마크 포인트가 없으면 기존 방식 사용 (두 눈 사이 거리 기반)
    left_eye = key_landmarks['left_eye']
    right_eye = key_landmarks['right_eye']
    eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
    # 패딩 비율 적용 (기본 0.3이지만 조절 가능)
    eye_radius = int(eye_distance * (0.3 * padding_ratio / 0.3))  # padding_ratio에 비례하여 조정
    
    # 눈 중심점에 오프셋 적용
    offset_eye_center_x = eye_center[0] + offset_x
    offset_eye_center_y = eye_center[1] + offset_y
    
    # 눈 영역 계산 (오프셋 적용된 중심점 기준)
    x1 = max(0, int(offset_eye_center_x - eye_radius))
    y1 = max(0, int(offset_eye_center_y - eye_radius))
    x2 = min(img_width, int(offset_eye_center_x + eye_radius))
    y2 = min(img_height, int(offset_eye_center_y + eye_radius))
    
    offset_eye_center = (int(offset_eye_center_x), int(offset_eye_center_y))
    return (x1, y1, x2, y2), offset_eye_center


def _get_mouth_region(key_landmarks, img_width, img_height, landmarks=None, padding_ratio_x=None, padding_ratio_y=None, offset_x=None, offset_y=None):
    """
    입 영역을 계산합니다 (랜드마크 포인트를 사용하여 정확하게 계산)
    
    Args:
        key_landmarks: 주요 랜드마크 딕셔너리
        img_width: 이미지 너비
        img_height: 이미지 높이
        landmarks: 랜드마크 포인트 리스트
        padding_ratio_x: 입 영역 수평 패딩 비율 (0.0 ~ 1.0, None이면 자동 계산, 기본값: 0.2)
        padding_ratio_y: 입 영역 수직 패딩 비율 (0.0 ~ 1.0, None이면 자동 계산, 기본값: 0.3)
        offset_x: 입 영역 수평 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
        offset_y: 입 영역 수직 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
    
    Returns:
        (x1, y1, x2, y2), mouth_center: 입 영역 좌표와 중심점
    """
    # 기본값 설정 (None이면 기본값 사용)
    if padding_ratio_x is None:
        padding_ratio_x = 0.2
    if padding_ratio_y is None:
        padding_ratio_y = 0.3
    if offset_x is None:
        offset_x = 0.0
    if offset_y is None:
        offset_y = 0.0
    mouth_center = key_landmarks['mouth']
    
    # MediaPipe Face Mesh의 입술 랜드마크 인덱스
    # 입술 외곽 (Outer Lip): 윗입술 + 아래입술 외곽선
    OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
    # 입 안쪽 (Inner Lip): 입 안쪽 경계선
    INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
    # 입 전체 (입술 외곽 + 입 안쪽)
    MOUTH_ALL_INDICES = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))
    
    # 랜드마크 포인트가 있으면 정확한 입 영역 계산
    if landmarks is not None and len(landmarks) >= 468:
        mouth_points = [landmarks[i] for i in MOUTH_ALL_INDICES if i < len(landmarks)]
        if mouth_points:
            # 입 포인트들의 경계 계산
            x_coords = [p[0] for p in mouth_points]
            y_coords = [p[1] for p in mouth_points]
            
            min_x = int(min(x_coords))
            max_x = int(max(x_coords))
            min_y = int(min(y_coords))
            max_y = int(max(y_coords))
            
            # 개선: 표준편차 기반 동적 패딩 계산
            if len(x_coords) > 1:
                mean_x = sum(x_coords) / len(x_coords)
                mean_y = sum(y_coords) / len(y_coords)
                std_x = (sum((x - mean_x) ** 2 for x in x_coords) / len(x_coords)) ** 0.5
                std_y = (sum((y - mean_y) ** 2 for y in y_coords) / len(y_coords)) ** 0.5
                
                # 표준편차를 기반으로 동적 패딩 계산 (최소값 보장)
                base_padding_x = max((max_x - min_x) * 0.1, std_x * 1.5)
                base_padding_y = max((max_y - min_y) * 0.1, std_y * 1.5)
                padding_x = int(base_padding_x * padding_ratio_x)
                padding_y = int(base_padding_y * padding_ratio_y)
            else:
                # 포인트가 부족한 경우 기본 계산
                padding_x = int((max_x - min_x) * padding_ratio_x)
                padding_y = int((max_y - min_y) * padding_ratio_y)
            
            # 입 중심점에 오프셋 적용
            offset_mouth_center_x = mouth_center[0] + offset_x
            offset_mouth_center_y = mouth_center[1] + offset_y
            
            # 오프셋이 적용된 중심점 기준으로 영역 계산
            center_x = (min_x + max_x) / 2 + offset_x
            center_y = (min_y + max_y) / 2 + offset_y
            
            x1 = max(0, int(center_x - (max_x - min_x) / 2 - padding_x))
            y1 = max(0, int(center_y - (max_y - min_y) / 2 - padding_y))
            x2 = min(img_width, int(center_x + (max_x - min_x) / 2 + padding_x))
            y2 = min(img_height, int(center_y + (max_y - min_y) / 2 + padding_y))
            
            # 오프셋이 적용된 중심점 반환
            offset_mouth_center = (int(offset_mouth_center_x), int(offset_mouth_center_y))
            return (x1, y1, x2, y2), offset_mouth_center
    
    # 랜드마크 포인트가 없으면 기존 방식 사용 (입 중심점 기반)
    left_eye = key_landmarks['left_eye']
    right_eye = key_landmarks['right_eye']
    eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
    
    # 입 크기 추정 (두 눈 사이 거리의 약 1/2)
    mouth_radius_x = int(eye_distance * 0.3)
    mouth_radius_y = int(eye_distance * 0.15)
    
    # 입 중심점에 오프셋 적용
    offset_mouth_center_x = mouth_center[0] + offset_x
    offset_mouth_center_y = mouth_center[1] + offset_y
    
    # 입 영역 계산 (오프셋 적용된 중심점 기준)
    x1 = max(0, int(offset_mouth_center_x - mouth_radius_x))
    y1 = max(0, int(offset_mouth_center_y - mouth_radius_y))
    x2 = min(img_width, int(offset_mouth_center_x + mouth_radius_x))
    y2 = min(img_height, int(offset_mouth_center_y + mouth_radius_y))
    
    offset_mouth_center = (int(offset_mouth_center_x), int(offset_mouth_center_y))
    return (x1, y1, x2, y2), offset_mouth_center


def _get_nose_region(key_landmarks, img_width, img_height, landmarks=None, padding_ratio=None, offset_x=None, offset_y=None):
    """
    코 영역을 계산합니다 (랜드마크 포인트를 사용하여 정확하게 계산)
    
    Args:
        key_landmarks: 주요 랜드마크 딕셔너리
        img_width: 이미지 너비
        img_height: 이미지 높이
        landmarks: 랜드마크 포인트 리스트
        padding_ratio: 코 영역 패딩 비율 (0.0 ~ 1.0, None이면 자동 계산, 기본값: 0.3)
        offset_x: 코 영역 수평 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
        offset_y: 코 영역 수직 오프셋 (픽셀, None이면 0.0 사용, 기본값: 0.0)
    
    Returns:
        (x1, y1, x2, y2), nose_center: 코 영역 좌표와 중심점
    """
    # 기본값 설정 (None이면 기본값 사용)
    if padding_ratio is None:
        padding_ratio = 0.3
    if offset_x is None:
        offset_x = 0.0
    if offset_y is None:
        offset_y = 0.0
    nose_center = key_landmarks['nose']
    
    # MediaPipe Face Mesh의 코 랜드마크 인덱스
    NOSE_INDICES = [8, 240, 98, 164, 327, 460, 4]  # 코 끝 및 코 영역
    
    # 랜드마크 포인트가 있으면 정확한 코 영역 계산
    if landmarks is not None and len(landmarks) >= 468:
        nose_points = [landmarks[i] for i in NOSE_INDICES if i < len(landmarks)]
        if nose_points:
            # 코 포인트들의 경계 계산
            x_coords = [p[0] for p in nose_points]
            y_coords = [p[1] for p in nose_points]
            
            min_x = int(min(x_coords))
            max_x = int(max(x_coords))
            min_y = int(min(y_coords))
            max_y = int(max(y_coords))
            
            # 개선: 표준편차 기반 동적 패딩 계산
            if len(x_coords) > 1:
                mean_x = sum(x_coords) / len(x_coords)
                mean_y = sum(y_coords) / len(y_coords)
                std_x = (sum((x - mean_x) ** 2 for x in x_coords) / len(x_coords)) ** 0.5
                std_y = (sum((y - mean_y) ** 2 for y in y_coords) / len(y_coords)) ** 0.5
                
                # 표준편차를 기반으로 동적 패딩 계산 (최소값 보장)
                base_padding_x = max((max_x - min_x) * 0.1, std_x * 1.5)
                base_padding_y = max((max_y - min_y) * 0.1, std_y * 1.5)
                padding_x = int(base_padding_x * padding_ratio)
                padding_y = int(base_padding_y * padding_ratio)
            else:
                # 포인트가 부족한 경우 기본 계산
                padding_x = int((max_x - min_x) * padding_ratio)
                padding_y = int((max_y - min_y) * padding_ratio)
            
            # 코 중심점에 오프셋 적용
            offset_nose_center_x = nose_center[0] + offset_x
            offset_nose_center_y = nose_center[1] + offset_y
            
            # 오프셋이 적용된 중심점 기준으로 영역 계산
            center_x = (min_x + max_x) / 2 + offset_x
            center_y = (min_y + max_y) / 2 + offset_y
            
            x1 = max(0, int(center_x - (max_x - min_x) / 2 - padding_x))
            y1 = max(0, int(center_y - (max_y - min_y) / 2 - padding_y))
            x2 = min(img_width, int(center_x + (max_x - min_x) / 2 + padding_x))
            y2 = min(img_height, int(center_y + (max_y - min_y) / 2 + padding_y))
            
            # 오프셋이 적용된 중심점 반환
            offset_nose_center = (int(offset_nose_center_x), int(offset_nose_center_y))
            return (x1, y1, x2, y2), offset_nose_center
    
    # 랜드마크 포인트가 없으면 기존 방식 사용 (두 눈 사이 거리 기반)
    left_eye = key_landmarks['left_eye']
    right_eye = key_landmarks['right_eye']
    eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
    
    # 코 크기 추정 (두 눈 사이 거리의 약 1/3)
    nose_radius = int(eye_distance * 0.2)
    
    # 코 중심점에 오프셋 적용
    offset_nose_center_x = nose_center[0] + offset_x
    offset_nose_center_y = nose_center[1] + offset_y
    
    # 코 영역 계산 (오프셋 적용된 중심점 기준)
    x1 = max(0, int(offset_nose_center_x - nose_radius))
    y1 = max(0, int(offset_nose_center_y - nose_radius))
    x2 = min(img_width, int(offset_nose_center_x + nose_radius))
    y2 = min(img_height, int(offset_nose_center_y + nose_radius))
    
    offset_nose_center = (int(offset_nose_center_x), int(offset_nose_center_y))
    return (x1, y1, x2, y2), offset_nose_center


def adjust_eye_size(image, eye_size_ratio=1.0, landmarks=None, left_eye_size_ratio=None, right_eye_size_ratio=None, 
                    eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                    left_eye_region_padding=None, right_eye_region_padding=None,
                    left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                    right_eye_region_offset_x=None, right_eye_region_offset_y=None):
    """
    눈 크기를 조정합니다 (개선된 버전: 정확한 랜드마크 기반 영역 계산 및 자연스러운 블렌딩).
    
    Args:
        image: PIL.Image 객체
        eye_size_ratio: 눈 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        left_eye_size_ratio: 왼쪽 눈 크기 비율 (None이면 eye_size_ratio 사용)
        right_eye_size_ratio: 오른쪽 눈 크기 비율 (None이면 eye_size_ratio 사용)
        eye_region_padding: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 개별 파라미터 사용)
        eye_region_offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 개별 파라미터 사용)
        eye_region_offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 개별 파라미터 사용)
        left_eye_region_padding: 왼쪽 눈 영역 패딩 비율
        right_eye_region_padding: 오른쪽 눈 영역 패딩 비율
        left_eye_region_offset_x: 왼쪽 눈 영역 수평 오프셋
        left_eye_region_offset_y: 왼쪽 눈 영역 수직 오프셋
        right_eye_region_offset_x: 오른쪽 눈 영역 수평 오프셋
        right_eye_region_offset_y: 오른쪽 눈 영역 수직 오프셋
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    # 개별 조정 모드 확인
    use_individual = (left_eye_size_ratio is not None) or (right_eye_size_ratio is not None)
    
    if use_individual:
        # 개별 조정 모드: 왼쪽/오른쪽 눈 중 하나라도 변경이 있으면 처리
        left_ratio = left_eye_size_ratio if left_eye_size_ratio is not None else 1.0
        right_ratio = right_eye_size_ratio if right_eye_size_ratio is not None else 1.0
        if abs(left_ratio - 1.0) < 0.01 and abs(right_ratio - 1.0) < 0.01:
            return image
    else:
        # 기본 조정 모드
        if abs(eye_size_ratio - 1.0) < 0.01:
            return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        result = img_array.copy()
        
        # 눈 영역 파라미터 결정 (개별 파라미터가 있으면 사용)
        use_individual_region = (left_eye_region_padding is not None or right_eye_region_padding is not None)
        
        # 왼쪽 눈과 오른쪽 눈 각각 처리
        for eye_name in ['left', 'right']:
            # 개별 파라미터가 있으면 사용, 없으면 기본 파라미터 사용
            if use_individual_region:
                if eye_name == 'left':
                    padding = left_eye_region_padding if left_eye_region_padding is not None else 0.3
                    offset_x = left_eye_region_offset_x if left_eye_region_offset_x is not None else 0.0
                    offset_y = left_eye_region_offset_y if left_eye_region_offset_y is not None else 0.0
                else:
                    padding = right_eye_region_padding if right_eye_region_padding is not None else 0.3
                    offset_x = right_eye_region_offset_x if right_eye_region_offset_x is not None else 0.0
                    offset_y = right_eye_region_offset_y if right_eye_region_offset_y is not None else 0.0
            else:
                padding = eye_region_padding if eye_region_padding is not None else 0.3
                offset_x = eye_region_offset_x if eye_region_offset_x is not None else 0.0
                offset_y = eye_region_offset_y if eye_region_offset_y is not None else 0.0
            
            # 랜드마크 포인트를 사용하여 정확한 눈 영역 계산 (위치 오프셋 포함)
            eye_region, eye_center = _get_eye_region(key_landmarks, img_width, img_height, eye_name, landmarks, 
                                                     padding, offset_x, offset_y)
            x1, y1, x2, y2 = eye_region
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # 눈 영역 추출
            eye_img = result[y1:y2, x1:x2].copy()
            if eye_img.size == 0:
                continue
            
            # 원본 눈 크기
            original_width = x2 - x1
            original_height = y2 - y1
            
            # 눈 크기 조정 (개별 조정 모드 또는 기본 모드)
            if use_individual:
                if eye_name == 'left':
                    current_ratio = left_eye_size_ratio if left_eye_size_ratio is not None else 1.0
                else:
                    current_ratio = right_eye_size_ratio if right_eye_size_ratio is not None else 1.0
            else:
                current_ratio = eye_size_ratio
            
            # 변경이 없으면 스킵
            if abs(current_ratio - 1.0) < 0.01:
                continue
            
            new_width = int(original_width * current_ratio)
            new_height = int(original_height * current_ratio)
            
            if new_width < 1 or new_height < 1:
                continue
            
            # 눈 영역 리사이즈 (고품질 보간 사용)
            eye_resized = cv2.resize(eye_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # 새로운 위치 계산 (중심점 기준, 오프셋이 이미 적용된 eye_center 사용)
            new_x1 = max(0, eye_center[0] - new_width // 2)
            new_y1 = max(0, eye_center[1] - new_height // 2)
            new_x2 = min(img_width, new_x1 + new_width)
            new_y2 = min(img_height, new_y1 + new_height)
            
            # 실제 사용할 크기
            actual_width = new_x2 - new_x1
            actual_height = new_y2 - new_y1
            
            if actual_width < 1 or actual_height < 1:
                continue
            
            # 리사이즈된 눈 영역을 실제 크기에 맞춤
            if actual_width != new_width or actual_height != new_height:
                eye_final = cv2.resize(eye_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
            else:
                eye_final = eye_resized
            
            # 마스크 생성 (부드러운 블렌딩을 위해, 개선된 버전: 시그모이드 함수 기반)
            mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
            
            # 원본 이미지에 블렌딩
            roi = result[new_y1:new_y2, new_x1:new_x2].copy()
            mask_3channel = np.stack([mask] * 3, axis=-1)  # RGB 채널로 확장
            
            # 시그모이드 함수 기반 부드러운 블렌딩
            blended = (roi * (1 - mask_3channel) + eye_final * mask_3channel).astype(np.uint8)
            result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 크기 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_eye_spacing(image, eye_spacing=0.0, landmarks=None, 
                      eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                      left_eye_region_padding=None, right_eye_region_padding=None,
                      left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                      right_eye_region_offset_x=None, right_eye_region_offset_y=None):
    """
    눈 간격을 조정합니다 (두 눈 사이의 거리를 조정).
    
    Args:
        image: PIL.Image 객체
        eye_spacing: 눈 간격 조정 값 (픽셀 단위, 양수=멀어짐, 음수=가까워짐)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        eye_region_padding: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 개별 파라미터 사용)
        eye_region_offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 개별 파라미터 사용)
        eye_region_offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 개별 파라미터 사용)
        left_eye_region_padding: 왼쪽 눈 영역 패딩 비율
        right_eye_region_padding: 오른쪽 눈 영역 패딩 비율
        left_eye_region_offset_x: 왼쪽 눈 영역 수평 오프셋
        left_eye_region_offset_y: 왼쪽 눈 영역 수직 오프셋
        right_eye_region_offset_x: 오른쪽 눈 영역 수평 오프셋
        right_eye_region_offset_y: 오른쪽 눈 영역 수직 오프셋
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(eye_spacing) < 0.1:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        result = img_array.copy()
        
        # 두 눈 중심점 가져오기 (원본 랜드마크 기준 - 간격 조정 계산용)
        left_eye_center_original = key_landmarks['left_eye']
        right_eye_center_original = key_landmarks['right_eye']
        
        # 두 눈 사이의 현재 거리 계산 (원본 기준)
        eye_distance = ((right_eye_center_original[0] - left_eye_center_original[0])**2 + 
                       (right_eye_center_original[1] - left_eye_center_original[1])**2)**0.5
        
        if eye_distance < 1:
            return image
        
        # 간격 조정 방향 계산 (두 눈을 연결하는 벡터 - 원본 기준)
        dx = right_eye_center_original[0] - left_eye_center_original[0]
        dy = right_eye_center_original[1] - left_eye_center_original[1]
        
        # 단위 벡터 계산
        unit_x = dx / eye_distance
        unit_y = dy / eye_distance
        
        # 각 눈의 이동 거리 (간격 조정 값의 절반씩)
        move_distance = eye_spacing / 2.0
        
        # 눈 영역 파라미터 결정 (개별 파라미터가 있으면 사용)
        use_individual_region = (left_eye_region_padding is not None or right_eye_region_padding is not None)
        
        # 왼쪽 눈과 오른쪽 눈 각각 처리
        for eye_name, move_direction in [('left', -1), ('right', 1)]:
            # 개별 파라미터가 있으면 사용, 없으면 기본 파라미터 사용
            if use_individual_region:
                if eye_name == 'left':
                    padding = left_eye_region_padding if left_eye_region_padding is not None else 0.3
                    offset_x = left_eye_region_offset_x if left_eye_region_offset_x is not None else 0.0
                    offset_y = left_eye_region_offset_y if left_eye_region_offset_y is not None else 0.0
                else:
                    padding = right_eye_region_padding if right_eye_region_padding is not None else 0.3
                    offset_x = right_eye_region_offset_x if right_eye_region_offset_x is not None else 0.0
                    offset_y = right_eye_region_offset_y if right_eye_region_offset_y is not None else 0.0
            else:
                padding = eye_region_padding if eye_region_padding is not None else 0.3
                offset_x = eye_region_offset_x if eye_region_offset_x is not None else 0.0
                offset_y = eye_region_offset_y if eye_region_offset_y is not None else 0.0
            
            # 원본 랜드마크 중심점 가져오기 (간격 조정 계산용)
            original_eye_center = left_eye_center_original if eye_name == 'left' else right_eye_center_original
            
            # 랜드마크 포인트를 사용하여 정확한 눈 영역 계산 (위치 오프셋 포함)
            eye_region, eye_center_with_offset = _get_eye_region(key_landmarks, img_width, img_height, eye_name, landmarks, 
                                                    padding, offset_x, offset_y)
            x1, y1, x2, y2 = eye_region
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # 눈 영역 추출
            eye_img = result[y1:y2, x1:x2].copy()
            if eye_img.size == 0:
                continue
            
            # 새로운 눈 위치 계산 (오프셋이 적용된 중심점 기준으로 간격 조정)
            # 오프셋이 적용된 중심점에서 간격 조정 이동을 적용해야 올바른 위치가 됩니다
            new_center_x = int(eye_center_with_offset[0] + move_direction * move_distance * unit_x)
            new_center_y = int(eye_center_with_offset[1] + move_direction * move_distance * unit_y)
            
            # 경계 체크
            new_center_x = max(0, min(img_width - 1, new_center_x))
            new_center_y = max(0, min(img_height - 1, new_center_y))
            
            # 눈 영역 크기
            eye_width = x2 - x1
            eye_height = y2 - y1
            
            # 새로운 위치 계산
            new_x1 = max(0, new_center_x - eye_width // 2)
            new_y1 = max(0, new_center_y - eye_height // 2)
            new_x2 = min(img_width, new_x1 + eye_width)
            new_y2 = min(img_height, new_y1 + eye_height)
            
            # 실제 사용할 크기
            actual_width = new_x2 - new_x1
            actual_height = new_y2 - new_y1
            
            if actual_width < 1 or actual_height < 1:
                continue
            
            # 눈 영역을 새로운 크기에 맞춤
            if actual_width != eye_width or actual_height != eye_height:
                eye_final = cv2.resize(eye_img, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
            else:
                eye_final = eye_img
            
            # 마스크 생성 (부드러운 블렌딩을 위해)
            mask_size = max(15, min(actual_width, actual_height) // 4)
            if mask_size % 2 == 0:
                mask_size += 1
            
            # 타원형 마스크 생성
            center_x = actual_width // 2
            center_y = actual_height // 2
            radius_x = max(1, actual_width // 2 - mask_size // 3)
            radius_y = max(1, actual_height // 2 - mask_size // 3)
            
            y_grid, x_grid = np.ogrid[:actual_height, :actual_width]
            ellipse_mask = ((x_grid - center_x) / radius_x)**2 + ((y_grid - center_y) / radius_y)**2 <= 1.0
            mask = (ellipse_mask.astype(np.uint8) * 255)
            
            # 가우시안 블러로 마스크 부드럽게
            mask = cv2.GaussianBlur(mask, (mask_size, mask_size), 0)
            
            # 원본 이미지에 블렌딩
            roi = result[new_y1:new_y2, new_x1:new_x2].copy()
            mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
            
            # 부드러운 블렌딩
            blended = (roi * (1 - mask_3channel) + eye_final * mask_3channel).astype(np.uint8)
            result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 간격 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_eye_position(image, eye_position_x=0.0, eye_position_y=0.0, landmarks=None,
                        eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                        left_eye_region_padding=None, right_eye_region_padding=None,
                        left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                        right_eye_region_offset_x=None, right_eye_region_offset_y=None,
                        eye='left'):
    """
    눈 위치를 조정합니다 (수직/수평 위치 미세 조정).
    
    Args:
        image: PIL.Image 객체
        eye_position_x: 눈 수평 위치 조정 (픽셀 단위, 양수=오른쪽, 음수=왼쪽)
        eye_position_y: 눈 수직 위치 조정 (픽셀 단위, 양수=아래, 음수=위)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        eye_region_padding: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 개별 파라미터 사용)
        eye_region_offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 개별 파라미터 사용)
        eye_region_offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 개별 파라미터 사용)
        left_eye_region_padding: 왼쪽 눈 영역 패딩 비율
        right_eye_region_padding: 오른쪽 눈 영역 패딩 비율
        left_eye_region_offset_x: 왼쪽 눈 영역 수평 오프셋
        left_eye_region_offset_y: 왼쪽 눈 영역 수직 오프셋
        right_eye_region_offset_x: 오른쪽 눈 영역 수평 오프셋
        right_eye_region_offset_y: 오른쪽 눈 영역 수직 오프셋
        eye: 'left' 또는 'right' (어떤 눈을 조정할지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(eye_position_x) < 0.1 and abs(eye_position_y) < 0.1:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        result = img_array.copy()
        
        # 눈 영역 파라미터 결정 (개별 파라미터가 있으면 사용)
        use_individual_region = (left_eye_region_padding is not None or right_eye_region_padding is not None)
        
        # 지정된 눈만 처리
        eye_name = eye
        # 개별 파라미터가 있으면 사용, 없으면 기본 파라미터 사용
        if use_individual_region:
            if eye_name == 'left':
                padding = left_eye_region_padding if left_eye_region_padding is not None else 0.3
                offset_x = left_eye_region_offset_x if left_eye_region_offset_x is not None else 0.0
                offset_y = left_eye_region_offset_y if left_eye_region_offset_y is not None else 0.0
            else:
                padding = right_eye_region_padding if right_eye_region_padding is not None else 0.3
                offset_x = right_eye_region_offset_x if right_eye_region_offset_x is not None else 0.0
                offset_y = right_eye_region_offset_y if right_eye_region_offset_y is not None else 0.0
        else:
            padding = eye_region_padding if eye_region_padding is not None else 0.3
            offset_x = eye_region_offset_x if eye_region_offset_x is not None else 0.0
            offset_y = eye_region_offset_y if eye_region_offset_y is not None else 0.0
        
        # 원본 랜드마크 중심점 가져오기 (위치 조정 계산용)
        original_eye_center = key_landmarks['left_eye'] if eye_name == 'left' else key_landmarks['right_eye']
        
        # 랜드마크 포인트를 사용하여 정확한 눈 영역 계산 (위치 오프셋 포함)
        eye_region, eye_center_with_offset = _get_eye_region(key_landmarks, img_width, img_height, eye_name, landmarks, 
                                                padding, offset_x, offset_y)
        x1, y1, x2, y2 = eye_region
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 눈 영역 추출
        eye_img = result[y1:y2, x1:x2].copy()
        if eye_img.size == 0:
            return image
        
        # 새로운 눈 위치 계산 (오프셋이 적용된 중심점 기준으로 위치 조정)
        # 오프셋이 적용된 중심점에서 위치 조정 값을 더해야 올바른 위치가 됩니다
        new_center_x = int(eye_center_with_offset[0] + eye_position_x)
        new_center_y = int(eye_center_with_offset[1] + eye_position_y)
        
        # 경계 체크
        new_center_x = max(0, min(img_width - 1, new_center_x))
        new_center_y = max(0, min(img_height - 1, new_center_y))
        
        # 눈 영역 크기
        eye_width = x2 - x1
        eye_height = y2 - y1
        
        # 새로운 위치 계산
        new_x1 = max(0, new_center_x - eye_width // 2)
        new_y1 = max(0, new_center_y - eye_height // 2)
        new_x2 = min(img_width, new_x1 + eye_width)
        new_y2 = min(img_height, new_y1 + eye_height)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 눈 영역을 새로운 크기에 맞춤
        if actual_width != eye_width or actual_height != eye_height:
            eye_final = cv2.resize(eye_img, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        else:
            eye_final = eye_img
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask_size = max(15, min(actual_width, actual_height) // 4)
        if mask_size % 2 == 0:
            mask_size += 1
        
        # 타원형 마스크 생성
        center_x = actual_width // 2
        center_y = actual_height // 2
        radius_x = max(1, actual_width // 2 - mask_size // 3)
        radius_y = max(1, actual_height // 2 - mask_size // 3)
        
        y_grid, x_grid = np.ogrid[:actual_height, :actual_width]
        ellipse_mask = ((x_grid - center_x) / radius_x)**2 + ((y_grid - center_y) / radius_y)**2 <= 1.0
        mask = (ellipse_mask.astype(np.uint8) * 255)
        
        # 가우시안 블러로 마스크 부드럽게
        mask = cv2.GaussianBlur(mask, (mask_size, mask_size), 0)
        
        # 원본 이미지에 블렌딩
        roi = result[new_y1:new_y2, new_x1:new_x2].copy()
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        
        # 부드러운 블렌딩
        blended = (roi * (1 - mask_3channel) + eye_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 위치 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_nose_size(image, nose_size_ratio=1.0, landmarks=None):
    """
    코 크기를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        nose_size_ratio: 코 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(nose_size_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['nose'] is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 랜드마크 포인트를 사용하여 정확한 코 영역 계산
        nose_region, nose_center = _get_nose_region(key_landmarks, img_width, img_height, landmarks)
        x1, y1, x2, y2 = nose_region
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 코 영역 추출
        nose_img = img_array[y1:y2, x1:x2]
        if nose_img.size == 0:
            return image
        
        # 코 크기 조정
        new_width = int((x2 - x1) * nose_size_ratio)
        new_height = int((y2 - y1) * nose_size_ratio)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 코 영역 리사이즈
        nose_resized = cv2.resize(nose_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (중심점 기준)
        new_x1 = max(0, nose_center[0] - new_width // 2)
        new_y1 = max(0, nose_center[1] - new_height // 2)
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, new_y1 + new_height)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 코 영역을 실제 크기에 맞춤
        nose_final = cv2.resize(nose_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해, 개선된 버전: 시그모이드 함수 기반)
        mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = np.stack([mask] * 3, axis=-1)  # RGB 채널로 확장
        
        # 시그모이드 함수 기반 부드러운 블렌딩
        blended = (roi * (1 - mask_3channel) + nose_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 코 크기 조정 실패: {e}")
        return image


def adjust_jaw(image, jaw_adjustment=0.0, landmarks=None):
    """
    턱선을 조정합니다.
    
    Args:
        image: PIL.Image 객체
        jaw_adjustment: 턱선 조정 값 (-50 ~ +50, 음수=작게, 양수=크게)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(jaw_adjustment) < 0.1:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 얼굴 중심과 입 위치 사용
        face_center = key_landmarks['face_center']
        mouth = key_landmarks['mouth']
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        
        if mouth is None:
            return image
        
        # 얼굴 너비 추정
        face_width = abs(right_eye[0] - left_eye[0]) * 2.5
        
        # 턱 영역 계산 (입 아래쪽)
        jaw_y = mouth[1] + int(abs(mouth[1] - face_center[1]) * 0.5)
        jaw_y = min(img_height - 1, max(0, jaw_y))
        
        # 턱 조정 비율 계산 (음수면 작게, 양수면 크게)
        # -50 ~ +50을 0.7 ~ 1.3 비율로 변환
        jaw_ratio = 1.0 + (jaw_adjustment / 50.0) * 0.3
        jaw_ratio = max(0.7, min(1.3, jaw_ratio))
        
        # 턱 영역 계산
        jaw_height = int(face_width * 0.3)
        x1 = max(0, int(face_center[0] - face_width / 2))
        y1 = max(0, jaw_y - jaw_height // 2)
        x2 = min(img_width, int(face_center[0] + face_width / 2))
        y2 = min(img_height, jaw_y + jaw_height // 2)
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 턱 영역 추출
        jaw_img = img_array[y1:y2, x1:x2]
        if jaw_img.size == 0:
            return image
        
        # 턱 크기 조정 (너비만 조정)
        new_width = int((x2 - x1) * jaw_ratio)
        new_height = y2 - y1
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 턱 영역 리사이즈
        jaw_resized = cv2.resize(jaw_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (중심점 기준)
        new_x1 = max(0, face_center[0] - new_width // 2)
        new_y1 = y1
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = y2
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 턱 영역을 실제 크기에 맞춤
        jaw_final = cv2.resize(jaw_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (25, 25), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + jaw_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 턱선 조정 실패: {e}")
        return image


def adjust_face_size(image, width_ratio=1.0, height_ratio=1.0, landmarks=None):
    """
    얼굴 크기를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        width_ratio: 얼굴 너비 비율 (1.0 = 원본)
        height_ratio: 얼굴 높이 비율 (1.0 = 원본)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(width_ratio - 1.0) < 0.01 and abs(height_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 얼굴 영역 계산 (눈과 입을 기준으로)
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        mouth = key_landmarks['mouth']
        face_center = key_landmarks['face_center']
        
        if mouth is None:
            return image
        
        # 얼굴 너비와 높이 추정
        face_width = abs(right_eye[0] - left_eye[0]) * 2.5
        face_height = abs(mouth[1] - (left_eye[1] + right_eye[1]) // 2) * 2.5
        
        # 얼굴 영역 계산
        x1 = max(0, int(face_center[0] - face_width / 2))
        y1 = max(0, int(face_center[1] - face_height / 2))
        x2 = min(img_width, int(face_center[0] + face_width / 2))
        y2 = min(img_height, int(face_center[1] + face_height / 2))
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 얼굴 영역 추출
        face_img = img_array[y1:y2, x1:x2]
        if face_img.size == 0:
            return image
        
        # 얼굴 크기 조정
        new_width = int((x2 - x1) * width_ratio)
        new_height = int((y2 - y1) * height_ratio)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 얼굴 영역 리사이즈
        face_resized = cv2.resize(face_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (중심점 기준)
        new_x1 = max(0, face_center[0] - new_width // 2)
        new_y1 = max(0, face_center[1] - new_height // 2)
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, new_y1 + new_height)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 얼굴 영역을 실제 크기에 맞춤
        face_final = cv2.resize(face_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (25, 25), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + face_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 얼굴 크기 조정 실패: {e}")
        return image


def adjust_mouth_size(image, mouth_size_ratio=1.0, mouth_width_ratio=1.0, landmarks=None):
    """
    입 크기와 너비를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        mouth_size_ratio: 입 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        mouth_width_ratio: 입 너비 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(mouth_size_ratio - 1.0) < 0.01 and abs(mouth_width_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 랜드마크 포인트를 사용하여 정확한 입 영역 계산
        mouth_region, mouth_center = _get_mouth_region(key_landmarks, img_width, img_height, landmarks)
        x1, y1, x2, y2 = mouth_region
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 입 영역 추출
        mouth_img = img_array[y1:y2, x1:x2]
        if mouth_img.size == 0:
            return image
        
        # 입 크기 조정 (크기와 너비 모두 적용)
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = int(original_width * mouth_width_ratio)
        new_height = int(original_height * mouth_size_ratio)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 입 영역 리사이즈
        mouth_resized = cv2.resize(mouth_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (중심점 기준)
        new_x1 = max(0, mouth_center[0] - new_width // 2)
        new_y1 = max(0, mouth_center[1] - new_height // 2)
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, new_y1 + new_height)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 입 영역을 실제 크기에 맞춤
        mouth_final = cv2.resize(mouth_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해, 개선된 버전: 시그모이드 함수 기반)
        mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = np.stack([mask] * 3, axis=-1)  # RGB 채널로 확장
        
        # 시그모이드 함수 기반 부드러운 블렌딩
        blended = (roi * (1 - mask_3channel) + mouth_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 입 크기 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_upper_lip_size(image, upper_lip_size_ratio=1.0, upper_lip_width_ratio=1.0, landmarks=None):
    """
    윗입술 크기와 너비를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        upper_lip_size_ratio: 윗입술 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        upper_lip_width_ratio: 윗입술 너비 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(upper_lip_size_ratio - 1.0) < 0.01 and abs(upper_lip_width_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        mouth_center = key_landmarks['mouth']
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        
        # 입 크기 추정 (두 눈 사이 거리의 약 1/2)
        eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
        mouth_radius_x = int(eye_distance * 0.3)  # 입 너비 (수평)
        mouth_radius_y = int(eye_distance * 0.15)  # 입 높이 (수직)
        
        # 윗입술 영역 계산 (입 중심점 위쪽 절반)
        x1 = max(0, mouth_center[0] - mouth_radius_x)
        y1 = max(0, mouth_center[1] - mouth_radius_y)  # 입 중심점 위쪽
        x2 = min(img_width, mouth_center[0] + mouth_radius_x)
        y2 = min(img_height, mouth_center[1])  # 입 중심점까지
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 윗입술 영역 추출
        upper_lip_img = img_array[y1:y2, x1:x2]
        if upper_lip_img.size == 0:
            return image
        
        # 윗입술 크기 조정
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = int(original_width * upper_lip_width_ratio)
        new_height = int(original_height * upper_lip_size_ratio)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 윗입술 영역 리사이즈
        upper_lip_resized = cv2.resize(upper_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점 기준, 위쪽으로 확장)
        new_x1 = max(0, mouth_center[0] - new_width // 2)
        new_y1 = max(0, mouth_center[1] - new_height)  # 입 중심점 위쪽으로
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, mouth_center[1])  # 입 중심점까지
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 윗입술 영역을 실제 크기에 맞춤
        upper_lip_final = cv2.resize(upper_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + upper_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 윗입술 크기 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_lower_lip_size(image, lower_lip_size_ratio=1.0, lower_lip_width_ratio=1.0, landmarks=None):
    """
    아래입술 크기와 너비를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        lower_lip_size_ratio: 아래입술 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        lower_lip_width_ratio: 아래입술 너비 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(lower_lip_size_ratio - 1.0) < 0.01 and abs(lower_lip_width_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        mouth_center = key_landmarks['mouth']
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        
        # 입 크기 추정 (두 눈 사이 거리의 약 1/2)
        eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
        mouth_radius_x = int(eye_distance * 0.3)  # 입 너비 (수평)
        mouth_radius_y = int(eye_distance * 0.15)  # 입 높이 (수직)
        
        # 아래입술 영역 계산 (입 중심점 아래쪽 절반)
        x1 = max(0, mouth_center[0] - mouth_radius_x)
        y1 = max(0, mouth_center[1])  # 입 중심점부터
        x2 = min(img_width, mouth_center[0] + mouth_radius_x)
        y2 = min(img_height, mouth_center[1] + mouth_radius_y)  # 입 중심점 아래쪽
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 아래입술 영역 추출
        lower_lip_img = img_array[y1:y2, x1:x2]
        if lower_lip_img.size == 0:
            return image
        
        # 아래입술 크기 조정
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = int(original_width * lower_lip_width_ratio)
        new_height = int(original_height * lower_lip_size_ratio)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 아래입술 영역 리사이즈
        lower_lip_resized = cv2.resize(lower_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점 기준, 아래쪽으로 확장)
        new_x1 = max(0, mouth_center[0] - new_width // 2)
        new_y1 = max(0, mouth_center[1])  # 입 중심점부터
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, mouth_center[1] + new_height)  # 입 중심점 아래쪽으로
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 아래입술 영역을 실제 크기에 맞춤
        lower_lip_final = cv2.resize(lower_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + lower_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 아래입술 크기 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_upper_lip_shape(image, upper_lip_shape_ratio=1.0, landmarks=None,
                          lip_region_padding_x=None, lip_region_padding_y=None, 
                          lip_region_offset_x=None, lip_region_offset_y=None):
    """
    윗입술 모양(두께/볼륨)을 조정합니다.
    MediaPipe 랜드마크 인덱스를 사용하여 정확한 윗입술 영역만 조정합니다.
    
    Args:
        image: PIL.Image 객체
        upper_lip_shape_ratio: 윗입술 모양 비율 (1.0 = 원본, 2.0 = 두꺼움, 0.5 = 얇음)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        lip_region_padding_x: 입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        lip_region_padding_y: 입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        lip_region_offset_x: 입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        lip_region_offset_y: 입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    # 기본값 설정 (None이면 기본값 사용)
    if lip_region_padding_x is None:
        lip_region_padding_x = 0.2
    if lip_region_padding_y is None:
        lip_region_padding_y = 0.3
    if lip_region_offset_x is None:
        lip_region_offset_x = 0.0
    if lip_region_offset_y is None:
        lip_region_offset_y = 0.0
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(upper_lip_shape_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 주요 랜드마크 추출 (입 중심점 계산용)
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        mouth_center = key_landmarks['mouth']
        mouth_center_y = mouth_center[1]
        
        # MediaPipe 윗입술 랜드마크 인덱스 (웹 검색 결과 기반)
        # 윗입술 외곽선 인덱스 (입 중심점 위쪽에 있는 포인트만 선택)
        ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
        
        # 윗입술 랜드마크 포인트 추출 (입 중심점 위쪽에 있는 포인트만)
        upper_lip_points = []
        for i in ALL_LIP_INDICES:
            if i < len(landmarks):
                point = landmarks[i]
                # 입 중심점보다 위쪽에 있는 포인트만 윗입술로 간주
                if point[1] < mouth_center_y:
                    upper_lip_points.append(point)
        
        if not upper_lip_points:
            return image
        
        # 윗입술 영역의 경계 계산 (실제 랜드마크 포인트 기반)
        upper_lip_x_coords = [p[0] for p in upper_lip_points]
        upper_lip_y_coords = [p[1] for p in upper_lip_points]
        
        x_min = int(min(upper_lip_x_coords))
        x_max = int(max(upper_lip_x_coords))
        y_min = int(min(upper_lip_y_coords))
        y_max = int(max(upper_lip_y_coords))
        
        # 윗입술 영역은 입 중심점 위쪽으로 제한
        y_max = min(y_max, int(mouth_center_y))
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 윗입술 영역에 패딩 추가 (입술 두께 조정을 위해)
        # 수직 패딩은 위쪽으로만 추가 (아래쪽은 입 중심점까지만)
        # None 체크 (방어적 프로그래밍)
        if lip_region_padding_x is None:
            lip_region_padding_x = 0.2
        if lip_region_padding_y is None:
            lip_region_padding_y = 0.3
        if lip_region_offset_x is None:
            lip_region_offset_x = 0.0
        if lip_region_offset_y is None:
            lip_region_offset_y = 0.0
        
        padding_x = int((x_max - x_min) * lip_region_padding_x)  # 가로 패딩 비율 적용
        padding_y = int((y_max - y_min) * lip_region_padding_y)  # 세로 패딩 비율 적용
        x1 = max(0, x_min - padding_x + int(lip_region_offset_x))
        y1 = max(0, y_min - padding_y + int(lip_region_offset_y))  # 위쪽 패딩 + 오프셋
        x2 = min(img_width, x_max + padding_x + int(lip_region_offset_x))
        y2 = min(img_height, y_max + int(lip_region_offset_y))  # 아래쪽은 입 중심점까지만 (패딩 없음, 오프셋만)
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 윗입술 영역 추출
        upper_lip_img = img_array[y1:y2, x1:x2]
        if upper_lip_img.size == 0:
            return image
        
        # 윗입술 두께 조정 (수직 크기만 조정하여 두께 변경)
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = original_width  # 너비는 유지
        new_height = int(original_height * upper_lip_shape_ratio)  # 두께만 조정
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 윗입술 영역 리사이즈 (두께 조정)
        upper_lip_resized = cv2.resize(upper_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점을 아래쪽 고정점으로 사용, 위쪽으로만 확장)
        center_x = (x_min + x_max) // 2
        
        # 아래쪽 경계(입 중심점)를 고정하고 위쪽으로만 확장
        new_x1 = max(0, center_x - new_width // 2)
        new_y2 = y2  # 아래쪽 경계 고정 (입 중심점)
        new_y1 = max(0, new_y2 - new_height)  # 위쪽으로 확장
        new_x2 = min(img_width, new_x1 + new_width)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 윗입술 영역을 실제 크기에 맞춤
        upper_lip_final = cv2.resize(upper_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + upper_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 윗입술 모양 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_lower_lip_shape(image, lower_lip_shape_ratio=1.0, landmarks=None,
                          lip_region_padding_x=None, lip_region_padding_y=None,
                          lip_region_offset_x=None, lip_region_offset_y=None):
    """
    아랫입술 모양(두께/볼륨)을 조정합니다.
    MediaPipe 랜드마크 인덱스를 사용하여 정확한 아래입술 영역만 조정합니다.
    
    Args:
        image: PIL.Image 객체
        lower_lip_shape_ratio: 아랫입술 모양 비율 (1.0 = 원본, 2.0 = 두꺼움, 0.5 = 얇음)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        lip_region_padding_x: 입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        lip_region_padding_y: 입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        lip_region_offset_x: 입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        lip_region_offset_y: 입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    # 기본값 설정 (None이면 기본값 사용)
    if lip_region_padding_x is None:
        lip_region_padding_x = 0.2
    if lip_region_padding_y is None:
        lip_region_padding_y = 0.3
    if lip_region_offset_x is None:
        lip_region_offset_x = 0.0
    if lip_region_offset_y is None:
        lip_region_offset_y = 0.0
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(lower_lip_shape_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 주요 랜드마크 추출 (입 중심점 계산용)
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        mouth_center = key_landmarks['mouth']
        mouth_center_y = mouth_center[1]
        
        # MediaPipe 아래입술 랜드마크 인덱스 (웹 검색 결과 기반)
        # 아래입술 외곽선 인덱스 (입 중심점 아래쪽에 있는 포인트만 선택)
        ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
        
        # 아래입술 랜드마크 포인트 추출 (입 중심점 아래쪽에 있는 포인트만)
        lower_lip_points = []
        for i in ALL_LIP_INDICES:
            if i < len(landmarks):
                point = landmarks[i]
                # 입 중심점보다 아래쪽에 있는 포인트만 아래입술로 간주
                if point[1] > mouth_center_y:
                    lower_lip_points.append(point)
        
        if not lower_lip_points:
            return image
        
        # 아래입술 영역의 경계 계산 (실제 랜드마크 포인트 기반)
        lower_lip_x_coords = [p[0] for p in lower_lip_points]
        lower_lip_y_coords = [p[1] for p in lower_lip_points]
        
        x_min = int(min(lower_lip_x_coords))
        x_max = int(max(lower_lip_x_coords))
        y_min = int(min(lower_lip_y_coords))
        y_max = int(max(lower_lip_y_coords))
        
        # 아래입술 영역은 입 중심점 아래쪽으로 제한
        y_min = max(y_min, int(mouth_center_y))
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 아래입술 영역에 패딩 추가 (입술 두께 조정을 위해)
        # 수직 패딩은 아래쪽으로만 추가 (위쪽은 입 중심점부터)
        # None 체크 (방어적 프로그래밍)
        if lip_region_padding_x is None:
            lip_region_padding_x = 0.2
        if lip_region_padding_y is None:
            lip_region_padding_y = 0.3
        if lip_region_offset_x is None:
            lip_region_offset_x = 0.0
        if lip_region_offset_y is None:
            lip_region_offset_y = 0.0
        
        padding_x = int((x_max - x_min) * lip_region_padding_x)  # 가로 패딩 비율 적용
        padding_y = int((y_max - y_min) * lip_region_padding_y)  # 세로 패딩 비율 적용
        x1 = max(0, x_min - padding_x + int(lip_region_offset_x))
        y1 = max(0, y_min + int(lip_region_offset_y))  # 위쪽은 입 중심점부터 (패딩 없음, 오프셋만)
        x2 = min(img_width, x_max + padding_x + int(lip_region_offset_x))
        y2 = min(img_height, y_max + padding_y + int(lip_region_offset_y))  # 아래쪽 패딩 + 오프셋
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 아래입술 영역 추출
        lower_lip_img = img_array[y1:y2, x1:x2]
        if lower_lip_img.size == 0:
            return image
        
        # 아래입술 두께 조정 (수직 크기만 조정하여 두께 변경)
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = original_width  # 너비는 유지
        new_height = int(original_height * lower_lip_shape_ratio)  # 두께만 조정
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 아래입술 영역 리사이즈 (두께 조정)
        lower_lip_resized = cv2.resize(lower_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점을 위쪽 고정점으로 사용, 아래쪽으로만 확장)
        center_x = (x_min + x_max) // 2
        
        # 위쪽 경계(입 중심점)를 고정하고 아래쪽으로만 확장
        new_x1 = max(0, center_x - new_width // 2)
        new_y1 = y1  # 위쪽 경계 고정 (입 중심점)
        new_y2 = min(img_height, new_y1 + new_height)  # 아래쪽으로 확장
        new_x2 = min(img_width, new_x1 + new_width)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 아래입술 영역을 실제 크기에 맞춤
        lower_lip_final = cv2.resize(lower_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + lower_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 아래입술 모양 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_upper_lip_width(image, upper_lip_width_ratio=1.0, landmarks=None,
                          lip_region_padding_x=None, lip_region_padding_y=None,
                          lip_region_offset_x=None, lip_region_offset_y=None):
    """
    윗입술 너비를 조정합니다.
    MediaPipe 랜드마크 인덱스를 사용하여 정확한 윗입술 영역만 조정합니다.
    
    Args:
        image: PIL.Image 객체
        upper_lip_width_ratio: 윗입술 너비 비율 (1.0 = 원본, 2.0 = 넓음, 0.5 = 좁음)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        lip_region_padding_x: 입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        lip_region_padding_y: 입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        lip_region_offset_x: 입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        lip_region_offset_y: 입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    # 기본값 설정 (None이면 기본값 사용)
    if lip_region_padding_x is None:
        lip_region_padding_x = 0.2
    if lip_region_padding_y is None:
        lip_region_padding_y = 0.3
    if lip_region_offset_x is None:
        lip_region_offset_x = 0.0
    if lip_region_offset_y is None:
        lip_region_offset_y = 0.0
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(upper_lip_width_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 주요 랜드마크 추출 (입 중심점 계산용)
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        mouth_center = key_landmarks['mouth']
        mouth_center_y = mouth_center[1]
        
        # MediaPipe 윗입술 랜드마크 인덱스
        ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
        
        # 윗입술 랜드마크 포인트 추출 (입 중심점 위쪽에 있는 포인트만)
        upper_lip_points = []
        for i in ALL_LIP_INDICES:
            if i < len(landmarks):
                point = landmarks[i]
                if point[1] < mouth_center_y:
                    upper_lip_points.append(point)
        
        if not upper_lip_points:
            return image
        
        # 윗입술 영역의 경계 계산
        upper_lip_x_coords = [p[0] for p in upper_lip_points]
        upper_lip_y_coords = [p[1] for p in upper_lip_points]
        
        x_min = int(min(upper_lip_x_coords))
        x_max = int(max(upper_lip_x_coords))
        y_min = int(min(upper_lip_y_coords))
        y_max = int(max(upper_lip_y_coords))
        
        # 윗입술 영역은 입 중심점 위쪽으로 제한
        y_max = min(y_max, int(mouth_center_y))
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 윗입술 영역에 패딩 추가 (파라미터 적용)
        # None 체크 (방어적 프로그래밍)
        if lip_region_padding_x is None:
            lip_region_padding_x = 0.2
        if lip_region_padding_y is None:
            lip_region_padding_y = 0.3
        if lip_region_offset_x is None:
            lip_region_offset_x = 0.0
        if lip_region_offset_y is None:
            lip_region_offset_y = 0.0
        
        padding_x = int((x_max - x_min) * lip_region_padding_x)
        padding_y = int((y_max - y_min) * lip_region_padding_y)
        x1 = max(0, x_min - padding_x + int(lip_region_offset_x))
        y1 = max(0, y_min - padding_y + int(lip_region_offset_y))
        x2 = min(img_width, x_max + padding_x + int(lip_region_offset_x))
        y2 = min(img_height, y_max + int(lip_region_offset_y))
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 윗입술 영역 추출
        upper_lip_img = img_array[y1:y2, x1:x2]
        if upper_lip_img.size == 0:
            return image
        
        # 윗입술 너비 조정 (수평 크기만 조정하여 너비 변경)
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = int(original_width * upper_lip_width_ratio)  # 너비만 조정
        new_height = original_height  # 높이는 유지
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 윗입술 영역 리사이즈 (너비 조정)
        upper_lip_resized = cv2.resize(upper_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점을 아래쪽 고정점으로 사용, 좌우로 확장)
        center_x = (x_min + x_max) // 2
        
        # 아래쪽 경계(입 중심점)를 고정하고 좌우로 확장
        new_x1 = max(0, center_x - new_width // 2)
        new_y2 = y2  # 아래쪽 경계 고정 (입 중심점)
        new_y1 = max(0, new_y2 - new_height)  # 위쪽은 높이 유지
        new_x2 = min(img_width, new_x1 + new_width)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 윗입술 영역을 실제 크기에 맞춤
        upper_lip_final = cv2.resize(upper_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + upper_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 윗입술 너비 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_lower_lip_width(image, lower_lip_width_ratio=1.0, landmarks=None,
                          lip_region_padding_x=None, lip_region_padding_y=None,
                          lip_region_offset_x=None, lip_region_offset_y=None):
    """
    아랫입술 너비를 조정합니다.
    MediaPipe 랜드마크 인덱스를 사용하여 정확한 아래입술 영역만 조정합니다.
    
    Args:
        image: PIL.Image 객체
        lower_lip_width_ratio: 아랫입술 너비 비율 (1.0 = 원본, 2.0 = 넓음, 0.5 = 좁음)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        lip_region_padding_x: 입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        lip_region_padding_y: 입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        lip_region_offset_x: 입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        lip_region_offset_y: 입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    # 기본값 설정 (None이면 기본값 사용)
    if lip_region_padding_x is None:
        lip_region_padding_x = 0.2
    if lip_region_padding_y is None:
        lip_region_padding_y = 0.3
    if lip_region_offset_x is None:
        lip_region_offset_x = 0.0
    if lip_region_offset_y is None:
        lip_region_offset_y = 0.0
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(lower_lip_width_ratio - 1.0) < 0.01:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 주요 랜드마크 추출 (입 중심점 계산용)
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        mouth_center = key_landmarks['mouth']
        mouth_center_y = mouth_center[1]
        
        # MediaPipe 아래입술 랜드마크 인덱스
        ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
        
        # 아래입술 랜드마크 포인트 추출 (입 중심점 아래쪽에 있는 포인트만)
        lower_lip_points = []
        for i in ALL_LIP_INDICES:
            if i < len(landmarks):
                point = landmarks[i]
                if point[1] > mouth_center_y:
                    lower_lip_points.append(point)
        
        if not lower_lip_points:
            return image
        
        # 아래입술 영역의 경계 계산
        lower_lip_x_coords = [p[0] for p in lower_lip_points]
        lower_lip_y_coords = [p[1] for p in lower_lip_points]
        
        x_min = int(min(lower_lip_x_coords))
        x_max = int(max(lower_lip_x_coords))
        y_min = int(min(lower_lip_y_coords))
        y_max = int(max(lower_lip_y_coords))
        
        # 아래입술 영역은 입 중심점 아래쪽으로 제한
        y_min = max(y_min, int(mouth_center_y))
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 아래입술 영역에 패딩 추가 (파라미터 적용)
        # None 체크 (방어적 프로그래밍)
        if lip_region_padding_x is None:
            lip_region_padding_x = 0.2
        if lip_region_padding_y is None:
            lip_region_padding_y = 0.3
        if lip_region_offset_x is None:
            lip_region_offset_x = 0.0
        if lip_region_offset_y is None:
            lip_region_offset_y = 0.0
        
        padding_x = int((x_max - x_min) * lip_region_padding_x)
        padding_y = int((y_max - y_min) * lip_region_padding_y)
        x1 = max(0, x_min - padding_x + int(lip_region_offset_x))
        y1 = max(0, y_min + int(lip_region_offset_y))
        x2 = min(img_width, x_max + padding_x + int(lip_region_offset_x))
        y2 = min(img_height, y_max + padding_y + int(lip_region_offset_y))
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 아래입술 영역 추출
        lower_lip_img = img_array[y1:y2, x1:x2]
        if lower_lip_img.size == 0:
            return image
        
        # 아래입술 너비 조정 (수평 크기만 조정하여 너비 변경)
        original_width = x2 - x1
        original_height = y2 - y1
        new_width = int(original_width * lower_lip_width_ratio)  # 너비만 조정
        new_height = original_height  # 높이는 유지
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 아래입술 영역 리사이즈 (너비 조정)
        lower_lip_resized = cv2.resize(lower_lip_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (입 중심점을 위쪽 고정점으로 사용, 좌우로 확장)
        center_x = (x_min + x_max) // 2
        
        # 위쪽 경계(입 중심점)를 고정하고 좌우로 확장
        new_x1 = max(0, center_x - new_width // 2)
        new_y1 = y1  # 위쪽 경계 고정 (입 중심점)
        new_y2 = min(img_height, new_y1 + new_height)  # 아래쪽은 높이 유지
        new_x2 = min(img_width, new_x1 + new_width)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 아래입술 영역을 실제 크기에 맞춤
        lower_lip_final = cv2.resize(lower_lip_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
        blended = (roi * (1 - mask_3channel) + lower_lip_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 아래입술 너비 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def adjust_lip_vertical_move(image, upper_lip_vertical_move=0.0, lower_lip_vertical_move=0.0, landmarks=None,
                              upper_lip_region_padding_x=None, upper_lip_region_padding_y=None,
                              lower_lip_region_padding_x=None, lower_lip_region_padding_y=None,
                              upper_lip_region_offset_x=None, upper_lip_region_offset_y=None,
                              lower_lip_region_offset_x=None, lower_lip_region_offset_y=None):
    """
    입술 수직 이동을 조정합니다. 윗입술과 아래입술을 각각 독립적으로 이동시킵니다.
    
    Args:
        image: PIL.Image 객체
        upper_lip_vertical_move: 윗입술 수직 이동 (-50 ~ +50 픽셀, 양수=위로, 음수=아래로)
        lower_lip_vertical_move: 아랫입술 수직 이동 (-50 ~ +50 픽셀, 양수=아래로, 음수=위로)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        upper_lip_region_padding_x: 윗입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        upper_lip_region_padding_y: 윗입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        lower_lip_region_padding_x: 아래입술 영역 가로 패딩 비율 (None이면 기본값 0.2 사용)
        lower_lip_region_padding_y: 아래입술 영역 세로 패딩 비율 (None이면 기본값 0.3 사용)
        upper_lip_region_offset_x: 윗입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        upper_lip_region_offset_y: 윗입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
        lower_lip_region_offset_x: 아래입술 영역 수평 오프셋 (None이면 기본값 0.0 사용)
        lower_lip_region_offset_y: 아래입술 영역 수직 오프셋 (None이면 기본값 0.0 사용)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    # 기본값 설정 (None이면 기본값 사용)
    if upper_lip_region_padding_x is None:
        upper_lip_region_padding_x = 0.2
    if upper_lip_region_padding_y is None:
        upper_lip_region_padding_y = 0.3
    if lower_lip_region_padding_x is None:
        lower_lip_region_padding_x = 0.2
    if lower_lip_region_padding_y is None:
        lower_lip_region_padding_y = 0.3
    if upper_lip_region_offset_x is None:
        upper_lip_region_offset_x = 0.0
    if upper_lip_region_offset_y is None:
        upper_lip_region_offset_y = 0.0
    if lower_lip_region_offset_x is None:
        lower_lip_region_offset_x = 0.0
    if lower_lip_region_offset_y is None:
        lower_lip_region_offset_y = 0.0
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(upper_lip_vertical_move) < 0.1 and abs(lower_lip_vertical_move) < 0.1:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks['mouth'] is None:
            return image
        
        mouth_center = key_landmarks['mouth']
        mouth_center_y = mouth_center[1]
        
        # MediaPipe 입술 랜드마크 인덱스
        ALL_LIP_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
        
        # 윗입술과 아래입술 포인트 분리
        upper_lip_points = []
        lower_lip_points = []
        for i in ALL_LIP_INDICES:
            if i < len(landmarks):
                point = landmarks[i]
                if point[1] < mouth_center_y:
                    upper_lip_points.append(point)
                elif point[1] > mouth_center_y:
                    lower_lip_points.append(point)
        
        if not upper_lip_points or not lower_lip_points:
            return image
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 윗입술 이동 (양수면 위로, 음수면 아래로)
        upper_move_y = -int(upper_lip_vertical_move)  # 양수면 위로 이동
        
        # 아래입술 이동 (양수면 아래로, 음수면 위로)
        lower_move_y = int(lower_lip_vertical_move)  # 양수면 아래로 이동
        
        result = img_array.copy()
        
        # 윗입술 영역 계산 및 이동 (upper_lip_vertical_move가 0이 아닐 때만)
        if abs(upper_lip_vertical_move) >= 0.1 and upper_lip_points:
            upper_x_coords = [p[0] for p in upper_lip_points]
            upper_y_coords = [p[1] for p in upper_lip_points]
            x_min = int(min(upper_x_coords))
            x_max = int(max(upper_x_coords))
            y_min = int(min(upper_y_coords))
            y_max = min(int(max(upper_y_coords)), int(mouth_center_y))
            
            # 패딩 추가 (파라미터 적용)
            # None 체크 (방어적 프로그래밍)
            if upper_lip_region_padding_x is None:
                upper_lip_region_padding_x = 0.2
            if upper_lip_region_padding_y is None:
                upper_lip_region_padding_y = 0.3
            if upper_lip_region_offset_x is None:
                upper_lip_region_offset_x = 0.0
            if upper_lip_region_offset_y is None:
                upper_lip_region_offset_y = 0.0
            
            padding_x = int((x_max - x_min) * upper_lip_region_padding_x)
            padding_y = int((y_max - y_min) * upper_lip_region_padding_y)
            x1 = max(0, x_min - padding_x + int(upper_lip_region_offset_x))
            y1 = max(0, y_min - padding_y + int(upper_lip_region_offset_y))
            x2 = min(img_width, x_max + padding_x + int(upper_lip_region_offset_x))
            y2 = min(img_height, y_max + int(upper_lip_region_offset_y))
            
            if x2 > x1 and y2 > y1:
                # 윗입술 영역 추출
                upper_lip_img = img_array[y1:y2, x1:x2]
                
                # 새로운 위치 계산 (위로 이동)
                new_y1 = max(0, y1 + upper_move_y)
                new_y2 = min(img_height, y2 + upper_move_y)
                new_x1 = x1
                new_x2 = x2
                
                if new_y2 > new_y1 and new_x2 > new_x1:
                    actual_height = new_y2 - new_y1
                    actual_width = new_x2 - new_x1
                    
                    # 영역 크기 조정 (필요시)
                    if actual_height != (y2 - y1) or actual_width != (x2 - x1):
                        upper_lip_resized = cv2.resize(upper_lip_img, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
                    else:
                        upper_lip_resized = upper_lip_img
                    
                    # 마스크 생성
                    mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
                    mask = cv2.GaussianBlur(mask, (15, 15), 0)
                    
                    # 블렌딩
                    roi = result[new_y1:new_y2, new_x1:new_x2]
                    mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
                    blended = (roi * (1 - mask_3channel) + upper_lip_resized * mask_3channel).astype(np.uint8)
                    result[new_y1:new_y2, new_x1:new_x2] = blended
        
        # 아래입술 영역 계산 및 이동 (lower_lip_vertical_move가 0이 아닐 때만)
        if abs(lower_lip_vertical_move) >= 0.1 and lower_lip_points:
            lower_x_coords = [p[0] for p in lower_lip_points]
            lower_y_coords = [p[1] for p in lower_lip_points]
            x_min = int(min(lower_x_coords))
            x_max = int(max(lower_x_coords))
            y_min = max(int(min(lower_y_coords)), int(mouth_center_y))
            y_max = int(max(lower_y_coords))
            
            # 패딩 추가 (파라미터 적용)
            # None 체크 (방어적 프로그래밍)
            if lower_lip_region_padding_x is None:
                lower_lip_region_padding_x = 0.2
            if lower_lip_region_padding_y is None:
                lower_lip_region_padding_y = 0.3
            if lower_lip_region_offset_x is None:
                lower_lip_region_offset_x = 0.0
            if lower_lip_region_offset_y is None:
                lower_lip_region_offset_y = 0.0
            
            padding_x = int((x_max - x_min) * lower_lip_region_padding_x)
            padding_y = int((y_max - y_min) * lower_lip_region_padding_y)
            x1 = max(0, x_min - padding_x + int(lower_lip_region_offset_x))
            y1 = max(0, y_min + int(lower_lip_region_offset_y))
            x2 = min(img_width, x_max + padding_x + int(lower_lip_region_offset_x))
            y2 = min(img_height, y_max + padding_y + int(lower_lip_region_offset_y))
            
            if x2 > x1 and y2 > y1:
                # 아래입술 영역 추출
                lower_lip_img = result[y1:y2, x1:x2]  # 이미 윗입술이 적용된 결과 사용
                
                # 새로운 위치 계산 (아래로 이동)
                new_y1 = max(0, y1 + lower_move_y)
                new_y2 = min(img_height, y2 + lower_move_y)
                new_x1 = x1
                new_x2 = x2
                
                if new_y2 > new_y1 and new_x2 > new_x1:
                    actual_height = new_y2 - new_y1
                    actual_width = new_x2 - new_x1
                    
                    # 영역 크기 조정 (필요시)
                    if actual_height != (y2 - y1) or actual_width != (x2 - x1):
                        lower_lip_resized = cv2.resize(lower_lip_img, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
                    else:
                        lower_lip_resized = lower_lip_img
                    
                    # 마스크 생성
                    mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
                    mask = cv2.GaussianBlur(mask, (15, 15), 0)
                    
                    # 블렌딩
                    roi = result[new_y1:new_y2, new_x1:new_x2]
                    mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
                    blended = (roi * (1 - mask_3channel) + lower_lip_resized * mask_3channel).astype(np.uint8)
                    result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 입술 수직 이동 조정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


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


def morph_face_by_polygons(image, original_landmarks, transformed_landmarks, selected_point_indices=None):
    """
    Delaunay Triangulation을 사용하여 폴리곤(랜드마크 포인트) 기반 얼굴 변형을 수행합니다.
    뒤집힌 삼각형이 발생하면 변형을 점진적으로 줄여서 재시도합니다.
    
    Args:
        image: PIL.Image 객체
        original_landmarks: 원본 랜드마크 포인트 리스트 [(x, y), ...] (폴리곤의 꼭짓점)
        transformed_landmarks: 변형된 랜드마크 포인트 리스트 [(x, y), ...] (변형된 폴리곤의 꼭짓점)
        selected_point_indices: 선택한 포인트 인덱스 리스트 (인덱스 기반 직접 매핑을 위해, None이면 전체 사용)
    
    Returns:
        PIL.Image: 변형된 이미지
    """
    if not _cv2_available:
        return image
    
    if not _scipy_available:
        print("[얼굴모핑] scipy가 설치되지 않았습니다. Delaunay Triangulation을 사용하려면 'pip install scipy'를 실행하세요.")
        return image
    
    if original_landmarks is None or transformed_landmarks is None:
        return image
    
    if len(original_landmarks) != len(transformed_landmarks):
        print(f"[얼굴모핑] 랜드마크 개수가 일치하지 않습니다: {len(original_landmarks)} != {len(transformed_landmarks)}")
        return image
    
    try:
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 이미지 경계 포인트 추가 (Delaunay Triangulation을 위해)
        # 경계 포인트: 4개 모서리
        margin = 10
        boundary_points = [
            (-margin, -margin),  # 왼쪽 위
            (img_width + margin, -margin),  # 오른쪽 위
            (img_width + margin, img_height + margin),  # 오른쪽 아래
            (-margin, img_height + margin)  # 왼쪽 아래
        ]
        
        # 모든 포인트 결합 (원본 + 경계)
        all_original_points = list(original_landmarks) + boundary_points
        all_transformed_points = list(transformed_landmarks) + boundary_points
        
        # numpy 배열로 변환
        original_points_array = np.array(all_original_points, dtype=np.float32)
        transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
        
        # 포인트 이동 거리 검증: 너무 많이 이동한 포인트가 있는지 확인
        max_displacement = 0.0
        max_displacement_idx = -1
        for i in range(len(original_landmarks)):
            if i < len(original_landmarks) and i < len(transformed_landmarks):
                orig_pt = original_landmarks[i]
                trans_pt = transformed_landmarks[i]
                displacement = np.sqrt((trans_pt[0] - orig_pt[0])**2 + (trans_pt[1] - orig_pt[1])**2)
                if displacement > max_displacement:
                    max_displacement = displacement
                    max_displacement_idx = i
        
        # 이미지 대각선 길이의 30%를 초과하면 경고
        image_diagonal = np.sqrt(img_width**2 + img_height**2)
        max_allowed_displacement = image_diagonal * 0.3
        
        if max_displacement > max_allowed_displacement:
            print(f"[얼굴모핑] 경고: 포인트 {max_displacement_idx}가 너무 많이 이동했습니다 ({max_displacement:.1f}픽셀, 허용치: {max_allowed_displacement:.1f}픽셀)")
            print(f"[얼굴모핑] 경고: 이미지 왜곡이 발생할 수 있습니다. 이동 거리를 줄여주세요.")
            # 과도하게 이동한 포인트를 제한 (허용치의 1.2배까지만 허용)
            if max_displacement > max_allowed_displacement * 1.2:
                scale_factor_limit = max_allowed_displacement * 1.2 / max_displacement
                for i in range(len(original_landmarks)):
                    if i < len(original_landmarks) and i < len(transformed_landmarks):
                        orig_pt = original_landmarks[i]
                        trans_pt = transformed_landmarks[i]
                        displacement = np.sqrt((trans_pt[0] - orig_pt[0])**2 + (trans_pt[1] - orig_pt[1])**2)
                        if displacement > max_allowed_displacement * 1.2:
                            # 이동 거리를 제한
                            dx = trans_pt[0] - orig_pt[0]
                            dy = trans_pt[1] - orig_pt[1]
                            limited_dx = dx * scale_factor_limit
                            limited_dy = dy * scale_factor_limit
                            transformed_landmarks[i] = (orig_pt[0] + limited_dx, orig_pt[1] + limited_dy)
                            print(f"[얼굴모핑] 경고: 포인트 {i}의 이동 거리를 제한했습니다 ({displacement:.1f} -> {max_allowed_displacement * 1.2:.1f}픽셀)")
                
                # 제한된 랜드마크로 배열 재생성
                all_transformed_points = list(transformed_landmarks) + boundary_points
                transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
        
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
        
        # 뒤집힌 삼각형 검사 및 변형 조정 (스케일 조정 전에 수행)
        # 눈 랜드마크는 항상 완전히 변형하고, 문제가 있는 주변 포인트만 선택적으로 조정
        from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
        
        # 눈 랜드마크 인덱스 (변형 강도 조정 대상에서 제외)
        eye_indices_set = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
        # 경계 포인트도 제외 (경계 포인트는 항상 원본 유지)
        boundary_start_idx = len(original_landmarks)
        boundary_indices_set = set(range(boundary_start_idx, len(original_points_array)))
        protected_indices = eye_indices_set | boundary_indices_set
        
        # 뒤집힌 삼각형 검사 (반복 검사 제거: 사용자가 폴리곤에서 이미 확인하고 수정했을 것으로 가정)
        # 단순히 뒤집힌 삼각형이 있는지 확인하고 경고만 출력
        flipped_count, flipped_indices, problematic_point_indices, neighbor_point_indices = _check_triangles_flipped(original_points_array, transformed_points_array, tri)
        
        if flipped_count > 0:
            print(f"[얼굴모핑] 경고: 뒤집힌 삼각형 {flipped_count}개 감지됨. 폴리곤에서 빨간색으로 표시된 삼각형을 확인하고 수정해주세요.")
            # 뒤집힌 삼각형이 있으면 문제 포인트를 원본으로 복원 (눈 랜드마크는 제외)
            for point_idx in problematic_point_indices:
                if point_idx not in protected_indices and point_idx < len(original_points_array):
                    transformed_points_array[point_idx] = original_points_array[point_idx].copy()
            print(f"[얼굴모핑] 뒤집힌 삼각형의 문제 포인트 {len(problematic_point_indices)}개를 원본으로 복원했습니다.")
        
        # 결과 이미지 초기화 (원본 이미지로 시작)
        result = img_array.copy()
        
        
        # 성능 최적화: 역변환 맵 방식 사용 (각 픽셀에 대해 한 번만 샘플링)
        # 이 방식이 각 삼각형마다 전체 이미지를 변환하는 것보다 훨씬 빠름
        
        # 이미지 크기 최적화: 큰 이미지는 다운샘플링
        max_dimension = 600  # 최대 차원 크기 (더 작게 설정하여 성능 향상)
        scale_factor = 1.0
        working_img = img_array
        working_width = img_width
        working_height = img_height
        
        if max(img_width, img_height) > max_dimension:
            scale_factor = max_dimension / max(img_width, img_height)
            working_width = int(img_width * scale_factor)
            working_height = int(img_height * scale_factor)
            # GPU 가속 리사이즈 시도 (CUDA 지원 시)
            if _cv2_cuda_available:
                try:
                    # GPU 메모리로 업로드
                    gpu_img = cv2.cuda_GpuMat()
                    gpu_img.upload(img_array)
                    # GPU에서 리사이즈
                    gpu_resized = cv2.cuda.resize(gpu_img, (working_width, working_height), interpolation=cv2.INTER_AREA)
                    # CPU로 다운로드
                    working_img = gpu_resized.download()
                except Exception:
                    # GPU 실패 시 CPU로 폴백
                    working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_AREA)
            else:
                working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_AREA)
            
            # 랜드마크 좌표도 스케일 조정
            original_points_array_scaled = original_points_array * scale_factor
            transformed_points_array_scaled = transformed_points_array * scale_factor
            
            # 스케일된 좌표로 Delaunay 재계산
            tri_scaled = Delaunay(original_points_array_scaled)
            tri = tri_scaled
            original_points_array = original_points_array_scaled
            transformed_points_array = transformed_points_array_scaled
        
        # 정변환 맵 생성: 원본 이미지의 각 픽셀을 변형된 위치로 직접 매핑
        # 정변환의 장점: 역변환 행렬의 오차 누적이 없고, 변형된 포인트 인덱스를 직접 사용하여 원본 삼각형을 찾을 수 있음
        # 결과 이미지 초기화 (float 타입으로 초기화하여 가중 평균 계산 가능)
        result = np.zeros((working_height, working_width, 3), dtype=np.float32)
        result_count = np.zeros((working_height, working_width), dtype=np.float32)  # 가중치 합계
        
        # 변형된 랜드마크와 원본 랜드마크의 차이 확인 (벡터화)
        # 경계 포인트를 제외한 실제 랜드마크만 확인
        if len(original_landmarks) > 0:
            orig_pts = original_points_array[:len(original_landmarks)]
            trans_pts = transformed_points_array[:len(original_landmarks)]
            diffs = np.sqrt(np.sum((trans_pts - orig_pts)**2, axis=1))
            max_diff = np.max(diffs)
            changed_count = np.sum(diffs > 0.1)
        else:
            max_diff = 0.0
            changed_count = 0
        # 랜드마크가 변형되지 않았으면 원본 이미지 반환
        if max_diff < 0.1:
            return image
        
        # 원본 이미지의 각 픽셀에 대해 해당하는 삼각형 찾기 및 정변환 계산
        # 성능 최적화: 벡터화된 연산 사용
        # 메모리 효율성을 위해 청크 단위로 처리 (큰 이미지의 경우)
        chunk_size = 100000  # 한 번에 처리할 픽셀 수
        total_pixels = working_height * working_width
        
        if total_pixels > chunk_size:
            # 큰 이미지는 청크 단위로 처리하여 메모리 사용량 감소
            y_coords_orig, x_coords_orig = np.mgrid[0:working_height, 0:working_width]
            pixel_coords_orig = np.column_stack([x_coords_orig.ravel(), y_coords_orig.ravel()])
            # 청크 단위로 삼각형 찾기
            simplex_indices_orig = np.full(total_pixels, -1, dtype=np.int32)
            for chunk_start in range(0, total_pixels, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_pixels)
                chunk_coords = pixel_coords_orig[chunk_start:chunk_end]
                simplex_indices_orig[chunk_start:chunk_end] = tri.find_simplex(chunk_coords)
        else:
            # 작은 이미지는 한 번에 처리
            y_coords_orig, x_coords_orig = np.mgrid[0:working_height, 0:working_width]
            pixel_coords_orig = np.column_stack([x_coords_orig.ravel(), y_coords_orig.ravel()])
            simplex_indices_orig = tri.find_simplex(pixel_coords_orig)
        
        # 각 삼각형의 정변환 행렬 미리 계산 (캐싱)
        forward_transform_cache = {}
        
        # 각 픽셀에 대해 정변환 적용
        # 주의: tri.simplices를 사용하여 원본 삼각형을 순회합니다
        # 원본 이미지의 픽셀 좌표가 속한 원본 삼각형을 찾고,
        # 그 삼각형의 포인트 인덱스를 사용하여 변형된 포인트를 가져옵니다
        # 참고: 조기 종료 최적화는 제거됨 - 전체 이미지 매핑을 위해 모든 삼각형 처리 필요
        total_pixels_processed = 0
        pixels_out_of_bounds = 0
        for simplex_idx, simplex in enumerate(tri.simplices):
            simplex = tri.simplices[simplex_idx]
            # 이 삼각형에 속한 픽셀 인덱스 (원본 이미지의 픽셀)
            pixel_mask = (simplex_indices_orig == simplex_idx)
            
            if not np.any(pixel_mask):
                continue
            
            # 원본 삼각형의 포인트 인덱스를 사용하여 원본과 변형된 포인트를 가져옵니다
            # 변형된 포인트 인덱스를 기억하여 원본에서 직접 찾아서 매핑 (오차 누적 방지)
            # 인덱스 기반 직접 매핑: simplex[0], simplex[1], simplex[2] 인덱스를 사용하여
            # 원본 랜드마크 포인트를 변형된 랜드마크 포인트로 직접 매핑
            # 원본 삼각형의 3개 포인트 (원본 랜드마크에서, 인덱스로 직접 접근)
            pt1_orig = original_points_array[simplex[0]]
            pt2_orig = original_points_array[simplex[1]]
            pt3_orig = original_points_array[simplex[2]]
            
            # 변형된 삼각형의 3개 포인트 (변형된 랜드마크에서, 같은 인덱스로 직접 접근)
            # 인덱스를 기억하고 있어서 원본에서 변형된 위치로 직접 매핑 가능
            # 선택한 포인트 인덱스로 원본에서 찾아서 변형된 위치로 매핑
            pt1_trans = transformed_points_array[simplex[0]]
            pt2_trans = transformed_points_array[simplex[1]]
            pt3_trans = transformed_points_array[simplex[2]]
            
            # 디버깅 코드 제거 (성능 최적화)
            
            # 정변환 행렬 계산 (원본 -> 변형된)
            # 원본 삼각형(src)에서 변형된 삼각형(dst)로의 변환 행렬
            # 변형된 포인트 인덱스를 기억하여 원본에서 직접 찾아서 매핑 (오차 누적 방지)
            src_triangle = np.array([pt1_orig, pt2_orig, pt3_orig], dtype=np.float32)  # 원본 삼각형
            dst_triangle = np.array([pt1_trans, pt2_trans, pt3_trans], dtype=np.float32)  # 변형된 삼각형
            
            # 삼각형 유효성 검사: 변형된 삼각형이 뒤집히지 않았는지 확인
            # 삼각형의 면적 계산 (벡터 외적 사용)
            v1 = dst_triangle[1] - dst_triangle[0]
            v2 = dst_triangle[2] - dst_triangle[0]
            cross_product = v1[0] * v2[1] - v1[1] * v2[0]
            triangle_area = abs(cross_product) / 2.0
            
            # 원본 삼각형 면적
            v1_orig = src_triangle[1] - src_triangle[0]
            v2_orig = src_triangle[2] - src_triangle[0]
            cross_product_orig = v1_orig[0] * v2_orig[1] - v1_orig[1] * v2_orig[0]
            triangle_area_orig = abs(cross_product_orig) / 2.0
            
            # 삼각형이 뒤집혔는지 확인 (외적의 부호가 바뀌면 뒤집힘)
            is_flipped = (cross_product * cross_product_orig < 0)
            
            # 눈동자 영역 확인 (468-477: 왼쪽 468-472, 오른쪽 473-477)
            iris_indices = set([468, 469, 470, 471, 472, 473, 474, 475, 476, 477])
            is_iris_triangle = any(idx in iris_indices for idx in simplex)
            
            # 삼각형이 너무 작거나 뒤집혔는지 확인
            # 매우 큰 변형(200% 이상)에서도 안정적으로 동작하도록 면적 임계값을 더 관대하게 설정
            # 면적이 원본의 2% 미만이면 무효, 또는 뒤집혔으면 무효
            # 작은 삼각형의 경우 더 관대한 임계값 사용
            # 눈동자 영역은 매우 작을 수 있으므로 더 관대한 임계값 사용
            if is_iris_triangle:
                # 눈동자 영역: 면적 검사 건너뛰기 (항상 변환 시도)
                area_threshold = 0.0  # 면적 검사 없음
            elif triangle_area_orig < 10.0:
                area_threshold = 0.05  # 작은 삼각형: 5% 미만이면 무효
            else:
                area_threshold = 0.02  # 일반 삼각형: 2% 미만이면 무효 (더 관대)
            
            # 삼각형이 뒤집혔는지 다시 확인 (이미 사전 검증했지만 안전을 위해)
            if is_flipped:
                # 뒤집힌 삼각형은 절대 허용하지 않음: 원본 사용 (눈동자 영역 포함)
                # 로그 제거 (성능 최적화)
                dst_triangle = src_triangle.copy()
            elif area_threshold > 0 and (triangle_area < triangle_area_orig * area_threshold or triangle_area < 1.0):
                # 면적이 너무 작은 삼각형: 원본 사용
                # 눈동자 영역도 면적이 너무 작으면 원본 사용 (안정성 확보)
                if is_iris_triangle and triangle_area_orig > 0.5 and triangle_area > 0.5:
                    # 눈동자 영역이지만 면적이 충분히 크면 변환 시도
                    pass
                else:
                    # 로그 제거 (성능 최적화)
                    dst_triangle = src_triangle.copy()
            
            # 정변환 행렬 (원본 좌표를 변형된 좌표로 변환)
            # 삼각형이 유효한지 다시 한 번 확인 (면적이 너무 작으면 정변환 행렬 계산 불가)
            # 눈동자 영역은 매우 작을 수 있으므로 더 관대한 임계값 사용
            min_area_threshold = 0.5 if is_iris_triangle else 0.1
            if triangle_area_orig < min_area_threshold or triangle_area < min_area_threshold:
                # 면적이 거의 0인 삼각형은 원본 사용
                if not is_iris_triangle or triangle_area_orig < 0.5:
                    dst_triangle = src_triangle.copy()
            
            # 삼각형이 degenerate(퇴화)되었는지 확인: 세 점이 거의 일직선상에 있는지
            # 세 점 사이의 최소 거리 확인
            dist12 = np.sqrt((dst_triangle[1][0] - dst_triangle[0][0])**2 + (dst_triangle[1][1] - dst_triangle[0][1])**2)
            dist13 = np.sqrt((dst_triangle[2][0] - dst_triangle[0][0])**2 + (dst_triangle[2][1] - dst_triangle[0][1])**2)
            dist23 = np.sqrt((dst_triangle[2][0] - dst_triangle[1][0])**2 + (dst_triangle[2][1] - dst_triangle[1][1])**2)
            min_side_length = min(dist12, dist13, dist23)
            
            # 변의 길이가 너무 짧으면 degenerate 삼각형 (정변환 불안정)
            if min_side_length < 0.5:
                # 로그 제거 (성능 최적화)
                dst_triangle = src_triangle.copy()
            
            try:
                # 정변환 행렬 계산 (원본 -> 변형된)
                M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)
                
                # 정변환 행렬의 행렬식 확인 (유효성 검증)
                # 행렬식이 0에 가까우면 변환이 불가능
                det = M_forward[0, 0] * M_forward[1, 1] - M_forward[0, 1] * M_forward[1, 0]
                if abs(det) < 1e-6:
                    # 행렬식이 너무 작으면 원본 사용
                    # 로그 제거 (성능 최적화)
                    dst_triangle = src_triangle.copy()
                    M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)
            except Exception as e:
                # 정변환 행렬 계산 실패 시 원본 사용
                # 로그 제거 (성능 최적화)
                dst_triangle = src_triangle.copy()
                M_forward = cv2.getAffineTransform(src_triangle, dst_triangle)
            
            # 이 삼각형에 속한 원본 픽셀 좌표
            triangle_pixels_orig = pixel_coords_orig[pixel_mask]
            
            # 정변환 적용: 원본 좌표 -> 변형된 좌표
            ones = np.ones((len(triangle_pixels_orig), 1), dtype=np.float32)
            triangle_pixels_orig_homogeneous = np.hstack([triangle_pixels_orig, ones])
            transformed_coords = (M_forward @ triangle_pixels_orig_homogeneous.T).T
            
            # 벡터화된 픽셀 처리 (성능 최적화)
            pixel_indices = np.where(pixel_mask)[0]
            if len(pixel_indices) == 0:
                continue
            
            # 원본 픽셀 좌표 (벡터화)
            orig_y_coords = pixel_indices // working_width
            orig_x_coords = pixel_indices % working_width
            
            # 변형된 좌표 (벡터화)
            trans_x = transformed_coords[:, 0]
            trans_y = transformed_coords[:, 1]
            
            # bilinear interpolation 좌표 계산 (벡터화)
            x0 = np.floor(trans_x).astype(np.int32)
            y0 = np.floor(trans_y).astype(np.int32)
            x1 = x0 + 1
            y1 = y0 + 1
            
            # 소수점 부분 (벡터화)
            fx = trans_x - x0.astype(np.float32)
            fy = trans_y - y0.astype(np.float32)
            
            # bilinear interpolation 가중치 (벡터화)
            w00 = (1 - fx) * (1 - fy)
            w01 = (1 - fx) * fy
            w10 = fx * (1 - fy)
            w11 = fx * fy
            
            # 원본 픽셀 값 (벡터화)
            pixel_values = working_img[orig_y_coords, orig_x_coords].astype(np.float32)
            
            # 범위 체크 (벡터화)
            valid_00 = (y0 >= 0) & (y0 < working_height) & (x0 >= 0) & (x0 < working_width)
            valid_01 = (y1 >= 0) & (y1 < working_height) & (x0 >= 0) & (x0 < working_width)
            valid_10 = (y0 >= 0) & (y0 < working_height) & (x1 >= 0) & (x1 < working_width)
            valid_11 = (y1 >= 0) & (y1 < working_height) & (x1 >= 0) & (x1 < working_width)
            
            # 가중치 분배 (완전 벡터화 - 성능 최적화)
            # NumPy의 advanced indexing을 사용하여 벡터화
            # valid_00, valid_01, valid_10, valid_11 마스크를 사용하여 한 번에 처리
            
            # 각 위치에 가중치를 더하기 위해 np.add.at 사용 (중복 인덱스 처리)
            # valid_00인 경우
            valid_00_indices = np.where(valid_00)[0]
            if len(valid_00_indices) > 0:
                y0_valid = y0[valid_00_indices]
                x0_valid = x0[valid_00_indices]
                w00_valid = w00[valid_00_indices]
                pixel_values_00 = pixel_values[valid_00_indices]
                weighted_values_00 = pixel_values_00 * w00_valid[:, np.newaxis]
                np.add.at(result, (y0_valid, x0_valid), weighted_values_00)
                np.add.at(result_count, (y0_valid, x0_valid), w00_valid)
            
            # valid_01인 경우
            valid_01_indices = np.where(valid_01)[0]
            if len(valid_01_indices) > 0:
                y1_valid = y1[valid_01_indices]
                x0_valid = x0[valid_01_indices]
                w01_valid = w01[valid_01_indices]
                pixel_values_01 = pixel_values[valid_01_indices]
                weighted_values_01 = pixel_values_01 * w01_valid[:, np.newaxis]
                np.add.at(result, (y1_valid, x0_valid), weighted_values_01)
                np.add.at(result_count, (y1_valid, x0_valid), w01_valid)
            
            # valid_10인 경우
            valid_10_indices = np.where(valid_10)[0]
            if len(valid_10_indices) > 0:
                y0_valid = y0[valid_10_indices]
                x1_valid = x1[valid_10_indices]
                w10_valid = w10[valid_10_indices]
                pixel_values_10 = pixel_values[valid_10_indices]
                weighted_values_10 = pixel_values_10 * w10_valid[:, np.newaxis]
                np.add.at(result, (y0_valid, x1_valid), weighted_values_10)
                np.add.at(result_count, (y0_valid, x1_valid), w10_valid)
            
            # valid_11인 경우
            valid_11_indices = np.where(valid_11)[0]
            if len(valid_11_indices) > 0:
                y1_valid = y1[valid_11_indices]
                x1_valid = x1[valid_11_indices]
                w11_valid = w11[valid_11_indices]
                pixel_values_11 = pixel_values[valid_11_indices]
                weighted_values_11 = pixel_values_11 * w11_valid[:, np.newaxis]
                np.add.at(result, (y1_valid, x1_valid), weighted_values_11)
                np.add.at(result_count, (y1_valid, x1_valid), w11_valid)
            
            # 범위를 벗어난 경우 처리 (벡터화)
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
            
            total_pixels_processed += len(pixel_indices)
        
        # 로그 제거 (성능 최적화)
        
        # 가중 평균으로 정규화 (여러 원본 픽셀이 같은 변형된 위치로 매핑된 경우)
        result_count_safe = np.maximum(result_count, 1e-6)  # 0으로 나누기 방지
        result = result / result_count_safe[:, :, np.newaxis]
        result = result.astype(np.uint8)
        
        # 빈 공간 채우기: 변형된 이미지에 빈 공간이 생긴 경우 처리
        empty_mask = (result_count < 1e-6)
        empty_count = np.sum(empty_mask)
        total_pixels = working_height * working_width
        empty_ratio = empty_count / total_pixels if total_pixels > 0 else 0
        
        if np.any(empty_mask):
            # 빈 공간을 주변 픽셀로 채우기 (inpainting)
            if _cv2_available and empty_ratio < 0.5:  # 빈 공간이 50% 미만일 때만 inpainting 사용
                # 빈 공간 마스크 생성
                empty_mask_uint8 = (empty_mask * 255).astype(np.uint8)
                # 주변 픽셀로 채우기
                result = cv2.inpaint(result, empty_mask_uint8, 3, cv2.INPAINT_TELEA)
            else:
                # 빈 공간이 너무 많거나 OpenCV가 없으면 원본 이미지로 채움
                # 하지만 변형된 영역은 유지
                result[empty_mask] = working_img[empty_mask]
        
        # 원본 크기로 복원 (다운샘플링했던 경우)
        if scale_factor < 1.0:
            result = cv2.resize(result, (img_width, img_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 경계 영역을 원본 이미지로 복원하여 검은색 테두리 방지
        # 경계 5픽셀 영역은 원본 이미지로 유지
        border_size = 5
        if border_size > 0 and result.shape[:2] == img_array.shape[:2]:
            # 경계 영역 복원 (크기가 일치하는 경우에만)
            result[0:border_size, :] = img_array[0:border_size, :]  # 상단
            result[-border_size:, :] = img_array[-border_size:, :]  # 하단
            result[:, 0:border_size] = img_array[:, 0:border_size]  # 왼쪽
            result[:, -border_size:] = img_array[:, -border_size:]  # 오른쪽
        
        print(f"[얼굴모핑] 랜드마크 변형 완료: 이미지 크기 {img_width}x{img_height}")
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 랜드마크 기반 변형 실패: {e}")
        import traceback
        traceback.print_exc()
        return image


def transform_landmarks_for_eye_size(landmarks, eye_size_ratio=1.0, left_eye_size_ratio=None, right_eye_size_ratio=None):
    """
    눈 크기 조정을 랜드마크 변형으로 변환합니다 (눈 주변 영역 포함).
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        eye_size_ratio: 기본 눈 크기 비율
        left_eye_size_ratio: 왼쪽 눈 크기 비율 (None이면 eye_size_ratio 사용)
        right_eye_size_ratio: 오른쪽 눈 크기 비율 (None이면 eye_size_ratio 사용)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    try:
        from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
        from utils.face_landmarks import get_key_landmarks
        
        # 눈 주변 영역 인덱스 (눈썹, 눈꺼풀, 눈 주변 피부)
        # 왼쪽 눈썹: [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
        LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
        # 오른쪽 눈썹: [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
        RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
        # 눈꺼풀 및 눈 주변 추가 포인트 (눈 인덱스와 인접한 포인트들)
        # 왼쪽 눈 주변: 눈 인덱스 + 눈썹 + 눈꺼풀 주변
        LEFT_EYE_SURROUNDING_INDICES = LEFT_EYE_INDICES + LEFT_EYEBROW_INDICES + [
            10, 151, 9, 10, 151, 337, 299, 333, 298, 301, 368, 264, 447, 366, 401, 435, 410, 454, 323, 361
        ]
        # 오른쪽 눈 주변: 눈 인덱스 + 눈썹 + 눈꺼풀 주변
        RIGHT_EYE_SURROUNDING_INDICES = RIGHT_EYE_INDICES + RIGHT_EYEBROW_INDICES + [
            172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323
        ]
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return landmarks
        
        transformed_landmarks = list(landmarks)
        
        # 두 눈 사이의 거리 계산 (영향 반경 제한용)
        left_eye_center = key_landmarks.get('left_eye')
        right_eye_center = key_landmarks.get('right_eye')
        eye_distance = None
        if left_eye_center is not None and right_eye_center is not None:
            eye_distance = ((right_eye_center[0] - left_eye_center[0])**2 + 
                          (right_eye_center[1] - left_eye_center[1])**2)**0.5
        
        # 왼쪽 눈 크기 조정 (비율이 유효하고 1.0과 다를 때만)
        left_ratio = left_eye_size_ratio if left_eye_size_ratio is not None else eye_size_ratio
        # 기본값(1.0)이거나 None이면 스킵
        if left_ratio is None or abs(left_ratio - 1.0) < 0.01:
            left_ratio = None
        elif left_ratio is not None and 0.1 <= left_ratio <= 5.0:
            left_eye_center = key_landmarks.get('left_eye')
            if left_eye_center is not None:
                
                # 새로운 접근 방식: 눈 영역 경계 기반 변형
                # 1. 눈 랜드마크의 경계 박스 계산 (눈 영역 정의)
                left_eye_points = [landmarks[i] for i in LEFT_EYE_INDICES if i < len(landmarks)]
                if not left_eye_points:
                    left_ratio = None
                else:
                    eye_min_x = min(p[0] for p in left_eye_points)
                    eye_max_x = max(p[0] for p in left_eye_points)
                    eye_min_y = min(p[1] for p in left_eye_points)
                    eye_max_y = max(p[1] for p in left_eye_points)
                    
                    eye_width = eye_max_x - eye_min_x
                    eye_height = eye_max_y - eye_min_y
                    eye_center_x = (eye_min_x + eye_max_x) / 2.0
                    eye_center_y = (eye_min_y + eye_max_y) / 2.0
                    
                    # 눈 영역 경계 확장 (패딩): 눈썹과 눈 주변만 포함 (얼굴 윤곽, 코는 제외)
                    # 패딩을 최소화하여 눈 영역만 변형
                    if left_ratio >= 2.0:
                        padding_factor = 1.3  # 매우 큰 변형: 1.3배 (최소한의 주변 영역만)
                    elif left_ratio > 1.5:
                        padding_factor = 1.25  # 큰 변형: 1.25배
                    else:
                        padding_factor = 1.2  # 기본: 1.2배 (눈과 눈썹만)
                    eye_boundary_min_x = eye_center_x - eye_width * padding_factor / 2.0
                    eye_boundary_max_x = eye_center_x + eye_width * padding_factor / 2.0
                    eye_boundary_min_y = eye_center_y - eye_height * padding_factor / 2.0
                    eye_boundary_max_y = eye_center_y + eye_height * padding_factor / 2.0
                    
                    
                    # 이미 변형된 포인트 추적
                    transformed_indices = set()
                    right_eye_excluded_indices = set()
                    
                    # 오른쪽 눈 영역 제외 (겹침 방지)
                    if right_eye_center is not None and eye_distance is not None:
                        right_eye_radius = eye_distance * 0.3
                        for idx in range(len(landmarks)):
                            if idx < len(landmarks):
                                x, y = landmarks[idx]
                                dist_to_right = ((x - right_eye_center[0])**2 + (y - right_eye_center[1])**2)**0.5
                                if dist_to_right < right_eye_radius:
                                    right_eye_excluded_indices.add(idx)
                    
                    # 얼굴 윤곽, 코, 입 영역 제외 (변형하지 않음)
                    # 얼굴 윤곽 (턱선): 인덱스 0-16
                    FACE_OUTLINE_INDICES = set(range(17))  # 0-16
                    # 코 영역: 인덱스 4, 8, 19, 20, 94, 98, 102, 115, 131, 134, 141, 164, 220, 235, 236, 240, 281, 305, 327, 358, 360, 363, 460
                    NOSE_INDICES = set([4, 8, 19, 20, 94, 98, 102, 115, 131, 134, 141, 164, 220, 235, 236, 240, 281, 305, 327, 358, 360, 363, 460])
                    # 입 영역: 인덱스 61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318
                    MOUTH_INDICES = set([61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318])
                    # 제외할 인덱스: 얼굴 윤곽, 코, 입
                    excluded_indices = FACE_OUTLINE_INDICES | NOSE_INDICES | MOUTH_INDICES
                    
                    # 2. 눈 영역 경계 내의 모든 랜드마크를 눈 크기 변화에 비례하여 변형
                    # MediaPipe 연결 정보를 사용하여 눈과 연결된 모든 포인트 찾기
                    try:
                        import mediapipe as mp
                        mp_face_mesh = mp.solutions.face_mesh
                        LEFT_EYE_CONNECTIONS = mp_face_mesh.FACEMESH_LEFT_EYE
                        # 연결된 모든 포인트 인덱스 수집
                        left_eye_connected_indices = set()
                        for connection in LEFT_EYE_CONNECTIONS:
                            left_eye_connected_indices.add(connection[0])
                            left_eye_connected_indices.add(connection[1])
                    except Exception as e:
                        left_eye_connected_indices = set(LEFT_EYE_SURROUNDING_INDICES)
                    
                    # 디버깅: 변형되지 않은 포인트 추적
                    skipped_points = []
                    
                    # 눈동자 인덱스 정의 (refine_landmarks=True일 때 사용 가능)
                    # 왼쪽 눈동자: 468 (중심), 469, 470, 471, 472
                    # 오른쪽 눈동자: 473 (중심), 474, 475, 476, 477
                    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
                    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
                    
                    # 1단계: 왼쪽 눈 인덱스와 왼쪽 눈동자 인덱스는 무조건 먼저 변형 (다른 조건 무시)
                    for idx in LEFT_EYE_INDICES + LEFT_IRIS_INDICES:
                        if idx < len(landmarks) and idx not in transformed_indices:
                            # 오른쪽 눈 영역에 포함되어 있어도 왼쪽 눈 인덱스는 변형
                            x, y = landmarks[idx]
                            dx = x - eye_center_x
                            dy = y - eye_center_y
                            scale = left_ratio  # 눈 랜드마크는 완전히 변형
                            transformed_landmarks[idx] = (
                                eye_center_x + dx * scale,
                                eye_center_y + dy * scale
                            )
                            transformed_indices.add(idx)
                    
                    # 2단계: LEFT_EYE_SURROUNDING_INDICES에 포함된 포인트는 무조건 변형 (경계 밖이어도)
                    for idx in range(len(landmarks)):
                        if idx < len(landmarks) and idx not in transformed_indices and idx not in right_eye_excluded_indices:
                            # 얼굴 윤곽, 코, 입은 제외
                            if idx in excluded_indices:
                                skipped_points.append((idx, "제외 인덱스 (얼굴윤곽/코/입)"))
                                continue
                            
                            x, y = landmarks[idx]
                            
                            # 눈 영역 경계 내에 있는지 확인
                            is_inside_boundary = (eye_boundary_min_x <= x <= eye_boundary_max_x and 
                                                  eye_boundary_min_y <= y <= eye_boundary_max_y)
                            
                            # LEFT_EYE_SURROUNDING_INDICES 또는 MediaPipe 연결 정보에 포함된 포인트는 경계 밖이어도 변형
                            is_surrounding_point = idx in LEFT_EYE_SURROUNDING_INDICES or idx in left_eye_connected_indices
                            
                            # 거리 기반 확인 (경계보다 더 넓은 범위)
                            dist_from_center = ((x - eye_center_x)**2 + (y - eye_center_y)**2)**0.5
                            max_dist = max(eye_width, eye_height) * padding_factor * 1.5  # 경계보다 1.5배 넓게
                            is_within_distance = dist_from_center <= max_dist
                            
                            if is_inside_boundary or is_surrounding_point or is_within_distance:
                                # 경계 내 또는 주변 포인트: 눈 크기 변화에 비례하여 변형
                                dx = x - eye_center_x
                                dy = y - eye_center_y
                                
                                # 경계 내부의 위치에 따라 변형 강도 조절 (중심에 가까울수록 더 많이 변형)
                                dist_from_center = ((dx**2 + dy**2)**0.5)
                                max_dist = max(eye_width, eye_height) * padding_factor / 2.0
                                
                                if max_dist > 0:
                                    # 중심에서의 거리에 따라 가중치 계산 (경계에 가까울수록 변형 강도 감소)
                                    normalized_dist = min(dist_from_center / max_dist, 1.0) if is_inside_boundary else min(dist_from_center / (max_dist * 1.5), 1.0)
                                    # 눈 랜드마크는 완전히 변형, 경계에 가까운 포인트는 점진적으로 변형
                                    if idx in LEFT_EYE_INDICES:
                                        scale = left_ratio  # 눈 랜드마크는 완전히 변형
                                    elif idx in LEFT_EYEBROW_INDICES:
                                        # 눈썹은 최소한으로만 변형 (눈과 연결되어 있으므로 약간만)
                                        # 눈 크기 변화의 30%만 적용
                                        eyebrow_factor = 0.3  # 눈썹은 눈 크기 변화의 30%만 적용
                                        scale = 1.0 + (left_ratio - 1.0) * eyebrow_factor
                                    else:
                                        # 주변 영역은 거리에 따라 점진적으로 변형 (최소한으로만)
                                        # 경계에 가까울수록 변형 강도 급격히 감소
                                        surrounding_factor = 1.0 - normalized_dist * 0.8  # 경계에 가까우면 거의 변형 안 함
                                        scale = 1.0 + (left_ratio - 1.0) * surrounding_factor * 0.5  # 최대 50%만 변형
                                    
                                    transformed_landmarks[idx] = (
                                        eye_center_x + dx * scale,
                                        eye_center_y + dy * scale
                                    )
                                    transformed_indices.add(idx)
                            else:
                                # 변형되지 않은 포인트 추적
                                reason = []
                                if not is_inside_boundary:
                                    reason.append("경계밖")
                                if not is_surrounding_point:
                                    reason.append("주변포인트아님")
                                if not is_within_distance:
                                    reason.append("거리초과")
                                if idx in right_eye_excluded_indices:
                                    reason.append("오른쪽눈영역")
                                skipped_points.append((idx, ", ".join(reason) if reason else "알수없음"))
                    
        
        # 오른쪽 눈 크기 조정 (비율이 유효하고 1.0과 다를 때만)
        right_ratio = right_eye_size_ratio if right_eye_size_ratio is not None else eye_size_ratio
        # 기본값(1.0)이거나 None이면 스킵
        if right_ratio is None or abs(right_ratio - 1.0) < 0.01:
            right_ratio = None
        elif right_ratio is not None and 0.1 <= right_ratio <= 5.0:
            right_eye_center = key_landmarks.get('right_eye')
            if right_eye_center is not None:
                
                # 새로운 접근 방식: 눈 영역 경계 기반 변형
                # 1. 눈 랜드마크의 경계 박스 계산 (눈 영역 정의)
                right_eye_points = [landmarks[i] for i in RIGHT_EYE_INDICES if i < len(landmarks)]
                if not right_eye_points:
                    right_ratio = None
                else:
                    eye_min_x = min(p[0] for p in right_eye_points)
                    eye_max_x = max(p[0] for p in right_eye_points)
                    eye_min_y = min(p[1] for p in right_eye_points)
                    eye_max_y = max(p[1] for p in right_eye_points)
                    
                    eye_width = eye_max_x - eye_min_x
                    eye_height = eye_max_y - eye_min_y
                    eye_center_x = (eye_min_x + eye_max_x) / 2.0
                    eye_center_y = (eye_min_y + eye_max_y) / 2.0
                    
                    # 눈 영역 경계 확장 (패딩): 눈썹과 눈 주변만 포함 (얼굴 윤곽, 코는 제외)
                    # 패딩을 최소화하여 눈 영역만 변형
                    if right_ratio >= 2.0:
                        padding_factor = 1.3  # 매우 큰 변형: 1.3배 (최소한의 주변 영역만)
                    elif right_ratio > 1.5:
                        padding_factor = 1.25  # 큰 변형: 1.25배
                    else:
                        padding_factor = 1.2  # 기본: 1.2배 (눈과 눈썹만)
                    eye_boundary_min_x = eye_center_x - eye_width * padding_factor / 2.0
                    eye_boundary_max_x = eye_center_x + eye_width * padding_factor / 2.0
                    eye_boundary_min_y = eye_center_y - eye_height * padding_factor / 2.0
                    eye_boundary_max_y = eye_center_y + eye_height * padding_factor / 2.0
                    
                    
                    # 이미 변형된 포인트 추적
                    transformed_indices = set()
                    left_eye_excluded_indices = set()
                    
                    # 왼쪽 눈 영역 제외 (겹침 방지)
                    if left_eye_center is not None and eye_distance is not None:
                        left_eye_radius = eye_distance * 0.3
                        for idx in range(len(landmarks)):
                            if idx < len(landmarks):
                                x, y = landmarks[idx]
                                dist_to_left = ((x - left_eye_center[0])**2 + (y - left_eye_center[1])**2)**0.5
                                if dist_to_left < left_eye_radius:
                                    left_eye_excluded_indices.add(idx)
                    
                    # 얼굴 윤곽, 코, 입 영역 제외 (변형하지 않음)
                    # 얼굴 윤곽 (턱선): 인덱스 0-16
                    FACE_OUTLINE_INDICES = set(range(17))  # 0-16
                    # 코 영역: 인덱스 4, 8, 19, 20, 94, 98, 102, 115, 131, 134, 141, 164, 220, 235, 236, 240, 281, 305, 327, 358, 360, 363, 460
                    NOSE_INDICES = set([4, 8, 19, 20, 94, 98, 102, 115, 131, 134, 141, 164, 220, 235, 236, 240, 281, 305, 327, 358, 360, 363, 460])
                    # 입 영역: 인덱스 61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318
                    MOUTH_INDICES = set([61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318])
                    # 제외할 인덱스: 얼굴 윤곽, 코, 입
                    excluded_indices = FACE_OUTLINE_INDICES | NOSE_INDICES | MOUTH_INDICES
                    
                    # 2. 눈 영역 경계 내의 모든 랜드마크를 눈 크기 변화에 비례하여 변형
                    # MediaPipe 연결 정보를 사용하여 눈과 연결된 모든 포인트 찾기
                    try:
                        import mediapipe as mp
                        mp_face_mesh = mp.solutions.face_mesh
                        RIGHT_EYE_CONNECTIONS = mp_face_mesh.FACEMESH_RIGHT_EYE
                        # 연결된 모든 포인트 인덱스 수집
                        right_eye_connected_indices = set()
                        for connection in RIGHT_EYE_CONNECTIONS:
                            right_eye_connected_indices.add(connection[0])
                            right_eye_connected_indices.add(connection[1])
                    except Exception as e:
                        right_eye_connected_indices = set(RIGHT_EYE_SURROUNDING_INDICES)
                    
                    # 디버깅: 변형되지 않은 포인트 추적
                    skipped_points = []
                    
                    # 눈동자 인덱스 정의 (refine_landmarks=True일 때 사용 가능)
                    # 왼쪽 눈동자: 468 (중심), 469, 470, 471, 472
                    # 오른쪽 눈동자: 473 (중심), 474, 475, 476, 477
                    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
                    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
                    
                    # 1단계: 오른쪽 눈 인덱스와 오른쪽 눈동자 인덱스는 무조건 먼저 변형 (다른 조건 무시)
                    for idx in RIGHT_EYE_INDICES + RIGHT_IRIS_INDICES:
                        if idx < len(landmarks) and idx not in transformed_indices:
                            # 왼쪽 눈 영역에 포함되어 있어도 오른쪽 눈 인덱스는 변형
                            x, y = landmarks[idx]
                            dx = x - eye_center_x
                            dy = y - eye_center_y
                            scale = right_ratio  # 눈 랜드마크는 완전히 변형
                            transformed_landmarks[idx] = (
                                eye_center_x + dx * scale,
                                eye_center_y + dy * scale
                            )
                            transformed_indices.add(idx)
                    
                    # 2단계: RIGHT_EYE_SURROUNDING_INDICES에 포함된 포인트는 무조건 변형 (경계 밖이어도)
                    for idx in range(len(landmarks)):
                        if idx < len(landmarks) and idx not in transformed_indices and idx not in left_eye_excluded_indices:
                            # 얼굴 윤곽, 코, 입은 제외
                            if idx in excluded_indices:
                                skipped_points.append((idx, "제외 인덱스 (얼굴윤곽/코/입)"))
                                continue
                            
                            x, y = landmarks[idx]
                            
                            # 눈 영역 경계 내에 있는지 확인
                            is_inside_boundary = (eye_boundary_min_x <= x <= eye_boundary_max_x and 
                                                  eye_boundary_min_y <= y <= eye_boundary_max_y)
                            
                            # RIGHT_EYE_SURROUNDING_INDICES 또는 MediaPipe 연결 정보에 포함된 포인트는 경계 밖이어도 변형
                            is_surrounding_point = idx in RIGHT_EYE_SURROUNDING_INDICES or idx in right_eye_connected_indices
                            
                            # 거리 기반 확인 (경계보다 더 넓은 범위)
                            dist_from_center = ((x - eye_center_x)**2 + (y - eye_center_y)**2)**0.5
                            max_dist = max(eye_width, eye_height) * padding_factor * 1.5  # 경계보다 1.5배 넓게
                            is_within_distance = dist_from_center <= max_dist
                            
                            if is_inside_boundary or is_surrounding_point or is_within_distance:
                                # 경계 내 또는 주변 포인트: 눈 크기 변화에 비례하여 변형
                                dx = x - eye_center_x
                                dy = y - eye_center_y
                                
                                # 경계 내부의 위치에 따라 변형 강도 조절 (중심에 가까울수록 더 많이 변형)
                                dist_from_center = ((dx**2 + dy**2)**0.5)
                                max_dist = max(eye_width, eye_height) * padding_factor / 2.0
                                
                                if max_dist > 0:
                                    # 중심에서의 거리에 따라 가중치 계산 (경계에 가까울수록 변형 강도 감소)
                                    normalized_dist = min(dist_from_center / max_dist, 1.0) if is_inside_boundary else min(dist_from_center / (max_dist * 1.5), 1.0)
                                    # 눈 랜드마크는 완전히 변형, 경계에 가까운 포인트는 점진적으로 변형
                                    if idx in RIGHT_EYE_INDICES:
                                        scale = right_ratio  # 눈 랜드마크는 완전히 변형
                                    elif idx in RIGHT_EYEBROW_INDICES:
                                        # 눈썹은 최소한으로만 변형 (눈과 연결되어 있으므로 약간만)
                                        # 눈 크기 변화의 30%만 적용
                                        eyebrow_factor = 0.3  # 눈썹은 눈 크기 변화의 30%만 적용
                                        scale = 1.0 + (right_ratio - 1.0) * eyebrow_factor
                                    else:
                                        # 주변 영역은 거리에 따라 점진적으로 변형 (최소한으로만)
                                        # 경계에 가까울수록 변형 강도 급격히 감소
                                        surrounding_factor = 1.0 - normalized_dist * 0.8  # 경계에 가까우면 거의 변형 안 함
                                        scale = 1.0 + (right_ratio - 1.0) * surrounding_factor * 0.5  # 최대 50%만 변형
                                    
                                    transformed_landmarks[idx] = (
                                        eye_center_x + dx * scale,
                                        eye_center_y + dy * scale
                                    )
                                    transformed_indices.add(idx)
                            else:
                                # 변형되지 않은 포인트 추적
                                reason = []
                                if not is_inside_boundary:
                                    reason.append("경계밖")
                                if not is_surrounding_point:
                                    reason.append("주변포인트아님")
                                if not is_within_distance:
                                    reason.append("거리초과")
                                if idx in left_eye_excluded_indices:
                                    reason.append("왼쪽눈영역")
                                skipped_points.append((idx, ", ".join(reason) if reason else "알수없음"))
                    
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 크기 랜드마크 변형 실패: {e}")
        import traceback
        traceback.print_exc()
        return landmarks


def transform_landmarks_for_nose_size(landmarks, nose_size_ratio=1.0):
    """
    코 크기 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        nose_size_ratio: 코 크기 비율
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(nose_size_ratio - 1.0) < 0.01:
        return landmarks
    
    try:
        from utils.face_landmarks import NOSE_TIP_INDEX
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks.get('nose') is None:
            return landmarks
        
        # 코 영역의 랜드마크 인덱스 (더 많은 포인트 포함)
        # 코 끝 및 코 영역: 기본 포인트
        nose_indices = [8, 240, 98, 164, 327, 460, 4]
        # 코 측면 및 날개 부분 추가
        nose_side_indices = [1, 2, 5, 6, 19, 20, 94, 125, 141, 235, 236, 3, 51, 48, 115, 131, 134, 102, 49, 220, 305, 281, 363, 360, 279, 358, 326, 97, 64, 291]
        # 중복 제거
        all_nose_indices = list(set(nose_indices + nose_side_indices))
        
        # 코 중심점 계산: 코 영역의 모든 포인트의 중심 사용 (더 정확함)
        nose_points = [landmarks[i] for i in all_nose_indices if i < len(landmarks)]
        if nose_points:
            nose_center = (
                sum(p[0] for p in nose_points) / len(nose_points),
                sum(p[1] for p in nose_points) / len(nose_points)
            )
        else:
            # 포인트가 없으면 기본 코 끝점 사용
            nose_center = key_landmarks['nose']
        
        transformed_landmarks = list(landmarks)
        
        # 변형된 포인트 개수 추적
        transformed_count = 0
        for idx in all_nose_indices:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                dx = x - nose_center[0]
                dy = y - nose_center[1]
                transformed_landmarks[idx] = (
                    nose_center[0] + dx * nose_size_ratio,
                    nose_center[1] + dy * nose_size_ratio
                )
                transformed_count += 1
        
        print(f"[얼굴모핑] 코 크기 랜드마크 변형: 비율={nose_size_ratio:.2f}, 변형된 포인트={transformed_count}개, 코 중심={nose_center}")
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 코 크기 랜드마크 변형 실패: {e}")
        return landmarks


def transform_landmarks_for_jaw(landmarks, jaw_adjustment=0.0):
    """
    턱선 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        jaw_adjustment: 턱선 조정 값 (-50 ~ +50, 음수=작게, 양수=크게)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(jaw_adjustment) < 0.1:
        return landmarks
    
    try:
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return landmarks
        
        # 턱 조정 비율 계산 (음수면 작게, 양수면 크게)
        # -50 ~ +50을 0.7 ~ 1.3 비율로 변환
        jaw_ratio = 1.0 + (jaw_adjustment / 50.0) * 0.3
        jaw_ratio = max(0.7, min(1.3, jaw_ratio))
        
        # 얼굴 중심점 (턱 변형의 기준점)
        face_center = key_landmarks.get('face_center')
        if face_center is None:
            return landmarks
        
        # 얼굴 윤곽 랜드마크 인덱스 (MediaPipe Face Mesh: 인덱스 0-16이 턱선)
        # 턱선: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
        jaw_indices = list(range(17))  # 0-16
        
        transformed_landmarks = list(landmarks)
        
        # 턱선 랜드마크 변형 (얼굴 중심을 기준으로 수평 확장/축소)
        for idx in jaw_indices:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                # 얼굴 중심점 기준으로 수평 거리만 조정
                dx = x - face_center[0]
                transformed_landmarks[idx] = (
                    face_center[0] + dx * jaw_ratio,
                    y  # 수직 위치는 유지
                )
        
        print(f"[얼굴모핑] 턱선 랜드마크 변형: 조정값={jaw_adjustment:.1f}, 비율={jaw_ratio:.2f}, 변형된 포인트={len(jaw_indices)}개")
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 턱선 랜드마크 변형 실패: {e}")
        import traceback
        traceback.print_exc()
        return landmarks


def transform_landmarks_for_face_size(landmarks, face_width_ratio=1.0, face_height_ratio=1.0):
    """
    얼굴 크기 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        face_width_ratio: 얼굴 너비 비율
        face_height_ratio: 얼굴 높이 비율
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(face_width_ratio - 1.0) < 0.01 and abs(face_height_ratio - 1.0) < 0.01:
        return landmarks
    
    try:
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return landmarks
        
        # 얼굴 중심점
        face_center = key_landmarks.get('face_center')
        if face_center is None:
            return landmarks
        
        transformed_landmarks = list(landmarks)
        
        # 모든 랜드마크 포인트에 대해 얼굴 중심 기준으로 크기 조정
        for idx in range(len(landmarks)):
            x, y = landmarks[idx]
            dx = x - face_center[0]
            dy = y - face_center[1]
            transformed_landmarks[idx] = (
                face_center[0] + dx * face_width_ratio,
                face_center[1] + dy * face_height_ratio
            )
        
        print(f"[얼굴모핑] 얼굴 크기 랜드마크 변형: 너비={face_width_ratio:.2f}, 높이={face_height_ratio:.2f}, 변형된 포인트={len(landmarks)}개")
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 얼굴 크기 랜드마크 변형 실패: {e}")
        import traceback
        traceback.print_exc()
        return landmarks


def transform_landmarks_for_mouth_size(landmarks, mouth_size_ratio=1.0, mouth_width_ratio=1.0):
    """
    입 크기 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        mouth_size_ratio: 입 크기 비율 (수직)
        mouth_width_ratio: 입 너비 비율 (수평)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(mouth_size_ratio - 1.0) < 0.01 and abs(mouth_width_ratio - 1.0) < 0.01:
        return landmarks
    
    try:
        from utils.face_landmarks import MOUTH_INDICES
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks.get('mouth') is None:
            return landmarks
        
        mouth_center = key_landmarks['mouth']
        transformed_landmarks = list(landmarks)
        
        for idx in MOUTH_INDICES:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                dx = x - mouth_center[0]
                dy = y - mouth_center[1]
                # 너비는 x축만, 크기는 y축만 조정
                transformed_landmarks[idx] = (
                    mouth_center[0] + dx * mouth_width_ratio,
                    mouth_center[1] + dy * mouth_size_ratio
                )
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 입 크기 랜드마크 변형 실패: {e}")
        return landmarks


def transform_landmarks_for_eye_position(landmarks, left_eye_position_x=0.0, left_eye_position_y=0.0,
                                       right_eye_position_x=0.0, right_eye_position_y=0.0):
    """
    눈 위치 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        left_eye_position_x: 왼쪽 눈 수평 이동 (픽셀)
        left_eye_position_y: 왼쪽 눈 수직 이동 (픽셀)
        right_eye_position_x: 오른쪽 눈 수평 이동 (픽셀)
        right_eye_position_y: 오른쪽 눈 수직 이동 (픽셀)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if (abs(left_eye_position_x) < 0.1 and abs(left_eye_position_y) < 0.1 and
        abs(right_eye_position_x) < 0.1 and abs(right_eye_position_y) < 0.1):
        return landmarks
    
    try:
        from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
        
        transformed_landmarks = list(landmarks)
        
        # 왼쪽 눈 이동
        if abs(left_eye_position_x) >= 0.1 or abs(left_eye_position_y) >= 0.1:
            for idx in LEFT_EYE_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    transformed_landmarks[idx] = (
                        x + left_eye_position_x,
                        y + left_eye_position_y
                    )
        
        # 오른쪽 눈 이동
        if abs(right_eye_position_x) >= 0.1 or abs(right_eye_position_y) >= 0.1:
            for idx in RIGHT_EYE_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    transformed_landmarks[idx] = (
                        x + right_eye_position_x,
                        y + right_eye_position_y
                    )
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 위치 랜드마크 변형 실패: {e}")
        return landmarks


def transform_landmarks_for_lip_shape(landmarks, upper_lip_shape=1.0, lower_lip_shape=1.0):
    """
    입술 모양(두께) 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        upper_lip_shape: 윗입술 모양/두께 비율 (0.5 ~ 2.0)
        lower_lip_shape: 아랫입술 모양/두께 비율 (0.5 ~ 2.0)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(upper_lip_shape - 1.0) < 0.01 and abs(lower_lip_shape - 1.0) < 0.01:
        return landmarks
    
    try:
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks.get('mouth') is None:
            return landmarks
        
        mouth_center = key_landmarks['mouth']
        transformed_landmarks = list(landmarks)
        
        # 입술 인덱스 (preview.py에서 참조)
        # 윗입술 외곽
        UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
        # 아래입술 외곽
        LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
        # 입 안쪽 (윗입술과 아래입술 모두 포함)
        INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
        
        # 윗입술 모양 조정 (수직 방향으로 확대/축소)
        if abs(upper_lip_shape - 1.0) >= 0.01:
            # 윗입술 중심 계산
            upper_lip_points = [landmarks[i] for i in UPPER_LIP_INDICES if i < len(landmarks)]
            if upper_lip_points:
                upper_lip_center_y = sum(p[1] for p in upper_lip_points) / len(upper_lip_points)
                
                for idx in UPPER_LIP_INDICES:
                    if idx < len(landmarks):
                        x, y = landmarks[idx]
                        # 입술 중심 기준으로 수직 방향만 조정
                        dy = y - upper_lip_center_y
                        transformed_landmarks[idx] = (
                            x,
                            upper_lip_center_y + dy * upper_lip_shape
                        )
                
                # 입 안쪽 윗입술 부분도 조정
                for idx in INNER_LIP_INDICES[:len(INNER_LIP_INDICES)//2]:
                    if idx < len(landmarks):
                        x, y = landmarks[idx]
                        if y < mouth_center[1]:  # 윗입술 영역
                            dy = y - upper_lip_center_y
                            transformed_landmarks[idx] = (
                                x,
                                upper_lip_center_y + dy * upper_lip_shape
                            )
        
        # 아래입술 모양 조정 (수직 방향으로 확대/축소)
        if abs(lower_lip_shape - 1.0) >= 0.01:
            # 아래입술 중심 계산
            lower_lip_points = [landmarks[i] for i in LOWER_LIP_INDICES if i < len(landmarks)]
            if lower_lip_points:
                lower_lip_center_y = sum(p[1] for p in lower_lip_points) / len(lower_lip_points)
                
                for idx in LOWER_LIP_INDICES:
                    if idx < len(landmarks):
                        x, y = landmarks[idx]
                        # 입술 중심 기준으로 수직 방향만 조정
                        dy = y - lower_lip_center_y
                        transformed_landmarks[idx] = (
                            x,
                            lower_lip_center_y + dy * lower_lip_shape
                        )
                
                # 입 안쪽 아래입술 부분도 조정
                for idx in INNER_LIP_INDICES[len(INNER_LIP_INDICES)//2:]:
                    if idx < len(landmarks):
                        x, y = landmarks[idx]
                        if y >= mouth_center[1]:  # 아래입술 영역
                            dy = y - lower_lip_center_y
                            transformed_landmarks[idx] = (
                                x,
                                lower_lip_center_y + dy * lower_lip_shape
                            )
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 입술 모양 랜드마크 변형 실패: {e}")
        return landmarks


def transform_landmarks_for_lip_width(landmarks, upper_lip_width=1.0, lower_lip_width=1.0):
    """
    입술 너비 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        upper_lip_width: 윗입술 너비 비율 (0.5 ~ 2.0)
        lower_lip_width: 아랫입술 너비 비율 (0.5 ~ 2.0)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(upper_lip_width - 1.0) < 0.01 and abs(lower_lip_width - 1.0) < 0.01:
        return landmarks
    
    try:
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks.get('mouth') is None:
            return landmarks
        
        mouth_center = key_landmarks['mouth']
        transformed_landmarks = list(landmarks)
        
        # 입술 인덱스
        UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
        LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
        INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
        
        # 윗입술 너비 조정 (수평 방향으로 확대/축소)
        if abs(upper_lip_width - 1.0) >= 0.01:
            for idx in UPPER_LIP_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    dx = x - mouth_center[0]
                    transformed_landmarks[idx] = (
                        mouth_center[0] + dx * upper_lip_width,
                        y
                    )
            
            # 입 안쪽 윗입술 부분도 조정
            for idx in INNER_LIP_INDICES[:len(INNER_LIP_INDICES)//2]:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    if y < mouth_center[1]:  # 윗입술 영역
                        dx = x - mouth_center[0]
                        transformed_landmarks[idx] = (
                            mouth_center[0] + dx * upper_lip_width,
                            y
                        )
        
        # 아래입술 너비 조정 (수평 방향으로 확대/축소)
        if abs(lower_lip_width - 1.0) >= 0.01:
            for idx in LOWER_LIP_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    dx = x - mouth_center[0]
                    transformed_landmarks[idx] = (
                        mouth_center[0] + dx * lower_lip_width,
                        y
                    )
            
            # 입 안쪽 아래입술 부분도 조정
            for idx in INNER_LIP_INDICES[len(INNER_LIP_INDICES)//2:]:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    if y >= mouth_center[1]:  # 아래입술 영역
                        dx = x - mouth_center[0]
                        transformed_landmarks[idx] = (
                            mouth_center[0] + dx * lower_lip_width,
                            y
                        )
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 입술 너비 랜드마크 변형 실패: {e}")
        return landmarks


def transform_landmarks_for_lip_vertical_move(landmarks, upper_lip_vertical_move=0.0, lower_lip_vertical_move=0.0):
    """
    입술 수직 이동 조정을 랜드마크 변형으로 변환합니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        upper_lip_vertical_move: 윗입술 수직 이동 (픽셀, 양수=위로, 음수=아래로)
        lower_lip_vertical_move: 아랫입술 수직 이동 (픽셀, 양수=아래로, 음수=위로)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(upper_lip_vertical_move) < 0.1 and abs(lower_lip_vertical_move) < 0.1:
        return landmarks
    
    try:
        from utils.face_landmarks import get_key_landmarks
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None or key_landmarks.get('mouth') is None:
            return landmarks
        
        mouth_center = key_landmarks['mouth']
        transformed_landmarks = list(landmarks)
        
        # 입술 인덱스
        UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
        LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
        INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
        
        # 윗입술 수직 이동
        if abs(upper_lip_vertical_move) >= 0.1:
            # 양수=위로, 음수=아래로 이동
            move_y = -upper_lip_vertical_move  # UI에서는 양수=위로이므로 y축은 반대
            
            for idx in UPPER_LIP_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    transformed_landmarks[idx] = (x, y + move_y)
            
            # 입 안쪽 윗입술 부분도 이동
            for idx in INNER_LIP_INDICES[:len(INNER_LIP_INDICES)//2]:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    if y < mouth_center[1]:  # 윗입술 영역
                        transformed_landmarks[idx] = (x, y + move_y)
        
        # 아래입술 수직 이동
        if abs(lower_lip_vertical_move) >= 0.1:
            # 양수=아래로, 음수=위로 이동
            move_y = lower_lip_vertical_move
            
            for idx in LOWER_LIP_INDICES:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    transformed_landmarks[idx] = (x, y + move_y)
            
            # 입 안쪽 아래입술 부분도 이동
            for idx in INNER_LIP_INDICES[len(INNER_LIP_INDICES)//2:]:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    if y >= mouth_center[1]:  # 아래입술 영역
                        transformed_landmarks[idx] = (x, y + move_y)
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 입술 수직 이동 랜드마크 변형 실패: {e}")
        return landmarks


def move_landmark_group(landmarks, group_name, offset_x=0.0, offset_y=0.0, maintain_relative_positions=True):
    """
    랜드마크 그룹을 이동시킵니다 (눈, 코, 입 등).
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트
        group_name: 그룹 이름 ('left_eye', 'right_eye', 'nose', 'mouth', 'upper_lip', 'lower_lip')
        offset_x: 수평 이동 (픽셀)
        offset_y: 수직 이동 (픽셀)
        maintain_relative_positions: 그룹 내부 랜드마크 간 상대적 위치 유지 여부 (기본값: True)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if abs(offset_x) < 0.1 and abs(offset_y) < 0.1:
        return landmarks
    
    try:
        from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES, NOSE_TIP_INDEX, MOUTH_INDICES
        
        transformed_landmarks = list(landmarks)
        
        # 그룹별 인덱스 결정
        if group_name == 'left_eye':
            group_indices = LEFT_EYE_INDICES
        elif group_name == 'right_eye':
            group_indices = RIGHT_EYE_INDICES
        elif group_name == 'nose':
            # 코 인덱스 (preview.py에서 참조)
            group_indices = [8, 240, 98, 164, 327, 460, 4]
        elif group_name == 'mouth':
            # 입 전체 인덱스
            OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
            INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
            group_indices = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))
        elif group_name == 'upper_lip':
            # 윗입술 인덱스
            group_indices = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
        elif group_name == 'lower_lip':
            # 아래입술 인덱스
            group_indices = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
        else:
            print(f"[얼굴모핑] 알 수 없는 그룹 이름: {group_name}")
            return landmarks
        
        if maintain_relative_positions:
            # 그룹 내부 랜드마크 간 상대적 위치 유지 (모든 포인트를 동일한 오프셋으로 이동)
            for idx in group_indices:
                if idx < len(landmarks):
                    x, y = landmarks[idx]
                    transformed_landmarks[idx] = (
                        x + offset_x,
                        y + offset_y
                    )
        else:
            # 그룹 중심 기준으로 이동 (중심점 계산 후 상대적 위치 유지하며 이동)
            group_points = [landmarks[i] for i in group_indices if i < len(landmarks)]
            if group_points:
                center_x = sum(p[0] for p in group_points) / len(group_points)
                center_y = sum(p[1] for p in group_points) / len(group_points)
                
                for idx in group_indices:
                    if idx < len(landmarks):
                        x, y = landmarks[idx]
                        # 중심점 기준 상대 위치 유지하며 이동
                        transformed_landmarks[idx] = (
                            (x - center_x) + center_x + offset_x,
                            (y - center_y) + center_y + offset_y
                        )
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 랜드마크 그룹 이동 실패: {e}")
        import traceback
        traceback.print_exc()
        return landmarks


def move_landmark_points(landmarks, point_indices, offsets, influence_radius=50.0):
    """
    특정 랜드마크 포인트를 이동시키고, 주변 포인트도 자연스럽게 이동시킵니다.
    
    Args:
        landmarks: 원본 랜드마크 포인트 리스트 [(x, y), ...]
        point_indices: 이동할 포인트 인덱스 리스트 [idx1, idx2, ...]
        offsets: 각 포인트의 이동 오프셋 리스트 [(dx1, dy1), (dx2, dy2), ...]
        influence_radius: 주변 포인트에 영향을 주는 반경 (픽셀, 기본값: 50.0)
    
    Returns:
        transformed_landmarks: 변형된 랜드마크 포인트 리스트
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    if len(point_indices) != len(offsets):
        print(f"[얼굴모핑] 포인트 인덱스와 오프셋 개수가 일치하지 않습니다: {len(point_indices)} != {len(offsets)}")
        return landmarks
    
    try:
        transformed_landmarks = list(landmarks)
        
        # 직접 이동할 포인트들
        direct_moves = {}
        for idx, offset in zip(point_indices, offsets):
            if 0 <= idx < len(landmarks):
                direct_moves[idx] = offset
        
        # 각 포인트에 대해 변형 계산
        for i in range(len(landmarks)):
            if i in direct_moves:
                # 직접 이동
                dx, dy = direct_moves[i]
                transformed_landmarks[i] = (landmarks[i][0] + dx, landmarks[i][1] + dy)
            else:
                # 주변 영향 계산 (가우시안 가중치)
                total_dx = 0.0
                total_dy = 0.0
                total_weight = 0.0
                
                for move_idx, (dx, dy) in direct_moves.items():
                    # 거리 계산
                    dist = ((landmarks[i][0] - landmarks[move_idx][0])**2 + 
                           (landmarks[i][1] - landmarks[move_idx][1])**2)**0.5
                    
                    if dist < influence_radius:
                        # 가우시안 가중치 (거리가 가까울수록 영향이 큼)
                        weight = np.exp(-(dist**2) / (2 * (influence_radius / 3)**2))
                        total_dx += dx * weight
                        total_dy += dy * weight
                        total_weight += weight
                
                if total_weight > 0:
                    # 가중 평균으로 이동
                    avg_dx = total_dx / total_weight
                    avg_dy = total_dy / total_weight
                    # 영향 감쇠 (거리에 따라)
                    influence_factor = min(1.0, total_weight)
                    transformed_landmarks[i] = (
                        landmarks[i][0] + avg_dx * influence_factor,
                        landmarks[i][1] + avg_dy * influence_factor
                    )
                else:
                    # 영향 없음
                    transformed_landmarks[i] = landmarks[i]
        
        return transformed_landmarks
        
    except Exception as e:
        print(f"[얼굴모핑] 랜드마크 포인트 이동 실패: {e}")
        import traceback
        traceback.print_exc()
        return landmarks


def apply_all_adjustments(image, eye_size=1.0, nose_size=1.0, mouth_size=1.0, mouth_width=1.0,
                          jaw_adjustment=0.0, face_width=1.0, face_height=1.0, landmarks=None,
                          left_eye_size=None, right_eye_size=None,
                          eye_spacing=False, left_eye_position_x=0.0, right_eye_position_x=0.0,
                          left_eye_position_y=0.0, right_eye_position_y=0.0,
                          eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                          left_eye_region_padding=None, right_eye_region_padding=None,
                          left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                          right_eye_region_offset_x=None, right_eye_region_offset_y=None,
                          use_individual_lip_region=False,
                          upper_lip_size=1.0, upper_lip_width=1.0,
                          lower_lip_size=1.0, lower_lip_width=1.0,
                          upper_lip_shape=1.0, lower_lip_shape=1.0, 
                          upper_lip_vertical_move=0.0, lower_lip_vertical_move=0.0,
                          upper_lip_region_padding_x=None, upper_lip_region_padding_y=None,
                          lower_lip_region_padding_x=None, lower_lip_region_padding_y=None,
        upper_lip_region_offset_x=None, upper_lip_region_offset_y=None,
        lower_lip_region_offset_x=None, lower_lip_region_offset_y=None,
        use_landmark_warping=False):
    """
    모든 얼굴 특징 보정을 한 번에 적용합니다.
    
    Args:
        image: PIL.Image 객체
        eye_size: 눈 크기 비율 (개별 조정 미사용 시)
        nose_size: 코 크기 비율
        mouth_size: 입 크기 비율 (개별 적용 미사용 시)
        mouth_width: 입 너비 비율 (개별 적용 미사용 시)
        jaw_adjustment: 턱선 조정 값
        face_width: 얼굴 너비 비율
        face_height: 얼굴 높이 비율
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        use_landmark_warping: 랜드마크 직접 변형 모드 사용 여부 (기본값: False)
            True일 때 Delaunay Triangulation 방식 사용
            False일 때 기존 영역 기반 방식 사용
        left_eye_size: 왼쪽 눈 크기 비율 (개별 조정 사용 시)
        right_eye_size: 오른쪽 눈 크기 비율 (개별 조정 사용 시)
        eye_spacing: 눈 간격 조정 활성화 여부 (Boolean, True면 자동으로 간격 조정)
        left_eye_position_x: 왼쪽 눈 수평 위치 조정 (픽셀)
        right_eye_position_x: 오른쪽 눈 수평 위치 조정 (픽셀)
        left_eye_position_y: 왼쪽 눈 수직 위치 조정 (픽셀)
        right_eye_position_y: 오른쪽 눈 수직 위치 조정 (픽셀)
        eye_region_padding: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 개별 파라미터 사용)
        eye_region_offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 개별 파라미터 사용)
        eye_region_offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 개별 파라미터 사용)
        left_eye_region_padding: 왼쪽 눈 영역 패딩 비율
        right_eye_region_padding: 오른쪽 눈 영역 패딩 비율
        left_eye_region_offset_x: 왼쪽 눈 영역 수평 오프셋
        left_eye_region_offset_y: 왼쪽 눈 영역 수직 오프셋
        right_eye_region_offset_x: 오른쪽 눈 영역 수평 오프셋
        right_eye_region_offset_y: 오른쪽 눈 영역 수직 오프셋
        use_individual_lip_region: 입술 개별 적용 여부 (Boolean, 호환성 유지)
        upper_lip_size: 윗입술 크기 비율 (개별 적용 사용 시, 호환성 유지)
        upper_lip_width: 윗입술 너비 비율 (개별 적용 사용 시, 호환성 유지)
        lower_lip_size: 아래입술 크기 비율 (개별 적용 사용 시, 호환성 유지)
        lower_lip_width: 아래입술 너비 비율 (개별 적용 사용 시, 호환성 유지)
        upper_lip_shape: 윗입술 모양/두께 비율 (0.5 ~ 2.0, 기본값: 1.0)
        lower_lip_shape: 아랫입술 모양/두께 비율 (0.5 ~ 2.0, 기본값: 1.0)
        upper_lip_vertical_move: 윗입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=위로, 음수=아래로)
        lower_lip_vertical_move: 아랫입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=아래로, 음수=위로)
        Note: upper_lip_width와 lower_lip_width는 use_individual_lip_region=True일 때 사용되며,
              새로운 방식에서는 upper_lip_shape, lower_lip_shape와 함께 사용됩니다.
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지 (한 번만)
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 랜드마크 직접 변형 모드 사용 시
        if use_landmark_warping and _scipy_available:
            # 원본 랜드마크 저장
            original_landmarks = list(landmarks)
            transformed_landmarks = list(landmarks)
            
            # 각 편집 파라미터를 기반으로 랜드마크 포인트 변형
            # 1. 눈 위치 조정 (변경이 있을 때만)
            if (abs(left_eye_position_x) >= 0.1 or abs(left_eye_position_y) >= 0.1 or 
                abs(right_eye_position_x) >= 0.1 or abs(right_eye_position_y) >= 0.1):
                transformed_landmarks = transform_landmarks_for_eye_position(
                    transformed_landmarks,
                    left_eye_position_x, left_eye_position_y,
                    right_eye_position_x, right_eye_position_y
                )
            
            # 2. 눈 크기 조정 (변경이 있을 때만)
            if left_eye_size is not None or right_eye_size is not None:
                # 개별 눈 크기 조정 모드: 둘 다 1.0에 가까우면 스킵
                left_ratio = left_eye_size if left_eye_size is not None else 1.0
                right_ratio = right_eye_size if right_eye_size is not None else 1.0
                # 유효성 검사: 값이 None이 아니고 유효한 범위인지 확인
                if left_ratio is not None and right_ratio is not None:
                    if (0.1 <= left_ratio <= 5.0 or 0.1 <= right_ratio <= 5.0) and \
                       (abs(left_ratio - 1.0) >= 0.01 or abs(right_ratio - 1.0) >= 0.01):
                        print(f"[얼굴모핑] 눈 크기 조정: 왼쪽={left_ratio:.2f}, 오른쪽={right_ratio:.2f}")
                        transformed_landmarks = transform_landmarks_for_eye_size(
                            transformed_landmarks,
                            eye_size_ratio=1.0,
                            left_eye_size_ratio=left_eye_size,
                            right_eye_size_ratio=right_eye_size
                        )
                    else:
                        print(f"[얼굴모핑] 눈 크기 조정 스킵: 왼쪽={left_ratio:.2f}, 오른쪽={right_ratio:.2f} (기본값 또는 범위 밖)")
            elif eye_size is not None and abs(eye_size - 1.0) >= 0.01:
                if 0.1 <= eye_size <= 5.0:
                    print(f"[얼굴모핑] 눈 크기 조정: 양쪽={eye_size:.2f}")
                    transformed_landmarks = transform_landmarks_for_eye_size(
                        transformed_landmarks,
                        eye_size_ratio=eye_size
                    )
                else:
                    print(f"[얼굴모핑] 눈 크기 조정 스킵: 값={eye_size:.2f} (범위 밖)")
            
            # 3. 코 크기 조정
            if abs(nose_size - 1.0) >= 0.01:
                print(f"[얼굴모핑] 코 크기 조정 적용: nose_size={nose_size:.2f}")
                transformed_landmarks = transform_landmarks_for_nose_size(
                    transformed_landmarks,
                    nose_size_ratio=nose_size
                )
                print(f"[얼굴모핑] 코 크기 조정 후 랜드마크 변형 완료")
            
            # 4. 입 크기 조정 (기본 파라미터 사용 시)
            if not use_individual_lip_region:
                if abs(mouth_size - 1.0) >= 0.01 or abs(mouth_width - 1.0) >= 0.01:
                    transformed_landmarks = transform_landmarks_for_mouth_size(
                        transformed_landmarks,
                        mouth_size_ratio=mouth_size,
                        mouth_width_ratio=mouth_width
                    )
            
            # 5. 입술 세부 편집 (shape, width, vertical_move)
            # 입술 모양(두께) 조정
            if abs(upper_lip_shape - 1.0) >= 0.01 or abs(lower_lip_shape - 1.0) >= 0.01:
                transformed_landmarks = transform_landmarks_for_lip_shape(
                    transformed_landmarks,
                    upper_lip_shape=upper_lip_shape,
                    lower_lip_shape=lower_lip_shape
                )
            
            # 입술 너비 조정
            if abs(upper_lip_width - 1.0) >= 0.01 or abs(lower_lip_width - 1.0) >= 0.01:
                transformed_landmarks = transform_landmarks_for_lip_width(
                    transformed_landmarks,
                    upper_lip_width=upper_lip_width,
                    lower_lip_width=lower_lip_width
                )
            
            # 입술 수직 이동 조정
            if abs(upper_lip_vertical_move) >= 0.1 or abs(lower_lip_vertical_move) >= 0.1:
                transformed_landmarks = transform_landmarks_for_lip_vertical_move(
                    transformed_landmarks,
                    upper_lip_vertical_move=upper_lip_vertical_move,
                    lower_lip_vertical_move=lower_lip_vertical_move
                )
            
            # 6. 얼굴 윤곽(턱선) 조정
            if abs(jaw_adjustment) >= 0.1:
                transformed_landmarks = transform_landmarks_for_jaw(
                    transformed_landmarks,
                    jaw_adjustment=jaw_adjustment
                )
            
            # 7. 얼굴 크기 조정 (너비/높이)
            if abs(face_width - 1.0) >= 0.01 or abs(face_height - 1.0) >= 0.01:
                transformed_landmarks = transform_landmarks_for_face_size(
                    transformed_landmarks,
                    face_width_ratio=face_width,
                    face_height_ratio=face_height
                )
            
            # 랜드마크 변형을 이미지에 적용
            # 변형이 실제로 있었는지 확인 (원본과 동일하면 스킵)
            landmarks_changed = False
            for i in range(len(original_landmarks)):
                if abs(original_landmarks[i][0] - transformed_landmarks[i][0]) > 0.1 or \
                   abs(original_landmarks[i][1] - transformed_landmarks[i][1]) > 0.1:
                    landmarks_changed = True
                    break
            
            if not landmarks_changed:
                print("[얼굴모핑] 랜드마크 변형 없음 (모든 값이 기본값), 원본 이미지 반환")
                return image
            
            print(f"[얼굴모핑] 랜드마크 변형 적용: 원본 {len(original_landmarks)}개, 변형 {len(transformed_landmarks)}개")
            result = morph_face_by_polygons(image, original_landmarks, transformed_landmarks)
            if result is None:
                print("[얼굴모핑] 랜드마크 변형 결과가 None입니다")
                return image
            else:
                print("[얼굴모핑] 랜드마크 변형 완료")
            return result
        
        # 각 조정을 순차적으로 적용
        # 순서: 간격 조정 → 위치 조정 → 크기 조정 → 기타 조정
        result = image.copy()
        
        # 눈 영역 파라미터 결정 (개별 파라미터가 있으면 사용, 없으면 기본값 사용)
        use_individual_region = (left_eye_region_padding is not None or right_eye_region_padding is not None)
        
        # 1. 눈 간격 조정은 수평 조정 값으로 처리되므로 여기서는 처리하지 않음
        # (눈 간격 조정 체크박스는 수평 조정 시 반대 동기화만 담당)
        
        # 2. 눈 위치 조정 (왼쪽/오른쪽 개별 처리)
        # 왼쪽 눈 위치 조정
        if abs(left_eye_position_x) >= 0.1 or abs(left_eye_position_y) >= 0.1:
            if use_individual_region:
                result = adjust_eye_position(result, left_eye_position_x, left_eye_position_y, landmarks,
                                            None, None, None,  # 기본 파라미터는 None
                                            left_eye_region_padding, right_eye_region_padding,
                                            left_eye_region_offset_x, left_eye_region_offset_y,
                                            right_eye_region_offset_x, right_eye_region_offset_y,
                                            eye='left')
            else:
                result = adjust_eye_position(result, left_eye_position_x, left_eye_position_y, landmarks,
                                            eye_region_padding, eye_region_offset_x, eye_region_offset_y,
                                            None, None, None, None, None, None,  # 개별 파라미터는 None
                                            eye='left')
        
        # 오른쪽 눈 위치 조정
        if abs(right_eye_position_x) >= 0.1 or abs(right_eye_position_y) >= 0.1:
            if use_individual_region:
                result = adjust_eye_position(result, right_eye_position_x, right_eye_position_y, landmarks,
                                            None, None, None,  # 기본 파라미터는 None
                                            left_eye_region_padding, right_eye_region_padding,
                                            left_eye_region_offset_x, left_eye_region_offset_y,
                                            right_eye_region_offset_x, right_eye_region_offset_y,
                                            eye='right')
            else:
                result = adjust_eye_position(result, right_eye_position_x, right_eye_position_y, landmarks,
                                            eye_region_padding, eye_region_offset_x, eye_region_offset_y,
                                            None, None, None, None, None, None,  # 개별 파라미터는 None
                                            eye='right')
        
        # 3. 눈 크기 조정 (개별 조정 또는 기본 조정, 개별 파라미터 전달)
        if left_eye_size is not None or right_eye_size is not None:
            # 개별 조정 모드
            if use_individual_region:
                result = adjust_eye_size(result, eye_size_ratio=1.0, landmarks=landmarks,
                                        left_eye_size_ratio=left_eye_size, right_eye_size_ratio=right_eye_size,
                                        eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                                        left_eye_region_padding=left_eye_region_padding, right_eye_region_padding=right_eye_region_padding,
                                        left_eye_region_offset_x=left_eye_region_offset_x, left_eye_region_offset_y=left_eye_region_offset_y,
                                        right_eye_region_offset_x=right_eye_region_offset_x, right_eye_region_offset_y=right_eye_region_offset_y)
            else:
                result = adjust_eye_size(result, eye_size_ratio=1.0, landmarks=landmarks,
                                        left_eye_size_ratio=left_eye_size, right_eye_size_ratio=right_eye_size,
                                        eye_region_padding=eye_region_padding, eye_region_offset_x=eye_region_offset_x, eye_region_offset_y=eye_region_offset_y,
                                        left_eye_region_padding=None, right_eye_region_padding=None,
                                        left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                                        right_eye_region_offset_x=None, right_eye_region_offset_y=None)
        elif abs(eye_size - 1.0) >= 0.01:
            # 기본 조정 모드
            if use_individual_region:
                result = adjust_eye_size(result, eye_size_ratio=eye_size, landmarks=landmarks,
                                        eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                                        left_eye_region_padding=left_eye_region_padding, right_eye_region_padding=right_eye_region_padding,
                                        left_eye_region_offset_x=left_eye_region_offset_x, left_eye_region_offset_y=left_eye_region_offset_y,
                                        right_eye_region_offset_x=right_eye_region_offset_x, right_eye_region_offset_y=right_eye_region_offset_y)
            else:
                result = adjust_eye_size(result, eye_size_ratio=eye_size, landmarks=landmarks,
                                        eye_region_padding=eye_region_padding, eye_region_offset_x=eye_region_offset_x, eye_region_offset_y=eye_region_offset_y,
                                        left_eye_region_padding=None, right_eye_region_padding=None,
                                        left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                                        right_eye_region_offset_x=None, right_eye_region_offset_y=None)
        
        # 4. 기타 조정
        result = adjust_nose_size(result, nose_size, landmarks)
        
        # 입 편집 (새로운 3가지 파라미터 사용)
        # 입술 영역 파라미터 결정 (개별 적용 여부에 따라, None이면 기본값 사용)
        # 기본값 설정
        default_padding_x = 0.2
        default_padding_y = 0.3
        default_offset_x = 0.0
        default_offset_y = 0.0
        
        if use_individual_lip_region:
            # 개별 적용 모드
            upper_padding_x = upper_lip_region_padding_x if upper_lip_region_padding_x is not None else default_padding_x
            upper_padding_y = upper_lip_region_padding_y if upper_lip_region_padding_y is not None else default_padding_y
            upper_offset_x = upper_lip_region_offset_x if upper_lip_region_offset_x is not None else default_offset_x
            upper_offset_y = upper_lip_region_offset_y if upper_lip_region_offset_y is not None else default_offset_y
            lower_padding_x = lower_lip_region_padding_x if lower_lip_region_padding_x is not None else default_padding_x
            lower_padding_y = lower_lip_region_padding_y if lower_lip_region_padding_y is not None else default_padding_y
            lower_offset_x = lower_lip_region_offset_x if lower_lip_region_offset_x is not None else default_offset_x
            lower_offset_y = lower_lip_region_offset_y if lower_lip_region_offset_y is not None else default_offset_y
        else:
            # 동기화 모드: 윗입술 값을 아래입술에 복사 (None이면 기본값 사용)
            upper_padding_x = upper_lip_region_padding_x if upper_lip_region_padding_x is not None else default_padding_x
            upper_padding_y = upper_lip_region_padding_y if upper_lip_region_padding_y is not None else default_padding_y
            upper_offset_x = upper_lip_region_offset_x if upper_lip_region_offset_x is not None else default_offset_x
            upper_offset_y = upper_lip_region_offset_y if upper_lip_region_offset_y is not None else default_offset_y
            lower_padding_x = upper_padding_x  # 윗입술 값 복사
            lower_padding_y = upper_padding_y
            lower_offset_x = upper_offset_x
            lower_offset_y = upper_offset_y
        
        # 1. 윗입술 모양 조정 (두께)
        if abs(upper_lip_shape - 1.0) >= 0.01:
            result = adjust_upper_lip_shape(result, upper_lip_shape, landmarks,
                                          upper_padding_x, upper_padding_y, upper_offset_x, upper_offset_y)
        
        # 2. 아랫입술 모양 조정 (두께)
        if abs(lower_lip_shape - 1.0) >= 0.01:
            result = adjust_lower_lip_shape(result, lower_lip_shape, landmarks,
                                          lower_padding_x, lower_padding_y, lower_offset_x, lower_offset_y)
        
        # 3. 윗입술 너비 조정
        if abs(upper_lip_width - 1.0) >= 0.01:
            result = adjust_upper_lip_width(result, upper_lip_width, landmarks,
                                          upper_padding_x, upper_padding_y, upper_offset_x, upper_offset_y)
        
        # 4. 아랫입술 너비 조정
        if abs(lower_lip_width - 1.0) >= 0.01:
            result = adjust_lower_lip_width(result, lower_lip_width, landmarks,
                                          lower_padding_x, lower_padding_y, lower_offset_x, lower_offset_y)
        
        # 5. 입술 수직 이동 조정
        if abs(upper_lip_vertical_move) >= 0.1 or abs(lower_lip_vertical_move) >= 0.1:
            result = adjust_lip_vertical_move(result, upper_lip_vertical_move, lower_lip_vertical_move, landmarks,
                                             upper_padding_x, upper_padding_y,
                                             lower_padding_x, lower_padding_y,
                                             upper_offset_x, upper_offset_y,
                                             lower_offset_x, lower_offset_y)
        
        # 기존 입 편집 함수는 호환성을 위해 유지 (새 파라미터가 없을 때만 사용)
        if upper_lip_shape == 1.0 and lower_lip_shape == 1.0 and abs(upper_lip_vertical_move) < 0.1 and abs(lower_lip_vertical_move) < 0.1:
            if use_individual_lip_region:
                # 개별 적용 모드: 윗입술과 아래입술 각각 편집
                result = adjust_upper_lip_size(result, upper_lip_size, upper_lip_width, landmarks)
                result = adjust_lower_lip_size(result, lower_lip_size, lower_lip_width, landmarks)
            elif abs(mouth_size - 1.0) >= 0.01 or abs(mouth_width - 1.0) >= 0.01:
                # 통합 모드: 입 전체 편집
                result = adjust_mouth_size(result, mouth_size, mouth_width, landmarks)
        
        result = adjust_jaw(result, jaw_adjustment, landmarks)
        result = adjust_face_size(result, face_width, face_height, landmarks)
        
        return result
        
    except Exception as e:
        print(f"[얼굴모핑] 얼굴 특징 보정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image
