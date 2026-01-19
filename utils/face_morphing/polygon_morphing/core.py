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


from .utils import _get_neighbor_points, _check_triangles_flipped

def morph_face_by_polygons(image, original_landmarks, transformed_landmarks, selected_point_indices=None,
                           left_iris_center_coord=None, right_iris_center_coord=None,
                           left_iris_center_orig=None, right_iris_center_orig=None):
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
        
        # 눈동자 포인트 제거 및 중앙 포인트 추가
        # 1. 눈동자 인덱스 가져오기
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
        
        # 2. 눈동자 포인트 제거
        original_landmarks_no_iris = [pt for i, pt in enumerate(original_landmarks) if i not in iris_indices]
        transformed_landmarks_no_iris = [pt for i, pt in enumerate(transformed_landmarks) if i not in iris_indices]
        
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
            """contour 포인트의 평균으로 중앙 포인트 계산"""
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
            
            # 중앙 포인트 계산 (평균)
            if left_iris_points:
                left_center_x = sum(p[0] for p in left_iris_points) / len(left_iris_points)
                left_center_y = sum(p[1] for p in left_iris_points) / len(left_iris_points)
                left_iris_center = (left_center_x, left_center_y)
            else:
                left_iris_center = None
            
            if right_iris_points:
                right_center_x = sum(p[0] for p in right_iris_points) / len(right_iris_points)
                right_center_y = sum(p[1] for p in right_iris_points) / len(right_iris_points)
                right_iris_center = (right_center_x, right_center_y)
            else:
                right_iris_center = None
            
            return left_iris_center, right_iris_center
        
        if left_iris_center_coord is not None and right_iris_center_coord is not None:
            # 전달된 좌표는 변형된 중앙 포인트 (드래그로 변경된 좌표)
            # morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저 (len-2), MediaPipe RIGHT_IRIS 나중 (len-1)
            # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
            # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
            # 따라서: 사용자 왼쪽 = MediaPipe LEFT_IRIS, 사용자 오른쪽 = MediaPipe RIGHT_IRIS
            left_iris_center_trans = left_iris_center_coord  # 변형된 중앙 포인트 (사용자 왼쪽 = MediaPipe LEFT_IRIS)
            right_iris_center_trans = right_iris_center_coord  # 변형된 중앙 포인트 (사용자 오른쪽 = MediaPipe RIGHT_IRIS)
            
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
                    print(f"[얼굴모핑] 경고: 원본 왼쪽 중앙 포인트 계산 실패, 변형된 값을 원본으로 사용")
                if right_iris_center_orig is None:
                    right_iris_center_orig = right_iris_center_trans
                    print(f"[얼굴모핑] 경고: 원본 오른쪽 중앙 포인트 계산 실패, 변형된 값을 원본으로 사용")
            
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
                    
                    # 원본 중심점이 현재 이미지 크기를 벗어나는지 확인
                    needs_adjustment = (left_iris_center_orig[0] > img_width or left_iris_center_orig[1] > img_height or
                                       right_iris_center_orig[0] > img_width or right_iris_center_orig[1] > img_height or
                                       abs(orig_img_width - img_width) > 1.0 or abs(orig_img_height - img_height) > 1.0 or
                                       abs(offset_x) > 1.0 or abs(offset_y) > 1.0)
                    
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
                        
                        # print(f"[얼굴모핑] 중심점 좌표 조정: 원본 이미지 크기 추정={orig_img_width:.1f}x{orig_img_height:.1f}, "
                        #       f"현재 이미지 크기={img_width}x{img_height}, 오프셋=({offset_x:.1f}, {offset_y:.1f}), "
                        #       f"스케일 비율={scale_x:.3f}x{scale_y:.3f}")
                        # print(f"[얼굴모핑] 원본 중심점 조정 전: 왼쪽={left_iris_center_orig}, 오른쪽={right_iris_center_orig}")
                        # print(f"[얼굴모핑] 원본 중심점 오프셋 적용 후: 왼쪽={left_iris_center_orig_offset}, 오른쪽={right_iris_center_orig_offset}")
                        # print(f"[얼굴모핑] 원본 중심점 최종 조정 후: 왼쪽={left_iris_center_orig_scaled}, 오른쪽={right_iris_center_orig_scaled}")
                        # print(f"[얼굴모핑] 변형 중심점 조정 전: 왼쪽={left_iris_center_trans}, 오른쪽={right_iris_center_trans}")
                        # print(f"[얼굴모핑] 변형 중심점 오프셋 적용 후: 왼쪽={left_iris_center_trans_offset}, 오른쪽={right_iris_center_trans_offset}")
                        # print(f"[얼굴모핑] 변형 중심점 최종 조정 후: 왼쪽={left_iris_center_trans_scaled}, 오른쪽={right_iris_center_trans_scaled}")
                        
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
                            
                            print(f"[얼굴모핑] 원본 중심점 좌표 스케일링 (랜드마크 없음): 원본 이미지 크기 추정={orig_img_width:.1f}x{orig_img_height:.1f}, "
                                  f"현재 이미지 크기={img_width}x{img_height}, 스케일 비율={scale_x:.3f}x{scale_y:.3f}")
                            print(f"[얼굴모핑] 원본 중심점 스케일링 전: 왼쪽={left_iris_center_orig}, 오른쪽={right_iris_center_orig}")
                            print(f"[얼굴모핑] 원본 중심점 스케일링 후: 왼쪽={left_iris_center_orig_scaled}, 오른쪽={right_iris_center_orig_scaled}")
                            
                            left_iris_center_orig = left_iris_center_orig_scaled
                            right_iris_center_orig = right_iris_center_orig_scaled
        else:
            # 파라미터로 전달되지 않은 경우: 계산으로 중앙 포인트 구하기
            left_iris_center_orig, right_iris_center_orig = _calculate_iris_centers_from_contour(
                original_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height)
            left_iris_center_trans, right_iris_center_trans = _calculate_iris_centers_from_contour(
                transformed_landmarks_tuple, left_iris_indices, right_iris_indices, img_width, img_height)
        
        # 4. 중앙 포인트 추가 (morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저, MediaPipe RIGHT_IRIS 나중)
        if left_iris_center_orig is not None and right_iris_center_orig is not None:
            # MediaPipe LEFT_IRIS 먼저 추가 (len-2), MediaPipe RIGHT_IRIS 나중 추가 (len-1)
            original_landmarks_no_iris.append(left_iris_center_orig)   # MediaPipe LEFT_IRIS (사용자 왼쪽)
            original_landmarks_no_iris.append(right_iris_center_orig)  # MediaPipe RIGHT_IRIS (사용자 오른쪽)
            transformed_landmarks_no_iris.append(left_iris_center_trans)
            transformed_landmarks_no_iris.append(right_iris_center_trans)
            
            # 중앙 포인트 이동 거리 계산 (중앙 포인트가 실제로 변경되었을 때만 로그 출력)
            left_displacement = np.sqrt((left_iris_center_trans[0] - left_iris_center_orig[0])**2 + 
                                       (left_iris_center_trans[1] - left_iris_center_orig[1])**2)
            right_displacement = np.sqrt((right_iris_center_trans[0] - right_iris_center_orig[0])**2 + 
                                        (right_iris_center_trans[1] - right_iris_center_orig[1])**2)
            
            # 중앙 포인트가 실제로 변경되었을 때만 상세 로그 출력
            if left_displacement > 0.1 or right_displacement > 0.1:
                print(f"[얼굴모핑] Delaunay 포인트 구성: 원본 {len(original_landmarks)}개 -> 눈동자 {len(iris_indices)}개 제거 -> 중앙 포인트 2개 추가 -> 최종 {len(original_landmarks_no_iris)}개")
                print(f"[얼굴모핑] Delaunay 포인트 구성: 변환 {len(transformed_landmarks)}개 -> 눈동자 {len(iris_indices)}개 제거 -> 중앙 포인트 2개 추가 -> 최종 {len(transformed_landmarks_no_iris)}개")
                print(f"[얼굴모핑] 중앙 포인트 인덱스: 왼쪽={len(original_landmarks_no_iris) - 2}, 오른쪽={len(original_landmarks_no_iris) - 1} (Delaunay 배열 내 인덱스)")
                print(f"[얼굴모핑] 중앙 포인트 원본: 왼쪽={left_iris_center_orig}, 오른쪽={right_iris_center_orig}")
                print(f"[얼굴모핑] 중앙 포인트 변형: 왼쪽={left_iris_center_trans}, 오른쪽={right_iris_center_trans}")
                print(f"[얼굴모핑] 중앙 포인트 이동 거리: 왼쪽={left_displacement:.2f}픽셀, 오른쪽={right_displacement:.2f}픽셀 (이미지 크기: {img_width}x{img_height})")
        
        # 이미지 경계 포인트 추가 (Delaunay Triangulation을 위해)
        # 경계 포인트: 4개 모서리
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
                
                # 중앙 포인트(인덱스 468, 469) 또는 이동 거리가 큰 포인트만 상세 로그
                if i >= len(original_landmarks_no_iris) - 2 or displacement > 10.0:
                    displacement_details.append({
                        'idx': i,
                        'orig': orig_pt,
                        'trans': trans_pt,
                        'displacement': displacement,
                        'is_iris_center': i >= len(original_landmarks_no_iris) - 2
                    })
        
        # 이동 거리 상세 로그 출력
        # if displacement_details:
        #     print(f"[얼굴모핑] 포인트 이동 거리 상세 (이미지 크기: {img_width}x{img_height}):")
        #     for detail in sorted(displacement_details, key=lambda x: x['displacement'], reverse=True)[:10]:  # 상위 10개만
        #         iris_label = " (눈동자 중심점)" if detail['is_iris_center'] else ""
        #         print(f"  포인트 {detail['idx']}{iris_label}: 원본=({detail['orig'][0]:.2f}, {detail['orig'][1]:.2f}), "
        #               f"변형=({detail['trans'][0]:.2f}, {detail['trans'][1]:.2f}), "
        #               f"이동거리={detail['displacement']:.2f}픽셀")
        
        # 이미지 대각선 길이의 30%를 초과하면 경고
        image_diagonal = np.sqrt(img_width**2 + img_height**2)
        max_allowed_displacement = image_diagonal * 0.3
        # print(f"[얼굴모핑] 이동 거리 검증: 최대 이동={max_displacement:.2f}픽셀, 허용치={max_allowed_displacement:.2f}픽셀 "
        #       f"(이미지 대각선 {image_diagonal:.2f}픽셀의 30%)")
        
        if max_displacement > max_allowed_displacement:
            # print(f"[얼굴모핑] 경고: 포인트 {max_displacement_idx}가 너무 많이 이동했습니다 ({max_displacement:.1f}픽셀, 허용치: {max_allowed_displacement:.1f}픽셀)")
            # print(f"[얼굴모핑] 경고: 이미지 왜곡이 발생할 수 있습니다. 이동 거리를 줄여주세요.")
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
                            old_pos = transformed_landmarks_no_iris[i]
                            transformed_landmarks_no_iris[i] = (orig_pt[0] + limited_dx, orig_pt[1] + limited_dy)
                            new_displacement = np.sqrt(limited_dx**2 + limited_dy**2)
                            iris_label = " (눈동자 중심점)" if i >= len(original_landmarks_no_iris) - 2 else ""
                            # print(f"[얼굴모핑] 경고: 포인트 {i}{iris_label}의 이동 거리를 제한했습니다 "
                            #       f"({displacement:.2f} -> {new_displacement:.2f}픽셀, "
                            #       f"원본=({orig_pt[0]:.2f}, {orig_pt[1]:.2f}), "
                            #       f"제한 전=({old_pos[0]:.2f}, {old_pos[1]:.2f}), "
                            #       f"제한 후=({transformed_landmarks_no_iris[i][0]:.2f}, {transformed_landmarks_no_iris[i][1]:.2f}))")
                
                # 제한된 랜드마크로 배열 재생성 (중앙 포인트 포함)
                all_transformed_points = list(transformed_landmarks_no_iris) + boundary_points
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
        # 경계 포인트를 제외한 실제 랜드마크만 확인 (중앙 포인트 포함)
        # original_landmarks_no_iris는 중앙 포인트를 포함한 470개 구조
        landmarks_count = len(original_landmarks_no_iris)  # 중앙 포인트 포함
        if landmarks_count > 0:
            orig_pts = original_points_array[:landmarks_count]
            trans_pts = transformed_points_array[:landmarks_count]
            diffs = np.sqrt(np.sum((trans_pts - orig_pts)**2, axis=1))
            max_diff = np.max(diffs)
            changed_count = np.sum(diffs > 0.1)
            print(f"[얼굴모핑] 랜드마크 변형 확인: 최대 차이={max_diff:.2f}픽셀, 변경된 포인트={changed_count}개 (전체 {landmarks_count}개 중)")
        else:
            max_diff = 0.0
            changed_count = 0
        # 랜드마크가 변형되지 않았으면 원본 이미지 반환
        if max_diff < 0.1:
            print(f"[얼굴모핑] 랜드마크 변형이 없어 원본 이미지 반환 (max_diff={max_diff:.2f})")
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




