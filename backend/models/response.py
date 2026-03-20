from pydantic import BaseModel
from typing import Optional


class AlternativeColor(BaseModel):
    color_name: str
    manufacturer: Optional[str] = None
    product_line: Optional[str] = None
    confidence: float


class IdentifyResponse(BaseModel):
    color_name: str
    manufacturer: Optional[str] = None
    product_line: Optional[str] = None
    condition: str  # new | good | worn | faded | damaged
    condition_confidence: float
    color_confidence: float
    final_confidence: float
    requires_manual_review: bool
    hex_preview: Optional[str] = None
    color_reasoning: str
    condition_reasoning: str
    alternatives: list[AlternativeColor] = []
    processing_time_ms: int


class ColorRecord(BaseModel):
    id: int
    manufacturer: str
    product_line: Optional[str] = None
    color_name: str
    hex_codes: list[str] = []
    swatch_url: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    db_color_count: int
    db_path: str
