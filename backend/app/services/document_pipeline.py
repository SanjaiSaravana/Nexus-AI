import io
import os
import re
import csv
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException, status

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}

class ParsedSection:
    def __init__(self, content: str, page_number: int = 1, section_heading: str = "General"):
        self.content = content
        self.page_number = page_number
        self.section_heading = section_heading

class DocumentPipeline:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename: strip path traversal patterns and directory separators.
        Rejects null bytes and traversal escapes.
        """
        if not filename:
            return "document"
        if "\x00" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Null byte detected in filename."
            )
        # Reject explicit path traversal sequences
        if ".." in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Path traversal detected in filename."
            )
        return os.path.basename(filename.replace("\\", "/"))

    @classmethod
    def validate_content(cls, ext: str, file_bytes: bytes):
        """
        Deep inspection of file headers and payload:
        - PDF magic bytes check (%PDF-)
        - DOCX zip container check (PK\x03\x04) and zip-bomb check
        - Plaintext rejection of executables (MZ, ELF, Mach-O, shebang) and binary null bytes
        """
        if not ext.startswith("."):
            ext = f".{ext}"
        ext = ext.lower()

        if ext == ".pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PDF file: Missing %PDF- magic header."
                )
        elif ext == ".docx":
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DOCX file: Missing standard zip header PK\\x03\\x04."
                )
            # Zip Bomb protection
            import zipfile
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    total_uncompressed = sum(info.file_size for info in z.infolist())
                    if total_uncompressed > 50 * 1024 * 1024:  # 50MB max uncompressed
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Security violation: Archive expansion exceeds safety limit (possible zip bomb)."
                        )
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DOCX file: Corrupted archive structure."
                )
        elif ext in [".txt", ".md", ".csv"]:
            # Check for executable signatures
            if file_bytes.startswith(b"MZ"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Executable binary (Windows PE) detected."
                )
            if file_bytes.startswith(b"\x7fELF"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Executable binary (Linux ELF) detected."
                )
            if file_bytes.startswith((b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Executable binary (Mach-O) detected."
                )
            if file_bytes.startswith(b"#!"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Shell script executable detected."
                )
            if b"\x00" in file_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Binary null bytes detected in text document."
                )

    @classmethod
    def validate_file(cls, filename: str, file_size: int, max_size_mb: int = 25, file_bytes: bytes = None) -> str:
        """Validate filename extension, sanitized path, and size. Optionally validate magic bytes."""
        if not filename or "." not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename must have a valid extension (.pdf, .docx, .txt, .md, .csv)"
            )

        # Sanitize filename (guards against path traversal)
        cls.sanitize_filename(filename)

        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Supported formats are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        if file_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {max_size_mb}MB."
            )

        if file_bytes is not None:
            cls.validate_content(ext, file_bytes)

        return ext.lstrip(".")

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace, remove control characters and clean text."""
        if not text:
            return ""
        # Replace carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace multiple spaces with a single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace 3 or more newlines with 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @classmethod
    def parse_document(cls, filename: str, file_bytes: bytes) -> List[ParsedSection]:
        """Extract text sections with page numbers and structural headings."""
        ext = os.path.splitext(filename)[1].lower()
        sections: List[ParsedSection] = []

        if ext == ".pdf":
            sections = cls._parse_pdf(file_bytes)
        elif ext == ".docx":
            sections = cls._parse_docx(file_bytes)
        elif ext == ".csv":
            sections = cls._parse_csv(file_bytes)
        elif ext == ".md":
            sections = cls._parse_markdown(file_bytes)
        elif ext == ".txt":
            sections = cls._parse_txt(file_bytes)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parser not implemented for extension '{ext}'"
            )

        if not sections or all(not s.content.strip() for s in sections):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract readable text from document. File may be encrypted, scanned image without OCR, or empty."
            )

        return sections

    @classmethod
    def _parse_pdf(cls, file_bytes: bytes) -> List[ParsedSection]:
        from pypdf import PdfReader
        sections = []
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                cleaned = cls.clean_text(page_text)
                if cleaned:
                    sections.append(ParsedSection(
                        content=cleaned,
                        page_number=page_idx + 1,
                        section_heading=f"Page {page_idx + 1}"
                    ))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF document: {str(e)}"
            )
        return sections

    @classmethod
    def _parse_docx(cls, file_bytes: bytes) -> List[ParsedSection]:
        import docx
        sections = []
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            current_heading = "Overview"
            current_paragraphs = []

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                # Heading detection
                if para.style and para.style.name and 'heading' in para.style.name.lower():
                    if current_paragraphs:
                        sections.append(ParsedSection(
                            content=cls.clean_text("\n".join(current_paragraphs)),
                            page_number=1,
                            section_heading=current_heading
                        ))
                        current_paragraphs = []
                    current_heading = text
                else:
                    current_paragraphs.append(text)

            # Tables
            for table in doc.tables:
                table_rows = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_data:
                        table_rows.append(" | ".join(row_data))
                if table_rows:
                    current_paragraphs.append("\nTable Data:\n" + "\n".join(table_rows))

            if current_paragraphs:
                sections.append(ParsedSection(
                    content=cls.clean_text("\n".join(current_paragraphs)),
                    page_number=1,
                    section_heading=current_heading
                ))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse DOCX document: {str(e)}"
            )
        return sections

    @classmethod
    def _parse_csv(cls, file_bytes: bytes) -> List[ParsedSection]:
        sections = []
        try:
            decoded = file_bytes.decode('utf-8', errors='replace')
            reader = csv.reader(io.StringIO(decoded))
            rows = list(reader)
            if not rows:
                return []

            headers = rows[0]
            row_chunks = []
            for r_idx, row in enumerate(rows[1:], start=1):
                # format row as key-value string
                row_str = ", ".join(f"{h}: {v}" for h, v in zip(headers, row) if v.strip())
                if row_str:
                    row_chunks.append(f"Row {r_idx}: {row_str}")

                if len(row_chunks) >= 20:
                    sections.append(ParsedSection(
                        content="\n".join(row_chunks),
                        page_number=(r_idx // 20) + 1,
                        section_heading=f"Rows {r_idx - 19} to {r_idx}"
                    ))
                    row_chunks = []

            if row_chunks:
                sections.append(ParsedSection(
                    content="\n".join(row_chunks),
                    page_number=(len(rows) // 20) + 1,
                    section_heading="Data Records"
                ))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse CSV document: {str(e)}"
            )
        return sections

    @classmethod
    def _parse_markdown(cls, file_bytes: bytes) -> List[ParsedSection]:
        sections = []
        decoded = file_bytes.decode('utf-8', errors='replace')
        lines = decoded.splitlines()

        current_heading = "Header"
        current_lines = []

        for line in lines:
            if line.startswith("#"):
                if current_lines:
                    cleaned = cls.clean_text("\n".join(current_lines))
                    if cleaned:
                        sections.append(ParsedSection(
                            content=cleaned,
                            page_number=1,
                            section_heading=current_heading
                        ))
                    current_lines = []
                current_heading = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            cleaned = cls.clean_text("\n".join(current_lines))
            if cleaned:
                sections.append(ParsedSection(
                    content=cleaned,
                    page_number=1,
                    section_heading=current_heading
                ))

        return sections

    @classmethod
    def _parse_txt(cls, file_bytes: bytes) -> List[ParsedSection]:
        decoded = file_bytes.decode('utf-8', errors='replace')
        cleaned = cls.clean_text(decoded)
        paragraphs = cleaned.split("\n\n")

        sections = []
        for p_idx, para in enumerate(paragraphs, start=1):
            if para.strip():
                sections.append(ParsedSection(
                    content=para.strip(),
                    page_number=1,
                    section_heading=f"Paragraph {p_idx}"
                ))
        return sections

    @classmethod
    def semantic_chunk(
        cls,
        sections: List[ParsedSection],
        max_chunk_chars: int = 1500,
        overlap_chars: int = 150
    ) -> List[Dict[str, Any]]:
        """Chunk sections with boundary awareness and overlap."""
        chunks = []
        chunk_idx = 0

        for sec in sections:
            content = sec.content
            if len(content) <= max_chunk_chars:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "content": content,
                    "page_number": sec.page_number,
                    "section_heading": sec.section_heading,
                    "metadata": {
                        "length": len(content),
                        "words": len(content.split())
                    }
                })
                chunk_idx += 1
            else:
                # Sliding window chunking with paragraph/sentence respect
                start = 0
                while start < len(content):
                    end = min(start + max_chunk_chars, len(content))
                    # Attempt sentence break near end
                    if end < len(content):
                        period_idx = content.rfind(". ", start, end)
                        if period_idx != -1 and period_idx > start + (max_chunk_chars // 2):
                            end = period_idx + 1

                    sub_chunk = content[start:end].strip()
                    if sub_chunk:
                        chunks.append({
                            "chunk_index": chunk_idx,
                            "content": sub_chunk,
                            "page_number": sec.page_number,
                            "section_heading": sec.section_heading,
                            "metadata": {
                                "length": len(sub_chunk),
                                "words": len(sub_chunk.split())
                            }
                        })
                        chunk_idx += 1

                    if end >= len(content):
                        break
                    start = max(start + 1, end - overlap_chars)

        return chunks

document_pipeline = DocumentPipeline()
