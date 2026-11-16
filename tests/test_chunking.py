from app.chunking import chunk_transcript


def test_empty_transcript_gives_no_chunks():
    assert chunk_transcript("") == []


def test_short_transcript_is_one_chunk():
    text = "Ravi: hello\nPriya: hi"

    chunks = chunk_transcript(text, max_chars=1000)

    assert chunks == [text]


def test_overlap_of_one_line():
    LINES = "aaaa\nbbbb\ncccc\ndddd"

    chunks = chunk_transcript(LINES, max_chars=10, overlap_lines=1)

    assert chunks == ["aaaa\nbbbb", "bbbb\ncccc", "cccc\ndddd"]


def test_zero_overlap():
    LINES = "aaaa\nbbbb\ncccc\ndddd"

    chunks = chunk_transcript(LINES, max_chars=10, overlap_lines=0)

    assert chunks == ["aaaa\nbbbb", "cccc\ndddd"]


def test_nothing_to_overlap():
    text = "Ravi: hello world\n" * 500

    chunks = chunk_transcript(text, max_chars=200, overlap_lines=0)

    assert "\n".join(chunks).splitlines() == text.splitlines()


def test_no_chunk_is_too_big():
    text = "Ravi: hello world\n" * 500

    chunks = chunk_transcript(text, max_chars=200, overlap_lines=2)

    assert all(len(chunk) <= 200 for chunk in chunks)
