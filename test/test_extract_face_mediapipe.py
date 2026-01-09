"""
extract_face_region 함수의 MediaPipe 옵션 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import kaodata_image
from PIL import Image

def test_mediapipe_extraction():
    """MediaPipe를 사용한 얼굴 추출 테스트"""
    print("=== MediaPipe 얼굴 추출 테스트 ===\n")
    
    # 테스트 이미지 경로들
    test_images = []
    
    # 1. test 폴더의 이미지들
    test_dir = 'test'
    if os.path.exists(test_dir):
        test_files = [
            'face_000_from_kaodata.png',
            'face_001_from_kaodata.png',
            'face_007_from_kaodata.png',
            'test_face.png'
        ]
        for f in test_files:
            path = os.path.join(test_dir, f)
            if os.path.exists(path):
                test_images.append(path)
    
    # 2. gui/png 폴더의 이미지들
    png_dir = 'gui/png'
    if os.path.exists(png_dir):
        import glob
        png_files = glob.glob(os.path.join(png_dir, '*.png'))
        if png_files:
            # 처음 3개만 테스트
            test_images.extend(png_files[:3])
    
    if not test_images:
        print("테스트할 이미지를 찾을 수 없습니다.")
        print("test 폴더나 gui/png 폴더에 이미지 파일이 있는지 확인하세요.")
        return
    
    print(f"테스트 이미지 {len(test_images)}개 발견\n")
    
    # MediaPipe 사용 가능 여부 확인
    try:
        from utils.face_landmarks import is_available
        mediapipe_available = is_available()
        print(f"MediaPipe 사용 가능: {mediapipe_available}\n")
    except ImportError:
        mediapipe_available = False
        print("MediaPipe 사용 불가 (ImportError)\n")
    
    # 결과 저장 디렉토리
    output_dir = 'test/extract_face_test_results'
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    for i, img_path in enumerate(test_images):
        print(f"[{i+1}/{len(test_images)}] 테스트: {os.path.basename(img_path)}")
        
        try:
            # 이미지 로드
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            print(f"  이미지 크기: {img.size}")
            
            # 1. OpenCV 방식 테스트
            try:
                print("  OpenCV 방식 테스트...")
                result_opencv = kaodata_image.extract_face_region(
                    img.copy(),
                    crop_scale=2.0,
                    use_mediapipe=False
                )
                opencv_path = os.path.join(output_dir, f"{os.path.basename(img_path)}_opencv.png")
                result_opencv.save(opencv_path)
                print(f"    성공: {result_opencv.size} -> {opencv_path}")
            except Exception as e:
                print(f"    실패: {e}")
                result_opencv = None
            
            # 2. MediaPipe 방식 테스트 (사용 가능한 경우)
            result_mediapipe = None
            if mediapipe_available:
                try:
                    print("  MediaPipe 방식 테스트...")
                    result_mediapipe = kaodata_image.extract_face_region(
                        img.copy(),
                        crop_scale=2.0,
                        use_mediapipe=True
                    )
                    mediapipe_path = os.path.join(output_dir, f"{os.path.basename(img_path)}_mediapipe.png")
                    result_mediapipe.save(mediapipe_path)
                    print(f"    성공: {result_mediapipe.size} -> {mediapipe_path}")
                except Exception as e:
                    print(f"    실패: {e}")
                    result_mediapipe = None
            else:
                print("  MediaPipe 방식 건너뜀 (사용 불가)")
            
            # 3. 결과 비교
            if result_opencv and result_mediapipe:
                if result_opencv.size == result_mediapipe.size:
                    print(f"    크기 일치: {result_opencv.size}")
                else:
                    print(f"    크기 차이: OpenCV={result_opencv.size}, MediaPipe={result_mediapipe.size}")
            
            success_count += 1
            print()
            
        except Exception as e:
            print(f"  오류 발생: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
            print()
    
    print(f"\n=== 테스트 완료 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"결과 저장 위치: {output_dir}")


def test_fallback_behavior():
    """MediaPipe가 없을 때 폴백 동작 테스트"""
    print("\n=== 폴백 동작 테스트 ===\n")
    
    # 테스트 이미지
    test_image = 'test/test_face.png'
    if not os.path.exists(test_image):
        test_image = 'test/face_000_from_kaodata.png'
    
    if not os.path.exists(test_image):
        print("테스트 이미지를 찾을 수 없습니다.")
        return
    
    try:
        img = Image.open(test_image)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"테스트 이미지: {test_image}")
        print(f"이미지 크기: {img.size}\n")
        
        # use_mediapipe=True로 설정했지만 MediaPipe가 없어도 폴백되어야 함
        print("use_mediapipe=True로 설정 (MediaPipe 없으면 OpenCV로 폴백)...")
        try:
            result = kaodata_image.extract_face_region(
                img.copy(),
                crop_scale=2.0,
                use_mediapipe=True
            )
            print(f"  성공: {result.size}")
            print("  폴백 동작 정상")
        except Exception as e:
            print(f"  실패: {e}")
            print("  폴백 동작 실패")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_mediapipe_extraction()
    test_fallback_behavior()
