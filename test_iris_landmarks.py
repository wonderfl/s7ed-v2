# 임시 테스트 스크립트
import mediapipe as mp

# MediaPipe Face Mesh 모델 로드
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 랜드마크 개수 확인
print(f"MediaPipe Face Mesh 랜드마크 총 개수: {len(mp_face_mesh.FACEMESH_CONTOURS)}")
print(f"Face Mesh 랜드마크 개수: 468 (표준) 또는 478 (iris 포함)")

# 눈동자 랜드마크 인덱스
iris_indices = {
    "left_iris": [468, 469, 470, 471, 472],
    "right_iris": [473, 474, 475, 476, 477]
}

print("눈동자 랜드마크 인덱스:")
print(f"왼쪽 눈동자: {iris_indices['left_iris']}")
print(f"오른쪽 눈동자: {iris_indices['right_iris']}")
