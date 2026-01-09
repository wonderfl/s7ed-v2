"""
설정 파일 저장/로드 유틸리티
"""
import os
import json

# 설정 파일 경로
CONFIG_FILE = 'config.json'

def load_config():
    """설정 파일을 불러옵니다."""
    import globals as gl
    
    if not os.path.exists(CONFIG_FILE):
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 설정값 적용
        if 'loading_file' in config:
            gl._loading_file = config['loading_file']
        if 'face_file' in config:
            gl._face_file = config['face_file']
        if 'png_dir' in config:
            gl._png_dir = config['png_dir']
        if 'save_file_dir' in config:
            gl._save_file_dir = config['save_file_dir']
        if 'face_extract_dir' in config:
            gl._face_extract_dir = config['face_extract_dir']
            
    except Exception as e:
        print(f"[설정] 설정 파일 로드 실패: {e}")

def save_config():
    """설정 파일에 저장합니다."""
    import globals as gl
    
    try:
        config = {
            'loading_file': gl._loading_file,
            'face_file': gl._face_file,
            'png_dir': gl._png_dir,
            'save_file_dir': gl._save_file_dir,
            'face_extract_dir': gl._face_extract_dir
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"[설정] 설정 파일 저장 실패: {e}")

def load_face_extract_params(image_path):
    """이미지별 팔레트 추출 파라미터를 불러옵니다.
    
    Args:
        image_path: 원본 이미지 파일 경로
        
    Returns:
        dict: 파라미터 딕셔너리, 파일이 없거나 오류 시 None
    """
    if not image_path:
        return None
    
    # 설정 파일 경로 생성: 원본파일명.s7ed.json
    config_path = f"{image_path}.s7ed.json"
    
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
        return params
    except Exception as e:
        print(f"[설정] 이미지별 설정 파일 로드 실패 ({config_path}): {e}")
        return None

def save_face_extract_params(image_path, params):
    """이미지별 팔레트 추출 파라미터를 저장합니다.
    
    Args:
        image_path: 원본 이미지 파일 경로
        params: 파라미터 딕셔너리
    """
    if not image_path:
        return
    
    # 설정 파일 경로 생성: 원본파일명.s7ed.json
    config_path = f"{image_path}.s7ed.json"
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[설정] 이미지별 설정 파일 저장 실패 ({config_path}): {e}")

