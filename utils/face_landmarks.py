"""
얼굴 랜드마크 감지 및 정렬 모듈
MediaPipe를 사용하여 얼굴의 주요 특징점을 감지하고 얼굴을 정렬합니다.
"""
import numpy as np
from PIL import Image

# MediaPipe 선택적 import
try:
    import mediapipe as mp
    _mediapipe_available = True
except ImportError:
    _mediapipe_available = False
    print("[얼굴랜드마크] MediaPipe가 설치되지 않았습니다. 얼굴 랜드마크 기능을 사용하려면 'pip install mediapipe'를 실행하세요.")


def is_available():
    """MediaPipe 사용 가능 여부 확인"""
    return _mediapipe_available


def detect_face_landmarks(image):
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
        return None, False
    
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
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        # RGB로 변환 (MediaPipe는 RGB를 기대)
        results = face_mesh.process(img_array)
        
        if results.multi_face_landmarks:
            # 첫 번째 얼굴의 랜드마크 가져오기
            face_landmarks = results.multi_face_landmarks[0]
            
            # 랜드마크 포인트를 (x, y) 좌표로 변환
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * img_width)
                y = int(landmark.y * img_height)
                landmarks.append((x, y))
            
            face_mesh.close()
            return landmarks, True
        else:
            face_mesh.close()
            return None, False
            
    except Exception as e:
        print(f"[얼굴랜드마크] 랜드마크 감지 실패: {e}")
        return None, False


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
    
    # MediaPipe Face Mesh의 주요 랜드마크 인덱스
    # 참고: https://github.com/google/mediapipe/blob/master/mediapipe/python/solutions/face_mesh.py
    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    NOSE_TIP_INDEX = 4
    MOUTH_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318]
    
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


def align_face(image, landmarks=None):
    """
    얼굴을 정렬합니다 (두 눈을 수평으로 맞춤).
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        aligned_image: 정렬된 PIL.Image 객체
        rotation_angle: 회전 각도 (도 단위)
    
    Note:
        MediaPipe가 없거나 얼굴을 찾지 못하면 원본 이미지를 반환합니다.
    """
    if not _mediapipe_available:
        return image, 0.0
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image, 0.0
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return image, 0.0
        
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        
        # 두 눈 사이의 각도 계산
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        
        # 수평이면 회전 불필요
        if abs(dy) < 1:
            return image, 0.0
        
        # 회전 각도 계산 (라디안 → 도)
        import math
        angle = math.degrees(math.atan2(dy, dx))
        
        # 이미지 회전 (두 눈의 중점을 중심으로)
        center_x = (left_eye[0] + right_eye[0]) // 2
        center_y = (left_eye[1] + right_eye[1]) // 2
        
        # PIL Image 회전
        aligned_image = image.rotate(-angle, center=(center_x, center_y), resample=Image.BICUBIC, expand=False)
        
        return aligned_image, angle
        
    except Exception as e:
        print(f"[얼굴랜드마크] 얼굴 정렬 실패: {e}")
        return image, 0.0
