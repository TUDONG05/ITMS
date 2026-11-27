import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from vercel.blob import BlobError, put_blob

from app.core.errors import ApiError
from app.core.settings import TRAINING_UPLOAD_DIR

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MIME_EXTENSIONS = {
    "application/pdf": ("pdf",),
    "application/msword": ("doc",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("docx",),
    "application/vnd.ms-excel": ("xls",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("xlsx",),
    "application/vnd.ms-powerpoint": ("ppt",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("pptx",),
    "text/plain": ("txt", "md"),
    "text/markdown": ("md",),
    "text/csv": ("csv",),
    "image/jpeg": ("jpg", "jpeg"),
    "image/png": ("png",),
    "image/gif": ("gif",),
    "image/webp": ("webp",),
    "video/mp4": ("mp4",),
    "video/webm": ("webm",),
    "audio/mpeg": ("mp3",),
    "audio/wav": ("wav",),
    "application/zip": ("zip",),
    "application/x-zip-compressed": ("zip",),
}


async def store_document(file: UploadFile) -> dict:
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    extensions = MIME_EXTENSIONS.get(content_type)
    original = (file.filename or "file").replace("\\", "/").rsplit("/", 1)[-1][:255]
    extension = Path(original).suffix.lstrip(".").lower()
    if not extensions or (extension and extension not in extensions):
        raise ApiError(
            415, "UNSUPPORTED_FILE_TYPE", "Loại tệp hoặc phần mở rộng không được hỗ trợ."
        )
    data = await file.read(MAX_DOCUMENT_BYTES + 1)
    if not data:
        raise ApiError(400, "EMPTY_FILE", "Tệp tải lên không có nội dung.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ApiError(413, "FILE_TOO_LARGE", "Tệp tải lên không được vượt quá 4 MB.")
    filename = f"{uuid.uuid4().hex}.{extension or extensions[0]}"
    use_blob = bool(
        os.getenv("VERCEL") or os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("BLOB_STORE_ID")
    )
    if use_blob:
        try:
            blob = await put_blob(
                f"training/{filename}",
                data,
                access="public",
                content_type=content_type,
                add_random_suffix=False,
            )
            url = blob.url
        except BlobError as exc:
            raise ApiError(
                502, "DOCUMENT_UPLOAD_FAILED", "Không thể lưu tệp tài liệu. Vui lòng thử lại."
            ) from exc
    else:
        TRAINING_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (TRAINING_UPLOAD_DIR / filename).write_bytes(data)
        url = f"/api/v1/uploads/training/{filename}"
    return {"url": url, "original_filename": original, "size_bytes": len(data)}
