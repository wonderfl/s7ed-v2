"""
확대/축소 성능 패치
canvas.py 수정 없이 성능 향상
"""
import time
from functools import wraps

def patch_zoom_methods():
    """확대/축소 메서드에 성능 패치 적용"""
    
    def debounce_zoom_decorator(func):
        """확대/축소 디바운싱 데코레이터"""
        last_call_time = [0]
        debounce_ms = 50  # 50ms 디바운스
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            current_time = time.time() * 1000
            
            if current_time - last_call_time[0] < debounce_ms:
                return  # 너무 빠른 호출 건너뛰기
            
            last_call_time[0] = current_time
            
            # 원본 함수 호출
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                print(f"확대/축소 오류: {e}")
                return
        
        return wrapper
    
    def optimize_preview_calls_decorator(func):
        """미리보기 호출 최적화 데코레이터"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 확대/축소 중에는 랜드마크 업데이트 지연
            self._is_zooming = True
            
            try:
                # 원본 함수 호출
                result = func(self, *args, **kwargs)
                
                # 랜드마크 업데이트 지연 (100ms -> 200ms)
                def delayed_landmark_update():
                    self._is_zooming = False
                    if hasattr(self, 'show_landmark_points') and (self.show_landmark_points.get() or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())):
                        if hasattr(self, 'clear_landmarks_display'):
                            self.clear_landmarks_display()
                        
                        # 연결선 및 폴리곤 제거
                        for canvas_name in ['original', 'edited']:
                            canvas = getattr(self, f'canvas_{canvas_name}', None)
                            items = getattr(self, 'landmark_polygon_items', {}).get(canvas_name, [])
                            for item_id in list(items):
                                try:
                                    if canvas:
                                        canvas.delete(item_id)
                                except Exception:
                                    pass
                            items.clear()
                        
                        if hasattr(self, 'update_face_features_display'):
                            self.update_face_features_display()
                
                # 지연 시간 증가 (100ms -> 200ms)
                if hasattr(self, 'after'):
                    self.after(200, delayed_landmark_update)
                
                return result
                
            except Exception as e:
                print(f"미리보기 업데이트 오류: {e}")
                self._is_zooming = False
                return
        
        return wrapper
    
    return {
        'debounce_zoom': debounce_zoom_decorator,
        'optimize_preview': optimize_preview_calls_decorator
    }


def apply_performance_patches():
    """성능 패치 적용"""
    patches = patch_zoom_methods()
    
    # 적용할 함수 목록
    functions_to_patch = [
        'zoom_in_original',
        'zoom_out_original', 
        'zoom_in_edited',
        'zoom_out_edited'
    ]
    
    print("성능 패치 적용 완료")
    return patches


# 전역 패치 인스턴스
performance_patches = apply_performance_patches()
