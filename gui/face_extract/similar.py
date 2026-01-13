"""
얼굴 추출 패널 - 비슷한 얼굴 검색 Mixin
비슷한 얼굴을 찾아서 목록으로 표시하는 기능을 담당
"""
import os
import json
import hashlib
import tkinter as tk
from tkinter import messagebox
from PIL import Image

import utils.face_landmarks as face_landmarks
import utils.kaodata_image as kaodata_image


def _get_features_dir(image_path):
    """이미지 파일이 있는 디렉토리의 features 폴더 경로 반환"""
    image_dir = os.path.dirname(image_path)
    features_dir = os.path.join(image_dir, 'features')
    # features 폴더가 없으면 생성
    if not os.path.exists(features_dir):
        try:
            os.makedirs(features_dir, exist_ok=True)
        except Exception as e:
            print(f"[비슷한얼굴] features 폴더 생성 실패: {e}")
    return features_dir


def _get_features_cache_filename(image_path, suffix=''):
    """이미지 파일명을 기반으로 캐시 파일명 생성"""
    # 이미지 파일명 (확장자 포함)
    image_filename = os.path.basename(image_path)
    # 캐시 파일명: {이미지파일명}.s7ed.features{suffix}
    cache_filename = f"{image_filename}.s7ed.features{suffix}"
    return cache_filename


