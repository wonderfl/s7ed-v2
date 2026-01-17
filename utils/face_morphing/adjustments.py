"""
이미지 조정 함수 모듈
얼굴 특징(눈, 코, 입, 턱 등)을 조정하는 함수들
"""
import numpy as np
from PIL import Image

from .constants import _cv2_available, _landmarks_available
from .utils import _create_blend_mask
from .region_extraction import _get_eye_region, _get_mouth_region, _get_nose_region

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


