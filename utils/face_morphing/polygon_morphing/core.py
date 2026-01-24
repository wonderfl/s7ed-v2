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
    """눈동자 중심점을 눈 영역 내로 제한
    
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
    
    # 마진 계산
    width = max_x - min_x
    height = max_y - min_y
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio
    
    # 제한된 영역 계산
    clamped_min_x = max(0, min_x - margin_x)
    clamped_min_y = max(0, min_y - margin_y)
    clamped_max_x = min(img_width, max_x + margin_x)
    clamped_max_y = min(img_height, max_y + margin_y)
    
    # 눈동자 중심점을 제한된 영역 내로 클램핑
    clamped_x = max(clamped_min_x, min(clamped_max_x, iris_center_coord[0]))
    clamped_y = max(clamped_min_y, min(clamped_max_y, iris_center_coord[1]))
    
    return (clamped_x, clamped_y)


def _prepare_iris_centers(original_landmarks, transformed_landmarks,
                         left_iris_center_coord, right_iris_center_coord,
                         left_iris_center_orig, right_iris_center_orig,
                         img_width, img_height, clamping_enabled=True, margin_ratio=0.3):    
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
    
    Returns:
        tuple: (original_landmarks_no_iris, transformed_landmarks_no_iris,
                original_points_array, transformed_points_array, iris_indices)
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
    
    # 디버깅: 전달된 중앙 포인트 좌표 확인
    try:
        from utils.logger import print_info
    except ImportError:
        def print_info(module, msg):
            print(f"[{module}] {msg}")
    
    print_info("얼굴모핑", f"morph_face_by_polygons 호출: left_iris_center_coord={left_iris_center_coord}, right_iris_center_coord={right_iris_center_coord}")
    print_info("얼굴모핑", f"원본 중앙 포인트: left_orig={left_iris_center_orig}, right_orig={right_iris_center_orig}")
    
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
    
    return (original_landmarks_no_iris, transformed_landmarks_no_iris,
            original_points_array, transformed_points_array, iris_indices)


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

def morph_face_by_polygons(image, original_landmarks, transformed_landmarks, selected_point_indices=None,
                           left_iris_center_coord=None, right_iris_center_coord=None,
                           left_iris_center_orig=None, right_iris_center_orig=None,
                           cached_original_bbox=None, blend_ratio=1.0,
                           clamping_enabled=True, margin_ratio=0.3, iris_center_only=False):
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

    try:        
        # 입력 검증 및 전처리
        validation_result = _validate_and_prepare_inputs(image, original_landmarks, transformed_landmarks)
        if validation_result is None:
            return image

        img_array, img_width, img_height = validation_result

        # 눈동자 포인트 처리 및 중앙 포인트 준비
        iris_result = _prepare_iris_centers(
            original_landmarks, transformed_landmarks,
            left_iris_center_coord, right_iris_center_coord,
            left_iris_center_orig, right_iris_center_orig,
            img_width, img_height,
            clamping_enabled=clamping_enabled, margin_ratio=margin_ratio
        )
        original_landmarks_no_iris, transformed_landmarks_no_iris, \
        original_points_array, transformed_points_array, iris_indices = iris_result        
        
        # Delaunay Triangulation 캐싱 (성능 최적화)
        # 랜드마크 포인트의 해시를 키로 사용
        tri = _create_delaunay_triangulation(original_points_array)

        # 뒤집힌 삼각형 검사 및 수정
        transformed_points_array = _check_and_fix_flipped_triangles(
            original_points_array, transformed_points_array, tri, original_landmarks_no_iris
        )

        # 성능 최적화: 역변환 맵 방식 사용 (각 픽셀에 대해 한 번만 샘플링)
        # 이 방식이 각 삼각형마다 전체 이미지를 변환하는 것보다 훨씬 빠름
        
        # 랜드마크 바운딩 박스 계산 (원본 이미지 크기 기준)
        # 성능 최적화: 캐시된 원본 바운딩 박스 사용 (이미지 로딩 시 한 번만 계산)
        # 바운딩 박스는 얼굴 전체를 포함해야 하므로 모든 랜드마크를 사용하여 계산
        # 경계 포인트는 이미지 경계 밖에 있어서 포함하면 전체 이미지가 되므로 제외
        # 패딩을 충분히 추가하여 얼굴 전체(턱, 이마 등)를 포함하도록 함
        if cached_original_bbox is not None:
            # 캐시된 바운딩 박스 사용 (이미 얼굴 전체를 포함하도록 계산된 값)
            bbox_orig = cached_original_bbox
        else:
            # 캐시가 없으면 모든 랜드마크를 사용하여 계산 (경계 포인트 제외)
            # 패딩을 50%로 늘려서 얼굴 전체(턱, 이마 등)를 포함하도록 함
            bbox_orig = _calculate_landmark_bounding_box(original_landmarks_no_iris, img_width, img_height, padding_ratio=0.5)
            # 참고: 이 값은 landmark_manager.set_original_bbox()로 캐시에 저장되어야 함
            # 하지만 이 함수는 반환값이 없으므로, 호출하는 쪽에서 캐시에 저장해야 함
        # 변형된 랜드마크는 매번 계산 필요 (변형될 수 있으므로)
        # 패딩을 50%로 늘려서 얼굴 전체(턱, 이마 등)를 포함하도록 함
        bbox_trans = _calculate_landmark_bounding_box(transformed_landmarks_no_iris, img_width, img_height, padding_ratio=0.5)
        
        # 두 바운딩 박스를 합쳐서 처리 영역 결정 (변형 시 확장 고려)
        # 원본 바운딩 박스 위치 저장 (업샘플링 시 사용)
        min_x_orig_bbox = None
        min_y_orig_bbox = None
        max_x_orig_bbox = None
        max_y_orig_bbox = None
        
        if bbox_orig and bbox_trans:
            min_x = min(bbox_orig[0], bbox_trans[0])
            min_y = min(bbox_orig[1], bbox_trans[1])
            max_x = max(bbox_orig[2], bbox_trans[2])
            max_y = max(bbox_orig[3], bbox_trans[3])
            
            # 원본 바운딩 박스 위치 저장
            min_x_orig_bbox = min_x
            min_y_orig_bbox = min_y
            max_x_orig_bbox = max_x
            max_y_orig_bbox = max_y
            
            # 바운딩 박스 크기 계산
            bbox_width = max_x - min_x
            bbox_height = max_y - min_y
            bbox_max_dimension = max(bbox_width, bbox_height)
            
            # 바운딩 박스 크기를 기준으로 다운샘플링 판단
            # 랜드마크 영역만 처리하므로 작게 설정해도 됨 (얼굴 영역은 보통 500-800px)
            # 패딩 포함해도 600-1000px 정도이므로 1000으로 설정해도 대부분 원본 해상도 유지
            max_dimension = 1000  # 랜드마크 영역만 처리하므로 작게 설정해도 충분
            scale_factor = 1.0
            working_img = img_array
            working_width = img_width
            working_height = img_height
            
            if bbox_max_dimension > max_dimension:
                # 바운딩 박스가 max_dimension보다 크면 다운샘플링
                scale_factor = max_dimension / bbox_max_dimension
                # 전체 이미지를 다운샘플링하되, 바운딩 박스 영역만 처리
                working_width = int(img_width * scale_factor)
                working_height = int(img_height * scale_factor)
                # GPU 가속 리사이즈 시도 (CUDA 지원 시)
                if _cv2_cuda_available:
                    try:
                        # GPU 메모리로 업로드
                        gpu_img = cv2.cuda_GpuMat()
                        gpu_img.upload(img_array)
                        # GPU에서 리사이즈 (INTER_LINEAR - 빠르고 품질 양호)
                        gpu_resized = cv2.cuda.resize(gpu_img, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
                        # CPU로 다운로드
                        working_img = gpu_resized.download()
                    except Exception:
                        # GPU 실패 시 CPU로 폴백
                        working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
                else:
                    working_img = cv2.resize(img_array, (working_width, working_height), interpolation=cv2.INTER_LINEAR)
                
                # 랜드마크 좌표도 스케일 조정
                original_points_array_scaled = original_points_array * scale_factor
                transformed_points_array_scaled = transformed_points_array * scale_factor
                
                # 스케일된 좌표로 Delaunay 재계산
                tri_scaled = Delaunay(original_points_array_scaled)
                tri = tri_scaled
                original_points_array = original_points_array_scaled
                transformed_points_array = transformed_points_array_scaled
                
                # 바운딩 박스도 스케일 조정
                min_x = int(min_x * scale_factor)
                min_y = int(min_y * scale_factor)
                max_x = int(max_x * scale_factor)
                max_y = int(max_y * scale_factor)
        else:
            # 바운딩 박스 계산 실패 시 전체 이미지 사용 (폴백)
            min_x, min_y = 0, 0
            max_x, max_y = img_width, img_height
            # 폴백 케이스에서도 원본 바운딩 박스 위치 저장 (전체 이미지)
            min_x_orig_bbox = 0
            min_y_orig_bbox = 0
            max_x_orig_bbox = img_width
            max_y_orig_bbox = img_height
            # 기존 로직 유지 (전체 이미지 크기 기준)
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
                
                original_points_array_scaled = original_points_array * scale_factor
                transformed_points_array_scaled = transformed_points_array * scale_factor
                
                tri_scaled = Delaunay(original_points_array_scaled)
                tri = tri_scaled
                original_points_array = original_points_array_scaled
                transformed_points_array = transformed_points_array_scaled
                
                max_x = working_width
                max_y = working_height
        
        # 정변환 맵 생성: 원본 이미지의 각 픽셀을 변형된 위치로 직접 매핑
        # 정변환의 장점: 역변환 행렬의 오차 누적이 없고, 변형된 포인트 인덱스를 직접 사용하여 원본 삼각형을 찾을 수 있음
        # 결과 이미지 초기화 (원본 이미지로 시작)
        result = working_img.copy().astype(np.float32)
        result_count = np.ones((working_height, working_width), dtype=np.float32)  # 원본은 이미 1로 설정
        # 변형된 픽셀이 매핑된 위치 추적 (blend_ratio = 1.0일 때 원본 제거용)
        transformed_mask = np.zeros((working_height, working_width), dtype=np.bool_)
        
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
        else:
            max_diff = 0.0
            changed_count = 0
        # 랜드마크가 변형되지 않았으면 원본 이미지 반환
        if max_diff < 0.1:
            return image
        
        # 바운딩 박스 영역만 처리
        bbox_width = max_x - min_x
        bbox_height = max_y - min_y
        bbox_total_pixels = bbox_width * bbox_height
        
        # 원본 이미지의 각 픽셀에 대해 해당하는 삼각형 찾기 및 정변환 계산
        # 성능 최적화: 벡터화된 연산 사용, 바운딩 박스 영역만 처리
        # 메모리 효율성을 위해 청크 단위로 처리 (큰 이미지의 경우)
        chunk_size = 100000  # 한 번에 처리할 픽셀 수
        
        # 바운딩 박스 내부 픽셀 좌표만 생성 (전역 좌표)
        y_coords_orig, x_coords_orig = np.mgrid[min_y:max_y, min_x:max_x]
        pixel_coords_orig_global = np.column_stack([x_coords_orig.ravel(), y_coords_orig.ravel()])
        
        if bbox_total_pixels > chunk_size:
            # 큰 바운딩 박스는 청크 단위로 처리하여 메모리 사용량 감소
            simplex_indices_orig = np.full(bbox_total_pixels, -1, dtype=np.int32)
            for chunk_start in range(0, bbox_total_pixels, chunk_size):
                chunk_end = min(chunk_start + chunk_size, bbox_total_pixels)
                chunk_coords = pixel_coords_orig_global[chunk_start:chunk_end]
                simplex_indices_orig[chunk_start:chunk_end] = tri.find_simplex(chunk_coords)
        else:
            # 작은 바운딩 박스는 한 번에 처리
            simplex_indices_orig = tri.find_simplex(pixel_coords_orig_global)
        
        # 눈동자 중심점만 드래그한 경우: 중앙 포인트와 눈 영역 랜드마크만 포함하는 삼각형만 변형
        if iris_center_only:
            # 중앙 포인트 인덱스 (470개 구조에서 468, 469번)
            iris_center_indices = {landmarks_count - 2, landmarks_count - 1}
            
            # 눈 영역 랜드마크 인덱스 가져오기 (인덱스 기반 필터링)
            try:
                from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
                # 눈 영역 랜드마크 (눈꺼풀 윤곽)
                eye_landmarks_raw = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
                
                # MediaPipe 인덱스(478개)를 468개 구조로 변환 필요 여부 확인
                # 현재 landmarks_count는 470개 (468개 + 중앙 포인트 2개)
                # 따라서 실제 랜드마크는 468개
                # MediaPipe는 478개이므로 10개(눈동자 윤곽)가 제거된 상태
                # 눈 랜드마크 인덱스가 468 미만이면 그대로 사용, 이상이면 조정 필요
                max_eye_idx = max(eye_landmarks_raw) if eye_landmarks_raw else 0
                if max_eye_idx >= landmarks_count - 2:  # 중앙 포인트 인덱스 제외
                    # 인덱스가 범위를 벗어남 - 매핑 필요
                    # 일단 사용 가능한 인덱스만 필터링
                    eye_landmarks = {idx for idx in eye_landmarks_raw if idx < landmarks_count - 2}
                else:
                    eye_landmarks = eye_landmarks_raw
                    
            except ImportError:
                # 폴백: 중앙 포인트만 사용
                eye_landmarks = set()
            
            # 경계 포인트
            boundary_indices = set(range(landmarks_count, landmarks_count + 4))
            
            # 먼저 중심점 좌표가 눈 영역 안에 있는지 확인
            left_iris_pt = original_points_array[landmarks_count - 2]
            right_iris_pt = original_points_array[landmarks_count - 1]
            
            # 눈 영역 랜드마크들의 좌표 범위 계산
            eye_coords = [original_points_array[idx] for idx in eye_landmarks]
            if eye_coords:
                eye_x_coords = [pt[0] for pt in eye_coords]
                eye_y_coords = [pt[1] for pt in eye_coords]
                eye_x_min, eye_x_max = min(eye_x_coords), max(eye_x_coords)
                eye_y_min, eye_y_max = min(eye_y_coords), max(eye_y_coords)
                
            
            # 1단계: 중심점을 포함하는 모든 삼각형의 꼭짓점 수집
            vertices_connected_to_iris = set()
            for simplex in tri.simplices:
                has_iris_center = any(idx in iris_center_indices for idx in simplex)
                if has_iris_center:
                    for idx in simplex:
                        if idx not in iris_center_indices and idx not in boundary_indices:
                            vertices_connected_to_iris.add(idx)
            
            # 2단계: 수집된 꼭짓점 중에서 눈 영역 인덱스만 필터링
            # MediaPipe 눈 영역 인덱스가 불완전하므로 ±7 확장 (눈동자 움직임 범위 확보)
            expanded_eye_landmarks = set(eye_landmarks)
            for idx in eye_landmarks:
                for offset in range(-7, 8):
                    expanded_idx = idx + offset
                    if 0 <= expanded_idx < landmarks_count - 2:
                        expanded_eye_landmarks.add(expanded_idx)
            
            # 중심점과 연결되었고, 확장된 눈 영역에 있는 꼭짓점만 허용
            filtered_vertices = vertices_connected_to_iris & expanded_eye_landmarks
            allowed_vertices = filtered_vertices | iris_center_indices | boundary_indices
            
            
            # 각 삼각형 검사: 중앙 포인트를 포함하고, 나머지 꼭짓점이 허용 영역에 있어야 함
            iris_triangles = set()
            sample_triangles = []  # 디버그용 샘플
            rejected_triangles = []  # 디버그용 거부된 샘플
            for simplex_idx, simplex in enumerate(tri.simplices):
                has_iris_center = any(idx in iris_center_indices for idx in simplex)
                if has_iris_center:
                    # 중앙 포인트 제외한 나머지 꼭짓점 확인
                    other_vertices = [idx for idx in simplex if idx not in iris_center_indices]
                    
                    # 나머지 꼭짓점이 모두 경계 포인트인지 확인
                    all_boundary = all(idx in boundary_indices for idx in other_vertices)
                    
                    # 경계 포인트만 있는 삼각형은 제외
                    if all_boundary:
                        if len(rejected_triangles) < 3:
                            rejected_triangles.append(('all_boundary', simplex_idx, simplex.tolist()))
                        continue
                    
                    # 나머지 꼭짓점이 허용된 영역에 있는지 확인
                    all_in_allowed_region = True
                    outside_vertices = []
                    for vert_idx in other_vertices:
                        if vert_idx not in allowed_vertices:
                            all_in_allowed_region = False
                            outside_vertices.append(int(vert_idx))
                    
                    if all_in_allowed_region:
                        iris_triangles.add(simplex_idx)
                        if len(sample_triangles) < 5:  # 처음 5개만 샘플링
                            sample_triangles.append((simplex_idx, simplex.tolist()))
                    else:
                        if len(rejected_triangles) < 3:
                            rejected_triangles.append(('outside_allowed_region', simplex_idx, simplex.tolist(), outside_vertices))
            
            
            # 중앙 포인트를 포함하지 않거나 눈 영역 밖의 삼각형은 변형하지 않음
            mask_iris_triangles = np.isin(simplex_indices_orig, list(iris_triangles))
            simplex_indices_orig[~mask_iris_triangles] = -1
        
        # 각 삼각형의 정변환 행렬 미리 계산 (캐싱)
        forward_transform_cache = {}
        
        # 성능 최적화: 바운딩 박스와 겹치는 삼각형만 처리
        # simplex_indices_orig에서 실제로 사용된 삼각형 인덱스만 추출
        valid_simplex_indices = np.unique(simplex_indices_orig[simplex_indices_orig >= 0])
        
        # 각 픽셀에 대해 정변환 적용
        # 주의: 바운딩 박스와 겹치는 삼각형만 순회합니다 (성능 최적화)
        # 원본 이미지의 픽셀 좌표가 속한 원본 삼각형을 찾고,
        # 그 삼각형의 포인트 인덱스를 사용하여 변형된 포인트를 가져옵니다
        total_pixels_processed = 0
        pixels_out_of_bounds = 0
        for simplex_idx in valid_simplex_indices:
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
            
            # 이 삼각형에 속한 원본 픽셀 좌표 (바운딩 박스 기준)
            triangle_pixels_orig = pixel_coords_orig_global[pixel_mask]
            
            # 정변환 적용: 원본 좌표 -> 변형된 좌표
            ones = np.ones((len(triangle_pixels_orig), 1), dtype=np.float32)
            triangle_pixels_orig_homogeneous = np.hstack([triangle_pixels_orig, ones])
            transformed_coords = (M_forward @ triangle_pixels_orig_homogeneous.T).T
            
            # 벡터화된 픽셀 처리 (성능 최적화)
            pixel_indices_bbox = np.where(pixel_mask)[0]
            if len(pixel_indices_bbox) == 0:
                continue
            
            # 바운딩 박스 내부 좌표를 전체 이미지 좌표로 변환
            # pixel_indices_bbox는 바운딩 박스 내부의 인덱스 (0부터 bbox_width*bbox_height-1)
            orig_y_coords_bbox = pixel_indices_bbox // bbox_width
            orig_x_coords_bbox = pixel_indices_bbox % bbox_width
            
            # 전체 이미지 좌표로 변환 (오프셋 추가)
            orig_y_coords = orig_y_coords_bbox + min_y
            orig_x_coords = orig_x_coords_bbox + min_x
            
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
                # 변형된 픽셀이 매핑된 위치 추적 (blend_ratio = 1.0일 때 원본 제거용)
                transformed_mask[y0_valid, x0_valid] = True
            
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
                # 변형된 픽셀이 매핑된 위치 추적
                transformed_mask[y1_valid, x0_valid] = True
            
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
                # 변형된 픽셀이 매핑된 위치 추적
                transformed_mask[y0_valid, x1_valid] = True
            
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
                # 변형된 픽셀이 매핑된 위치 추적
                transformed_mask[y1_valid, x1_valid] = True
            
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
            
            total_pixels_processed += len(pixel_indices_bbox)
        
        # 로그 제거 (성능 최적화)
        
        # 블렌딩 비율 범위 제한 (정규화 전에 적용)
        blend_ratio = max(0.0, min(1.0, blend_ratio))
        
        # 가중 평균으로 정규화 (여러 원본 픽셀이 같은 변형된 위치로 매핑된 경우)
        result_count_safe = np.maximum(result_count, 1e-6)  # 0으로 나누기 방지
        result_normalized = result / result_count_safe[:, :, np.newaxis]
        
        # blend_ratio = 1.0일 때 변형된 픽셀 영역에서 원본 제거 (완전 덮어쓰기)
        # 변형된 픽셀이 매핑된 위치에서는 원본을 제거하고 변형된 픽셀만 사용
        if blend_ratio == 1.0:
            # 변형된 픽셀이 매핑된 위치 추적 (result_count > 1.0이면 변형된 픽셀이 매핑된 위치)
            transformed_pixel_mask = (result_count > 1.0 + 1e-6)
            if np.any(transformed_pixel_mask):
                # 변형된 픽셀이 매핑된 위치에서 원본 제거하고 변형된 픽셀만 사용
                # result_normalized = (원본 * 1.0 + 변형된 픽셀 * w) / (1.0 + w)
                # 변형된 픽셀만 추출: transformed_only = (result_normalized * (1.0 + w) - 원본 * 1.0) / w
                mask_3d = transformed_pixel_mask[:, :, np.newaxis]
                working_img_float = working_img.astype(np.float32)
                result_count_float = result_count[:, :, np.newaxis]
                # 변형된 픽셀만 추출: (result_normalized * result_count - 원본 * 1.0) / (result_count - 1.0)
                result_count_minus_one = np.maximum(result_count_float - 1.0, 1e-6)  # 0으로 나누기 방지
                transformed_only = (result_normalized * result_count_float - working_img_float) / result_count_minus_one
                # 변형된 픽셀이 매핑된 위치에서는 변형된 픽셀만 사용, 그 외는 원본 유지
                result_normalized = np.where(mask_3d, transformed_only, working_img_float)
        
        result = result_normalized.astype(np.uint8)
        
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
        # 성능 최적화: 바운딩 박스 영역만 업샘플링, 나머지는 원본 이미지 사용
        if scale_factor < 1.0 and min_x_orig_bbox is not None:
            # 바운딩 박스 영역만 업샘플링 (전체 이미지 업샘플링 대신)
            # 원본 이미지로 시작
            result_full = img_array.copy().astype(np.float32)
            
            # 다운샘플링된 이미지에서 바운딩 박스 영역 추출
            # min_x, min_y, max_x, max_y는 다운샘플링된 이미지 기준이므로 그대로 사용
            bbox_result = result[min_y:max_y, min_x:max_x].copy()
            
            # bbox_result의 실제 크기 (다운샘플링된 크기)
            bbox_result_height, bbox_result_width = bbox_result.shape[:2]
            
            # 원본 이미지에서의 바운딩 박스 크기 계산
            # 이미지 경계 내로 제한
            min_x_orig = max(0, min_x_orig_bbox)
            min_y_orig = max(0, min_y_orig_bbox)
            max_x_orig = min(img_width, max_x_orig_bbox)
            max_y_orig = min(img_height, max_y_orig_bbox)
            bbox_width_orig = max_x_orig - min_x_orig
            bbox_height_orig = max_y_orig - min_y_orig
            
            if bbox_width_orig > 0 and bbox_height_orig > 0:
                # 바운딩 박스 영역만 업샘플링 (원본 크기로 복원)
                # bbox_result는 다운샘플링된 크기이므로 원본 크기로 업샘플링
                bbox_result_upscaled = cv2.resize(
                    bbox_result, 
                    (bbox_width_orig, bbox_height_orig), 
                    interpolation=cv2.INTER_LINEAR
                )
                # 원본 이미지에 업샘플링된 바운딩 박스 영역만 복사
                result_full[min_y_orig:max_y_orig, min_x_orig:max_x_orig] = bbox_result_upscaled.astype(np.float32)
            
            result = result_full
        
        # 블렌딩 비율 적용 (adjust_region_size와 동일한 의미로 통일)
        # blend_ratio = 0.0: 원본만 (변형 결과 적용 안 함)
        # blend_ratio = 1.0: 변형 결과만 (완전 덮어쓰기)
        # blend_ratio가 클수록 변형 결과(result)의 비율이 높아짐
        # (blend_ratio는 이미 위에서 범위 제한됨)
        if blend_ratio == 0.0:
            # 원본만 사용: 변형 결과를 적용하지 않음
            result = img_array.copy()
        elif blend_ratio == 1.0:
            # 변형 결과만 사용: 완전 덮어쓰기 (이미 정규화 단계에서 원본 제거됨)
            # result는 이미 변형된 픽셀만 포함하므로 그대로 사용
            if result.shape[:2] != img_array.shape[:2]:
                # 크기가 다르면 원본 이미지 크기로 업샘플링
                result = cv2.resize(result, (img_width, img_height), interpolation=cv2.INTER_LINEAR)
        else:
            # 원본 이미지와 변형 결과 블렌딩 (0.0 < blend_ratio < 1.0)
            if result.shape[:2] == img_array.shape[:2]:
                # float32로 변환하여 블렌딩 계산
                result_float = result.astype(np.float32)
                img_array_float = img_array.astype(np.float32)
                # 블렌딩: adjust_region_size와 동일한 방식
                # blend_ratio가 클수록 변형 결과(result)의 비율이 높아짐
                result = (img_array_float * (1.0 - blend_ratio) + result_float * blend_ratio).astype(np.uint8)
            else:
                # 크기가 다르면 원본 이미지로 업샘플링 후 블렌딩
                result_resized = cv2.resize(result, (img_width, img_height), interpolation=cv2.INTER_LINEAR)
                result_float = result_resized.astype(np.float32)
                img_array_float = img_array.astype(np.float32)
                result = (img_array_float * (1.0 - blend_ratio) + result_float * blend_ratio).astype(np.uint8)
        
        return Image.fromarray(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return image
        
