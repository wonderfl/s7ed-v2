"""MediaPipe 눈동자 인덱스 상세 확인"""
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
    
    print("=" * 80)
    print("MediaPipe FACEMESH_LEFT_IRIS 연결:")
    print("=" * 80)
    for i, (a, b) in enumerate(LEFT_IRIS):
        print(f"  연결 {i}: {a} <-> {b}")
    
    left_set = set()
    for a, b in LEFT_IRIS:
        left_set.add(a)
        left_set.add(b)
    
    print(f"\nLEFT_IRIS 고유 인덱스: {sorted(left_set)} ({len(left_set)}개)")
    
    print("\n" + "=" * 80)
    print("MediaPipe FACEMESH_RIGHT_IRIS 연결:")
    print("=" * 80)
    for i, (a, b) in enumerate(RIGHT_IRIS):
        print(f"  연결 {i}: {a} <-> {b}")
    
    right_set = set()
    for a, b in RIGHT_IRIS:
        right_set.add(a)
        right_set.add(b)
    
    print(f"\nRIGHT_IRIS 고유 인덱스: {sorted(right_set)} ({len(right_set)}개)")
    
    print("\n" + "=" * 80)
    print("전체 눈동자 인덱스:")
    print("=" * 80)
    all_iris = sorted(left_set | right_set)
    print(f"  {all_iris} ({len(all_iris)}개)")
    
    print("\n" + "=" * 80)
    print("인덱스 범위 확인:")
    print("=" * 80)
    print(f"  최소값: {min(all_iris)}")
    print(f"  최대값: {max(all_iris)}")
    print(f"  468-477 범위에 있는가? {all(468 <= idx <= 477 for idx in all_iris)}")
    
except Exception as e:
    print(f"에러: {e}")
    import traceback
    traceback.print_exc()
