"""
얼굴 변환 모듈
얼굴의 나이를 변환합니다 (어리게/늙게).
"""
import numpy as np
from PIL import Image, ImageFilter

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


def make_younger(image, age_reduction=20, landmarks=None):
    """
    얼굴을 어리게 만듭니다.
    
    Args:
        image: PIL.Image 객체
        age_reduction: 나이 감소량 (0 ~ 50 세, 기본값: 20)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 어리게 변환된 이미지
    """
    if age_reduction <= 0:
        return image
    
    try:
        # RGB 모드로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        
        # 나이 감소 비율 계산 (0 ~ 50을 0.0 ~ 1.0으로)
        age_ratio = min(1.0, age_reduction / 50.0)
        
        # 1. 얼굴 비율 조정 (눈 크게, 얼굴 작게)
        if _landmarks_available:
            if landmarks is None:
                landmarks, detected = detect_face_landmarks(img_rgb)
                if detected:
                    key_landmarks = get_key_landmarks(landmarks)
                    if key_landmarks:
                        # 얼굴 특징 보정 모듈 사용
                        import utils.face_morphing as face_morphing
                        
                        # 눈 크기 증가 (1.0 ~ 1.3)
                        eye_ratio = 1.0 + age_ratio * 0.3
                        img_rgb = face_morphing.adjust_eye_size(img_rgb, eye_size_ratio=eye_ratio, landmarks=landmarks)
                        
                        # 얼굴 크기 감소 (1.0 ~ 0.9)
                        face_ratio = 1.0 - age_ratio * 0.1
                        img_rgb = face_morphing.adjust_face_size(img_rgb, width_ratio=face_ratio, height_ratio=face_ratio, landmarks=landmarks)
        
        # 2. 피부 매끄럽게 (블러 적용)
        if _cv2_available:
            img_array = np.array(img_rgb)
            
            # 얼굴 영역만 블러 적용 (전체 이미지에 블러를 적용하면 안 됨)
            # 간단한 방법: 약간의 가우시안 블러
            blur_radius = int(age_ratio * 3)  # 0 ~ 3 픽셀
            if blur_radius > 0:
                blurred = cv2.GaussianBlur(img_array, (blur_radius * 2 + 1, blur_radius * 2 + 1), 0)
                # 원본과 블러를 블렌딩
                blend_ratio = age_ratio * 0.5  # 최대 50% 블렌딩
                img_array = (img_array.astype(np.float32) * (1 - blend_ratio) + 
                            blurred.astype(np.float32) * blend_ratio).astype(np.uint8)
                img_rgb = Image.fromarray(img_array)
        else:
            # PIL 필터 사용
            blur_radius = age_ratio * 0.5
            if blur_radius > 0:
                blurred = img_rgb.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                blend_ratio = age_ratio * 0.3
                img_rgb = Image.blend(img_rgb, blurred, blend_ratio)
        
        # 3. 밝기 약간 증가 (어린 피부는 더 밝음)
        from PIL import ImageEnhance
        brightness_factor = 1.0 + age_ratio * 0.1  # 최대 10% 밝게
        enhancer = ImageEnhance.Brightness(img_rgb)
        img_rgb = enhancer.enhance(brightness_factor)
        
        return img_rgb
        
    except Exception as e:
        print(f"[얼굴변환] 어리게 변환 실패: {e}")
        return image


def make_older(image, age_increase=20, landmarks=None):
    """
    얼굴을 늙게 만듭니다.
    
    Args:
        image: PIL.Image 객체
        age_increase: 나이 증가량 (0 ~ 50 세, 기본값: 20)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 늙게 변환된 이미지
    """
    if age_increase <= 0:
        return image
    
    try:
        # RGB 모드로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        
        # 나이 증가 비율 계산 (0 ~ 50을 0.0 ~ 1.0으로)
        age_ratio = min(1.0, age_increase / 50.0)
        
        # 1. 얼굴 비율 조정 (눈 작게, 얼굴 크게)
        if _landmarks_available:
            if landmarks is None:
                landmarks, detected = detect_face_landmarks(img_rgb)
                if detected:
                    key_landmarks = get_key_landmarks(landmarks)
                    if key_landmarks:
                        # 얼굴 특징 보정 모듈 사용
                        import utils.face_morphing as face_morphing
                        
                        # 눈 크기 감소 (1.0 ~ 0.85)
                        eye_ratio = 1.0 - age_ratio * 0.15
                        img_rgb = face_morphing.adjust_eye_size(img_rgb, eye_size_ratio=eye_ratio, landmarks=landmarks)
                        
                        # 얼굴 크기 증가 (1.0 ~ 1.1)
                        face_ratio = 1.0 + age_ratio * 0.1
                        img_rgb = face_morphing.adjust_face_size(img_rgb, width_ratio=face_ratio, height_ratio=face_ratio, landmarks=landmarks)
        
        # 2. 주름 추가 (노이즈 패턴)
        if _cv2_available:
            img_array = np.array(img_rgb)
            
            # 얼굴 영역에 주름 패턴 추가
            # 간단한 방법: 노이즈 추가 및 엣지 강화
            noise_strength = int(age_ratio * 10)  # 0 ~ 10
            if noise_strength > 0:
                # 노이즈 생성
                noise = np.random.randint(-noise_strength, noise_strength + 1, img_array.shape, dtype=np.int16)
                img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            # 엣지 강화 (주름 효과)
            edge_strength = age_ratio * 0.3
            if edge_strength > 0:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
                # 엣지를 약간 어둡게 블렌딩
                img_array = (img_array.astype(np.float32) * (1 - edge_strength) + 
                            (img_array.astype(np.float32) - edges_rgb.astype(np.float32) * 0.3) * edge_strength).astype(np.uint8)
            
            img_rgb = Image.fromarray(img_array)
        
        # 3. 피부 질감 변경 (텍스처 추가)
        # 언샤프 마스킹으로 질감 강화
        from PIL import ImageFilter
        texture_strength = age_ratio * 0.2
        if texture_strength > 0:
            textured = img_rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            img_rgb = Image.blend(img_rgb, textured, texture_strength)
        
        # 4. 색상 약간 어둡게 (늙은 피부는 더 어둡고 황색)
        from PIL import ImageEnhance
        brightness_factor = 1.0 - age_ratio * 0.1  # 최대 10% 어둡게
        enhancer = ImageEnhance.Brightness(img_rgb)
        img_rgb = enhancer.enhance(brightness_factor)
        
        # 색온도 조정 (더 따뜻하게/황색)
        saturation_factor = 1.0 + age_ratio * 0.1  # 최대 10% 채도 증가
        enhancer = ImageEnhance.Color(img_rgb)
        img_rgb = enhancer.enhance(saturation_factor)
        
        return img_rgb
        
    except Exception as e:
        print(f"[얼굴변환] 늙게 변환 실패: {e}")
        return image


def transform_age(image, age_adjustment=0, landmarks=None):
    """
    얼굴의 나이를 변환합니다.
    
    Args:
        image: PIL.Image 객체
        age_adjustment: 나이 조정 값 (-50 ~ +50 세, 음수=어리게, 양수=늙게)
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 나이가 변환된 이미지
    """
    if abs(age_adjustment) < 1:
        return image
    
    try:
        if age_adjustment < 0:
            # 어리게
            return make_younger(image, age_reduction=abs(age_adjustment), landmarks=landmarks)
        else:
            # 늙게
            return make_older(image, age_increase=age_adjustment, landmarks=landmarks)
            
    except Exception as e:
        print(f"[얼굴변환] 나이 변환 실패: {e}")
        return image
