import base64
import io

import pytest
from PIL import Image, PngImagePlugin

from telecom_app.avatar import MAX_THUMBNAIL, MAX_UPLOAD, AvatarUpload, normalize_avatar
from tests.foundation.conftest import PASSWORD, login
from tests.foundation.test_profile import VALUES


def picture(format="PNG", size=(600, 300), color="red", **kwargs):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, format=format, **kwargs)
    return stream.getvalue()


def payload(raw, mime="image/png", revision=0):
    return {
        "mime": mime,
        "content_base64": base64.b64encode(raw).decode(),
        "expected_revision": revision,
    }


def test_normalization_removes_metadata_and_bounds_dimensions():
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "synthetic-private-metadata")
    output = normalize_avatar(AvatarUpload(**payload(picture(pnginfo=metadata))))
    assert len(output) <= MAX_THUMBNAIL and b"synthetic-private-metadata" not in output
    with Image.open(io.BytesIO(output)) as image:
        assert image.format == "JPEG" and image.size == (256, 128)
        assert not image.getexif() and "icc_profile" not in image.info
    exif = Image.Exif()
    exif[274] = 6
    rotated = normalize_avatar(AvatarUpload(**payload(picture("JPEG", exif=exif), "image/jpeg")))
    with Image.open(io.BytesIO(rotated)) as image:
        assert image.size == (128, 256) and not image.getexif()


@pytest.mark.parametrize(
    "raw,mime",
    [
        (b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/png"),
        (b"not an image", "image/png"),
        (picture(), "image/jpeg"),
        (picture("JPEG"), "image/png"),
        (picture()[:30], "image/png"),
        (picture(size=(4097, 1)), "image/png"),
        (picture(size=(2000, 2001)), "image/png"),
    ],
)
def test_untrusted_images_rejected(raw, mime):
    with pytest.raises(ValueError):
        normalize_avatar(AvatarUpload(**payload(raw, mime)))


def test_animation_and_invalid_base64_rejected():
    stream = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(
        stream, format="PNG", save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")]
    )
    with pytest.raises(ValueError):
        normalize_avatar(AvatarUpload(**payload(stream.getvalue())))
    with pytest.raises(ValueError):
        normalize_avatar(AvatarUpload(mime="image/png", content_base64="!!!", expected_revision=0))


def test_avatar_lifecycle_is_private_and_preserves_profile_fields(client, identity):
    upload = payload(picture())
    assert client.post("/api/profile/avatar", json=upload).status_code == 401
    assert client.get("/api/profile/avatar").status_code == 401
    login(client)
    assert client.get("/api/profile/avatar").status_code == 404
    response = client.post("/api/profile/avatar", json=upload)
    assert response.status_code == 200 and response.json()["has_avatar"] is True
    assert "content_base64" not in response.text
    fetched = client.get("/api/profile/avatar")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"] == "image/jpeg"
    assert fetched.headers["cache-control"] == "no-store"
    assert fetched.headers["x-content-type-options"] == "nosniff"
    original = fetched.content
    assert client.post("/api/profile/avatar", json=upload).status_code == 409
    assert client.post("/api/profile", json={**VALUES, "expected_revision": 1}).status_code == 200
    assert client.get("/api/profile/avatar").content == original
    assert (
        client.post(
            "/api/profile/avatar", json=payload(picture(color="blue"), revision=2)
        ).status_code
        == 200
    )
    assert client.get("/api/profile/avatar").content != original
    assert (
        client.post("/api/profile/avatar/remove", json={"expected_revision": 3}).status_code == 200
    )
    assert client.get("/api/profile/avatar").status_code == 404
    assert client.get("/api/profile").json()["display_name"] == VALUES["display_name"]
    assert "avatar" not in identity.store.get("admin@mongodb.com")["profile"]


def test_other_user_cannot_read_or_write_avatar_by_supplied_identity(client, identity):
    login(client)
    client.post("/api/profile/avatar", json=payload(picture()))
    owner = identity.store.get("admin@mongodb.com")
    client.post("/api/users", json={"email": "photo@example.test", "password": PASSWORD})
    client.post("/api/logout", json={})
    client.post("/api/login", json={"email": "photo@example.test", "password": PASSWORD})
    assert client.get("/api/profile/avatar").status_code == 404
    assert (
        client.post(
            "/api/profile/avatar", json={**payload(picture()), "user_id": owner["user_id"]}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/profile/avatar/remove", json={"expected_revision": 1, "email": owner["_id"]}
        ).status_code
        == 400
    )
    assert (
        identity.store.get("admin@mongodb.com")["profile"]["avatar"] == owner["profile"]["avatar"]
    )


def test_upload_limits_do_not_weaken_other_routes(client):
    login(client)
    assert (
        client.post("/api/profile/avatar", json=payload(b"x" * (MAX_UPLOAD + 1))).status_code == 400
    )
    assert (
        client.post(
            "/api/profile/avatar",
            content=b"x" * 2_797_001,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/profile", content=b"x" * 8193, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
