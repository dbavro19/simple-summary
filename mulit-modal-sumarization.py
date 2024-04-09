import boto3
import botocore
import json
import pdfplumber
import fitz  # PyMuPDF

def parse_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages):
            print(f"Page {page_number + 1}:")

            # Extract text
            text = page.extract_text()
            if text:
                print("  Text found:")
                print(text[:100])  # Print the first 100 characters of text

            # Extract tables
            tables = page.extract_tables()
            if tables:
                print("  Tables found:")
                for table in tables:
                    print(table)  # Print the table data

            # Extract images
            with fitz.open(pdf_path) as doc:
                img_page = doc.load_page(page_number)
                images = img_page.get_images(full=True)
                if images:
                    print("  Images found:")
                    for img_index, img in enumerate(images):
                        print(f"    Image {img_index + 1}")


def summarize_section(text):
    # Summarize the section
    summary = ""
    return summary


def summarize_summaries(summaries):
    # Summarize the summaries
    summary = ""
    for section in summaries:
        summary += section + "\n"

    # Return the summary
    return summary

def index_section(section):
    # Index the section
    index = ""
    return index

if __name__ == "__main__":
    parse_pdf("test3.pdf")

