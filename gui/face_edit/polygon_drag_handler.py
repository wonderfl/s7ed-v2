"""
얼굴 편집 패널 - 폴리곤 드래그 처리 Mixin
폴리곤 포인트 드래그 이벤트 처리를 담당
"""
import numpy as np
import math

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
from utils.logger import print_info, print_debug, print_error, print_warning
from PIL import Image, ImageDraw, ImageFilter


def clamp_iris_position(center, eye_landmarks, margin_ratio=0.3):
    """눈동자 위치를 눈 랜드마크 내로 클램핑"""
    if center is None or not eye_landmarks:
        return center
    
    x, y = center
    
    # 눈 랜드마크에서 경계 계산
    eye_x = [pt[0] for pt in eye_landmarks]
    eye_y = [pt[1] for pt in eye_landmarks]
    
    min_x, max_x = min(eye_x), max(eye_x)
    min_y, max_y = min(eye_y), max(eye_y)
    
    # 마진 적용
    width = max_x - min_x
    height = max_y - min_y
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio
    
    # 클램핑
    clamped_x = max(min_x + margin_x, min(x, max_x - margin_x))
    clamped_y = max(min_y + margin_y, min(y, max_y - margin_y))
    
    return (clamped_x, clamped_y)


def crop_eye_region(image, eye_landmarks, padding=20):
    """눈 영역 크롭"""
    if image is None or not eye_landmarks:
        return None, None, None
    
    # 눈 랜드마크 경계 계산
    eye_x = [pt[0] for pt in eye_landmarks]
    eye_y = [pt[1] for pt in eye_landmarks]
    
    min_x, max_x = min(eye_x), max(eye_x)
    min_y, max_y = min(eye_y), max(eye_y)
    
    # 패딩 추가
    crop_x1 = max(0, int(min_x - padding))
    crop_y1 = max(0, int(min_y - padding))
    crop_x2 = min(image.width, int(max_x + padding))
    crop_y2 = min(image.height, int(max_y + padding))
    
    # 눈 영역 크롭
    eye_region = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    
    # 오프셋 정보
    offset_x = crop_x1
    offset_y = crop_y1
    
    return eye_region, offset_x, offset_y


def detect_precise_iris(image, eye_landmarks):
    """정교한 눈동자 감지 (색상 기반)"""
    if image is None or not eye_landmarks:
        return None, None, None
    
    # 눈 영역 계산
    eye_x = [pt[0] for pt in eye_landmarks]
    eye_y = [pt[1] for pt in eye_landmarks]
    min_x, max_x = min(eye_x), max(eye_x)
    min_y, max_y = min(eye_y), max(eye_y)
    
    # 눈 영역 크롭 (여유 공간 포함)
    padding = 10
    crop_x1 = max(0, int(min_x - padding))
    crop_y1 = max(0, int(min_y - padding))
    crop_x2 = min(image.width, int(max_x + padding))
    crop_y2 = min(image.height, int(max_y + padding))
    
    eye_region = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    
    # numpy 배열로 변환
    eye_array = np.array(eye_region)
    
    # 눈동자 감지 (어두운 영역 찾기)
    gray = np.mean(eye_array, axis=2)
    
    # 어두운 픽셀 마스크 (상위 20% 어두운 픽셀)
    threshold = np.percentile(gray, 20)
    dark_mask = gray < threshold
    
    # 가장 큰 어두운 영역 찾기 (눈동자 후보)
    from scipy import ndimage
    labeled, num_features = ndimage.label(dark_mask)
    
    if num_features == 0:
        return None, None, None
    
    # 가장 큰 영역 선택
    sizes = ndimage.sum(dark_mask, labeled, range(num_features + 1))
    largest_label = np.argmax(sizes[1:]) + 1
    
    # 눈동자 중심 계산
    iris_mask = labeled == largest_label
    y_coords, x_coords = np.where(iris_mask)
    iris_center_x = int(np.mean(x_coords)) + crop_x1
    iris_center_y = int(np.mean(y_coords)) + crop_y1
    
    # 눈동자 반경 계산
    distances = np.sqrt((x_coords - np.mean(x_coords))**2 + (y_coords - np.mean(y_coords))**2)
    iris_radius = int(np.percentile(distances, 90))  # 90% 지점을 반경으로
    
    return (iris_center_x, iris_center_y), iris_radius, eye_region


def extract_iris_image(image, eye_landmarks, iris_size=15):
    """진짜 눈동자만 추출 - 눈이 아닌 눈동자"""
    if image is None or not eye_landmarks:
        return None, None
    
    # 눈 중심 계산
    eye_x = [pt[0] for pt in eye_landmarks]
    eye_y = [pt[1] for pt in eye_landmarks]
    center_x = sum(eye_x) / len(eye_x)
    center_y = sum(eye_y) / len(eye_y)
    
    # 눈동자만 작게 크롭 (눈이 아닌 눈동자만)
    iris_only_size = 12  # 눈동자만의 크기 (작게)
    
    # 눈동자만 영역 크롭
    x1 = max(0, int(center_x - iris_only_size))
    y1 = max(0, int(center_y - iris_only_size))
    x2 = min(image.width, int(center_x + iris_only_size))
    y2 = min(image.height, int(center_y + iris_only_size))
    
    iris_image = image.crop((x1, y1, x2, y2))
    
    # 눈동자만 마스크 (작고 완벽한 원)
    mask = Image.new('L', iris_image.size, 0)
    draw = ImageDraw.Draw(mask)
    center = (iris_image.width // 2, iris_image.height // 2)
    radius = iris_only_size - 1  # 작은 반경 (눈동자만)
    
    # 완벽한 작은 원 (눈동자만)
    draw.ellipse([center[0]-radius, center[1]-radius, 
                  center[0]+radius, center[1]+radius], fill=255)
    
    return iris_image, mask


def simple_iris_morph(image, left_center, right_center, left_eye_landmarks=None, right_eye_landmarks=None):
    """간단한 눈동자 이동 - 복잡한 거 다 버림"""
    if image is None:
        return None
    
    # PIL 이미지로 변환
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)
    
    # 이미지 복사
    result = image.copy()
    draw = ImageDraw.Draw(result)
    
    # 왼쪽 눈동자 (그냥 검은 원)
    if left_center:
        x, y = int(left_center[0]), int(left_center[1])
        draw.ellipse([x-10, y-10, x+10, y+10], fill='black')
    
    # 오른쪽 눈동자 (그냥 검은 원)
    if right_center:
        x, y = int(right_center[0]), int(right_center[1])
        draw.ellipse([x-10, y-10, x+10, y+10], fill='black')
    
    return result


