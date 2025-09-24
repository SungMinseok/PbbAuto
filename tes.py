import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
pytesseract.pytesseract.tesseract_cmd = fr'C:\Program Files\Tesseract-OCR\tesseract.exe'


def image_to_text_with_fallback(
    img_path,
    lang='kor',
    save_inverted=False,
    resize=True,
    sharpen=True,
    thresholding=True,
    preview=False
):
    def preprocess_image(img):
        # 그레이스케일
        img = img.convert("L")

        # 리사이즈 (2배 확대)
        if resize:
            img = img.resize((img.width * 2, img.height * 2))

        # 샤프닝
        if sharpen:
            img = img.filter(ImageFilter.SHARPEN)

        # 이진화 (명암 임계값 적용)
        if thresholding:
            img = img.point(lambda x: 0 if x < 160 else 255, '1')

        return img

    def try_ocr(image):
        custom_config = r'--psm 7'  # 한 줄 텍스트에 최적화
        return pytesseract.image_to_string(image, lang=lang, config=custom_config).strip()

    try:
        print(f"[🔍] OCR 처리 중: {img_path}")
        img = Image.open(img_path)
        #img.show()
        # 1차 시도
        result = try_ocr(img)
        if result:
            print("[✅ 원본 OCR 결과]:", result)
            return result

        # 2차 시도: 반전 후 전처리
        processed_img = preprocess_image(img)
        processed_img.show()
        inverted = ImageOps.invert(img.convert("RGB"))
        inverted = preprocess_image(inverted)
        #inverted.show()

        if save_inverted:
            test_path = img_path.replace(".jpg", "_inverted_preprocessed.jpg")
            inverted.save(test_path)
            print(f"[🖼 반전+전처리 이미지 저장됨]: {test_path}")

        result = try_ocr(inverted)
        if result:
            print("[✅ 반전 OCR 결과 (반전 후 전처리)]:", result)
        else:
            print("[⚠️ 반전 후에도 텍스트를 찾지 못했습니다.]")

        return result

    except Exception as e:
        print(f"[❌ 오류 발생]: {e}")
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