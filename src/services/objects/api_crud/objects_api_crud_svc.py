"""
Модуль содержит классы, описывающие входные данные для команд CRUD для объектов
и класс сервиса ``objects_api_crud_svc``\.
"""
import json
import sys
from uuid import UUID
from typing import Any, List
from pydantic import Field, validator

from fastapi import APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(".")

from src.common import api_crud_svc as svc
from src.services.objects.api_crud.objects_api_crud_settings import ObjectsAPICRUDSettings

origins = [
    "http://localhost:5173",
]

class ObjectCreateAttributes(svc.NodeAttributes):
    pass

class ObjectCreate(svc.NodeCreate):
    attributes: ObjectCreateAttributes = Field(title="Атрибуты объекта")

    # validate_id = validator('parentId', 'dataStorageId', 'connectorId', allow_reuse=True)(svc.valid_uuid)

class ObjectRead(svc.NodeRead):
    pass

class OneObjectInReadResult(svc.OneNodeInReadResult):
    pass

class ObjectReadResult(svc.NodeReadResult):
    data: List[OneObjectInReadResult] = Field(title="Список объектов.")
    pass

class ObjectUpdate(svc.NodeUpdate):
    pass

class ObjectsAPICRUD(svc.APICRUDSvc):
    """Сервис работы с объектами в иерархии.

    Подписывается на очередь ``objects_api_crud`` обменника ``objects_api_crud``\,
    в которую публикует сообщения сервис ``objects_api_crud`` (все имена
    указываются в переменных окружения).

    Формат ожидаемых сообщений

    """

    _outgoing_commands = {
        "create": "objects.create",
        "read": "objects.read",
        "update": "objects.update",
        "delete": "objects.delete"
    }

    def __init__(self, settings: ObjectsAPICRUDSettings, *args, **kwargs):
        super().__init__(settings, *args, **kwargs)

    async def create(self, payload: ObjectCreate) -> dict:
        return await super().create(payload=payload)

    async def read(self, payload: ObjectRead) -> dict:
        return await super().read(payload=payload)

    async def update(self, payload: ObjectUpdate) -> dict:
        return await super().update(payload=payload)

settings = ObjectsAPICRUDSettings()

app = ObjectsAPICRUD(settings=settings, title="`ObjectsAPICRUD` service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

@router.post("/", response_model=svc.NodeCreateResult, status_code=201)
async def create(payload: ObjectCreate):
    return await app.create(payload)

@router.get("/", response_model=svc.NodeReadResult | None, status_code=200)
async def read(q: str | None = None, payload: ObjectRead | None = None):
    return await app.api_get_read(ObjectRead, q, payload)

@router.put("/", status_code=202)
async def update(payload: ObjectUpdate):
    await app.update(payload)

@router.delete("/", status_code=202)
async def delete(payload: ObjectRead):
    await app.delete(payload)

app.include_router(router, prefix=f"{settings.api_version}/objects", tags=["objects"])
