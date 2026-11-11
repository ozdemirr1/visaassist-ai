"""Remove location data from photos before they are stored (ADR 0005, decision 4).

A phone photo carries the place where it was taken: in the GPS block of its EXIF data and often
again in an XMP packet. Neither is needed to check a document, so both are removed on upload.

The file is edited in place and keeps its length: the GPS block is overwritten, not cut out, so
no other offset in the file moves and the rest of the EXIF data (above all the orientation, which
viewers need to show the photo upright) stays valid. No image library is needed.

Covered: EXIF GPS and XMP in JPEG, EXIF GPS in PNG (`eXIf` chunk). Not covered: metadata inside
PDF files, XMP in PNG text chunks and maker-specific notes. A file whose structure cannot be
followed is stored unchanged.
"""

import struct
import zlib

_EXIF_HEADER = b"Exif\x00\x00"
_XMP_HEADERS = (b"http://ns.adobe.com/xap/1.0/\x00", b"http://ns.adobe.com/xmp/extension/\x00")
_GPS_POINTER_TAG = 0x8825
# Bytes per value for the TIFF field types 1-12.
_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
_MAX_IFDS = 8  # IFD0, the thumbnail IFD and a margin; also stops a looping chain
_ENTRY = 12


class _Malformed(Exception):
    pass


def remove_location(data: bytes, mime_type: str) -> bytes:
    """The same file without location data; unchanged if it has none or cannot be parsed."""
    buffer = bytearray(data)
    try:
        if mime_type == "image/jpeg":
            changed = _scrub_jpeg(buffer)
        elif mime_type == "image/png":
            changed = _scrub_png(buffer)
        else:
            return data
    except (_Malformed, struct.error, IndexError):
        return data
    return bytes(buffer) if changed else data


def _scrub_jpeg(buffer: bytearray) -> bool:
    changed = False
    position = 2  # after the start-of-image marker
    while position + 4 <= len(buffer):
        if buffer[position] != 0xFF:
            raise _Malformed
        marker = buffer[position + 1]
        if marker == 0xFF:  # fill byte before a marker
            position += 1
            continue
        if marker in (0xDA, 0xD9):  # image data or end of image: no metadata after this
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # markers without a length
            position += 2
            continue
        (length,) = struct.unpack_from(">H", buffer, position + 2)
        start, end = position + 4, position + 2 + length
        if length < 2 or end > len(buffer):
            raise _Malformed
        if marker == 0xE1:
            payload = bytes(buffer[start:end])
            if payload.startswith(_EXIF_HEADER):
                changed |= _scrub_tiff(buffer, start + len(_EXIF_HEADER), end)
            else:
                for header in _XMP_HEADERS:
                    if payload.startswith(header):
                        blank = start + len(header)
                        buffer[blank:end] = b" " * (end - blank)
                        changed = True
        position = end
    return changed


def _scrub_png(buffer: bytearray) -> bool:
    changed = False
    position = 8  # after the signature
    while position + 12 <= len(buffer):
        (length,) = struct.unpack_from(">I", buffer, position)
        kind = bytes(buffer[position + 4 : position + 8])
        start, end = position + 8, position + 8 + length
        if end + 4 > len(buffer):
            raise _Malformed
        if kind == b"eXIf" and _scrub_tiff(buffer, start, end):
            struct.pack_into(">I", buffer, end, zlib.crc32(kind + bytes(buffer[start:end])))
            changed = True
        if kind == b"IEND":
            break
        position = end + 4
    return changed


def _scrub_tiff(buffer: bytearray, base: int, end: int) -> bool:
    """Empty every GPS block of the EXIF data in buffer[base:end]. Offsets count from `base`."""
    size = end - base
    if size < 8:
        raise _Malformed
    order = {b"II": "<", b"MM": ">"}.get(bytes(buffer[base : base + 2]))
    if order is None or struct.unpack_from(order + "H", buffer, base + 2)[0] != 42:
        raise _Malformed

    def check(offset: int, length: int) -> None:
        if offset < 0 or length < 0 or offset + length > size:
            raise _Malformed

    def u16(offset: int) -> int:
        check(offset, 2)
        return struct.unpack_from(order + "H", buffer, base + offset)[0]

    def u32(offset: int) -> int:
        check(offset, 4)
        return struct.unpack_from(order + "I", buffer, base + offset)[0]

    def zero(offset: int, length: int) -> None:
        check(offset, length)
        buffer[base + offset : base + offset + length] = bytes(length)

    changed = False
    ifd = u32(4)
    for _ in range(_MAX_IFDS):
        if ifd == 0:
            break
        count = u16(ifd)
        for index in range(count):
            entry = ifd + 2 + index * _ENTRY
            if u16(entry) == _GPS_POINTER_TAG:
                changed |= _empty_gps_block(u32(entry + 8), u16, u32, zero, buffer, base, order)
        ifd = u32(ifd + 2 + count * _ENTRY)
    return changed


def _empty_gps_block(gps, u16, u32, zero, buffer: bytearray, base: int, order: str) -> bool:
    """Overwrite the values of the GPS block and leave only its version entry."""
    count = u16(gps)
    if count == 0:
        return False
    for index in range(count):
        entry = gps + 2 + index * _ENTRY
        length = _TYPE_SIZE.get(u16(entry + 2), 1) * u32(entry + 4)
        if length > 4:  # the value is stored elsewhere; the entry holds its offset
            zero(u32(entry + 8), length)
    zero(gps + 2, count * _ENTRY + 4)  # the entries and the pointer to a next block
    # A block must have at least one entry: GPSVersionID 2.3.0.0, which says nothing about a place.
    struct.pack_into(order + "H", buffer, base + gps, 1)
    struct.pack_into(order + "HHI", buffer, base + gps + 2, 0, 1, 4)
    buffer[base + gps + 10 : base + gps + 14] = b"\x02\x03\x00\x00"
    return True
