from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from typing import Dict, Any
import uvicorn
from pathlib import Path
from word_processor import WordProcessor
from pdf_processor import PDFProcessor, ProcessingMode

app = FastAPI(
    title="PDF Processing API",
    description="Multi-mode PDF processing with Fast, Rich, and Pro modes",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processor (which now uses the parsers)
processor = PDFProcessor()

# Ensure outputs directory exists
Path("outputs").mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "message": "PDF Processing API",
        "modes": {
            "fast": "pdfplumber - Fast but less accurate",
            "rich": "markitdown - Accurate but slower", 
            "pro": "agentic-doc - Most accurate for images/scanned PDFs"
        },
        "endpoints": {
            "fast_mode": "/process/fast",
            "rich_mode": "/process/rich",
            "pro_mode": "/process/pro",
            "download": "/download/{filename}",
            "files": "/files"
        }
    }

@app.post("/process/fast")
async def process_fast_mode(
    file: UploadFile = File(...),
    auto_detect: bool = True
):
    """Process PDF in Fast mode using pdfplumber"""
    return await process_pdf_internal(file, ProcessingMode.FAST, auto_detect)

@app.post("/process/rich") 
async def process_rich_mode(
    file: UploadFile = File(...),
    auto_detect: bool = True
):
    """Process PDF in Rich mode using markitdown"""
    return await process_pdf_internal(file, ProcessingMode.RICH, auto_detect)

@app.post("/process/pro")
async def process_pro_mode(
    file: UploadFile = File(...),
    auto_detect: bool = True
):
    """Process PDF in Pro mode using agentic-doc"""
    return await process_pdf_internal(file, ProcessingMode.PRO, auto_detect)

async def process_pdf_internal(
    file: UploadFile, 
    mode: ProcessingMode,
    auto_detect: bool
) -> Dict[str, Any]:
    """Internal PDF processing function - calls the processor"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process the PDF using our processor
        result = processor.process_pdf(temp_path, mode, auto_detect)
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        return result
        
    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated markdown files"""
    file_path = Path("outputs") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='text/markdown'
    )

@app.get("/files")
async def list_files():
    """List all generated markdown files"""
    output_dir = Path("outputs")
    files = []
    
    for file_path in output_dir.glob("*.md"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "created": file_path.stat().st_ctime
        })
    
    return {"files": files}
@app.post("/export/word")
async def export_to_word(
    file: UploadFile = File(...),
    mode: str = "fast",
    language: str = "auto"
):
    """Process PDF and export directly to Word format"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process PDF first
        processing_mode = ProcessingMode(mode)
        result = processor.process_pdf(temp_path, processing_mode, auto_detect=True)
        
        if not result.get("success"):
            os.unlink(temp_path)
            return result
        
        # Export to Word
        word_result = processor.save_as_word(
            result.get("markdown_content", ""),
            language=language
        )
        
        # Clean up
        os.unlink(temp_path)
        
        return {
            **result,
            "word_export": word_result
        }
        
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Word export failed: {str(e)}")

@app.post("/convert/to-word")
async def convert_to_word(
    markdown_content: str = Form(...),
    language: str = Form("auto")
):
    """Convert existing markdown content to Word format"""
    try:
        result = processor.save_as_word(markdown_content, language=language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@app.get("/download/word/{filename}")
async def download_word_file(filename: str):
    """Download generated Word files"""
    file_path = Path("outputs") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Word file not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PDF Processor API"}

# if __name__ == "__main__":
#     uvicorn.run(
#         "server:app",
#         host="0.0.0.0", 
#         port=8000,
#         reload=True,
#         log_level="info"
#     )