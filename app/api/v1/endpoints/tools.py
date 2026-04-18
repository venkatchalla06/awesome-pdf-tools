from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.schemas.tool import ToolInfo

router = APIRouter()

@router.get("/", response_model=List[ToolInfo])
async def get_available_tools():
    """Get list of available PDF tools"""
    tools = [
        ToolInfo(
            id="merge",
            name="Merge PDF",
            description="Combine multiple PDF files into one",
            category="organize",
            icon="📄",
            max_files=20
        ),
        ToolInfo(
            id="split",
            name="Split PDF",
            description="Split PDF into individual pages",
            category="organize", 
            icon="✂️",
            max_files=1
        ),
        ToolInfo(
            id="compress",
            name="Compress PDF",
            description="Reduce PDF file size",
            category="optimize",
            icon="📦",
            max_files=1
        ),
        ToolInfo(
            id="pdf_to_word",
            name="PDF to Word",
            description="Convert PDF to editable Word document",
            category="convert",
            icon="📝",
            max_files=1
        ),
        ToolInfo(
            id="pdf_to_ppt",
            name="PDF to PowerPoint",
            description="Convert PDF pages to PowerPoint slides",
            category="convert",
            icon="📊",
            max_files=1
        ),
        ToolInfo(
            id="ocr",
            name="OCR PDF",
            description="Extract text from scanned PDFs",
            category="convert",
            icon="🔍",
            max_files=1
        ),
        ToolInfo(
            id="watermark",
            name="Watermark PDF",
            description="Add text watermark to PDF",
            category="edit",
            icon="💧",
            max_files=1
        ),
        ToolInfo(
            id="page_number",
            name="Add Page Numbers",
            description="Insert page numbers into PDF",
            category="edit",
            icon="🔢",
            max_files=1
        )
    ]
    
    return tools

@router.get("/{tool_id}/parameters")
async def get_tool_parameters(tool_id: str):
    """Get required parameters for a specific tool"""
    parameters = {
        "merge": {
            "description": "Merge multiple PDF files",
            "parameters": []
        },
        "split": {
            "description": "Split PDF into pages",
            "parameters": [
                {
                    "name": "pages",
                    "type": "array",
                    "description": "Specific pages to extract (leave empty for all pages)",
                    "required": False
                }
            ]
        },
        "compress": {
            "description": "Compress PDF file",
            "parameters": [
                {
                    "name": "quality",
                    "type": "string",
                    "description": "Compression quality",
                    "options": ["low", "medium", "high"],
                    "default": "medium",
                    "required": False
                }
            ]
        },
        "pdf_to_ppt": {
            "description": "Convert PDF pages to PowerPoint slides",
            "parameters": [
                {
                    "name": "dpi",
                    "type": "integer",
                    "description": "Image resolution for slide rendering (default 150)",
                    "required": False,
                    "default": 150
                }
            ]
        },
        "watermark": {
            "description": "Add watermark to PDF",
            "parameters": [
                {
                    "name": "text",
                    "type": "string",
                    "description": "Watermark text",
                    "required": True
                }
            ]
        }
    }
    
    if tool_id not in parameters:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return parameters[tool_id]