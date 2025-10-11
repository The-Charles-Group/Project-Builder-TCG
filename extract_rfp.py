#!/usr/bin/env python3
"""Extract text from Uncommon Schools RFP PDF"""

from pypdf import PdfReader
import sys

pdf_path = "attached_assets/FINAL Uncommon Schools - May 2025 Media Agency RFP (2)_1760155166246.pdf"

try:
    reader = PdfReader(pdf_path)
    text = ""
    for page_num, page in enumerate(reader.pages):
        text += page.extract_text()
    
    # Save to file
    with open("/tmp/uncommon_schools_rfp.txt", "w") as f:
        f.write(text)
    
    print(f"Extracted {len(text)} characters from {len(reader.pages)} pages")
    print("\nFirst 2000 characters of RFP:")
    print("-" * 50)
    print(text[:2000])
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)