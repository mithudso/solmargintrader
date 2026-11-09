"""Copy and index ordered CSV candles as verified, gap-free segments.

The index never imputes a missing bar. A query crossing a gap is refused. The
source file and its provenance remain separate from the private normalized copy.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from contextlib import closing


class SegmentError(ValueError):
    pass


HEADER = b"timestamp,open,high,low,close,volume\n"


def _row(line: bytes, step: int) -> tuple[int, float, float, float, float, float]:
    try:
        fields = line.decode("ascii").strip().split(",")
        if len(fields) != 6:
            raise ValueError("wrong column count")
        ts = int(fields[0]); op, hi, low, close, volume = map(float, fields[1:])
        if (ts < 0 or ts > 10_000_000_000 or ts % step or not all(math.isfinite(x) for x in (op, hi, low, close, volume))
                or min(op, hi, low, close) <= 0 or volume < 0 or hi < max(op, low, close) or low > min(op, hi, close)):
            raise ValueError("invalid OHLCV or timestamp")
        return ts, op, hi, low, close, volume
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise SegmentError(f"invalid source row: {exc}") from exc


def build(source: Path, directory: Path, *, asset: str, source_description: str,
          quote: str = "unknown", step: int = 60) -> dict:
    """Create a private immutable copy and index; never change the source."""
    if not asset or not source_description or not quote or isinstance(step, bool) or not isinstance(step, int) or step <= 0:
        raise SegmentError("asset, source, quote and positive interval are required")
    if source.is_symlink() or not source.is_file():
        raise SegmentError("source must be a regular non-symlink file")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    directory.chmod(0o700)
    data_tmp, index_tmp = directory / "candles.csv.partial", directory / "index.sqlite.partial"
    data_final, index_final = directory / "candles.csv", directory / "index.sqlite"
    source_stat = source.stat()
    fd = os.open(index_tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
    total_hash = hashlib.sha256(); count = gaps = missing = 0
    first = last = seg_start = seg_end = None
    seg_offset = seg_count = 0
    seg_hash = hashlib.sha256()
    with closing(sqlite3.connect(index_tmp)) as db, db:
        db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE segments (start INTEGER PRIMARY KEY, end INTEGER NOT NULL, byte_start INTEGER NOT NULL, byte_end INTEGER NOT NULL, count INTEGER NOT NULL, sha256 TEXT NOT NULL)")
        def finish_segment(offset: int) -> None:
            if seg_count:
                db.execute("INSERT INTO segments VALUES (?,?,?,?,?,?)", (seg_start, seg_end, seg_offset, offset, seg_count, seg_hash.hexdigest()))
        data_fd = os.open(data_tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with source.open("rb") as src, os.fdopen(data_fd, "wb") as dst:
            header = src.readline()
            if header != HEADER:
                raise SegmentError("source CSV header does not match canonical schema")
            dst.write(header); total_hash.update(header)
            for line_number, line in enumerate(src, 2):
                if not line.endswith(b"\n"):
                    raise SegmentError(f"truncated line {line_number}")
                row = _row(line, step); ts = row[0]
                if last is not None and ts <= last:
                    raise SegmentError(f"duplicate or out-of-order timestamp at line {line_number}")
                offset = dst.tell()
                if seg_count and (ts != last + step or seg_count == 1440):
                    finish_segment(offset)
                    seg_count = 0; seg_hash = hashlib.sha256()
                if last is not None and ts != last + step:
                    gaps += 1; missing += (ts - last) // step - 1
                if not seg_count:
                    seg_start, seg_offset = ts, offset
                dst.write(line); total_hash.update(line); seg_hash.update(line)
                seg_end = ts; seg_count += 1; count += 1
                first = ts if first is None else first; last = ts
            finish_segment(dst.tell())
            dst.flush(); os.fsync(dst.fileno())
        if not count:
            raise SegmentError("source has no observations")
        after = source.stat()
        if (source_stat.st_ino, source_stat.st_size, source_stat.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise SegmentError("source changed while being copied")
        metadata = {"schema": 1, "asset": asset, "quote": quote, "source_path": str(source),
                    "source_description": source_description, "interval_seconds": step,
                    "count": count, "first": first, "last": last, "gap_runs": gaps,
                    "missing_slots": missing, "sha256": total_hash.hexdigest()}
        db.executemany("INSERT INTO metadata VALUES (?,?)", ((k,json.dumps(v)) for k,v in metadata.items()))
    os.replace(data_tmp, data_final)
    os.replace(index_tmp, index_final)
    return metadata


def read_range(directory: Path, start: int, end: int) -> list[tuple]:
    """Read [start,end] only if every segment is verified and every bar exists."""
    index = directory / "index.sqlite"; data = directory / "candles.csv"
    if not index.is_file() or not data.is_file() or index.is_symlink() or data.is_symlink():
        raise SegmentError("complete segment index and data are required")
    with closing(sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        metadata = {k: json.loads(v) for k,v in db.execute("SELECT key,value FROM metadata")}
        step = metadata["interval_seconds"]
        if start < 0 or end < start or start % step or end % step:
            raise SegmentError("invalid query range")
        segments = db.execute("SELECT start,end,byte_start,byte_end,count,sha256 FROM segments WHERE start<=? AND end>=? ORDER BY start", (end,start)).fetchall()
        rows=[]; expected=start
        with data.open("rb") as f:
            for lo,hi,offset,stop,count,digest in segments:
                f.seek(offset); raw=f.read(stop-offset)
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise SegmentError("segment checksum mismatch")
                lines=raw.splitlines(keepends=True)
                if len(lines)!=count:
                    raise SegmentError("segment row count mismatch")
                for line in lines:
                    row=_row(line,step)
                    if start<=row[0]<=end:
                        if row[0]!=expected:
                            raise SegmentError("requested range has missing bars")
                        rows.append(row); expected+=step
        if expected!=end+step:
            raise SegmentError("requested range has missing bars or is outside coverage")
        return rows
