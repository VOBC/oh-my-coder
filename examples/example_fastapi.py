"""
FastAPI 项目示例

演示如何使用 Oh My Coder 开发 FastAPI 项目。

场景：为电商系统实现商品管理 API
"""

# ============================================================
# 第一步：探索项目结构
# ============================================================

# CLI 命令：
# omc explore .

# 预期输出：
# - 识别为 FastAPI 项目
# - 发现现有文件：main.py, models/, routers/
# - 技术栈：FastAPI, SQLAlchemy, Pydantic

# ============================================================
# 第二步：执行构建任务
# ============================================================

# CLI 命令：
# omc run "为电商系统实现商品管理 REST API，包括：
# 1. 商品 CRUD 接口
# 2. 分类管理接口
# 3. 库存管理接口
# 4. 图片上传接口
# 要求：使用 FastAPI，遵循 RESTful 规范" -w build

# ============================================================
# 预期生成的代码结构
# ============================================================

"""
project/
├── main.py                 # FastAPI 应用入口
├── models/
│   ├── __init__.py
│   ├── product.py          # 商品模型
│   ├── category.py         # 分类模型
│   └── inventory.py        # 库存模型
├── routers/
│   ├── __init__.py
│   ├── products.py         # 商品路由
│   ├── categories.py       # 分类路由
│   └── inventory.py        # 库存路由
├── schemas/
│   ├── __init__.py
│   ├── product.py          # 商品 Schema
│   ├── category.py         # 分类 Schema
│   └── inventory.py        # 库存 Schema
└── services/
    ├── __init__.py
    ├── product_service.py  # 商品服务
    └── image_service.py    # 图片服务
"""

# ============================================================
# 示例：生成的商品路由代码
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..schemas.product import ProductCreate, ProductUpdate, ProductResponse
from ..services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """获取商品列表，支持分页和筛选"""
    service = ProductService(db)
    return service.list(
        skip=skip,
        limit=limit,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """获取单个商品详情"""
    service = ProductService(db)
    product = service.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
):
    """创建新商品"""
    service = ProductService(db)
    return service.create(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
):
    """更新商品信息"""
    service = ProductService(db)
    updated = service.update(product_id, product)
    if not updated:
        raise HTTPException(status_code=404, detail="商品不存在")
    return updated


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """删除商品"""
    service = ProductService(db)
    success = service.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在")


# ============================================================
# 示例：生成的商品模型
# ============================================================

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class Product(Base):
    """商品模型"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    original_price = Column(Float)
    stock = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"))
    image_url = Column(String(255))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    category = relationship("Category", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False)


# ============================================================
# 示例：生成的 Pydantic Schema
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    """商品基础 Schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    """创建商品 Schema"""

    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """更新商品 Schema"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class ProductResponse(ProductBase):
    """商品响应 Schema"""

    id: int
    stock: int
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 第三步：验证和测试
# ============================================================

# CLI 命令：
# omc run "为商品 API 生成单元测试和集成测试" -w test

# 测试示例：
"""
import pytest
from fastapi.testclient import Client
from main import app

client = TestClient(app)


def test_list_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_product():
    response = client.post(
        "/products/",
        json={
            "name": "测试商品",
            "price": 99.99,
            "stock": 100
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试商品"
    assert data["price"] == 99.99


def test_get_product():
    # 先创建
    create_response = client.post(
        "/products/",
        json={"name": "测试商品", "price": 99.99}
    )
    product_id = create_response.json()["id"]
    
    # 再获取
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
"""

# ============================================================
# 第四步：代码审查
# ============================================================

# CLI 命令：
# omc run "审查商品管理模块的代码质量和安全性" -w review

# ============================================================
# 运行步骤总结
# ============================================================

"""
完整执行流程：

1. 探索项目
   omc explore .

2. 构建 API
   omc run "实现商品管理 REST API" -w build

3. 生成测试
   omc run "为商品 API 生成测试" -w test

4. 代码审查
   omc run "审查代码质量" -w review

5. 查看报告
   打开 reports/ 目录查看执行报告
"""
