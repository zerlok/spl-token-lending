import uvicorn

from spl_token_lending.api.main import app

uvicorn.run(app)
