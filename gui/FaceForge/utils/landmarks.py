"""
얼굴 랜드마크 감지 및 정렬 모듈
MediaPipe를 사용하여 얼굴의 주요 특징점을 감지하고 얼굴을 정렬합니다.
"""
import math
import numpy as np
from PIL import Image

# 로거 (지연 로딩)
_logger = None

def _get_logger():
    """로거 가져오기 (지연 로딩)"""
    global _logger
    if _logger is None:
        from utils.logger import get_logger
        _logger = get_logger('얼굴랜드마크')
    return _logger

try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

from .debugs import DEBUG_POLYGON_WARPING
from utils.logger import debug, info, warning, error, log

# MediaPipe 선택적 import
try:
    # MediaPipe 경고 메시지 억제 (import 전에 설정)
    import os
    
    # 환경 변수 설정 (MediaPipe가 로드되기 전에 설정해야 함)
    # main.py에서 이미 설정되었을 수 있지만, 여기서도 확실히 설정
    if 'GLOG_minloglevel' not in os.environ:
        os.environ['GLOG_minloglevel'] = '3'  # FATAL만 표시
    if 'TF_CPP_MIN_LOG_LEVEL' not in os.environ:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # TensorFlow 로그 완전 억제
    
    # absl.logging 억제
    try:
        import absl.logging
        absl.logging.set_verbosity(absl.logging.ERROR)
        import logging
        logging.getLogger('absl').setLevel(logging.ERROR)
        logging.getLogger('tensorflow').setLevel(logging.ERROR)
    except:
        pass
    
    # warnings 필터 설정
    import warnings
    warnings.filterwarnings('ignore')
    
    # MediaPipe import
    import mediapipe as mp
    
    _mediapipe_available = True
except ImportError:
    _mediapipe_available = False
    # 로거는 나중에 import (순환 참조 방지)
    try:
        from utils.logger import get_logger
        logger = get_logger('얼굴랜드마크')
        logger.warning("MediaPipe가 설치되지 않았습니다. 얼굴 랜드마크 기능을 사용하려면 'pip install mediapipe'를 실행하세요.")
    except:
        print("[얼굴랜드마크] MediaPipe가 설치되지 않았습니다. 얼굴 랜드마크 기능을 사용하려면 'pip install mediapipe'를 실행하세요.")


def is_available():
    """MediaPipe 사용 가능 여부 확인"""
    return _mediapipe_available


def detect_face_landmarks(image, params=None):
    """
    이미지에서 얼굴 랜드마크를 감지합니다.
    
    Args:
        image: PIL.Image 객체 (RGB 모드)
    
    Returns:
        landmarks: 랜드마크 포인트 리스트 [(x, y), ...] 또는 None (얼굴을 찾지 못한 경우)
        face_detected: 얼굴 감지 여부 (bool)
    
    Note:
        MediaPipe가 없으면 None을 반환합니다.
    """
    if not _mediapipe_available:
        return False, None
    if not image:
        return False, None

    try:
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        img_height, img_width = img_array.shape[:2]
        
        # MediaPipe Face Mesh 초기화
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,            
            refine_landmarks=False, # 468, True: 478
            min_detection_confidence=0.5
        )
        
        # RGB로 변환 (MediaPipe는 RGB를 기대)
        results = face_mesh.process(img_array)
        
        if results.multi_face_landmarks:
            # 첫 번째 얼굴의 랜드마크 가져오기
            face_landmarks = results.multi_face_landmarks[0]
            
            # 랜드마크 포인트를 (x, y) 좌표로 변환
            landmarks = []
            if params:
                offset_x = params.get("offset_x", 0.0)
                offset_y = params.get("offset_y", 0.0)
                scale_x = params.get("scale_x", 1.0)
                scale_y = params.get("scale_y", 1.0)
                pivot_x = params.get("pivot_x", 0.0)
                pivot_y = params.get("pivot_y", 0.0)                
                rotation_deg = params.get("rotation_deg", 0.0)

                image_center_x = img_width / 2
                image_center_y = img_height / 2

                marks_pivot_x = image_center_x
                marks_pivot_y = image_center_y

                marks = face_landmarks.landmark
                count = len(marks)
                if count:
                    sum_x = 0.0
                    sum_y = 0.0
                    for pos in marks:
                        sum_x += pos.x
                        sum_y += pos.y
                    avg_x = sum_x / count
                    avg_y = sum_y / count

                    marks_pivot_x = avg_x * img_width
                    marks_pivot_y = avg_y * img_height

                adjusted = []
                rad = math.radians(rotation_deg)
                cos_a, sin_a = math.cos(rad), math.sin(rad)

                for pos in face_landmarks.landmark:
                    x = pos.x * img_width
                    y = pos.y * img_height

                    # 스케일
                    sx = x * scale_x
                    sy = y * scale_y

                    # 회전 (pivot 기준)
                    dx = sx - (marks_pivot_x +pivot_x)
                    dy = sy - (marks_pivot_y +pivot_y)

                    rx = dx * cos_a - dy * sin_a
                    ry = dx * sin_a + dy * cos_a

                    ix = int(rx +marks_pivot_x +pivot_x +offset_x)
                    iy = int(ry +marks_pivot_y +pivot_y +offset_y)

                    # 오프셋
                    adjusted.append((ix, iy))

                print("adjusted", f"{len(adjusted)} / {len(face_landmarks.landmark)}")
                landmarks = adjusted                

            else:
                for pos in face_landmarks.landmark:
                    x = int(pos.x * img_width)
                    y = int(pos.y * img_height)
                    landmarks.append((x, y))
            
            face_mesh.close()

            if DEBUG_POLYGON_WARPING:
                info("detect_face_landmarks", 
                    f"image[ {image.size}, {id(image)} ], "
                    f"landmarks[ {len(landmarks)} / {len(face_landmarks.landmark)} ], \n"
                    f"params[ {params} ]"
                )

            return True, landmarks

        else:
            face_mesh.close()
            return False, None
            
    except Exception as e:
        _get_logger().error(f"랜드마크 감지 실패: {e}", exc_info=True)
        return False, None


