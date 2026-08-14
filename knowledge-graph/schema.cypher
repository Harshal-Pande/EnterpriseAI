// Enterprise AI Mesh - Neo4j Schema Cypher

// Constraints & Indexes
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (w:Warehouse) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:InventoryItem) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (pd:ProcurementDecision) REQUIRE pd.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (fa:FinancialApproval) REQUIRE fa.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (lr:LogisticsRoute) REQUIRE lr.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ae:AuditEvent) REQUIRE ae.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE;

// Note: Relationships are formed dynamically. Key relationships include:
// (Customer)-[:PLACED]->(Order)
// (Order)-[:REQUIRES]->(Product)
// (Warehouse)-[:STORES]->(InventoryItem)
// (InventoryItem)-[:IS_OF_TYPE]->(Product)
// (Supplier)-[:SUPPLIES]->(Product)
// (Agent)-[:MADE]->(ProcurementDecision)
// (ProcurementDecision)-[:APPROVED_BY]->(FinancialApproval)
// (Order)-[:DELIVERED_VIA]->(LogisticsRoute)
// (Order)-[:HAS_AUDIT]->(AuditEvent)
