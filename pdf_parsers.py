import pdfplumber
from markitdown import MarkItDown
from agentic_doc.parse import parse
from typing import Dict, Any, List
import os

class PDFParsers:
    """Handles the actual PDF parsing with different libraries"""
    
    @staticmethod
    def parse_with_pdfplumber(file_path: str) -> Dict[str, Any]:
        """Fast mode - using pdfplumber"""
        try:
            content = {}
            markdown_content = "# PDF Extraction - Fast Mode (pdfplumber)\n\n"
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages):
                    # Enhanced text extraction
                    text = page.extract_text() or ""
                    
                    # Extract characters with formatting information
                    chars = page.chars if hasattr(page, 'chars') and page.chars else []
                    char_info = []
                    if chars:
                        for char in chars[:10]:  # Sample first 10 chars for analysis
                            char_info.append({
                                'text': char.get('text', ''),
                                'size': char.get('size', 0),
                                'fontname': char.get('fontname', ''),
                                'bold': char.get('bold', False),
                                'italic': char.get('italic', False)
                            })
                    
                    # Extract tables
                    tables = page.extract_tables()
                    table_data = []
                    for table in tables:
                        table_data.append([row for row in table if any(cell is not None for cell in row)])
                    
                    content[f"page_{i+1}"] = {
                        "text": text,
                        "tables": table_data,
                        "page_number": i + 1,
                        "bbox": page.bbox,
                        "characters_sample": char_info,
                        "width": page.width,
                        "height": page.height
                    }
                    
                    # Build markdown content
                    markdown_content += f"## Page {i+1}\n\n"
                    markdown_content += f"{text}\n\n"
                    
                    if table_data:
                        markdown_content += "### Tables\n\n"
                        for table_idx, table in enumerate(table_data):
                            markdown_content += f"#### Table {table_idx + 1}\n\n"
                            for row in table:
                                markdown_content += "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |\n"
                            markdown_content += "\n"
                    
                    markdown_content += "---\n\n"
            
            return {
                "success": True,
                "content": content,
                "markdown_content": markdown_content,
                "total_pages": total_pages,
                "method": "pdfplumber"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def parse_with_markitdown(file_path: str) -> Dict[str, Any]:
        """Rich mode - using actual markitdown library"""
        try:
            # Initialize markitdown with plugins enabled for better accuracy
            md = MarkItDown(enable_plugins=True)
            
            # Convert PDF using markitdown
            result = md.convert(file_path)
            
            # Build structured content
            content = {
                "page_1": {  # markitdown typically processes as single document
                    "text": result.text_content,
                    "page_number": 1,
                    "processed_with": "markitdown"
                }
            }
            
            # Generate markdown content
            markdown_content = "# PDF Extraction - Rich Mode (markitdown)\n\n"
            markdown_content += "## Extracted Content\n\n"
            markdown_content += result.text_content + "\n\n"
        
            
            return {
                "success": True,
                "content": content,
                "markdown_content": markdown_content,
                "total_pages": 1,  # markitdown processes as single document
                "method": "markitdown",
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def parse_with_agentic_doc(file_path: str) -> Dict[str, Any]:
        """Pro mode - using actual agentic-doc library for image-based PDFs"""
        try:
            # Parse PDF using agentic-doc
            results = parse(file_path)
            
            content = {}
            markdown_content = "# PDF Extraction - Pro Mode (agentic-doc)\n\n"
            markdown_content += "## OCR Extracted Content\n\n"
            
            for i, result in enumerate(results):
                page_markdown = result.markdown if hasattr(result, 'markdown') else str(result)
                
                content[f"page_{i+1}"] = {
                    "markdown": page_markdown,
                    "page_number": i + 1,
                    "processed_with": "agentic_doc",
                    "is_ocr_processed": True
                }
                
                # Build markdown content
                markdown_content += f"## Page {i+1}\n\n"
                markdown_content += f"{page_markdown}\n\n"
                markdown_content += "---\n\n"
            
            return {
                "success": True,
                "content": content,
                "markdown_content": markdown_content,
                "total_pages": len(results),
                "method": "agentic_doc"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}