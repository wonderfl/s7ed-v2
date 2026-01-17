"""
영역 추출 함수 모듈
얼굴 특징 영역(눈, 입, 코)을 추출하는 함수들
"""
from .constants import _landmarks_available


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
