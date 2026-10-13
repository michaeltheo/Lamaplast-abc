from app.core.db import get_db
from app.core.pagination import MAX_PAGE_SIZE, Pagination, paginate
from app.models import ProductGroup
from app.schemas.lookups import ProductGroupOut
from app.schemas.pagination import Page
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

# Μικρό app μόνο για το test: ένα endpoint με σελιδοποίηση πάνω στις 39 ομάδες προϊόντων.
app = FastAPI()


@app.get("/groups", response_model=Page[ProductGroupOut])
def groups(p: Pagination, pillar: str | None = None, db: Session = Depends(get_db)):
    query = select(ProductGroup).order_by(ProductGroup.Group_Code)
    if pillar is not None:
        query = query.where(ProductGroup.Pillar_Code == pillar)
    return paginate(db, query, p)


client = TestClient(app)


def test_defaults_to_first_page_of_fifty():
    body = client.get("/groups").json()
    assert (body["page"], body["page_size"], body["total"]) == (1, 50, 39)
    assert len(body["items"]) == 39


def test_first_page_has_page_size_items():
    body = client.get("/groups", params={"page_size": 10}).json()
    assert len(body["items"]) == 10
    assert body["items"][0]["Group_Code"] == "01-1-100"
    assert body["total"] == 39


def test_second_page_continues_where_first_ended():
    first = client.get("/groups", params={"page": 1, "page_size": 10}).json()["items"]
    second = client.get("/groups", params={"page": 2, "page_size": 10}).json()["items"]
    assert second[0]["Group_Code"] > first[-1]["Group_Code"]
    assert not {g["Group_Code"] for g in first} & {g["Group_Code"] for g in second}


def test_last_page_has_the_remainder():
    body = client.get("/groups", params={"page": 4, "page_size": 10}).json()
    assert len(body["items"]) == 9


def test_page_past_the_end_is_empty_but_keeps_total():
    body = client.get("/groups", params={"page": 99, "page_size": 10}).json()
    assert body["items"] == []
    assert body["total"] == 39


def test_total_counts_only_filtered_rows():
    body = client.get("/groups", params={"pillar": "01-2", "page_size": 5}).json()
    assert len(body["items"]) == 5
    assert body["total"] == 7


def test_page_size_at_max_is_accepted():
    assert client.get("/groups", params={"page_size": MAX_PAGE_SIZE}).status_code == 200


def test_page_size_above_max_is_rejected():
    assert client.get("/groups", params={"page_size": MAX_PAGE_SIZE + 1}).status_code == 422


def test_page_zero_is_rejected():
    assert client.get("/groups", params={"page": 0}).status_code == 422
