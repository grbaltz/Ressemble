# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
import json
import re
import pymupdf
from datetime import date

PAGES_CONFIG_PATH = Path("/home/grbaltz/Development/YearReportCompiler/src/pages.json")
TEMPLATE_CONFIG_PATH = Path("/home/grbaltz/Development/YearReportCompiler/src/template.json")
BASE_DATA_PATH = Path("/home/grbaltz/Development/YearReportCompiler/src/import/split_pages")
ADVISORS_PATH = Path("/home/grbaltz/Development/YearReportCompiler/src/import/advisors")
EXPORT_PATH = Path("/home/grbaltz/Development/YearReportCompiler/src/export")

AVENIR_BLACK_FONT_FILE = "/home/grbaltz/Development/YearReportCompiler/src/fonts/Avenir Black.ttf"

def assemble_report(log, progress, advisors_filename, client_name, enrolled):
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

        doc = pymupdf.open(page.get("filename"))
        pdf = doc[0]
        
        # check if placeholder
        if not page.get("placeholder") and not page.get("slot"):
            report_pages.append(page["filename"])
            continue
        
        match page["slot"]:
            case "cover":
                print("Cover slot")

                old_text = "The ### Household"
                new_text = "The " + client_name + " Household"
                replace_text_with_formatting(page["filename"], old_text, new_text, AVENIR_BLACK_FONT_FILE)
                # hits = pdf.search_for(old_text)


                # for rect in hits:
                #     pdf.add_redact_annot(rect)
                #     pdf.apply_redactions()
                #     pdf.insert_text(rect.bl - (0, 3), new_text)

                # doc.save(page["filename"], incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
                # doc.close()

                report_pages.append(page["filename"])
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
            case "emx":
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
            case "bd":
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

    # saved_path = merged_pdf.name

    merged_pdf.save(output_path)
    merged_pdf.close()

    return output_path

def int_to_rgb(color_int):
    r = ((color_int >> 16) & 0xFF) / 255
    g = ((color_int >> 8) & 0xFF) / 255
    b = (color_int & 0xFF) / 255
    return (r, g, b)


def replace_text_with_formatting(pdf_path, search_text, replace_text, font_file=None):
    doc = pymupdf.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")

        for block in blocks["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if search_text in span["text"]:

                            print(
                                span["text"],
                                span["font"],
                                span["size"],
                                span["color"],
                            )

                            size = span["size"]
                            color = int_to_rgb(span["color"])
                            bbox = span["bbox"]
                            rect = pymupdf.Rect(bbox)

                            page.add_redact_annot(rect)
                            page.apply_redactions()

                            if font_file:
                                fontname = "Avenir-Black"
                                page.insert_font(fontname=fontname, fontfile=font_file)
                            else:
                                fontname = span["font"]

                            page.insert_text(
                                rect.bl,
                                replace_text,
                                fontname=fontname,
                                fontsize=size,
                                color=color
                            )

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()