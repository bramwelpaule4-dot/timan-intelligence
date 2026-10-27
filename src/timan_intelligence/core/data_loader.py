"""Validated import helpers for supported tabular file formats."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".xls"}


def load_dataframe(source: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Load a CSV or Excel workbook into a DataFrame.

    `filename` should be supplied when `source` is a file-like upload object.
    This helper does not clean or modify the data after loading.
    """
    name = filename or getattr(source, "name", None)
    if not name:
        raise ValueError("A filename is required to identify the file format.")

    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. Supported formats: CSV and Excel."
        )

    if suffix == ".csv":
        try:
            return pd.read_csv(source)
        except UnicodeDecodeError:
            if hasattr(source, "seek"):
                source.seek(0)
            return pd.read_csv(source, encoding="latin-1")

    # For Excel workbooks, use the first worksheet by default. Worksheet selection
    # should be made explicit in the UI in a later iteration.
    return pd.read_excel(source)
