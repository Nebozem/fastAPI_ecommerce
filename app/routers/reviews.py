from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.schemas import ReviewResponse as ReviewSchema, ReviewCreate
from app.db_depends import get_db
from app.auth import get_current_buyer, get_current_user

router = APIRouter(prefix="/reviews",
                   tags=["reviews"])

async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.rating = avg_rating

@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных отзывов.
    """
    result = await db.execute(select(ReviewModel).where(ReviewModel.is_active == True))
    reviews = result.scalars().all()
    return reviews

@router.get("/products/{product_id}", response_model=list[ReviewSchema])
async def get_reviews_by_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает все активые отзывы конкретного товара.
    """
    result = await db.scalars(select(ProductModel).where(ProductModel.is_active == True, ProductModel.id == product_id))
    products = result.first()
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    result_2 = await db.execute(select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True))
    reviews = result_2.scalars().all()
    return reviews

@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def post_review(review: ReviewCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_buyer)):
    """
    Создаёт новый отзыв, привязанный к текущему покупателю (только для 'buyer').
    """
    stmt = await db.scalars(select(ProductModel).where(ProductModel.is_active == True, ProductModel.id == review.product_id))
    result = stmt.first()
    if not result:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    if review.grade > 5 or review.grade < 1:
        raise HTTPException(status_code=422, detail="Grade must be between 1 and 5")

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.flush()
    await update_product_rating(db, review.product_id)
    await db.commit()
    await db.refresh(db_review)

    return db_review

@router.delete("/reviews/{review_id}")
async def delete_review(review_id: int, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    """
    Выполняет мягкое удаление отзыва, если он принадлежит текущему покупателю.
    """
    stmt = select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    result = await db.scalars(stmt)
    db_review = result.first()
    if not db_review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if db_review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    db_review.is_active = False

    await update_product_rating(db, db_review.product_id)
    await db.commit()

    return {"message": "Review deleted"}