"""중간에 비어있는 배열의 Delaunay 매핑 테스트"""
import numpy as np

print("=" * 80)
print("중간에 비어있는 배열의 Delaunay 매핑 테스트")
print("=" * 80)

# 시뮬레이션: 원본 478개, contour 8개 제거
original_indices = list(range(478))  # 0-477
remove_indices = [469, 470, 471, 472, 474, 475, 476, 477]  # contour 제거

# 제거 후 배열
filtered_list = [i for i in original_indices if i not in remove_indices]
print(f"\n[제거 후 배열]")
print(f"원본: {len(original_indices)}개 (0-477)")
print(f"제거: {len(remove_indices)}개 {remove_indices}")
print(f"남은: {len(filtered_list)}개")
print(f"첫 10개: {filtered_list[:10]}")
print(f"마지막 10개: {filtered_list[-10:]}")

# 인덱스 매핑 테이블 생성
index_mapping = {}
for new_idx, old_idx in enumerate(filtered_list):
    index_mapping[old_idx] = new_idx

print(f"\n[인덱스 매핑 예시]")
print(f"원본 인덱스 0 -> Delaunay 배열 인덱스 {index_mapping[0]}")
print(f"원본 인덱스 467 -> Delaunay 배열 인덱스 {index_mapping[467]}")
print(f"원본 인덱스 468 -> Delaunay 배열 인덱스 {index_mapping[468]}")
print(f"원본 인덱스 473 -> Delaunay 배열 인덱스 {index_mapping[473]}")

# 문제 시나리오
print(f"\n[문제 시나리오]")
print("원본 인덱스 468을 참조하는 삼각형이 있다면:")
print(f"  - Delaunay 배열에서 인덱스 {index_mapping[468]}를 사용")
print(f"  - 이건 맞음 (원본 인덱스 468 = Delaunay 배열 인덱스 {index_mapping[468]})")
print("\n하지만 원본 인덱스 469를 참조하는 삼각형이 있다면:")
if 469 in index_mapping:
    print(f"  - Delaunay 배열에서 인덱스 {index_mapping[469]}를 사용")
else:
    print(f"  - 원본 인덱스 469는 제거되었으므로 Delaunay 배열에 없음!")
    print(f"  - 이 경우 삼각형이 잘못된 인덱스를 참조하게 됨")

# Delaunay Triangulation 관점
print(f"\n[Delaunay Triangulation 관점]")
print("Delaunay는 포인트 배열의 인덱스를 그대로 사용:")
print("  - simplex[0], simplex[1], simplex[2]는 Delaunay 배열 인덱스")
print("  - 이 인덱스로 original_points_array와 transformed_points_array에 접근")
print("  - 원본 인덱스와 Delaunay 배열 인덱스가 다르면 문제 발생!")

print(f"\n[결론]")
print("중간에 비어있는 배열을 사용하면:")
print("  1. 원본 인덱스와 Delaunay 배열 인덱스가 다름")
print("  2. 삼각형 변환 시 매핑 테이블이 필요")
print("  3. 현재 코드는 매핑 테이블 없이 작동하므로 문제 발생 가능")
print("\n해결 방법:")
print("  A. 매핑 테이블 생성 및 사용")
print("  B. 모든 인덱스를 연속적으로 재구성 (현재 방식)")
print("  C. 중심점 인덱스(468, 473)도 제거하고 계산된 중앙 포인트만 사용")
