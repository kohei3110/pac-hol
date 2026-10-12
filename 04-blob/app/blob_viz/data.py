import csv
from dataclasses import dataclass
import io
import re


MAX_FILE_BYTES = 65536
MAX_ROWS = 24
MAX_VALUE = 1000000
MAX_FILES = 10
MONTH = re.compile(r"20[0-9]{2}-(?:0[1-9]|1[0-2])")
VALUE = re.compile(r"(?:0|[1-9][0-9]{0,6})")
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,95}\.csv", re.IGNORECASE)
FILE_ID = re.compile(r"file-(?:0[1-9]|10)")


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class DataRow:
    month: str
    value: int


@dataclass(frozen=True)
class Dataset:
    rows: tuple[DataRow, ...]

    def as_dict(self) -> dict:
        return {
            "rows": [{"month": row.month, "value": row.value} for row in self.rows],
            "rowCount": len(self.rows),
            "total": sum(row.value for row in self.rows),
            "maximum": max(row.value for row in self.rows),
        }


def validate_filename(value: object) -> str:
    if not isinstance(value, str) or not FILENAME.fullmatch(value) or ".." in value:
        raise AppError("filename", "ファイル名は英数字等の短い名前で、拡張子.csvにしてください。")
    return value


def validate_file_id(value: str) -> str:
    if not FILE_ID.fullmatch(value):
        raise AppError("file_id", "このアプリのファイルIDではありません。", 404)
    return value


def parse_csv(content: bytes) -> Dataset:
    if not content or len(content) > MAX_FILE_BYTES:
        raise AppError("file_size", "CSVは空でなく、64 KiB以内にしてください。", 413 if content else 400)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError("encoding", "UTF-8のCSVを選んでください。Shift-JIS等には対応していません。") from None
    if "\x00" in text:
        raise AppError("csv", "CSVに使用できない文字が含まれています。")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    rows = []
    months = set()
    try:
        if reader.fieldnames != ["month", "value"]:
            raise AppError("columns", "先頭行はmonth,valueの2列にしてください。")
        for number, raw in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise AppError("rows", "データは1〜24行にしてください。")
            if set(raw) != {"month", "value"} or not all(isinstance(value, str) for value in raw.values()):
                raise AppError("columns", f"{number}行目の列数が正しくありません。")
            month, value = raw["month"].strip(), raw["value"].strip()
            if not MONTH.fullmatch(month):
                raise AppError("month", f"{number}行目の月は2000〜2099年のYYYY-MMで指定してください。")
            if month in months:
                raise AppError("duplicate_month", f"{number}行目の月が重複しています。")
            if not VALUE.fullmatch(value) or int(value) > MAX_VALUE:
                raise AppError("value", f"{number}行目の値は0〜1000000の整数にしてください。")
            months.add(month)
            rows.append(DataRow(month, int(value)))
    except csv.Error:
        raise AppError("csv", "CSVの引用符や区切りの形式が正しくありません。") from None
    if not rows:
        raise AppError("rows", "ヘッダーだけでなく、1〜24行のデータを入れてください。")
    return Dataset(tuple(sorted(rows, key=lambda row: row.month)))
