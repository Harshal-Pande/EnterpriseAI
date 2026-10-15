"""Comprehensive data audit script for Enterprise AI Mesh (P0 Audit)."""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.connection import connect, load_project_env

load_project_env()
conn = connect("DATABASE_URL")
cur = conn.cursor()

print("--- DATA AUDIT SNAPSHOT ---")

# Columns of orders table
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'orders' AND table_schema = 'public'
    ORDER BY ordinal_position;
""")
orders_cols = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
print(f"Orders columns: {orders_cols}")

# Find timestamp columns in orders
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'orders' AND data_type LIKE '%timestamp%' AND table_schema = 'public';
""")
ts_cols = [r[0] for r in cur.fetchall()]
print(f"Orders timestamp columns: {ts_cols}")

# Date range for orders
if ts_cols:
    c = ts_cols[0]
    cur.execute(f"SELECT min({c}), max({c}) FROM orders;")
    print(f"Orders {c} range: {cur.fetchone()}")

# Shipments columns & dates
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'shipments' AND data_type LIKE '%timestamp%' AND table_schema = 'public';
""")
ship_ts_cols = [r[0] for r in cur.fetchall()]
if ship_ts_cols:
    c = ship_ts_cols[0]
    cur.execute(f"SELECT min({c}), max({c}) FROM shipments;")
    print(f"Shipments {c} range: {cur.fetchone()}")

# Lines per order distribution
cur.execute("""
    SELECT lines_count, count(*) 
    FROM (
        SELECT order_id, count(*) AS lines_count 
        FROM order_lines 
        GROUP BY order_id
    ) sub 
    GROUP BY lines_count 
    ORDER BY lines_count;
""")
print(f"Lines-per-order distribution: {cur.fetchall()}")

# Total orders vs order lines
cur.execute("SELECT count(*) FROM orders;")
print(f"Total orders: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM order_lines;")
print(f"Total order lines: {cur.fetchone()[0]}")

# Products in BOM
cur.execute("SELECT count(distinct product_id) FROM products;")
total_products = cur.fetchone()[0]

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'bill_of_materials' AND table_schema = 'public'
    ORDER BY ordinal_position;
""")
bom_cols = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
print(f"BOM columns: {bom_cols}")

cur.execute("SELECT count(*) FROM bill_of_materials;")
print(f"Total BOM rows: {cur.fetchone()[0]}")

# Suppliers & Offers
cur.execute("SELECT count(*) FROM suppliers;")
print(f"Total suppliers: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM supplier_offers;")
print(f"Total supplier offers: {cur.fetchone()[0]}")

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'supplier_offers' AND table_schema = 'public'
    ORDER BY ordinal_position;
""")
print(f"Supplier offers columns: {[r[0] for r in cur.fetchall()]}")

cur.execute("SELECT count(distinct item_id) FROM supplier_offers;")
print(f"Distinct items covered by supplier offers: {cur.fetchone()[0]}")

# Warehouses & inventory
cur.execute("SELECT count(*) FROM warehouses;")
print(f"Total warehouses: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM inventory;")
print(f"Total inventory rows: {cur.fetchone()[0]}")
cur.execute("SELECT count(distinct item_id) FROM inventory;")
print(f"Distinct items in inventory: {cur.fetchone()[0]}")

# Budgets
cur.execute("SELECT count(*) FROM budgets;")
print(f"Total budgets: {cur.fetchone()[0]}")

# Graph status via RelationalGraphEngine
try:
    from app.services.graph_service import RelationalGraphEngine
    engine = RelationalGraphEngine()
    g = engine.build_graph()
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    print(f"Graph Nodes: {len(nodes)}, Graph Edges: {len(edges)}")
    
    # Calculate connected components
    adj = {}
    for n in nodes:
        adj[n["id"]] = set()
    for e in edges:
        s, t = e["source"], e["target"]
        if s in adj and t in adj:
            adj[s].add(t)
            adj[t].add(s)
            
    visited = set()
    comps = []
    for nid in adj:
        if nid not in visited:
            comp = set()
            stack = [nid]
            while stack:
                curr = stack.pop()
                if curr not in comp:
                    comp.add(curr)
                    for nxt in adj[curr]:
                        if nxt not in comp:
                            stack.append(nxt)
            visited.update(comp)
            comps.append(comp)
            
    print(f"Connected components count: {len(comps)}")
    if comps:
        largest = max(len(c) for c in comps)
        print(f"Largest component size: {largest} nodes (out of {len(nodes)})")
        isolated = sum(1 for c in comps if len(c) == 1)
        print(f"Isolated nodes count: {isolated}")
except Exception as e:
    print(f"Graph engine inspection: {e}")

cur.close()
conn.close()