# MediaPipe Face Mesh의 주요 랜드마크 인덱스
# 참고: https://github.com/google/mediapipe/blob/master/mediapipe/python/solutions/face_mesh.py
LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
NOSE_TIP_INDEX = 4
MOUTH_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318]


def get_key_landmarks(landmarks):
    """
    주요 랜드마크 포인트를 추출합니다.
    
    Args:
        landmarks: 랜드마크 포인트 리스트 [(x, y), ...]
    
    Returns:
        dict: 주요 랜드마크 포인트 딕셔너리
            - left_eye: 왼쪽 눈 중심
            - right_eye: 오른쪽 눈 중심
            - nose: 코 끝
            - mouth: 입 중심
            - face_center: 얼굴 중심
    """
    if landmarks is None or len(landmarks) < 468:
        return None
    
    # 눈 중심 계산
    left_eye_points = [landmarks[i] for i in LEFT_EYE_INDICES if i < len(landmarks)]
    right_eye_points = [landmarks[i] for i in RIGHT_EYE_INDICES if i < len(landmarks)]
    
    if left_eye_points and right_eye_points:
        left_eye_center = (
            sum(p[0] for p in left_eye_points) // len(left_eye_points),
            sum(p[1] for p in left_eye_points) // len(left_eye_points)
        )
        right_eye_center = (
            sum(p[0] for p in right_eye_points) // len(right_eye_points),
            sum(p[1] for p in right_eye_points) // len(right_eye_points)
        )
    else:
        return None
    
    # 코 끝
    nose_tip = landmarks[NOSE_TIP_INDEX] if NOSE_TIP_INDEX < len(landmarks) else None
    
    # 입 중심 계산
    mouth_points = [landmarks[i] for i in MOUTH_INDICES if i < len(landmarks)]
    if mouth_points:
        mouth_center = (
            sum(p[0] for p in mouth_points) // len(mouth_points),
            sum(p[1] for p in mouth_points) // len(mouth_points)
        )
    else:
        mouth_center = None
    
    # 얼굴 중심 (두 눈의 중점과 입의 중점)
    if nose_tip and mouth_center:
        face_center = (
            (left_eye_center[0] + right_eye_center[0] + nose_tip[0] + mouth_center[0]) // 4,
            (left_eye_center[1] + right_eye_center[1] + nose_tip[1] + mouth_center[1]) // 4
        )
    else:
        face_center = (
            (left_eye_center[0] + right_eye_center[0]) // 2,
            (left_eye_center[1] + right_eye_center[1]) // 2
        )
    
    return {
        'left_eye': left_eye_center,
        'right_eye': right_eye_center,
        'nose': nose_tip,
        'mouth': mouth_center,
        'face_center': face_center
    }


