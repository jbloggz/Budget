#
# MIT License
#
# Copyright (c) 2023 Josef Barnes
#
# auth.py: This file contains authentication code for the budget App
#

# System imports
import os
import json
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from calendar import timegm
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# Local imports
from model import Token
from database import Database


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='oauth2/token')
with open(os.environ.get('SECRETS_PATH', 'secrets.json')) as fp:
    secrets = json.load(fp)


def verify_user(username: str, password: str) -> bool:
    '''
    Verify a user

    Args:
        username: The name of the user
        password: The password of the user

    Returns:
        True if the user is valid, False if not
    '''
    if username not in secrets['users']:
        return False
    return pwd_context.verify(password, secrets['users'][username])


def hash_password(password: str) -> str:
    '''
    Hash a password for storage in a database

    Args:
        password: The plain text password

    Returns:
        The hashed password
    '''
    return pwd_context.hash(password)


def create_token(user: str) -> Token:
    '''
    Create a JSON web token

    Args:
        user: The user name
        expires_delta: The TTL

    Returns:
        The encoded token
    '''
    now = datetime.utcnow()
    access_expire = now + timedelta(seconds=secrets['access_token_ttl'])
    refresh_expire = now + timedelta(seconds=secrets['refresh_token_ttl'])
    token = Token(
        access_token=jwt.encode({'sub': user, 'exp': access_expire, 'iat': now}, secrets['access_token_key'], algorithm=secrets['algorithm']),
        refresh_token=jwt.encode({'sub': user, 'exp': refresh_expire, 'iat': now}, secrets['refresh_token_key'], algorithm=secrets['algorithm']),
        token_type='bearer'
    )
    with Database() as db:
        db.add_token(token.refresh_token, timegm(refresh_expire.utctimetuple()))

    return token


def validate_token(key: str, token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    try:
        payload = jwt.decode(token, secrets[key], algorithms=secrets['algorithm'])
        username: str = payload.get('sub')
        if username not in secrets['users']:
            raise ValueError('Invalid username')
        return username
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid/expired access token',
            headers={'WWW-Authenticate': 'Bearer'},
        )


def validate_access_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    return validate_token('access_token_key', token)


def validate_refresh_token(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    with Database() as db:
        if not db.has_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid/expired refresh token',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        db.clear_token(token)
        return validate_token('refresh_token_key', token)
