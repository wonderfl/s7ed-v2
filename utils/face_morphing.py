"""
얼굴 특징 보정 모듈
랜드마크 포인트를 기반으로 얼굴의 특징을 변형합니다.
"""
import numpy as np
from PIL import Image, ImageDraw

try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, is_available as landmarks_available
    _landmarks_available = landmarks_available()
except ImportError:
    _landmarks_available = False


def _get_eye_region(key_landmarks, img_width, img_height, eye='left', landmarks=None, padding_ratio=0.3, offset_x=0.0, offset_y=0.0):
    """
    눈 영역을 계산합니다 (랜드마크 포인트를 사용하여 정확하게 계산)
    
    Args:
        key_landmarks: 주요 랜드마크 딕셔너리
        img_width: 이미지 너비
        img_height: 이미지 높이
        eye: 'left' 또는 'right'
        landmarks: 랜드마크 포인트 리스트
        padding_ratio: 눈 영역 패딩 비율 (0.0 ~ 1.0, 기본값: 0.3)
        offset_x: 눈 영역 수평 오프셋 (픽셀, 기본값: 0.0)
        offset_y: 눈 영역 수직 오프셋 (픽셀, 기본값: 0.0)
    
    Returns:
        (x1, y1, x2, y2), eye_center: 눈 영역 좌표와 중심점
    """
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
            
            # 여유 공간 추가 (눈 주변 영역 포함, 패딩 비율 적용)
            padding = int(((max_x - min_x) + (max_y - min_y)) / 2 * padding_ratio)
            
            # 눈 중심점에 오프셋 적용
            offset_eye_center_x = eye_center[0] + offset_x
            offset_eye_center_y = eye_center[1] + offset_y
            
            # 오프셋이 적용된 중심점 기준으로 영역 계산
            center_x = (min_x + max_x) / 2 + offset_x
            center_y = (min_y + max_y) / 2 + offset_y
            
            x1 = max(0, int(center_x - (max_x - min_x) / 2 - padding))
            y1 = max(0, int(center_y - (max_y - min_y) / 2 - padding))
            x2 = min(img_width, int(center_x + (max_x - min_x) / 2 + padding))
            y2 = min(img_height, int(center_y + (max_y - min_y) / 2 + padding))
            
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
            
            # 마스크 생성 (부드러운 블렌딩을 위해)
            # 마스크 크기를 눈 크기에 비례하여 조정
            mask_size = max(15, min(actual_width, actual_height) // 4)
            # 홀수로 만들기 (가우시안 블러를 위해)
            if mask_size % 2 == 0:
                mask_size += 1
            
            # 타원형 마스크 생성 (눈 모양에 더 자연스러움)
            center_x = actual_width // 2
            center_y = actual_height // 2
            # 타원의 반지름 (경계에서 약간 안쪽으로)
            radius_x = max(1, actual_width // 2 - mask_size // 3)
            radius_y = max(1, actual_height // 2 - mask_size // 3)
            
            # 타원형 마스크 생성
            y_grid, x_grid = np.ogrid[:actual_height, :actual_width]
            ellipse_mask = ((x_grid - center_x) / radius_x)**2 + ((y_grid - center_y) / radius_y)**2 <= 1.0
            mask = (ellipse_mask.astype(np.uint8) * 255)
            
            # 가우시안 블러로 마스크 부드럽게 (동적 크기 사용)
            mask = cv2.GaussianBlur(mask, (mask_size, mask_size), 0)
            
            # 원본 이미지에 블렌딩
            roi = result[new_y1:new_y2, new_x1:new_x2].copy()
            mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
            
            # 더 부드러운 블렌딩 (선형 보간)
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
        
        nose_center = key_landmarks['nose']
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        
        # 코 크기 추정 (두 눈 사이 거리의 약 1/3)
        eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
        nose_radius = int(eye_distance * 0.2)
        
        # 코 영역 계산
        x1 = max(0, nose_center[0] - nose_radius)
        y1 = max(0, nose_center[1] - nose_radius)
        x2 = min(img_width, nose_center[0] + nose_radius)
        y2 = min(img_height, nose_center[1] + nose_radius)
        
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
        
        # 마스크 생성 (부드러운 블렌딩을 위해)
        mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (15, 15), 0)
        
        # 원본 이미지에 블렌딩
        result = img_array.copy()
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
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


def apply_all_adjustments(image, eye_size=1.0, nose_size=1.0, jaw_adjustment=0.0, 
                          face_width=1.0, face_height=1.0, landmarks=None,
                          left_eye_size=None, right_eye_size=None,
                          eye_spacing=False, left_eye_position_x=0.0, right_eye_position_x=0.0,
                          left_eye_position_y=0.0, right_eye_position_y=0.0,
                          eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                          left_eye_region_padding=None, right_eye_region_padding=None,
                          left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                          right_eye_region_offset_x=None, right_eye_region_offset_y=None):
    """
    모든 얼굴 특징 보정을 한 번에 적용합니다.
    
    Args:
        image: PIL.Image 객체
        eye_size: 눈 크기 비율 (개별 조정 미사용 시)
        nose_size: 코 크기 비율
        jaw_adjustment: 턱선 조정 값
        face_width: 얼굴 너비 비율
        face_height: 얼굴 높이 비율
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
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
        result = adjust_jaw(result, jaw_adjustment, landmarks)
        result = adjust_face_size(result, face_width, face_height, landmarks)
        
        return result
        
    except Exception as e:
        print(f"[얼굴모핑] 얼굴 특징 보정 실패: {e}")
        import traceback
        traceback.print_exc()
        return image