class SimilarFaceManagerMixin:
    """비슷한 얼굴 검색 기능 Mixin"""
    
    def _get_features_cache_path(self, image_path):
        """특징 벡터 캐시 파일 경로 반환 (features 폴더 내)"""
        features_dir = _get_features_dir(image_path)
        cache_filename = _get_features_cache_filename(image_path)
        return os.path.join(features_dir, cache_filename)
    
    def _load_features_cache(self, image_path):
        """특징 벡터 캐시 로드 (기존 함수, 호환성 유지)"""
        cache_path = self._get_features_cache_path(image_path)
        return self._load_features_cache_by_key(image_path, cache_path)
    
    def _save_features_cache(self, image_path, features):
        """특징 벡터 캐시 저장 (기존 함수, 호환성 유지)"""
        cache_path = self._get_features_cache_path(image_path)
        self._save_features_cache_by_key(image_path, cache_path, features)
    
    def _extract_face_features_for_image(self, image_path, include_clothing=False, clothing_only=False):
        """이미지에서 얼굴 특징 벡터 추출 (캐싱 포함)"""
        # 캐시 확인 (옷 포함 여부에 따라 다른 캐시 키 사용)
        features_dir = _get_features_dir(image_path)
        if clothing_only:
            cache_filename = _get_features_cache_filename(image_path, '_clothing_only')
        elif include_clothing:
            cache_filename = _get_features_cache_filename(image_path, '_clothing')
        else:
            cache_filename = _get_features_cache_filename(image_path)
        cache_key = os.path.join(features_dir, cache_filename)
        
        cached_features = self._load_features_cache_by_key(image_path, cache_key)
        if cached_features is not None:
            return cached_features
        
        try:
            # 이미지 로드
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 특징 벡터 추출
            if clothing_only:
                features = face_landmarks.extract_clothing_features_vector(image)
            elif include_clothing:
                features = face_landmarks.extract_combined_features_vector(image, include_clothing=True)
            else:
                features = face_landmarks.extract_face_features_vector(image)
            
            # 캐시 저장
            if features is not None:
                self._save_features_cache_by_key(image_path, cache_key, features)
            
            return features
            
        except Exception as e:
            print(f"[비슷한얼굴] 특징 추출 실패 ({image_path}): {e}")
            return None
    
    def _load_features_cache_by_key(self, image_path, cache_key):
        """특징 벡터 캐시 로드 (캐시 키 지정)"""
        if not os.path.exists(cache_key):
            return None
        
        try:
            # 이미지 파일의 수정 시간 확인
            image_mtime = os.path.getmtime(image_path)
            
            with open(cache_key, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 캐시의 이미지 수정 시간과 비교
            if cache_data.get('image_mtime') == image_mtime:
                import numpy as np
                # 튜플인 경우와 단일 벡터인 경우 처리
                features_data = cache_data['features']
                if isinstance(features_data, list) and len(features_data) == 2:
                    # 결합 특징 벡터 (얼굴, 옷)
                    face_features = np.array(features_data[0], dtype=np.float32)
                    clothing_features = np.array(features_data[1], dtype=np.float32) if features_data[1] else None
                    return (face_features, clothing_features)
                else:
                    # 단일 특징 벡터
                    features = np.array(features_data, dtype=np.float32)
                    return features
            
            # 수정 시간이 다르면 캐시 무효화
            return None
            
        except Exception as e:
            print(f"[비슷한얼굴] 캐시 로드 실패: {e}")
            return None
    
    def _save_features_cache_by_key(self, image_path, cache_key, features):
        """특징 벡터 캐시 저장 (캐시 키 지정)"""
        if features is None:
            return
        
        try:
            image_mtime = os.path.getmtime(image_path)
            
            # 튜플인 경우와 단일 벡터인 경우 처리
            if isinstance(features, tuple):
                # 결합 특징 벡터 (얼굴, 옷)
                features_data = [
                    features[0].tolist(),
                    features[1].tolist() if features[1] is not None else None
                ]
            else:
                # 단일 특징 벡터
                features_data = features.tolist()
            
            cache_data = {
                'image_mtime': image_mtime,
                'features': features_data
            }
            
            with open(cache_key, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            print(f"[비슷한얼굴] 캐시 저장 실패: {e}")
    
    def find_similar_faces(self, reference_image_path=None, top_n=10, include_clothing=False):
        """
        현재 이미지와 비슷한 얼굴들을 찾습니다.
        
        Args:
            reference_image_path: 기준 이미지 경로 (None이면 현재 이미지 사용)
            top_n: 반환할 상위 N개
            include_clothing: 옷 특징 포함 여부
        
        Returns:
            similar_faces: 유사도 점수와 함께 정렬된 리스트 [(similarity, file_path), ...]
        """
        if reference_image_path is None:
            reference_image_path = self.current_image_path
        
        if not reference_image_path or not os.path.exists(reference_image_path):
            return []
        
        # 기준 이미지의 특징 벡터 추출
        reference_features = self._extract_face_features_for_image(reference_image_path, include_clothing=include_clothing)
        if reference_features is None:
            return []
        
        # 이미지 디렉토리 경로 가져오기
        if self.face_extract_dir and os.path.exists(self.face_extract_dir):
            png_dir = self.face_extract_dir
        else:
            png_dir = kaodata_image.get_png_dir()
        
        if not os.path.exists(png_dir):
            return []
        
        # 모든 이미지 파일 찾기
        import glob
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.tiff', '*.tif', '*.webp']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(png_dir, ext)))
            image_files.extend(glob.glob(os.path.join(png_dir, ext.upper())))
        
        # 중복 제거
        image_files = list(set(os.path.normpath(f) for f in image_files))
        
        # 기준 이미지는 제외
        image_files = [f for f in image_files if f != reference_image_path]
        
        # 모든 이미지의 특징 벡터 추출
        face_features_list = []
        total = len(image_files)
        
        for idx, image_path in enumerate(image_files):
            try:
                features = self._extract_face_features_for_image(image_path, include_clothing=include_clothing, clothing_only=False)
                if features is not None:
                    face_features_list.append((features, image_path))
                
                # 진행률 업데이트 (UI가 있는 경우)
                if hasattr(self, 'similar_faces_status_label'):
                    progress = int((idx + 1) / total * 100)
                    self.similar_faces_status_label.config(
                        text=f"검색 중... {idx + 1}/{total} ({progress}%)"
                    )
                    self.update()  # UI 업데이트
                    
            except Exception as e:
                print(f"[비슷한얼굴] 이미지 처리 실패 ({image_path}): {e}")
                continue
        
        # 비슷한 얼굴 찾기
        if include_clothing:
            # 옷 포함 비교
            similarities = []
            for features, metadata in face_features_list:
                if features is not None:
                    similarity = face_landmarks.calculate_combined_similarity(
                        reference_features, 
                        features,
                        face_weight=0.7,
                        clothing_weight=0.3
                    )
                    similarities.append((similarity, metadata))
            
            # 유사도가 높은 순으로 정렬
            similarities.sort(key=lambda x: x[0], reverse=True)
            similar_faces = similarities[:top_n]
        else:
            # 얼굴만 비교
            similar_faces = face_landmarks.find_similar_faces(
                reference_features, 
                face_features_list, 
                top_n=top_n
            )
        
        return similar_faces
