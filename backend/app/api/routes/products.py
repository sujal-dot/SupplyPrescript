"""Product API router."""

import logging
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.product import Product
from app.schemas.product import ProductListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=ProductListResponse, summary="List products with pagination and search")
def get_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (1 to 100)"),
    search: Optional[str] = Query(None, description="Search product name or ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    """
    Retrieve products from PostgreSQL with pagination, search, and category filtering.
    """
    try:
        query = db.query(Product)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Product.product_name.ilike(term) | Product.product_id.ilike(term)
            )
        if category:
            query = query.filter(func.lower(Product.category) == category.strip().lower())

        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size
        products = query.order_by(Product.id.asc()).offset(offset).limit(page_size).all()

        return {
            "data": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as exc:
        logger.error(f"Error fetching products: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching products",
        )
