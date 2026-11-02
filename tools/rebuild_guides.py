#!/usr/bin/env python3
"""Refresh guide content in the checked-in HTML shells, optionally printing PDFs."""

import argparse
import base64
import html
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LESSONS = {
    "01": "01-vm",
    "02": "02-bastion",
    "03": "03-containerapps",
    "04": "04-blob",
    "05": "05-voice-agent",
}


def section_sources(folder):
    sources = {
        "participant": folder / "guide.md",
        "instructor": folder / "instructor-guide.md",
        "validation": folder / "run-through.md",
        "screenshots": folder / "screenshots.md",
        "self-study": ROOT / "self-study.md",
    }
    if folder.name == "04-blob":
        sources["setup"] = folder / "setup/README.md"
    if folder.name == "05-voice-agent":
        sources["verification"] = folder / "verification/README.md"
        sources["permissions"] = folder / "permissions.md"
    return sources


def data_url(path):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render(source, section, sources):
    result = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html5", "--wrap=none", str(source)],
        check=True, capture_output=True, text=True,
    )
    content = result.stdout
    prefix = "" if section == "participant" else f"{section}-"
    content = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m[1]}"', content)
    targets = {path.resolve(): name for name, path in sources.items()}

    def image(match):
        path = (source.parent / unquote(html.unescape(match[1]))).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"Image outside repository: {path}")
        return f'src="{data_url(path)}" loading="eager"'

    content = re.sub(r'src="([^"]+)"', image, content)

    def link(match):
        url = html.unescape(match[1])
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            return f'href="{html.escape(url, quote=True)}" rel="noopener noreferrer" target="_blank"'
        if not parts.path:
            return f'href="#{prefix}{html.escape(parts.fragment, quote=True)}"'
        path = (source.parent / unquote(parts.path)).resolve()
        if path in targets:
            target = targets[path]
            anchor = target
            if parts.fragment:
                target_prefix = "" if target == "participant" else f"{target}-"
                anchor = target_prefix + parts.fragment
            return f'href="#{html.escape(anchor, quote=True)}"'
        if path.is_relative_to(ROOT) and path.suffix in {".png", ".csv", ".txt", ".zip"}:
            return f'href="{data_url(path)}" download="{html.escape(path.name, quote=True)}"'
        if path.is_relative_to(ROOT):
            relative = Path(os.path.relpath(path, sources["participant"].parent))
            if path.name == "guide.md":
                relative = relative.with_suffix(".html")
            url = relative.as_posix()
            if parts.fragment:
                url += "#" + parts.fragment
        return f'href="{html.escape(url, quote=True)}"'

    return re.sub(r'href="([^"]+)"', link, content)


def rebuild(folder, pdf, chrome):
    target = folder / "guide.html"
    content = target.read_text()
    sources = section_sources(folder)
    anchors = {}

    def headings(fragment):
        return {
            re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", label))): identifier
            for identifier, label in re.findall(
                r'<h[1-6]\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h[1-6]>',
                fragment, flags=re.DOTALL,
            )
        }

    for section, source in sources.items():
        pattern = rf'(<section\b[^>]*\bid="{section}"[^>]*>).*?(</section>)'
        original = re.search(pattern, content, flags=re.DOTALL)
        if original is None:
            raise ValueError(f"Missing {section} section in {target}")
        rendered = render(source, section, sources)
        new_headings = headings(rendered)
        for label, identifier in headings(original[0]).items():
            if label in new_headings:
                anchors[identifier] = new_headings[label]
        content, count = re.subn(
            pattern, lambda m: m[1] + rendered + m[2], content, flags=re.DOTALL,
        )
        if count != 1:
            raise ValueError(f"Expected one {section} section in {target}, found {count}")
    content = re.sub(
        r'href="#([^"]+)"',
        lambda m: f'href="#{anchors.get(m[1], m[1])}"',
        content,
    )
    target.write_text(content)
    if pdf:
        with tempfile.TemporaryDirectory(prefix="hol-guide-print-") as profile:
            subprocess.run(
                [
                    chrome, "--headless", "--no-first-run", "--no-default-browser-check",
                    f"--user-data-dir={profile}", "--no-pdf-header-footer",
                    "--allow-file-access-from-files",
                    f"--print-to-pdf={folder / 'guide.pdf'}",
                    target.as_uri() + "?scoutTheme=light",
                ],
                check=True, capture_output=True, text=True,
            )
    print(f"Updated {folder.name}: HTML" + (" + PDF" if pdf else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lesson", choices=LESSONS)
    parser.add_argument("--pdf", action="store_true", help="Print using headless Chrome")
    parser.add_argument(
        "--chrome",
        default=shutil.which("google-chrome") or shutil.which("chromium")
        or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    args = parser.parse_args()
    if not shutil.which("pandoc"):
        parser.error("pandoc is required to render the Markdown guides")
    if args.pdf and not Path(args.chrome).is_file():
        parser.error("Chrome is required for --pdf; specify its executable with --chrome")
    for lesson in ([args.lesson] if args.lesson else LESSONS):
        rebuild(ROOT / LESSONS[lesson], args.pdf, args.chrome)


if __name__ == "__main__":
    main()
