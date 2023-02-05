# Centralized SPL token lending

**Goal**

Build a backend API for issuing SPL tokens to users and tracking the outstanding debt

**Requirements**

1. User can request a token amount to be lent over by the server and receive the requested amount on his solana wallet
2. User can view his outstanding debt (wallet address, amount, token address)
3. User can view all outstanding debts (wallet address, amount, token address)

**Tech stack**

- Postgres
- Docker
- Python/Nodejs/JVM-based languages

**Bonus points:**

- Verify that the user requesting tokens is the owner of the keypair
- Deploying and providing API scripts that test the flow and state

**Hints**

- use devnet cluster for building and showcase
- create test token and support only that specific token to reduce scope

**Terminology**

SPL - solana program libarary - official token specification of Solana chain

Lending - server issues tokens and keeps tracking of the amounts

**Useful references**

Solana RPC api for creating
transactions: [https://docs.solana.com/developing/clients/jsonrpc-api](https://docs.solana.com/developing/clients/jsonrpc-api)

Solana SPL token docs for token transfer instruction:

- [https://spl.solana.com/token](https://spl.solana.com/token)
- [https://www.npmjs.com/package/@solana/spl-token](https://www.npmjs.com/package/@solana/spl-token)
- [https://dev.to/0xbolt/how-to-send-solana-transaction-using-python-1dii](https://dev.to/0xbolt/how-to-send-solana-transaction-using-python-1dii)

Solana transaction explorer: [https://explorer.solana.com/](https://explorer.solana.com/)

## Solution

A backend API service was written in Python language. A backend API stores users' loans in postgres database and allows
to initialize the loan by provided public key for a specified amount, then user has to approve the loan by signing
received loan id with hist keypair and posting the signature back to API.

Also, users may get a list of all loans the service provided and filter the necessary information from API.

A detailed openapi styled documentation is available on http://localhost:8000/docs url (to visit it, you have to start
the API service on your local machine).

### Dependencies

Project:

* docker + docker-compose
* python
    * poetry -- manages python project dependencies
    * FastAPI + uvicorn -- API is build on it and server runs with uvicorn
    * pydantic -- provides serialization for API and token configuration for the service
    * solana -- provides a simplified integration with solana / SPL json-rpc API
    * gino + alembic -- performs postgres SQL query execution and DB migrations
    * dependency-injector -- performs application assembling and easy app configuration in tests
    * mypy + pytest -- code type checking & integration tests were implemented with these tools
* postgres

### Known issues

* sometimes solana devnet returns 429 (Too Many Requests) or even Internal Server Error, so client has to wait awhile
  and retry the operation
    * usually this happens when server initializes a new wallet with airdrop and creates a new token and mints some
      amount of it
* on first token lending service will initialize wallet and token account, so request duration may take up to 2 minutes
* submit loan request may take up to 1 minute, because service waits for token transfer transaction to be finalized

### How to start

Start your own centralized API for token lending on your local machine using docker-compose

```bash
# build spl-token-lending-api service docker image
docker-compose build

# run spl token lending project with postgres and spl-token-lending-api service
docker-compose up -d
```

Use CLI script for initializing your custom wallet and lend some tokens

```bash
python scripts/token-lending-cli.py lend

user keypair: ******
user pubkey: HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf
loan amount: 133
loan initialized: {'id': '******', 'status': 'PENDING', 'wallet': 'HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf', 'amount': 133}
submit [y/n]: y
confirming the loan with keypair signature (this can take a while) ...
loan submitted: {'id': '******', 'status': 'ACTIVE', 'wallet': 'HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf', 'amount': 133}
```

List your loans

```bash
python scripts/token-lending-cli.py list

user keypair: ******
user pubkey: HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf
loans: {'info': {'offset': 0, 'limit': 1000, 'total': 1}, 'items': [{'id': '******', 'status': 'ACTIVE', 'wallet': 'HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf', 'amount': 133}]}
```

You may find your lent tokens in solana
explorer: https://explorer.solana.com/address/HXJ9DuvFSqfrUPxoytns3zybYjMHjzrvsGMtc45mUujf/tokens?cluster=devnet

### Development

Install poetry, python, docker, docker-compose.

Setup project for development (all following commands assumed to be run from project root dir).

```bash
poetry install
```

Create dev files: `.env` and `docker-compose.override.yml`

```
# .env content example

TOKEN_REPOSITORY_CONFIG_PATH=tests/secrets/token-repository-config.json
SOLANA_ENDPOINT=https://api.devnet.solana.com
POSTGRES_DSN=postgresql://spl-token-lending:secret@localhost:5432/dev
POSTGRES_PASSWORD=secret
LOGGING_LEVEL=debug
```

```
# docker-compose.override.yml content example

version: '3.3'

services:
  # map postgres ports, so you can connect to DB in tests / local service run
  postgres:
    ports:
      - "5432:5432"
```

Run MyPy check

```bash
poetry run mypy
```

Run tests

```bash
export CONFIG_ENV_FILE=.env

# run all tests, except slow (for quick checks, no coverage reports + enable debugger breakpoints and stop on first test failure)
poetry run pytest --no-cov -x -m "not slow"

# run all tests, this won't be fast
poetry run pytest 
``` 

### To Do

1. Simplify lending process:
    1. Make single endpoint for accepting the loan request from a user
    2. Create a loan in DB and start a token transfer transaction with 2 signatures: token lending source (service) &
       token destination (user)
    3. Service should start to listen for user to sign / confirm the transaction (try to use websocket API for that)
    4. After user signs the transaction with his own keypair - solana finishes transaction and service updates the
       status of the loan to active
2. Reduce loan amount when user returns some tokens to source account and close loans
    1. Listen to source account token transfers and analyse incoming tokens and reduce loan amount for appropriate
       wallet
    2. Close the loan when user returns full amount
3. Store source token account configuration in database, not in a config file.
    1. Add endpoints to initialize the wallet / tokens and store info in DB.
    2. Construct token lending entity in the code from database when loan initializes
4. (Best solution for cases 1, 2, 3) refactor API, so it just subscribes and listens for specified token transfers and
   calculates loans
5. Increase test coverage, test code for solana integration failures and make tests more reproducible (use fixed values
   for public keys and keypairs).

