"""令牌验证依赖"""
from fastapi import Header, HTTPException
from .config import ACCESS_TOKEN


async def verify_token(x_docmind_token: str = Header(default="")):
    """仅上传和问答接口校验令牌，其余放行"""
    if ACCESS_TOKEN and x_docmind_token != ACCESS_TOKEN:
        raise HTTPException(403, "缺少有效令牌，联系 WX：19267826845 获取")
