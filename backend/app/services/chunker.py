from typing import List

def chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 300) -> List[str]:
    """
    Splits text into chunks of roughly chunk_size characters with chunk_overlap characters of overlap.
    Aims to split on paragraph/line boundaries to keep context clean.
    """
    if not text:
        return []
        
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If paragraph itself is too large, split it by sentences or characters
        if len(paragraph) > chunk_size:
            # Commit current chunk if any
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split large paragraph into smaller pieces
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                chunks.append(paragraph[start:end])
                start += chunk_size - chunk_overlap
            continue
            
        if current_length + len(paragraph) + 1 > chunk_size:
            chunks.append("\n".join(current_chunk))
            
            # Retain overlap from current chunk
            overlap_text = []
            overlap_len = 0
            for item in reversed(current_chunk):
                if overlap_len + len(item) + 1 <= chunk_overlap:
                    overlap_text.insert(0, item)
                    overlap_len += len(item) + 1
                else:
                    break
            
            current_chunk = overlap_text + [paragraph]
            current_length = sum(len(x) + 1 for x in current_chunk)
        else:
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 1
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks
