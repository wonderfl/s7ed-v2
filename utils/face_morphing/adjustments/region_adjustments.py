"""
이미지 조정 함수 모듈
얼굴 특징(눈, 코, 입, 턱 등)을 조정하는 함수들
"""
import numpy as np
from PIL import Image

from ..constants import _cv2_available, _landmarks_available
from ..utils import _create_blend_mask
from ..region_extraction import _get_eye_region, _get_mouth_region, _get_nose_region, _get_region_center

# 외부 모듈 import
try:
    import cv2
except ImportError:
    cv2 = None

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks
except ImportError:
    detect_face_landmarks = None
    get_key_landmarks = None


def adjust_region_size(image, region_name, size_x=1.0, size_y=1.0, center_offset_x=0.0, center_offset_y=0.0, landmarks=None):
    """
    부위별 크기 조절 (중심점 오프셋 포함 기준)
    
    Args:
        image: PIL.Image 객체
        region_name: 부위 이름 ('face_oval', 'left_eye', 'right_eye', 'left_eyebrow', 'right_eyebrow',
                    'nose', 'upper_lips', 'lower_lips', 'left_iris', 'right_iris', 'contours', 'tesselation')
        size_x: 크기 비율 X (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        size_y: 크기 비율 Y (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        center_offset_x: 중심점 오프셋 X (픽셀, 기본값: 0.0)
        center_offset_y: 중심점 오프셋 Y (픽셀, 기본값: 0.0)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    # 크기 비율이 1.0에 가까우면 스킵 (0.01보다 작은 차이는 무시)
    if abs(size_x - 1.0) < 0.01 and abs(size_y - 1.0) < 0.01:
        return image
    
    # 디버그 출력
    print(f"[얼굴모핑] 부위 크기 조절 시작: {region_name}, size_x={size_x:.2f}, size_y={size_y:.2f}, center_offset=({center_offset_x:.1f}, {center_offset_y:.1f})")
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 부위 중심점 계산 (오프셋 포함)
        from .region_extraction import _get_region_center
        center = _get_region_center(region_name, landmarks, center_offset_x, center_offset_y)
        if center is None:
            return image
        
        center_x, center_y = center
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 중심점을 기준으로 영역 크기 추정 (부위별 기본 크기)
        region_size = min(img_width, img_height) * 0.1  # 기본 크기 (이미지 크기의 10%)
        
        # 부위별 크기 조정
        if region_name in ['left_eye', 'right_eye']:
            # 눈 영역은 기존 함수 활용
            key_landmarks = get_key_landmarks(landmarks)
            if key_landmarks is None:
                return image
            eye_name = 'left' if region_name == 'left_eye' else 'right'
            eye_region, _ = _get_eye_region(key_landmarks, img_width, img_height, eye_name, landmarks, 0.3, center_offset_x, center_offset_y)
            x1, y1, x2, y2 = eye_region
            region_size = max(x2 - x1, y2 - y1) / 2
        elif region_name == 'nose':
            # 코 영역은 기존 함수 활용
            key_landmarks = get_key_landmarks(landmarks)
            if key_landmarks is None:
                return image
            nose_region, _ = _get_nose_region(key_landmarks, img_width, img_height, landmarks, 0.3, center_offset_x, center_offset_y)
            x1, y1, x2, y2 = nose_region
            region_size = max(x2 - x1, y2 - y1) / 2
        else:
            # 다른 부위는 중심점 기준으로 영역 계산
            # 랜드마크 포인트들의 분산을 기반으로 크기 추정
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            indices = []
            if region_name == 'face_oval':
                FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
                for conn in FACE_OVAL:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'left_eyebrow':
                LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
                for conn in LEFT_EYEBROW:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'right_eyebrow':
                RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
                for conn in RIGHT_EYEBROW:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'lips':
                # Lips 전체 인덱스 (FACEMESH_LIPS 사용)
                LIPS = list(mp_face_mesh.FACEMESH_LIPS)
                for conn in LIPS:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'upper_lips':
                # 하위 호환성 유지
                UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
                indices = UPPER_LIP_INDICES
            elif region_name == 'lower_lips':
                # 하위 호환성 유지
                LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
                indices = LOWER_LIP_INDICES
            elif region_name == 'left_iris':
                try:
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    for conn in LEFT_IRIS:
                        indices.append(conn[0])
                        indices.append(conn[1])
                except AttributeError:
                    # MediaPipe 정의 사용
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        left_iris_indices, _ = get_iris_indices()
                        indices = left_iris_indices
                    except ImportError:
                        # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477])
                        indices = [474, 475, 476, 477]
            elif region_name == 'right_iris':
                try:
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    for conn in RIGHT_IRIS:
                        indices.append(conn[0])
                        indices.append(conn[1])
                except AttributeError:
                    # MediaPipe 정의 사용
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        _, right_iris_indices = get_iris_indices()
                        indices = right_iris_indices
                    except ImportError:
                        # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: RIGHT_IRIS=[469,470,471,472])
                        indices = [469, 470, 471, 472]
            elif region_name == 'contours':
                CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
                for conn in CONTOURS:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'tesselation':
                TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
                for conn in TESSELATION:
                    indices.append(conn[0])
                    indices.append(conn[1])
            
            # 유효한 인덱스만 필터링
            valid_indices = [i for i in set(indices) if i < len(landmarks)]
            if valid_indices:
                x_coords = [landmarks[i][0] for i in valid_indices]
                y_coords = [landmarks[i][1] for i in valid_indices]
                if x_coords and y_coords:
                    region_size = max(max(x_coords) - min(x_coords), max(y_coords) - min(y_coords)) / 2
        
        # 영역 추출 (중심점 기준)
        half_size = int(region_size)
        x1 = max(0, int(center_x - half_size))
        y1 = max(0, int(center_y - half_size))
        x2 = min(img_width, int(center_x + half_size))
        y2 = min(img_height, int(center_y + half_size))
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 부위 영역 추출
        region_img = img_array[y1:y2, x1:x2].copy()
        if region_img.size == 0:
            return image
        
        # 크기 조절
        new_width = int((x2 - x1) * size_x)
        new_height = int((y2 - y1) * size_y)
        
        if new_width < 1 or new_height < 1:
            return image
        
        # 영역 리사이즈
        region_resized = cv2.resize(region_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 새로운 위치 계산 (중심점 기준)
        new_x1 = max(0, int(center_x - new_width // 2))
        new_y1 = max(0, int(center_y - new_height // 2))
        new_x2 = min(img_width, new_x1 + new_width)
        new_y2 = min(img_height, new_y1 + new_height)
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 리사이즈된 영역을 실제 크기에 맞춤
        region_final = cv2.resize(region_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩)
        mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        
        # 원본 영역과 새 영역이 겹치는지 확인
        overlap = not (x2 <= new_x1 or new_x2 <= x1 or y2 <= new_y1 or new_y2 <= y1)
        
        if overlap:
            # 겹치는 경우: 원본 영역을 먼저 지우고 새 영역 배치
            # 원본 영역 주변의 픽셀들을 수집하여 평균값 계산
            border_pixels = []
            # 위쪽 경계
            if y1 > 0:
                border_pixels.extend(img_array[y1-1, x1:x2].tolist())
            # 아래쪽 경계
            if y2 < img_height:
                border_pixels.extend(img_array[y2, x1:x2].tolist())
            # 왼쪽 경계
            if x1 > 0:
                border_pixels.extend(img_array[y1:y2, x1-1].tolist())
            # 오른쪽 경계
            if x2 < img_width:
                border_pixels.extend(img_array[y1:y2, x2].tolist())
            
            # 주변 픽셀의 평균값 계산
            if border_pixels:
                border_array = np.array(border_pixels)
                if len(border_array.shape) == 2 and border_array.shape[1] == 3:
                    avg_color = np.mean(border_array, axis=0).astype(np.uint8)
                else:
                    # 단일 값인 경우
                    avg_color = np.array([np.mean(border_array)] * 3, dtype=np.uint8)
            else:
                # 주변 픽셀이 없으면 원본 이미지의 평균값 사용
                avg_color = np.mean(img_array, axis=(0, 1)).astype(np.uint8)
            
            # 원본 영역을 평균 색상으로 채움
            result[y1:y2, x1:x2] = avg_color
        
        # 새로운 위치에 블렌딩
        region_area = result[new_y1:new_y2, new_x1:new_x2]
        
        if region_area.shape[:2] == region_final.shape[:2]:
            for c in range(3):
                region_area[:, :, c] = (region_area[:, :, c] * (1 - mask) + 
                                       region_final[:, :, c] * mask).astype(np.uint8)
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 부위 크기 조절 실패 ({region_name}): {e}")
        import traceback
        traceback.print_exc()
        return image



def adjust_region_position(image, region_name, position_x=0.0, position_y=0.0, 
                          center_offset_x=0.0, center_offset_y=0.0, landmarks=None):
    """
    부위별 위치 이동 (중심점 오프셋 + 추가 이동)
    
    Args:
        image: PIL.Image 객체
        region_name: 부위 이름 ('face_oval', 'left_eye', 'right_eye', 'left_eyebrow', 'right_eyebrow',
                    'nose', 'upper_lips', 'lower_lips', 'left_iris', 'right_iris', 'contours', 'tesselation')
        position_x: 위치 이동 X (픽셀, 기본값: 0.0)
        position_y: 위치 이동 Y (픽셀, 기본값: 0.0)
        center_offset_x: 중심점 오프셋 X (픽셀, 기본값: 0.0)
        center_offset_y: 중심점 오프셋 Y (픽셀, 기본값: 0.0)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
    if abs(position_x) < 0.1 and abs(position_y) < 0.1:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        if landmarks is None or len(landmarks) < 468:
            return image
        
        # 부위 중심점 계산 (오프셋 포함)
        from .region_extraction import _get_region_center
        center = _get_region_center(region_name, landmarks, center_offset_x, center_offset_y)
        if center is None:
            return image
        
        center_x, center_y = center
        
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        result = img_array.copy()
        
        # 중심점을 기준으로 영역 크기 추정
        region_size = min(img_width, img_height) * 0.1
        
        # 부위별 크기 조정 (adjust_region_size와 동일한 로직)
        if region_name in ['left_eye', 'right_eye']:
            key_landmarks = get_key_landmarks(landmarks)
            if key_landmarks is None:
                return image
            eye_name = 'left' if region_name == 'left_eye' else 'right'
            eye_region, _ = _get_eye_region(key_landmarks, img_width, img_height, eye_name, landmarks, 0.3, center_offset_x, center_offset_y)
            x1, y1, x2, y2 = eye_region
            region_size = max(x2 - x1, y2 - y1) / 2
        elif region_name == 'nose':
            key_landmarks = get_key_landmarks(landmarks)
            if key_landmarks is None:
                return image
            nose_region, _ = _get_nose_region(key_landmarks, img_width, img_height, landmarks, 0.3, center_offset_x, center_offset_y)
            x1, y1, x2, y2 = nose_region
            region_size = max(x2 - x1, y2 - y1) / 2
        else:
            # 다른 부위는 중심점 기준으로 영역 계산 (adjust_region_size와 동일)
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            indices = []
            if region_name == 'face_oval':
                FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
                for conn in FACE_OVAL:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'left_eyebrow':
                LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
                for conn in LEFT_EYEBROW:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'right_eyebrow':
                RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
                for conn in RIGHT_EYEBROW:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'lips':
                # Lips 전체 인덱스 (FACEMESH_LIPS 사용)
                LIPS = list(mp_face_mesh.FACEMESH_LIPS)
                for conn in LIPS:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'upper_lips':
                # 하위 호환성 유지
                UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
                indices = UPPER_LIP_INDICES
            elif region_name == 'lower_lips':
                # 하위 호환성 유지
                LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
                indices = LOWER_LIP_INDICES
            elif region_name == 'left_iris':
                try:
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    for conn in LEFT_IRIS:
                        indices.append(conn[0])
                        indices.append(conn[1])
                except AttributeError:
                    # MediaPipe 정의 사용
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        left_iris_indices, _ = get_iris_indices()
                        indices = left_iris_indices
                    except ImportError:
                        # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477])
                        indices = [474, 475, 476, 477]
            elif region_name == 'right_iris':
                try:
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    for conn in RIGHT_IRIS:
                        indices.append(conn[0])
                        indices.append(conn[1])
                except AttributeError:
                    # MediaPipe 정의 사용
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        _, right_iris_indices = get_iris_indices()
                        indices = right_iris_indices
                    except ImportError:
                        # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: RIGHT_IRIS=[469,470,471,472])
                        indices = [469, 470, 471, 472]
            elif region_name == 'contours':
                CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
                for conn in CONTOURS:
                    indices.append(conn[0])
                    indices.append(conn[1])
            elif region_name == 'tesselation':
                TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
                for conn in TESSELATION:
                    indices.append(conn[0])
                    indices.append(conn[1])
            
            valid_indices = [i for i in set(indices) if i < len(landmarks)]
            if valid_indices:
                x_coords = [landmarks[i][0] for i in valid_indices]
                y_coords = [landmarks[i][1] for i in valid_indices]
                if x_coords and y_coords:
                    region_size = max(max(x_coords) - min(x_coords), max(y_coords) - min(y_coords)) / 2
        
        # 영역 추출 (중심점 기준)
        half_size = int(region_size)
        x1 = max(0, int(center_x - half_size))
        y1 = max(0, int(center_y - half_size))
        x2 = min(img_width, int(center_x + half_size))
        y2 = min(img_height, int(center_y + half_size))
        
        if x2 <= x1 or y2 <= y1:
            return image
        
        # 부위 영역 추출
        region_img = result[y1:y2, x1:x2].copy()
        if region_img.size == 0:
            return image
        
        # 새로운 위치 계산 (오프셋이 적용된 중심점 + 추가 이동)
        new_center_x = int(center_x + position_x)
        new_center_y = int(center_y + position_y)
        
        # 경계 체크
        new_center_x = max(0, min(img_width - 1, new_center_x))
        new_center_y = max(0, min(img_height - 1, new_center_y))
        
        # 새로운 영역 위치 계산
        new_x1 = max(0, new_center_x - half_size)
        new_y1 = max(0, new_center_y - half_size)
        new_x2 = min(img_width, new_center_x + half_size)
        new_y2 = min(img_height, new_center_y + half_size)
        
        if new_x2 <= new_x1 or new_y2 <= new_y1:
            return image
        
        # 실제 사용할 크기
        actual_width = new_x2 - new_x1
        actual_height = new_y2 - new_y1
        
        if actual_width < 1 or actual_height < 1:
            return image
        
        # 원본 영역을 지움 (검은색으로 채움)
        result[y1:y2, x1:x2] = 0
        
        # 리사이즈된 영역을 실제 크기에 맞춤
        region_resized = cv2.resize(region_img, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 마스크 생성 (부드러운 블렌딩)
        mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
        
        # 새로운 위치에 블렌딩
        region_area = result[new_y1:new_y2, new_x1:new_x2]
        
        if region_area.shape[:2] == region_resized.shape[:2]:
            for c in range(3):
                region_area[:, :, c] = (region_area[:, :, c] * (1 - mask) + 
                                       region_resized[:, :, c] * mask).astype(np.uint8)
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 부위 위치 이동 실패 ({region_name}): {e}")
        import traceback
        traceback.print_exc()
        return image




