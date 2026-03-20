import time
import logging
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from backend.config import settings
from backend.core.vision import analyze_image
from backend.core.matcher import match_color
from backend.models.response import IdentifyResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp"
}


@router.post("/identify", response_model=IdentifyResponse)
async def identify_shingle(
    image: UploadFile = File(..., description="Photo of the roof shingles"),
    include_alternatives: bool = Form(default=True),
):
    start = time.monotonic()

    # Validate content type
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unsupported file type '{content_type}'. Use JPEG, PNG, or WEBP.",
                "code": "INVALID_FILE_TYPE",
            },
        )

    # Read and validate size
    image_bytes = await image.read()
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"File exceeds {settings.max_upload_size_mb}MB limit.",
                "code": "FILE_TOO_LARGE",
            },
        )

    if len(image_bytes) < 1024:
        raise HTTPException(
            status_code=400,
            detail={"error": "File is too small to be a valid image.", "code": "FILE_TOO_SMALL"},
        )

    logger.info("Analyzing image: %s, size=%d bytes", image.filename, len(image_bytes))

    try:
        vision_result = await analyze_image(image_bytes, content_type)
    except ValueError as e:
        if "ANTHROPIC_API_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": str(e),
                    "code": "API_KEY_NOT_CONFIGURED",
                },
            )
        raise HTTPException(
            status_code=503,
            detail={"error": f"Vision analysis failed: {e}", "code": "VISION_ERROR"},
        )
    except Exception as e:
        logger.exception("Unexpected error during vision analysis")
        raise HTTPException(
            status_code=503,
            detail={"error": "Vision service temporarily unavailable.", "code": "VISION_UNAVAILABLE"},
        )

    matched = await match_color(vision_result, include_alternatives=include_alternatives)
    processing_ms = int((time.monotonic() - start) * 1000)

    return IdentifyResponse(
        **matched,
        processing_time_ms=processing_ms,
    )
