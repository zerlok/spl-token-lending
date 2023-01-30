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

Solana RPC api for creating transactions: [https://docs.solana.com/developing/clients/jsonrpc-api](https://docs.solana.com/developing/clients/jsonrpc-api)

Solana SPL token docs for token transfer instruction:

- [https://spl.solana.com/token](https://spl.solana.com/token)
- [https://www.npmjs.com/package/@solana/spl-token](https://www.npmjs.com/package/@solana/spl-token)
- [https://dev.to/0xbolt/how-to-send-solana-transaction-using-python-1dii](https://dev.to/0xbolt/how-to-send-solana-transaction-using-python-1dii)

Solana transaction explorer: [https://explorer.solana.com/](https://explorer.solana.com/)

