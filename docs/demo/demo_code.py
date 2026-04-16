#!/usr/bin/env python3
"""
Oh My Coder 演示用示例代码
用于演示代码探索功能
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="电商 API", version="1.0.0")

# 数据模型
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True

class Item(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None

# 模拟数据库
users_db = []
items_db = []

# 用户路由
@app.get("/users", response_model=List[User])
async def get_users():
    """获取所有用户"""
    return users_db

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """获取单个用户"""
    user = next((u for u in users_db if u.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@app.post("/users", response_model=User)
async def create_user(user: User):
    """创建用户"""
    users_db.append(user)
    return user

# 商品路由
@app.get("/items", response_model=List[Item])
async def get_items():
    """获取所有商品"""
    return items_db

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """获取单个商品"""
    item = next((i for i in items_db if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")
    return item

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    """创建商品"""
    items_db.append(item)
    return item

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
