"""Small SQLite product and sales registry for business-aware forecasting."""
from __future__ import annotations
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parents[1] / 'data' / 'cerebro_registry.sqlite'

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS product(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', brand TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS location(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS sales_observation(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES product(id), location_id INTEGER REFERENCES location(id), date TEXT NOT NULL, units REAL NOT NULL CHECK(units>=0), price REAL, promotion INTEGER NOT NULL DEFAULT 0, visitors REAL, stockout INTEGER NOT NULL DEFAULT 0, UNIQUE(product_id,location_id,date));
    CREATE TABLE IF NOT EXISTS inventory_state(product_id INTEGER PRIMARY KEY REFERENCES product(id), current_stock REAL NOT NULL DEFAULT 0, incoming_stock REAL NOT NULL DEFAULT 0, supplier_lead_time INTEGER NOT NULL DEFAULT 7);
    ''')
    return conn

def add_product(name: str, category: str = '', brand: str = '') -> dict[str, Any]:
    with connect() as c:
        row=c.execute('SELECT * FROM product WHERE lower(name)=lower(?)', (name.strip(),)).fetchone()
        if row: return dict(row)
        cur=c.execute('INSERT INTO product(name,category,brand) VALUES(?,?,?)',(name.strip(),category.strip(),brand.strip()))
        c.execute('INSERT INTO inventory_state(product_id) VALUES(?)',(cur.lastrowid,))
        return dict(c.execute('SELECT * FROM product WHERE id=?',(cur.lastrowid,)).fetchone())

def products() -> list[dict]:
    with connect() as c: return [dict(x) for x in c.execute('SELECT * FROM product ORDER BY name')]

def save_sales(product_id: int, rows: list[dict], location_id: int|None=None) -> dict:
    dates=[str(r['date']) for r in rows]
    if dates != sorted(set(dates)): raise ValueError('Sales dates must be unique and sorted before saving.')
    with connect() as c:
        if not c.execute('SELECT 1 FROM product WHERE id=?',(product_id,)).fetchone(): raise ValueError('Unknown product.')
        for r in rows:
            c.execute('INSERT OR REPLACE INTO sales_observation(product_id,location_id,date,units,price,promotion,visitors,stockout) VALUES(?,?,?,?,?,?,?,?)',(product_id,location_id,str(r['date']),float(r['units']),r.get('price'),int(bool(r.get('promotion'))),r.get('visitors'),int(bool(r.get('stockout')))))
    return readiness(product_id)

def readiness(product_id: int) -> dict:
    with connect() as c:
        p=c.execute('SELECT * FROM product WHERE id=?',(product_id,)).fetchone()
        rows=[dict(x) for x in c.execute('SELECT * FROM sales_observation WHERE product_id=? ORDER BY date',(product_id,))]
    if not p: raise ValueError('Unknown product.')
    dates=[date.fromisoformat(r['date']) for r in rows]
    gaps=sum((b-a).days-1 for a,b in zip(dates,dates[1:]) if (b-a).days>1)
    n=len(rows); zeros=sum(r['units']==0 for r in rows)
    level='READY' if n>=28 and gaps==0 else 'LIMITED' if n>=7 else 'INSUFFICIENT HISTORY'
    return {'product':dict(p),'days':n,'frequency':'daily' if len(dates)<2 or all((b-a).days==1 for a,b in zip(dates,dates[1:])) else 'irregular','missing_dates':gaps,'zero_demand_percent':round(zeros/n*100,1) if n else 0,'recent_average':round(sum(r['units'] for r in rows[-14:])/max(1,len(rows[-14:])),2),'stockout_days':sum(r['stockout'] for r in rows),'price_available':any(r['price'] is not None for r in rows),'promotion_available':any(r['promotion'] for r in rows),'status':level}
