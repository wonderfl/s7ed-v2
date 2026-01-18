    if current_tab == '전체':
    # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 모든 부위의 폴리곤 그리기
    try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
    RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
    LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
    RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
    NOSE = list(mp_face_mesh.FACEMESH_NOSE)
    LIPS = list(mp_face_mesh.FACEMESH_LIPS)
    FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
    CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
    TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
    # 선택된 부위 확인
    selected_regions = []
    if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
    selected_regions.append(('face_oval', FACE_OVAL))
    if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
    selected_regions.append(('left_eye', LEFT_EYE))
    if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
    selected_regions.append(('right_eye', RIGHT_EYE))
    if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
    selected_regions.append(('left_eyebrow', LEFT_EYEBROW))
    if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
    selected_regions.append(('right_eyebrow', RIGHT_EYEBROW))
    if hasattr(self, 'show_nose') and self.show_nose.get():
    selected_regions.append(('nose', NOSE))
    # Lips를 하나로 통합
    if hasattr(self, 'show_lips') and self.show_lips.get():
    selected_regions.append(('lips', LIPS))
    if hasattr(self, 'show_contours') and self.show_contours.get():
    selected_regions.append(('contours', CONTOURS))
    if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
    selected_regions.append(('tesselation', TESSELATION))
    # 눈동자 연결 정보 (refine_landmarks=True일 때 사용 가능)
    try:
    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
    except AttributeError:
    # 구버전 MediaPipe에서는 지원하지 않을 수 있음
    LEFT_IRIS = []
    RIGHT_IRIS = []
    # 모든 부위의 폴리곤 그리기 함수
    def draw_polygon_mesh(connections, tag_name, part_name, target_indices=None):
    """연결 정보를 사용해서 폴리곤 메쉬 그리기"""
    # 연결 정보에서 모든 포인트 인덱스 수집
    polygon_indices_set = set()
    for idx1, idx2 in connections:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    polygon_indices_set.add(idx1)
    polygon_indices_set.add(idx2)
    # 확장 레벨에 따라 주변 포인트 추가
    if expansion_level > 0:
    try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
    # TESSELATION 그래프 구성
    tesselation_graph = {}
    for idx1, idx2 in tesselation:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    if idx1 not in tesselation_graph:
    tesselation_graph[idx1] = []
    if idx2 not in tesselation_graph:
    tesselation_graph[idx2] = []
    tesselation_graph[idx1].append(idx2)
    tesselation_graph[idx2].append(idx1)
    # 확장 레벨만큼 이웃 포인트 추가
    current_indices = polygon_indices_set.copy()
    for level in range(expansion_level):
    next_level_indices = set()
    for idx in current_indices:
    if idx in tesselation_graph:
    for neighbor in tesselation_graph[idx]:
    if neighbor < len(landmarks):
    next_level_indices.add(neighbor)
    polygon_indices_set.update(next_level_indices)
    current_indices = next_level_indices
    except ImportError:
    pass
    # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
    polygon_indices = list(polygon_indices_set)
    canvas_type = 'original' if canvas == self.canvas_original else 'edited'
    point_map = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
    for idx in polygon_indices:
    if idx < len(landmarks):
    point_map.add(idx)
    # 인덱스 표시 (폴리곤에 포함된 포인트들)
    if show_indices:
    for idx in polygon_indices:
    if idx < len(landmarks):
    # 랜드마크 좌표 가져오기
    pt = landmarks[idx]
    if isinstance(pt, tuple):
    img_x, img_y = pt
    else:
    img_x = pt.x * img_width
    img_y = pt.y * img_height
    # 캔버스 좌표로 변환
    rel_x = (img_x - img_width / 2) * scale_x
    rel_y = (img_y - img_height / 2) * scale_y
    canvas_x = pos_x + rel_x
    canvas_y = pos_y + rel_y
    # 인덱스 번호 표시
    text_offset = 10  # 포인트에서 약간 떨어진 위치
    text_id = canvas.create_text(
    canvas_x + text_offset,
    canvas_y - text_offset,
    text=str(idx),
    fill=color,
    font=("Arial", 12, "bold"),  # 글자 크기 8 -> 12로 증가
    tags=("landmarks_polygon", f"landmark_text_{idx}", tag_name)
    )
    items_list.append(text_id)
    # 텍스트를 최상위로 올림
    try:
    canvas.tag_raise(text_id, "landmarks_polygon")
    canvas.tag_raise(text_id)
    except Exception:
    pass
    # 확장 레벨 0일 때는 연결선으로 그리기 (폴리곤 대신)
    if expansion_level == 0:
    # 연결선 그리기
    for idx1, idx2 in connections:
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
    line_id = canvas.create_line(
    canvas_x1, canvas_y1, canvas_x2, canvas_y2,
    fill=color, width=2, tags=("landmarks_polygon", tag_name)
    )
    items_list.append(line_id)
    # 연결선에도 클릭 이벤트 바인딩 (폴리곤과 동일하게)
    bind_polygon_click_events(line_id, target_indices)
    else:
    # 확장 레벨 > 0일 때는 폴리곤으로 그리기
    points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=connections, expansion_level=expansion_level
    )
    if points and len(points) >= 3:
    if len(points) % 4 == 0:
    # 삼각형 메쉬
    triangle_count = 0
    for i in range(0, len(points), 4):
    if i + 4 <= len(points):
    triangle_points = points[i:i+4]
    polygon_id = canvas.create_polygon(
    triangle_points,
    fill="",
    outline=color,
    width=1,
    tags=("landmarks_polygon", tag_name)
    )
    items_list.append(polygon_id)
    # 폴리곤 클릭 이벤트 바인딩
    bind_polygon_click_events(polygon_id, target_indices)
    triangle_count += 1
    else:
    # 단일 폴리곤 (폴백)
    polygon_id = canvas.create_polygon(
    points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", tag_name)
    )
    items_list.append(polygon_id)
    # 폴리곤 클릭 이벤트 바인딩
    bind_polygon_click_events(polygon_id, target_indices)
    # 각 부위의 랜드마크 인덱스 수집
    left_eye_indices = set()
    right_eye_indices = set()
    left_eyebrow_indices = set()
    right_eyebrow_indices = set()
    nose_indices = set()
    lips_indices = set()
    face_oval_indices = set()
    for idx1, idx2 in LEFT_EYE:
    left_eye_indices.add(idx1)
    left_eye_indices.add(idx2)
    for idx1, idx2 in RIGHT_EYE:
    right_eye_indices.add(idx1)
    right_eye_indices.add(idx2)
    for idx1, idx2 in LEFT_EYEBROW:
    left_eyebrow_indices.add(idx1)
    left_eyebrow_indices.add(idx2)
    for idx1, idx2 in RIGHT_EYEBROW:
    right_eyebrow_indices.add(idx1)
    right_eyebrow_indices.add(idx2)
    for idx1, idx2 in NOSE:
    nose_indices.add(idx1)
    nose_indices.add(idx2)
    for idx1, idx2 in LIPS:
    lips_indices.add(idx1)
    lips_indices.add(idx2)
    for idx1, idx2 in FACE_OVAL:
    face_oval_indices.add(idx1)
    face_oval_indices.add(idx2)
    # 선택된 부위만 폴리곤 그리기
    if len(selected_regions) > 0:
    # 선택된 부위만 그리기
    for region_name, connections in selected_regions:
    if region_name == 'left_eye':
    draw_polygon_mesh(LEFT_EYE, "polygon_left_eye", "왼쪽 눈", None)
    elif region_name == 'right_eye':
    draw_polygon_mesh(RIGHT_EYE, "polygon_right_eye", "오른쪽 눈", None)
    elif region_name == 'left_eyebrow':
    draw_polygon_mesh(LEFT_EYEBROW, "polygon_left_eyebrow", "왼쪽 눈썹", None)
    elif region_name == 'right_eyebrow':
    draw_polygon_mesh(RIGHT_EYEBROW, "polygon_right_eyebrow", "오른쪽 눈썹", None)
    elif region_name == 'nose':
    draw_polygon_mesh(NOSE, "polygon_nose", "코", None)
    elif region_name == 'lips':
    draw_polygon_mesh(LIPS, "polygon_lips", "Lips", None)
    elif region_name == 'face_oval':
    draw_polygon_mesh(FACE_OVAL, "polygon_face_oval", "Face Oval", None)
    elif region_name == 'contours':
    draw_polygon_mesh(CONTOURS, "polygon_contours", "Contours", None)
    elif region_name == 'tesselation':
    draw_polygon_mesh(TESSELATION, "polygon_tesselation", "Tesselation", None)
    # Tesselation 선택 시 눈동자도 함께 그리기
    if LEFT_IRIS and len(landmarks) > 468:
    # MediaPipe의 실제 인덱스 추출 (정의된 연결 정보만 사용)
    left_iris_indices_set = set()
    for idx1, idx2 in LEFT_IRIS:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    left_iris_indices_set.add(idx1)
    left_iris_indices_set.add(idx2)
    right_iris_indices_set = set()
    for idx1, idx2 in RIGHT_IRIS:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    right_iris_indices_set.add(idx1)
    right_iris_indices_set.add(idx2)
    # 모든 눈동자 인덱스 세트
    all_iris_indices_set = left_iris_indices_set | right_iris_indices_set
    # custom_landmarks를 사용할 때는 눈동자 폴리곤을 그리지 않음 (중앙 포인트만 표시)
    # MediaPipe의 실제 인덱스가 landmarks에 존재하는지 확인
    # 단, custom_landmarks를 사용 중이고 중앙 포인트가 추가되었다면 (길이가 원본보다 작거나 같고 중앙 포인트 인덱스가 있으면) 눈동자 포인트가 제거된 것으로 간주
    has_iris_points = (len(all_iris_indices_set) > 0 and 
    all(idx < len(landmarks) for idx in all_iris_indices_set))
    # custom_landmarks를 사용 중이고, 중앙 포인트 인덱스가 설정되어 있으면 눈동자 포인트가 제거된 것으로 간주
    has_center_points = (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None and
    hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None)
    # custom_landmarks 확인 (LandmarkManager 사용)
    # force_use_custom이 True이면 강제로 custom_landmarks 사용
    if force_use_custom:
    is_custom = True
    elif hasattr(self, 'landmark_manager'):
    custom = self.landmark_manager.get_custom_landmarks()
    # get_custom_landmarks()는 복사본을 반환하므로 길이만 비교 (성능 최적화)
    is_custom = (custom is not None and landmarks is not None and len(landmarks) == len(custom))
    else:
    is_custom = (hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and 
    landmarks is not None and
    (landmarks is self.custom_landmarks or 
    len(landmarks) == len(self.custom_landmarks)))
    use_custom = (is_custom and (not has_iris_points or has_center_points))
    print(f"[폴리곤렌더러] Tesselation 탭 - 왼쪽 눈동자: has_iris_points={has_iris_points}, use_custom={use_custom}, landmarks 길이={len(landmarks)}, left_iris_indices={sorted(left_iris_indices_set)}")
    if not use_custom:
    # 원본 랜드마크를 사용할 때만 폴리곤 그리기
    left_iris_points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=LEFT_IRIS, expansion_level=0
    )
    if left_iris_points and len(left_iris_points) >= 3:
    polygon_id = canvas.create_polygon(
    left_iris_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_left_iris")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, None)
    # 눈동자 포인트 인덱스(468-477)는 polygon_point_map에 저장하지 않음
    # 중앙 포인트만 저장 (나중에 추가됨)
    else:
    # custom_landmarks를 사용할 때는 인덱스 세트만 생성 (중앙 포인트 계산용)
    # 이미 위에서 left_iris_indices_set 생성됨
    pass
    # 왼쪽 눈동자 중앙 포인트 표시 (폴리곤 조건과 독립적으로)
    # LEFT_IRIS에서 추출한 실제 인덱스 사용
    left_iris_indices_list = list(left_iris_indices_set)
    left_iris_coords = []
    for idx in left_iris_indices_list:
    if idx < len(landmarks):
    pt = landmarks[idx]
    if isinstance(pt, tuple):
    img_x, img_y = pt
    else:
    img_x = pt.x * img_width
    img_y = pt.y * img_height
    left_iris_coords.append((img_x, img_y))
    # 중앙 포인트 좌표 계산 (방법 A: 배열 끝 인덱스 직접 사용)
    center_x = None
    center_y = None
    # custom_landmarks를 사용할 때는 배열 끝 인덱스에서 직접 가져오기
    # custom_landmarks에는 눈동자 포인트가 제거되고 중앙 포인트가 추가되어 있음
    if use_custom and len(landmarks) >= 2:
    # 중앙 포인트 인덱스: 왼쪽=len-2, 오른쪽=len-1
    left_center_idx = len(landmarks) - 2
    if left_center_idx >= 0 and left_center_idx < len(landmarks):
    center_pt = landmarks[left_center_idx]
    if isinstance(center_pt, tuple):
    center_x, center_y = center_pt
    else:
    center_x = center_pt.x * img_width
    center_y = center_pt.y * img_height
    # 계산된 좌표 저장 (다음 렌더링에서 사용)
    self._left_iris_center_coord = (center_x, center_y)
    elif hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None:
    # 원본 랜드마크를 사용할 때는 저장된 좌표 사용 (드래그로 이동한 경우)
    center_x, center_y = self._left_iris_center_coord
    elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
    # 원본 랜드마크에서 계산
    # original_landmarks 가져오기 (LandmarkManager 사용)
    if hasattr(self, 'landmark_manager'):
    original = self.landmark_manager.get_original_landmarks()
    else:
    original = self.original_landmarks if hasattr(self, 'original_landmarks') else None
    if original is not None:
    # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
    # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
    # 사용자 관점: 왼쪽 = MediaPipe RIGHT_IRIS
    _, right_iris_indices = self._get_iris_indices()
    center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
    if center is not None:
    center_x, center_y = center
    # 계산된 좌표 저장
    self._left_iris_center_coord = center
    else:
    # 폴백: landmarks에서 직접 계산
    if left_iris_coords:
    center_x = sum(c[0] for c in left_iris_coords) / len(left_iris_coords)
    center_y = sum(c[1] for c in left_iris_coords) / len(left_iris_coords)
    if center_x is not None and center_y is not None:
    # 캔버스 좌표로 변환
    rel_x = (center_x - img_width / 2) * scale_x
    rel_y = (center_y - img_height / 2) * scale_y
    canvas_x = pos_x + rel_x
    canvas_y = pos_y + rel_y
    # 중앙 포인트를 원으로 표시 (더 크게 표시하여 클릭하기 쉽게)
    center_radius = 8
    center_id = canvas.create_oval(
    canvas_x - center_radius,
    canvas_y - center_radius,
    canvas_x + center_radius,
    canvas_y + center_radius,
    fill="yellow",
    outline="red",
    width=2,
    tags=("landmarks_polygon", "iris_center_left")
    )
    items_list.append(center_id)
    # 중앙 포인트 인덱스 표시 (인덱스 표시가 활성화된 경우)
    if show_indices:
    text_offset = center_radius + 5
    # custom_landmarks에는 중앙 포인트가 추가되어 있음
    if use_custom and len(landmarks) >= 2:
    left_center_idx = len(landmarks) - 2
    index_text = str(left_center_idx)
    else:
    index_text = "C-L"
    text_id = canvas.create_text(
    canvas_x + text_offset,
    canvas_y - text_offset,
    text=index_text,
    fill="red",
    font=("Arial", 12, "bold"),
    tags=("landmarks_polygon", "iris_center_left_text", "iris_center_left")
    )
    items_list.append(text_id)
    # 중앙 포인트 드래그 이벤트 바인딩 (좌표 기반)
    def on_left_iris_center_click(event):
    print(f"[얼굴편집] 왼쪽 눈동자 중앙 포인트 클릭")
    self.on_iris_center_drag_start(event, 'left', canvas)
    return "break"
    def on_left_iris_center_drag(event):
    self.on_iris_center_drag(event, 'left', canvas)
    return "break"
    def on_left_iris_center_release(event):
    self.on_iris_center_drag_end(event, 'left', canvas)
    return "break"
    canvas.tag_bind(center_id, "<Button-1>", on_left_iris_center_click)
    canvas.tag_bind(center_id, "<B1-Motion>", on_left_iris_center_drag)
    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_left_iris_center_release)
    if RIGHT_IRIS and len(landmarks) > 468:
    # MediaPipe의 실제 인덱스 추출 (왼쪽에서 이미 생성했지만 명확성을 위해)
    if 'right_iris_indices_set' not in locals():
    right_iris_indices_set = set()
    for idx1, idx2 in RIGHT_IRIS:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    right_iris_indices_set.add(idx1)
    right_iris_indices_set.add(idx2)
    # 모든 눈동자 인덱스 세트 (왼쪽과 오른쪽 합침)
    if 'left_iris_indices_set' in locals():
    all_iris_indices_set = left_iris_indices_set | right_iris_indices_set
    else:
    all_iris_indices_set = right_iris_indices_set
    # custom_landmarks를 사용할 때는 눈동자 폴리곤을 그리지 않음 (중앙 포인트만 표시)
    # MediaPipe의 실제 인덱스가 landmarks에 존재하는지 확인
    # 단, custom_landmarks를 사용 중이고 중앙 포인트가 추가되었다면 (길이가 원본보다 작거나 같고 중앙 포인트 인덱스가 있으면) 눈동자 포인트가 제거된 것으로 간주
    has_iris_points = (len(all_iris_indices_set) > 0 and 
    all(idx < len(landmarks) for idx in all_iris_indices_set))
    # custom_landmarks를 사용 중이고, 중앙 포인트 좌표가 설정되어 있으면 눈동자 포인트가 제거된 것으로 간주
    has_center_points = (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None and
    hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None)
    use_custom = (hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and 
    (landmarks is self.custom_landmarks) and (not has_iris_points or has_center_points))
    print(f"[폴리곤렌더러] Tesselation 탭 - 오른쪽 눈동자: has_iris_points={has_iris_points}, use_custom={use_custom}, landmarks 길이={len(landmarks)}, right_iris_indices={sorted(right_iris_indices_set)}")
    if not use_custom:
    # 원본 랜드마크를 사용할 때만 폴리곤 그리기
    right_iris_points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=RIGHT_IRIS, expansion_level=0
    )
    if right_iris_points and len(right_iris_points) >= 3:
    polygon_id = canvas.create_polygon(
    right_iris_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_right_iris")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, None)
    # 눈동자 포인트 인덱스(468-477)는 polygon_point_map에 저장하지 않음
    # 중앙 포인트만 저장 (나중에 추가됨)
    else:
    # custom_landmarks를 사용할 때는 인덱스 세트만 생성 (중앙 포인트 계산용)
    # 이미 위에서 right_iris_indices_set 생성됨
    pass
    # 오른쪽 눈동자 중앙 포인트 표시 (폴리곤 조건과 독립적으로)
    # RIGHT_IRIS에서 추출한 실제 인덱스 사용
    right_iris_indices_list = list(right_iris_indices_set)
    right_iris_coords = []
    for idx in right_iris_indices_list:
    if idx < len(landmarks):
    pt = landmarks[idx]
    if isinstance(pt, tuple):
    img_x, img_y = pt
    else:
    img_x = pt.x * img_width
    img_y = pt.y * img_height
    right_iris_coords.append((img_x, img_y))
    # 중앙 포인트 좌표 계산 (방법 A: 배열 끝 인덱스 직접 사용)
    center_x = None
    center_y = None
    # custom_landmarks를 사용할 때는 배열 끝 인덱스에서 직접 가져오기
    # custom_landmarks에는 눈동자 포인트가 제거되고 중앙 포인트가 추가되어 있음
    # morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저 (len-2), MediaPipe RIGHT_IRIS 나중 (len-1)
    # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
    # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
    # 따라서: len-2 = MediaPipe LEFT_IRIS (사용자 왼쪽), len-1 = MediaPipe RIGHT_IRIS (사용자 오른쪽)
    if use_custom and len(landmarks) >= 2:
    # 중앙 포인트 인덱스: 사용자 왼쪽=len-2 (MediaPipe LEFT_IRIS), 사용자 오른쪽=len-1 (MediaPipe RIGHT_IRIS)
    right_center_idx = len(landmarks) - 1  # MediaPipe RIGHT_IRIS = 사용자 오른쪽
    if right_center_idx >= 0 and right_center_idx < len(landmarks):
    center_pt = landmarks[right_center_idx]
    if isinstance(center_pt, tuple):
    center_x, center_y = center_pt
    else:
    center_x = center_pt.x * img_width
    center_y = center_pt.y * img_height
    # 계산된 좌표 저장 (다음 렌더링에서 사용)
    self._right_iris_center_coord = (center_x, center_y)
    elif hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None:
    # 원본 랜드마크를 사용할 때는 저장된 좌표 사용 (드래그로 이동한 경우)
    center_x, center_y = self._right_iris_center_coord
    elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
    # 원본 랜드마크에서 계산
    # original_landmarks 가져오기 (LandmarkManager 사용)
    if hasattr(self, 'landmark_manager'):
    original = self.landmark_manager.get_original_landmarks()
    else:
    original = self.original_landmarks if hasattr(self, 'original_landmarks') else None
    if original is not None:
    # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
    # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
    # 사용자 관점: 오른쪽 = MediaPipe LEFT_IRIS
    left_iris_indices, _ = self._get_iris_indices()
    center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
    if center is not None:
    center_x, center_y = center
    # 계산된 좌표 저장
    self._right_iris_center_coord = center
    else:
    # 폴백: landmarks에서 직접 계산
    if right_iris_coords:
    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
    if center_x is not None and center_y is not None:
    # 캔버스 좌표로 변환
    rel_x = (center_x - img_width / 2) * scale_x
    rel_y = (center_y - img_height / 2) * scale_y
    canvas_x = pos_x + rel_x
    canvas_y = pos_y + rel_y
    # 중앙 포인트를 원으로 표시 (더 크게 표시하여 클릭하기 쉽게)
    center_radius = 8
    center_id = canvas.create_oval(
    canvas_x - center_radius,
    canvas_y - center_radius,
    canvas_x + center_radius,
    canvas_y + center_radius,
    fill="yellow",
    outline="red",
    width=2,
    tags=("landmarks_polygon", "iris_center_right")
    )
    items_list.append(center_id)
    # 중앙 포인트 인덱스 표시 (인덱스 표시가 활성화된 경우)
    if show_indices:
    text_offset = center_radius + 5
    # custom_landmarks에는 중앙 포인트가 추가되어 있음
    if use_custom and len(landmarks) >= 2:
    right_center_idx = len(landmarks) - 1
    index_text = str(right_center_idx)
    else:
    index_text = "C-R"
    text_id = canvas.create_text(
    canvas_x + text_offset,
    canvas_y - text_offset,
    text=index_text,
    fill="red",
    font=("Arial", 12, "bold"),
    tags=("landmarks_polygon", "iris_center_right_text", "iris_center_right")
    )
    items_list.append(text_id)
    # 중앙 포인트 드래그 이벤트 바인딩 (좌표 기반)
    def on_right_iris_center_click(event):
    print(f"[얼굴편집] 오른쪽 눈동자 중앙 포인트 클릭")
    self.on_iris_center_drag_start(event, 'right', canvas)
    return "break"
    def on_right_iris_center_drag(event):
    self.on_iris_center_drag(event, 'right', canvas)
    return "break"
    def on_right_iris_center_release(event):
    self.on_iris_center_drag_end(event, 'right', canvas)
    return "break"
    canvas.tag_bind(center_id, "<Button-1>", on_right_iris_center_click)
    canvas.tag_bind(center_id, "<B1-Motion>", on_right_iris_center_drag)
    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_right_iris_center_release)
    # 선택된 부위가 없으면 아무것도 그리지 않음
    # 왼쪽 눈동자 (별도로 그리기) - Tesselation이 선택되지 않았을 때만
    # 왼쪽 눈동자를 선택했을 때 왼쪽 눈도 함께 그려야 함
    if (hasattr(self, 'show_left_iris') and self.show_left_iris.get() and 
    not (hasattr(self, 'show_tesselation') and self.show_tesselation.get()) and
    LEFT_IRIS and len(landmarks) > 468):
    # 왼쪽 눈동자만 선택했을 때는 눈 부위를 함께 그리지 않음
    left_iris_indices_set = set()
    for idx1, idx2 in LEFT_IRIS:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    left_iris_indices_set.add(idx1)
    left_iris_indices_set.add(idx2)
    # 눈동자 중심점(468)도 인덱스에 추가
    if 468 < len(landmarks):
    left_iris_indices_set.add(468)
    # custom_landmarks를 사용할 때는 눈동자 폴리곤을 그리지 않음 (중앙 포인트만 표시)
    # 눈동자 포인트 인덱스(468-477)가 landmarks에 존재하는지 확인
    # 단, custom_landmarks를 사용 중이고 중앙 포인트가 추가되었다면 눈동자 포인트가 제거된 것으로 간주
    try:
    from utils.face_morphing.region_extraction import get_iris_indices
    left_iris_indices, right_iris_indices = get_iris_indices()
    all_iris_indices = left_iris_indices + right_iris_indices
    max_iris_index = max(all_iris_indices) if all_iris_indices else 0
    has_iris_points = (len(landmarks) > max_iris_index and 
    all(idx < len(landmarks) for idx in all_iris_indices))
    except ImportError:
    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
    has_iris_points = (len(landmarks) > 477 and 
    all(idx < len(landmarks) for idx in [469, 470, 471, 472, 474, 475, 476, 477]))
    # custom_landmarks를 사용 중이고, 중앙 포인트 인덱스가 설정되어 있으면 눈동자 포인트가 제거된 것으로 간주
    has_center_points = (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None and
    hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None)
    use_custom = (hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and 
    (landmarks is self.custom_landmarks) and (not has_iris_points or has_center_points))
    print(f"[폴리곤렌더러] 눈 탭 - 왼쪽 눈동자: has_iris_points={has_iris_points}, use_custom={use_custom}, landmarks 길이={len(landmarks)}, landmarks is custom_landmarks={landmarks is self.custom_landmarks if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None else False}")
    if not use_custom:
    # 원본 랜드마크를 사용할 때만 폴리곤 그리기
    print(f"[폴리곤렌더러] 왼쪽 눈동자 폴리곤 그리기 시작")
    left_iris_points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=LEFT_IRIS, expansion_level=0
    )
    if left_iris_points and len(left_iris_points) >= 3:
    polygon_id = canvas.create_polygon(
    left_iris_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_left_iris")
    )
    items_list.append(polygon_id)
    # 폴리곤 클릭 이벤트 바인딩
    bind_polygon_click_events(polygon_id, None)
    # 눈동자 포인트 인덱스(468-477)는 polygon_point_map에 저장하지 않음
    # 중앙 포인트만 저장 (나중에 추가됨)
    # 왼쪽 눈동자 중앙 포인트 표시 (폴리곤 조건과 독립적으로)
    # 좌표 기반으로 계산 (custom_landmarks는 수정하지 않음)
    center_x = None
    center_y = None
    # 드래그로 이동한 좌표가 있으면 사용, 없으면 original_landmarks에서 계산
    if hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None:
    center_x, center_y = self._left_iris_center_coord
    elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
    # original_landmarks 가져오기 (LandmarkManager 사용)
    if hasattr(self, 'landmark_manager'):
    original = self.landmark_manager.get_original_landmarks()
    else:
    original = self.original_landmarks if hasattr(self, 'original_landmarks') else None
    if original is not None:
    left_iris_indices, _ = self._get_iris_indices()
    center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
    if center is not None:
    center_x, center_y = center
    # 계산된 좌표 저장
    self._left_iris_center_coord = center
    else:
    # 폴백: landmarks에서 직접 계산
    left_iris_indices_list = list(left_iris_indices_set)
    left_iris_coords = []
    for idx in left_iris_indices_list:
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
    if center_x is not None and center_y is not None:
    # 캔버스 좌표로 변환
    rel_x = (center_x - img_width / 2) * scale_x
    rel_y = (center_y - img_height / 2) * scale_y
    canvas_x = pos_x + rel_x
    canvas_y = pos_y + rel_y
    # 중앙 포인트를 원으로 표시
    center_radius = 5
    center_id = canvas.create_oval(
    canvas_x - center_radius,
    canvas_y - center_radius,
    canvas_x + center_radius,
    canvas_y + center_radius,
    fill="yellow",
    outline="red",
    width=2,
    tags=("landmarks_polygon", "iris_center_left")
    )
    items_list.append(center_id)
    # 중앙 포인트 인덱스 표시 (인덱스 표시가 활성화된 경우)
    if show_indices:
    text_offset = center_radius + 5
    # 실제 인덱스 계산: custom_landmarks 길이에서 중앙 포인트 인덱스 계산
    # custom_landmarks는 원본 478개에서 눈동자 10개 제거 후 중앙 포인트 2개 추가 = 470개
    # 중앙 포인트는 마지막 2개: 추가 순서는 left_iris_center 먼저 (len-2), right_iris_center 나중 (len-1)
    # 하지만 렌더러에서 순서를 바꿨으므로: 왼쪽=len-1, 오른쪽=len-2
    if use_custom and landmarks is not None:
    # custom_landmarks를 사용할 때: 마지막 2개가 중앙 포인트
    # 렌더러와 일치하도록 순서 바꿈
    left_center_idx = len(landmarks) - 1  # 렌더러와 일치
    right_center_idx = len(landmarks) - 2  # 렌더러와 일치
    index_text = str(left_center_idx)
    else:
    # 원본 랜드마크를 사용할 때는 "C-L" 표시
    index_text = "C-L"
    text_id = canvas.create_text(
    canvas_x + text_offset,
    canvas_y - text_offset,
    text=index_text,
    fill="red",
    font=("Arial", 12, "bold"),
    tags=("landmarks_polygon", "iris_center_left_text", "iris_center_left")
    )
    items_list.append(text_id)
    # 중앙 포인트 드래그 이벤트 바인딩 (좌표 기반)
    def on_left_iris_center_click(event):
    print(f"[얼굴편집] 왼쪽 눈동자 중앙 포인트 클릭")
    self.on_iris_center_drag_start(event, 'left', canvas)
    return "break"
    def on_left_iris_center_drag(event):
    self.on_iris_center_drag(event, 'left', canvas)
    return "break"
    def on_left_iris_center_release(event):
    self.on_iris_center_drag_end(event, 'left', canvas)
    return "break"
    canvas.tag_bind(center_id, "<Button-1>", on_left_iris_center_click)
    canvas.tag_bind(center_id, "<B1-Motion>", on_left_iris_center_drag)
    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_left_iris_center_release)
    # 오른쪽 눈동자 (별도로 그리기) - 선택된 부위에 포함된 경우만
    if (hasattr(self, 'show_right_iris') and self.show_right_iris.get() and 
    not (hasattr(self, 'show_tesselation') and self.show_tesselation.get()) and
    RIGHT_IRIS and len(landmarks) > 468):
    right_iris_indices_set = set()
    for idx1, idx2 in RIGHT_IRIS:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    right_iris_indices_set.add(idx1)
    right_iris_indices_set.add(idx2)
    # 눈동자 중심점(473)도 인덱스에 추가
    if 473 < len(landmarks):
    right_iris_indices_set.add(473)
    # custom_landmarks를 사용할 때는 눈동자 폴리곤을 그리지 않음 (중앙 포인트만 표시)
    # 눈동자 포인트 인덱스(468-477)가 landmarks에 존재하는지 확인
    # 단, custom_landmarks를 사용 중이고 중앙 포인트가 추가되었다면 눈동자 포인트가 제거된 것으로 간주
    try:
    from utils.face_morphing.region_extraction import get_iris_indices
    left_iris_indices, right_iris_indices = get_iris_indices()
    all_iris_indices = left_iris_indices + right_iris_indices
    max_iris_index = max(all_iris_indices) if all_iris_indices else 0
    has_iris_points = (len(landmarks) > max_iris_index and 
    all(idx < len(landmarks) for idx in all_iris_indices))
    except ImportError:
    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
    has_iris_points = (len(landmarks) > 477 and 
    all(idx < len(landmarks) for idx in [469, 470, 471, 472, 474, 475, 476, 477]))
    # custom_landmarks를 사용 중이고, 중앙 포인트 인덱스가 설정되어 있으면 눈동자 포인트가 제거된 것으로 간주
    has_center_points = (hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None and
    hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None)
    use_custom = (hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and 
    (landmarks is self.custom_landmarks) and (not has_iris_points or has_center_points))
    print(f"[폴리곤렌더러] 눈 탭 - 오른쪽 눈동자: has_iris_points={has_iris_points}, use_custom={use_custom}, landmarks 길이={len(landmarks)}")
    if not use_custom:
    # 원본 랜드마크를 사용할 때만 폴리곤 그리기
    print(f"[폴리곤렌더러] 오른쪽 눈동자 폴리곤 그리기 시작")
    right_iris_points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=RIGHT_IRIS, expansion_level=0
    )
    if right_iris_points and len(right_iris_points) >= 3:
    polygon_id = canvas.create_polygon(
    right_iris_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_right_iris")
    )
    items_list.append(polygon_id)
    # 폴리곤 클릭 이벤트 바인딩
    bind_polygon_click_events(polygon_id, None)
    # 눈동자 포인트 인덱스(468-477)는 polygon_point_map에 저장하지 않음
    # 중앙 포인트만 저장 (나중에 추가됨)
    # 오른쪽 눈동자 중앙 포인트 표시 (폴리곤 조건과 독립적으로)
    # RIGHT_IRIS에서 추출한 실제 인덱스 사용
    right_iris_indices_list = list(right_iris_indices_set)
    right_iris_coords = []
    for idx in right_iris_indices_list:
    if idx < len(landmarks):
    pt = landmarks[idx]
    if isinstance(pt, tuple):
    img_x, img_y = pt
    else:
    img_x = pt.x * img_width
    img_y = pt.y * img_height
    right_iris_coords.append((img_x, img_y))
    # 중앙 포인트를 배열에 추가하고 인덱스 확인
    center_x = None
    center_y = None
    center_index = None
    # custom_landmarks에 중앙 포인트 추가 및 인덱스 확인
    # 중앙 포인트 좌표 계산 (좌표 기반)
    center_x = None
    center_y = None
    # 드래그로 이동한 좌표가 있으면 사용, 없으면 original_landmarks에서 계산
    if hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None:
    center_x, center_y = self._right_iris_center_coord
    elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
    # original_landmarks 가져오기 (LandmarkManager 사용)
    if hasattr(self, 'landmark_manager'):
    original = self.landmark_manager.get_original_landmarks()
    else:
    original = self.original_landmarks if hasattr(self, 'original_landmarks') else None
    if original is not None:
    _, right_iris_indices = self._get_iris_indices()
    center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
    if center is not None:
    center_x, center_y = center
    # 계산된 좌표 저장
    self._right_iris_center_coord = center
    else:
    # 폴백: landmarks에서 직접 계산
    if right_iris_coords:
    center_x = sum(c[0] for c in right_iris_coords) / len(right_iris_coords)
    center_y = sum(c[1] for c in right_iris_coords) / len(right_iris_coords)
    if center_x is not None and center_y is not None:
    # 캔버스 좌표로 변환
    rel_x = (center_x - img_width / 2) * scale_x
    rel_y = (center_y - img_height / 2) * scale_y
    canvas_x = pos_x + rel_x
    canvas_y = pos_y + rel_y
    # 중앙 포인트를 원으로 표시
    center_radius = 5
    center_id = canvas.create_oval(
    canvas_x - center_radius,
    canvas_y - center_radius,
    canvas_x + center_radius,
    canvas_y + center_radius,
    fill="yellow",
    outline="red",
    width=2,
    tags=("landmarks_polygon", "iris_center_right")
    )
    items_list.append(center_id)
    # 중앙 포인트 인덱스 표시 (인덱스 표시가 활성화된 경우)
    if show_indices:
    text_offset = center_radius + 5
    # 실제 인덱스 계산: custom_landmarks 길이에서 중앙 포인트 인덱스 계산
    # custom_landmarks는 원본 478개에서 눈동자 10개 제거 후 중앙 포인트 2개 추가 = 470개
    # 중앙 포인트는 마지막 2개: 추가 순서는 left_iris_center 먼저 (len-2), right_iris_center 나중 (len-1)
    # 하지만 렌더러에서 순서를 바꿨으므로: 왼쪽=len-1, 오른쪽=len-2
    if use_custom and landmarks is not None:
    # custom_landmarks를 사용할 때: 마지막 2개가 중앙 포인트
    # 렌더러와 일치하도록 순서 바꿈
    left_center_idx = len(landmarks) - 1  # 렌더러와 일치
    right_center_idx = len(landmarks) - 2  # 렌더러와 일치
    index_text = str(right_center_idx)
    else:
    # 원본 랜드마크를 사용할 때는 "C-R" 표시
    index_text = "C-R"
    text_id = canvas.create_text(
    canvas_x + text_offset,
    canvas_y - text_offset,
    text=index_text,
    fill="red",
    font=("Arial", 12, "bold"),
    tags=("landmarks_polygon", "iris_center_right_text", "iris_center_right")
    )
    items_list.append(text_id)
    # 중앙 포인트 드래그 이벤트 바인딩 (좌표 기반)
    def on_right_iris_center_click(event):
    print(f"[얼굴편집] 오른쪽 눈동자 중앙 포인트 클릭")
    self.on_iris_center_drag_start(event, 'right', canvas)
    return "break"
    def on_right_iris_center_drag(event):
    self.on_iris_center_drag(event, 'right', canvas)
    return "break"
    def on_right_iris_center_release(event):
    self.on_iris_center_drag_end(event, 'right', canvas)
    return "break"
    canvas.tag_bind(center_id, "<Button-1>", on_right_iris_center_click)
    canvas.tag_bind(center_id, "<B1-Motion>", on_right_iris_center_drag)
    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_right_iris_center_release)
    # 선택된 부위가 없으면 아무것도 그리지 않음
    except ImportError:
    # MediaPipe가 없으면 인덱스 기반으로 폴백
    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
    RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
    NOSE_INDICES = [8, 240, 98, 164, 327, 460, 4]
    OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
    INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
    MOUTH_ALL_INDICES = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))
    jaw_indices = list(range(17))  # 0-16
    # 눈 탭인 경우 눈썹 제외
    if current_tab == '눈':
    # 눈과 눈동자만 포함
    eye_indices_set = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
    # 눈동자 인덱스 추가 (MediaPipe 정의 사용)
    try:
    from utils.face_morphing.region_extraction import get_iris_indices
    left_iris_indices, right_iris_indices = get_iris_indices()
    iris_indices = left_iris_indices + right_iris_indices
    min_iris_index = min(iris_indices) if iris_indices else 468
    except ImportError:
    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
    iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
    min_iris_index = 469
    if len(landmarks) > min_iris_index:
    for idx in iris_indices:
    if idx < len(landmarks):
    eye_indices_set.add(idx)
    # 왼쪽 눈 폴리곤
    left_eye_points = self._get_polygon_from_indices(LEFT_EYE_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
    if left_eye_points and len(left_eye_points) >= 3:
    polygon_id = canvas.create_polygon(
    left_eye_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_left_eye")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, eye_indices_set)
    # 오른쪽 눈 폴리곤
    right_eye_points = self._get_polygon_from_indices(RIGHT_EYE_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
    if right_eye_points and len(right_eye_points) >= 3:
    polygon_id = canvas.create_polygon(
    right_eye_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_right_eye")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, eye_indices_set)
    else:
    # 전체 탭: 모든 부위 폴리곤 그리기
    for indices, tag_name, part_name in [
    (LEFT_EYE_INDICES, "polygon_left_eye", "왼쪽 눈"),
    (RIGHT_EYE_INDICES, "polygon_right_eye", "오른쪽 눈"),
    (LEFT_EYEBROW_INDICES, "polygon_left_eyebrow", "왼쪽 눈썹"),
    (RIGHT_EYEBROW_INDICES, "polygon_right_eyebrow", "오른쪽 눈썹"),
    (NOSE_INDICES, "polygon_nose", "코"),
    (MOUTH_ALL_INDICES, "polygon_lips", "입"),
    (jaw_indices, "polygon_jaw", "턱선")
    ]:
    # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
    if canvas == self.canvas_original:
    for idx in indices:
    if idx < len(landmarks):
    self.polygon_point_map_original.add(idx)
    elif canvas == self.canvas_edited:
    for idx in indices:
    if idx < len(landmarks):
    self.polygon_point_map_edited.add(idx)
    points = self._get_polygon_from_indices(indices, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
    if points and len(points) >= 3:
    polygon_id = canvas.create_polygon(
    points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", tag_name)
    )
    items_list.append(polygon_id)
    # 폴리곤 클릭 이벤트 바인딩 (전체 탭이므로 None)
    bind_polygon_click_events(polygon_id, None)
    from utils.logger import get_logger
    logger = get_logger('얼굴편집')
    logger.debug(f"{part_name} 폴리곤 그리기 (폴백): {len(points)}개 포인트")
