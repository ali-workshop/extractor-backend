import re
import os
from pathlib import Path
from typing import Dict, Any, Optional
from spire.doc import *
from spire.doc.common import *
import tempfile

class WordProcessor:
    """Handles conversion of markdown text to Word documents with footnote processing"""
    
    @staticmethod
    def normalize_arabic_text(text: str) -> str:
        """Normalize Arabic text and digits"""
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        western_digits = "0123456789"
        trans = str.maketrans(arabic_digits, western_digits)
        text = text.translate(trans)
        text = re.sub(r"[\u200E\u200F\u202A-\u202E]", "", text)  # remove invisible marks
        return text
    
    @staticmethod
    def extract_footnotes(text: str) -> Dict[str, str]:
        """Extract manual footnotes from text"""
        footnote_pattern = re.compile(r'^\s*\((\d+)\)\s*(.+)$', flags=re.MULTILINE)
        footnotes = {}
        
        for match in footnote_pattern.finditer(text):
            num = match.group(1)
            footnote_text = match.group(2).strip()
            footnotes[num] = footnote_text
        
        return footnotes
    
    @staticmethod
    def remove_footnote_content_from_main(text: str, footnotes: Dict[str, str]) -> str:
        """Remove footnote content from main text"""
        cleaned_text = text
        for num, content in footnotes.items():
            escaped_content = re.escape(content)
            cleaned_text = re.sub(escaped_content, '', cleaned_text)
        
        # Clean up formatting
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        return cleaned_text.strip()
    
    @staticmethod
    def clean_markdown_text(text: str) -> str:
        """Clean markdown text before processing"""
        # Remove HTML comments
        cleaned = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Remove horizontal lines
        cleaned = re.sub(r'-{3,}', '', cleaned)
        # Normalize multiple blank lines
        cleaned = re.sub(r'\n{2,}', '\n\n', cleaned)
        return cleaned.strip()
    
    def process_to_word(self, markdown_content: str, output_dir: str = "outputs", 
                       language: str = "auto") -> Dict[str, Any]:
        """
        Convert markdown content to Word document with footnote processing
        
        Args:
            markdown_content: Extracted markdown text from PDF
            output_dir: Directory to save output file
            language: Text direction ('auto', 'ltr', 'rtl')
        
        Returns:
            Dictionary with processing results
        """
        try:
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Step 1: Clean markdown text
            clean_text = self.clean_markdown_text(markdown_content)
            
            # Step 2: Extract footnotes
            footnotes = self.extract_footnotes(clean_text)
            
            # Step 3: Remove footnote content from main text
            main_text = self.remove_footnote_content_from_main(clean_text, footnotes)
            
            # Step 4: Create Word document
            document = Document()
            section = document.AddSection()
            paragraph = section.AddParagraph()
            paragraph.AppendText(main_text)
            
            # Set text direction based on language detection
            if language == "rtl" or (language == "auto" and self.detect_arabic_text(main_text)):
                paragraph.Format.HorizontalAlignment = HorizontalAlignment.Right
                paragraph.Format.RightToLeft = True
            else:
                paragraph.Format.HorizontalAlignment = HorizontalAlignment.Left
                paragraph.Format.RightToLeft = False
            
            # Step 5: Insert Word footnotes
            inserted_refs = set()
            inline_ref_pattern = re.compile(r'\(\s*(\d+)\s*\)')
            
            for match in inline_ref_pattern.finditer(main_text):
                num = match.group(1)
                if num not in footnotes or num in inserted_refs:
                    continue
                inserted_refs.add(num)
                
                note_text = footnotes[num]
                selection = document.FindString(match.group(), False, True)
                
                if selection is not None:
                    text_range = selection.GetAsOneRange()
                    para = text_range.OwnerParagraph
                    index = para.ChildObjects.IndexOf(text_range)
                    
                    # Insert actual Word footnote
                    footnote = para.AppendFootnote(FootnoteType.Footnote)
                    para.ChildObjects.Insert(index + 1, footnote)
                    
                    # Format footnote text
                    fn_text = footnote.TextBody.AddParagraph().AppendText(note_text)
                    fn_text.CharacterFormat.FontName = "Arial"
                    fn_text.CharacterFormat.FontSize = 12
                    
                    # Format footnote marker
                    footnote.MarkerCharacterFormat.FontName = "Simplified Arabic"
                    footnote.MarkerCharacterFormat.FontSize = 14
                    footnote.MarkerCharacterFormat.Bold = True
            
            # Step 6: Generate output filename
            output_file = Path(output_dir) / f"processed_document_{len(inserted_refs)}_footnotes.docx"
            
            # Step 7: Save document
            document.SaveToFile(str(output_file), FileFormat.Docx2016)
            document.Close()
            
            return {
                "success": True,
                "word_file": str(output_file),
                "footnotes_count": len(inserted_refs),
                "total_footnotes_detected": len(footnotes),
                "language": "rtl" if paragraph.Format.RightToLeft else "ltr"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Word processing failed: {str(e)}"
            }
    
    def detect_arabic_text(self, text: str) -> bool:
        """Detect if text contains Arabic characters"""
        arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        return bool(arabic_pattern.search(text))