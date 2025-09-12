"""Document structure extraction: sections, headings, paragraphs for better citations."""
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from ..common.logging import get_logger

log = get_logger("ingest/structure")

class DocumentSection:
    def __init__(self, section_id: str, source_id: str, title: str, number: Optional[str] = None, 
                 level: int = 0, page_start: int = 1, page_end: int = 1, parent_id: Optional[str] = None):
        self.section_id = section_id
        self.source_id = source_id
        self.parent_id = parent_id
        self.title = title
        self.number = number
        self.level = level
        self.page_start = page_start
        self.page_end = page_end
        self.path = self._build_path()
    
    def _build_path(self) -> str:
        # For now, simple path construction
        if self.number:
            return f"{self.number} > {self.title}"
        return self.title

def extract_section_tree(pages: List[str], pdf_path: Optional[Path] = None) -> List[DocumentSection]:
    """Extract hierarchical document structure from pages."""
    sections = []
    
    try:
        # Try to extract PDF outline/TOC first
        if pdf_path:
            sections = _extract_pdf_outline(pdf_path)
            if sections:
                log.info(f"Extracted {len(sections)} sections from PDF outline")
                return sections
    except Exception as e:
        log.warning(f"PDF outline extraction failed: {e}")
    
    # Fallback to heading pattern detection
    sections = _extract_heading_patterns(pages)
    log.info(f"Extracted {len(sections)} sections from heading patterns")
    return sections

def _extract_pdf_outline(pdf_path: Path) -> List[DocumentSection]:
    """Extract sections from PDF outline/bookmarks."""
    sections = []
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        outline = doc.get_toc()
        doc.close()
        
        if not outline:
            return []
        
        for i, (level, title, page_num) in enumerate(outline):
            section_id = f"sec_{i:04d}"
            # Estimate page_end as next section start - 1, or document end
            page_end = outline[i + 1][2] - 1 if i + 1 < len(outline) else page_num
            
            section = DocumentSection(
                section_id=section_id,
                source_id="",  # Will be set by caller
                title=title.strip(),
                number=_extract_section_number(title),
                level=level,
                page_start=page_num,
                page_end=max(page_num, page_end)
            )
            sections.append(section)
            
    except Exception as e:
        log.warning(f"PDF outline parsing failed: {e}")
        return []
    
    return sections

def _extract_heading_patterns(pages: List[str]) -> List[DocumentSection]:
    """Fallback: extract sections from heading patterns."""
    sections = []
    
    # Common heading patterns in regulatory documents
    heading_patterns = [
        r'^\s*([IVX]+|\d+)\.\s*([A-Z][^.!?]*[^.!?\s])\s*$',  # "1. DEFINITIONS" or "I. SCOPE"
        r'^\s*([A-Z][A-Z\s]{3,})\s*$',  # ALL CAPS lines
        r'^\s*(\d+(?:\.\d+)*)\s+([A-Z][^.!?]*[^.!?\s])\s*$',  # "2.1 Risk Assessment"
    ]
    
    section_count = 0
    for page_idx, page_text in enumerate(pages, 1):
        lines = page_text.split('\n')
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if len(line) < 3 or len(line) > 150:  # Skip very short/long lines
                continue
                
            for pattern in heading_patterns:
                match = re.match(pattern, line)
                if match:
                    section_count += 1
                    section_id = f"sec_{section_count:04d}"
                    
                    if len(match.groups()) >= 2:
                        number, title = match.groups()[:2]
                    else:
                        number = None
                        title = line
                    
                    level = _determine_heading_level(number, title)
                    
                    section = DocumentSection(
                        section_id=section_id,
                        source_id="",  # Will be set by caller
                        title=title.strip(),
                        number=number.strip() if number else None,
                        level=level,
                        page_start=page_idx,
                        page_end=page_idx  # Single page for now, can be enhanced
                    )
                    sections.append(section)
                    break
    
    return sections

def _extract_section_number(title: str) -> Optional[str]:
    """Extract section number from title."""
    # Match patterns like "1.", "2.1", "I.", "A."
    match = re.match(r'^([IVX]+|\d+(?:\.\d+)*|[A-Z])\.?\s*', title)
    return match.group(1) if match else None

def _determine_heading_level(number: Optional[str], title: str) -> int:
    """Determine hierarchical level from numbering/formatting."""
    if not number:
        return 1
    
    # Roman numerals = level 1
    if re.match(r'^[IVX]+$', number):
        return 1
    
    # Count dots in decimal numbering (2.1.3 = level 3)
    if '.' in number:
        return len(number.split('.'))
    
    # Single digit = level 1
    if number.isdigit():
        return 1
    
    return 1

def assign_sections_to_chunks(chunks: List[Dict[str, Any]], sections: List[DocumentSection]) -> List[Dict[str, Any]]:
    """Assign section information to chunks based on page/position."""
    enhanced_chunks = []
    
    for chunk in chunks:
        page_start = chunk.get('page_start', 1)
        page_end = chunk.get('page_end', 1)
        
        # Find the most specific section that contains this chunk
        best_section = None
        for section in sections:
            if section.page_start <= page_start <= section.page_end:
                if not best_section or section.level > best_section.level:
                    best_section = section
        
        # Enhance chunk with section information
        enhanced_chunk = dict(chunk)
        if best_section:
            enhanced_chunk['section_id'] = best_section.section_id
            enhanced_chunk['section_path'] = best_section.path
        else:
            enhanced_chunk['section_path'] = chunk.get('section_path', 'Document')
        
        enhanced_chunks.append(enhanced_chunk)
    
    return enhanced_chunks

def detect_paragraphs(page_text: str) -> Dict[int, int]:
    """Detect paragraph numbers within a page."""
    para_mapping = {}
    
    # Split by double newlines or indented lines
    paragraphs = re.split(r'\n\s*\n|\n(?=\s{4,})', page_text)
    
    char_pos = 0
    for para_no, para in enumerate(paragraphs, 1):
        para_end = char_pos + len(para)
        para_mapping[char_pos] = para_no
        char_pos = para_end + 2  # Account for paragraph separators
    
    return para_mapping

def get_paragraph_number(text_position: int, para_mapping: Dict[int, int]) -> int:
    """Get paragraph number for a given text position."""
    best_para = 1
    for start_pos, para_no in para_mapping.items():
        if start_pos <= text_position:
            best_para = para_no
        else:
            break
    return best_para