class PolygonDragHandlerMixin:
    """폴리곤 드래그 처리 기능 Mixin"""
    
    def on_polygon_drag_start(self, event, landmark_index, canvas_obj):
        """폴리곤에서 포인트를 찾아서 드래그 시작"""
        # 드래그 시작 시 확대/축소 플래그 해제
        if hasattr(self, '_skip_morphing_change'):
            self._skip_morphing_change = False
        
        # 고급 모드가 아니어도 드래그 가능
        # 드래그 종료 시 자동으로 고급 모드로 변형 적용
        
        # 폴리곤에서 포인트를 찾았을 때 바로 드래그 모드로 진입
        self.dragging_polygon = True
        self.dragged_polygon_index = landmark_index
        self.dragged_polygon_canvas = canvas_obj
        
        # 드래그 시작 위치 저장
        self.polygon_drag_start_x = event.x
        self.polygon_drag_start_y = event.y
        
        # 이미지 드래그 시작 플래그 초기화 (이미지 드래그 방지)
        if canvas_obj == self.canvas_original:
            self.canvas_original_drag_start_x = None
            self.canvas_original_drag_start_y = None
        else:
            self.canvas_edited_drag_start_x = None
            self.canvas_edited_drag_start_y = None
        
        # 현재 랜드마크의 이미지 좌표 계산 - LandmarkManager 사용
        if canvas_obj == self.canvas_original:
            if self.current_image is None:
                return
            img = self.current_image
            # 랜드마크 가져오기 (커스텀 또는 원본) - LandmarkManager 사용
            custom = self.landmark_manager.get_custom_landmarks()
            face = self.landmark_manager.get_face_landmarks()
            if custom is not None:
                landmarks = custom
            elif face is not None:
                landmarks = face
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if landmarks is None:
                    return
                self.landmark_manager.set_face_landmarks(landmarks)
                self.face_landmarks = self.landmark_manager.get_face_landmarks()
                # 원본 랜드마크도 저장 (이미지 크기와 함께 바운딩 박스 계산하여 캐싱)
                if not self.landmark_manager.has_original_landmarks():
                    img_width, img_height = img.size
                    self.landmark_manager.set_original_landmarks(landmarks, img_width, img_height)
                    self.original_landmarks = self.landmark_manager.get_original_landmarks()
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            if self.edited_image is None:
                return
            img = self.edited_image
            # 편집된 이미지의 랜드마크는 커스텀 랜드마크 사용 - LandmarkManager 사용
            custom = self.landmark_manager.get_custom_landmarks()
            if custom is not None:
                landmarks = custom
            else:
                landmarks, _ = face_landmarks.detect_face_landmarks(self.edited_image)
                if landmarks is None:
                    return
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if landmarks is None or landmark_index >= len(landmarks):
            return
        
        self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = landmarks[landmark_index]
        
        # 커스텀 랜드마크 초기화 (처음 드래그할 때) - LandmarkManager 사용
        # 주의: custom_landmarks가 없을 때만 초기화 (사이즈 변환이 이미 적용된 상태 보존)
        # 사이즈 변경 후 드래그 시 사이즈 변환이 반복 적용되는 문제 방지:
        # - custom_landmarks가 이미 있으면 그대로 사용 (사이즈 변환 포함)
        # - custom_landmarks가 없으면 transformed_landmarks 또는 원본으로 초기화
        custom = self.landmark_manager.get_custom_landmarks()
        if custom is None:
            # custom_landmarks가 없으면 transformed_landmarks 우선 사용 (사이즈 변환 포함)
            transformed = self.landmark_manager.get_transformed_landmarks()
            if transformed is not None:
                # transformed_landmarks는 set_transformed_landmarks로 직접 참조로 저장되므로,
                # custom_landmarks에 직접 참조로 저장하면 같은 리스트를 공유하게 되어 수정 시 transformed_landmarks도 변경됨
                # 따라서 복사본이 필요함 (custom_landmarks는 수정 가능해야 함)
                self.landmark_manager.set_custom_landmarks(list(transformed), reason="on_polygon_drag_start")
            else:
                # transformed_landmarks가 없으면 원본 얼굴 랜드마크 사용
                original_face = self.landmark_manager.get_original_face_landmarks()
                if original_face is not None:
                    # 원본을 복사본으로 설정 (변환 적용을 위해)
                    self.landmark_manager.set_custom_landmarks(list(original_face), reason="on_polygon_drag_start")
                elif landmarks is not None:
                    # 원본이 없으면 현재 landmarks 사용
                    self.landmark_manager.set_custom_landmarks(list(landmarks) if landmarks is not None else None, reason="on_polygon_drag_start")
        
        # 선택된 포인트 표시 (큰 원으로 강조)
        self._draw_selected_landmark_indicator(canvas_obj, landmark_index, event.x, event.y)
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_polygon_drag(self, event, landmark_index, canvas_obj):
        """폴리곤에서 찾은 포인트 드래그 중"""
        # 포인트가 선택되어 있고 드래그 중인 경우에만 처리
        if not self.dragging_polygon or self.dragged_polygon_index != landmark_index:
            return
        
        # 중앙 포인트 드래그의 경우 ('left' 또는 'right' 문자열)
        if isinstance(landmark_index, str):
            # on_iris_center_drag로 위임
            self.on_iris_center_drag(event, landmark_index, canvas_obj)
            return
        
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is None:
            return
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            # display_size가 없으면 이미지 크기 사용
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 좌표를 이미지 좌표로 변환
        # 이미지 중심이 pos_x, pos_y에 있으므로
        rel_x = (event.x - pos_x) / scale_x
        rel_y = (event.y - pos_y) / scale_y
        img_x = img_width / 2 + rel_x
        img_y = img_height / 2 + rel_y
        
        # 이미지 경계 내로 제한
        img_x = max(0, min(img_width - 1, img_x))
        img_y = max(0, min(img_height - 1, img_y))
        
        # 랜드마크 위치 업데이트
        # landmark_index가 정수인지 확인 (중앙 포인트 드래그의 경우 'left'/'right' 문자열일 수 있음)
        if isinstance(landmark_index, int) and landmark_index >= 0:
            # 이전 위치 가져오기 (디버깅용)
            old_pos = None
            custom = self.landmark_manager.get_custom_landmarks()
            if custom is not None and landmark_index < len(custom):
                old_pos = custom[landmark_index]
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(landmark_index, (img_x, img_y))
                self.landmark_manager.mark_as_dragged(landmark_index)
            
            # 선택된 포인트 표시 업데이트
            self._update_selected_landmark_indicator(canvas_obj, event.x, event.y)
        elif isinstance(landmark_index, str):
            # 중앙 포인트 드래그의 경우 ('left' 또는 'right') - on_iris_center_drag에서 처리됨
            # 이미 위에서 on_iris_center_drag로 위임했으므로 여기서는 처리하지 않음
            pass
        
        # 성능 최적화: 드래그 중에는 실시간 미리보기 비활성화
        # 드래그 종료 시에만 최종 편집 적용
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_polygon_drag_end(self, event, landmark_index, canvas_obj):
        """폴리곤에서 찾은 포인트 드래그 종료"""
        if not self.dragging_polygon or self.dragged_polygon_index != landmark_index:
            return
        
        # 드래그 종료 시 확대/축소 플래그 해제
        if hasattr(self, '_skip_morphing_change'):
            self._skip_morphing_change = False
        
        # 드래그 종료 시 항상 변형 적용
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        # 눈동자 중심점 드래그 여부 확인 (landmark_index가 'left' 또는 'right' 문자열)
        is_iris_center_drag = isinstance(landmark_index, str) and landmark_index in ('left', 'right')
        
        # 일반 랜드마크 드래그 또는 눈동자 중심점 드래그 모두 적용
        if custom is not None or is_iris_center_drag:
            self.apply_polygon_drag_final()
        
        # 마지막으로 선택한 포인트 인덱스 저장 (드래그 종료 후에도 유지)
        # landmark_index는 정수 또는 문자열('left'/'right')
        self.last_selected_landmark_index = landmark_index
        
        # 선택된 포인트 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 드래그 종료 시 플래그 초기화 (이미지 드래그 가능하도록)
        # 주의: 드래그 표시(_dragged_indices)는 유지 (슬라이더 변형 시 제외하기 위해)
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.dragged_polygon_canvas = None
        
        # 이벤트 전파 중단 (이미지 드래그 방지)
        return "break"
    
    def on_iris_center_drag_start(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 시작
        iris_side: 'left' 또는 'right' (좌표 기반)
        """
        print(f"[DEBUG] Starting iris drag: {iris_side} on {canvas_obj}")
        
        # 드래그 시작
        self.dragging_polygon = True
        self.dragged_polygon_index = iris_side  # 'left' 또는 'right' 저장
        self.dragged_polygon_canvas = canvas_obj
        
        print(f"[DEBUG] Set dragging_polygon=True, dragged_polygon_index={iris_side}")
        
        # 드래그 시작 위치 저장
        self.polygon_drag_start_x = event.x
        self.polygon_drag_start_y = event.y
        
        # 이미지 드래그 시작 플래그 초기화
        if canvas_obj == self.canvas_original:
            self.canvas_original_drag_start_x = None
            self.canvas_original_drag_start_y = None
        else:
            self.canvas_edited_drag_start_x = None
            self.canvas_edited_drag_start_y = None
        
        # 현재 이미지 가져오기
        if canvas_obj == self.canvas_original:
            if self.current_image is None:
                return
            img = self.current_image
        else:
            if self.edited_image is None:
                return
            img = self.edited_image
        
        # 중앙 포인트 좌표 가져오기
        if iris_side == 'left' and hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None:
            self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = self._left_iris_center_coord
            start_center = self._left_iris_center_coord
        elif iris_side == 'right' and hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None:
            self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = self._right_iris_center_coord
            start_center = self._right_iris_center_coord
        else:
            # 좌표가 없으면 original_landmarks에서 계산
            original = self.landmark_manager.get_original_landmarks_full()
            
            if original is not None:
                img_width, img_height = img.size
                left_iris_indices, right_iris_indices = self._get_iris_indices()
                if iris_side == 'left':
                    center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                else:
                    center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                if center is not None:
                    self.polygon_drag_start_img_x, self.polygon_drag_start_img_y = center
                    start_center = center
                else:
                    return
            else:
                return
        
        # 드래그 시작 로그
        print_info("얼굴편집", f"중심점 드래그 시작 ({iris_side}): 시작 좌표=({self.polygon_drag_start_img_x:.1f}, {self.polygon_drag_start_img_y:.1f})")
        
        # 눈동자 중심점 드래그임을 명확히 표시 (apply_polygon_drag_final에서 감지용)
        self.last_selected_landmark_index = iris_side  # 'left' 또는 'right'
        
        # 선택된 포인트 표시
        self._draw_selected_landmark_indicator(canvas_obj, None, event.x, event.y)
        
        return "break"
    
    def on_iris_center_drag(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 중
        iris_side: 'left' 또는 'right' (좌표 기반)
        """
        if not self.dragging_polygon or self.dragged_polygon_index != iris_side:
            return
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 좌표를 이미지 좌표로 변환
        rel_x = (event.x - pos_x) / scale_x
        rel_y = (event.y - pos_y) / scale_y
        new_center_x = img_width / 2 + rel_x
        new_center_y = img_height / 2 + rel_y
        
        # 이미지 경계 내로 제한
        new_center_x = max(0, min(img_width - 1, new_center_x))
        new_center_y = max(0, min(img_height - 1, new_center_y))
        
        # 중앙 포인트 좌표 업데이트
        # custom_landmarks의 배열 끝 인덱스도 직접 업데이트 (방법 A)
        custom = self.landmark_manager.get_custom_landmarks()
        
        if custom is not None and len(custom) >= 2:
            # 계산된 중앙 포인트 인덱스: 
            # custom_landmarks에는 눈동자 포인트가 제거되고 중앙 포인트가 추가되어 있음
            # landmarks[468] = LEFT_EYE_INDICES에서 계산된 중심
            # landmarks[469] = RIGHT_EYE_INDICES에서 계산된 중심
            
            if iris_side == 'left':
                # UI Left → landmarks[469] = len(custom)-1
                right_idx = len(custom) - 1
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(right_idx, (new_center_x, new_center_y))
                left_center_current = self.landmark_manager.get_left_iris_center_coord()
                self.landmark_manager.set_iris_center_coords(
                    left_center_current,
                    (new_center_x, new_center_y)
                )
            elif iris_side == 'right':
                # UI Right → landmarks[468] = len(custom)-2
                left_idx = len(custom) - 2
                # LandmarkManager를 통해서만 수정 (직접 참조로 수정)
                self.landmark_manager.update_custom_landmark(left_idx, (new_center_x, new_center_y))
                right_center_current = self.landmark_manager.get_right_iris_center_coord()
                self.landmark_manager.set_iris_center_coords(
                    (new_center_x, new_center_y),
                    right_center_current
                )
        else:
            # custom_landmarks가 없거나 길이가 부족한 경우
            # face_landmarks를 가져와서 중앙 포인트를 추가한 custom_landmarks 생성
            face_landmarks_list = self.landmark_manager.get_face_landmarks()
            # face_landmarks가 None이면 원본 랜드마크 사용
            if face_landmarks_list is None:
                face_landmarks_list = self.landmark_manager.get_original_face_landmarks()
            
            if face_landmarks_list is not None:
                # face_landmarks에 중앙 포인트 추가 (470개 구조)
                custom = list(face_landmarks_list)
                if iris_side == 'left':
                    left_center = (new_center_x, new_center_y)
                    right_center = self.landmark_manager.get_right_iris_center_coord()
                else:
                    left_center = self.landmark_manager.get_left_iris_center_coord()
                    right_center = (new_center_x, new_center_y)
                
                # 중앙 포인트가 하나라도 있으면 custom_landmarks 생성
                if left_center is not None or right_center is not None:
                    # None인 중앙 포인트는 원본에서 계산
                    if left_center is None:
                        left_center = self.landmark_manager.get_original_left_iris_center_coord()
                    if right_center is None:
                        right_center = self.landmark_manager.get_original_right_iris_center_coord()
                    
                    # 원본도 없으면 original_iris_landmarks에서 계산
                    if left_center is None or right_center is None:
                        original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                        if original_iris_landmarks is not None and len(original_iris_landmarks) == 10:
                            left_iris_points = original_iris_landmarks[:5]
                            right_iris_points = original_iris_landmarks[5:]
                            if left_center is None and left_iris_points:
                                left_center = (
                                    sum(p[0] for p in left_iris_points) / len(left_iris_points),
                                    sum(p[1] for p in left_iris_points) / len(left_iris_points)
                                )
                            if right_center is None and right_iris_points:
                                right_center = (
                                    sum(p[0] for p in right_iris_points) / len(right_iris_points),
                                    sum(p[1] for p in right_iris_points) / len(right_iris_points)
                                )
                    
                    if left_center is not None and right_center is not None:
                        custom.append(left_center)
                        custom.append(right_center)
                        self.landmark_manager.set_custom_landmarks(custom, reason="on_iris_center_drag_create")
                        self.landmark_manager.set_iris_center_coords(left_center, right_center)
        
        # 눈동자 중심점 드래그 중에는 선택된 포인트 표시 업데이트를 하지 않음 (자취 방지)
        # 일반 랜드마크 드래그와 달리 눈동자 중심점은 별도로 처리됨
        # self._update_selected_landmark_indicator(canvas_obj, event.x, event.y)  # 주석 처리
        
        # 드래그 중에 중심점 실시간 업데이트
        try:
            # iris_center 태그를 가진 모든 아이템 찾기
            iris_centers = canvas_obj.find_withtag("iris_center")
            for center_id in iris_centers:
                # 해당 iris_side의 중심점만 업데이트
                tags = canvas_obj.gettags(center_id)
                if f"iris_center_{iris_side}" in tags:
                    # 중심점 위치 업데이트
                    center_radius = 5
                    canvas_obj.coords(
                        center_id,
                        event.x - center_radius,
                        event.y - center_radius,
                        event.x + center_radius,
                        event.y + center_radius
                    )
                    # 중심점을 최상위로 올리기
                    canvas_obj.tag_raise(center_id)
                    print(f"[DEBUG] Updated iris center position: {iris_side} at ({event.x}, {event.y})")
                    break
            
            # 드래그 중에 연결선 실시간 업데이트
            self._update_iris_connections_during_drag(canvas_obj, iris_side, event.x, event.y)
            
        except Exception as e:
            print(f"[DEBUG] Error updating iris center position: {e}")
        
        return "break"
    
    def _update_iris_connections_during_drag(self, canvas_obj, iris_side, center_x, center_y):
        """드래그 중에 연결선 실시간 업데이트"""
        try:
            # iris_connections 태그를 가진 모든 연결선 찾기
            connection_lines = canvas_obj.find_withtag("iris_connections")
            
            # 해당 iris_side의 연결선만 업데이트
            for line_id in connection_lines:
                tags = canvas_obj.gettags(line_id)
                if any(f"iris_connection_{iris_side}_" in tag for tag in tags):
                    # 연결선의 끝점을 중심점 위치로 업데이트
                    coords = canvas_obj.coords(line_id)
                    if len(coords) == 4:  # 선은 4개 좌표 (x1, y1, x2, y2)
                        # 첫 번째 점을 중심점 위치로 업데이트 (두 번째 점은 외곽점)
                        canvas_obj.coords(line_id, center_x, center_y, coords[2], coords[3])
            
            # 외곽선도 업데이트
            outline_lines = canvas_obj.find_withtag(f"iris_outline_{iris_side}")
            for line_id in outline_lines:
                # 외곽선은 현재 위치를 유지 (중심점이 아니라 외곽점들로 구성)
                pass
            
            print(f"[DEBUG] Updated iris connections for {iris_side} during drag")
            
        except Exception as e:
            print(f"[DEBUG] Error updating iris connections: {e}")
    
    def on_iris_center_drag_end(self, event, iris_side, canvas_obj):
        """눈동자 중앙 포인트 드래그 종료"""
        if not self.dragging_polygon or self.dragged_polygon_index != iris_side:
            return
        
        # 드래그 종료 시 최종 좌표 확인
        final_left = self.landmark_manager.get_left_iris_center_coord()
        final_right = self.landmark_manager.get_right_iris_center_coord()
        print_info("얼굴편집", f"중심점 드래그 종료 ({iris_side}): 최종 좌표 - left={final_left}, right={final_right}")
        
        # 드래그 종료 시 항상 변형 적용
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        # custom_landmarks가 None이어도 중앙 포인트가 설정되어 있으면 적용
        # (on_iris_center_drag에서 custom_landmarks를 생성했을 수 있음)
        if custom is not None or final_left is not None or final_right is not None:
            self.apply_polygon_drag_final()
        
        # 선택된 포인트 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 드래그 종료 시 플래그 초기화
        self.dragging_polygon = False
        self.dragged_polygon_index = None
        self.dragged_polygon_canvas = None
        
        # 폴리곤 표시가 활성화되어 있으면 폴리곤 다시 그리기
        if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'update_face_features_display'):
                self.update_face_features_display()
        
        return "break"
    
    def apply_polygon_drag_preview(self):
        """폴리곤 드래그 중 실시간 미리보기 (현재 비활성화: 성능 최적화)"""
        # 성능 최적화: 드래그 중에는 실시간 미리보기 비활성화
        # 드래그 종료 시에만 최종 편집 적용
        pass
    
    def _move_iris_only(self, image, left_center_orig, right_center_orig, left_center_new, right_center_new):
        """눈동자 영역만 이동 (머리 변형 없이)
        
        Args:
            image: PIL.Image - 원본 이미지
            left_center_orig: tuple - 원본 왼쪽 눈동자 중심 좌표 (x, y)
            right_center_orig: tuple - 원본 오른쪽 눈동자 중심 좌표 (x, y)
            left_center_new: tuple - 새로운 왼쪽 눈동자 중심 좌표 (x, y)
            right_center_new: tuple - 새로운 오른쪽 눈동자 중심 좌표 (x, y)
        
        Returns:
            PIL.Image - 눈동자가 이동된 이미지
        """
        import numpy as np
        from PIL import Image
        import cv2
        
        # PIL 이미지를 numpy 배열로 변환
        img_array = np.array(image)
        result = img_array.copy()
        
        # 눈동자 반지름 추정 (눈 크기의 약 40%)
        img_width, img_height = image.size
        iris_radius = int(min(img_width, img_height) * 0.04)  # 이미지 크기의 4%
        
        # 각 눈동자 이동 처리
        for center_orig, center_new in [(left_center_orig, left_center_new), 
                                         (right_center_orig, right_center_new)]:
            if center_orig is None or center_new is None:
                continue
            
            # 이동 거리 계산
            dx = center_new[0] - center_orig[0]
            dy = center_new[1] - center_orig[1]
            
            # 이동 거리가 너무 작으면 건너뜀
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                continue
            
            print_info("얼굴편집", f"눈동자 이동: 원본={center_orig}, 새위치={center_new}, 이동=({dx:.1f}, {dy:.1f})")
            
            # 원형 마스크 생성 (원본 위치)
            y_coords, x_coords = np.ogrid[:img_height, :img_width]
            mask = ((x_coords - center_orig[0])**2 + (y_coords - center_orig[1])**2) <= iris_radius**2
            
            # 부드러운 경계를 위한 그라디언트 마스크
            distance = np.sqrt((x_coords - center_orig[0])**2 + (y_coords - center_orig[1])**2)
            soft_mask = np.clip(1.0 - (distance - iris_radius * 0.7) / (iris_radius * 0.3), 0, 1)
            
            # 원본 눈동자 영역 추출
            iris_region = img_array[mask].copy()
            
            # 새로운 위치에 마스크 생성
            new_mask = ((x_coords - center_new[0])**2 + (y_coords - center_new[1])**2) <= iris_radius**2
            new_distance = np.sqrt((x_coords - center_new[0])**2 + (y_coords - center_new[1])**2)
            new_soft_mask = np.clip(1.0 - (new_distance - iris_radius * 0.7) / (iris_radius * 0.3), 0, 1)
            
            # 원본 위치의 눈동자를 주변 색상으로 inpaint (간단한 블러)
            # 원형 영역을 주변 픽셀로 채움
            for c in range(3):  # RGB 채널
                # 원형 영역 주변의 평균 색상으로 채움
                border_mask = ((distance >= iris_radius * 0.9) & (distance <= iris_radius * 1.2))
                if border_mask.any():
                    avg_color = np.mean(img_array[border_mask, c])
                    result[mask, c] = result[mask, c] * (1 - soft_mask[mask]) + avg_color * soft_mask[mask]
            
            # 새로운 위치에 눈동자 그리기
            if new_mask.any() and len(iris_region) > 0:
                # 원본과 새 위치의 마스크 크기 확인
                orig_count = mask.sum()
                new_count = new_mask.sum()
                min_count = min(orig_count, new_count)
                
                # 크기가 다르면 작은 쪽에 맞춤
                if orig_count == new_count:
                    # 크기가 같으면 직접 할당
                    result[new_mask] = result[new_mask] * (1 - new_soft_mask[new_mask, np.newaxis]) + \
                                       iris_region * new_soft_mask[new_mask, np.newaxis]
                else:
                    # 크기가 다르면 min_count만큼만 처리
                    new_mask_indices = np.where(new_mask)
                    for i in range(min_count):
                        y, x = new_mask_indices[0][i], new_mask_indices[1][i]
                        alpha = new_soft_mask[y, x]
                        result[y, x] = result[y, x] * (1 - alpha) + iris_region[i] * alpha
        
        # numpy 배열을 PIL 이미지로 변환
        result_image = Image.fromarray(result.astype(np.uint8))
        return result_image
    
    def apply_polygon_drag_final(self, force_slider_mode=False):
        """폴리곤 드래그 종료 시 최종 편집 적용
        
        Args:
            force_slider_mode: (사용 안 함, 하위 호환성 유지용)
        """
        # custom_landmarks 확인 (LandmarkManager 사용)
        custom = self.landmark_manager.get_custom_landmarks()
        
        # 중앙 포인트가 설정되어 있으면 custom_landmarks가 None이어도 적용
        left_center = self.landmark_manager.get_left_iris_center_coord()
        right_center = self.landmark_manager.get_right_iris_center_coord()
        has_iris_centers = left_center is not None or right_center is not None
        
        if (custom is None and not has_iris_centers) or self.current_image is None:
            return
        
        # custom_landmarks가 None이면 원본 랜드마크를 사용 (중앙 포인트만 변경된 경우)
        if custom is None:
            original_face = self.landmark_manager.get_original_face_landmarks()
            if original_face is not None:
                custom = list(original_face)  # 복사본 생성
                self.landmark_manager.set_custom_landmarks(custom, reason="apply_polygon_drag_final: 중앙 포인트만 변경")
        
        try:
            # 원본 랜드마크 가져오기 (LandmarkManager 사용)
            if not self.landmark_manager.has_original_landmarks():
                original_landmarks, _ = face_landmarks.detect_face_landmarks(self.current_image)
                if original_landmarks is None:
                    print_warning("얼굴편집", "원본 랜드마크 감지 실패")
                    return
                # 이미지 크기와 함께 바운딩 박스 계산하여 캐싱
                img_width, img_height = self.current_image.size
                self.landmark_manager.set_original_landmarks(original_landmarks, img_width, img_height)
                self.original_landmarks = self.landmark_manager.get_original_landmarks()
            else:
                original_landmarks = self.landmark_manager.get_original_landmarks()
            
            # 슬라이더로 변형된 랜드마크가 있으면 그것을 기준으로 사용
            # custom_landmarks는 슬라이더 변형 + 드래그 변형이 모두 적용된 상태
            # 이미지 변형 시에는 원본 랜드마크를 기준으로 custom_landmarks를 사용
            
            # 디버깅: 변형된 랜드마크 확인
            changed_indices = []
            for i in range(min(len(original_landmarks), len(self.custom_landmarks))):
                orig = original_landmarks[i]
                custom = self.custom_landmarks[i]
                diff = ((custom[0] - orig[0])**2 + (custom[1] - orig[1])**2)**0.5
                if diff > 0.1:
                    changed_indices.append((i, diff))
            
            if hasattr(self, 'last_selected_landmark_index') and self.last_selected_landmark_index is not None:
                last_idx = self.last_selected_landmark_index
                # 중앙 포인트 드래그의 경우 'left'/'right' 문자열이므로 정수 체크 필요
                if isinstance(last_idx, int) and last_idx >= 0:
                    # custom_landmarks 가져오기 (LandmarkManager 사용)
                    custom = self.landmark_manager.get_custom_landmarks()
                    
                    if custom is not None and last_idx < len(original_landmarks) and last_idx < len(custom):
                        orig_pos = original_landmarks[last_idx]
                        custom_pos = custom[last_idx]
                        diff = ((custom_pos[0] - orig_pos[0])**2 + (custom_pos[1] - orig_pos[1])**2)**0.5
                        print_info("얼굴편집", f"마지막 선택 포인트 인덱스 {last_idx}: 원본=({orig_pos[0]:.1f}, {orig_pos[1]:.1f}), 변형=({custom_pos[0]:.1f}, {custom_pos[1]:.1f}), 거리={diff:.1f}픽셀")
                elif isinstance(last_idx, str):
                    # 중앙 포인트 드래그의 경우 ('left' 또는 'right')
                    print_info("얼굴편집", f"마지막 선택 포인트: 중앙 포인트 ({last_idx})")
            
            # 마지막으로 선택한 포인트 인덱스 확인
            last_selected_index = getattr(self, 'last_selected_landmark_index', None)
            # iris_center_only 플래그는 morph_face_by_polygons에서 사용되지 않으므로 제거
            # iris_mapping_method 파라미터만으로 충분히 구분 가능
            
            # 드래그된 포인트 백업 (슬라이더 적용 전에 저장)
            dragged_indices = self.landmark_manager.get_dragged_indices()
            dragged_points_backup = {}
            if dragged_indices:
                custom_before_sliders = self.landmark_manager.get_custom_landmarks()
                if custom_before_sliders is not None:
                    # custom_landmarks가 470개인 경우 마지막 2개 제외하고 백업
                    max_idx = 468 if len(custom_before_sliders) == 470 else len(custom_before_sliders)
                    for idx in dragged_indices:
                        if 0 <= idx < max_idx:
                            dragged_points_backup[idx] = custom_before_sliders[idx]  # 튜플 복사 (좌표값만)
            
            # 공통 슬라이더 적용 (morph_face_by_polygons 호출 전에 custom_landmarks 변환)
            # 옵션 변경 시(force_slider_mode=False)에는 슬라이더 적용 건너뛰기
            # _apply_common_sliders_to_landmarks가 custom_landmarks를 변환하므로 먼저 호출
            
            # 옵션 변경 시가 아니면 슬라이더 적용
            if force_slider_mode != False:
                if hasattr(self, '_apply_common_sliders'):
                    # _apply_common_sliders는 _apply_common_sliders_to_landmarks를 호출하여 custom_landmarks를 변환
                    # base_image를 전달하여 슬라이더가 모두 기본값일 때 원본으로 복원할 수 있도록 함
                    base_image = self.aligned_image if hasattr(self, 'aligned_image') and self.aligned_image is not None else self.current_image
                    temp_result = self._apply_common_sliders(self.current_image, base_image=base_image)
                
                # 드래그된 포인트 복원 (슬라이더 적용 후에도 드래그 변경 보존)
                # 직접 참조를 유지하면서 드래그된 포인트만 복원
                if dragged_points_backup:
                    custom_after_sliders = self.landmark_manager.get_custom_landmarks()
                    if custom_after_sliders is not None:
                        # custom_landmarks가 470개인 경우 마지막 2개는 중앙 포인트이므로 제외하고 복원
                        max_idx = 468 if len(custom_after_sliders) == 470 else len(custom_after_sliders)
                        restored_count = 0
                        for idx, backup_pos in dragged_points_backup.items():
                            if 0 <= idx < max_idx:
                                # 직접 참조를 통해 수정 (복사본 생성 없음)
                                custom_after_sliders[idx] = backup_pos
                                restored_count += 1
                        
                        # LandmarkManager는 직접 참조를 저장하므로 변경사항이 이미 반영됨
                        # 하지만 명시적으로 저장하여 변경 이력 기록
                        # set_custom_landmarks는 직접 참조를 그대로 저장하므로 복사본 생성 안 함
                        self.landmark_manager.set_custom_landmarks(custom_after_sliders, reason="드래그 포인트 복원")
                
                if temp_result is not None:
                    # custom_landmarks가 변환되었으므로 다시 확인
                    changed_indices_after = []
                    # custom_landmarks 가져오기 (LandmarkManager 사용)
                    custom = self.landmark_manager.get_custom_landmarks()
                    
                    if custom is not None:
                        # custom_landmarks가 470개인 경우 마지막 2개 제외
                        custom_for_check = custom[:468] if len(custom) == 470 else custom
                        for i in range(min(len(original_landmarks), len(custom_for_check))):
                            orig = original_landmarks[i]
                            custom_point = custom_for_check[i]
                            diff = ((custom_point[0] - orig[0])**2 + (custom_point[1] - orig[1])**2)**0.5
                            if diff > 0.1:
                                changed_indices_after.append((i, diff))
            
            # 슬라이더가 모두 기본값이고 랜드마크가 변형되지 않았는지 확인
            # 옵션 변경 시(force_slider_mode=False)에는 이 체크를 건너뛰고 항상 morph_face_by_polygons 호출
            if force_slider_mode != False:
                size_x = self.region_size_x.get()
                size_y = self.region_size_y.get()
                center_offset_x = self.region_center_offset_x.get()
                center_offset_y = self.region_center_offset_y.get()
                position_x = self.region_position_x.get()
                position_y = self.region_position_y.get()
                
                size_x_condition = abs(size_x - 1.0) >= 0.01
                size_y_condition = abs(size_y - 1.0) >= 0.01
                size_condition = size_x_condition or size_y_condition
                offset_x_condition = abs(center_offset_x) >= 0.1
                offset_y_condition = abs(center_offset_y) >= 0.1
                pos_x_condition = abs(position_x) >= 0.1
                pos_y_condition = abs(position_y) >= 0.1
                conditions_met = offset_x_condition or offset_y_condition or size_condition or pos_x_condition or pos_y_condition
            
            # custom_landmarks 가져오기 (랜드마크 변형 확인용)
            custom_for_check = self.landmark_manager.get_custom_landmarks()
            
            # 랜드마크가 변형되었는지 확인
            landmarks_changed = False
            if custom_for_check is not None:
                # custom_landmarks가 470개인 경우 중앙 포인트 2개를 제외한 468개만 비교
                custom_length = len(custom_for_check)
                compare_length = min(len(original_landmarks), custom_length)
                # 470개인 경우 마지막 2개는 중앙 포인트이므로 제외
                if custom_length == 470:
                    compare_length = 468
                
                if compare_length > 0:
                    for i in range(compare_length):
                        if i < len(original_landmarks) and i < len(custom_for_check):
                            orig = original_landmarks[i]
                            custom_point = custom_for_check[i]
                            diff = ((custom_point[0] - orig[0])**2 + (custom_point[1] - orig[1])**2)**0.5
                            if diff > 0.1:
                                landmarks_changed = True
                                break
                
                # 중앙 포인트도 확인 (custom_landmarks가 470개인 경우)
                if custom_length == 470:
                    left_center = self.landmark_manager.get_left_iris_center_coord()
                    right_center = self.landmark_manager.get_right_iris_center_coord()
                    if left_center is not None or right_center is not None:
                        # 중앙 포인트가 있으면 변형된 것으로 간주
                        landmarks_changed = True
            
            # result 초기화
            result = None
            
            # 슬라이더가 모두 기본값이고 랜드마크도 변형되지 않았으면 원본 이미지 반환
            # 옵션 변경 시(force_slider_mode=False)에는 이 체크를 건너뛰고 항상 morph_face_by_polygons 호출
            if force_slider_mode != False:
                if not conditions_met:
                    # 랜드마크가 변형되지 않았을 때만 custom_landmarks를 원본으로 복원
                    # (드래그로 변경한 랜드마크는 보존해야 함)
                    if not landmarks_changed:
                        # 슬라이더가 모두 기본값이고 랜드마크도 변형되지 않았으면 custom_landmarks를 원본으로 복원
                        original_face = self.landmark_manager.get_original_face_landmarks()
                        if original_face is not None:
                            self.landmark_manager.set_custom_landmarks(original_face, reason="슬라이더 초기화")
                        
                        result = base_image
                    else:
                        # 랜드마크는 변형되었지만 슬라이더는 기본값이므로 morph_face_by_polygons 호출
                        # custom_landmarks는 드래그로 변경된 상태를 유지해야 하므로 복원하지 않음
                        result = None  # 아래에서 morph_face_by_polygons 호출
            
            # result가 None이면 morph_face_by_polygons 호출
            if result is None:
                # 랜드마크 변형 적용 (원본 이미지와 원본 랜드마크를 기준으로)
                # 고급 모드 여부와 관계없이 Delaunay Triangulation 사용
                # 마지막으로 선택한 포인트 인덱스 전달 (인덱스 기반 직접 매핑을 위해)
                
                # 눈동자 중심점만 변경한 경우 (last_selected_index가 'left' 또는 'right')
                # custom_landmarks_for_morph를 원본으로 설정 (얼굴 랜드마크 468개는 고정)
                # 중앙 포인트만 파라미터로 전달하여 눈동자만 움직이게 함
                if isinstance(last_selected_index, str) and last_selected_index in ('left', 'right'):
                    # 원본 얼굴 랜드마크 사용 (468개, 중앙 포인트 제외)
                    original_face = self.landmark_manager.get_original_face_landmarks()
                    
                    if original_face is not None:
                        custom_landmarks_for_morph = list(original_face)  # 복사본 생성
                    else:
                        custom_landmarks_for_morph = self.landmark_manager.get_custom_landmarks()
                else:
                    # _apply_common_sliders 호출 후 custom_landmarks가 업데이트되었을 수 있으므로 다시 가져오기
                    custom_landmarks_for_morph = self.landmark_manager.get_custom_landmarks()
                
                # custom_landmarks가 470개인 경우 마지막 2개를 중앙 포인트로 추출하고 468개로 변환
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                
                # 디버깅: landmark_manager에서 가져온 중앙 포인트 확인
                print_info("얼굴편집", f"apply_polygon_drag_final: landmark_manager에서 가져온 중앙 포인트 - left={left_center}, right={right_center}")
                
                # 원본 중앙 포인트 가져오기 (landmark_manager에서 저장된 값 사용)
                left_center_orig = self.landmark_manager.get_original_left_iris_center_coord()
                right_center_orig = self.landmark_manager.get_original_right_iris_center_coord()
                
                # 디버깅: 원본 중앙 포인트 확인
                print_info("얼굴편집", f"apply_polygon_drag_final: 원본 중앙 포인트 - left_orig={left_center_orig}, right_orig={right_center_orig}")
                
                # 없으면 original_iris_landmarks에서 계산
                if left_center_orig is None or right_center_orig is None:
                    original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                    
                    if original_iris_landmarks is not None and len(original_iris_landmarks) == 10:
                        # 눈동자 랜드마크: 첫 5개와 다음 5개
                        first_iris_points = original_iris_landmarks[:5]
                        second_iris_points = original_iris_landmarks[5:]
                        
                        # x 좌표로 왼쪽/오른쪽 판단
                        if first_iris_points and second_iris_points:
                            first_center_x = sum(p[0] for p in first_iris_points) / len(first_iris_points)
                            second_center_x = sum(p[0] for p in second_iris_points) / len(second_iris_points)
                            
                            # x 좌표 비교
                            if first_center_x > second_center_x:
                                left_iris_points = first_iris_points
                                right_iris_points = second_iris_points
                            else:
                                left_iris_points = second_iris_points
                                right_iris_points = first_iris_points
                            
                            if left_center_orig is None:
                                left_center_orig = (
                                    sum(p[0] for p in left_iris_points) / len(left_iris_points),
                                    sum(p[1] for p in left_iris_points) / len(left_iris_points)
                                )
                            if right_center_orig is None:
                                right_center_orig = (
                                    sum(p[0] for p in right_iris_points) / len(right_iris_points),
                                    sum(p[1] for p in right_iris_points) / len(right_iris_points)
                                )
                            
                            # landmark_manager에 원본으로 저장
                            self.landmark_manager.set_iris_center_coords(
                                left_center_orig, 
                                right_center_orig,
                                is_original=True
                            )
                
                # custom_landmarks에서 중앙 포인트 추출 (470개인 경우)
                extracted_left_center = None
                extracted_right_center = None
                if custom_landmarks_for_morph is not None and len(custom_landmarks_for_morph) == 470:
                    # 마지막 2개가 중앙 포인트이므로 추출
                    # [-2] = LEFT, [-1] = RIGHT (변경하지 말 것)
                    extracted_left_center = custom_landmarks_for_morph[-2]   # LEFT
                    extracted_right_center = custom_landmarks_for_morph[-1]  # RIGHT
                    # custom_landmarks를 468개로 변환 (중앙 포인트 제거)
                    custom_landmarks_for_morph = custom_landmarks_for_morph[:-2]
                    
                # 중앙 포인트 파라미터로 사용 (landmark_manager에서 가져온 값이 없으면 추출한 값 사용)
                if left_center is None and extracted_left_center is not None:
                    left_center = extracted_left_center
                if right_center is None and extracted_right_center is not None:
                    right_center = extracted_right_center
                
                # original_landmarks는 항상 468개 (중앙 포인트는 파라미터로 전달)
                # 눈동자 중심점만 변경한 경우, custom_landmarks_for_morph와 동일하게 원본 사용
                if isinstance(last_selected_index, str) and last_selected_index in ('left', 'right'):
                    # custom_landmarks_for_morph와 동일한 출처에서 가져오기 (원본 얼굴 랜드마크)
                    original_face_for_morph = self.landmark_manager.get_original_face_landmarks()
                    if original_face_for_morph is not None:
                        original_landmarks_for_morph = original_face_for_morph
                    else:
                        original_landmarks_for_morph = original_landmarks
                else:
                    # 일반적인 경우 원본 랜드마크 사용
                    original_landmarks_for_morph = original_landmarks
                
                # 디버깅: custom_landmarks_for_morph와 original_landmarks_for_morph 비교
                if custom_landmarks_for_morph is not None and original_landmarks_for_morph is not None:
                    if len(custom_landmarks_for_morph) == len(original_landmarks_for_morph):
                        diff_count = 0
                        max_diff = 0.0
                        for i in range(len(custom_landmarks_for_morph)):
                            if isinstance(custom_landmarks_for_morph[i], tuple) and isinstance(original_landmarks_for_morph[i], tuple):
                                diff = ((custom_landmarks_for_morph[i][0] - original_landmarks_for_morph[i][0])**2 + 
                                       (custom_landmarks_for_morph[i][1] - original_landmarks_for_morph[i][1])**2)**0.5
                                if diff > 0.1:
                                    diff_count += 1
                                    max_diff = max(max_diff, diff)
                        print_info("얼굴편집", f"랜드마크 비교: 다른 포인트 {diff_count}개, 최대 차이 {max_diff:.2f}픽셀")
                    else:
                        print_info("얼굴편집", f"랜드마크 길이 불일치: custom={len(custom_landmarks_for_morph)}, original={len(original_landmarks_for_morph)}")
                
                # 디버그: 중앙 포인트 좌표 확인
                print_info("얼굴편집", f"중심점 드래그 적용: left_center={left_center}, right_center={right_center}")
                print_info("얼굴편집", f"원본 중심점: left_orig={left_center_orig}, right_orig={right_center_orig}")
                print_info("얼굴편집", f"마지막 선택 인덱스: {last_selected_index}")
                
                # 캐시된 원본 바운딩 박스 가져오기
                img_width, img_height = self.current_image.size
                cached_bbox = self.landmark_manager.get_original_bbox(img_width, img_height)
                # 블렌딩 비율 가져오기
                blend_ratio = self.blend_ratio.get() if hasattr(self, 'blend_ratio') else 1.0
                # 눈동자 이동 범위 제한 파라미터 가져오기
                clamping_enabled = getattr(self, 'iris_clamping_enabled', None)
                margin_ratio = getattr(self, 'iris_clamping_margin_ratio', None)
                clamping_enabled_val = clamping_enabled.get() if clamping_enabled is not None else True
                margin_ratio_val = margin_ratio.get() if margin_ratio is not None else 0.3
                
                # 디버그: morph_face_by_polygons 호출 전 파라미터 확인
                print_info("얼굴편집", f"morph_face_by_polygons 호출: original={len(original_landmarks_for_morph)}개, transformed={len(custom_landmarks_for_morph)}개")
                print_info("얼굴편집", f"중앙 포인트: left={left_center}, right={right_center}, left_orig={left_center_orig}, right_orig={right_center_orig}")
                print_info("얼굴편집", f"클램핑: enabled={clamping_enabled_val}, margin_ratio={margin_ratio_val}")
                
               
                # morph_face_by_polygons 호출 (폴리곤 모드)
                # iris_mapping_method 파라미터로 맵핑 방법 구분
                
                # 맵핑 방법 파라미터 가져오기
                iris_mapping_method = getattr(self, 'iris_mapping_method', None)
                iris_mapping_method_val = iris_mapping_method.get() if iris_mapping_method is not None else "iris_outline"
                
                # 옵션 변경 시에는 현재 맵핑 방법에 해당하는 인덱스를 전달
                # 선택적 변형 복잡성 제거하고 항상 전체 변형 사용
                selected_indices = None
                
                result = face_morphing.morph_face_by_polygons(
                        self.current_image,  # 원본 이미지
                        original_landmarks_for_morph,  # 원본 랜드마크 (468개)
                        custom_landmarks_for_morph,  # 변형된 랜드마크 (468개, 중앙 포인트 제거됨)
                        selected_point_indices=selected_indices,  # 선택한 포인트 인덱스
                        left_iris_center_coord=left_center,  # 드래그로 변환된 왼쪽 중앙 포인트
                        right_iris_center_coord=right_center,  # 드래그로 변환된 오른쪽 중앙 포인트
                        left_iris_center_orig=left_center_orig,  # 원본 왼쪽 중앙 포인트
                        right_iris_center_orig=right_center_orig,  # 원본 오른쪽 중앙 포인트
                        cached_original_bbox=cached_bbox,  # 캐시된 원본 바운딩 박스
                        blend_ratio=blend_ratio,  # 블렌딩 비율
                        clamping_enabled=clamping_enabled_val,  # 눈동자 이동 범위 제한 활성화 여부
                        margin_ratio=margin_ratio_val,  # 눈동자 이동 범위 제한 마진 비율
                        iris_mapping_method=iris_mapping_method_val  # 눈동자 맵핑 방법 (iris_outline/eye_landmarks)
                    )
                
                # 디버그: 결과 확인
                print_info("얼굴편집", f"morph_face_by_polygons 결과: {type(result)}, 크기: {result.size if result else 'None'}")
            
            if result is None:
                print_error("얼굴편집", "랜드마크 변형 결과가 None입니다")
                return
            
            # 편집된 이미지 업데이트
            self.edited_image = result
            self.face_landmarks = self.custom_landmarks  # 현재 편집된 랜드마크 저장 (표시용)
            
            # 이미지 해시 계산 및 업데이트 (옵션 변경 시에는 강제 업데이트)
            try:
                import hashlib
                img_bytes = result.tobytes()
                current_hash = hashlib.md5(img_bytes).hexdigest()
                
                # 옵션 변경 시(force_slider_mode=False)에는 강제로 화면 업데이트
                if force_slider_mode == False:
                    print_info("얼굴편집", f"옵션 변경으로 인한 강제 화면 업데이트")
                    self.show_edited_preview()
                    self._last_edited_image_hash = current_hash
                elif current_hash != getattr(self, '_last_edited_image_hash', None):
                    print_info("얼굴편집", f"이미지 해시 변경됨, show_edited_preview() 호출")
                    self.show_edited_preview()
                    self._last_edited_image_hash = current_hash
                else:
                    print_info("얼굴편집", f"이미지 해시 동일, show_edited_preview() 건너뜀")
            except Exception as e:
                print_error("얼굴편집", f"이미지 해시 계산 실패: {e}")
                self.show_edited_preview()  # 오류 시 무조건 업데이트       
            # 랜드마크 표시 업데이트 (이미 조건부 호출됨)
            if self.show_landmark_points.get():
                self.update_face_features_display()
            
        except Exception as e:
            print_error("얼굴편집", f"랜드마크 드래그 최종 적용 실패: {e}", e)
            import traceback
            traceback.print_exc()
    
    def _find_nearest_landmark_for_drag(self, event, landmarks, current_tab, canvas_obj):
        """캔버스 레벨에서 가장 가까운 랜드마크 포인트 찾기 (화면에 보이는 모든 포인트 중에서)"""
        if landmarks is None or len(landmarks) == 0:
            return None
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return None
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        # 캔버스 크기 가져오기 (화면 범위 확인용)
        canvas_width = canvas_obj.winfo_width()
        canvas_height = canvas_obj.winfo_height()
        
        # 이미지 영역 계산 (이미지가 화면에 보이는 범위)
        image_left = pos_x - display_width / 2
        image_right = pos_x + display_width / 2
        image_top = pos_y - display_height / 2
        image_bottom = pos_y + display_height / 2
        
        # 클릭 위치가 이미지 영역 밖에 있으면 포인트를 찾지 않음
        click_threshold = 15  # 캔버스 좌표계 기준 선택 범위 (픽셀)
        margin = click_threshold
        if (event.x < image_left - margin or event.x > image_right + margin or
            event.y < image_top - margin or event.y > image_bottom + margin):
            # 이미지 영역 밖을 클릭했으면 포인트를 찾지 않음
            return None
        
        # 화면에 보이는 포인트 확인
        # 1. 랜드마크 체크박스가 체크되어 있으면 polygon_point_map에 있는 포인트
        # 2. 폴리곤만 체크되어 있으면 현재 탭에 해당하는 포인트들 (폴리곤에 포함된 포인트)
        # 캔버스 타입 결정
        canvas_type = 'original' if canvas_obj == self.canvas_original else 'edited'
        visible_point_set = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
        polygon_items = self.landmark_polygon_items[canvas_type]
        
        # 폴리곤에 포함된 포인트만 확인 (polygon_point_map 사용)
        # 확장 레벨로 추가된 포인트도 포함됨
        if len(polygon_items) > 0:
            # 폴리곤이 그려져 있으면 polygon_point_map에 있는 포인트만 확인
            # 이렇게 하면 확장 레벨로 추가된 포인트도 포함됨
            visible_indices = list(visible_point_set)
        else:
            # 폴리곤이 그려져 있지 않으면 빈 리스트
            visible_indices = []
        
        # 중앙 포인트를 먼저 체크 (눈동자 포인트보다 우선)
        # 눈동자 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 찾지 않음
        center_radius = 10  # 중앙 포인트 클릭 범위 (캔버스 좌표계 기준, 픽셀)
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
            RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            
            # 왼쪽 눈동자 중앙 포인트 체크
            left_iris_indices_set = set()
            for idx1, idx2 in LEFT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    left_iris_indices_set.add(idx1)
                    left_iris_indices_set.add(idx2)
            if 468 < len(landmarks):
                left_iris_indices_set.add(468)
            
            if left_iris_indices_set:
                left_iris_coords = []
                for idx in left_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        left_iris_coords.append((img_x, img_y))
                
                if left_iris_coords:
                    center_x = sum(c[0] for c in left_iris_coords) / len(left_iris_coords)
                    center_y = sum(c[1] for c in left_iris_coords) / len(left_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        # 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 제외
                        visible_indices = [idx for idx in visible_indices if idx not in left_iris_indices_set]
            
            # 오른쪽 눈동자 중앙 포인트 체크
            right_iris_indices_set = set()
            for idx1, idx2 in RIGHT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    right_iris_indices_set.add(idx1)
                    right_iris_indices_set.add(idx2)
            if 473 < len(landmarks):
                right_iris_indices_set.add(473)
            
            if right_iris_indices_set:
                right_iris_coords = []
                for idx in right_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        right_iris_coords.append((img_x, img_y))
                
                if right_iris_coords:
                    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
                    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        # 중앙 포인트가 클릭 범위 내에 있으면 눈동자 포인트를 제외
                        visible_indices = [idx for idx in visible_indices if idx not in right_iris_indices_set]
        except (ImportError, AttributeError):
            # MediaPipe가 없거나 FACEMESH_LEFT_IRIS/FACEMESH_RIGHT_IRIS가 없으면 스킵
            pass
        
        min_distance = float('inf')
        nearest_idx = None
        
        for idx in visible_indices:
            if idx >= len(landmarks):
                continue
            landmark = landmarks[idx]
            if landmark is None:
                continue
            
            # 랜드마크 좌표 (이미지 좌표계)
            if isinstance(landmark, tuple):
                lm_img_x, lm_img_y = landmark
            else:
                lm_img_x = landmark.x * img_width
                lm_img_y = landmark.y * img_height
            
            # 랜드마크를 캔버스 좌표로 변환
            rel_lm_x = (lm_img_x - img_width / 2) * scale_x
            rel_lm_y = (lm_img_y - img_height / 2) * scale_y
            lm_canvas_x = pos_x + rel_lm_x
            lm_canvas_y = pos_y + rel_lm_y
            
            # 포인트가 이미지 영역 내에 있는지 확인 (이미지 영역 밖의 포인트는 선택 불가)
            if (lm_canvas_x < image_left or lm_canvas_x > image_right or
                lm_canvas_y < image_top or lm_canvas_y > image_bottom):
                # 이미지 영역 밖에 있는 포인트는 건너뛰기
                continue
            
            # 화면에 보이는 포인트만 확인 (캔버스 범위 내에 있는지 체크)
            # 마진을 두어 약간 벗어난 포인트도 선택 가능하도록 함
            margin = click_threshold
            if (lm_canvas_x < -margin or lm_canvas_x > canvas_width + margin or
                lm_canvas_y < -margin or lm_canvas_y > canvas_height + margin):
                # 화면 범위 밖에 있는 포인트는 건너뛰기
                continue
            
            # 캔버스 좌표계 기준으로 거리 계산 (화면에서 보이는 거리)
            distance = math.sqrt((event.x - lm_canvas_x)**2 + (event.y - lm_canvas_y)**2)
            
            # 최소 거리 업데이트 (캔버스 좌표계 기준 15픽셀 이내만 선택)
            # 이미 드래그 중인 포인트를 우선하지 않고, 항상 가장 가까운 포인트를 선택
            if distance < min_distance and distance < click_threshold:
                min_distance = distance
                nearest_idx = idx
        
        return nearest_idx
    
    def _check_iris_center_click(self, event, landmarks, canvas_obj):
        """중앙 포인트가 클릭 범위 내에 있는지 확인"""
        if landmarks is None or len(landmarks) == 0:
            return False
        
        # 이미지 좌표계로 변환
        if canvas_obj == self.canvas_original:
            img = self.current_image
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
        else:
            img = self.edited_image
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
        
        if img is None or pos_x is None or pos_y is None:
            return False
        
        img_width, img_height = img.size
        display_size = getattr(canvas_obj, 'display_size', None)
        if display_size is None:
            display_width = img_width
            display_height = img_height
        else:
            display_width, display_height = display_size
        
        scale_x = display_width / img_width
        scale_y = display_height / img_height
        
        center_radius = 25  # 중앙 포인트 클릭 범위 (캔버스 좌표계 기준, 픽셀)
        
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
            RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            
            # 왼쪽 눈동자 중앙 포인트 체크 (계산값)
            left_iris_indices_set = set()
            for idx1, idx2 in LEFT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    left_iris_indices_set.add(idx1)
                    left_iris_indices_set.add(idx2)
            if 468 < len(landmarks):
                left_iris_indices_set.add(468)
            
            if left_iris_indices_set:
                left_iris_coords = []
                for idx in left_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        left_iris_coords.append((img_x, img_y))
                
                if left_iris_coords:
                    center_x = sum(c[0] for c in left_iris_coords) / len(left_iris_coords)
                    center_y = sum(c[1] for c in left_iris_coords) / len(left_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        return True
            
            # 오른쪽 눈동자 중앙 포인트 체크 (계산값)
            right_iris_indices_set = set()
            for idx1, idx2 in RIGHT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    right_iris_indices_set.add(idx1)
                    right_iris_indices_set.add(idx2)
            if 473 < len(landmarks):
                right_iris_indices_set.add(473)
            
            if right_iris_indices_set:
                right_iris_coords = []
                for idx in right_iris_indices_set:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        right_iris_coords.append((img_x, img_y))
                
                if right_iris_coords:
                    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
                    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    center_canvas_x = pos_x + rel_x
                    center_canvas_y = pos_y + rel_y
                    center_distance = math.sqrt((event.x - center_canvas_x)**2 + (event.y - center_canvas_y)**2)
                    if center_distance < center_radius:
                        return True
        except (ImportError, AttributeError):
            # MediaPipe가 없거나 FACEMESH_LEFT_IRIS/FACEMESH_RIGHT_IRIS가 없으면 스킵
            pass
        
        return False
    
    def _calculate_iris_center(self, landmarks, iris_indices, img_width, img_height):
        """눈동자 인덱스에서 중앙 포인트 계산
        
        Args:
            landmarks: 랜드마크 리스트
            iris_indices: 눈동자 인덱스 리스트
            img_width: 이미지 너비
            img_height: 이미지 높이
        
        Returns:
            (center_x, center_y) 튜플 또는 None
        """
        if not landmarks or not iris_indices:
            return None
        
        iris_coords = []
        for idx in iris_indices:
            if idx < len(landmarks):
                pt = landmarks[idx]
                if isinstance(pt, tuple):
                    iris_coords.append(pt)
                else:
                    iris_coords.append((pt.x * img_width, pt.y * img_height))
        
        if not iris_coords:
            return None
        
        center_x = sum(c[0] for c in iris_coords) / len(iris_coords)
        center_y = sum(c[1] for c in iris_coords) / len(iris_coords)
        return (center_x, center_y)
    
    def _get_iris_indices(self, for_468_structure=False):
        """MediaPipe 눈동자 인덱스 반환 (공통 유틸리티 함수 사용)
        
        Args:
            for_468_structure: 468개 랜드마크 구조용 인덱스 반환 여부
            
        Returns:
            for_468_structure=False: (left_iris_indices, right_iris_indices) 튜플
            for_468_structure=True: 468개 구조용 눈동자 주변 인덱스 리스트
        """
        if for_468_structure:
            # 468개 구조용 눈동자 주변 인덱스 (IRIS_OUTLINE 맵핑용)
            return [33, 7, 163, 144, 145, 173, 157, 158, 159, 160, 161, 246, 
                   161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 
                   163, 7, 33, 263, 249, 390, 373, 374, 380, 381, 382, 362]
        else:
            try:
                from utils.face_morphing.region_extraction import get_iris_indices
                return get_iris_indices()
            except ImportError:
                # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                return [474, 475, 476, 477], [469, 470, 471, 472]
    