# Unstructured Data Extraction — Notes

## Sources Processed
1. **benefits.pdf** — synthetic Summary of Benefits and Coverage (pdfplumber)
2. **claims_process.docx** — synthetic claims filing guide (python-docx)
3. **enrollment_scan.pdf** — synthetic scanned enrollment form (pytesseract + pdf2image OCR)
4. **Clean webpage** — American Heart Association FAQ page (requests + BeautifulSoup)
5. **Messy webpage** — CMS Fact Sheets & FAQs index page (requests + BeautifulSoup)

## Observations

**PDF extraction (pdfplumber):** Text and table content extracted cleanly with correct
structure preserved. No issues.

**Word doc extraction (python-docx):** Headings and bullet points extracted as plain
paragraphs — all text captured correctly, though formatting (bold, bullets) is lost
in plain text output.

**OCR (pytesseract):** Correctly read the synthetic form fields (name, member ID,
plan name) from the image-based PDF. [Note here if you spotted any misread
characters or garbled words.]

**Clean webpage scrape:** Produced readable, well-formed sentences with minimal noise.

**Messy webpage scrape:** Contained repeated dates, navigation fragments, and broken
sentence structure even after basic cleaning (whitespace collapse). This shows that
raw `get_text()` scraping isn't sufficient for messy real-world pages — targeted
extraction (e.g. selecting specific `<div>`/`<article>` tags) would be needed for
production use.

## Next Steps
This raw text is the foundation for the RAG/chunking pipeline planned for a later day.