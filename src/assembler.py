# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
from src.pdf_reader import PDFReader
from src.matcher import match_pages

# TEMPLATE_PDF = Path('./src/import/template/')

def find_ext(dr, ext):
    return glob(path.join(dr,"*.{}".format(ext)))

def assemble_report(output, client_name):
    print("Start assembling!")

# get page replacement assignments
# for each page in template.json, get documents to replace it with\