"""Tesseract OCR for scanned (image-only) PDF pages.

`ocr_page(image)` runs pytesseract on a PIL image and returns (text, mean_confidence).
Words with confidence < 0 (Tesseract's "no confidence" sentinel, -1) are dropped from both
the text and the confidence average, since they carry no signal.
"""
from __future__ import annotations

import pytesseract


def ocr_page(image) -> tuple[str, float | None]:
    """OCR a single page image. Returns (text, mean_word_confidence in [0,100] or None if no words)."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words: list[str] = []
    confs: list[float] = []
    for word, conf_str in zip(data["text"], data["conf"]):
        try:
            conf = float(conf_str)
        except (TypeError, ValueError):
            continue
        if conf < 0:
            continue
        word = word.strip()
        if not word:
            continue
        words.append(word)
        confs.append(conf)
    text = " ".join(words)
    mean_conf = (sum(confs) / len(confs)) if confs else None
    return text, mean_conf
