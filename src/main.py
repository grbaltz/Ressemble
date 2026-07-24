# import pandas as pd
from pathlib import Path
import shutil
from pdf_reader import PDFReader
import matcher

TEST_FILE = Path('./src/import/text.txt')
TEST_PDF = Path('./src/import/Fullan Rebalance Portfolio Report through 071726.pdf')
BASE_DATA_PATH = Path("./src/import/split_pages/")

with open(TEST_FILE, "r") as f:
    content = f.read()
    print(content)
    shutil.copy(TEST_FILE, './src/export/textexport.txt')

doc = PDFReader(TEST_PDF)
text = doc.get_text()
doc.split_pages()

matcher.match_pages(BASE_DATA_PATH)