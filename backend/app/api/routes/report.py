"""POST /api/report - turn an analysis payload into a downloadable PDF.

The client sends back the analysis it already has rather than re-uploading the
resume. That keeps this endpoint stateless, avoids a second parse, and means no
file ever touches the disk here.
"""

import logging

from fastapi import APIRouter, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool

from app.schemas.analysis import AnalysisResponse
from app.services.report_builder import build_report, suggested_filename

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


@router.post(
    "/report",
    summary="Render an analysis as a PDF",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "The report as a PDF file.",
        }
    },
)
async def create_report(analysis: AnalysisResponse) -> Response:
    """Take an analysis payload, return the PDF bytes of its report.

    Validated against the same schema /api/analyze returns, so a hand-edited or
    truncated body is rejected with a 422 before reportlab ever sees it.
    """
    # mode="json" so datetimes arrive as ISO strings: report_builder takes plain
    # data and must not depend on pydantic types.
    payload = analysis.model_dump(mode="json")

    try:
        # reportlab is CPU-bound; keep the event loop free the same way
        # /api/analyze does.
        pdf_bytes = await run_in_threadpool(build_report, payload)
    except Exception as exc:
        logger.exception("Report generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate the PDF report.",
        ) from exc

    filename = suggested_filename(payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # The browser can only read a header it is told about; without this
            # the frontend cannot recover the filename from a cross-origin call.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
