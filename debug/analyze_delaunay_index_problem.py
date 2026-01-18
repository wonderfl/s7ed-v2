"""Delaunay 인덱스 매핑 문제 분석"""
print("=" * 80)
print("Delaunay Triangulation 인덱스 매핑 문제 분석")
print("=" * 80)

# 시나리오: contour 8개만 제거, 중심점 468, 473 유지
original_landmarks = list(range(478))  # 0-477
remove_indices = [469, 470, 471, 472, 474, 475, 476, 477]  # contour만 제거

# 제거 후 배열 (현재 코드 방식)
filtered_list = [pt for i, pt in enumerate(original_landmarks) if i not in remove_indices]

print(f"\n[현재 방식: 인덱스 재구성]")
print(f"원본: {len(original_landmarks)}개 (인덱스 0-477)")
print(f"제거: {len(remove_indices)}개 {remove_indices}")
print(f"남은: {len(filtered_list)}개")
print(f"\nDelaunay 배열 구성:")
print(f"  인덱스 0-467: 원본 인덱스 0-467 (그대로)")
print(f"  인덱스 468: 원본 인덱스 468 (왼쪽 중심점)")
print(f"  인덱스 469: 원본 인덱스 473 (오른쪽 중심점)")
print(f"  인덱스 470: 추가된 왼쪽 중앙 포인트 (계산)")
print(f"  인덱스 471: 추가된 오른쪽 중앙 포인트 (계산)")

print(f"\n[문제점]")
print("1. 원본 인덱스와 Delaunay 배열 인덱스가 다름:")
print(f"   - 원본 인덱스 0 -> Delaunay 배열 인덱스 0 (같음)")
print(f"   - 원본 인덱스 468 -> Delaunay 배열 인덱스 468 (같음)")
print(f"   - 원본 인덱스 473 -> Delaunay 배열 인덱스 469 (다름!)")

print(f"\n2. 삼각형 변환 시:")
print("   - simplex[0], simplex[1], simplex[2]는 Delaunay 배열 인덱스")
print("   - 이 인덱스로 original_points_array와 transformed_points_array에 접근")
print("   - 하지만 원본 인덱스와 다르므로 매핑이 필요!")

print(f"\n3. 현재 코드 (540-549줄):")
print("   pt1_orig = original_points_array[simplex[0]]")
print("   pt1_trans = transformed_points_array[simplex[0]]")
print("   -> simplex[0]은 Delaunay 배열 인덱스이므로 문제 없음")
print("   -> 하지만 원본 인덱스와의 관계를 알 수 없음")

print(f"\n[결론]")
print("현재 방식은 작동하지만:")
print("  - Delaunay 배열은 연속적으로 재구성됨 (인덱스 0부터 시작)")
print("  - 원본 인덱스와 Delaunay 배열 인덱스가 다름")
print("  - 삼각형 변환은 Delaunay 배열 인덱스를 사용하므로 문제 없음")
print("  - 하지만 원본 인덱스를 참조해야 할 때는 매핑 테이블 필요")

print(f"\n[눈동자 이동을 위한 방법]")
print("방법 1: 중심점 인덱스(468, 473) 그대로 사용")
print("  - Delaunay 배열에서 인덱스 468, 469 사용")
print("  - 드래그 시 custom_landmarks[468], custom_landmarks[473] 업데이트")
print("  - Delaunay에 전달 시 custom_landmarks[468], custom_landmarks[473] 사용")
print("  - 매핑: 원본 468 -> Delaunay 468, 원본 473 -> Delaunay 469")
print("\n방법 2: 계산된 중앙 포인트 사용 (현재 방식)")
print("  - contour 8개 제거 + 중앙 포인트 2개 추가")
print("  - 드래그 좌표를 별도로 관리")
print("  - Delaunay에 전달 시 계산된 좌표 사용")
print("  - 매핑: 원본 인덱스와 Delaunay 배열 인덱스가 다름 (매핑 테이블 필요)")