def draw_landmarks(image, landmarks, key_landmarks=None, show_all_points=False):
    """
    이미지에 랜드마크를 그립니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 [(x, y), ...] (468개)
        key_landmarks: 주요 랜드마크 딕셔너리 (get_key_landmarks 결과)
        show_all_points: True면 모든 468개 포인트 표시, False면 주요 포인트만 표시
    
    Returns:
        PIL.Image: 랜드마크가 그려진 이미지
    """
    if landmarks is None or len(landmarks) < 468:
        return image
    
    try:
        # PIL Image를 numpy 배열로 변환
        if image.mode != 'RGB':
            img_array = np.array(image.convert('RGB'))
        else:
            img_array = np.array(image)
        
        # OpenCV 사용 (선택적)
        try:
            import cv2
            _cv2_available = True
        except ImportError:
            _cv2_available = False
        
        if _cv2_available:
            # OpenCV로 그리기
            img_copy = img_array.copy()
            
            # MediaPipe 공식 상수 사용
            if _mediapipe_available:
                mp_face_mesh = mp.solutions.face_mesh
                FACE_OVAL = mp_face_mesh.FACEMESH_FACE_OVAL
                LEFT_EYEBROW = mp_face_mesh.FACEMESH_LEFT_EYEBROW
                RIGHT_EYEBROW = mp_face_mesh.FACEMESH_RIGHT_EYEBROW
                LEFT_EYE = mp_face_mesh.FACEMESH_LEFT_EYE
                RIGHT_EYE = mp_face_mesh.FACEMESH_RIGHT_EYE
                NOSE = mp_face_mesh.FACEMESH_NOSE
                LIPS = mp_face_mesh.FACEMESH_LIPS
            else:
                # MediaPipe가 없으면 빈 리스트 (그리지 않음)
                FACE_OVAL = []
                LEFT_EYEBROW = []
                RIGHT_EYEBROW = []
                LEFT_EYE = []
                RIGHT_EYE = []
                NOSE = []
                LIPS = []
            
            if show_all_points:
                # 모든 포인트를 작은 점으로 표시
                for point in landmarks:
                    x, y = point
                    cv2.circle(img_copy, (x, y), 1, (255, 255, 255), -1)
            
            # 중심점은 표시하지 않음 (윤곽선만 표시)
            
            # MediaPipe 공식 상수를 사용하여 윤곽선 그리기
            # 각 상수는 [(시작점, 끝점), ...] 형태의 튜플 리스트
            
            # 1. 얼굴 윤곽선 (하늘색 선)
            for connection in FACE_OVAL:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (0, 255, 255), 2)  # 하늘색 (BGR), 두께 2
            
            # 2. 왼쪽 눈썹 (보라색 선)
            for connection in LEFT_EYEBROW:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (255, 0, 255), 2)  # 보라색, 두께 2
            
            # 3. 오른쪽 눈썹 (분홍색 선)
            for connection in RIGHT_EYEBROW:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (255, 192, 203), 2)  # 분홍색, 두께 2
            
            # 4. 왼쪽 눈 윤곽선 (빨간색 선)
            for connection in LEFT_EYE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (255, 0, 0), 2)  # 빨간색 (BGR), 두께 2
            
            # 5. 오른쪽 눈 윤곽선 (빨간색 선)
            for connection in RIGHT_EYE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (255, 0, 0), 2)  # 빨간색 (BGR), 두께 2
            
            # 6. 코 윤곽선 (파란색 선)
            for connection in NOSE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (0, 0, 255), 2)  # 파란색 (BGR), 두께 2
            
            # 7. 입술 윤곽선 (초록색 선)
            for connection in LIPS:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    cv2.line(img_copy, pt1, pt2, (0, 255, 0), 2)  # 초록색, 두께 2
            
            # numpy 배열을 PIL Image로 변환
            return Image.fromarray(img_copy)
        else:
            # OpenCV가 없으면 PIL로 직접 그리기
            from PIL import ImageDraw
            img_copy = image.copy()
            draw = ImageDraw.Draw(img_copy)
            
            # MediaPipe 공식 상수 사용
            if _mediapipe_available:
                mp_face_mesh = mp.solutions.face_mesh
                FACE_OVAL = mp_face_mesh.FACEMESH_FACE_OVAL
                LEFT_EYEBROW = mp_face_mesh.FACEMESH_LEFT_EYEBROW
                RIGHT_EYEBROW = mp_face_mesh.FACEMESH_RIGHT_EYEBROW
                LEFT_EYE = mp_face_mesh.FACEMESH_LEFT_EYE
                RIGHT_EYE = mp_face_mesh.FACEMESH_RIGHT_EYE
                NOSE = mp_face_mesh.FACEMESH_NOSE
                LIPS = mp_face_mesh.FACEMESH_LIPS
            else:
                # MediaPipe가 없으면 빈 리스트 (그리지 않음)
                FACE_OVAL = []
                LEFT_EYEBROW = []
                RIGHT_EYEBROW = []
                LEFT_EYE = []
                RIGHT_EYE = []
                NOSE = []
                LIPS = []
            
            # 중심점은 표시하지 않음 (윤곽선만 표시)
            
            # MediaPipe 공식 상수를 사용하여 윤곽선 그리기
            # 1. 얼굴 윤곽선 (하늘색 선)
            for connection in FACE_OVAL:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(255, 255, 0), width=2)  # RGB 형식
            
            # 2. 왼쪽 눈썹 (보라색 선)
            for connection in LEFT_EYEBROW:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(255, 0, 255), width=2)
            
            # 3. 오른쪽 눈썹 (분홍색 선)
            for connection in RIGHT_EYEBROW:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(203, 192, 255), width=2)  # RGB 형식
            
            # 4. 왼쪽 눈 윤곽선 (빨간색 선)
            for connection in LEFT_EYE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(0, 0, 255), width=2)  # RGB 형식
            
            # 5. 오른쪽 눈 윤곽선 (빨간색 선)
            for connection in RIGHT_EYE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(0, 0, 255), width=2)  # RGB 형식
            
            # 6. 코 윤곽선 (파란색 선)
            for connection in NOSE:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(255, 0, 0), width=2)  # RGB 형식
            
            # 7. 입술 윤곽선 (초록색 선)
            for connection in LIPS:
                idx1, idx2 = connection
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    draw.line([pt1, pt2], fill=(0, 255, 0), width=2)
            
            return img_copy
            
    except Exception as e:
        _get_logger().error(f"랜드마크 그리기 실패: {e}", exc_info=True)
        return image


