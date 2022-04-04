from typing import Optional
from loguru import logger

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from webserver.utils import _get_validation_cycles, _get_elections, _get_complaints


# FastAPI app
description = """TON Validation Service"""

app = FastAPI(
    title="TON Validation Service",
    description=description
)

@app.exception_handler(HTTPException)
async def httpexception_handler(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse({"detail": "unknown"}, status_code=503)

@app.get('/getValidationCycles')
def get_validation_cycles(cycle_id: Optional[int]=None, 
                          wallet_address: Optional[str]=None,
                          adnl_address: Optional[str]=None,
                          limit: int=1,
                          return_participants: bool=True):
    return _get_validation_cycles(cycle_id, wallet_address, adnl_address, limit, return_participants)

@app.get('/getElections')
def get_elections(election_id: Optional[int]=None, 
                  wallet_address: Optional[str]=None,
                  adnl_address: Optional[str]=None, 
                  limit: int=1, 
                  return_participants: bool=True):
    return _get_elections(election_id, wallet_address, adnl_address, limit, return_participants)

@app.get('/getComplaints')
def get_complaints(wallet_address: Optional[str]=None, 
                   adnl_address: Optional[str]=None, 
                   election_id: Optional[int]=None,
                   limit: int=1):
    return _get_complaints(wallet_address, adnl_address, election_id, limit)


