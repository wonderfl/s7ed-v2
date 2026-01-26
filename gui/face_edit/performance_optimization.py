"""
얼굴 편집 성능 최적화 모듈
이미지 확대/축소 시 버벅임 방지
"""
import time
from PIL import Image, ImageTk
from functools import lru_cache
import threading


class PerformanceOptimizer:
    """성능 최적화 유틸리티"""
    
    def __init__(self, max_cache_size=20):
        self.max_cache_size = max_cache_size
        self._resize_cache = {}
        self._last_zoom_time = 0
        self._zoom_debounce_ms = 50  # 50ms 디바운스
        self._pending_zoom = False
        
    def optimized_resize(self, image, size, scale_factor=1.0):
        """최적화된 이미지 리사이즈"""
        if image is None:
            return None
            
        width, height = size
        
        # 캐시 키 생성
        cache_key = (id(image), width, height, round(scale_factor, 2))
        
        # 캐시 확인
        if cache_key in self._resize_cache:
            return self._resize_cache[cache_key]
        
        # 원본 크기와 비교
        original_width, original_height = image.size
        
        # 리사이즈 알고리즘 선택 (성능 최적화)
        if scale_factor > 1.0:  # 확대
            # 2배 이상 확대时는 속도优先
            if scale_factor >= 2.0:
                resample = Image.NEAREST  # 가장 빠름
            elif scale_factor >= 1.5:
                resample = Image.BILINEAR  # 균형
            else:
                resample = Image.BICUBIC  # 품질
        else:  # 축소
            if scale_factor < 0.5:
                resample = Image.LANCZOS  # 고품질
            else:
                resample = Image.BICUBIC  # 균형
        
        # 리사이즈 수행
        try:
            resized = image.resize((width, height), resample)
            
            # 캐시 관리
            if len(self._resize_cache) >= self.max_cache_size:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(self._resize_cache))
                del self._resize_cache[oldest_key]
            
            self._resize_cache[cache_key] = resized
            return resized
            
        except Exception as e:
            print(f"이미지 리사이즈 실패: {e}")
            return image.resize((width, height), Image.BILINEAR)
    
    def debounce_zoom(self, callback):
        """확대/축소 디바운싱"""
        current_time = time.time() * 1000  # ms로 변환
        
        if current_time - self._last_zoom_time < self._zoom_debounce_ms:
            self._pending_zoom = True
            return
        
        self._last_zoom_time = current_time
        self._pending_zoom = False
        
        # 콜백 실행
        if callback:
            callback()
    
    def clear_cache(self):
        """캐시 초기화"""
        self._resize_cache.clear()
    
    def get_cache_stats(self):
        """캐시 통계"""
        return {
            'cache_size': len(self._resize_cache),
            'max_size': self.max_cache_size,
            'hit_rate': getattr(self, '_cache_hits', 0) / max(1, getattr(self, '_cache_requests', 1))
        }


class AsyncImageProcessor:
    """비동기 이미지 처리"""
    
    def __init__(self):
        self.processing_queue = []
        self.processing = False
    
    def async_resize(self, image, size, callback, scale_factor=1.0):
        """비동기 이미지 리사이즈"""
        if self.processing:
            return
        
        def process():
            try:
                self.processing = True
                optimizer = PerformanceOptimizer()
                resized = optimizer.optimized_resize(image, size, scale_factor)
                
                # 메인 스레드에서 콜백 실행
                if callback:
                    callback(resized)
                    
            except Exception as e:
                print(f"비동기 이미지 처리 실패: {e}")
            finally:
                self.processing = False
        
        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=process, daemon=True)
        thread.start()


class ZoomLimiter:
    """확대/축소 제한"""
    
    def __init__(self, max_scale=4.0, min_scale=0.3):
        self.max_scale = max_scale
        self.min_scale = min_scale
    
    def clamp_scale(self, current_scale, delta):
        """스케일 제한"""
        new_scale = current_scale * delta
        return max(self.min_scale, min(self.max_scale, new_scale))
    
    def should_skip_zoom(self, current_scale, target_scale):
        """불필요한 확대/축소 건너뛰기"""
        # 변화가 1% 미만이면 건너뛰기
        if abs(target_scale - current_scale) < 0.01:
            return True
        return False


# 전역 인스턴스
performance_optimizer = PerformanceOptimizer()
async_processor = AsyncImageProcessor()
zoom_limiter = ZoomLimiter()
