"""MediaPipe 눈동자 인덱스 확인"""
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
    
    left_set = set()
    for a, b in LEFT_IRIS:
        left_set.add(a)
        left_set.add(b)
    
    right_set = set()
    for a, b in RIGHT_IRIS:
        right_set.add(a)
        right_set.add(b)
    
    print(f"LEFT_IRIS 연결 수: {len(LEFT_IRIS)}")
    print(f"LEFT_IRIS 인덱스: {sorted(left_set)} ({len(left_set)}개)")
    print(f"RIGHT_IRIS 연결 수: {len(RIGHT_IRIS)}")
    print(f"RIGHT_IRIS 인덱스: {sorted(right_set)} ({len(right_set)}개)")
    print(f"총 인덱스: {len(left_set) + len(right_set)}개")
    print(f"전체 인덱스: {sorted(left_set | right_set)}")
except Exception as e:
    print(f"에러: {e}")
    import traceback
    traceback.print_exc()
