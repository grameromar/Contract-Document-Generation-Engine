"""HTTP routes for the template API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from latexgen.core.service import TemplateService

from .dependencies import get_service
from .schemas import FieldSchema, GenerateRequest, ParseRequest, ParseResponse

router = APIRouter()

# Name suggested to the browser for the downloaded PDF.
_PDF_FILENAME = "document.pdf"


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


@router.post(
    "/generate",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def generate(
    request: GenerateRequest,
    service: TemplateService = Depends(get_service),
) -> Response:
    """Render a template with the user's values and return the compiled PDF.

    Declared with ``def`` rather than ``async def`` on purpose: compiling
    blocks for up to the configured timeout, and FastAPI runs plain functions
    in a worker thread, so a slow compilation does not stall other requests.
    Domain errors are translated to HTTP responses by the handlers in
    :mod:`latexgen.web.errors`.

    Args:
        request: The template text and the values keyed by field name.
        service: The shared template service.

    Returns:
        The PDF bytes as ``application/pdf``, marked as a download.
    """
    pdf = service.generate(request.template, request.values)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_PDF_FILENAME}"'},
    )
