"""Module defines FastAPI application for running spl-token-lending backend service."""

from fastapi import FastAPI, status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from spl_token_lending.api.dependencies import get_container
from spl_token_lending.api.handlers import router
from spl_token_lending.db.migration import run_migration_upgrade

app = FastAPI()
app.include_router(router)


@app.exception_handler(ValueError)
async def handle_value_error(request: Request, err: ValueError) -> Response:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "request has invalid value", "detail": str(err)},
    )


@app.on_event("startup")
async def init_container() -> None:
    run_migration_upgrade()

    await get_container().init_resources()  # type: ignore[misc]


@app.on_event("shutdown")
async def shutdown_container() -> None:
    await get_container().shutdown_resources()  # type: ignore[misc]
