from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel


class PostSchema(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class Base(DeclarativeBase):
    pass


class PostModel(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    author_id = Column(Integer, index=True)
    is_active = Column(Boolean, default=True)
router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)


@router.put("/{post_id}")
async def post_delete(post_id: int, db: Session = Depends(get_db)):
    stmt = select(PostModel).where(PostModel.id == post_id, PostModel.is_active == True)
    post = db.scalars(stmt).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    db.execute(update(PostModel).where(PostModel.id == post_id).values(is_active=False))
    db.commit()

    return "Post marked as inactive"