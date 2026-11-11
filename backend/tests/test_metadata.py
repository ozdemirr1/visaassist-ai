"""Location data is removed from photos before storing (ADR 0005).

The test images are built by hand: a few bytes of EXIF with an invented position, no real photo.
"""

import struct
import zlib

import pytest

from app.storage.metadata import remove_location

LATITUDE = struct.pack("<6I", 41, 1, 0, 1, 2952, 100)  # 41° 0' 29.52": three rationals
XMP = b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta><exif:GPSLatitude>41,0.49N</exif:GPSLatitude>"


def exif(order: str = "<") -> bytes:
    """TIFF block: IFD0 (orientation, GPS pointer) and a GPS block (ref "N", latitude)."""
    latitude = LATITUDE if order == "<" else struct.pack(">6I", 41, 1, 0, 1, 2952, 100)
    header = (b"II" if order == "<" else b"MM") + struct.pack(order + "HI", 42, 8)
    ifd0 = struct.pack(order + "H", 2)
    ifd0 += struct.pack(order + "HHIHH", 0x0112, 3, 1, 6, 0)  # Orientation = 6
    ifd0 += struct.pack(order + "HHII", 0x8825, 4, 1, 38)  # GPS block at offset 38
    ifd0 += struct.pack(order + "I", 0)
    gps = struct.pack(order + "H", 2)
    gps += struct.pack(order + "HHI", 1, 2, 2) + b"N\x00\x00\x00"  # GPSLatitudeRef
    gps += struct.pack(order + "HHII", 2, 5, 3, 68)  # GPSLatitude at offset 68
    gps += struct.pack(order + "I", 0)
    block = header + ifd0 + gps + latitude
    assert len(header + ifd0) == 38 and len(header + ifd0 + gps) == 68
    return block


def segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def jpeg(*segments: bytes) -> bytes:
    scan = b"\xff\xda\x00\x02" + b"scan data \xff\xe1 that is not a segment" + b"\xff\xd9"
    return b"\xff\xd8" + segment(0xE0, b"JFIF\x00") + b"".join(segments) + scan


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


@pytest.mark.parametrize("order", ["<", ">"])
def test_gps_values_are_overwritten_and_the_file_keeps_its_length(order: str) -> None:
    block = exif(order)
    photo = jpeg(segment(0xE1, b"Exif\x00\x00" + block))

    cleaned = remove_location(photo, "image/jpeg")

    assert len(cleaned) == len(photo)
    assert block[68:] not in cleaned  # the coordinates
    start = cleaned.index(b"Exif\x00\x00") + 6
    tiff = cleaned[start : start + len(block)]
    assert tiff[:38] == block[:38]  # IFD0 with the orientation is untouched
    # The GPS block now holds only GPSVersionID 2.3.0.0.
    assert struct.unpack_from(order + "HHHI", tiff, 38) == (1, 0, 1, 4)
    assert tiff[48:52] == b"\x02\x03\x00\x00"
    assert tiff[52:] == bytes(len(tiff) - 52)


def test_xmp_packet_is_blanked() -> None:
    photo = jpeg(segment(0xE1, XMP))
    cleaned = remove_location(photo, "image/jpeg")
    assert len(cleaned) == len(photo)
    assert b"GPSLatitude" not in cleaned
    assert b"http://ns.adobe.com/xap/1.0/\x00" in cleaned


def test_image_data_after_the_metadata_is_not_touched() -> None:
    photo = jpeg(segment(0xE1, b"Exif\x00\x00" + exif()))
    cleaned = remove_location(photo, "image/jpeg")
    tail = photo[photo.index(b"\xff\xda") :]
    assert cleaned.endswith(tail)


def test_png_exif_chunk_is_cleaned_and_its_checksum_updated() -> None:
    block = exif()
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", bytes(13))
        + chunk(b"eXIf", block)
        + chunk(b"IDAT", b"pixels")
        + chunk(b"IEND", b"")
    )
    cleaned = remove_location(png, "image/png")
    assert len(cleaned) == len(png) and block[68:] not in cleaned
    start = cleaned.index(b"eXIf") + 4
    data = cleaned[start : start + len(block)]
    (crc,) = struct.unpack_from(">I", cleaned, start + len(block))
    assert crc == zlib.crc32(b"eXIf" + data)


@pytest.mark.parametrize(
    ("data", "mime_type"),
    [
        (jpeg(), "image/jpeg"),  # no metadata
        (b"\xff\xd8\xff\xe1\xff\xff truncated", "image/jpeg"),  # segment longer than the file
        (jpeg(segment(0xE1, b"Exif\x00\x00" + exif()[:30])), "image/jpeg"),  # cut EXIF block
        (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\xff\xffeXIf", "image/png"),
        (b"%PDF-1.7\n%%EOF\n", "application/pdf"),
    ],
)
def test_files_without_location_or_with_a_broken_structure_are_returned_unchanged(
    data: bytes, mime_type: str
) -> None:
    assert remove_location(data, mime_type) is data
