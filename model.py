from victordb import VictorBaseModel

from typing import ClassVar, List
from dataclasses import dataclass, field


@dataclass
class Document(VictorBaseModel):
    __classname__: ClassVar[str] = "Document"

    title:  str = ""
    author: str = ""
    source: str = ""
    raw_text: str = ""
    metadata: List[str] = field(default_factory=list)

@dataclass
class DocumentChunk(VictorBaseModel):
    __classname__: ClassVar[str] = "DocumentChunk"
    __indexed__: ClassVar[List[str]] = ["document_id"]

    document_id: int = 0
    content: str = ""
    position: int = 0

