"""
성능 최적화 모듈
이미지 리사이즈 및 렌더링 성능 최적화
"""
import time
from typing import Tuple, Optional
from PIL import Image

class PerformanceOptimizer:
    """성능 최적화 클래스"""
    
    def __init__(self):
        self._resize_cache = {}
        self._cache_max_size = 20
        self._last_cleanup_time = time.time()
    
    def optimized_resize(self, image: Image.Image, size: Tuple[int, int], scale_factor: float = 1.0) -> Image.Image:
        """
        최적화된 이미지 리사이즈
        
        Args:
            image: 원본 PIL 이미지
            size: 목표 크기 (width, height)
            scale_factor: 확대/축소 비율
            
        Returns:
            리사이즈된 PIL 이미지
        """
        # 캐시 키 생성
        cache_key = f"{id(image)}_{size[0]}x{size[1]}_{scale_factor:.2f}"
        
        # 캐시 확인
        if cache_key in self._resize_cache:
            cached_image, cached_time = self._resize_cache[cache_key]
            if time.time() - cached_time < 300:  # 5분 유효
                return cached_image
        
        # 리사이즈 방법 선택
        if scale_factor > 1.0:
            # 확대: BILINEAR 사용 (더 빠름)
            resized = image.resize(size, Image.BILINEAR)
        elif scale_factor < 0.5:
            # 크게 축소: NEAREST 사용 (가장 빠름)
            resized = image.resize(size, Image.NEAREST)
        else:
            # 일반: LANCZOS 사용 (품질 우선)
            resized = image.resize(size, Image.LANCZOS)
        
        # 캐시에 저장
        self._resize_cache[cache_key] = (resized, time.time())
        
        # 캐시 정리 (주기적으로)
        current_time = time.time()
        if current_time - self._last_cleanup_time > 60:  # 1분마다 정리
            self._cleanup_cache()
            self._last_cleanup_time = current_time
        
        return resized
    
    def _cleanup_cache(self):
        """오래된 캐시 정리"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, (_, cached_time) in self._resize_cache.items():
            if current_time - cached_time > 300:  # 5분 이상된 것 삭제
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._resize_cache[key]
        
        # 캐시 크기 제한
        if len(self._resize_cache) > self._cache_max_size:
            # 가장 오래된 것부터 삭제
            sorted_items = sorted(
                self._resize_cache.items(),
                key=lambda x: x[1][1]
            )
            
            for key, _ in sorted_items[:-self._cache_max_size]:
                del self._resize_cache[key]
    
    def clear_cache(self):
        """캐시 비우기"""
        self._resize_cache.clear()

# 전역 인스턴스
_optimizer = PerformanceOptimizer()