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


def _get_eye_region(key_landmarks, img_width, img_height, eye='left'):
    """눈 영역을 계산합니다"""
    if eye == 'left':
        eye_center = key_landmarks['left_eye']
    else:
        eye_center = key_landmarks['right_eye']
    
    # 눈 크기 추정 (두 눈 사이 거리의 약 1/4)
    left_eye = key_landmarks['left_eye']
    right_eye = key_landmarks['right_eye']
    eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
    eye_radius = int(eye_distance * 0.25)
    
    # 눈 영역 계산
    x1 = max(0, eye_center[0] - eye_radius)
    y1 = max(0, eye_center[1] - eye_radius)
    x2 = min(img_width, eye_center[0] + eye_radius)
    y2 = min(img_height, eye_center[1] + eye_radius)
    
    return (x1, y1, x2, y2), eye_center


def adjust_eye_size(image, eye_size_ratio=1.0, landmarks=None):
    """
    눈 크기를 조정합니다.
    
    Args:
        image: PIL.Image 객체
        eye_size_ratio: 눈 크기 비율 (1.0 = 원본, 2.0 = 2배, 0.5 = 절반)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available or not _cv2_available:
        return image
    
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
        
        # 왼쪽 눈과 오른쪽 눈 각각 처리
        for eye_name in ['left', 'right']:
            eye_region, eye_center = _get_eye_region(key_landmarks, img_width, img_height, eye_name)
            x1, y1, x2, y2 = eye_region
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # 눈 영역 추출
            eye_img = result[y1:y2, x1:x2]
            if eye_img.size == 0:
                continue
            
            # 눈 크기 조정
            new_width = int((x2 - x1) * eye_size_ratio)
            new_height = int((y2 - y1) * eye_size_ratio)
            
            if new_width < 1 or new_height < 1:
                continue
            
            # 눈 영역 리사이즈
            eye_resized = cv2.resize(eye_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # 새로운 위치 계산 (중심점 기준)
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
            eye_final = cv2.resize(eye_resized, (actual_width, actual_height), interpolation=cv2.INTER_LANCZOS4)
            
            # 마스크 생성 (부드러운 블렌딩을 위해)
            mask = np.ones((actual_height, actual_width), dtype=np.uint8) * 255
            
            # 가우시안 블러로 마스크 부드럽게
            mask = cv2.GaussianBlur(mask, (15, 15), 0)
            
            # 원본 이미지에 블렌딩
            roi = result[new_y1:new_y2, new_x1:new_x2]
            mask_3channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB) / 255.0
            blended = (roi * (1 - mask_3channel) + eye_final * mask_3channel).astype(np.uint8)
            result[new_y1:new_y2, new_x1:new_x2] = blended
        
        return Image.fromarray(result)
        
    except Exception as e:
        print(f"[얼굴모핑] 눈 크기 조정 실패: {e}")
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
                          face_width=1.0, face_height=1.0, landmarks=None):
    """
    모든 얼굴 특징 보정을 한 번에 적용합니다.
    
    Args:
        image: PIL.Image 객체
        eye_size: 눈 크기 비율
        nose_size: 코 크기 비율
        jaw_adjustment: 턱선 조정 값
        face_width: 얼굴 너비 비율
        face_height: 얼굴 높이 비율
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
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
        result = image.copy()
        result = adjust_eye_size(result, eye_size, landmarks)
        result = adjust_nose_size(result, nose_size, landmarks)
        result = adjust_jaw(result, jaw_adjustment, landmarks)
        result = adjust_face_size(result, face_width, face_height, landmarks)
        
        return result
        
    except Exception as e:
        print(f"[얼굴모핑] 얼굴 특징 보정 실패: {e}")
        return image
