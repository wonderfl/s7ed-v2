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


def adjust_eye_size(image, eye_size_ratio=1.0, landmarks=None, left_eye_size_ratio=None, right_eye_size_ratio=None, 
                    eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                    left_eye_region_padding=None, right_eye_region_padding=None,
                    left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                    right_eye_region_offset_x=None, right_eye_region_offset_y=None, blend_ratio=1.0):
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
        blend_ratio: 블렌딩 비율 (0.0 = 완전 오버라이트, 1.0 = 완전 블렌딩, 기본값: 1.0)
    
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
            
            # 블렌딩 비율 범위 제한
            blend_ratio = max(0.0, min(1.0, blend_ratio))
            
            # 마스크 생성 (부드러운 블렌딩을 위해, 개선된 버전: 시그모이드 함수 기반)
            mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
            
            # 블렌딩 비율 적용
            mask_adjusted = mask * blend_ratio
            
            # 새 영역을 블렌딩 비율에 따라 덮어쓰기
            roi = result[new_y1:new_y2, new_x1:new_x2].copy()
            mask_3channel = np.stack([mask_adjusted] * 3, axis=-1)  # RGB 채널로 확장
            
            # 시그모이드 함수 기반 부드러운 블렌딩
            blended = (roi * (1 - mask_3channel) + eye_final * mask_3channel).astype(np.uint8)
            result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
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
        import traceback
        traceback.print_exc()
        return image



