"""Convert DOCX and PDF files in Documentos/ to Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path

import mammoth


def convert_docx(source: Path, destination: Path) -> None:
	with source.open("rb") as document:
		result = mammoth.convert_to_markdown(document)
	destination.write_text(result.value.rstrip() + "\n", encoding="utf-8")


def convert_pdf(source: Path, destination: Path) -> None:
	import pymupdf

	pages = []
	with pymupdf.open(source) as document:
		for page in document:
			text = page.get_text().strip()
			if text:
				pages.append(text)
	destination.write_text("\n\n".join(pages).rstrip() + "\n", encoding="utf-8")


def pdf_has_docx_equivalent(pdf: Path, docx_files: set[Path]) -> bool:
	candidate = pdf.with_suffix("")
	return candidate.with_suffix(".docx") in docx_files or pdf.stem + ".docx" in {
		path.name for path in docx_files
	}


def convert_folder(folder: Path, include_pdfs: bool = False) -> list[Path]:
	docx_files = set(folder.glob("*.docx"))
	converted: list[Path] = []

	for source in sorted(docx_files):
		destination = source.with_suffix(".md")
		convert_docx(source, destination)
		converted.append(destination)

	if include_pdfs:
		pdf_files = sorted(folder.glob("*.pdf"))
	else:
		pdf_files = [
			source
			for source in sorted(folder.glob("*.pdf"))
			if not pdf_has_docx_equivalent(source, docx_files)
		]

	for source in pdf_files:
		destination = source.with_suffix(".md")
		convert_pdf(source, destination)
		converted.append(destination)

	return converted


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"folder",
		nargs="?",
		type=Path,
		default=Path(__file__).parent / "Documentos",
		help="folder containing DOCX and PDF files",
	)
	parser.add_argument(
		"--include-pdfs",
		action="store_true",
		help="also convert PDFs that have a DOCX equivalent",
	)
	args = parser.parse_args()

	for destination in convert_folder(args.folder, args.include_pdfs):
		print(destination.name)


if __name__ == "__main__":
	main()
