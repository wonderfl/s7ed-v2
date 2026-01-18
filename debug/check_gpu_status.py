"""
GPU 사용 상태 확인 스크립트
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("GPU 사용 상태 확인")
print("=" * 60)

# 1. OpenCV CUDA 지원 확인
print("\n[1] OpenCV CUDA 지원 확인")
try:
    import cv2
    print(f"  OpenCV 버전: {cv2.__version__}")
    try:
        cuda_device_count = cv2.cuda.getCudaEnabledDeviceCount()
        print(f"  CUDA 지원: {'예' if cuda_device_count > 0 else '아니오'}")
        if cuda_device_count > 0:
            print(f"  CUDA 디바이스 수: {cuda_device_count}")
            try:
                device_info = cv2.cuda.getDevice()
                print(f"  현재 CUDA 디바이스: {device_info}")
            except:
                pass
        else:
            print("  주의: OpenCV가 CUDA 지원 없이 빌드되었습니다.")
            print("  GPU 가속을 사용하려면 CUDA 지원 OpenCV 빌드가 필요합니다.")
    except AttributeError:
        print("  CUDA 지원: 아니오 (OpenCV가 CUDA 지원 없이 빌드됨)")
    except Exception as e:
        print(f"  CUDA 확인 중 오류: {e}")
except ImportError:
    print("  OpenCV가 설치되지 않았습니다.")

# 2. 프로젝트 상수 확인
print("\n[2] 프로젝트 GPU 설정 확인")
try:
    from utils.face_morphing.constants import _cv2_available, _cv2_cuda_available
    print(f"  OpenCV 사용 가능: {_cv2_available}")
    print(f"  CUDA 사용 가능: {_cv2_cuda_available}")
    
    if _cv2_cuda_available:
        print("  상태: GPU 가속이 활성화되어 있습니다.")
    else:
        print("  상태: GPU 가속이 비활성화되어 있습니다. (CPU로 폴백)")
except Exception as e:
    print(f"  상수 확인 중 오류: {e}")

# 3. 실제 GPU 사용 코드 확인
print("\n[3] GPU 사용 코드 확인")
try:
    from utils.face_morphing.polygon_morphing.core import morph_face_by_polygons
    import inspect
    source = inspect.getsource(morph_face_by_polygons)
    if '_cv2_cuda_available' in source and 'cv2.cuda' in source:
        print("  GPU 가속 코드가 포함되어 있습니다.")
        if 'cv2.cuda.resize' in source:
            print("  - 이미지 리사이즈에 GPU 가속 사용")
        if 'cv2.cuda_GpuMat' in source:
            print("  - GPU 메모리 사용 코드 포함")
    else:
        print("  GPU 가속 코드가 없습니다.")
except Exception as e:
    print(f"  코드 확인 중 오류: {e}")

# 4. MediaPipe GPU 확인 (선택적)
print("\n[4] MediaPipe GPU 확인")
try:
    import mediapipe as mp
    print(f"  MediaPipe 버전: {mp.__version__}")
    # MediaPipe는 기본적으로 CPU를 사용하며, GPU는 특별한 설정이 필요합니다
    print("  참고: MediaPipe는 기본적으로 CPU를 사용합니다.")
    print("  GPU 가속을 사용하려면 특별한 설정이 필요합니다.")
except ImportError:
    print("  MediaPipe가 설치되지 않았습니다.")

# 5. NumPy/CuPy 확인
print("\n[5] NumPy/CuPy 확인")
try:
    import numpy as np
    print(f"  NumPy 버전: {np.__version__}")
    print("  NumPy는 CPU를 사용합니다.")
    
    try:
        import cupy as cp
        print(f"  CuPy 버전: {cp.__version__}")
        print("  CuPy가 설치되어 있습니다. (현재 프로젝트에서는 사용하지 않음)")
    except ImportError:
        print("  CuPy가 설치되지 않았습니다. (GPU 가속 NumPy)")
except ImportError:
    print("  NumPy가 설치되지 않았습니다.")

print("\n" + "=" * 60)
print("요약")
print("=" * 60)
try:
    from utils.face_morphing.constants import _cv2_cuda_available
    if _cv2_cuda_available:
        print("GPU 가속: 활성화됨")
        print("- 이미지 리사이즈 작업이 GPU에서 수행됩니다.")
        print("- GPU 실패 시 자동으로 CPU로 폴백됩니다.")
    else:
        print("GPU 가속: 비활성화됨")
        print("- 모든 작업이 CPU에서 수행됩니다.")
        print("- GPU 가속을 사용하려면 CUDA 지원 OpenCV 빌드가 필요합니다.")
        print("  (일반 opencv-python은 CPU만 지원)")
except:
    print("GPU 상태 확인 실패")

print("\n" + "=" * 60)
