"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from fastapi import FastAPI

from config import PROFILING_MODE, PYROSCOPE_SERVER_URL, RUN_MODE, SERVER_NAME


def setup_pyroscope():
    if PROFILING_MODE is True and PYROSCOPE_SERVER_URL is not None:
        import pyroscope

        pyroscope.configure(
            application_name=SERVER_NAME,
            server_address=PYROSCOPE_SERVER_URL,
            sample_rate=100,  # default is 100
            detect_subprocesses=True,  # detect subprocesses started by the main process; default is False
            oncpu=False,  # report cpu time only; default is True
            gil_only=False,  # only include traces for threads that are holding on to the Global Interpreter Lock; default is True
            enable_logging=False,  # does enable logging facility; default is False
            tags={"RUN_MODE": RUN_MODE},
        )


def setup_otel(app: FastAPI | None = None) -> None:
    if PROFILING_MODE is True:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        resource = Resource(attributes={"service.name": SERVER_NAME})
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider=tracer_provider)

        # fastapi instrumentation
        if app is not None:
            from opentelemetry.instrumentation import fastapi as otel_fastapi

            instrumentor = otel_fastapi.FastAPIInstrumentor()
            instrumentor.instrument_app(
                app=app,
                tracer_provider=tracer_provider,
            )

        # aiohttp instrumentation
        from opentelemetry.instrumentation import asyncio as otel_asyncio

        instrumentor = otel_asyncio.AsyncioInstrumentor()
        instrumentor.instrument(tracer_provider=tracer_provider)

        # asyncpg instrumentation
        from opentelemetry.instrumentation import asyncpg as otel_asyncpg

        instrumentor = otel_asyncpg.AsyncPGInstrumentor()
        instrumentor.instrument(tracer_provider=tracer_provider)

        # httpx instrumentation
        from opentelemetry.instrumentation import httpx as otel_httpx

        instrumentor = otel_httpx.HTTPXClientInstrumentor()
        instrumentor.instrument(tracer_provider=tracer_provider)

        # psycopg instrumentation
        from opentelemetry.instrumentation import psycopg as otel_psycopg

        instrumentor = otel_psycopg.PsycopgInstrumentor()
        instrumentor.instrument(tracer_provider=tracer_provider)

        # SQLAlchemy instrumentation
        from opentelemetry.instrumentation import sqlalchemy as otel_sqlalchemy

        instrumentor = otel_sqlalchemy.SQLAlchemyInstrumentor()
        instrumentor.instrument(
            tracer_provider=tracer_provider, enable_commenter=True, commenter_options={}
        )

        # Exporter setting
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from pyroscope.otel import PyroscopeSpanProcessor

        otlp_exporter = OTLPSpanExporter()
        batch_span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor=batch_span_processor)

        pyroscope_span_processor = PyroscopeSpanProcessor()
        tracer_provider.add_span_processor(span_processor=pyroscope_span_processor)
