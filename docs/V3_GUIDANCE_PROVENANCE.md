# V3 guidance provenance

V3 collects from Fair Work Ombudsman pages only:

- Workplace Guides, downloaded as official DOCX files where available;
- Fact Sheets published under the FWO tools-and-resources section;
- Best Practice Guides published under the FWO tools-and-resources section.

The fetched HTML and DOCX files are kept under `data/raw/guidance/` and are
ignored by Git. JSONL chunks retain the page URL, publisher, retrieval date,
document type and authority level. A guidance record is deliberately stored
separately from the Act, Award or Pay Guide it may discuss.
