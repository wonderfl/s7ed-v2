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


def adjust_nose_size(image, nose_size_ratio=1.0, landmarks=None, blend_ratio=1.0):
    """
    코 크기를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        nose_size_ratio: 코 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        blend_ratio: 블렌딩 비율 (0.0 = 완전 오버라이트, 1.0 = 완전 블렌딩, 기본값: 1.0)
    
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
        
        # 블렌딩 비율 범위 제한
        blend_ratio = max(0.0, min(1.0, blend_ratio))
        
        # 마스크 생성 (부드러운 블렌딩을 위해, 개선된 버전: 시그모이드 함수 기반)
        mask = _create_blend_mask(actual_width, actual_height, mask_type='ellipse')
        
        # 블렌딩 비율 적용
        mask_adjusted = mask * blend_ratio
        
        # 원본 이미지 복사
        result = img_array.copy()
        
        # 새 영역을 블렌딩 비율에 따라 덮어쓰기
        roi = result[new_y1:new_y2, new_x1:new_x2]
        mask_3channel = np.stack([mask_adjusted] * 3, axis=-1)  # RGB 채널로 확장
        
        # 시그모이드 함수 기반 부드러운 블렌딩
        blended = (roi * (1 - mask_3channel) + nose_final * mask_3channel).astype(np.uint8)
        result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 코 크기 조정 실패: {e}")
        return image



