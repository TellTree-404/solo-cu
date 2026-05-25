"""Screenshot capture and coordinate scaling."""

import base64
import io
from dataclasses import dataclass

from PIL import ImageGrab

from .config import TARGET_HEIGHT, TARGET_WIDTH
from .dpi import ensure_dpi_awareness

ensure_dpi_awareness()


@dataclass
class Screenshot:
    """A captured screen frame."""

    base64: str
    pil_image: "ImageGrab.Image"
    original_width: int
    original_height: int
    scaled_width: int
    scaled_height: int


def take_screenshot() -> Screenshot:
    """Capture the primary display and resize to the target resolution."""
    raw = ImageGrab.grab()
    ow, oh = raw.size

    # Scale down to target for vision API, pad with black to preserve aspect
    scale_w = TARGET_WIDTH / ow
    scale_h = TARGET_HEIGHT / oh
    scale = min(scale_w, scale_h)
    new_w = max(1, int(ow * scale))
    new_h = max(1, int(oh * scale))
    resized = raw.resize((new_w, new_h), ImageGrab.Image.Resampling.LANCZOS)

    # Pad to exact target size with black border
    canvas = ImageGrab.Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0))
    offset_x = (TARGET_WIDTH - new_w) // 2
    offset_y = (TARGET_HEIGHT - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    return Screenshot(
        base64=b64,
        pil_image=raw,
        original_width=ow,
        original_height=oh,
        scaled_width=TARGET_WIDTH,
        scaled_height=TARGET_HEIGHT,
    )


def scale_to_original(x: int, y: int, orig_w: int, orig_h: int) -> tuple[int, int]:
    """Map a coordinate from scaled-space (1024x768) back to original screen space."""
    scale = min(TARGET_WIDTH / orig_w, TARGET_HEIGHT / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    pad_x = (TARGET_WIDTH - new_w) // 2
    pad_y = (TARGET_HEIGHT - new_h) // 2

    ox = int((x - pad_x) / scale)
    oy = int((y - pad_y) / scale)
    ox = max(0, min(ox, orig_w - 1))
    oy = max(0, min(oy, orig_h - 1))
    return ox, oy


def crop_screenshot(ss: Screenshot, left: int, top: int, width: int, height: int) -> Screenshot:
    """Crop a full screenshot to a window region. No black-bar padding.

    The returned image is resized so its max dimension is TARGET_WIDTH.
    Coordinates from Mimo are scaled proportionally to the cropped window.
    To get absolute screen coords: abs_x = left + rel_x, abs_y = top + rel_y.
    """
    raw = ss.pil_image
    right = left + width
    bottom = top + height
    left = max(0, left)
    top = max(0, top)
    right = min(right, ss.original_width)
    bottom = min(bottom, ss.original_height)
    cropped = raw.crop((left, top, right, bottom))
    cw, ch = cropped.size

    # Fit into TARGET_WIDTH x TARGET_HEIGHT without padding
    scale = min(TARGET_WIDTH / cw, TARGET_HEIGHT / ch)
    new_w = max(1, int(cw * scale))
    new_h = max(1, int(ch * scale))
    resized = cropped.resize((new_w, new_h), ImageGrab.Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    return Screenshot(
        base64=b64,
        pil_image=cropped,
        original_width=cw,
        original_height=ch,
        scaled_width=new_w,
        scaled_height=new_h,
    )
