"""Company document repository API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)