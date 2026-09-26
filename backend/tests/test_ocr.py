"""Unit test for the OCR helper (app.ingest.ocr.ocr_page).

Renders a small image with known text via PIL and checks Tesseract recovers it. Skipped
entirely if tesseract is not installed on the machine running the tests.
"""
from __future__ import annotations

import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract is not installed",
)


def _make_text_image(text: str) -> Image.Image:
    img = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 40), text, fill="black", font=font)
    return img


def test_ocr_page_recovers_known_text():
    from app.ingest.ocr import ocr_page

    image = _make_text_image("KUPAKOSH WELL 15-9-F-5")
    text, mean_conf = ocr_page(image)

    assert "KUPAKOSH" in text.upper()
    assert "WELL" in text.upper()
    assert mean_conf is not None
    assert mean_conf > 0


def test_ocr_page_blank_image_has_no_words():
    from app.ingest.ocr import ocr_page

    image = Image.new("RGB", (200, 100), color="white")
    text, mean_conf = ocr_page(image)

    assert text.strip() == ""
    assert mean_conf is None
