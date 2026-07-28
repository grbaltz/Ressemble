# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
from pdf_reader import PDFReader
import matcher

TEMPLATE_PDF = Path('./src/import/template/')
BASE_DATA_PATH = Path("./src/import/split_pages/")

def clear_directory(directory_path):
    for item in Path(directory_path).iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

def find_ext(dr, ext):
    return glob(path.join(dr,"*.{}".format(ext)))

template = Path(find_ext(TEMPLATE_PDF, "pdf")[0])
doc = PDFReader(template)
text = doc.get_text()
clear_directory(BASE_DATA_PATH)
doc.split_pages()

matcher.match_pages(BASE_DATA_PATH)