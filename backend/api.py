#
# MIT License
#
# Copyright (c) 2023 Josef Barnes
#
# api.py: This file implements a RESTFul API for the budget App
#

# System imports
from typing import List, Annotated
from fastapi import FastAPI, Query, Depends, HTTPException, status

# Local imports
from database import Database
from model import Transaction, Allocation, Token, OAuth2RequestForm
from auth import create_token, verify_user, validate_access_token, validate_refresh_token


app = FastAPI()
db = Database()


@app.post('/transaction/', status_code=201, response_model=Transaction)
def add_transaction(user: Annotated[str, Depends(validate_access_token)], txn: Transaction) -> Transaction:
    with db:
        db.add_transaction(txn)
    return txn


@app.get('/transaction/', response_model=List[Transaction], dependencies=[Depends(validate_access_token)])
def get_transactions(query: str) -> List[Transaction]:
    with db:
        return db.get_transaction_list(query)


@app.get('/allocation/', response_model=List[Allocation], dependencies=[Depends(validate_access_token)])
def get_allocations(query: str) -> List[Allocation]:
    with db:
        return db.get_allocation_list(query)


@app.put('/allocation/', dependencies=[Depends(validate_access_token)])
def update_allocation(alloc: Allocation) -> None:
    with db:
        db.update_allocation(alloc)


@app.get('/allocation/split/', dependencies=[Depends(validate_access_token)])
def split_allocation(id: int, amount: int) -> Allocation:
    with db:
        return db.split_allocation(id, amount)


@app.get('/allocation/merge/', dependencies=[Depends(validate_access_token)])
def merge_allocation(ids: Annotated[List[int], Query()]) -> Allocation:
    with db:
        return db.merge_allocations(ids)


@app.post('/oauth2/token/', response_model=Token)
def auth(form_data: Annotated[OAuth2RequestForm, Depends()]) -> Token:
    if form_data.grant_type == 'refresh_token':
        username = validate_refresh_token(form_data.refresh_token)
        return create_token(username)
    else:
        if not verify_user(form_data.username, form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect username or password',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        return create_token(form_data.username)
