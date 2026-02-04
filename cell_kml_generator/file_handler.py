import csv
import os

import pandas as pd


def detect_delimiter(sample_text):
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample_text, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except csv.Error:
        for delim in [",", ";", "\t", "|"]:
            if delim in sample_text:
                return delim
    return ","


def load_file(path):
    _, ext = os.path.splitext(path.lower())
    if ext in [".csv", ".txt"]:
        with open(path, "r", encoding="latin-1") as handle:
            sample = "".join([handle.readline() for _ in range(5)])
        delimiter = detect_delimiter(sample)
        df = pd.read_csv(
            path,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
            encoding="latin-1",
        )
        return df, {"delimiter": delimiter, "format": ext.lstrip(".")}
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path, dtype=str)
        df = df.fillna("")
        return df, {"format": ext.lstrip(".")}
    raise ValueError("Unsupported file type: %s" % ext)
