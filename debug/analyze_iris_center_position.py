"""눈동자 중심점 위치 분석"""
print("=" * 80)
print("눈동자 중심점 위치 분석")
print("=" * 80)

print("\n[문제]")
print("눈동자 중심점이 왼쪽으로 쏠려있다")

print("\n[현재 코드 분석]")
print("1. _calculate_iris_centers:")
print("   left_iris_center = MediaPipe LEFT_IRIS (474, 475, 476, 477)의 평균")
print("   right_iris_center = MediaPipe RIGHT_IRIS (469, 470, 471, 472)의 평균")
print("   return (left_iris_center, right_iris_center)")

print("\n2. morph_face_by_polygons 추가 순서:")
print("   original_landmarks_no_iris.append(left_iris_center_orig)  # 인덱스 len-2")
print("   original_landmarks_no_iris.append(right_iris_center_orig)  # 인덱스 len-1")

print("\n3. 렌더러에서 가져오기:")
print("   왼쪽: landmarks[len(landmarks) - 2]  # left_iris_center")
print("   오른쪽: landmarks[len(landmarks) - 1]  # right_iris_center")

print("\n[MediaPipe LEFT/RIGHT 의미]")
print("MediaPipe의 LEFT/RIGHT는 사용자 관점이 아닌 이미지 관점:")
print("  - MediaPipe LEFT_IRIS = 이미지에서 보이는 오른쪽 눈 (사용자 관점 왼쪽)")
print("  - MediaPipe RIGHT_IRIS = 이미지에서 보이는 왼쪽 눈 (사용자 관점 오른쪽)")

print("\n[현재 매핑]")
print("  left_iris_center = MediaPipe LEFT_IRIS (이미지 오른쪽, 사용자 왼쪽)")
print("  right_iris_center = MediaPipe RIGHT_IRIS (이미지 왼쪽, 사용자 오른쪽)")
print("  추가 순서: left_iris_center 먼저 (len-2), right_iris_center 나중 (len-1)")
print("  렌더러: len-2를 왼쪽으로, len-1을 오른쪽으로 표시")
print("  -> 이론적으로는 올바름")

print("\n[문제 원인 추정]")
print("1. MediaPipe LEFT_IRIS와 RIGHT_IRIS의 실제 인덱스가 반대일 수 있음")
print("2. 추가 순서가 잘못되었을 수 있음")
print("3. 렌더러에서 가져오는 순서가 잘못되었을 수 있음")

print("\n[해결 방법]")
print("방법 1: 추가 순서를 바꾸기")
print("  - right_iris_center 먼저 추가 (len-2)")
print("  - left_iris_center 나중 추가 (len-1)")
print("  - 렌더러: len-2를 오른쪽으로, len-1을 왼쪽으로 표시")

print("\n방법 2: 렌더러에서 가져오는 순서를 바꾸기 (가장 간단)")
print("  - 왼쪽: len(landmarks) - 1")
print("  - 오른쪽: len(landmarks) - 2")

print("\n방법 3: _calculate_iris_centers 반환 순서를 바꾸기")
print("  - return (right_iris_center, left_iris_center)")
print("  - 추가 순서는 그대로")

print("\n[추천]")
print("방법 2가 가장 간단: 렌더러에서만 순서를 바꾸면 됨")
print("하지만 방법 1이 더 근본적인 해결책")
