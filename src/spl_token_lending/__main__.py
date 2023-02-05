"""Package starts uvicorn process with app from `api` package."""

import uvicorn

from spl_token_lending.api.main import app

uvicorn.run(app, host="0.0.0.0")
