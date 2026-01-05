"""
이미지 조정 기능 모듈
얼굴 추출 패널에서 사용하는 이미지 조정 기능들을 순수 함수로 구현
"""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def convert_to_rgb(img):
    """이미지를 RGB 모드로 변환"""
    if img.mode == 'RGB':
        return img
    elif img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (0, 0, 0))
        background.paste(img, mask=img.split()[3])
        return background
    else:
        return img.convert('RGB')


def apply_equalize(img, value):
    """평탄화 (Histogram Equalization) 적용"""
    if value <= 0.0:
        return img
    
    try:
        import cv2
        import numpy as np
        original_img = img.copy()
        img_array = np.array(img)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
        img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
        img_bgr = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
        img_array = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        equalized_img = Image.fromarray(img_array)
        
        if value < 1.0:
            return Image.blend(original_img, equalized_img, value)
        else:
            return equalized_img
    except ImportError:
        try:
            original_img = img.copy()
            equalized_img = ImageOps.equalize(img)
            if value < 1.0:
                return Image.blend(original_img, equalized_img, value)
            else:
                return equalized_img
        except Exception as e:
            print(f"[이미지조정] 평탄화 실패: {e}")
            return img
    except Exception as e:
        print(f"[이미지조정] 평탄화 실패: {e}")
        return img


def apply_brightness(img, value):
    """밝기 조정"""
    if value == 1.0:
        return img
    enhancer = ImageEnhance.Brightness(img)
    return enhancer.enhance(value)


def apply_contrast(img, value):
    """대비 조정"""
    if value == 1.0:
        return img
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(value)


def apply_noise_reduction(img, value):
    """노이즈 제거"""
    if value <= 0.0:
        return img
    
    try:
        import cv2
        import numpy as np
        sigma_color = value * 0.5
        sigma_space = value * 0.5
        img_array = np.array(img, dtype=np.uint8)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        filtered = cv2.bilateralFilter(img_bgr, d=9, sigmaColor=sigma_color, sigmaSpace=sigma_space)
        img_array = cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img_array)
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] Noise Reduction 조정 실패: {e}")
        return img


def apply_clarity(img, value):
    """명확도 조정"""
    if value == 0.0:
        return img
    
    try:
        import numpy as np
        amount = abs(value) / 50.0
        if value > 0:
            blurred = img.filter(ImageFilter.GaussianBlur(radius=1.0))
            img_array = np.array(img, dtype=np.float32)
            blur_array = np.array(blurred, dtype=np.float32)
            img_array = img_array + (img_array - blur_array) * amount
            img_array = np.clip(img_array, 0, 255)
            return Image.fromarray(img_array.astype(np.uint8))
        else:
            blur_radius = abs(value) / 50.0
            return img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] Clarity 조정 실패: {e}")
        return img


def apply_dehaze(img, value):
    """안개 제거"""
    if value == 0.0:
        return img
    
    try:
        amount = abs(value) / 100.0
        enhancer = ImageEnhance.Contrast(img)
        if value > 0:
            return enhancer.enhance(1.0 + amount * 0.5)
        else:
            return enhancer.enhance(1.0 - amount * 0.3)
    except Exception as e:
        print(f"[이미지조정] Dehaze 조정 실패: {e}")
        return img


def apply_saturation(img, value):
    """채도 조정"""
    if value == 1.0:
        return img
    enhancer = ImageEnhance.Color(img)
    return enhancer.enhance(value)


def apply_vibrance(img, value):
    """비브런스 조정"""
    if value == 1.0:
        return img
    
    try:
        import cv2
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        img_hsv = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        
        saturation_channel = img_hsv[:, :, 1]
        hue_channel = img_hsv[:, :, 0]
        skin_mask = ((hue_channel >= 0) & (hue_channel <= 30)) | ((hue_channel >= 150) & (hue_channel <= 180))
        weight = np.where(skin_mask, 0.5, 1.0)
        adjustment = (value - 1.0) * weight
        
        saturation_channel = saturation_channel + adjustment * 50
        saturation_channel = np.clip(saturation_channel, 0, 255)
        
        img_hsv[:, :, 1] = saturation_channel
        img_array = cv2.cvtColor(img_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        return Image.fromarray(img_array)
    except ImportError:
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(value)
    except Exception as e:
        print(f"[이미지조정] Vibrance 조정 실패: {e}")
        return img


def apply_hue(img, value):
    """색조 조정"""
    if value == 0.0:
        return img
    
    try:
        import cv2
        import numpy as np
        img_array = np.array(img, dtype=np.uint8)
        img_hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        img_hsv[:, :, 0] = (img_hsv[:, :, 0].astype(np.int16) + int(value)) % 180
        img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        return Image.fromarray(img_array)
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] 색조 조정 실패: {e}")
        return img


def apply_color_temp(img, value):
    """색온도 조정"""
    if value == 0.0:
        return img
    
    try:
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        temp_factor = value / 100.0 * 0.3
        
        if temp_factor > 0:
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] + temp_factor * 50, 0, 255)
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] + temp_factor * 30, 0, 255)
        else:
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] - temp_factor * 50, 0, 255)
        
        return Image.fromarray(img_array.astype(np.uint8))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] 색온도 조정 실패: {e}")
        return img


def apply_tint(img, value):
    """틴트 조정"""
    if value == 0.0:
        return img
    
    try:
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        tint_factor = value / 150.0 * 0.3
        
        if tint_factor > 0:
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] + tint_factor * 40, 0, 255)
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] - tint_factor * 40, 0, 255)
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] + tint_factor * 40, 0, 255)
        else:
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] + tint_factor * 40, 0, 255)
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] - tint_factor * 40, 0, 255)
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] + tint_factor * 40, 0, 255)
        
        return Image.fromarray(img_array.astype(np.uint8))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] 틴트 조정 실패: {e}")
        return img


