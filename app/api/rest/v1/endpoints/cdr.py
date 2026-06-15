from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import CDRCreate, CDRResponse
from app.services import create_cdr, get_cdr, list_cdrs

router = APIRouter(
    prefix="/cdr",
    tags=["CDR"],
    responses={
        404: {"description": "CDR record not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=CDRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Insert a CDR record",
    description="Write a call detail record from Asterisk.",
    response_description="The created CDR record",
)
async def insert_cdr(
    request: CDRCreate = Body(
        ...,
        examples=[
            {
                "uniqueid": "HASH-20260615-143022-42",
                "call_id": "HASH-20260615-143022-42",
                "src": "256700123456",
                "dst": "8446",
                "channel": "",
                "context": "ivr",
                "exten": "8446",
                "calldate": "2026-06-15T14:30:22",
                "duration": 120,
                "billsec": 115,
                "disposition": "ANSWERED",
                "cause": "16",
                "recording_file": None,
            }
        ],
    ),
    db: Session = Depends(get_db),
):
    """
    Insert a call detail record written by Asterisk on call completion:

    - **uniqueid**: Set to the same HASH call_id value by the AGI script
    - **call_id**: Internal call_id linking to the pipeline call record
    - **src**: Source (caller) number
    - **dst**: Destination (dialled) number
    - **channel**: Asterisk channel string
    - **context**: Asterisk dialplan context
    - **exten**: Dialled extension
    - **calldate**: Date and time the call started
    - **duration**: Total call duration in seconds
    - **billsec**: Billable seconds (after answer)
    - **disposition**: Call outcome (ANSWERED, NO ANSWER, BUSY, FAILED)
    - **cause**: Hangup cause code
    - **recording_file**: Path to the call recording file (if any)
    """
    return create_cdr(db, request)


@router.get(
    "",
    response_model=list[CDRResponse],
    status_code=status.HTTP_200_OK,
    summary="List CDR records",
    description="Return paginated call detail records ordered by most recent first.",
)
async def list_cdr_records(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return."),
    offset: int = Query(0, ge=0, description="Records to skip for pagination."),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of Asterisk call detail records.

    - **limit**: Maximum number of records to return (1–1 000)
    - **offset**: Number of records to skip
    """
    return list_cdrs(db, limit=limit, offset=offset)


@router.get(
    "/{uniqueid}",
    response_model=CDRResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single CDR record",
    description="Return the CDR record for a given Asterisk uniqueid.",
)
async def get_cdr_record(uniqueid: str, db: Session = Depends(get_db)):
    """
    Retrieve a single CDR by its Asterisk uniqueid.

    - **uniqueid**: The Asterisk globally unique call identifier
    """
    row = get_cdr(db, uniqueid)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CDR {uniqueid} not found")
    return row
