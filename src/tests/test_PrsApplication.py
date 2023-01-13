import asyncio
import pytest
from app.svc.Services import Services as svc

@pytest.mark.asyncio
async def test_reg_tag(create_vm_default_datastorage, create_tag):
    vm = await create_vm_default_datastorage
    assert svc.data_storages, "There are no datastorages in cache."
    tag = await create_tag
    assert svc.tags, "There are no tags in cache."

    assert svc.tags[tag.id]['app']['dataStorageId'] == vm.id
    assert svc.tags[tag.id]['data_storage']['metric'] == f"t_{tag.data.attributes.cn.replace('-', '_')}"
