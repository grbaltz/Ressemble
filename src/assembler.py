# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
from src.pdf_reader import PDFReader
from src.scanner import match_pages

ADVISORS_PATH = Path("./src/import/advisors")

def assemble_report(log, request_advisors):
    select_advisor_files(log, request_advisors)

def select_advisor_files(log, request_advisors):
    log("Request Advisors")
    f = Path(ADVISORS_PATH / "advisors").name
    advisors = request_advisors(f)
    print(f"Selected advisors: {advisors}")
    