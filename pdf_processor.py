import os
import tempfile
from typing import Dict, Any
from enum import Enum

# Logging and UI
from colorama import Fore, Style, init
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from loguru import logger
import fitz 
from word_processor import WordProcessor
# Our parsers
from pdf_parsers import PDFParsers

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class ProcessingMode(Enum):
    FAST = "fast"      # pdfplumber for text-based PDFs
    RICH = "rich"      # markitdown for text-based PDFs  
    PRO = "pro"        # agentic-doc for image-based/scanned PDFs

class PDFProcessor:
    def __init__(self):
        self.console = Console()
        self.parsers = PDFParsers()
        self.word_processor = WordProcessor() 
        self.setup_logging()
        
    def setup_logging(self):
        """Setup beautiful logging with colors"""
        logger.remove()
        logger.add(
            lambda msg: self.console.print(f"[cyan]LOG[/cyan] {msg}"),
            format="{message}",
            level="INFO"
        )
    
    def log_mode_selection(self, mode: ProcessingMode, filename: str):
        """Log mode selection with colored output"""
        mode_colors = {
            ProcessingMode.FAST: Fore.GREEN,
            ProcessingMode.RICH: Fore.BLUE, 
            ProcessingMode.PRO: Fore.MAGENTA
        }
        
        mode_descriptions = {
            ProcessingMode.FAST: "Fast (pdfplumber) - Quick but less accurate",
            ProcessingMode.RICH: "Rich (markitdown) - Accurate but slower", 
            ProcessingMode.PRO: "Pro (agentic-doc) - Most accurate for images/scanned"
        }
        
        color = mode_colors.get(mode, Fore.WHITE)
        self.console.print(
            Panel.fit(
                f"📄 Processing: {filename}\n"
                f"🎯 Mode: {color}{mode.value.upper()}{Style.RESET_ALL}\n"
                f"📝 Description: {mode_descriptions[mode]}",
                title="🚀 PDF Processing Started",
                border_style="bright_blue"
            )
        )
    
    
    def detect_pdf_type( self,file_path: str) -> str:
        """Detect PDF type using structural analysis (text/image blocks, fonts), with improved mixed support."""
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            if total_pages == 0:
                return "unknown"
            
            # Sample ~5% pages, capped at 10 for efficiency
            sample_size = min(10, max(1, total_pages // 20))
            sample_indices = [i * total_pages // sample_size for i in range(sample_size)]
            
            image_pages = 0
            text_pages = 0
            ambiguous_pages = 0
            for idx in sample_indices:
                if idx >= total_pages:
                    continue
                page = doc[idx]
                page_area = abs(page.rect)
                
                # Text and image areas via blocks (unified, no separate image call)
                text_area = 0.0
                image_area = 0.0
                blocks = page.get_text("blocks")
                for block in blocks:
                    if len(block) > 6:
                        r = fitz.Rect(block[:4])
                        block_type = block[6]
                        if block_type == 0:  # Text block
                            text = block[4]
                            if text.strip():
                                text_area += abs(r)
                        elif block_type == 1:  # Image block
                            image_area += abs(r)
                
                text_coverage = (text_area / page_area) if page_area > 0 else 0
                image_coverage = (image_area / page_area) if page_area > 0 else 0
                
                # Font check
                has_fonts = len(page.get_fonts()) > 0
                
                # Tunable thresholds
                image_threshold = 0.8  # % page covered by images
                text_threshold = 0.05  # Min text coverage for "text"
                
                # Per-page classification (refined for blocks)
                if image_coverage > image_threshold or (text_coverage < 0.01 and not has_fonts):
                    image_pages += 1
                elif text_coverage > text_threshold and has_fonts:
                    text_pages += 1
                else:
                    ambiguous_pages += 1
            
            image_ratio = image_pages / max(sample_size, 1)
            text_ratio = text_pages / max(sample_size, 1)
            ambiguous_ratio = ambiguous_pages / max(sample_size, 1)
            
            logger.debug(f"PDF analysis: image_ratio={image_ratio:.2f}, text_ratio={text_ratio:.2f}, ambiguous_ratio={ambiguous_ratio:.2f}")
            
            doc.close()
            
            # Decision thresholds (tunable majority for less false mixed)
            majority = 0.6
            if image_ratio > majority:
                return "image_based"
            elif text_ratio > majority:
                return "text_based"
            else:
                return "mixed"
                
        except Exception as e:
            logger.error(f"Error detecting PDF type: {e}")
            return "unknown"
    def save_markdown_output(self, content: str, output_path: str, mode: ProcessingMode):
        """Save extracted content to markdown file"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.success(f"📁 Markdown output saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save markdown output: {e}")
            return False
    
    def process_pdf(self, file_path: str, mode: ProcessingMode, auto_detect: bool = False) -> Dict[str, Any]:
        """Main PDF processing method - orchestrates the parsing"""
        
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}
        
        self.log_mode_selection(mode, os.path.basename(file_path))
        
        # 🚨 ALWAYS detect PDF type for validation (regardless of auto_detect)
        pdf_type = self.detect_pdf_type(file_path)
        logger.info(f"Detected PDF type: {pdf_type}")
        
        # 🛑 VALIDATION: Block FAST/RICH modes for image/mixed PDFs
        if mode in [ProcessingMode.FAST, ProcessingMode.RICH] and pdf_type in ["image_based", "mixed"]:
            self.console.print(
                Panel.fit(
                    f"❌ [bold red]Cannot process {pdf_type.replace('_', ' ')} PDF with {mode.value} mode[/bold red]\n\n"
                    f"📄 [bold]File Type:[/bold] {pdf_type.replace('_', ' ').title()}\n"
                    f"🎯 [bold]Selected Mode:[/bold] {mode.value.upper()}\n"
                    f"💡 [bold]Solution:[/bold] Upgrade to [bold magenta]PRO mode[/bold magenta] for image-based/scanned PDFs\n\n"
                    f"✨ [bold]PRO features:[/bold] Advanced OCR, Image processing, Mixed content handling",
                    title="🚫 Upgrade Required",
                    border_style="red"
                )
            )
            return {
                "success": False, 
                "error": f"Cannot process {pdf_type} PDF with {mode.value} mode",
                "pdf_type": pdf_type,
                "requires_upgrade": True,
                "recommended_mode": "pro"
            }
        
        # Auto-detection logic (only for mode switching, not blocking)
        if auto_detect:
            # Override mode based on detection (only if not already blocked above)
            if pdf_type == "image_based" and mode != ProcessingMode.PRO:
                logger.warning("Image-based PDF detected. Switching to PRO mode for better accuracy.")
                mode = ProcessingMode.PRO
            elif pdf_type == "text_based" and mode == ProcessingMode.PRO:
                logger.info("Text-based PDF detected. PRO mode might be overkill.")
        
        # Process based on selected mode with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            
            progress_descriptions = {
                ProcessingMode.FAST: "📖 Extracting with pdfplumber (Fast Mode)...",
                ProcessingMode.RICH: "🎨 Processing with markitdown (Rich Mode)...", 
                ProcessingMode.PRO: "🔍 OCR processing with agentic-doc (Pro Mode)..."
            }
            
            task = progress.add_task(progress_descriptions[mode], total=100)
            
            try:
                # Call the appropriate parser
                if mode == ProcessingMode.FAST:
                    result = self.parsers.parse_with_pdfplumber(file_path)
                elif mode == ProcessingMode.RICH:
                    result = self.parsers.parse_with_markitdown(file_path)
                elif mode == ProcessingMode.PRO:
                    result = self.parsers.parse_with_agentic_doc(file_path)
                else:
                    result = {"success": False, "error": "Invalid processing mode"}
                
                progress.update(task, completed=100)
                
                # Save markdown file if successful
                if result.get("success"):
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = f"outputs/{mode.value}_{base_name}.md"
                    
                    if self.save_markdown_output(result["markdown_content"], output_path, mode):
                        result["markdown_file"] = output_path
                    
                    self.display_results(result)
                else:
                    logger.error(f"Processing failed: {result.get('error', 'Unknown error')}")
                
                return result
                
            except Exception as e:
                progress.update(task, completed=100)
                error_msg = f"Unexpected error during processing: {e}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
    
    def display_results(self, result: Dict[str, Any]):
        """Display processing results in a beautiful table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="dim", width=20)
        table.add_column("Value", style="green")
        
        table.add_row("Processing Method", result.get("method", "Unknown"))
        table.add_row("Total Pages", str(result.get("total_pages", 0)))
        table.add_row("Status", "✅ Success")
        table.add_row("Output File", result.get("markdown_file", "N/A"))
        
        # Calculate total characters
        total_chars = 0
        content = result.get("content", {})
        for page_data in content.values():
            text = page_data.get("text") or page_data.get("markdown", "")
            total_chars += len(text)
        
        table.add_row("Total Characters", str(total_chars))
        
        self.console.print(
            Panel.fit(
                table,
                title="📊 Processing Results",
                border_style="green"
            )
        )
        
        # Show sample of first page content
        if content:
            first_page = list(content.values())[0]
            sample_text = first_page.get("text") or first_page.get("markdown", "")
            sample_preview = sample_text[:300] + "..." if len(sample_text) > 300 else sample_text
            
            # Show markdown preview
            if result.get("markdown_file"):
                self.console.print(
                    Panel.fit(
                        f"📁 Output saved to: [bold green]{result['markdown_file']}[/bold green]",
                        title="💾 File Output",
                        border_style="blue"
                    )
                )
            
            self.console.print(
                Panel.fit(
                    sample_preview,
                    title="📄 Content Preview",
                    border_style="yellow"
                )
            )


    def save_as_word(self, markdown_content: str, output_dir: str = "outputs", 
                    language: str = "auto") -> Dict[str, Any]:
        """
        Save extracted content as Word document with footnote processing
        
        Args:
            markdown_content: Extracted markdown text
            output_dir: Output directory for Word file
            language: Text direction ('auto', 'ltr', 'rtl')
        
        Returns:
            Dictionary with processing results
        """
        try:
            self.console.print(
                Panel.fit(
                    "📝 Converting to Word document with footnote processing...",
                    title="🔤 Word Export",
                    border_style="blue"
                )
            )
            
            result = self.word_processor.process_to_word(
                markdown_content, output_dir, language
            )
            
            if result["success"]:
                self.console.print(
                    Panel.fit(
                        f"✅ Word document created successfully!\n"
                        f"📁 File: {result['word_file']}\n"
                        f"📑 Footnotes processed: {result['footnotes_count']}\n"
                        f"🌐 Language: {result['language'].upper()}",
                        title="🎉 Word Export Complete",
                        border_style="green"
                    )
                )
            else:
                logger.error(f"Word export failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Word processing error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}