"""Split extracted blocks into chunks that fit in a prompt.

Rules:
- Never cut in the middle of a line (a line is often one table row or one sentence group).
- Never mix pages, so every chunk has one exact page citation.
- Each chunk starts with a short "document header" (file + page) so search can match
  questions like "on the Bluegum invoice" even when the body text doesn't repeat the name.
"""

from dataclasses import dataclass, asdict

from .extract import Block


@dataclass
class Chunk:
    id: str
    source: str
    page: int
    kind: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _title_from_filename(name: str) -> str:
    return name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")


def chunk_blocks(blocks: list[Block], max_chars: int = 900) -> list[Chunk]:
    chunks: list[Chunk] = []
    counters: dict[tuple, int] = {}

    def emit(block: Block, lines: list[str]) -> None:
        key = (block.source, block.page)
        n = counters.get(key, 0)
        counters[key] = n + 1
        header = f"[{_title_from_filename(block.source)} | page {block.page}]"
        chunks.append(
            Chunk(
                id=f"{block.source}#p{block.page}#c{n}",
                source=block.source,
                page=block.page,
                kind=block.kind,
                text=header + "\n" + "\n".join(lines),
            )
        )

    for block in blocks:
        current: list[str] = []
        size = 0
        for line in block.text.splitlines():
            line = line.strip()
            if not line:
                continue
            if current and size + len(line) > max_chars:
                emit(block, current)
                # One line of overlap keeps context across the boundary for prose.
                current = current[-1:] if block.kind == "text" else []
                size = sum(len(x) for x in current)
            current.append(line)
            size += len(line)
        if current:
            emit(block, current)
    return chunks
