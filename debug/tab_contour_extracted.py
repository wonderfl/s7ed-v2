    elif current_tab == '윤곽':
    # 얼굴 외곽선: MediaPipe 연결 정보 사용
    try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
    # 윤곽 탭의 랜드마크 인덱스 수집
    face_oval_indices_set = set()
    for idx1, idx2 in FACE_OVAL:
    face_oval_indices_set.add(idx1)
    face_oval_indices_set.add(idx2)
    # 확장 레벨에 따라 주변 포인트 추가
    if expansion_level > 0:
    try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
    tesselation_graph = {}
    for idx1, idx2 in tesselation:
    if idx1 < len(landmarks) and idx2 < len(landmarks):
    if idx1 not in tesselation_graph:
    tesselation_graph[idx1] = []
    if idx2 not in tesselation_graph:
    tesselation_graph[idx2] = []
    tesselation_graph[idx1].append(idx2)
    tesselation_graph[idx2].append(idx1)
    current_indices = face_oval_indices_set.copy()
    for level in range(expansion_level):
    next_level_indices = set()
    for idx in current_indices:
    if idx in tesselation_graph:
    for neighbor in tesselation_graph[idx]:
    if neighbor < len(landmarks):
    next_level_indices.add(neighbor)
    face_oval_indices_set.update(next_level_indices)
    current_indices = next_level_indices
    except ImportError:
    pass
    # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
    if canvas == self.canvas_original:
    for idx in face_oval_indices_set:
    if idx < len(landmarks):
    self.polygon_point_map_original[idx] = True
    elif canvas == self.canvas_edited:
    for idx in face_oval_indices_set:
    if idx < len(landmarks):
    self.polygon_point_map_edited[idx] = True
    face_oval_points = self._get_polygon_from_indices(
    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
    use_mediapipe_connections=True, connections=FACE_OVAL, expansion_level=expansion_level
    )
    if face_oval_points and len(face_oval_points) >= 3:
    # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
    if len(face_oval_points) % 4 == 0:
    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
    triangle_count = 0
    for i in range(0, len(face_oval_points), 4):
    if i + 4 <= len(face_oval_points):
    triangle_points = face_oval_points[i:i+4]
    polygon_id = canvas.create_polygon(
    triangle_points,
    fill="",
    outline=color,
    width=1,
    tags=("landmarks_polygon", "polygon_face_oval")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, face_oval_indices_set)
    triangle_count += 1
    else:
    # 단일 폴리곤 (폴백)
    polygon_id = canvas.create_polygon(
    face_oval_points,
    fill="",
    outline=color,
    width=2,
    tags=("landmarks_polygon", "polygon_face_oval")
    )
    items_list.append(polygon_id)
    bind_polygon_click_events(polygon_id, face_oval_indices_set)
    except ImportError:
    # 폴백: 인덱스 기반 (FACE_OVAL 인덱스는 연결 정보에서 추출)
    from utils.logger import get_logger
    logger = get_logger('얼굴편집')
    logger.warning("MediaPipe를 사용할 수 없어 얼굴 외곽선을 그릴 수 없음")
    except Exception as e:
    from utils.logger import get_logger
    logger = get_logger('얼굴편집')
    logger.error(f"폴리곤 그리기 실패: {e}", exc_info=True)
    import traceback
    traceback.print_exc()
