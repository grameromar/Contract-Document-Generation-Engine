"""HTTP routes for the template API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from latexgen.core.service import TemplateService

from .dependencies import get_service
from .schemas import FieldSchema, ParseRequest, ParseResponse

router = APIRouter()


@router.post("/parse", response_model=ParseResponse)
def parse( request: ParseRequest, service: TemplateService = Depends(get_service),
) -> ParseResponse:
    """Discover the dynamic fields declared in a template.

    The frontend calls this first, to build the input form from the returned
    field metadata before any values are entered.
    """
    fields = service.parse(request.template)
    return ParseResponse(
        fields=[FieldSchema.model_validate(field) for field in fields]
    )