def extract_face_features_vector(image, landmarks=None):
    """
    얼굴에서 특징 벡터를 추출합니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        features: 특징 벡터 (numpy array) 또는 None (얼굴을 찾지 못한 경우)
    """
    if not _mediapipe_available:
        return None
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            detected, landmarks = detect_face_landmarks(image)
            if not detected or landmarks is None:
                return None
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return None
        
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        nose = key_landmarks['nose']
        mouth = key_landmarks['mouth']
        face_center = key_landmarks['face_center']
        
        # 이미지 크기
        img_width, img_height = image.size
        
        # 얼굴 영역 크기 추정 (두 눈 사이 거리를 기준으로)
        eye_distance = math.sqrt((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)
        
        # 특징 벡터 구성 (정규화된 값들)
        features = []
        
        # 1. 눈 사이 거리 (정규화: 이미지 너비 대비)
        features.append(eye_distance / img_width if img_width > 0 else 0.0)
        
        # 2. 얼굴 비율 (눈-입 거리 / 눈-코 거리)
        if nose and mouth:
            eye_nose_dist = math.sqrt((nose[0] - (left_eye[0] + right_eye[0])/2)**2 + 
                                     (nose[1] - (left_eye[1] + right_eye[1])/2)**2)
            eye_mouth_dist = math.sqrt((mouth[0] - (left_eye[0] + right_eye[0])/2)**2 + 
                                      (mouth[1] - (left_eye[1] + right_eye[1])/2)**2)
            if eye_nose_dist > 0:
                features.append(eye_mouth_dist / eye_nose_dist)
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        # 3. 코 위치 (정규화: 얼굴 중심 기준)
        if nose and face_center:
            nose_offset_x = (nose[0] - face_center[0]) / eye_distance if eye_distance > 0 else 0.0
            nose_offset_y = (nose[1] - face_center[1]) / eye_distance if eye_distance > 0 else 0.0
            features.append(nose_offset_x)
            features.append(nose_offset_y)
        else:
            features.extend([0.0, 0.0])
        
        # 4. 입 위치 (정규화: 얼굴 중심 기준)
        if mouth and face_center:
            mouth_offset_x = (mouth[0] - face_center[0]) / eye_distance if eye_distance > 0 else 0.0
            mouth_offset_y = (mouth[1] - face_center[1]) / eye_distance if eye_distance > 0 else 0.0
            features.append(mouth_offset_x)
            features.append(mouth_offset_y)
        else:
            features.extend([0.0, 0.0])
        
        # 5. 얼굴 너비/높이 비율 (추정)
        # 얼굴 영역을 대략적으로 추정 (눈 위치와 입 위치를 기준)
        if mouth:
            face_width_est = eye_distance * 1.5  # 대략적인 얼굴 너비
            face_height_est = abs(mouth[1] - (left_eye[1] + right_eye[1])/2) * 2.5  # 대략적인 얼굴 높이
            if face_height_est > 0:
                features.append(face_width_est / face_height_est)
            else:
                features.append(0.0)
        else:
            features.append(0.0)
        
        # 6. 주요 랜드마크 포인트들의 상대적 위치 (정규화)
        # 눈, 코, 입의 상대적 위치를 더 세밀하게 추출
        if nose and mouth:
            # 눈-코-입 삼각형의 각도
            eye_center_x = (left_eye[0] + right_eye[0]) / 2
            eye_center_y = (left_eye[1] + right_eye[1]) / 2
            
            # 코에서 눈까지의 거리
            nose_eye_dist = math.sqrt((nose[0] - eye_center_x)**2 + (nose[1] - eye_center_y)**2)
            # 코에서 입까지의 거리
            nose_mouth_dist = math.sqrt((nose[0] - mouth[0])**2 + (nose[1] - mouth[1])**2)
            
            if eye_distance > 0:
                features.append(nose_eye_dist / eye_distance)
                features.append(nose_mouth_dist / eye_distance)
            else:
                features.extend([0.0, 0.0])
        else:
            features.extend([0.0, 0.0])
        
        return np.array(features, dtype=np.float32)
        
    except Exception as e:
        _get_logger().error(f"특징 벡터 추출 실패: {e}", exc_info=True)
        return None


def calculate_face_similarity(features1, features2):
    """
    두 얼굴 특징 벡터의 유사도를 계산합니다.
    
    Args:
        features1: 첫 번째 얼굴의 특징 벡터 (numpy array)
        features2: 두 번째 얼굴의 특징 벡터 (numpy array)
    
    Returns:
        similarity: 유사도 점수 (0.0 ~ 1.0, 1.0이 가장 유사)
    """
    if features1 is None or features2 is None:
        return 0.0
    
    try:
        # 코사인 유사도 계산
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cosine_similarity = dot_product / (norm1 * norm2)
        
        # 코사인 유사도를 0~1 범위로 정규화 (일반적으로 -1~1이지만 특징 벡터는 모두 양수이므로 0~1)
        # 더 정확한 비교를 위해 유클리드 거리도 고려
        euclidean_distance = np.linalg.norm(features1 - features2)
        
        # 거리를 유사도로 변환 (거리가 작을수록 유사도가 높음)
        # 최대 거리를 추정하여 정규화 (경험적으로 설정)
        max_distance = 10.0  # 대략적인 최대 거리
        distance_similarity = 1.0 / (1.0 + euclidean_distance / max_distance)
        
        # 코사인 유사도와 거리 유사도를 결합 (가중 평균)
        similarity = 0.7 * cosine_similarity + 0.3 * distance_similarity
        
        # 0~1 범위로 클리핑
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
        
    except Exception as e:
        _get_logger().error(f"유사도 계산 실패: {e}", exc_info=True)
        return 0.0


def find_similar_faces(reference_features, face_features_list, top_n=10):
    """
    기준 얼굴과 비슷한 얼굴들을 찾습니다.
    
    Args:
        reference_features: 기준 얼굴의 특징 벡터
        face_features_list: 비교할 얼굴들의 특징 벡터 리스트 [(features, metadata), ...]
            metadata는 파일 경로나 인덱스 등 추가 정보
        top_n: 반환할 상위 N개
    
    Returns:
        similar_faces: 유사도 점수와 함께 정렬된 리스트 [(similarity, metadata), ...]
    """
    if reference_features is None:
        return []
    
    similarities = []
    for features, metadata in face_features_list:
        if features is not None:
            similarity = calculate_face_similarity(reference_features, features)
            similarities.append((similarity, metadata))
    
    # 유사도가 높은 순으로 정렬
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 N개 반환
    return similarities[:top_n]


def extract_clothing_region(image, landmarks=None):
    """
    이미지에서 옷 영역을 추출합니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        clothing_region: 옷 영역 이미지 (PIL.Image) 또는 None
    """
    if not _mediapipe_available:
        return None
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            detected, landmarks = detect_face_landmarks(image)
            if not detected or landmarks is None:
                return None
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return None
        
        # 이미지 크기
        img_width, img_height = image.size
        
        # 입 위치 확인
        if 'mouth' in key_landmarks and key_landmarks['mouth']:
            mouth_y = key_landmarks['mouth'][1]
        elif 'nose' in key_landmarks and key_landmarks['nose']:
            # 입이 없으면 코 위치 기준으로 추정
            nose_y = key_landmarks['nose'][1]
            mouth_y = nose_y + (nose_y - (key_landmarks['left_eye'][1] + key_landmarks['right_eye'][1]) // 2) * 0.5
        else:
            return None
        
        # 얼굴 너비 추정 (두 눈 사이 거리 기준)
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        eye_distance = math.sqrt((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)
        face_width = int(eye_distance * 2.0)  # 얼굴 너비는 눈 사이 거리의 약 2배
        
        # 얼굴 중심 X 좌표
        face_center_x = (left_eye[0] + right_eye[0]) // 2
        
        # 옷 영역 추정
        # 입 아래부터 이미지 하단까지
        clothing_top = int(mouth_y + eye_distance * 0.3)  # 입 아래 약간 여유 공간
        clothing_bottom = img_height
        
        # 옷 영역이 너무 작으면 (이미지 하단이 얼굴에 가까우면) None 반환
        if clothing_bottom - clothing_top < eye_distance * 0.5:
            return None
        
        # 얼굴 중심 기준으로 좌우 경계 설정
        clothing_left = max(0, face_center_x - face_width // 2)
        clothing_right = min(img_width, face_center_x + face_width // 2)
        
        # 옷 영역 크롭
        clothing_region = image.crop((clothing_left, clothing_top, clothing_right, clothing_bottom))
        
        return clothing_region
        
    except Exception as e:
        _get_logger().error(f"옷 영역 추출 실패: {e}", exc_info=True)
        return None


def extract_clothing_features_vector(image, landmarks=None):
    """
    옷 영역에서 특징 벡터를 추출합니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        features: 옷 특징 벡터 (numpy array) 또는 None
    """
    try:
        # 옷 영역 추출
        clothing_region = extract_clothing_region(image, landmarks)
        if clothing_region is None:
            return None
        
        # RGB 모드로 변환
        if clothing_region.mode != 'RGB':
            clothing_region = clothing_region.convert('RGB')
        
        # 옷 영역을 일정한 크기로 리사이즈 (정규화)
        normalized_size = (128, 128)  # 옷 영역 정규화 크기
        clothing_resized = clothing_region.resize(normalized_size, Image.LANCZOS)
        
        # numpy 배열로 변환
        img_array = np.array(clothing_resized)
        
        # 특징 벡터 구성
        features = []
        
        if _cv2_available:
            # OpenCV를 사용한 히스토그램 계산
            # BGR로 변환
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # RGB 각 채널별 히스토그램 (32 bins로 축소하여 차원 감소)
            hist_bins = 32
            for i in range(3):  # B, G, R
                hist = cv2.calcHist([img_bgr], [i], None, [hist_bins], [0, 256])
                # 정규화
                hist = hist / (hist.sum() + 1e-10)  # 0으로 나누기 방지
                features.extend(hist.flatten().tolist())
            
            # 평균 색상 (R, G, B)
            mean_color = img_array.mean(axis=(0, 1))
            features.extend(mean_color.tolist())
            
            # 색상 표준편차 (R, G, B)
            std_color = img_array.std(axis=(0, 1))
            features.extend(std_color.tolist())
        else:
            # OpenCV가 없으면 간단한 통계값만 사용
            # 평균 색상
            mean_color = img_array.mean(axis=(0, 1))
            features.extend(mean_color.tolist())
            
            # 색상 표준편차
            std_color = img_array.std(axis=(0, 1))
            features.extend(std_color.tolist())
            
            # 중앙값 색상
            median_color = np.median(img_array.reshape(-1, 3), axis=0)
            features.extend(median_color.tolist())
        
        return np.array(features, dtype=np.float32)
        
    except Exception as e:
        _get_logger().error(f"옷 특징 벡터 추출 실패: {e}", exc_info=True)
        return None


def calculate_clothing_similarity(features1, features2):
    """
    두 옷 특징 벡터의 유사도를 계산합니다.
    
    Args:
        features1: 첫 번째 옷의 특징 벡터 (numpy array)
        features2: 두 번째 옷의 특징 벡터 (numpy array)
    
    Returns:
        similarity: 유사도 점수 (0.0 ~ 1.0, 1.0이 가장 유사)
    """
    if features1 is None or features2 is None:
        return 0.0
    
    try:
        # 히스토그램 교차 (Histogram Intersection) 또는 Bhattacharyya 거리
        # 히스토그램 부분과 통계 부분을 분리하여 비교
        
        # 히스토그램 부분 (앞부분)
        if len(features1) > 6 and len(features2) > 6:
            # 히스토그램이 있는 경우 (OpenCV 사용)
            hist1 = features1[:-6]  # 마지막 6개는 평균/표준편차
            hist2 = features2[:-6]
            
            # 히스토그램 교차 (Histogram Intersection)
            hist_intersection = np.minimum(hist1, hist2).sum()
            hist_union = np.maximum(hist1, hist2).sum()
            hist_similarity = hist_intersection / (hist_union + 1e-10)
        else:
            hist_similarity = 0.5  # 히스토그램이 없으면 중간값
        
        # 통계 부분 (평균, 표준편차)
        stats1 = features1[-6:] if len(features1) >= 6 else features1
        stats2 = features2[-6:] if len(features2) >= 6 else features2
        
        # 유클리드 거리 기반 유사도
        stats_distance = np.linalg.norm(stats1 - stats2)
        max_stats_distance = 1000.0  # 대략적인 최대 거리
        stats_similarity = 1.0 / (1.0 + stats_distance / max_stats_distance)
        
        # 히스토그램 유사도와 통계 유사도 결합
        similarity = 0.6 * hist_similarity + 0.4 * stats_similarity
        
        # 0~1 범위로 클리핑
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
        
    except Exception as e:
        _get_logger().error(f"옷 유사도 계산 실패: {e}", exc_info=True)
        return 0.0


def extract_combined_features_vector(image, landmarks=None, include_clothing=True):
    """
    얼굴 특징과 옷 특징을 결합한 종합 특징 벡터를 추출합니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        include_clothing: 옷 특징 포함 여부
    
    Returns:
        combined_features: (face_features, clothing_features) 튜플 또는 None
    """
    # 얼굴 특징 추출
    face_features = extract_face_features_vector(image, landmarks)
    if face_features is None:
        return None
    
    # 옷 특징 추출
    clothing_features = None
    if include_clothing:
        clothing_features = extract_clothing_features_vector(image, landmarks)
    
    return (face_features, clothing_features)


def calculate_combined_similarity(features1, features2, face_weight=0.7, clothing_weight=0.3):
    """
    얼굴 특징과 옷 특징을 결합한 종합 유사도를 계산합니다.
    
    Args:
        features1: (face_features, clothing_features) 튜플
        features2: (face_features, clothing_features) 튜플
        face_weight: 얼굴 유사도 가중치 (기본값: 0.7)
        clothing_weight: 옷 유사도 가중치 (기본값: 0.3)
    
    Returns:
        similarity: 종합 유사도 점수 (0.0 ~ 1.0)
    """
    if features1 is None or features2 is None:
        return 0.0
    
    face_features1, clothing_features1 = features1
    face_features2, clothing_features2 = features2
    
    # 얼굴 유사도 계산
    face_similarity = calculate_face_similarity(face_features1, face_features2)
    
    # 옷 유사도 계산
    if clothing_features1 is not None and clothing_features2 is not None:
        clothing_similarity = calculate_clothing_similarity(clothing_features1, clothing_features2)
        # 종합 유사도
        combined_similarity = face_weight * face_similarity + clothing_weight * clothing_similarity
    else:
        # 옷 특징이 없으면 얼굴만 사용
        combined_similarity = face_similarity
    
    return combined_similarity
