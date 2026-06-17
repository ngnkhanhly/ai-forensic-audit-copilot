import os
import pypdf
import google.generativeai as genai
from backend.app.config import settings

# Attempt to import PaddleOCR
try:
    from paddleocr import PaddleOCR
    # Initialize PaddleOCR (det=True, rec=True, lang='en' by default, or support multi-language/Vietnamese)
    # Use use_angle_cls=True to handle rotated images
    try:
        ocr_client = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    except Exception:
        ocr_client = PaddleOCR(use_angle_cls=True, lang='en')
except Exception as e:
    print(f"PaddleOCR failed to import or initialize: {e}. Will fall back to PDF extraction or Gemini OCR.")
    ocr_client = None

def perform_ocr(file_path: str) -> str:
    """
    Performs OCR on the given file path.
    If it is a PDF with embedded text, tries to extract it first.
    If it is scanned or an image, runs PaddleOCR.
    If PaddleOCR is unavailable or fails, falls back to Gemini Multimodal vision to read the file.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Try extracting text directly if it is a digital PDF
    if ext == ".pdf":
        try:
            reader = pypdf.PdfReader(file_path)
            extracted_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 50: # Check if it actually has text, not scanned
                    extracted_text.append(page_text)
            if len(extracted_text) == len(reader.pages):
                # Looks like a digital PDF with readable text
                return "\n\n--- PAGE BREAK ---\n\n".join(extracted_text)
        except Exception as e:
            print(f"Direct PDF text extraction failed: {e}")

    # 2. Try PaddleOCR if initialized
    if ocr_client:
        try:
            # PaddleOCR takes file path directly
            # Returns list of results (one per page or box list depending on file type)
            results = ocr_client.ocr(file_path, cls=True)
            lines = []
            for page in results:
                if page:
                    for line in page:
                        # line format: [[bbox], (text, confidence)]
                        text = line[1][0]
                        lines.append(text)
            if lines:
                return "\n".join(lines)
        except Exception as e:
            print(f"PaddleOCR execution failed: {e}")

    # 3. Fallback: Use OpenAI vision capabilities (GPT-4o-mini is multimodal)
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "placeholder_key":
        try:
            import base64
            from openai import OpenAI
            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Read file bytes
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
            mime_type = "application/pdf" if ext == ".pdf" else "image/jpeg"
            if ext in [".png", ".webp"]:
                mime_type = f"image/{ext[1:]}"
            
            # For PDFs, since they cannot be sent directly as base64 images in simple API calls easily, 
            # we check if it's an image. If it's a PDF, we print a warning, but try anyway, or 
            # let's write a base64 image tag for images.
            if ext != ".pdf":
                base64_image = base64.b64encode(file_bytes).decode("utf-8")
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all visible text from this document. Keep the visual reading order. Do not translate or comment."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4096
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI fallback OCR failed: {e}")
            
    # Absolute minimum fallback
    return f"[Scanned document: {os.path.basename(file_path)}]"
