import pypdf

def parse_pdf(file_path: str) -> str:
    """
    Parses a PDF file and extracts text page by page.
    """
    text = []
    try:
        reader = pypdf.PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # Keep track of pages in case we want to reference them
                text.append(page_text)
            else:
                text.append(f"[Page {i+1} is empty or scanned image]")
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF: {str(e)}")
    
    return "\n\n--- PAGE BREAK ---\n\n".join(text)
