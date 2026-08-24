import pymupdf
from pathlib import Path
from src.paths import BASE_DATA_PATH

class PDFReader:

    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.import_path = BASE_DATA_PATH
        self.import_path.mkdir(parents=True, exist_ok=True)

    def get_text(self):
        text = []

        with pymupdf.open(self.pdf_path) as doc:
            for page in doc:
                text.append(page.get_text())

            return "\n".join(text)
        
    # def split_pages(self):
    #     doc = pymupdf.open(self.pdf_path)
    #     base_name = Path(doc.name).stem

    #     for page_num in range(len(doc)):  
    #         new_pdf = pymupdf.open()  
    #         new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
    #         output_path = self.import_path / f"{page_num}.pdf"
    #         print(f"output_path: {output_path}")
            
    #         new_pdf.save(output_path)
    #         new_pdf.close()
        
    #     print(f"Successfully split {doc.name} into {len(doc)} pages.")
    #     doc.close()
            
    def split_pages(self):
        doc = pymupdf.open(self.pdf_path)
        base_name = Path(doc.name).stem

        # Create a unique output directory named after the source file
        output_dir = self.import_path / base_name
        output_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(len(doc)):
            new_pdf = pymupdf.open()
            new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)

            output_path = output_dir / f"{page_num}.pdf"
            print(f"output_path: {output_path}")

            new_pdf.save(output_path)
            new_pdf.close()

        print(f"Successfully split {doc.name} into {len(doc)} pages in {output_dir}.")
        doc.close()
        
        return output_dir
            