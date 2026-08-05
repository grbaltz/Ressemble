# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
import json
import re
import pymupdf
from datetime import date

PAGES_CONFIG_PATH = Path("./src/pages.json")
TEMPLATE_CONFIG_PATH = Path("./src/template.json")
BASE_DATA_PATH = Path("./src/import/split_pages")
ADVISORS_PATH = Path("./src/import/advisors")
EXPORT_PATH = Path("./src/export")

def assemble_report(log, progress, advisors_filename):
    # select_advisor_file(log, request_advisors)
    print("assemble")

    bd_slot = 1
    
    # assemble array of files in order, then combine them
    report_pages = []
    
    ###
    # loop across all files in template.pages
    # check if page is placeholder
    #   if yes -> check if emx/bd -> insert emx/bd1/bd2
    #   if no -> insert page
    ###
    
    with open(TEMPLATE_CONFIG_PATH, "r") as t:
        template = json.load(t)
        
    for i, page in enumerate(template["pages"]):
        print(f"page: {page}")
        
        # check if placeholder
        if not page.get("placeholder") and not page.get("slot"):
            report_pages.append(page["filename"])
            continue
        
        match page["slot"]:
            case "advisors":
                print("Advisors slot")

                path = template.get("advisors_filename")

                if not path:
                    print("no advisors source provided")
                    report_pages.append(page["filename"])
                    continue

                # page = Path(path)
                print(f"adv path: {path}")
                report_pages.append(path)

            case "EMX":
                print("EMX slot")
                # get emx source from template.json
                # get pages from import/split_pages/{emx_source}
                path = template["sources"]["emx_dir"]

                if not path:
                    print("no emx source provided")
                    report_pages.append(page["filename"])
                    continue

                pages = Path(path)
                print(f"pages: {pages}")
                for p in sorted(pages.glob("*.pdf"), key=lambda x: numeric_key(x.name)):
                    print(f"page {str(p)}")
                    report_pages.append(str(p))
            case "Black Diamond":
                print("Black Diamond slot")
                # get bd source from template.json
                # get pages from import/split_pages/{bd_source}
                path = template["sources"]["blackdiamond_dir"]

                if not path:
                    print("no bd source provided")
                    report_pages.append(page["filename"])
                    continue

                pages = Path(f"{path}/bd{bd_slot}")
                print(f"pages: {pages}")
                for p in sorted(pages.glob("*.pdf"), key=lambda x: numeric_key(x.name)):
                    print(f"page {str(p)}")
                    report_pages.append(str(p))
                bd_slot += 1
            case _:
                print("no slot saved")
                report_pages.append(page["filename"])
                continue

    print(f"Report pages: {report_pages}")
    report_path = merge_pdfs(report_pages, f"{EXPORT_PATH}/report_{date.today()}.pdf")
    print(f"report_page: {report_path}")
    return report_path

def numeric_key(filename):
    parts = re.split(r'(\d+)', filename)
    return [int(p) if p.isdigit() else p for p in parts]

def merge_pdfs(pdf_list, output_path):
    merged_pdf = pymupdf.open()

    for pdf_path in pdf_list:
        pdf_document = pymupdf.open(pdf_path)
        merged_pdf.insert_pdf(pdf_document)
        pdf_document.close()    

    merged_pdf.save(output_path)

    saved_path = merged_pdf.name
    merged_pdf.close()

    return saved_path