# Database Schema Notes

This file outlines the intended schema for the PostgreSQL / pgvector database.

## Tables
- `orders` (id, customer_id, status, created_at, updated_at)
- `inventory` (id, item_name, quantity, warehouse_id)
- `suppliers` (id, name, rating, api_endpoint)
- `audit_events` (id, order_id, event_type, tx_hash, timestamp)

## Vector Embeddings
- Future: store text embeddings of supplier contracts or past procurement negotiations to aid LLM decision-making.
