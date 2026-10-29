from fastapi import APIRouter, HTTPException
from global_data import global_data

router = APIRouter(prefix="/api/v1/global-data", tags=["global-data"])


@router.get("")
def get_global_data() -> dict:
    return global_data.snapshot().as_dict()


@router.get("/cases/{case_id}")
def get_global_case(case_id: str) -> dict:
    case = global_data.case(case_id)
    if case is None:
        raise HTTPException(404, "Global diagnostic case not found")
    return case
