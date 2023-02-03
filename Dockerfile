ARG ALPINE_VERSION=3.17
ARG PYTHON_VERSION=3.9
ARG POETRY_VERSION=1.3.1
ARG BASE_IMAGE=python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}

FROM ${BASE_IMAGE} AS poetry

ARG PYTHON_VERSION
ARG POETRY_VERSION

ENV PATH="/root/.local/bin:${PATH}" \
    PYTHONPATH="/poetry/.venv/lib/python${PYTHON_VERSION}/site-packages:${PYTHONPATH}" \
    POETRY_VERSION="${POETRY_VERSION}" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /poetry/

RUN apk add --no-cache build-base musl-dev libffi-dev curl gcc
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

ENTRYPOINT ["poetry"]


FROM poetry AS build

WORKDIR /srv/

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

COPY src/ src/


FROM build AS development

RUN poetry install --no-root

COPY tests/ tests/


FROM ${BASE_IMAGE} AS runtime

RUN mkdir -p /data/ \
    && adduser -DH app \
    && chown app:app /data/ /srv/
USER app

ARG PYTHON_VERSION

ENV PATH="/srv/.venv/bin/:${PATH}" \
    PYTHONPATH="/srv/.venv/lib/python${PYTHON_VERSION}/site-packages/:${PYTHONPATH}" \
    PYTHONOPTIMIZE=2
WORKDIR /srv/
VOLUME /data/
EXPOSE 8000
ENTRYPOINT ["uvicorn"]
CMD ["spl_token_lending.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]

COPY --from=build /srv/.venv/ /srv/.venv/
COPY --from=build /srv/src/ /srv/src/
