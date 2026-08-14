// Enterprise AI Mesh - Sample Data

// Create Agents
CREATE (:Agent {id: "SupervisorAgent", name: "Supervisor"});
CREATE (:Agent {id: "InventoryAgent", name: "Inventory"});
CREATE (:Agent {id: "ProcurementAgent", name: "Procurement"});

// Create Sample Order ORD-1042
CREATE (c:Customer {id: "CUST-001", name: "Acme Corp"})
CREATE (o:Order {id: "ORD-1042", status: "processing"})
CREATE (c)-[:PLACED]->(o);

// Create Sample Order WP-800
CREATE (c2:Customer {id: "CUST-002", name: "Globex"})
CREATE (o2:Order {id: "WP-800", status: "pending"})
CREATE (c2)-[:PLACED]->(o2);

// Add missing links
CREATE (p1:Product {id: "PROD-A", name: "Industrial Widget"})
CREATE (o)-[:REQUIRES {quantity: 50}]->(p1);

CREATE (s1:Supplier {id: "SUPP-001", name: "WidgetCo"})
CREATE (s1)-[:SUPPLIES]->(p1);
