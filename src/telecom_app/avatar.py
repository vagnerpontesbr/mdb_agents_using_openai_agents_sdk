"""Bounded raster normalization; never retain the original upload or its metadata."""

import base64
import binascii
import io
import warnings
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field

from .contracts import Contract

MAX_UPLOAD = 2 * 1024 * 1024
MAX_ENCODED = 4 * ((MAX_UPLOAD + 2) // 3)
MAX_THUMBNAIL = 128 * 1024


class AvatarRevision(Contract):
    expected_revision: int = Field(ge=0, le=2_147_483_646, strict=True)


class AvatarUpload(AvatarRevision):
    mime: Literal["image/jpeg", "image/png"]
    content_base64: str = Field(min_length=1, max_length=MAX_ENCODED)


def normalize_avatar(upload: AvatarUpload) -> bytes:
    try:
        raw = base64.b64decode(upload.content_base64, validate=True)
        if not raw or len(raw) > MAX_UPLOAD:
            raise ValueError("Invalid image size")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=["JPEG", "PNG"]) as source:
                if (
                    {"JPEG": "image/jpeg", "PNG": "image/png"}.get(source.format or "")
                    != upload.mime
                    or getattr(source, "n_frames", 1) != 1
                    or max(source.size) > 4096
                    or source.width * source.height > 4_000_000
                ):
                    raise ValueError("Invalid image dimensions or format")
                source.verify()
            with Image.open(io.BytesIO(raw), formats=["JPEG", "PNG"]) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source)
                oriented.thumbnail((256, 256), Image.Resampling.LANCZOS)
                # Copy pixels into a fresh image so EXIF, comments and ICC data cannot survive.
                clean = Image.new("RGB", oriented.size, "white")
                rgba = oriented.convert("RGBA")
                clean.paste(rgba, mask=rgba.getchannel("A"))
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=85)
        normalized = output.getvalue()
        if len(normalized) > MAX_THUMBNAIL:
            raise ValueError("Thumbnail exceeds limit")
        return normalized
    except (
        OSError,
        ValueError,
        SyntaxError,
        binascii.Error,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValueError("Invalid profile photo") from None
