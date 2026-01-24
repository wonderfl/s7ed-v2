"""
얼굴 편집 패널 - 랜드마크 표시 Mixin
랜드마크 포인트 및 연결선 표시 관련 기능을 담당
"""
import math
import tkinter as tk


class LandmarkDisplayMixin:
    
    def _draw_region_centers(self, canvas, image, landmarks, pos_x, pos_y, items_list):
        """선택된 부위의 중심점을 캔버스에 그리기"""
        if image is None or pos_x is None or pos_y is None or landmarks is None:
            return
        
        # 전체 탭이 아니거나 부위가 선택되지 않았으면 그리지 않음
        current_tab = getattr(self, 'current_morphing_tab', '눈')
        if current_tab != "전체":
            return
        
        # 선택된 부위 목록 가져오기
        selected_regions = []
        if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
            selected_regions.append('face_oval')
        if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
            selected_regions.append('left_eye')
        if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
            selected_regions.append('right_eye')
        if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
            selected_regions.append('left_eyebrow')
        if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
            selected_regions.append('right_eyebrow')
        if hasattr(self, 'show_nose') and self.show_nose.get():
            selected_regions.append('nose')
        if hasattr(self, 'show_lips') and self.show_lips.get():
            selected_regions.append('lips')
        if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
            selected_regions.append('left_iris')
        if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
            selected_regions.append('right_iris')
        if hasattr(self, 'show_contours') and self.show_contours.get():
            selected_regions.append('contours')
        if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
            selected_regions.append('tesselation')
        
        if not selected_regions:
            return
        
        try:
            from utils.face_morphing.region_extraction import _get_region_center
            
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 공통 슬라이더 값 가져오기
            center_offset_x = self.region_center_offset_x.get() if hasattr(self, 'region_center_offset_x') else 0.0
            center_offset_y = self.region_center_offset_y.get() if hasattr(self, 'region_center_offset_y') else 0.0
            
            # 각 선택된 부위의 중심점 그리기
            for region_name in selected_regions:
                center = _get_region_center(region_name, landmarks, center_offset_x, center_offset_y)
                if center is None:
                    continue
                
                center_x, center_y = center
                
                # 캔버스 좌표로 변환
                rel_x = (center_x - img_width / 2) * scale_x
                rel_y = (center_y - img_height / 2) * scale_y
                canvas_x = pos_x + rel_x
                canvas_y = pos_y + rel_y
                
                # 중심점을 십자가 모양으로 그리기 (크기: 10픽셀)
                size = 5
                # 가로선
                line1 = canvas.create_line(
                    canvas_x - size, canvas_y,
                    canvas_x + size, canvas_y,
                    fill="yellow",
                    width=2,
                    tags=("region_center", f"center_{region_name}")
                )
                items_list.append(line1)
                
                # 세로선
                line2 = canvas.create_line(
                    canvas_x, canvas_y - size,
                    canvas_x, canvas_y + size,
                    fill="yellow",
                    width=2,
                    tags=("region_center", f"center_{region_name}")
                )
                items_list.append(line2)
                
                # 중심점을 원으로도 그리기 (반지름 3픽셀)
                circle = canvas.create_oval(
                    canvas_x - 3, canvas_y - 3,
                    canvas_x + 3, canvas_y + 3,
                    outline="yellow",
                    width=2,
                    fill="",
                    tags=("region_center", f"center_{region_name}")
                )
                items_list.append(circle)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
    """랜드마크 표시 기능 Mixin"""
    
    def _draw_landmarks_on_canvas(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, draw_points=True, draw_lines=False, draw_polygons=False, polygon_items_list=None, show_indices=False):
        """캔버스에 랜드마크 그리기 (현재 선택된 탭에 따라 필터링)
        
        Args:
            draw_points: 랜드마크 포인트를 그릴지 여부
            draw_lines: 연결선을 그릴지 여부
            draw_polygons: 폴리곤을 그릴지 여부
            polygon_items_list: 연결선과 폴리곤 아이템을 저장할 리스트 (None이면 items_list 사용)
            show_indices: 인덱스 번호를 표시할지 여부
        """
        if polygon_items_list is None:
            polygon_items_list = items_list
        if image is None or pos_x is None or pos_y is None:
            return

        try:
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            
            # 이미지 스케일 계산
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # MediaPipe Face Mesh 랜드마크 인덱스 정의
            # 참고: https://github.com/google/mediapipe/blob/master/mediapipe/python/solutions/face_mesh.py
            LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
            # 눈썹 인덱스
            LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
            RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
            # 눈 주변 영역 인덱스 (눈꺼풀, 눈 주변 피부) - transform_points_for_eye_size와 동일하게
            # 중복 제거를 위해 set 사용
            LEFT_EYE_SURROUNDING_INDICES = list(set(LEFT_EYE_INDICES + LEFT_EYEBROW_INDICES + [
                10, 151, 9, 337, 299, 333, 298, 301, 368, 264, 447, 366, 401, 435, 410, 454, 323, 361,
                # 추가 눈 주변 포인트들
                107, 55, 65, 52, 53, 46, 70, 63, 105, 66,  # 눈썹 추가 포인트
                226, 113, 225, 224, 223, 222, 221, 189, 244, 233, 232, 231, 230, 229, 228, 31, 228, 229, 230, 231, 232, 233, 244, 189, 221, 222, 223, 224, 225, 113, 226,  # 왼쪽 눈 주변 추가
            ]))
            RIGHT_EYE_SURROUNDING_INDICES = list(set(RIGHT_EYE_INDICES + RIGHT_EYEBROW_INDICES + [
                172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323,
                # 추가 눈 주변 포인트들
                336, 285, 295, 282, 283, 276, 300, 293, 334, 296,  # 눈썹 추가 포인트
                446, 342, 445, 444, 443, 442, 441, 413, 463, 453, 452, 451, 450, 449, 448, 261, 448, 449, 450, 451, 452, 453, 463, 413, 441, 442, 443, 444, 445, 342, 446,  # 오른쪽 눈 주변 추가
            ]))
            
            # 입 랜드마크 정의 (입 전체 vs 입술 구분)
            # 입술 외곽 (Outer Lip): 윗입술 + 아래입술 외곽선
            OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
            # 입 안쪽 (Inner Lip): 입 안쪽 경계선
            INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
            # 입 전체 (입술 외곽 + 입 안쪽)
            MOUTH_ALL_INDICES = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))
            # 입술만 (입술 외곽만)
            LIP_ONLY_INDICES = OUTER_LIP_INDICES
            
            # 윗입술과 아래입술 구분
            # 윗입술 외곽 (위쪽 절반)
            UPPER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84]
            # 아래입술 외곽 (아래쪽 절반)
            LOWER_LIP_INDICES = [181, 91, 146, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324]
            
            NOSE_INDICES = [8, 240, 98, 164, 327, 460, 4]  # 코 끝 및 코 영역
            
            # 현재 선택된 탭에 따라 표시할 랜드마크 인덱스 결정
            current_tab = getattr(self, 'current_morphing_tab', '눈')
            
            if current_tab == '전체':
                # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 아무것도 표시하지 않음
                if hasattr(self, '_get_target_indices_for_tab'):
                    target_indices_list = self._get_target_indices_for_tab('전체')
                    if target_indices_list is not None and len(target_indices_list) > 0:
                        # 선택된 부위가 있으면 선택된 부위만 표시
                        target_indices = set(target_indices_list)
                    else:
                        # 선택된 부위가 없으면 빈 세트 (아무것도 표시하지 않음)
                        target_indices = set()
                else:
                    # _get_target_indices_for_tab 함수가 없으면 아무것도 표시하지 않음
                    target_indices = set()
            elif current_tab == '눈':
                # 눈 탭: 왼쪽 눈, 오른쪽 눈, 눈동자만 표시 (눈썹 제외)
                # 눈 인덱스만 사용 (눈썹 제외)
                target_indices = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
                # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능)
                # custom_landmarks를 사용할 때는 눈동자 포인트(468-477)가 제거되고 중앙 포인트로 대체됨
                # LandmarkManager를 통해 얼굴/눈동자 분리 확인
                iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                iris_centers = self.landmark_manager.get_custom_iris_centers()
                has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
                has_iris_centers = (iris_centers is not None and len(iris_centers) == 2)
                
                if has_iris_landmarks or has_iris_centers:
                    # custom_landmarks를 사용하는 경우 눈동자 포인트 인덱스 제외
                    use_custom = hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and landmarks is self.custom_landmarks
                    if not use_custom and has_iris_landmarks:
                        # 원본 랜드마크를 사용하는 경우에만 눈동자 포인트 인덱스 추가 (MediaPipe 정의 사용)
                        try:
                            from utils.face_morphing.region_extraction import get_iris_indices
                            left_iris_indices, right_iris_indices = get_iris_indices()
                            iris_indices = left_iris_indices + right_iris_indices
                        except ImportError:
                            # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                            iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                        for idx in iris_indices:
                            if idx < len(landmarks):
                                target_indices.add(idx)
                    elif use_custom and has_iris_centers:
                        # custom_landmarks를 사용하는 경우 중앙 포인트 인덱스만 추가
                        if hasattr(self, '_left_iris_center_index') and self._left_iris_center_index is not None:
                            if self._left_iris_center_index < len(landmarks):
                                target_indices.add(self._left_iris_center_index)
                        if hasattr(self, '_right_iris_center_index') and self._right_iris_center_index is not None:
                            if self._right_iris_center_index < len(landmarks):
                                target_indices.add(self._right_iris_center_index)
            elif current_tab == '눈동자':
                # 눈동자 탭: 눈동자 인덱스만 표시
                target_indices = set()
                # LandmarkManager를 통해 얼굴/눈동자 분리 확인
                iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                iris_centers = self.landmark_manager.get_custom_iris_centers()
                has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
                has_iris_centers = (iris_centers is not None and len(iris_centers) == 2)
                
                if has_iris_landmarks or has_iris_centers:
                    use_custom = hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and landmarks is self.custom_landmarks
                    if not use_custom:
                        # 원본 랜드마크를 사용하는 경우에만 눈동자 포인트 인덱스 추가
                        try:
                            from utils.face_morphing.region_extraction import get_iris_indices
                            left_iris_indices, right_iris_indices = get_iris_indices()
                            iris_indices = left_iris_indices + right_iris_indices
                        except ImportError:
                            iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                        for idx in iris_indices:
                            if idx < len(landmarks):
                                target_indices.add(idx)
                    else:
                        # custom_landmarks를 사용하는 경우 중앙 포인트 인덱스만 추가
                        if hasattr(self, '_left_iris_center_index') and self._left_iris_center_index is not None:
                            if self._left_iris_center_index < len(landmarks):
                                target_indices.add(self._left_iris_center_index)
                        if hasattr(self, '_right_iris_center_index') and self._right_iris_center_index is not None:
                            if self._right_iris_center_index < len(landmarks):
                                target_indices.add(self._right_iris_center_index)
            elif current_tab == '눈썹':
                # 눈썹 탭: 왼쪽/오른쪽 눈썹 랜드마크 표시
                target_indices = set(LEFT_EYEBROW_INDICES + RIGHT_EYEBROW_INDICES)
            elif current_tab == '입':
                # 입 탭: 입 전체 표시 (입술 외곽 + 입 안쪽)
                target_indices = set(MOUTH_ALL_INDICES)
            elif current_tab == '코':
                # 코 탭: 코 랜드마크만 표시
                target_indices = set(NOSE_INDICES)
            elif current_tab == '턱선':
                # 턱선 탭: 턱선 관련 랜드마크 표시 (인덱스 0-16)
                jaw_indices = list(range(17))  # 0-16
                target_indices = set(jaw_indices)
            else:
                # 윤곽 탭 또는 기타: 모든 랜드마크 표시
                target_indices = None
            
            # 랜드마크 포인트 크기
            point_size = 2  # 기본 랜드마크 포인트 크기 (픽셀)
            
            # 랜드마크 포인트 그리기 (draw_points가 True일 때만)
            if draw_points:
                # custom_landmarks를 사용할 때는 눈동자 포인트 인덱스 제외 (MediaPipe 정의 사용)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices_to_exclude = set(left_iris_indices + right_iris_indices)
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    iris_indices_to_exclude = set([469, 470, 471, 472, 474, 475, 476, 477])
                use_custom = hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and landmarks is self.custom_landmarks
                
                for idx, landmark in enumerate(landmarks):
                    # 현재 탭에 해당하는 랜드마크만 표시
                    if target_indices is not None and idx not in target_indices:
                        continue
                    
                    # custom_landmarks를 사용할 때는 눈동자 포인트 인덱스 제외 (중앙 포인트만 표시)
                    if use_custom and idx in iris_indices_to_exclude:
                        continue
                    
                    # 랜드마크 좌표 (튜플 형태: (x, y))
                    if isinstance(landmark, tuple):
                        # detect_face_landmarks가 반환하는 형태: (x, y) 픽셀 좌표
                        img_x, img_y = landmark
                    else:
                        # MediaPipe landmark 객체 형태: landmark.x, landmark.y (0.0 ~ 1.0)
                        img_x = landmark.x * img_width
                        img_y = landmark.y * img_height
                    
                    # 캔버스 좌표로 변환 (이미지 중심 기준)
                    rel_x = (img_x - img_width / 2) * scale_x
                    rel_y = (img_y - img_height / 2) * scale_y
                    
                    # 캔버스 절대 좌표
                    canvas_x = pos_x + rel_x
                    canvas_y = pos_y + rel_y
                    
                    # 랜드마크 포인트 크기 (드래그 가능하도록 클릭 영역은 크게 유지)
                    # 고급 모드일 때는 약간 더 크게 표시
                    use_warping = getattr(self, 'use_landmark_warping', None)
                    if use_warping is not None and hasattr(use_warping, 'get'):
                        is_warping_mode = use_warping.get()
                    else:
                        is_warping_mode = False
                    
                    # 기본 크기: 2픽셀, 고급 모드: 3픽셀
                    actual_point_size = point_size
                    
                    # 작은 원으로 랜드마크 포인트 그리기
                    point_id = canvas.create_oval(
                        canvas_x - actual_point_size, canvas_y - actual_point_size,
                        canvas_x + actual_point_size, canvas_y + actual_point_size,
                        fill=color, outline=color, width=1, tags=("landmarks", f"landmark_{idx}")
                    )
                    items_list.append(point_id)
                    
                    # 클릭 영역을 더 크게 만들기 (보이지 않는 큰 원)
                    # 실제 포인트보다 큰 클릭 영역으로 선택 용이성 향상
                    # 폴리곤 클릭 대신 포인트를 직접 클릭할 수 있도록 클릭 영역을 크게 설정
                    click_area_size = actual_point_size + 10  # 포인트보다 10픽셀 더 큰 클릭 영역 (폴리곤 클릭 대신 사용)
                    click_area_id = canvas.create_oval(
                        canvas_x - click_area_size, canvas_y - click_area_size,
                        canvas_x + click_area_size, canvas_y + click_area_size,
                        fill="", outline="", width=0, tags=("landmarks", f"landmark_{idx}", "landmark_click_area")
                    )
                    items_list.append(click_area_id)
                    
                    # 랜드마크 포인트를 그릴 때는 polygon_point_map에 저장하지 않음
                    # 폴리곤을 그릴 때만 polygon_point_map에 저장함
                    
                    # 인덱스 번호 표시 (show_indices가 True일 때만)
                    if show_indices:
                        # 포인트 옆에 인덱스 번호 표시
                        text_offset = actual_point_size + 5  # 포인트에서 약간 떨어진 위치
                        text_id = canvas.create_text(
                            canvas_x + text_offset,
                            canvas_y - text_offset,
                            text=str(idx),
                            fill=color,
                            font=("Arial", 12, "bold"),  # 글자 크기 8 -> 12로 증가
                            tags=("landmarks", f"landmark_text_{idx}")
                        )
                        items_list.append(text_id)
                        # 텍스트도 최상위로 올림
                        try:
                            canvas.tag_raise(text_id, "landmarks_polygon")
                            canvas.tag_raise(text_id)
                        except Exception:
                            pass
                    
                    # 랜드마크 포인트와 클릭 영역을 폴리곤보다 앞에 배치 (드래그 우선순위 확보)
                    try:
                        canvas.tag_raise(point_id, "landmarks_polygon")
                        canvas.tag_raise(click_area_id, "landmarks_polygon")
                        # 포인트와 클릭 영역을 최상위로 올림
                        canvas.tag_raise(point_id)
                        canvas.tag_raise(click_area_id)
                    except Exception:
                        pass
            
            # 폴리곤 표시 (draw_polygons가 True일 때만) - 먼저 그리기
            if draw_polygons:
                # 폴리곤 그리기
                self._draw_landmark_polygons(canvas, image, landmarks, pos_x, pos_y, polygon_items_list, color, current_tab)
            
            # 연결선 표시 (draw_lines가 True일 때만) - 폴리곤 다음에 그리기
            if draw_lines:
                self._draw_landmark_lines(canvas, image, landmarks, pos_x, pos_y, polygon_items_list, color, current_tab)
                
                # 연결선을 그린 후, 모든 랜드마크 포인트와 클릭 영역을 연결선보다 앞에 배치
                # (랜드마크 드래그 우선순위 확보)
                if draw_points:
                    try:
                        # 모든 랜드마크 포인트와 클릭 영역을 연결선보다 앞으로
                        for item in canvas.find_withtag("landmarks"):
                            try:
                                canvas.tag_raise(item, "landmarks_polygon")
                            except Exception:
                                pass
                        for item in canvas.find_withtag("landmark_click_area"):
                            try:
                                canvas.tag_raise(item, "landmarks_polygon")
                            except Exception:
                                pass
                    except Exception:
                        # 태그가 없으면 무시 (이미 삭제되었거나 아직 생성되지 않음)
                        pass
        
        except Exception as e:
            import traceback
            traceback.print_exc()
    

    def _draw_landmark_lines(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, current_tab):
        """랜드마크 연결선 그리기 (연결선만, 폴리곤 아님)"""
        if image is None or pos_x is None or pos_y is None or landmarks is None:
            return
        try:
            import math
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # MediaPipe 연결 정보 가져오기
            try:
                import mediapipe as mp
                mp_face_mesh = mp.solutions.face_mesh
                FACE_OVAL = mp_face_mesh.FACEMESH_FACE_OVAL
                LEFT_EYE = mp_face_mesh.FACEMESH_LEFT_EYE
                RIGHT_EYE = mp_face_mesh.FACEMESH_RIGHT_EYE
                LEFT_EYEBROW = mp_face_mesh.FACEMESH_LEFT_EYEBROW
                RIGHT_EYEBROW = mp_face_mesh.FACEMESH_RIGHT_EYEBROW
                NOSE = mp_face_mesh.FACEMESH_NOSE
                LIPS = mp_face_mesh.FACEMESH_LIPS
            except ImportError:
                # MediaPipe가 없으면 폴리곤 그리지 않음
                return
            
            # 현재 탭에 따라 표시할 연결선 결정
            # MediaPipe의 FACEMESH 상수는 frozenset 타입이므로 리스트로 변환
            connections_to_draw = []
            if current_tab == '전체':
                # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 아무것도 표시하지 않음
                if hasattr(self, '_get_selected_region_indices'):
                    selected_indices = self._get_selected_region_indices()
                    if selected_indices is not None and len(selected_indices) > 0:
                        # 선택된 부위의 연결선만 표시
                        connections_to_draw = []
                        selected_set = set(selected_indices)
                        # 각 부위의 연결선 중 선택된 인덱스에 포함된 것만 추가
                        all_connections = list(FACE_OVAL) + list(LEFT_EYE) + list(RIGHT_EYE) + list(LEFT_EYEBROW) + list(RIGHT_EYEBROW) + list(NOSE) + list(LIPS)
                        try:
                            CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
                            all_connections.extend(CONTOURS)
                        except AttributeError:
                            pass
                        try:
                            TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
                            all_connections.extend(TESSELATION)
                        except AttributeError:
                            pass
                        try:
                            LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                            RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                            all_connections.extend(LEFT_IRIS)
                            all_connections.extend(RIGHT_IRIS)
                        except AttributeError:
                            pass
                        for conn in all_connections:
                            if conn[0] in selected_set and conn[1] in selected_set:
                                connections_to_draw.append(conn)
                    else:
                        # 선택된 부위가 없으면 빈 리스트 (아무것도 표시하지 않음)
                        connections_to_draw = []
                else:
                    # _get_selected_region_indices 함수가 없으면 아무것도 표시하지 않음
                    connections_to_draw = []
            elif current_tab == '눈동자':
                # 눈동자 탭: 눈동자 연결선만 그리기
                try:
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    connections_to_draw = list(LEFT_IRIS) + list(RIGHT_IRIS)
                except AttributeError:
                    connections_to_draw = []
            elif current_tab == '눈':
                # 눈 편집 시: 연결선만 그리기 (폴리곤은 별도로, 눈썹 제외)
                connections_to_draw = list(LEFT_EYE) + list(RIGHT_EYE)
                # 눈동자 연결 정보 추가
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    try:
                        LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                        RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                        if LEFT_IRIS and RIGHT_IRIS:
                            connections_to_draw.extend(LEFT_IRIS)
                            connections_to_draw.extend(RIGHT_IRIS)
                    except AttributeError:
                        pass
                except ImportError:
                    pass
            elif current_tab == '눈썹':
                # 눈썹 편집 시: 눈썹 연결선만 그리기
                connections_to_draw = list(LEFT_EYEBROW) + list(RIGHT_EYEBROW)
            elif current_tab == '코':
                connections_to_draw = list(NOSE)
            elif current_tab == '입':
                connections_to_draw = list(LIPS)
            elif current_tab == '턱선':
                # 턱선 편집 시: 얼굴 외곽선 연결선 그리기
                connections_to_draw = list(FACE_OVAL)
            else:
                # 윤곽 탭 또는 기타: 모든 연결선 표시
                connections_to_draw = list(FACE_OVAL) + list(LEFT_EYE) + list(RIGHT_EYE) + list(NOSE) + list(LIPS)
            
            # 연결선 그리기
            line_count = 0
            for idx1, idx2 in connections_to_draw:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    # 랜드마크 좌표 가져오기
                    pt1 = landmarks[idx1]
                    pt2 = landmarks[idx2]
                    
                    if isinstance(pt1, tuple):
                        img_x1, img_y1 = pt1
                    else:
                        img_x1 = pt1.x * img_width
                        img_y1 = pt1.y * img_height
                    
                    if isinstance(pt2, tuple):
                        img_x2, img_y2 = pt2
                    else:
                        img_x2 = pt2.x * img_width
                        img_y2 = pt2.y * img_height
                    
                    # 캔버스 좌표로 변환
                    rel_x1 = (img_x1 - img_width / 2) * scale_x
                    rel_y1 = (img_y1 - img_height / 2) * scale_y
                    rel_x2 = (img_x2 - img_width / 2) * scale_x
                    rel_y2 = (img_y2 - img_height / 2) * scale_y
                    
                    canvas_x1 = pos_x + rel_x1
                    canvas_y1 = pos_y + rel_y1
                    canvas_x2 = pos_x + rel_x2
                    canvas_y2 = pos_y + rel_y2
                    
                    # 연결선 그리기 (시각적 표시용) - cyan 색상 사용
                    line_id = canvas.create_line(
                        canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                        fill="cyan", width=2, tags=("landmarks_polygon", f"polygon_line_{current_tab}")
                    )
                    items_list.append(line_id)
                    
                    # 연결선 클릭 기능 제거 (체크박스로 자동 표시되므로 불필요)
                    # 연결선을 랜드마크 포인트보다 확실히 뒤에 배치하여 랜드마크 드래그 방해 최소화
                    # 모든 랜드마크 관련 아이템(포인트, 클릭 영역)보다 뒤에 배치
                    try:
                        # landmarks 태그가 있는 모든 아이템보다 뒤로
                        canvas.tag_lower(line_id, "landmarks")
                        # landmark_click_area 태그가 있는 아이템보다도 뒤로
                        canvas.tag_lower(line_id, "landmark_click_area")
                    except Exception:
                        pass
                    line_count += 1
            
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _draw_selected_landmark_indicator(self, canvas_obj, landmark_index, x, y):
        """선택된 랜드마크 포인트를 표시하고 연결된 선들의 색상 변경"""
        # 기존 표시 제거
        self._remove_selected_landmark_indicator(canvas_obj)
        
        # 선택된 포인트를 작은 원으로 표시 (빨간색 테두리, 투명한 채우기)
        indicator_size = 2  # 선택 표시 크기
        if canvas_obj == self.canvas_original:
            self.selected_landmark_indicator_original = canvas_obj.create_oval(
                x - indicator_size, y - indicator_size,
                x + indicator_size, y + indicator_size,
                outline="red", width=2, fill="red", tags=("selected_landmark",)
            )
            # 선택 표시를 맨 앞으로
            canvas_obj.tag_raise(self.selected_landmark_indicator_original)
        else:
            self.selected_landmark_indicator_edited = canvas_obj.create_oval(
                x - indicator_size, y - indicator_size,
                x + indicator_size, y + indicator_size,
                outline="red", width=2, fill="red", tags=("selected_landmark",)
            )
            # 선택 표시를 맨 앞으로
            canvas_obj.tag_raise(self.selected_landmark_indicator_edited)
        
        # 선택된 포인트에 연결된 선들의 색상 변경
        # 특별한 인덱스(-1, -2: 눈동자 중앙)는 연결선 하이라이트 생략
        if landmark_index is not None and landmark_index >= 0:
            self._highlight_connected_lines(canvas_obj, landmark_index)

    def _update_selected_landmark_indicator(self, canvas_obj, x, y):
        """선택된 포인트 표시 위치 업데이트 및 연결된 선과 폴리곤 갱신"""
        indicator_size = 2
        if canvas_obj == self.canvas_original:
            if self.selected_landmark_indicator_original is not None:
                try:
                    # 선택된 포인트 표시 위치 업데이트
                    canvas_obj.coords(
                        self.selected_landmark_indicator_original,
                        x - indicator_size, y - indicator_size,
                        x + indicator_size, y + indicator_size
                    )
                    canvas_obj.tag_raise(self.selected_landmark_indicator_original)
                except Exception as e:
                    # 아이템이 삭제된 경우 재생성
                    if self.dragged_polygon_index is not None:
                        self._draw_selected_landmark_indicator(canvas_obj, self.dragged_polygon_index, x, y)
        else:
            if self.selected_landmark_indicator_edited is not None:
                try:
                    # 선택된 포인트 표시 위치 업데이트
                    canvas_obj.coords(
                        self.selected_landmark_indicator_edited,
                        x - indicator_size, y - indicator_size,
                        x + indicator_size, y + indicator_size
                    )
                    canvas_obj.tag_raise(self.selected_landmark_indicator_edited)
                except Exception as e:
                    # 아이템이 삭제된 경우 재생성
                    if self.dragged_polygon_index is not None:
                        self._draw_selected_landmark_indicator(canvas_obj, self.dragged_polygon_index, x, y)
        
        # 연결된 선들의 위치 업데이트
        if self.dragged_polygon_index is not None:
            self._update_connected_lines(canvas_obj, self.dragged_polygon_index, x, y)
            
            # 연결된 폴리곤 실시간 갱신
            self._update_connected_polygons(canvas_obj, self.dragged_polygon_index)

    def _remove_selected_landmark_indicator(self, canvas_obj):
        """선택된 포인트 표시 및 연결된 선 제거"""
        if canvas_obj == self.canvas_original:
            if self.selected_landmark_indicator_original is not None:
                try:
                    canvas_obj.delete(self.selected_landmark_indicator_original)
                except:
                    pass
                self.selected_landmark_indicator_original = None
            # 연결된 선들 제거
            for line_id in self.selected_landmark_lines_original:
                try:
                    canvas_obj.delete(line_id)
                except:
                    pass
            self.selected_landmark_lines_original.clear()
        else:
            if self.selected_landmark_indicator_edited is not None:
                try:
                    canvas_obj.delete(self.selected_landmark_indicator_edited)
                except:
                    pass
                self.selected_landmark_indicator_edited = None
            # 연결된 선들 제거
            for line_id in self.selected_landmark_lines_edited:
                try:
                    canvas_obj.delete(line_id)
                except:
                    pass
            self.selected_landmark_lines_edited.clear()

    def _highlight_connected_lines(self, canvas_obj, landmark_index):
        """선택된 포인트에 연결된 선들을 빨간색으로 강조 (현재 탭의 폴리곤에 포함된 연결선만)"""
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            # 현재 탭에 해당하는 연결 정보 가져오기
            current_tab = getattr(self, 'current_morphing_tab', '눈')
            tab_connections = []
            
            if current_tab == '전체':
                # 전체 탭: 모든 부위의 연결선
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE) +
                                 list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_NOSE) +
                                 list(mp_face_mesh.FACEMESH_LIPS) +
                                 list(mp_face_mesh.FACEMESH_FACE_OVAL))
            elif current_tab == '눈동자':
                # 눈동자 탭: 눈동자 연결선만
                try:
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    tab_connections = list(LEFT_IRIS) + list(RIGHT_IRIS)
                except AttributeError:
                    tab_connections = []
            elif current_tab == '눈':
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE) +
                                 list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW))
            elif current_tab == '눈썹':
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW))
            elif current_tab == '코':
                tab_connections = list(mp_face_mesh.FACEMESH_NOSE)
            elif current_tab == '입':
                tab_connections = list(mp_face_mesh.FACEMESH_LIPS)
            elif current_tab == '턱선':
                tab_connections = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            elif current_tab == '윤곽':
                tab_connections = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            else:
                # 기본값: 눈 관련
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE))
            
            # 현재 탭의 연결 정보에서 선택된 포인트와 연결된 선 찾기
            connected_indices = set()
            for idx1, idx2 in tab_connections:
                if idx1 == landmark_index:
                    connected_indices.add(idx2)
                elif idx2 == landmark_index:
                    connected_indices.add(idx1)
            
            # 연결된 선들을 빨간색으로 그리기
            if canvas_obj == self.canvas_original:
                landmarks = self.custom_landmarks if self.custom_landmarks is not None else self.face_landmarks
                pos_x = self.canvas_original_pos_x
                pos_y = self.canvas_original_pos_y
                img = self.current_image
            else:
                landmarks = self.custom_landmarks if self.custom_landmarks is not None else None
                if landmarks is None:
                    return
                pos_x = self.canvas_edited_pos_x
                pos_y = self.canvas_edited_pos_y
                img = self.edited_image
            
            if landmarks is None or img is None or pos_x is None or pos_y is None:
                return
            
            img_width, img_height = img.size
            display_size = getattr(canvas_obj, 'display_size', None)
            if display_size is None:
                return
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 선택된 포인트의 캔버스 좌표
            if isinstance(landmarks[landmark_index], tuple):
                selected_x, selected_y = landmarks[landmark_index]
            else:
                selected_x = landmarks[landmark_index].x * img_width
                selected_y = landmarks[landmark_index].y * img_height
            
            rel_x = (selected_x - img_width / 2) * scale_x
            rel_y = (selected_y - img_height / 2) * scale_y
            canvas_selected_x = pos_x + rel_x
            canvas_selected_y = pos_y + rel_y
            
            # 연결된 각 포인트로 선 그리기
            for connected_idx in connected_indices:
                if connected_idx >= len(landmarks):
                    continue
                
                if isinstance(landmarks[connected_idx], tuple):
                    conn_x, conn_y = landmarks[connected_idx]
                else:
                    conn_x = landmarks[connected_idx].x * img_width
                    conn_y = landmarks[connected_idx].y * img_height
                
                rel_conn_x = (conn_x - img_width / 2) * scale_x
                rel_conn_y = (conn_y - img_height / 2) * scale_y
                canvas_conn_x = pos_x + rel_conn_x
                canvas_conn_y = pos_y + rel_conn_y
                
                # 빨간색 연결선 그리기
                line_id = canvas_obj.create_line(
                    canvas_selected_x, canvas_selected_y,
                    canvas_conn_x, canvas_conn_y,
                    fill="red", width=2, tags=("selected_landmark_line",)
                )
                
                if canvas_obj == self.canvas_original:
                    self.selected_landmark_lines_original.append(line_id)
                else:
                    self.selected_landmark_lines_edited.append(line_id)
                
                # 선을 맨 앞으로
                canvas_obj.tag_raise(line_id)
        except Exception as e:
            print(f"[랜드마크 연결선 강조] 오류 발생: {e}")
            pass

    def _update_connected_lines(self, canvas_obj, landmark_index, x, y):
        """연결된 선들의 위치 업데이트 (현재 탭의 폴리곤에 포함된 연결선만)"""
        if canvas_obj == self.canvas_original:
            landmarks = self.custom_landmarks if self.custom_landmarks is not None else self.face_landmarks
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
            img = self.current_image
            line_ids = self.selected_landmark_lines_original
        else:
            landmarks = self.custom_landmarks if self.custom_landmarks is not None else None
            if landmarks is None:
                return
            pos_x = self.canvas_edited_pos_x
            pos_y = self.canvas_edited_pos_y
            img = self.edited_image
            line_ids = self.selected_landmark_lines_edited
        
        if landmarks is None or img is None or pos_x is None or pos_y is None:
            return
        
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            # 현재 탭에 해당하는 연결 정보 가져오기
            current_tab = getattr(self, 'current_morphing_tab', '눈')
            tab_connections = []
            
            if current_tab == '전체':
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE) +
                                 list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_NOSE) +
                                 list(mp_face_mesh.FACEMESH_LIPS) +
                                 list(mp_face_mesh.FACEMESH_FACE_OVAL))
            elif current_tab == '눈동자':
                # 눈동자 탭: 눈동자 연결선만
                try:
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    tab_connections = list(LEFT_IRIS) + list(RIGHT_IRIS)
                except AttributeError:
                    tab_connections = []
            elif current_tab == '눈':
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE) +
                                 list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW))
            elif current_tab == '눈썹':
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYEBROW) +
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW))
            elif current_tab == '코':
                tab_connections = list(mp_face_mesh.FACEMESH_NOSE)
            elif current_tab == '입':
                tab_connections = list(mp_face_mesh.FACEMESH_LIPS)
            elif current_tab == '턱선':
                tab_connections = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            elif current_tab == '윤곽':
                tab_connections = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            else:
                tab_connections = (list(mp_face_mesh.FACEMESH_LEFT_EYE) + 
                                 list(mp_face_mesh.FACEMESH_RIGHT_EYE))
            
            # 현재 탭의 연결 정보에서 선택된 포인트와 연결된 선 찾기
            connected_indices = set()
            for idx1, idx2 in tab_connections:
                if idx1 == landmark_index:
                    connected_indices.add(idx2)
                elif idx2 == landmark_index:
                    connected_indices.add(idx1)
            
            img_width, img_height = img.size
            display_size = getattr(canvas_obj, 'display_size', None)
            if display_size is None:
                return
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 연결된 선들 업데이트
            for i, connected_idx in enumerate(connected_indices):
                if i >= len(line_ids) or connected_idx >= len(landmarks):
                    continue
                
                if isinstance(landmarks[connected_idx], tuple):
                    conn_x, conn_y = landmarks[connected_idx]
                else:
                    conn_x = landmarks[connected_idx].x * img_width
                    conn_y = landmarks[connected_idx].y * img_height
                
                rel_conn_x = (conn_x - img_width / 2) * scale_x
                rel_conn_y = (conn_y - img_height / 2) * scale_y
                canvas_conn_x = pos_x + rel_conn_x
                canvas_conn_y = pos_y + rel_conn_y
                
                try:
                    canvas_obj.coords(line_ids[i], x, y, canvas_conn_x, canvas_conn_y)
                    canvas_obj.tag_raise(line_ids[i])
                except:
                    pass
        except Exception as e:
            print(f"[연결된 선들의 위치 업데이트] 오류 발생: {e}")
            pass
