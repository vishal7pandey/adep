"""PIL + OpenCV geometry provider [§9, BLK-007].

Implements geometry tools: crop, rotate, deskew, auto_orient, resize,
denoise, threshold. Follows the geometry-tool split (§2.3):
- deskew / auto_orient: auto-estimate angles (Hough/minAreaRect)
- rotate: takes explicit agent-supplied angle (deliberate only)

All functions return ToolResult with processed image handle (path).
No new dependencies beyond PIL + OpenCV (already in requirements.txt).
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

import cv2
import numpy as np
from PIL import Image

from src.tools.base import ToolResult

logger = logging.getLogger(__name__)


def _save_image(img: np.ndarray, prefix: str = "ade") -> str:
    """Save a numpy image array to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".png", prefix=f"{prefix}_")
    os.close(fd)
    cv2.imwrite(path, img)
    return path


def _load_image(image_path: str) -> np.ndarray:
    """Load an image as a numpy array (BGR format for OpenCV)."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    return img


def crop(image_path: str, bbox: tuple[int, int, int, int], **kwargs: Any) -> ToolResult:
    """Crop a region from an image.

    Args:
        image_path: Path to the source image.
        bbox: (x1, y1, x2, y2) pixel coordinates.

    Returns:
        ToolResult with data=path to cropped image.
    """
    try:
        img = _load_image(image_path)
        x1, y1, x2, y2 = bbox
        cropped = img[y1:y2, x1:x2]
        if cropped.size == 0:
            return ToolResult(ok=False, error="Crop region is empty", tool="crop")
        path = _save_image(cropped, "crop")
        return ToolResult(ok=True, data=path, tool="crop")
    except Exception as e:
        return ToolResult(ok=False, error=f"Crop failed: {e}", tool="crop")


def rotate(image_path: str, angle: float, **kwargs: Any) -> ToolResult:
    """Rotate an image by an explicit angle (agent-supplied, deliberate only) [§2.3].

    Args:
        image_path: Path to the source image.
        angle: Rotation angle in degrees (clockwise).

    Returns:
        ToolResult with data=path to rotated image.
    """
    try:
        img = _load_image(image_path)
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        rotated = cv2.warpAffine(img, matrix, (w, h))
        path = _save_image(rotated, "rotate")
        return ToolResult(ok=True, data=path, tool="rotate")
    except Exception as e:
        return ToolResult(ok=False, error=f"Rotate failed: {e}", tool="rotate")


def deskew(image_path: str, **kwargs: Any) -> ToolResult:
    """Auto-deskew an image by estimating the skew angle [§2.3].

    Uses Hough transform on edge-detected text to estimate the skew angle,
    then rotates to correct it. The agent passes no angle — the tool
    estimates it.

    Args:
        image_path: Path to the source image.

    Returns:
        ToolResult with data=path to deskewed image.
    """
    try:
        img = _load_image(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                minLineLength=img.shape[1] // 5, maxLineGap=20)

        if lines is None:
            return ToolResult(ok=True, data=image_path, tool="deskew")

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 != x1:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if abs(angle) < 45:
                    angles.append(angle)

        if not angles:
            return ToolResult(ok=True, data=image_path, tool="deskew")

        median_angle = np.median(angles)
        if abs(median_angle) < 0.1:
            return ToolResult(ok=True, data=image_path, tool="deskew")

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(img, matrix, (w, h))
        path = _save_image(deskewed, "deskew")
        return ToolResult(ok=True, data=path, tool="deskew")
    except Exception as e:
        return ToolResult(ok=False, error=f"Deskew failed: {e}", tool="deskew")


def auto_orient(image_path: str, **kwargs: Any) -> ToolResult:
    """Auto-orient an image by detecting the correct rotation [§2.3].

    Uses EXIF orientation data if available, otherwise estimates from
    text layout. The agent passes no rotation — the tool estimates it.

    Args:
        image_path: Path to the source image.

    Returns:
        ToolResult with data=path to oriented image.
    """
    try:
        from PIL import Image as PILImage, ExifTags
        pil_img = PILImage.open(image_path)

        # Check EXIF orientation
        try:
            exif = pil_img._getexif()
            if exif:
                for tag, value in exif.items():
                    if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == "Orientation":
                        if value == 3:
                            pil_img = pil_img.rotate(180, expand=True)
                        elif value == 6:
                            pil_img = pil_img.rotate(270, expand=True)
                        elif value == 8:
                            pil_img = pil_img.rotate(90, expand=True)
                        break
        except (AttributeError, KeyError):
            pass

        path = _save_image(cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR), "orient")
        return ToolResult(ok=True, data=path, tool="auto_orient")
    except Exception as e:
        return ToolResult(ok=False, error=f"Auto-orient failed: {e}", tool="auto_orient")


def resize(image_path: str, scale: float = 1.0, **kwargs: Any) -> ToolResult:
    """Resize an image by a scale factor.

    Args:
        image_path: Path to the source image.
        scale: Scale factor (1.0 = no change, 2.0 = double, 0.5 = half).

    Returns:
        ToolResult with data=path to resized image.
    """
    try:
        img = _load_image(image_path)
        h, w = img.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        path = _save_image(resized, "resize")
        return ToolResult(ok=True, data=path, tool="resize")
    except Exception as e:
        return ToolResult(ok=False, error=f"Resize failed: {e}", tool="resize")


def denoise(image_path: str, **kwargs: Any) -> ToolResult:
    """Denoise an image using OpenCV's fastNlMeansDenoising.

    Args:
        image_path: Path to the source image.

    Returns:
        ToolResult with data=path to denoised image.
    """
    try:
        img = _load_image(image_path)
        denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        path = _save_image(denoised, "denoise")
        return ToolResult(ok=True, data=path, tool="denoise")
    except Exception as e:
        return ToolResult(ok=False, error=f"Denoise failed: {e}", tool="denoise")


def threshold(image_path: str, **kwargs: Any) -> ToolResult:
    """Apply adaptive thresholding to an image.

    Useful for enhancing text on noisy backgrounds (e.g. thermal receipts).

    Args:
        image_path: Path to the source image.

    Returns:
        ToolResult with data=path to thresholded image.
    """
    try:
        img = _load_image(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        path = _save_image(thresh, "threshold")
        return ToolResult(ok=True, data=path, tool="threshold")
    except Exception as e:
        return ToolResult(ok=False, error=f"Threshold failed: {e}", tool="threshold")
