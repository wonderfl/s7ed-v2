"""눈동자 중심점 순서 확인"""
print("=" * 80)
print("눈동자 중심점 순서 확인")
print("=" * 80)

print("\n[문제]")
print("눈동자 중심점이 왼쪽으로 쏠려있다")

print("\n[확인 사항]")
print("1. _calculate_iris_centers 반환 순서:")
print("   return left_iris_center, right_iris_center")
print("   -> (왼쪽, 오른쪽)")

print("\n2. morph_face_by_polygons에서 추가 순서:")
print("   original_landmarks_no_iris.append(left_iris_center_orig)")
print("   original_landmarks_no_iris.append(right_iris_center_orig)")
print("   -> 왼쪽 먼저, 오른쪽 나중")
print("   -> 인덱스: 왼쪽=len-2, 오른쪽=len-1")

print("\n3. 렌더러에서 가져오는 순서:")
print("   왼쪽: len(landmarks) - 2")
print("   오른쪽: len(landmarks) - 1")
print("   -> 올바름")

print("\n[가능한 원인]")
print("1. MediaPipe LEFT_IRIS와 RIGHT_IRIS 정의가 실제로 반대일 수 있음")
print("   - MediaPipe의 LEFT/RIGHT는 사용자 관점이 아닌 이미지 관점")
print("   - 이미지에서 왼쪽 = MediaPipe RIGHT_IRIS")
print("   - 이미지에서 오른쪽 = MediaPipe LEFT_IRIS")

print("\n2. _calculate_iris_centers에서 반환 순서가 잘못되었을 수 있음")
print("   - 현재: (left_iris_center, right_iris_center)")
print("   - MediaPipe LEFT_IRIS는 이미지에서 오른쪽 눈")
print("   - MediaPipe RIGHT_IRIS는 이미지에서 왼쪽 눈")

print("\n3. 추가 순서가 잘못되었을 수 있음")
print("   - 현재: 왼쪽 먼저, 오른쪽 나중")
print("   - 하지만 MediaPipe LEFT_IRIS가 실제로는 오른쪽 눈이면 순서가 바뀜")

print("\n[해결 방법]")
print("방법 1: _calculate_iris_centers 반환 순서 확인")
print("   - MediaPipe LEFT_IRIS = 이미지 오른쪽 눈")
print("   - MediaPipe RIGHT_IRIS = 이미지 왼쪽 눈")
print("   - 반환 순서: (이미지 왼쪽, 이미지 오른쪽)")
print("   - 즉: (RIGHT_IRIS, LEFT_IRIS)")

print("\n방법 2: 추가 순서 확인")
print("   - 현재: left_iris_center 먼저, right_iris_center 나중")
print("   - 하지만 left_iris_center가 MediaPipe LEFT_IRIS라면 이미지 오른쪽")
print("   - 순서를 바꿔야 할 수 있음")

print("\n[확인 필요]")
print("1. MediaPipe LEFT_IRIS와 RIGHT_IRIS의 실제 의미")
print("2. _calculate_iris_centers에서 계산하는 순서")
print("3. 추가하는 순서와 렌더러에서 가져오는 순서의 일치")
