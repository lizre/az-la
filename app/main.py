# FastAPI is the web framework — it handles incoming HTTP requests and routes them
# to the right function based on the URL and method (GET, POST, etc.)
from fastapi import FastAPI, HTTPException, Depends

# CORSMiddleware allows the browser to make API requests from a different origin.
# Without this, the browser would block JavaScript from calling /items.
from fastapi.middleware.cors import CORSMiddleware

# HTMLResponse tells FastAPI to send HTML instead of JSON for a specific endpoint.
from fastapi.responses import HTMLResponse

# Session is the type hint for a database session (used in endpoint parameters).
from sqlalchemy.orm import Session

# List is used to say "this endpoint returns a list of items".
from typing import List

# uvicorn is the server that runs the FastAPI app.
import uvicorn

# Import our own modules. The dot (.) means "from the same package (app/)".
from .database import get_db, engine  # the DB connection and session factory
from . import models, schemas          # table definitions and API shapes


# Create all database tables on startup if they don't already exist.
# SQLAlchemy looks at all the classes that inherit from Base (i.e. Item in models.py)
# and creates the corresponding tables in PostgreSQL.
# This is safe to run every time — it only creates tables that are missing.
models.Base.metadata.create_all(bind=engine)


# Create the FastAPI app instance. The title and description show up in the /docs UI.
app = FastAPI(
    title="Azure Learning App",
    description="A simple REST API to learn Azure deployment",
    version="1.0.0"
)

# CORS (Cross-Origin Resource Sharing) — allows the HTML page served at /
# to make fetch() calls to /items in the browser.
# allow_origins=["*"] means any origin is allowed. Fine for learning,
# but in production you'd restrict this to your own domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---
# A route is a URL pattern + HTTP method that maps to a function.
# The decorator (@app.get, @app.post, etc.) registers the function with FastAPI.


@app.get("/", response_class=HTMLResponse)
def root():
    """
    Serves the HTML frontend at the root URL.
    response_class=HTMLResponse tells FastAPI to send the return value as HTML,
    not wrap it in JSON (which is the default).
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Azure Learning App</title>
  <style>
    body { font-family: sans-serif; max-width: 600px; margin: 60px auto; padding: 0 20px; }
    h1 { font-size: 1.4rem; margin-bottom: 24px; }
    input, textarea { display: block; width: 100%; box-sizing: border-box; padding: 8px;
                      margin-bottom: 10px; font-size: 1rem; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 8px 20px; font-size: 1rem; background: #0078d4; color: white;
             border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background: #005fa3; }
    #status { margin-top: 10px; font-size: 0.9rem; color: green; }
    #error  { margin-top: 10px; font-size: 0.9rem; color: red; }
    ul { list-style: none; padding: 0; margin-top: 30px; }
    li { border: 1px solid #eee; border-radius: 4px; padding: 10px 14px; margin-bottom: 8px; }
    li .name { font-weight: bold; }
    li .desc { color: #555; font-size: 0.9rem; margin-top: 2px; }
    li .date { color: #aaa; font-size: 0.8rem; margin-top: 4px; }
  </style>
</head>
<body>
  <h1>Items</h1>
  <input id="name" type="text" placeholder="Name (required)" />
  <textarea id="desc" rows="2" placeholder="Description (optional)"></textarea>
  <button onclick="addItem()">Save</button>
  <div id="status"></div>
  <div id="error"></div>
  <ul id="list"></ul>

  <script>
    // Fetch all items from the API and render them in the list.
    async function loadItems() {
      const res = await fetch('/items');
      const items = await res.json();
      const list = document.getElementById('list');
      list.innerHTML = '';
      // Reverse so newest items appear at the top.
      items.reverse().forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = '<div class="name">' + escHtml(item.name) + '</div>' +
          (item.description ? '<div class="desc">' + escHtml(item.description) + '</div>' : '') +
          '<div class="date">' + new Date(item.created_at).toLocaleString() + '</div>';
        list.appendChild(li);
      });
    }

    // Read the form values and POST them to the API to create a new item.
    async function addItem() {
      const name = document.getElementById('name').value.trim();
      const desc = document.getElementById('desc').value.trim();
      document.getElementById('status').textContent = '';
      document.getElementById('error').textContent = '';
      if (!name) { document.getElementById('error').textContent = 'Name is required.'; return; }
      const res = await fetch('/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc || null })
      });
      if (res.ok) {
        document.getElementById('name').value = '';
        document.getElementById('desc').value = '';
        document.getElementById('status').textContent = 'Saved!';
        loadItems();  // refresh the list
      } else {
        document.getElementById('error').textContent = 'Something went wrong.';
      }
    }

    // Escape special HTML characters to prevent XSS — if someone saves
    // "<script>alert('hi')</script>" as an item name, this stops it from running.
    function escHtml(str) {
      return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    // Load items immediately when the page opens.
    loadItems();
  </script>
</body>
</html>
"""


@app.get("/health")
def health():
    """
    A simple health check endpoint. Returns {"status": "ok"} if the app is running.
    Azure (and other platforms) can ping this to check if the app is alive.
    """
    return {"status": "ok"}


# --- Items CRUD endpoints ---
# CRUD = Create, Read, Update, Delete — the four basic database operations.
# Each endpoint uses `db: Session = Depends(get_db)` which tells FastAPI to
# automatically call get_db() and pass the resulting session in as `db`.


@app.get("/items", response_model=List[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    """
    GET /items — returns all items in the database.
    response_model=List[schemas.Item] tells FastAPI to validate and format
    the response using the Item schema, and to document it in /docs.
    """
    return db.query(models.Item).all()


@app.get("/items/{item_id}", response_model=schemas.Item)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """
    GET /items/42 — returns a single item by its ID.
    {item_id} in the path is a path parameter — FastAPI extracts it from the URL
    and passes it to the function as an integer.
    """
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        # HTTPException causes FastAPI to return an error response instead of continuing.
        # status_code=404 means "not found" — a standard HTTP status code.
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=schemas.Item, status_code=201)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    POST /items — creates a new item.
    FastAPI reads the request body and validates it against schemas.ItemCreate.
    status_code=201 means "created" — the standard HTTP code for successful creation.
    """
    # **item.dict() unpacks the schema fields as keyword arguments into the model constructor.
    # This is equivalent to: models.Item(name=item.name, description=item.description)
    db_item = models.Item(**item.dict())
    db.add(db_item)      # stage the new row (not saved yet)
    db.commit()          # write it to the database
    db.refresh(db_item)  # reload from DB to get the auto-generated id and created_at
    return db_item


@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    PUT /items/42 — replaces an existing item with new data.
    PUT means "replace the whole thing" (vs PATCH which means "change some fields").
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    # Loop over each field in the incoming data and update the database row.
    for key, value in item.dict().items():
        setattr(db_item, key, value)  # setattr(obj, "name", "foo") is like obj.name = "foo"
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    DELETE /items/42 — deletes an item.
    status_code=204 means "no content" — the standard HTTP code for a successful delete
    that returns nothing in the response body.
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()


# This block only runs if you execute the file directly with `python main.py`.
# It does NOT run when the app is started by uvicorn in production (via the Dockerfile CMD).
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
