"""
성능 설정 관리
사용자가 성능 옵션을 조정할 수 있도록 함
"""

class PerformanceSettings:
    """성능 설정 클래스"""
    
    def __init__(self):
        # 확대/축소 설정
        self.max_scale = 4.0  # 최대 확대 비율 (8.0 -> 4.0으로 제한)
        self.min_scale = 0.3  # 최소 축소 비율
        self.zoom_step = 1.05  # 확대 스텝 (1.1 -> 1.05로 세밀하게)
        
        # 캐시 설정
        self.resize_cache_size = 15  # 리사이즈 캐시 크기 (10 -> 15로 증가)
        self.landmark_cache_size = 20  # 랜드마크 캐시 크기
        
        # 렌더링 설정
        self.debounce_ms = 50  # 디바운스 시간 (ms)
        self.landmark_update_delay = 200  # 랜드마크 업데이트 지연 (ms)
        self.async_resize_threshold = 1000  # 비동기 리사이즈 임계값 (px)
        
        # 품질 설정
        self.use_fast_resampling = True  # 빠른 리샘플링 사용
        self.lanczos_threshold = 0.5  # LANCZOS 사용 임계값
        
    def get_optimized_scale(self, current_scale, delta):
        """최적화된 스케일 계산"""
        new_scale = current_scale * delta
        
        # 과도한 확대 방지
        if new_scale > self.max_scale:
            new_scale = self.max_scale
        elif new_scale < self.min_scale:
            new_scale = self.min_scale
        
        # 미미한 변화 건너뛰기
        if abs(new_scale - current_scale) < 0.01:
            return current_scale
        
        return new_scale
    
    def should_use_async_resize(self, width, height):
        """비동기 리사이즈 사용 여부"""
        return width > self.async_resize_threshold or height > self.async_resize_threshold
    
    def get_resampling_method(self, scale_factor):
        """스케일 팩터에 따른 리샘플링 방법 선택"""
        if not self.use_fast_resampling:
            from PIL import Image
            return Image.LANCZOS
        
        if scale_factor > 2.0:
            from PIL import Image
            return Image.NEAREST  # 가장 빠름
        elif scale_factor > 1.0:
            from PIL import Image
            return Image.BILINEAR  # 균형
        elif scale_factor < self.lanczos_threshold:
            from PIL import Image
            return Image.LANCZOS  # 고품질
        else:
            from PIL import Image
            return Image.BICUBIC  # 균형


# 전역 설정 인스턴스
performance_settings = PerformanceSettings()
