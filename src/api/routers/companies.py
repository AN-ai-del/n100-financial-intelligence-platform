"""Company-data API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)