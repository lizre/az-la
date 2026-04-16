from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from .database import get_db, engine
from . import models, schemas

# Create all tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Azure Learning App",
    description="A simple REST API to learn Azure deployment",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def root():
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
    async function loadItems() {
      const res = await fetch('/items');
      const items = await res.json();
      const list = document.getElementById('list');
      list.innerHTML = '';
      items.reverse().forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = '<div class="name">' + escHtml(item.name) + '</div>' +
          (item.description ? '<div class="desc">' + escHtml(item.description) + '</div>' : '') +
          '<div class="date">' + new Date(item.created_at).toLocaleString() + '</div>';
        list.appendChild(li);
      });
    }

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
        loadItems();
      } else {
        document.getElementById('error').textContent = 'Something went wrong.';
      }
    }

    function escHtml(str) {
      return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    loadItems();
  </script>
</body>
</html>
"""


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Items CRUD (teaches you DB + networking) ---

@app.get("/items", response_model=List[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    return db.query(models.Item).all()


@app.get("/items/{item_id}", response_model=schemas.Item)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=schemas.Item, status_code=201)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
