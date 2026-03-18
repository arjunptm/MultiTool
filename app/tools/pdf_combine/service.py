from io import BytesIO
from pathlib import Path

import fitz
from pypdf import PdfWriter


def combine_pdfs(pdf_paths: list[str], output_path: str) -> None:
  """
  Combine PDFs in the given order and write them to output_path.
  """
  if not pdf_paths:
    raise ValueError("No PDF files were provided.")

  writer = PdfWriter()

  for pdf_path in pdf_paths:
    path = Path(pdf_path)
    if not path.exists():
      raise FileNotFoundError(f"File not found: {pdf_path}")

    writer.append(str(path))

  output = Path(output_path)
  output.parent.mkdir(parents=True, exist_ok=True)

  with output.open("wb") as f:
    writer.write(f)

  writer.close()


def flatten_and_combine_pdfs(
  pdf_paths: list[str],
  output_path: str,
  dpi: int = 150,
) -> None:
  """
  Flatten PDFs by rasterizing each page, then combine them into one PDF.

  This is a very reliable form of flattening because interactive fields,
  annotations, and appearance layers are burned into the page image.

  Tradeoff:
  - output pages become image-based
  - text may no longer be selectable/searchable
  - file size may increase
  """
  if not pdf_paths:
    raise ValueError("No PDF files were provided.")

  if dpi < 72:
    raise ValueError("dpi must be at least 72.")

  output = Path(output_path)
  output.parent.mkdir(parents=True, exist_ok=True)

  combined_doc = fitz.open()
  zoom = dpi / 72.0
  matrix = fitz.Matrix(zoom, zoom)

  try:
    for pdf_path in pdf_paths:
      input_path = Path(pdf_path)
      if not input_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

      source_doc = fitz.open(str(input_path))
      try:
        for page in source_doc:
          pix = page.get_pixmap(matrix=matrix, alpha=False)

          img_bytes = pix.tobytes("png")
          img_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)

          out_page = combined_doc.new_page(
            width=page.rect.width,
            height=page.rect.height,
          )
          out_page.insert_image(img_rect, stream=img_bytes)
      finally:
        source_doc.close()

    combined_doc.save(str(output), garbage=4, deflate=True)
  finally:
    combined_doc.close()