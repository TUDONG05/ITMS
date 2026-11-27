import re
import uuid
from datetime import datetime
from urllib.parse import unquote, urlsplit

from pydantic import ConfigDict, Field, field_validator

from app.models.document import DOCUMENT_FILE_FORMATS
from app.models.enums import InternshipPosition
from app.schemas.base import BaseSchema


def validate_document_url(value: str) -> str:
    value = value.strip()
    if not value or any(ord(char) < 32 for char in value) or "\\" in value:
        raise ValueError("URL tài liệu không hợp lệ.")
    decoded = value
    for _ in range(3):
        decoded = unquote(decoded)
    if "\\" in decoded or any(part in (".", "..") for part in urlsplit(decoded).path.split("/")):
        raise ValueError("Đường dẫn tài liệu không hợp lệ.")
    parsed = urlsplit(value)
    if (
        parsed.scheme in ("http", "https")
        and parsed.hostname
        and not parsed.username
        and not parsed.password
    ):
        return value
    if re.fullmatch(r"/api/v1/uploads/training/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)*", value):
        return value
    raise ValueError("Chỉ chấp nhận URL HTTP(S) hoặc tệp đào tạo đã tải lên.")


def document_format(url: str) -> str:
    path = unquote(urlsplit(url).path)
    match = re.search(r"\.([A-Za-z0-9]{1,15})$", path)
    return match.group(1).lower() if match else "link"


class DocumentCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    url: str = Field(max_length=4000)
    positions: list[InternshipPosition] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên tài liệu không được để trống.")
        return value.strip()

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        value = validate_document_url(value)
        if document_format(value) not in DOCUMENT_FILE_FORMATS:
            raise ValueError("Chỉ chấp nhận tệp tài liệu thuộc định dạng được hỗ trợ.")
        return value

    @field_validator("positions")
    @classmethod
    def unique_positions(cls, value: list[InternshipPosition]) -> list[InternshipPosition]:
        return list(dict.fromkeys(value))


class DocumentUpdate(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    positions: list[InternshipPosition] | None = None

    @field_validator("title", "positions")
    @classmethod
    def non_null(cls, value):
        if value is None:
            raise ValueError("Trường này không được để trống.")
        return value

    _clean_title = field_validator("title")(DocumentCreate.clean_title.__func__)
    _unique_positions = field_validator("positions")(DocumentCreate.unique_positions.__func__)


class DocumentSummary(BaseSchema):
    id: uuid.UUID
    title: str
    url: str
    format: str
    positions: list[InternshipPosition] = Field(default_factory=list)
    original_filename: str | None = None


class DocumentRead(DocumentSummary):
    description: str | None = None
    size_bytes: int | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0


class DocumentPage(BaseSchema):
    items: list[DocumentRead]
    total: int
    formats: list[str]
