"""
Middleware de rate limiting.

TODO: implémenter avec redis-py (sliding window algorithm).
Limites : 60 req/min par IP, 500 req/h par compte.
"""
from __future__ import annotations
# TODO: from fastapi import Request, HTTPException
# TODO: import redis
