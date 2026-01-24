"""
통합 함수 모듈
모든 얼굴 특징 보정을 한 번에 적용하는 통합 함수
"""
import numpy as np
from PIL import Image

from .constants import _landmarks_available, _scipy_available
from .adjustments import (
    adjust_eye_size, adjust_eye_spacing, adjust_eye_position,
    adjust_nose_size, adjust_jaw, adjust_face_size, adjust_mouth_size,
    adjust_upper_lip_size, adjust_lower_lip_size,
    adjust_upper_lip_shape, adjust_lower_lip_shape,
    adjust_upper_lip_width, adjust_lower_lip_width,
    adjust_lip_vertical_move
)
from .polygon_morphing import (
    transform_points_for_eye_size,
    transform_points_for_nose_size,
    transform_points_for_jaw,
    transform_points_for_face_size,
    transform_points_for_mouth_size,
    transform_points_for_eye_position,
    transform_points_for_lip_shape,
    transform_points_for_lip_width,
    transform_points_for_lip_vertical_move,
    morph_face_by_polygons
)

# 외부 모듈 import
try:
    from utils.face_landmarks import detect_face_landmarks
except ImportError:
    detect_face_landmarks = None


def apply_all_adjustments(image, eye_size=1.0, nose_size=1.0, mouth_size=1.0, mouth_width=1.0,
                          jaw_adjustment=0.0, face_width=1.0, face_height=1.0, landmarks=None,
                          left_eye_size=None, right_eye_size=None,
                          eye_spacing=False, left_eye_position_x=0.0, right_eye_position_x=0.0,
                          left_eye_position_y=0.0, right_eye_position_y=0.0,
                          eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                          left_eye_region_padding=None, right_eye_region_padding=None,
                          left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                          right_eye_region_offset_x=None, right_eye_region_offset_y=None,
                          use_individual_lip_region=False,
                          upper_lip_size=1.0, upper_lip_width=1.0,
                          lower_lip_size=1.0, lower_lip_width=1.0,
                          upper_lip_shape=1.0, lower_lip_shape=1.0, 
                          upper_lip_vertical_move=0.0, lower_lip_vertical_move=0.0,
                          upper_lip_region_padding_x=None, upper_lip_region_padding_y=None,
                          lower_lip_region_padding_x=None, lower_lip_region_padding_y=None,
        upper_lip_region_offset_x=None, upper_lip_region_offset_y=None,
        lower_lip_region_offset_x=None, lower_lip_region_offset_y=None,
        use_landmark_warping=False, blend_ratio=1.0,
        clamping_enabled=True, margin_ratio=0.3):
    """
    모든 얼굴 특징 보정을 한 번에 적용합니다.
    
    Args:
        image: PIL.Image 객체
        eye_size: 눈 크기 비율 (개별 조정 미사용 시)
        nose_size: 코 크기 비율
        mouth_size: 입 크기 비율 (개별 적용 미사용 시)
        mouth_width: 입 너비 비율 (개별 적용 미사용 시)
        jaw_adjustment: 턱선 조정 값
        face_width: 얼굴 너비 비율
        face_height: 얼굴 높이 비율
        landmarks: 랜드마크 포인트 리스트 (None이면 자동 감지)
        use_landmark_warping: 랜드마크 직접 변형 모드 사용 여부 (기본값: False)
            True일 때 Delaunay Triangulation 방식 사용
            False일 때 기존 영역 기반 방식 사용
        left_eye_size: 왼쪽 눈 크기 비율 (개별 조정 사용 시)
        right_eye_size: 오른쪽 눈 크기 비율 (개별 조정 사용 시)
        eye_spacing: 눈 간격 조정 활성화 여부 (Boolean, True면 자동으로 간격 조정)
        left_eye_position_x: 왼쪽 눈 수평 위치 조정 (픽셀)
        right_eye_position_x: 오른쪽 눈 수평 위치 조정 (픽셀)
        left_eye_position_y: 왼쪽 눈 수직 위치 조정 (픽셀)
        right_eye_position_y: 오른쪽 눈 수직 위치 조정 (픽셀)
        eye_region_padding: 눈 영역 패딩 비율 (0.0 ~ 1.0, None이면 개별 파라미터 사용)
        eye_region_offset_x: 눈 영역 수평 오프셋 (픽셀, None이면 개별 파라미터 사용)
        eye_region_offset_y: 눈 영역 수직 오프셋 (픽셀, None이면 개별 파라미터 사용)
        left_eye_region_padding: 왼쪽 눈 영역 패딩 비율
        right_eye_region_padding: 오른쪽 눈 영역 패딩 비율
        left_eye_region_offset_x: 왼쪽 눈 영역 수평 오프셋
        left_eye_region_offset_y: 왼쪽 눈 영역 수직 오프셋
        right_eye_region_offset_x: 오른쪽 눈 영역 수평 오프셋
        right_eye_region_offset_y: 오른쪽 눈 영역 수직 오프셋
        use_individual_lip_region: 입술 개별 적용 여부 (Boolean, 호환성 유지)
        upper_lip_size: 윗입술 크기 비율 (개별 적용 사용 시, 호환성 유지)
        upper_lip_width: 윗입술 너비 비율 (개별 적용 사용 시, 호환성 유지)
        lower_lip_size: 아래입술 크기 비율 (개별 적용 사용 시, 호환성 유지)
        lower_lip_width: 아래입술 너비 비율 (개별 적용 사용 시, 호환성 유지)
        upper_lip_shape: 윗입술 모양/두께 비율 (0.5 ~ 2.0, 기본값: 1.0)
        lower_lip_shape: 아랫입술 모양/두께 비율 (0.5 ~ 2.0, 기본값: 1.0)
        upper_lip_vertical_move: 윗입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=위로, 음수=아래로)
        lower_lip_vertical_move: 아랫입술 수직 이동 (-50 ~ +50 픽셀, 기본값: 0.0, 양수=아래로, 음수=위로)
        Note: upper_lip_width와 lower_lip_width는 use_individual_lip_region=True일 때 사용되며,
              새로운 방식에서는 upper_lip_shape, lower_lip_shape와 함께 사용됩니다.
    
    Returns:
        PIL.Image: 조정된 이미지
    """
    if not _landmarks_available:
        return image
    
    try:
        # 랜드마크가 없으면 자동 감지 (한 번만)
        if landmarks is None:
            landmarks, detected = detect_face_landmarks(image)
            if not detected:
                return image
        
        # 랜드마크 직접 변형 모드 사용 시
        if use_landmark_warping and _scipy_available:
            # 원본 랜드마크 저장
            original_landmarks = list(landmarks)
            transformed_landmarks = list(landmarks)
            
            # 각 편집 파라미터를 기반으로 랜드마크 포인트 변형
            # 1. 눈 위치 조정 (변경이 있을 때만)
            if (abs(left_eye_position_x) >= 0.1 or abs(left_eye_position_y) >= 0.1 or 
                abs(right_eye_position_x) >= 0.1 or abs(right_eye_position_y) >= 0.1):
                transformed_landmarks = transform_points_for_eye_position(
                    transformed_landmarks,
                    left_eye_position_x, left_eye_position_y,
                    right_eye_position_x, right_eye_position_y
                )
            
            # 2. 눈 크기 조정 (변경이 있을 때만)
            if left_eye_size is not None or right_eye_size is not None:
                # 개별 눈 크기 조정 모드: 둘 다 1.0에 가까우면 스킵
                left_ratio = left_eye_size if left_eye_size is not None else 1.0
                right_ratio = right_eye_size if right_eye_size is not None else 1.0
                # 유효성 검사: 값이 None이 아니고 유효한 범위인지 확인
                if left_ratio is not None and right_ratio is not None:
                    if (0.1 <= left_ratio <= 5.0 or 0.1 <= right_ratio <= 5.0) and \
                       (abs(left_ratio - 1.0) >= 0.01 or abs(right_ratio - 1.0) >= 0.01):
                        transformed_landmarks = transform_points_for_eye_size(
                            transformed_landmarks,
                            eye_size_ratio=1.0,
                            left_eye_size_ratio=left_eye_size,
                            right_eye_size_ratio=right_eye_size
                        )

            elif eye_size is not None and abs(eye_size - 1.0) >= 0.01:
                if 0.1 <= eye_size <= 5.0:
                    transformed_landmarks = transform_points_for_eye_size(
                        transformed_landmarks,
                        eye_size_ratio=eye_size
                    )
            
            # 3. 코 크기 조정
            if abs(nose_size - 1.0) >= 0.01:
                transformed_landmarks = transform_points_for_nose_size(
                    transformed_landmarks,
                    nose_size_ratio=nose_size
                )
            
            # 4. 입 크기 조정 (기본 파라미터 사용 시)
            if not use_individual_lip_region:
                if abs(mouth_size - 1.0) >= 0.01 or abs(mouth_width - 1.0) >= 0.01:
                    transformed_landmarks = transform_points_for_mouth_size(
                        transformed_landmarks,
                        mouth_size_ratio=mouth_size,
                        mouth_width_ratio=mouth_width
                    )
            
            # 5. 입술 세부 편집 (shape, width, vertical_move)
            # 입술 모양(두께) 조정
            if abs(upper_lip_shape - 1.0) >= 0.01 or abs(lower_lip_shape - 1.0) >= 0.01:
                transformed_landmarks = transform_points_for_lip_shape(
                    transformed_landmarks,
                    upper_lip_shape=upper_lip_shape,
                    lower_lip_shape=lower_lip_shape
                )
            
            # 입술 너비 조정
            if abs(upper_lip_width - 1.0) >= 0.01 or abs(lower_lip_width - 1.0) >= 0.01:
                transformed_landmarks = transform_points_for_lip_width(
                    transformed_landmarks,
                    upper_lip_width=upper_lip_width,
                    lower_lip_width=lower_lip_width
                )
            
            # 입술 수직 이동 조정
            if abs(upper_lip_vertical_move) >= 0.1 or abs(lower_lip_vertical_move) >= 0.1:
                transformed_landmarks = transform_points_for_lip_vertical_move(
                    transformed_landmarks,
                    upper_lip_vertical_move=upper_lip_vertical_move,
                    lower_lip_vertical_move=lower_lip_vertical_move
                )
            
            # 6. 얼굴 윤곽(턱선) 조정
            if abs(jaw_adjustment) >= 0.1:
                transformed_landmarks = transform_points_for_jaw(
                    transformed_landmarks,
                    jaw_adjustment=jaw_adjustment
                )
            
            # 7. 얼굴 크기 조정 (너비/높이)
            if abs(face_width - 1.0) >= 0.01 or abs(face_height - 1.0) >= 0.01:
                transformed_landmarks = transform_points_for_face_size(
                    transformed_landmarks,
                    face_width_ratio=face_width,
                    face_height_ratio=face_height
                )
            
            # 랜드마크 변형을 이미지에 적용
            # 변형이 실제로 있었는지 확인 (원본과 동일하면 스킵)
            landmarks_changed = False
            for i in range(len(original_landmarks)):
                if abs(original_landmarks[i][0] - transformed_landmarks[i][0]) > 0.1 or \
                   abs(original_landmarks[i][1] - transformed_landmarks[i][1]) > 0.1:
                    landmarks_changed = True
                    break
            
            if not landmarks_changed:
                print("[얼굴모핑] 랜드마크 변형 없음 (모든 값이 기본값), 원본 이미지 반환")
                return image
            
            result = morph_face_by_polygons(
                image, original_landmarks, transformed_landmarks,
                clamping_enabled=clamping_enabled, margin_ratio=margin_ratio
            )
            if result is None:
                print("[얼굴모핑] 랜드마크 변형 결과가 None입니다")
                return image
            else:
                print("[얼굴모핑] 랜드마크 변형 완료")
            return result
        
        # 각 조정을 순차적으로 적용
        # 순서: 간격 조정 → 위치 조정 → 크기 조정 → 기타 조정
        result = image.copy()
        
        # 눈 영역 파라미터 결정 (개별 파라미터가 있으면 사용, 없으면 기본값 사용)
        use_individual_region = (left_eye_region_padding is not None or right_eye_region_padding is not None)
        
        # 1. 눈 간격 조정은 수평 조정 값으로 처리되므로 여기서는 처리하지 않음
        # (눈 간격 조정 체크박스는 수평 조정 시 반대 동기화만 담당)
        
        # 2. 눈 위치 조정 (왼쪽/오른쪽 개별 처리)
        # 왼쪽 눈 위치 조정
        if abs(left_eye_position_x) >= 0.1 or abs(left_eye_position_y) >= 0.1:
            if use_individual_region:
                result = adjust_eye_position(result, left_eye_position_x, left_eye_position_y, landmarks,
                                            None, None, None,  # 기본 파라미터는 None
                                            left_eye_region_padding, right_eye_region_padding,
                                            left_eye_region_offset_x, left_eye_region_offset_y,
                                            right_eye_region_offset_x, right_eye_region_offset_y,
                                            eye='left')
            else:
                result = adjust_eye_position(result, left_eye_position_x, left_eye_position_y, landmarks,
                                            eye_region_padding, eye_region_offset_x, eye_region_offset_y,
                                            None, None, None, None, None, None,  # 개별 파라미터는 None
                                            eye='left')
        
        # 오른쪽 눈 위치 조정
        if abs(right_eye_position_x) >= 0.1 or abs(right_eye_position_y) >= 0.1:
            if use_individual_region:
                result = adjust_eye_position(result, right_eye_position_x, right_eye_position_y, landmarks,
                                            None, None, None,  # 기본 파라미터는 None
                                            left_eye_region_padding, right_eye_region_padding,
                                            left_eye_region_offset_x, left_eye_region_offset_y,
                                            right_eye_region_offset_x, right_eye_region_offset_y,
                                            eye='right')
            else:
                result = adjust_eye_position(result, right_eye_position_x, right_eye_position_y, landmarks,
                                            eye_region_padding, eye_region_offset_x, eye_region_offset_y,
                                            None, None, None, None, None, None,  # 개별 파라미터는 None
                                            eye='right')
        
        # 3. 눈 크기 조정 (개별 조정 또는 기본 조정, 개별 파라미터 전달)
        if left_eye_size is not None or right_eye_size is not None:
            # 개별 조정 모드
            if use_individual_region:
                result = adjust_eye_size(result, eye_size_ratio=1.0, landmarks=landmarks,
                                        left_eye_size_ratio=left_eye_size, right_eye_size_ratio=right_eye_size,
                                        eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                                        left_eye_region_padding=left_eye_region_padding, right_eye_region_padding=right_eye_region_padding,
                                        left_eye_region_offset_x=left_eye_region_offset_x, left_eye_region_offset_y=left_eye_region_offset_y,
                                        right_eye_region_offset_x=right_eye_region_offset_x, right_eye_region_offset_y=right_eye_region_offset_y,
                                        blend_ratio=blend_ratio)
            else:
                result = adjust_eye_size(result, eye_size_ratio=1.0, landmarks=landmarks,
                                        left_eye_size_ratio=left_eye_size, right_eye_size_ratio=right_eye_size,
                                        eye_region_padding=eye_region_padding, eye_region_offset_x=eye_region_offset_x, eye_region_offset_y=eye_region_offset_y,
                                        left_eye_region_padding=None, right_eye_region_padding=None,
                                        left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                                        right_eye_region_offset_x=None, right_eye_region_offset_y=None,
                                        blend_ratio=blend_ratio)
        elif abs(eye_size - 1.0) >= 0.01:
            # 기본 조정 모드
            if use_individual_region:
                result = adjust_eye_size(result, eye_size_ratio=eye_size, landmarks=landmarks,
                                        eye_region_padding=None, eye_region_offset_x=None, eye_region_offset_y=None,
                                        left_eye_region_padding=left_eye_region_padding, right_eye_region_padding=right_eye_region_padding,
                                        left_eye_region_offset_x=left_eye_region_offset_x, left_eye_region_offset_y=left_eye_region_offset_y,
                                        right_eye_region_offset_x=right_eye_region_offset_x, right_eye_region_offset_y=right_eye_region_offset_y,
                                        blend_ratio=blend_ratio)
            else:
                result = adjust_eye_size(result, eye_size_ratio=eye_size, landmarks=landmarks,
                                        eye_region_padding=eye_region_padding, eye_region_offset_x=eye_region_offset_x, eye_region_offset_y=eye_region_offset_y,
                                        left_eye_region_padding=None, right_eye_region_padding=None,
                                        left_eye_region_offset_x=None, left_eye_region_offset_y=None,
                                        right_eye_region_offset_x=None, right_eye_region_offset_y=None,
                                        blend_ratio=blend_ratio)
        
        # 4. 기타 조정
        result = adjust_nose_size(result, nose_size, landmarks, blend_ratio=blend_ratio)
        
        # 입 편집 (새로운 3가지 파라미터 사용)
        # 입술 영역 파라미터 결정 (개별 적용 여부에 따라, None이면 기본값 사용)
        # 기본값 설정
        default_padding_x = 0.2
        default_padding_y = 0.3
        default_offset_x = 0.0
        default_offset_y = 0.0
        
        if use_individual_lip_region:
            # 개별 적용 모드
            upper_padding_x = upper_lip_region_padding_x if upper_lip_region_padding_x is not None else default_padding_x
            upper_padding_y = upper_lip_region_padding_y if upper_lip_region_padding_y is not None else default_padding_y
            upper_offset_x = upper_lip_region_offset_x if upper_lip_region_offset_x is not None else default_offset_x
            upper_offset_y = upper_lip_region_offset_y if upper_lip_region_offset_y is not None else default_offset_y
            lower_padding_x = lower_lip_region_padding_x if lower_lip_region_padding_x is not None else default_padding_x
            lower_padding_y = lower_lip_region_padding_y if lower_lip_region_padding_y is not None else default_padding_y
            lower_offset_x = lower_lip_region_offset_x if lower_lip_region_offset_x is not None else default_offset_x
            lower_offset_y = lower_lip_region_offset_y if lower_lip_region_offset_y is not None else default_offset_y
        else:
            # 동기화 모드: 윗입술 값을 아래입술에 복사 (None이면 기본값 사용)
            upper_padding_x = upper_lip_region_padding_x if upper_lip_region_padding_x is not None else default_padding_x
            upper_padding_y = upper_lip_region_padding_y if upper_lip_region_padding_y is not None else default_padding_y
            upper_offset_x = upper_lip_region_offset_x if upper_lip_region_offset_x is not None else default_offset_x
            upper_offset_y = upper_lip_region_offset_y if upper_lip_region_offset_y is not None else default_offset_y
            lower_padding_x = upper_padding_x  # 윗입술 값 복사
            lower_padding_y = upper_padding_y
            lower_offset_x = upper_offset_x
            lower_offset_y = upper_offset_y
        
        # 1. 윗입술 모양 조정 (두께)
        if abs(upper_lip_shape - 1.0) >= 0.01:
            result = adjust_upper_lip_shape(result, upper_lip_shape, landmarks,
                                          upper_padding_x, upper_padding_y, upper_offset_x, upper_offset_y)
        
        # 2. 아랫입술 모양 조정 (두께)
        if abs(lower_lip_shape - 1.0) >= 0.01:
            result = adjust_lower_lip_shape(result, lower_lip_shape, landmarks,
                                          lower_padding_x, lower_padding_y, lower_offset_x, lower_offset_y)
        
        # 3. 윗입술 너비 조정
        if abs(upper_lip_width - 1.0) >= 0.01:
            result = adjust_upper_lip_width(result, upper_lip_width, landmarks,
                                          upper_padding_x, upper_padding_y, upper_offset_x, upper_offset_y)
        
        # 4. 아랫입술 너비 조정
        if abs(lower_lip_width - 1.0) >= 0.01:
            result = adjust_lower_lip_width(result, lower_lip_width, landmarks,
                                          lower_padding_x, lower_padding_y, lower_offset_x, lower_offset_y)
        
        # 5. 입술 수직 이동 조정
        if abs(upper_lip_vertical_move) >= 0.1 or abs(lower_lip_vertical_move) >= 0.1:
            result = adjust_lip_vertical_move(result, upper_lip_vertical_move, lower_lip_vertical_move, landmarks,
                                             upper_padding_x, upper_padding_y,
                                             lower_padding_x, lower_padding_y,
                                             upper_offset_x, upper_offset_y,
                                             lower_offset_x, lower_offset_y)
        
        # 기존 입 편집 함수는 호환성을 위해 유지 (새 파라미터가 없을 때만 사용)
        if upper_lip_shape == 1.0 and lower_lip_shape == 1.0 and abs(upper_lip_vertical_move) < 0.1 and abs(lower_lip_vertical_move) < 0.1:
            if use_individual_lip_region:
                # 개별 적용 모드: 윗입술과 아래입술 각각 편집
                result = adjust_upper_lip_size(result, upper_lip_size, upper_lip_width, landmarks, blend_ratio=blend_ratio)
                result = adjust_lower_lip_size(result, lower_lip_size, lower_lip_width, landmarks, blend_ratio=blend_ratio)
            elif abs(mouth_size - 1.0) >= 0.01 or abs(mouth_width - 1.0) >= 0.01:
                # 통합 모드: 입 전체 편집
                result = adjust_mouth_size(result, mouth_size, mouth_width, landmarks, blend_ratio=blend_ratio)
        
        result = adjust_jaw(result, jaw_adjustment, landmarks)
        result = adjust_face_size(result, face_width, face_height, landmarks, blend_ratio=blend_ratio)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return image
