import pytest
from maskinfly import mask_output

def test_mask_output_decorator_sync():
    @mask_output()
    def func():
        return {"password": "secret"}
    assert func() == {"password": "***"}

@pytest.mark.asyncio
async def test_mask_output_decorator_async():
    @mask_output(mask_char='X', mask_length=2)
    async def func():
        return {"token": "abc"}
    result = await func()
    assert result == {"token": "XX"}
