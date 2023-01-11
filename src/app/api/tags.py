from fastapi import APIRouter, Depends
import app.main as main
import app.models.ModelNode as ModelNode
import app.models.Tag as Tag

router = APIRouter()

@router.post("/", response_model=ModelNode.PrsResponseCreate, status_code=201)
async def create(payload : Tag.PrsTagCreate):
    tag = await main.app.create_tag(payload)
    id_ = tag.get_id()
    return {"id": id_}

@router.get("/{id_}/", response_model=Tag.PrsTagCreate)
async def read_tag(id_: str):
    return main.app.read_tag(id_).data
