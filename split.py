from pypdf import PdfReader, PdfWriter
import os

def split_book(input_path, book_prefix, chapters):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
    
    reader = PdfReader(input_path)
    os.makedirs("static/books", exist_ok=True)
    total_pages = len(reader.pages)
    
    for ch_name, (start_page, end_page) in chapters.items():
        actual_end = min(end_page, total_pages)
        if start_page > total_pages:
            continue
            
        writer = PdfWriter()
        for i in range(start_page - 1, actual_end):
            writer.add_page(reader.pages[i])
            
        output_path = f"static/books/{book_prefix}_{ch_name}.pdf"
        with open(output_path, "wb") as f:
            writer.write(f)
        print(f"Generated: {output_path} (Pages {start_page} to {actual_end})")

# Full list of chapters for Swokowski 
# (Note: Check your specific PDF's Table of Contents and tweak the end numbers if your edition differs slightly)
swokowski_chapters = {
    "ch1": (1, 65),
    "ch2": (66, 140),
    "ch3": (141, 220),
    "ch4": (221, 290),
    "ch5": (291, 360),
    "ch6": (361, 430),
    "ch7": (431, 500),
    "ch8": (501, 570),
    "ch9": (571, 640),
    "ch10": (641, 710),
    "ch11": (711, 790),
    "ch12": (791, 870),
    "ch13": (871, 950),
}

# Full list of chapters for Thomas' Calculus 
thomas_chapters = {
    "ch1": (1, 57),
    "ch2": (58, 134),
    "ch3": (135, 221),
    "ch4": (222, 296),
    "ch5": (297, 364),
    "ch6": (365, 419),
    "ch7": (420, 455),
    "ch8": (456, 520),
    "ch9": (521, 575),
    "ch10": (576, 627),
    "ch11": (628, 700),
    "ch12": (701, 750),
    "ch13": (751, 792),
    "ch14": (793, 853),
    "ch15": (854, 949),
    "ch16": (950, 1042),
}

print("Splitting Swokowski into all chapters...")
split_book("static/books/swokowski.pdf", "swokowski", swokowski_chapters)

print("\nSplitting Thomas into all chapters...")
split_book("static/books/thomas.pdf", "thomas", thomas_chapters)

print("\nAll textbook chapters generated successfully!")