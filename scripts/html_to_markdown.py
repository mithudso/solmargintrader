#!/usr/bin/env python3
"""Recursively convert saved HTML to text-only Markdown, without network or dependencies.

Usage: python3 scripts/html_to_markdown.py SOURCE [--output OUTPUT] [--overwrite]
The default SOURCE is the current directory. OUTPUT defaults to a sibling directory
named SOURCE-markdown. Original HTML is never modified; existing outputs are skipped.
"""

from __future__ import annotations

import argparse
import codecs
import os
import re
import sys
import tempfile
import stat
import uuid
from html.parser import HTMLParser
from pathlib import Path

VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)
IGNORE = frozenset(
    [
        "head",
        "script",
        "style",
        "svg",
        "canvas",
        "template",
        "noscript",
        "iframe",
        "object",
    ]
)
BLOCK = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "caption",
        "dd",
        "details",
        "dialog",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "header",
        "main",
        "nav",
        "p",
        "section",
        "summary",
        "table",
        "tbody",
        "tfoot",
        "thead",
    ]
)
SPACE = re.compile(r"\s+")
ESCAPE = re.compile(r"([\\`*_\[\]#!|~])")
CHARSET = re.compile(rb"charset\s*=\s*[\"']?\s*([\w.-]+)", re.IGNORECASE)


