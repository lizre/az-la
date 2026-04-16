from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .database import Base


# A model is a Python class that represents a database table.
# Each instance of the class represents one row in that table.
# SQLAlchemy reads these class definitions and creates the actual
# tables in PostgreSQL when `Base.metadata.create_all()` is called at startup.

class Item(Base):
    # __tablename__ tells SQLAlchemy what to call the table in the database.
    __tablename__ = "items"

    # Each Column() call defines one column in the table.
    # The first argument is the data type. The keyword arguments set constraints.

    # Integer primary key — auto-increments so each row gets a unique ID automatically.
    id = Column(Integer, primary_key=True, index=True)

    # String(100) means a text column with a max length of 100 characters.
    # nullable=False means this field is required — the database will reject a row without it.
    name = Column(String(100), nullable=False)

    # Text is like String but with no length limit. Good for longer content.
    # nullable=True means this field is optional (this is also the default).
    description = Column(Text, nullable=True)

    # DateTime columns for tracking when rows were created and last changed.
    # server_default=func.now() tells the database to automatically set this
    # to the current timestamp when a new row is inserted — you don't have to pass it yourself.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # onupdate=func.now() tells the database to automatically update this timestamp
    # whenever the row is modified. It stays null until the first update.
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
