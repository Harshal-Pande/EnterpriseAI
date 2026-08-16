import os
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "enterprise_password")

class Neo4jConnector:
    def __init__(self):
        self.driver = None

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j database successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_query(self, query, parameters=None):
        if not self.driver:
            raise Exception("Driver not initialized. Call connect() first.")
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

# Global singleton
neo4j_db = Neo4jConnector()

def get_neo4j():
    return neo4j_db

def seed_graph():
    """Seed the initial nodes and relationships if they do not exist."""
    queries = [
        "MERGE (c:Customer {id: 'CUST-003'}) SET c.name = 'Tata Steels Ltd', c.sector = 'Heavy Metals'",
        "MERGE (p:Product {id: 'WP-800'}) SET p.name = 'Industrial Water Pump', p.category = 'Industrial Pumps'",
        "MERGE (s1:Supplier {id: 'SUP-A'}) SET s1.name = 'Apex Industrial'",
        "MERGE (s2:Supplier {id: 'SUP-B'}) SET s2.name = 'Bharat Heavy'",
        "MERGE (s3:Supplier {id: 'SUP-C'}) SET s3.name = 'Crestline Global'",
        "MERGE (w:Warehouse {id: 'WH-NAGPUR'}) SET w.name = 'Nagpur DC Hub'",
        "MERGE (s2)-[:SUPPLIES]->(p)",
        "MERGE (w)-[:STORES]->(p)",
        "MERGE (a1:Agent {id: 'supervisor'}) SET a1.name = 'Supervisor Agent'",
        "MERGE (a2:Agent {id: 'inventory'}) SET a2.name = 'Inventory Agent'",
        "MERGE (a3:Agent {id: 'procurement'}) SET a3.name = 'Procurement Agent'",
        "MERGE (a4:Agent {id: 'finance'}) SET a4.name = 'Finance Agent'",
        "MERGE (a5:Agent {id: 'logistics'}) SET a5.name = 'Logistics Agent'"
    ]
    for q in queries:
        neo4j_db.execute_query(q)
    logger.info("Neo4j graph seeded successfully.")

def track_decision(agent_id, decision_type, order_id, details=""):
    """Track an agent decision in the graph and link it to the order."""
    query = f"""
    MATCH (a:Agent {{id: $agent_id}}), (o:Order {{id: $order_id}})
    CREATE (d:Decision {{id: randomUUID(), type: $decision_type, details: $details, timestamp: timestamp()}})
    CREATE (a)-[:MADE]->(d)
    CREATE (d)-[:FOR_ORDER]->(o)
    RETURN d
    """
    return neo4j_db.execute_query(query, {"agent_id": agent_id, "decision_type": decision_type, "order_id": order_id, "details": details})
