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

from .constants import _cv2_available, _cv2_cuda_available, _scipy_available, _landmarks_available, _delaunay_cache, _delaunay_cache_max_size

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


