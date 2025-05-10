import io
import base64
from PIL import Image, ImageChops

__all__ = [
    "compress_image_to_size",
    "create_rotated_frame",
    "encode_image_to_base64",
]

def compress_image_to_size(img: Image.Image, target_size_mb: int) -> Image.Image | None:
    """Compress *img* (RGB) until it is smaller than *target_size_mb* (in megabytes).

    Returns a *new* PIL Image when successful, or ``None`` if the loop
    cannot reach the required size within the hard‑coded iteration limit.
    """
    target_size = target_size_mb * 1024 * 1024
    quality = 95
    width, height = img.size
    scale_factor = 0.95

    for _ in range(30):
        buffer = io.BytesIO()
        temp_img = img.resize((int(width), int(height)), Image.Resampling.LANCZOS)
        temp_img.convert("RGB").save(buffer, format="JPEG", quality=quality)
        size = buffer.tell()

        if size <= target_size:
            buffer.seek(0)
            return Image.open(buffer)

        quality -= 5
        width *= scale_factor
        height *= scale_factor
        if quality < 20:
            scale_factor -= 0.05

    return None


def create_rotated_frame(original: Image.Image, angle: float, crop: bool) -> Image.Image:
    """Return a single RGBA frame that is *original* rotated by *angle* degrees.

    If *crop* is true, the function removes the surrounding transparent/border
    area so that the output is as tight as possible.
    """
    canvas_size = original.size
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    rotated = original.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    if crop:
        bg = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
        diff = ImageChops.difference(rotated, bg)
        bbox = diff.getbbox()
        if bbox:
            rotated = rotated.crop(bbox)

    x = (canvas_size[0] - rotated.size[0]) // 2
    y = (canvas_size[1] - rotated.size[1]) // 2
    canvas.paste(rotated, (x, y), rotated)
    return canvas


def encode_image_to_base64(img: Image.Image, *, fmt: str = "PNG") -> str:
    """Encode *img* to a Base64 **string** (no data‑URL prefix)."""
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
