from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# Schemas define the shape of data coming in and out of the API.
# They are separate from models (which define the database tables) because
# what you expose in the API isn't always the same as what you store internally.
# For example, you might store a hashed password but never return it in the API.
#
# Pydantic (the library these are based on) automatically validates incoming data.
# If a request is missing a required field or sends the wrong type, FastAPI returns
# a 422 error with a clear message — without you writing any validation code.


class ItemCreate(BaseModel):
    """
    The shape of data the API expects when creating or updating an item.
    This is what the user sends in the request body.

    `name` is required — Pydantic will reject a request that doesn't include it.
    `description` is optional — if not provided, it defaults to None.
    """
    name: str
    description: Optional[str] = None


class Item(ItemCreate):
    """
    The shape of data the API returns when reading an item.
    Extends ItemCreate (so it includes name and description) and adds
    the fields that only exist after the item has been saved to the database.

    You'd never send `id` or `created_at` when creating an item — the database
    generates those. But you do want to include them in the response.
    """
    id: int                           # assigned by the database, not the user
    created_at: datetime              # set automatically on insert
    updated_at: Optional[datetime] = None  # null until the item is edited

    class Config:
        # By default Pydantic only works with plain dictionaries.
        # from_attributes=True tells it to also work with SQLAlchemy model objects,
        # so FastAPI can convert a database row directly into a response.
        from_attributes = True
