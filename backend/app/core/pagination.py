from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class PageParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


Pagination = Annotated[PageParams, Depends()]


def paginate(db: Session, query: Select, p: PageParams) -> dict:
    """Το query πρέπει να έχει order_by: ο SQL Server δεν δέχεται OFFSET χωρίς ORDER BY."""
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = db.scalars(query.offset(p.offset).limit(p.page_size)).all()
    return {"items": items, "total": total, "page": p.page, "page_size": p.page_size}
