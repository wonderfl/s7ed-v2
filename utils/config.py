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
            
        print(f"[설정] 설정 파일을 불러왔습니다: {CONFIG_FILE}")
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
            'save_file_dir': gl._save_file_dir
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
        print(f"[설정] 설정 파일에 저장했습니다: {CONFIG_FILE}")
    except Exception as e:
        print(f"[설정] 설정 파일 저장 실패: {e}")

