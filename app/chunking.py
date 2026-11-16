def chunk_transcript(transcript: str, max_chars: int = 6000, overlap_lines: int = 3) -> list[str]:
    lines = [line for line in transcript.splitlines() if line.strip()]

    chunks = []
    current = []
    size = 0

    for line in lines:
        line_size = len(line) + 1
        if len(current) > overlap_lines and size + line_size > max_chars:
            chunks.append("\n".join(current))
            current = current[len(current) - overlap_lines :]
            size = sum(len(line) + 1 for line in current)
        current.append(line)
        size += line_size

    if current:
        chunks.append("\n".join(current))

    return chunks
