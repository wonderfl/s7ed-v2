"""
얼굴 생성 모듈
여러 얼굴을 합성하거나 파트를 조합하여 새로운 얼굴을 생성합니다.
"""
import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, align_face, is_available as landmarks_available
    from utils.face_morphing import adjust_eye_size, adjust_nose_size, adjust_jaw, adjust_face_size
    _landmarks_available = landmarks_available()
except ImportError:
    _landmarks_available = False


def extract_face_features(image, landmarks=None):
    """
    얼굴에서 특징을 추출합니다.
    
    Args:
        image: PIL.Image 객체
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        dict: 얼굴 특징 딕셔너리
            - eye_size: 눈 크기 비율 (기준 얼굴 대비)
            - nose_size: 코 크기 비율
            - face_width: 얼굴 너비 비율
            - face_height: 얼굴 높이 비율
            - eye_distance: 눈 사이 거리
            - face_shape: 얼굴 형태 (타원형, 둥근형 등)
    """
    if not _landmarks_available:
        return None
    
    try:
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return None
        
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            return None
        
        left_eye = key_landmarks['left_eye']
        right_eye = key_landmarks['right_eye']
        nose = key_landmarks.get('nose')
        mouth = key_landmarks.get('mouth')
        
        if not left_eye or not right_eye:
            return None
        
        # 눈 사이 거리
        eye_distance = ((right_eye[0] - left_eye[0])**2 + 
                        (right_eye[1] - left_eye[1])**2)**0.5
        
        # 얼굴 크기 추정
        if mouth:
            face_height = abs(mouth[1] - (left_eye[1] + right_eye[1]) // 2) * 2.5
        else:
            face_height = eye_distance * 2.0
        
        face_width = eye_distance * 2.5
        
        # 눈 크기 추정 (랜드마크 기반)
        # 실제로는 더 정교한 계산이 필요하지만, 간단하게 눈 사이 거리를 기준으로
        eye_size_ratio = 1.0  # 기본값, 실제로는 더 정교한 계산 필요
        
        # 코 크기 추정
        if nose:
            nose_size_ratio = 1.0  # 기본값
        else:
            nose_size_ratio = 1.0
        
        return {
            'eye_size': eye_size_ratio,
            'nose_size': nose_size_ratio,
            'face_width': face_width,
            'face_height': face_height,
            'eye_distance': eye_distance,
            'landmarks': landmarks,
            'key_landmarks': key_landmarks
        }
    except Exception as e:
        print(f"[얼굴생성] 특징 추출 실패: {e}")
        return None


def morph_faces(face_images, weights=None):
    """
    여러 얼굴을 합성합니다 (Feature-based Generation).
    각 얼굴의 특징을 추출하고 조합하여 새로운 얼굴을 생성합니다.
    
    Args:
        face_images: PIL.Image 객체 리스트 (최소 2개)
        weights: 각 얼굴의 가중치 리스트 (None이면 균등 가중치)
    
    Returns:
        PIL.Image: 합성된 얼굴 이미지
    """
    if len(face_images) < 2:
        raise ValueError("얼굴 합성을 하려면 최소 2개 이상의 얼굴이 필요합니다.")
    
    if weights is None:
        weights = [1.0] * len(face_images)
    
    if len(weights) != len(face_images):
        weights = [1.0] * len(face_images)
    
    # 가중치 정규화
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
    else:
        weights = [1.0 / len(face_images)] * len(face_images)
    
    try:
        # 모든 얼굴을 RGB로 변환
        rgb_images = []
        for img in face_images:
            if img.mode != 'RGB':
                rgb_images.append(img.convert('RGB'))
            else:
                rgb_images.append(img)
        
        # 첫 번째 얼굴을 기준으로 크기 통일
        base_size = rgb_images[0].size
        resized_images = []
        for img in rgb_images:
            if img.size != base_size:
                resized_images.append(img.resize(base_size, Image.LANCZOS))
            else:
                resized_images.append(img)
        
        if _landmarks_available and _cv2_available:
            try:
                # 첫 번째 얼굴을 베이스로 사용
                base_image = resized_images[0]
                
                # 베이스 얼굴의 특징 추출
                base_features = extract_face_features(base_image)
                if base_features is None:
                    raise ValueError("베이스 얼굴에서 특징을 추출할 수 없습니다.")
                
                # 베이스 얼굴 정렬
                base_aligned, _ = align_face(base_image, base_features['landmarks'])
                
                # 정렬 후 다시 특징 추출
                base_aligned_landmarks, base_detected = detect_face_landmarks(base_aligned)
                if not base_detected or base_aligned_landmarks is None:
                    raise ValueError("정렬된 베이스 얼굴에서 랜드마크를 찾을 수 없습니다.")
                
                base_key = get_key_landmarks(base_aligned_landmarks)
                if base_key is None:
                    raise ValueError("정렬된 베이스 얼굴의 주요 랜드마크를 추출할 수 없습니다.")
                
                # 베이스 얼굴의 눈 사이 거리 (기준)
                base_left_eye = base_key['left_eye']
                base_right_eye = base_key['right_eye']
                base_eye_distance = ((base_right_eye[0] - base_left_eye[0])**2 + 
                                     (base_right_eye[1] - base_left_eye[1])**2)**0.5
                
                # 모든 얼굴의 특징 추출 및 조합
                combined_features = {
                    'eye_size': 1.0,
                    'nose_size': 1.0,
                    'face_width': 1.0,
                    'face_height': 1.0,
                    'eye_distance': base_eye_distance
                }
                
                # 가중 평균으로 특징 조합
                for i, img in enumerate(resized_images):
                    features = extract_face_features(img)
                    if features:
                        weight = weights[i]
                        # 눈 사이 거리 기준으로 크기 조정
                        if features['eye_distance'] > 0 and base_eye_distance > 0:
                            scale = features['eye_distance'] / base_eye_distance
                            combined_features['eye_size'] += (features['eye_size'] * scale - 1.0) * weight
                            combined_features['nose_size'] += (features['nose_size'] * scale - 1.0) * weight
                            combined_features['face_width'] += (features['face_width'] / base_eye_distance - combined_features['face_width']) * weight
                            combined_features['face_height'] += (features['face_height'] / base_eye_distance - combined_features['face_height']) * weight
                
                # 베이스 얼굴을 결과로 시작 (특징 조정 제거 - 조각나는 문제 방지)
                result = base_aligned.copy()
                result_array = np.array(result)
                base_array = np.array(base_aligned)
                
                # 얼굴 영역 마스크 생성
                face_center = (
                    (base_left_eye[0] + base_right_eye[0]) // 2,
                    (base_left_eye[1] + base_right_eye[1]) // 2
                )
                ellipse_width = int(base_eye_distance * 2.5)
                ellipse_height = int(base_eye_distance * 3.2)
                
                mask = np.zeros((base_size[1], base_size[0]), dtype=np.uint8)
                cv2.ellipse(mask, 
                           (face_center[0], face_center[1]),
                           (ellipse_width // 2, ellipse_height // 2),
                           0, 0, 360, 255, -1)
                mask = cv2.GaussianBlur(mask, (31, 31), 0)
                mask_3channel = mask.astype(np.float32) / 255.0
                mask_3channel = np.stack([mask_3channel, mask_3channel, mask_3channel], axis=2)
                
                # 다른 얼굴들의 색상을 가중 평균으로 블렌딩 (얼굴 영역만)
                for i, img in enumerate(resized_images[1:], 1):
                    if weights[i] > 0.1:
                        # 얼굴 정렬
                        landmarks, detected = detect_face_landmarks(img)
                        if detected and landmarks:
                            aligned, _ = align_face(img, landmarks)
                            aligned_array = np.array(aligned)
                            if aligned_array.shape == result_array.shape:
                                # 얼굴 영역만 색상 블렌딩
                                color_diff = (aligned_array.astype(np.float32) - base_array) * mask_3channel
                                result_array = result_array + color_diff * weights[i]
                
                result_array = np.clip(result_array, 0, 255).astype(np.uint8)
                result = Image.fromarray(result_array)
                
                return result
                
            except Exception as e:
                print(f"[얼굴생성] 특징 기반 합성 실패, 단순 블렌딩으로 폴백: {e}")
                import traceback
                traceback.print_exc()
        
        # 랜드마크가 없거나 실패한 경우 단순 블렌딩
        img_arrays = [np.array(img) for img in resized_images]
        
        # 가중 평균 계산
        result_array = np.zeros_like(img_arrays[0], dtype=np.float32)
        for img_array, weight in zip(img_arrays, weights):
            result_array += img_array.astype(np.float32) * weight
        
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        return Image.fromarray(result_array)
        
    except Exception as e:
        print(f"[얼굴생성] 얼굴 합성 실패: {e}")
        # 실패 시 첫 번째 이미지 반환
        return face_images[0].copy()


def extract_face_part(image, part_key, landmarks=None):
    """
    얼굴에서 특정 파트를 추출합니다.
    
    Args:
        image: PIL.Image 객체
        part_key: 파트 키 ('left_eye', 'right_eye', 'nose', 'mouth', 'face_outline', 'skin')
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
    
    Returns:
        PIL.Image: 추출된 파트 이미지 (마스크 포함)
        mask: 마스크 이미지 (PIL.Image)
    """
    if not _landmarks_available:
        # 랜드마크가 없으면 전체 이미지 반환
        mask = Image.new('L', image.size, 255)
        return image, mask
    
    try:
        # 랜드마크가 없으면 자동 감지
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                mask = Image.new('L', image.size, 255)
                return image, mask
        
        # 주요 랜드마크 추출
        key_landmarks = get_key_landmarks(landmarks)
        if key_landmarks is None:
            mask = Image.new('L', image.size, 255)
            return image, mask
        
        # RGB 모드로 변환
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image
        
        img_array = np.array(img_rgb)
        img_height, img_width = img_array.shape[:2]
        
        # 파트별 영역 계산
        center = None
        radius = 0
        
        if part_key == 'left_eye':
            center = key_landmarks.get('left_eye')
            if center is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            left_eye = key_landmarks.get('left_eye')
            right_eye = key_landmarks.get('right_eye')
            if left_eye is None or right_eye is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
            radius = int(eye_distance * 0.25)
        elif part_key == 'right_eye':
            center = key_landmarks.get('right_eye')
            if center is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            left_eye = key_landmarks.get('left_eye')
            right_eye = key_landmarks.get('right_eye')
            if left_eye is None or right_eye is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
            radius = int(eye_distance * 0.25)
        elif part_key == 'nose':
            center = key_landmarks.get('nose')
            if center is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            left_eye = key_landmarks.get('left_eye')
            right_eye = key_landmarks.get('right_eye')
            if left_eye is None or right_eye is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
            radius = int(eye_distance * 0.2)
        elif part_key == 'mouth':
            center = key_landmarks.get('mouth')
            if center is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            left_eye = key_landmarks.get('left_eye')
            right_eye = key_landmarks.get('right_eye')
            if left_eye is None or right_eye is None:
                mask = Image.new('L', image.size, 255)
                return image, mask
            eye_distance = ((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)**0.5
            radius = int(eye_distance * 0.3)
        else:
            # face_outline, skin은 전체 얼굴 영역
            mask = Image.new('L', image.size, 255)
            return image, mask
        
        if center is None or radius <= 0:
            mask = Image.new('L', image.size, 255)
            return image, mask
        
        # 마스크 생성 (원형)
        if _cv2_available:
            mask_array = np.zeros((img_height, img_width), dtype=np.uint8)
            cv2.circle(mask_array, center, radius, 255, -1)
            # 가우시안 블러로 부드럽게
            mask_array = cv2.GaussianBlur(mask_array, (15, 15), 0)
            mask = Image.fromarray(mask_array, mode='L')
        else:
            # PIL로 원형 마스크 생성
            from PIL import ImageDraw
            mask = Image.new('L', image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse(
                [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
                fill=255
            )
            # 간단한 블러 효과
            mask = mask.filter(ImageFilter.GaussianBlur(radius=5))
        
        # 파트 이미지 추출
        part_img = Image.new('RGB', image.size, (0, 0, 0))
        part_img.paste(img_rgb, (0, 0))
        
        return part_img, mask
        
    except Exception as e:
        print(f"[얼굴생성] 파트 추출 실패: {e}")
        mask = Image.new('L', image.size, 255)
        return image, mask


def combine_face_parts(part_images):
    """
    여러 얼굴의 파트를 조합하여 새로운 얼굴을 생성합니다.
    
    Args:
        part_images: 파트 이미지 딕셔너리
            {
                'left_eye': PIL.Image,
                'right_eye': PIL.Image,
                'nose': PIL.Image,
                'mouth': PIL.Image,
                'face_outline': PIL.Image,
                'skin': PIL.Image
            }
    
    Returns:
        PIL.Image: 조합된 얼굴 이미지
    """
    if not part_images:
        raise ValueError("최소한 하나의 파트가 필요합니다.")
    
    try:
        # 기본 이미지 선택 (우선순위: face_outline > skin > 첫 번째 파트)
        base_key = None
        if 'face_outline' in part_images and part_images['face_outline'] is not None:
            base_key = 'face_outline'
        elif 'skin' in part_images and part_images['skin'] is not None:
            base_key = 'skin'
        else:
            base_key = list(part_images.keys())[0]
        
        base_image = part_images[base_key]
        if base_image.mode != 'RGB':
            base_image = base_image.convert('RGB')
        
        # 기준 크기
        base_size = base_image.size
        
        # 모든 파트를 기준 크기로 리사이즈
        resized_parts = {}
        for key, img in part_images.items():
            if img is None:
                continue
            if img.mode != 'RGB':
                img = img.convert('RGB')
            if img.size != base_size:
                resized_parts[key] = img.resize(base_size, Image.LANCZOS)
            else:
                resized_parts[key] = img
        
        # 기본 이미지로 시작
        result = base_image.copy()
        
        if _landmarks_available and _cv2_available:
            # 랜드마크 기반 파트 조합
            try:
                # 각 파트를 추출하고 블렌딩
                for part_key, part_img in resized_parts.items():
                    if part_key == base_key:
                        continue
                    
                    # 파트 추출
                    extracted_part, mask = extract_face_part(part_img, part_key)
                    
                    # 마스크를 사용하여 블렌딩
                    result = Image.composite(extracted_part, result, mask)
                    
            except Exception as e:
                print(f"[얼굴생성] 랜드마크 기반 파트 조합 실패, 단순 블렌딩으로 폴백: {e}")
                # 폴백: 단순 블렌딩
                for part_key, part_img in resized_parts.items():
                    if part_key != base_key:
                        # 간단한 블렌딩 (중앙 영역만)
                        result = Image.blend(result, part_img, 0.3)
        else:
            # 랜드마크가 없으면 단순 블렌딩
            for part_key, part_img in resized_parts.items():
                if part_key != base_key:
                    # 간단한 블렌딩
                    result = Image.blend(result, part_img, 0.3)
        
        return result
        
    except Exception as e:
        print(f"[얼굴생성] 파트 조합 실패: {e}")
        import traceback
        traceback.print_exc()
        # 실패 시 첫 번째 이미지 반환
        if part_images:
            first_img = list(part_images.values())[0]
            if first_img is not None:
                return first_img.copy()
        raise