def apply_gamma(img, value):
    """감마 보정"""
    if value == 1.0:
        return img
    
    try:
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        img_array = img_array / 255.0
        img_array = np.power(img_array, 1.0 / value)
        img_array = img_array * 255.0
        img_array = np.clip(img_array, 0, 255)
        return Image.fromarray(img_array.astype(np.uint8))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] 감마 보정 실패: {e}")
        return img


def apply_exposure(img, value):
    """노출 조정"""
    if value == 1.0:
        return img
    
    try:
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        exposure_factor = 0.25 * (4.0 ** value)
        img_array = img_array * exposure_factor
        img_array = np.clip(img_array, 0, 255)
        return Image.fromarray(img_array.astype(np.uint8))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] 노출 조정 실패: {e}")
        return img


def apply_sharpness(img, value):
    """선명도 조정"""
    if value == 1.0:
        return img
    enhancer = ImageEnhance.Sharpness(img)
    return enhancer.enhance(value)


def apply_vignette(img, value):
    """비네팅 조정"""
    if value == 0.0:
        return img
    
    try:
        import numpy as np
        img_array = np.array(img, dtype=np.float32)
        height, width = img_array.shape[:2]
        
        center_x = width / 2.0
        center_y = height / 2.0
        max_distance = np.sqrt(center_x ** 2 + center_y ** 2)
        
        y_coords, x_coords = np.ogrid[:height, :width]
        distances = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)
        normalized_distances = distances / max_distance
        
        vignette_strength = abs(value) / 100.0
        if value > 0:
            mask = (1.0 - normalized_distances) * vignette_strength
            img_array = img_array + mask[:, :, np.newaxis] * 50.0
        else:
            mask = normalized_distances * vignette_strength
            img_array = img_array - mask[:, :, np.newaxis] * 50.0
        
        img_array = np.clip(img_array, 0, 255)
        return Image.fromarray(img_array.astype(np.uint8))
    except ImportError:
        return img
    except Exception as e:
        print(f"[이미지조정] Vignette 조정 실패: {e}")
        return img


# 이미지 조정 파이프라인 순서 정의
ADJUSTMENT_PIPELINE = [
    ('equalize', apply_equalize),
    ('brightness', apply_brightness),
    ('contrast', apply_contrast),
    ('noise_reduction', apply_noise_reduction),
    ('clarity', apply_clarity),
    ('dehaze', apply_dehaze),
    ('saturation', apply_saturation),
    ('vibrance', apply_vibrance),
    ('hue', apply_hue),
    ('color_temp', apply_color_temp),
    ('tint', apply_tint),
    ('gamma', apply_gamma),
    ('exposure', apply_exposure),
    ('sharpness', apply_sharpness),
    ('vignette', apply_vignette),
]


def process_image_pipeline(img, adjustments, resize_before=None, resize_after=None):
    """
    이미지 조정 파이프라인 처리
    
    Args:
        img: PIL.Image 객체
        adjustments: 조정 값 딕셔너리 (예: {'brightness': 1.2, 'contrast': 1.1, ...})
        resize_before: Equalize 후 리사이즈 크기 (width, height) 튜플 또는 None
        resize_after: Sharpness 전 리사이즈 크기 (width, height) 튜플 또는 None
    
    Returns:
        PIL.Image: 조정된 이미지
    
    처리 순서:
        1. RGB 변환
        2. Equalize
        3. 리사이즈 (resize_before, 있으면)
        4. Brightness, Contrast, Noise Reduction, Clarity, Dehaze, Saturation, Vibrance, Hue, Color Temp, Tint, Gamma, Exposure
        5. 리사이즈 (resize_after, 있으면)
        6. Sharpness
        7. Vignette
    """
    # RGB 변환
    img = convert_to_rgb(img)
    
    # Equalize (항상 먼저)
    equalize_value = adjustments.get('equalize', 0.0)
    if equalize_value > 0.0:
        img = apply_equalize(img, equalize_value)
    
    # 리사이즈 (Equalize 후, 다른 조정 전)
    if resize_before:
        img = img.resize(resize_before, Image.LANCZOS)
    
    # 중간 조정들 (Brightness ~ Exposure)
    for key, func in ADJUSTMENT_PIPELINE:
        if key in ['equalize', 'sharpness', 'vignette']:
            continue  # 나중에 처리
        
        value = adjustments.get(key, None)
        if value is not None:
            # 기본값 체크
            if key in ['brightness', 'contrast', 'saturation', 'vibrance', 'exposure']:
                if value == 1.0:
                    continue
            elif key == 'noise_reduction':
                if value <= 0.0:
                    continue
            elif key in ['clarity', 'dehaze', 'hue', 'color_temp', 'tint', 'gamma']:
                if value == 0.0:
                    continue
            
            img = func(img, value)
    
    # 리사이즈 (Sharpness 전)
    if resize_after:
        img = img.resize(resize_after, Image.LANCZOS)
    
    # Sharpness (리사이즈 후)
    sharpness_value = adjustments.get('sharpness', 1.0)
    if sharpness_value != 1.0:
        img = apply_sharpness(img, sharpness_value)
    
    # Vignette (마지막)
    vignette_value = adjustments.get('vignette', 0.0)
    if vignette_value != 0.0:
        img = apply_vignette(img, vignette_value)
    
    return img

