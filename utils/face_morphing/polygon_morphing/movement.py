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


def move_point_group(landmarks, group_name, offset_x=0.0, offset_y=0.0, maintain_relative_positions=True):
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




def move_points(landmarks, point_indices, offsets, influence_radius=50.0):
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




