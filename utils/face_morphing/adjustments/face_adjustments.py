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



