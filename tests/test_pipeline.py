"""Unit tests that run without any model (no Ollama, no AWS needed).

    python -m pytest -q
"""

import pytest

from taxrag.answer import parse_response
from taxrag.bm25 import BM25, tokenize
from taxrag.chunk import chunk_blocks
from taxrag.evaluate import is_correct, normalise
from taxrag.extract import Block, table_to_lines


def test_table_rows_keep_their_headers():
    rows = [["Date", "Description", "Debit"], ["02/07/2026", "Rent", "$3,200.00"], ["03/07/2026", "Deposit", ""]]
    lines = table_to_lines(rows)
    assert lines[0] == "Date: 02/07/2026 | Description: Rent | Debit: $3,200.00"
    assert lines[1] == "Date: 03/07/2026 | Description: Deposit"  # empty cells dropped


def test_chunks_never_mix_pages_and_respect_size():
    blocks = [Block("a.pdf", 1, "text", "\n".join(["line one " * 10] * 20)), Block("a.pdf", 2, "text", "page two")]
    chunks = chunk_blocks(blocks, max_chars=300)
    assert {c.page for c in chunks} == {1, 2}
    assert all(len(c.text) < 300 + 200 for c in chunks)  # body + header + one overlap line
    assert len({c.id for c in chunks}) == len(chunks)


def test_tokenizer_keeps_invoice_numbers_and_amounts():
    assert "inv-1042" in tokenize("Payment for INV-1042")
    assert "3135.00" in tokenize("$3135.00") or "3135" in tokenize("$3135.00")


def test_bm25_ranks_exact_match_first():
    bm = BM25(["invoice INV-1042 total", "invoice INV-1057 total", "staff expense guide"])
    scores = bm.scores("INV-1057")
    assert scores.index(max(scores)) == 1


def test_parse_rejects_unknown_citations():
    raw = '{"found": true, "answer": "$5", "citations": ["made-up#p9#c0"]}'
    with pytest.raises(ValueError):
        parse_response(raw, {"real#p1#c0"})


def test_parse_not_found_clears_answer():
    found, answer, cites = parse_response('{"found": false, "answer": "maybe", "citations": ["x"]}', set())
    assert (found, answer, cites) == (False, None, [])


def test_parse_rejects_broken_json():
    with pytest.raises(Exception):
        parse_response("The answer is $5", {"a"})


def test_answer_matching_ignores_formatting():
    assert normalise("$3,135.00") == "3135"
    assert is_correct("The total is $3,135", ["3,135.00"])
    assert not is_correct("The total is $3,315", ["3,135.00"])
    assert is_correct("Paid on 16 July 2026", ["16/07/2026", "16 July"], mode="any")