class MarkdownParser(HTMLParser):
    """Keep readable text and structural Markdown; discard embedded payloads."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[tuple[str, bool]] = []
        self.lists: list[int | None] = []
        self.pre: list[str] | None = None
        self.cell_count = 0

    @property
    def hidden(self) -> bool:
        return bool(self.stack and self.stack[-1][1])

    def boundary(self, count: int = 2) -> None:
        self.parts.append("\n" * count)

    def block_boundary(self) -> None:
        # Layout wrappers inside a heading/list item must not split its Markdown marker.
        if any(tag == "li" or re.fullmatch(r"h[1-6]", tag) for tag, _ in self.stack):
            if self.parts and not self.parts[-1].endswith((" ", "\n")):
                self.parts.append(" ")
        else:
            self.boundary()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        hidden = self.hidden or tag in IGNORE or "hidden" in attr
        hidden = hidden or (attr.get("aria-hidden") or "").lower() == "true"
        hidden = hidden or bool(
            re.search(
                r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:!important\s*)?(?:;|$)",
                attr.get("style") or "",
                re.IGNORECASE,
            )
        )
        if tag not in VOID:
            self.stack.append((tag, hidden))
        if hidden:
            return
        if self.pre is not None:
            if tag == "br":
                self.pre.append("\n")
            return
        if tag == "pre":
            self.boundary()
            self.pre = []
        elif re.fullmatch(r"h[1-6]", tag):
            self.boundary()
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag in {"ul", "ol"}:
            self.boundary(1 if self.lists else 2)
            try:
                start = int(attr.get("start") or "1")
            except ValueError:
                start = 1
            self.lists.append(start if tag == "ol" else None)
        elif tag == "li":
            self.boundary(1)
            number = self.lists[-1] if self.lists else None
            self.parts.append("    " * max(0, len(self.lists) - 1))
            self.parts.append(f"{number}. " if number is not None else "- ")
            if self.lists and number is not None:
                self.lists[-1] = number + 1
        elif tag == "tr":
            self.boundary(1)
            self.cell_count = 0
        elif tag in {"td", "th"}:
            if self.cell_count:
                self.parts.append(" | ")
            self.cell_count += 1
        elif tag == "br":
            if any(re.fullmatch(r"h[1-6]", t) for t, _ in self.stack):
                self.parts.append(" ")
            else:
                self.boundary(1)
        elif tag in BLOCK or tag == "hr":
            self.block_boundary()

    def handle_endtag(self, tag: str) -> None:
        # A stray closing tag must not release a surrounding hidden element.
        match = next(
            (i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag),
            None,
        )
        if match is None:
            return
        hidden = self.hidden
        del self.stack[match:]
        if hidden:
            return
        if self.pre is not None:
            if tag == "pre":
                code = "".join(self.pre).strip("\n")
                runs = [len(m[0]) for m in re.finditer(r"`+", code)]
                fence = "`" * max(3, max(runs, default=0) + 1)
                self.parts.append(f"{fence}\n{code}\n{fence}")
                self.pre = None
                self.boundary()
            return
        if tag in {"ul", "ol"}:
            if self.lists:
                self.lists.pop()
            self.boundary(1 if self.lists else 2)
        elif re.fullmatch(r"h[1-6]", tag):
            self.boundary()
        elif tag in BLOCK:
            self.block_boundary()
        elif tag in {"li", "tr"}:
            self.boundary(1)

    def handle_data(self, data: str) -> None:
        if self.hidden:
            return
        if self.pre is not None:
            self.pre.append(data)
            return
        data = SPACE.sub(" ", data)
        if not self.parts or self.parts[-1].endswith((" ", "\n")):
            data = data.lstrip()
        if not data:
            return
        # Escaped entities stay text even when the source displayed literal HTML.
        data = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.parts.append(ESCAPE.sub(r"\\\1", data))

    def markdown(self) -> str:
        if self.pre is not None:
            self.handle_endtag("pre")
        text = "".join(self.parts)
        # Normalize outside fences only: blank lines and indentation inside code matter.
        result: list[str] = []
        fence: str | None = None
        for line in text.splitlines():
            if re.fullmatch(r"`{3,}", line):
                if fence is None:
                    fence = line
                elif line == fence:
                    fence = None
                result.append(line)
            elif fence is not None:
                result.append(line)
            else:
                line = line.rstrip()
                if line.strip() or (result and result[-1]):
                    result.append(line)
        return "\n".join(result).strip() + "\n"


def html_to_markdown(html: str) -> str:
    parser = MarkdownParser()
    parser.feed(html)
    parser.close()
    return parser.markdown()


def read_html(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return raw.decode("utf-16")
    if raw.startswith(codecs.BOM_UTF8):
        return raw.decode("utf-8-sig")
    match = CHARSET.search(raw[:4096])
    if match:
        return raw.decode(match[1].decode("ascii"))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("windows-1252")


def conversion_plan(source: Path, output: Path) -> list[tuple[Path, Path]]:
    source, output = source.resolve(), output.resolve()
    plan: list[tuple[Path, Path]] = []
    owners: dict[Path, Path] = {}

    def walk_error(error: OSError) -> None:
        raise error

    for directory, dirs, files in os.walk(
        source, followlinks=False, onerror=walk_error
    ):
        dirs[:] = sorted(
            d
            for d in dirs
            if not (Path(directory) / d).is_symlink()
            and (Path(directory) / d).resolve() != output
        )
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() not in {".html", ".htm"} or path.is_symlink():
                continue
            target = output / path.relative_to(source).with_suffix(".md")
            relative = target.relative_to(output)
            if any((output / Path(*relative.parts[:n])).is_symlink() for n in range(1, len(relative.parts) + 1)):
                raise ValueError(f"Refusing output symlink: {target}")
            if target in owners:
                raise ValueError(
                    f"Output collision: {owners[target]} and {path} -> {target}"
                )
            owners[target] = path
            plan.append((path, target))
    return plan


def write_markdown(target: Path, text: str, overwrite: bool, *, output_root: Path) -> None:
    """Publish through no-follow directory descriptors inside the declared root."""
    relative = target.relative_to(output_root)
    if any(part in {".", ".."} for part in relative.parts):
        raise ValueError("Output path escapes its root")
    output_root.mkdir(parents=True, exist_ok=True)
    parent = os.open(output_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".html-md-" + uuid.uuid4().hex
    created = False
    try:
        for part in relative.parts[:-1]:
            try:
                os.mkdir(part, dir_fd=parent)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        try:
            if stat.S_ISLNK(os.stat(relative.name, dir_fd=parent, follow_symlinks=False).st_mode):
                raise ValueError("Refusing output symlink")
        except FileNotFoundError:
            pass
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=parent)
        created = True
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, relative.name, src_dir_fd=parent, dst_dir_fd=parent)
        else:
            os.link(temporary, relative.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
    finally:
        if created:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
        os.close(parent)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", nargs="?", type=Path, default=Path.cwd())
    ap.add_argument(
        "--output",
        "-o",
        type=Path,
        help="mirror root (default: SOURCE-markdown sibling)",
    )
    ap.add_argument(
        "--overwrite", action="store_true", help="replace existing Markdown files"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="report planned counts without writing"
    )
    args = ap.parse_args(argv)
    source = args.source.resolve()
    output = (args.output or source.with_name(source.name + "-markdown")).resolve()
    if not source.is_dir():
        ap.error(f"Source is not a directory: {source}")
    if output == source or source.is_relative_to(output):
        ap.error("Output must not be the source directory or its ancestor")
    try:
        plan = conversion_plan(source, output)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    if not plan:
        print(f"No HTML files found below {source}", file=sys.stderr)
        return 1
    print(f"Found {len(plan)} HTML files. Output: {output}", flush=True)
    converted = skipped = failed = empty = 0
    try:
        for index, (path, target) in enumerate(plan, 1):
            if target.exists() and not args.overwrite:
                skipped += 1
            elif args.dry_run:
                converted += 1
            else:
                try:
                    text = html_to_markdown(read_html(path))
                    write_markdown(target, text, args.overwrite, output_root=output)
                    converted += 1
                    empty += not bool(text.strip())
                except (OSError, ValueError, LookupError) as exc:
                    failed += 1
                    print(f"ERROR {path}: {exc}", file=sys.stderr)
            if index % 1000 == 0:
                print(f"Processed {index}/{len(plan)}", flush=True)
    except KeyboardInterrupt:
        print("Interrupted. Rerun the same command to resume.", file=sys.stderr)
        return 130
    verb = "Would convert" if args.dry_run else "Converted"
    print(f"{verb} {converted}; skipped {skipped}; failed {failed}; empty {empty}.")
    if empty:
        print("Empty pages may require JavaScript; only saved HTML text is extracted.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
