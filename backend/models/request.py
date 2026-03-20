from pydantic import BaseModel


class IdentifyRequest(BaseModel):
    include_alternatives: bool = True
