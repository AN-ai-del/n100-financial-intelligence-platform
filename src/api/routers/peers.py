"""Peer comparison API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/peers",
    tags=["Peers"],
)