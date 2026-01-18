import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

# 눈썹 인덱스 가져오기
LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
eyebrow_indices = set([i for conn in LEFT_EYEBROW + RIGHT_EYEBROW for i in conn])
print(f"눈썹 인덱스: {sorted(eyebrow_indices)}")
print(f"눈썹 인덱스 개수: {len(eyebrow_indices)}개")

# TESSELATION 인덱스 가져오기 (468 미만만)
TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)
tesselation_indices = set([i for conn in TESSELATION for i in conn if i < 468])
print(f"\nTESSELATION 인덱스 (< 468): {len(tesselation_indices)}개")

# 눈썹 인덱스가 TESSELATION에 포함되는지 확인
eyebrow_in_tesselation = eyebrow_indices & tesselation_indices
print(f"\n눈썹 인덱스 중 TESSELATION에 포함된 것: {sorted(eyebrow_in_tesselation)}")
print(f"모든 눈썹 인덱스가 TESSELATION에 포함됨: {len(eyebrow_indices) == len(eyebrow_in_tesselation)}")

# TESSELATION 그래프 구성 (확장 확인용)
tesselation_graph = {}
for idx1, idx2 in TESSELATION:
    if idx1 < 468 and idx2 < 468:
        if idx1 not in tesselation_graph:
            tesselation_graph[idx1] = []
        if idx2 not in tesselation_graph:
            tesselation_graph[idx2] = []
        tesselation_graph[idx1].append(idx2)
        tesselation_graph[idx2].append(idx1)

print(f"\nTESSELATION 그래프: {len(tesselation_graph)}개 포인트")

# 눈썹 포인트들이 그래프에 있는지 확인
eyebrow_in_graph = [idx for idx in eyebrow_indices if idx in tesselation_graph]
print(f"눈썹 포인트 중 그래프에 포함된 것: {sorted(eyebrow_in_graph)}")
print(f"모든 눈썹 포인트가 그래프에 포함됨: {len(eyebrow_indices) == len(eyebrow_in_graph)}")

# 눈썹 포인트의 이웃 확인 (확장 가능 여부)
if eyebrow_in_graph:
    sample_idx = sorted(eyebrow_in_graph)[0]
    neighbors = tesselation_graph.get(sample_idx, [])
    print(f"\n샘플 눈썹 포인트 {sample_idx}의 이웃: {neighbors[:10]}... (총 {len(neighbors)}개)")
