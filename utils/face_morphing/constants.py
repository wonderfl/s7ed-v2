"""
상수 및 전역 변수 모듈
"""
import os

# OpenCV 선택적 import
try:
    import cv2
    _cv2_available = True
    # OpenCV CUDA 지원 확인
    try:
        _cv2_cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
    except AttributeError:
        # OpenCV가 CUDA 지원 없이 빌드된 경우
        _cv2_cuda_available = False
except ImportError:
    _cv2_available = False
    _cv2_cuda_available = False

# scipy 선택적 import
try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False

# face_landmarks 선택적 import
try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, is_available as landmarks_available
    _landmarks_available = landmarks_available()
except ImportError:
    _landmarks_available = False

# Delaunay Triangulation 캐시 (성능 최적화)
_delaunay_cache = {}
_delaunay_cache_max_size = 5  # 최대 캐시 크기
