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


def transform_points_for_eye_size(landmarks, eye_size_ratio=1.0, left_eye_size_ratio=None, right_eye_size_ratio=None):
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




def transform_points_for_nose_size(landmarks, nose_size_ratio=1.0):
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




def transform_points_for_jaw(landmarks, jaw_adjustment=0.0):
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




def transform_points_for_face_size(landmarks, face_width_ratio=1.0, face_height_ratio=1.0):
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




def transform_points_for_mouth_size(landmarks, mouth_size_ratio=1.0, mouth_width_ratio=1.0):
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




def transform_points_for_eye_position(landmarks, left_eye_position_x=0.0, left_eye_position_y=0.0,
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




def transform_points_for_lip_shape(landmarks, upper_lip_shape=1.0, lower_lip_shape=1.0):
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




def transform_points_for_lip_width(landmarks, upper_lip_width=1.0, lower_lip_width=1.0):
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




def transform_points_for_lip_vertical_move(landmarks, upper_lip_vertical_move=0.0, lower_lip_vertical_move=0.0):
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




