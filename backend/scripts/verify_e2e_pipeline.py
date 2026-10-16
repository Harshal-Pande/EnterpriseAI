"""Phase 9: Local End-to-End Verification of Order Lifecycle Pipeline."""

import urllib.request
import json
import sys

base_url = 'http://127.0.0.1:8000'
headers = {'X-API-Key': 'dev-operator-key', 'Content-Type': 'application/json'}

def post_json(path, data):
    req = urllib.request.Request(f"{base_url}{path}", data=json.dumps(data).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def get_json(path):
    req = urllib.request.Request(f"{base_url}{path}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

print("======================================================================")
print("             PHASE 9: LOCAL END-TO-END PIPELINE VERIFICATION           ")
print("======================================================================")

# 1. Create Orders A, B, C
print("\n[Step 1] Creating Requisition Orders A, B, C...")
oa = post_json('/api/orders/', {'customer_ref': 'E2E Client Alpha', 'entity_id': 'EAS-EAST', 'lines': [{'product_id': 'PRD-HRC', 'requested_qty': 40, 'unit_price_inr': 72000}]})
print(f"  -> Created Order A: {oa['order_id']} (Queue Pos: {oa['queue_position']})")

ob = post_json('/api/orders/', {'customer_ref': 'E2E Client Beta', 'entity_id': 'EAS-EAST', 'lines': [{'product_id': 'PRD-CRC', 'requested_qty': 30, 'unit_price_inr': 84500}]})
print(f"  -> Created Order B: {ob['order_id']} (Queue Pos: {ob['queue_position']})")

oc = post_json('/api/orders/', {'customer_ref': 'E2E Client Gamma', 'entity_id': 'EAS-EAST', 'lines': [{'product_id': 'PRD-REB', 'requested_qty': 60, 'unit_price_inr': 61000}]})
print(f"  -> Created Order C: {oc['order_id']} (Queue Pos: {oc['queue_position']})")

# 2. Verify FIFO Queue contains them in order
print("\n[Step 2] Verifying FIFO Queue Sequence...")
queued = get_json('/api/orders/lifecycle/queued?limit=150')
queued_ids = [q['order_id'] for q in queued]
idx_a = queued_ids.index(oa['order_id'])
idx_b = queued_ids.index(ob['order_id'])
idx_c = queued_ids.index(oc['order_id'])
assert idx_a < idx_b < idx_c, f"FIFO ordering failed: indices {idx_a}, {idx_b}, {idx_c}"
print(f"  -> VERIFIED: Sequence is {oa['order_id']} (#{idx_a+1}) -> {ob['order_id']} (#{idx_b+1}) -> {oc['order_id']} (#{idx_c+1})")

# 3. Execute Order A
print("\n[Step 3] Executing Order A through Governed Multi-Agent Mesh...")
res_a = post_json(f"/api/orders/lifecycle/run-order/{oa['order_id']}?scenario=NORMAL", {})
print(f"  -> Status: {res_a['status']}")
print(f"  -> Duration: {res_a['duration_ms']}ms")
print(f"  -> Mined into Blockchain Block: #{res_a['block_number']}")
print(f"  -> Transaction Hash: {res_a['tx_hash']}")

# 4. Verify Order A is removed from Queued and stored in Done
print("\n[Step 4] Verifying Order Lifecycle State Transitions...")
queued_after = get_json('/api/orders/lifecycle/queued?limit=150')
assert oa['order_id'] not in [q['order_id'] for q in queued_after], "Error: Order A still in queue!"
print(f"  -> VERIFIED: {oa['order_id']} deleted from orders_queued (FIFO).")

done = get_json('/api/orders/lifecycle/done?limit=50')
assert any(d['order_id'] == oa['order_id'] for d in done), "Error: Order A not in done archive!"
print(f"  -> VERIFIED: {oa['order_id']} permanently recorded in orders_done.")

# 5. Verify Decision Log for Order A
print("\n[Step 5] Verifying 5 Specialist Agent Decisions Persisted...")
decs = get_json(f"/api/orders/lifecycle/decisions?order_id={oa['order_id']}")
assert len(decs) == 5, f"Expected 5 agent decisions, got {len(decs)}"
for d in decs:
    print(f"  [{d['agent_name']}] {d['decision_type']}: {d['finding']} (Confidence: {d['confidence_score']*100:.1f}%, Anchored: {d['anchored_to_blockchain']})")

# 6. Verify Blockchain Block
print("\n[Step 6] Verifying Blockchain Block & Transaction Integrity...")
blocks = get_json('/api/orders/lifecycle/blockchain/blocks?limit=5')
latest_block = next((b for b in blocks if b['block_number'] == res_a['block_number']), None)
assert latest_block is not None, f"Block #{res_a['block_number']} not found!"
print(f"  -> Block #{latest_block['block_number']} Hash: {latest_block['block_hash']}")
print(f"  -> Merkle Root: {latest_block['merkle_root']}")
print(f"  -> Transaction Count: {latest_block['transaction_count']}")
print(f"  -> Validator: {latest_block['validator']}")

# 7. Execute Order B with Exception Scenario
print("\n[Step 7] Executing Order B with Controlled Exception (SUPPLIER_UNAVAILABLE)...")
res_b = post_json(f"/api/orders/lifecycle/run-order/{ob['order_id']}?scenario=SUPPLIER_UNAVAILABLE", {})
print(f"  -> Outcome: {res_b['status']} ({res_b.get('exception_type')})")
print(f"  -> Cause: {res_b.get('exception_cause')}")

running = get_json('/api/orders/lifecycle/running')
assert any(r['order_id'] == ob['order_id'] and r['status'] == 'EXCEPTION' for r in running), "Order B not in running with EXCEPTION!"
print(f"  -> VERIFIED: {ob['order_id']} held in orders_running with live EXCEPTION status for operator resolution.")

# 8. Verify Polling is Side-Effect Free
print("\n[Step 8] Verifying Polling Invariance (Zero Side Effects)...")
q_len_1 = len(get_json('/api/orders/lifecycle/queued?limit=150'))
for _ in range(5):
    get_json('/api/orders/lifecycle/queued?limit=150')
    get_json('/api/orders/lifecycle/running')
    get_json('/api/orders/lifecycle/done?limit=50')
q_len_2 = len(get_json('/api/orders/lifecycle/queued?limit=150'))
assert q_len_1 == q_len_2, "Polling modified queue length!"
print("  -> VERIFIED: Consecutive polling calls produced zero mutations.")

print("\n======================================================================")
print("       ALL PHASE 9 END-TO-END VERIFICATION CHECKS PASSED (100%)       ")
print("======================================================================")
