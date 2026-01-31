from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile

def _open_image(file) -> Image.Image:
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return img

def make_webp(file, max_size=(1600, 1600), quality=82) -> ContentFile:
    img = _open_image(file)
    img.thumbnail(max_size, Image.LANCZOS)

    out = BytesIO()
    # convert RGBA -> RGB for webp if needed
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    img.save(out, format="WEBP", quality=quality, method=6)
    return ContentFile(out.getvalue())

def make_thumb_webp(file, size=(520, 520), quality=78) -> ContentFile:
    img = _open_image(file)
    img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))

    out = BytesIO()
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    img.save(out, format="WEBP", quality=quality, method=6)
    return ContentFile(out.getvalue())
