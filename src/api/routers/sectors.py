"""Sector analytics API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/sectors",
    tags=["Sectors"],
)