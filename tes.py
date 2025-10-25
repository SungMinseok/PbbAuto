# 로그 설정을 가장 먼저 import
import logger_setup

import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
pytesseract.pytesseract.tesseract_cmd = fr'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 전역 변수: 마지막 OCR 시도 정보 저장
_last_ocr_attempts = []


def image_to_text_with_fallback(
    img_path,
    lang='kor',
    save_inverted=False,
    resize=True,
    sharpen=True,
    thresholding=True,
    preview=False,
    expected_text=None,
    exact_match=False
):
    """
    개선된 OCR 함수 - 자동 언어 감지 및 다중 줄 지원
    
    개선사항:
    1. 자동 언어 감지: lang='auto'일 경우 영어+한글 동시 시도
    2. 다중 줄 지원: 여러 PSM 모드 시도
    3. 신뢰도 기반 최적 결과 선택
    4. 조기 종료: expected_text가 발견되면 즉시 반환 (속도 향상)
    
    Args:
        expected_text: 찾을 텍스트 (있으면 발견 시 즉시 종료)
        exact_match: True면 완전일치, False면 일부포함
    """
    
    def preprocess_image(img, mode='standard'):
        """다양한 전처리 모드 지원"""
        # 그레이스케일
        img = img.convert("L")

        if mode == 'standard':
            # 리사이즈 (2배 확대)
            if resize:
                img = img.resize((img.width * 2, img.height * 2))
            # 샤프닝
            if sharpen:
                img = img.filter(ImageFilter.SHARPEN)
            # 이진화
            if thresholding:
                img = img.point(lambda x: 0 if x < 160 else 255, '1')
        
        elif mode == 'enhanced':
            # 고품질 리사이즈 (3배 확대)
            img = img.resize((img.width * 3, img.height * 3), Image.Resampling.LANCZOS)
            # 대비 향상
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            # 샤프닝
            img = img.filter(ImageFilter.SHARPEN)
            # 적응형 이진화
            img = img.point(lambda x: 0 if x < 140 else 255, '1')
        
        elif mode == 'light':
            # 밝은 텍스트용
            if resize:
                img = img.resize((img.width * 2, img.height * 2))
            # 밝기 조정
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.5)
            # 이진화 (낮은 임계값)
            img = img.point(lambda x: 0 if x < 180 else 255, '1')

        return img

    def try_ocr_with_confidence(image, lang_code, psm_mode):
        """OCR 실행하고 신뢰도와 함께 반환"""
        import time
        start_time = time.time()
        
        try:
            custom_config = f'--psm {psm_mode} --oem 3'
            
            # 텍스트 추출
            ocr_start = time.time()
            text = pytesseract.image_to_string(image, lang=lang_code, config=custom_config).strip()
            ocr_time = time.time() - ocr_start
            
            # 신뢰도 정보 추출 (있는 경우)
            conf_start = time.time()
            try:
                data = pytesseract.image_to_data(image, lang=lang_code, config=custom_config, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except:
                # 신뢰도 계산 실패 시 텍스트 길이로 대체
                avg_confidence = min(len(text) * 10, 100)  # 텍스트가 길수록 높은 점수
            conf_time = time.time() - conf_start
            
            total_time = time.time() - start_time
            
            # 상세 로그 출력
            result_preview = text[:30] + "..." if len(text) > 30 else text
            print(f"    [{lang_code}|PSM{psm_mode}] {total_time:.2f}s (OCR:{ocr_time:.2f}s, Conf:{conf_time:.2f}s) "
                  f"→ 신뢰도:{avg_confidence:.1f}% '{result_preview}'")
            
            return text, avg_confidence
        except Exception as e:
            total_time = time.time() - start_time
            print(f"    [{lang_code}|PSM{psm_mode}] {total_time:.2f}s → 실패: {e}")
            return "", 0

    # 전역 변수 초기화 (이전 실행 결과 제거)
    global _last_ocr_attempts
    _last_ocr_attempts = []
    
    try:
        import time
        total_start_time = time.time()
        
        print(f"🔍 OCR 처리 중: {img_path}")
        img = Image.open(img_path)
        
        if preview:
            img.show()
        
        # 시도할 설정들
        best_result = ""
        best_confidence = 0
        best_info = ""
        
        # 언어 설정 (속도 최적화: 가장 효과적인 조합만)
        if lang == 'auto':
            languages = ['eng+kor']  # 동시 인식만 (가장 효과적)
            print("  언어: 자동 감지 (영어+한글)")
        elif lang == 'kor':
            languages = ['kor+eng']  # 한글 우선 조합
            print("  언어: 한글 우선")
        else:
            languages = [lang]
            print(f"  언어: {lang}")
        
        # PSM 모드 (속도 최적화: 가장 범용적인 2개만)
        # 7: 단일 텍스트 줄
        # 6: 단일 균일 텍스트 블록 (여러 줄 지원, 가장 범용적)
        psm_modes = [7, 6]
        
        attempts = []
        
        # 1단계: 원본 이미지로 빠른 시도
        stage1_start = time.time()
        print("  [1단계] 원본 이미지 시도...")
        for lang_code in languages:
            for psm in psm_modes:
                text, conf = try_ocr_with_confidence(img, lang_code, psm)
                if text:
                    attempts.append((text, conf, f"원본|PSM{psm}"))
                    if conf > best_confidence:
                        best_result = text
                        best_confidence = conf
                        best_info = f"원본 (PSM={psm}, 신뢰도={conf:.1f})"
                    
                    # 기대 텍스트가 있고 발견되면 즉시 종료 (최고 속도 최적화!)
                    if expected_text and text:
                        is_match = False
                        if exact_match:
                            is_match = text.strip() == expected_text.strip()
                        else:
                            is_match = expected_text in text
                        
                        if is_match:
                            stage1_time = time.time() - stage1_start
                            total_time = time.time() - total_start_time
                            print(f"  ⏱️ 1단계 소요시간: {stage1_time:.2f}s")
                            print(f"✅ OCR 성공 (기대 텍스트 발견, 총 {total_time:.2f}s): '{text}'")
                            print(f"   원본 (PSM={psm}, 신뢰도={conf:.1f})")
                            return text
                    
                    # 신뢰도가 높으면 바로 종료 (속도 최적화)
                    if conf > 70:
                        stage1_time = time.time() - stage1_start
                        total_time = time.time() - total_start_time
                        print(f"  ⏱️ 1단계 소요시간: {stage1_time:.2f}s")
                        print(f"✅ OCR 성공 (고신뢰도, 총 {total_time:.2f}s): '{best_result}'")
                        print(f"   {best_info}")
                        return best_result
        
        stage1_time = time.time() - stage1_start
        print(f"  ⏱️ 1단계 완료: {stage1_time:.2f}s (최고 신뢰도: {best_confidence:.1f}%)")
        
        # 2단계: 신뢰도가 낮으면 전처리 1회만 시도
        if best_confidence < 50:
            stage2_start = time.time()
            print("  [2단계] 전처리 이미지 시도...")
            processed = preprocess_image(img, mode='standard')
            for lang_code in languages:
                for psm in psm_modes:
                    text, conf = try_ocr_with_confidence(processed, lang_code, psm)
                    if text:
                        attempts.append((text, conf, f"전처리|PSM{psm}"))
                        if conf > best_confidence:
                            best_result = text
                            best_confidence = conf
                            best_info = f"전처리 (PSM={psm}, 신뢰도={conf:.1f})"
                        
                        # 기대 텍스트가 있고 발견되면 즉시 종료
                        if expected_text and text:
                            is_match = False
                            if exact_match:
                                is_match = text.strip() == expected_text.strip()
                            else:
                                is_match = expected_text in text
                            
                            if is_match:
                                stage2_time = time.time() - stage2_start
                                total_time = time.time() - total_start_time
                                print(f"  ⏱️ 2단계 소요시간: {stage2_time:.2f}s")
                                print(f"✅ OCR 성공 (기대 텍스트 발견, 총 {total_time:.2f}s): '{text}'")
                                print(f"   전처리 (PSM={psm}, 신뢰도={conf:.1f})")
                                return text
                        
                        # 전처리 후 신뢰도 60 이상이면 충분
                        if conf > 60:
                            stage2_time = time.time() - stage2_start
                            total_time = time.time() - total_start_time
                            print(f"  ⏱️ 2단계 소요시간: {stage2_time:.2f}s")
                            print(f"✅ OCR 성공 (전처리, 총 {total_time:.2f}s): '{best_result}'")
                            print(f"   {best_info}")
                            return best_result
            
            stage2_time = time.time() - stage2_start
            print(f"  ⏱️ 2단계 완료: {stage2_time:.2f}s (최고 신뢰도: {best_confidence:.1f}%)")
        
        # 3단계: 여전히 안 되면 반전 시도 (최소한으로)
        if best_confidence < 30:
            stage3_start = time.time()
            print("  [3단계] 반전 이미지 시도...")
            inverted = ImageOps.invert(img.convert("RGB"))
            processed = preprocess_image(inverted, mode='standard')
            
            if preview:
                processed.show()
            
            if save_inverted:
                test_path = img_path.replace(".jpg", "_inverted_preprocessed.jpg")
                processed.save(test_path)
                print(f"    🖼 반전+전처리 이미지 저장: {test_path}")
            
            for lang_code in languages:
                text, conf = try_ocr_with_confidence(processed, lang_code, 6)  # PSM 6만 시도
                if text:
                    attempts.append((text, conf, "반전"))
                    if conf > best_confidence:
                        best_result = text
                        best_confidence = conf
                        best_info = f"반전 (신뢰도={conf:.1f})"
                    
                    # 기대 텍스트가 있고 발견되면 즉시 종료
                    if expected_text and text:
                        is_match = False
                        if exact_match:
                            is_match = text.strip() == expected_text.strip()
                        else:
                            is_match = expected_text in text
                        
                        if is_match:
                            stage3_time = time.time() - stage3_start
                            total_time = time.time() - total_start_time
                            print(f"  ⏱️ 3단계 소요시간: {stage3_time:.2f}s")
                            print(f"✅ OCR 성공 (기대 텍스트 발견, 총 {total_time:.2f}s): '{text}'")
                            print(f"   반전 (신뢰도={conf:.1f})")
                            return text
                    
                    break  # 결과가 나오면 즉시 종료
            
            stage3_time = time.time() - stage3_start
            print(f"  ⏱️ 3단계 완료: {stage3_time:.2f}s (최고 신뢰도: {best_confidence:.1f}%)")
        
        # 결과 출력
        total_time = time.time() - total_start_time
        if best_result:
            print(f"✅ OCR 성공 (총 {total_time:.2f}s): '{best_result}'")
            print(f"   {best_info}")
        else:
            print(f"⚠️ OCR 결과 없음 (총 {total_time:.2f}s) - 텍스트를 찾지 못했습니다")
        
        # 디버깅을 위해 시도 정보도 저장 (전역 변수는 함수 시작 부분에서 이미 선언됨)
        _last_ocr_attempts = attempts
        
        return best_result

    except Exception as e:
        print(f"❌ OCR 오류: {e}")
        import traceback
        traceback.print_exc()
        return None
    
#image_to_text_with_fallback("test.jpg", lang="kor")

#image_to_text_with_fallback("250411_105635.jpg", lang="kor")
if __name__ == "__main__":
    # 예시 이미지 경로
    #image_path = "250411_105635.jpg"
    # OCR 처리
    #image_to_text_with_fallback(image_path, lang="kor", preview=True)
    
    # Test with a specific image
    image_to_text_with_fallback(fr".\screenshot\250527_125958.jpg", lang="kor")