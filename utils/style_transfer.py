"""
스타일 전송 모듈
다른 이미지의 색상과 텍스처를 현재 이미지에 적용합니다.
"""
import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False


def transfer_color_histogram(source_image, target_image, strength=1.0):
    """
    색상 히스토그램 매칭을 사용하여 소스 이미지의 색상을 타겟 이미지에 전송합니다.
    
    Args:
        source_image: PIL.Image 객체 (스타일 소스)
        target_image: PIL.Image 객체 (적용할 이미지)
        strength: 적용 강도 (0.0 ~ 1.0, 기본값: 1.0)
    
    Returns:
        PIL.Image: 색상이 전송된 이미지
    """
    if not _cv2_available:
        return target_image
    
    if strength <= 0.0:
        return target_image
    
    try:
        # RGB 모드로 변환
        if source_image.mode != 'RGB':
            source_image = source_image.convert('RGB')
        if target_image.mode != 'RGB':
            target_image = target_image.convert('RGB')
        
        # PIL Image를 numpy 배열로 변환
        source_array = np.array(source_image)
        target_array = np.array(target_image)
        
        # BGR로 변환 (OpenCV는 BGR 사용)
        source_bgr = cv2.cvtColor(source_array, cv2.COLOR_RGB2BGR)
        target_bgr = cv2.cvtColor(target_array, cv2.COLOR_RGB2BGR)
        
        # 각 채널별 히스토그램 매칭
        result_channels = []
        for i in range(3):  # B, G, R 채널
            source_channel = source_bgr[:, :, i]
            target_channel = target_bgr[:, :, i]
            
            # 히스토그램 매칭
            matched_channel = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(target_channel)
            
            # 소스 이미지의 히스토그램 계산
            hist_source = cv2.calcHist([source_channel], [0], None, [256], [0, 256])
            hist_target = cv2.calcHist([target_channel], [0], None, [256], [0, 256])
            
            # 누적 분포 함수 계산
            cdf_source = hist_source.cumsum()
            cdf_target = hist_target.cumsum()
            
            # 정규화
            cdf_source = (cdf_source - cdf_source.min()) * 255 / (cdf_source.max() - cdf_source.min())
            cdf_target = (cdf_target - cdf_target.min()) * 255 / (cdf_target.max() - cdf_target.min())
            
            # 매핑 테이블 생성
            mapping = np.zeros(256, dtype=np.uint8)
            for j in range(256):
                idx = np.argmin(np.abs(cdf_source - cdf_target[j]))
                mapping[j] = idx
            
            # 히스토그램 매칭 적용
            matched = cv2.LUT(target_channel, mapping)
            
            # 강도에 따라 블렌딩
            if strength < 1.0:
                matched = (target_channel * (1 - strength) + matched * strength).astype(np.uint8)
            
            result_channels.append(matched)
        
        # 채널 합치기
        result_bgr = cv2.merge(result_channels)
        
        # RGB로 변환
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        
        return Image.fromarray(result_rgb)
        
    except Exception as e:
        print(f"[스타일전송] 색상 히스토그램 매칭 실패: {e}")
        return target_image


def transfer_texture(source_image, target_image, strength=1.0):
    """
    텍스처를 전송합니다 (간단한 필터링 기반).
    
    Args:
        source_image: PIL.Image 객체 (스타일 소스)
        target_image: PIL.Image 객체 (적용할 이미지)
        strength: 적용 강도 (0.0 ~ 1.0, 기본값: 1.0)
    
    Returns:
        PIL.Image: 텍스처가 전송된 이미지
    """
    if strength <= 0.0:
        return target_image
    
    try:
        # RGB 모드로 변환
        if target_image.mode != 'RGB':
            target_image = target_image.convert('RGB')
        
        # 간단한 텍스처 전송: 소스 이미지의 텍스처 특성을 추출하여 적용
        # 방법: 소스 이미지의 고주파 성분(엣지, 텍스처)을 타겟에 적용
        
        if not _cv2_available:
            # OpenCV가 없으면 PIL 필터 사용
            # 소스 이미지의 텍스처를 추출하기 위해 엣지 감지
            if source_image.mode != 'RGB':
                source_image = source_image.convert('RGB')
            
            # 간단한 텍스처 효과: 언샤프 마스킹
            target_sharp = target_image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            
            # 강도에 따라 블렌딩
            if strength < 1.0:
                from PIL import ImageEnhance
                result = Image.blend(target_image, target_sharp, strength)
            else:
                result = target_sharp
            
            return result
        
        # OpenCV 사용 (더 정교한 텍스처 전송)
        source_array = np.array(source_image.convert('RGB'))
        target_array = np.array(target_image)
        
        # BGR로 변환
        source_bgr = cv2.cvtColor(source_array, cv2.COLOR_RGB2BGR)
        target_bgr = cv2.cvtColor(target_array, cv2.COLOR_RGB2BGR)
        
        # 소스 이미지의 텍스처 추출 (고주파 성분)
        source_gray = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2GRAY)
        source_texture = cv2.Laplacian(source_gray, cv2.CV_64F)
        source_texture = np.abs(source_texture)
        source_texture = (source_texture / source_texture.max() * 255).astype(np.uint8)
        
        # 타겟 이미지에 텍스처 적용
        target_gray = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2GRAY)
        
        # 텍스처 강도 조정
        texture_strength = source_texture.astype(np.float32) / 255.0 * strength
        
        # 타겟 이미지에 텍스처 블렌딩
        result_gray = (target_gray.astype(np.float32) * (1 - texture_strength) + 
                      source_texture.astype(np.float32) * texture_strength).astype(np.uint8)
        
        # 컬러 이미지로 복원
        result_bgr = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2BGR)
        
        # 원본 색상 정보 일부 유지
        if strength < 1.0:
            result_bgr = (target_bgr.astype(np.float32) * (1 - strength) + 
                         result_bgr.astype(np.float32) * strength).astype(np.uint8)
        
        # RGB로 변환
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        
        return Image.fromarray(result_rgb)
        
    except Exception as e:
        print(f"[스타일전송] 텍스처 전송 실패: {e}")
        return target_image


def transfer_style(source_image, target_image, color_strength=1.0, texture_strength=1.0):
    """
    스타일을 전송합니다 (색상 + 텍스처).
    
    Args:
        source_image: PIL.Image 객체 (스타일 소스)
        target_image: PIL.Image 객체 (적용할 이미지)
        color_strength: 색상 전송 강도 (0.0 ~ 1.0, 기본값: 1.0)
        texture_strength: 텍스처 전송 강도 (0.0 ~ 1.0, 기본값: 1.0)
    
    Returns:
        PIL.Image: 스타일이 전송된 이미지
    """
    try:
        result = target_image.copy()
        
        # 색상 전송
        if color_strength > 0.0:
            result = transfer_color_histogram(source_image, result, color_strength)
        
        # 텍스처 전송
        if texture_strength > 0.0:
            result = transfer_texture(source_image, result, texture_strength)
        
        return result
        
    except Exception as e:
        print(f"[스타일전송] 스타일 전송 실패: {e}")
        return target_image
