"""Synthetic Data Generator v3 — Phase P3.

Generates realistic Indian steel supply chain data anchored to reference date 2026-10-15.
Uses a fixed seed for full reproducibility. All data is validated before load.

Usage:
    python backend/data/synth/generate.py --target TEST_DATABASE_URL
    python backend/data/synth/generate.py --target TEST_DATABASE_URL --dry-run
    python backend/data/synth/generate.py --target TEST_DATABASE_URL --output-dir ./out
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("synth.generate")

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
SEED = 20261015  # Anchored to project reference date
REF_DATE = datetime(2026, 10, 15, tzinfo=timezone.utc)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def _rng(seed: int = SEED) -> random.Random:
    return random.Random(seed)


# ──────────────────────────────────────────────────────────────────────────────
# Seed reference data (extends workbook fixtures without modifying them)
# ──────────────────────────────────────────────────────────────────────────────

# Additional products beyond the 11 existing ones
EXTRA_PRODUCTS = [
    ("PRD-WIRE", "Wire Rod", "Finished Steel", "MT", 58000.0),
    ("PRD-BEAM", "H-Beam", "Structural Steel", "MT", 72000.0),
    ("PRD-PIPE", "ERW Pipe", "Tubular Steel", "MT", 85000.0),
    ("PRD-GALV", "Galvanised Coil", "Finished Steel", "MT", 92000.0),
    ("PRD-SHEET", "HR Sheet", "Finished Steel", "MT", 62000.0),
    ("PRD-ANGLE", "Structural Angle", "Structural Steel", "MT", 68000.0),
    ("PRD-STRIP", "Steel Strip", "Finished Steel", "MT", 65000.0),
    ("PRD-BILLET", "Billet", "Semifinished Steel", "MT", 45000.0),
    ("PRD-SLAB", "Slab", "Semifinished Steel", "MT", 43000.0),
    ("PRD-PELLET", "Iron Ore Pellet", "Raw Material", "MT", 11000.0),
    ("MAT-SCRAP", "Steel Scrap", "Raw Material", "MT", 28000.0),
    ("MAT-ALLOY", "Ferro Alloys", "Raw Material", "KG", 210.0),
    ("MAT-ZINC", "Zinc Ingot", "Raw Material", "MT", 280000.0),
    ("MAT-OIL", "Hydraulic Oil", "Consumable", "L", 180.0),
    ("MAT-ROLL", "Rolling Mill Roll", "Consumable", "EA", 750000.0),
]

CUSTOMERS = [
    ("CUST-001", "Tata Motors Ltd", "B2B", "Pune", "MH", 50_000_000, 45, "STRATEGIC"),
    ("CUST-002", "Mahindra & Mahindra", "B2B", "Mumbai", "MH", 40_000_000, 45, "STRATEGIC"),
    ("CUST-003", "Ashok Leyland", "B2B", "Chennai", "TN", 30_000_000, 30, "PREFERRED"),
    ("CUST-004", "L&T Construction", "B2B", "Hyderabad", "TS", 25_000_000, 30, "PREFERRED"),
    ("CUST-005", "Bajaj Auto Ltd", "B2B", "Pune", "MH", 15_000_000, 30, "PREFERRED"),
    ("CUST-006", "Voltas Ltd", "B2B", "Mumbai", "MH", 8_000_000, 30, "STANDARD"),
    ("CUST-007", "Indian Railways", "B2B", "New Delhi", "DL", 100_000_000, 60, "STRATEGIC"),
    ("CUST-008", "ONGC Ltd", "B2B", "Mumbai", "MH", 20_000_000, 45, "PREFERRED"),
    ("CUST-009", "NHPC Ltd", "B2B", "Faridabad", "HR", 12_000_000, 30, "PREFERRED"),
    ("CUST-010", "SAIL Distribution", "INTERNAL", "Bhilai", "CG", 0, 0, "STANDARD"),
    ("CUST-011", "Rashtriya Ispat Nigam", "B2B", "Visakhapatnam", "AP", 18_000_000, 30, "PREFERRED"),
    ("CUST-012", "Godrej Industries", "B2B", "Mumbai", "MH", 10_000_000, 30, "STANDARD"),
    ("CUST-013", "Premier Cement", "B2B", "Cochin", "KL", 7_000_000, 45, "STANDARD"),
    ("CUST-014", "Maruti Suzuki India", "B2B", "Gurugram", "HR", 35_000_000, 45, "STRATEGIC"),
    ("CUST-015", "BHEL Haridwar", "B2B", "Haridwar", "UK", 20_000_000, 45, "PREFERRED"),
    ("CUST-016", "IRCON International", "B2B", "New Delhi", "DL", 15_000_000, 30, "PREFERRED"),
    ("CUST-017", "Hindalco Industries", "B2B", "Mumbai", "MH", 22_000_000, 30, "PREFERRED"),
    ("CUST-018", "JSW Energy", "B2B", "Mumbai", "MH", 9_000_000, 30, "STANDARD"),
    ("CUST-019", "Megha Engineering", "B2B", "Hyderabad", "TS", 6_000_000, 30, "STANDARD"),
    ("CUST-020", "Sai Infra Projects", "B2B", "Bengaluru", "KA", 4_000_000, 30, "STANDARD"),
    ("CUST-021", "Star Wire India", "B2B", "Faridabad", "HR", 3_000_000, 30, "STANDARD"),
    ("CUST-022", "Uttam Steel", "B2B", "Mumbai", "MH", 5_000_000, 30, "STANDARD"),
    ("CUST-023", "EXPORT-SGP-GENCO", "EXPORT", "Singapore", None, 0, 60, "STANDARD"),
    ("CUST-024", "EXPORT-UAE-MASDAR", "EXPORT", "Dubai", None, 0, 60, "STANDARD"),
    ("CUST-025", "EXPORT-BD-BASHUNDHARA", "EXPORT", "Dhaka", None, 0, 45, "STANDARD"),
    ("CUST-026", "EXPORT-VN-HOAPHAT", "EXPORT", "Hanoi", None, 0, 45, "STANDARD"),
    ("CUST-027", "EXPORT-KE-DEVKI", "EXPORT", "Nairobi", None, 0, 60, "STANDARD"),
    ("CUST-028", "Hindustan Aeronautics", "B2B", "Bengaluru", "KA", 8_000_000, 45, "PREFERRED"),
    ("CUST-029", "ArcelorMittal Nippon", "B2B", "Hazira", "GJ", 60_000_000, 30, "STRATEGIC"),
    ("CUST-030", "Vizag Steel Traders", "B2B", "Visakhapatnam", "AP", 2_500_000, 30, "STANDARD"),
    ("CUST-031", "South India Steel Corp", "B2B", "Chennai", "TN", 4_000_000, 30, "STANDARD"),
    ("CUST-032", "Minda Industries", "B2B", "Pune", "MH", 3_000_000, 30, "STANDARD"),
    ("CUST-033", "Kalyani Steels", "B2B", "Pune", "MH", 5_500_000, 30, "STANDARD"),
    ("CUST-034", "Patton International", "B2B", "Mumbai", "MH", 1_500_000, 30, "STANDARD"),
    ("CUST-035", "Bhilwara Energy", "B2B", "Bhilwara", "RJ", 2_000_000, 30, "STANDARD"),
    ("CUST-036", "Thermax Ltd", "B2B", "Pune", "MH", 6_000_000, 30, "STANDARD"),
    ("CUST-037", "Walchandnagar Industries", "B2B", "Mumbai", "MH", 3_000_000, 30, "STANDARD"),
    ("CUST-038", "Mukand Ltd", "B2B", "Thane", "MH", 4_000_000, 30, "STANDARD"),
    ("CUST-039", "EID Parry", "B2B", "Chennai", "TN", 1_000_000, 45, "STANDARD"),
    ("CUST-040", "Internal Distribution", "INTERNAL", "Bhilai", "CG", 0, 0, "STANDARD"),
    ("CUST-041", "EXPORT-AU-BLUESCOPE", "EXPORT", "Melbourne", None, 0, 60, "STANDARD"),
    ("CUST-042", "Kirloskar Electric", "B2B", "Bengaluru", "KA", 2_500_000, 30, "STANDARD"),
    ("CUST-043", "Greenko Group", "B2B", "Hyderabad", "TS", 4_000_000, 30, "STANDARD"),
    ("CUST-044", "MECON Ltd", "B2B", "Ranchi", "JH", 6_000_000, 30, "PREFERRED"),
    ("CUST-045", "Deepak Fertilisers", "B2B", "Pune", "MH", 3_000_000, 45, "STANDARD"),
    ("CUST-046", "Dixon Technologies", "B2B", "Noida", "UP", 2_000_000, 30, "STANDARD"),
    ("CUST-047", "Precision Camshafts", "B2B", "Solapur", "MH", 1_500_000, 30, "STANDARD"),
    ("CUST-048", "Man Industries", "B2B", "Mumbai", "MH", 3_500_000, 30, "STANDARD"),
    ("CUST-049", "Suraj Products Ltd", "B2B", "Mumbai", "MH", 1_200_000, 30, "STANDARD"),
    ("CUST-050", "HPCL Biofuels", "B2B", "Patna", "BR", 1_000_000, 45, "STANDARD"),
    ("CUST-051", "IOCL Mathura", "B2B", "Mathura", "UP", 8_000_000, 30, "PREFERRED"),
    ("CUST-052", "National Steel Corp", "B2B", "Jamshedpur", "JH", 5_000_000, 30, "PREFERRED"),
    ("CUST-053", "Zenith Steel India", "B2B", "Raipur", "CG", 2_000_000, 30, "STANDARD"),
    ("CUST-054", "Raipur Wire Products", "B2B", "Raipur", "CG", 1_500_000, 30, "STANDARD"),
    ("CUST-055", "RITES Ltd", "B2B", "Gurugram", "HR", 7_000_000, 45, "PREFERRED"),
    ("CUST-056", "Shyam Metalics", "B2B", "Sambalpur", "OD", 4_500_000, 30, "STANDARD"),
    ("CUST-057", "Electrotherm India", "B2B", "Ahmedabad", "GJ", 3_000_000, 30, "STANDARD"),
    ("CUST-058", "IMC Ltd", "B2B", "Kolkata", "WB", 2_000_000, 30, "STANDARD"),
    ("CUST-059", "RINL Vizag", "B2B", "Visakhapatnam", "AP", 25_000_000, 30, "STRATEGIC"),
    ("CUST-060", "Orissa Minerals Dev", "B2B", "Bhubaneswar", "OD", 3_000_000, 45, "STANDARD"),
]

CARRIERS = [
    ("CAR-001", "Concor Rail Logistics", "RAIL", ["PAN_INDIA"], 5000, 7, 0.91, 2.5),
    ("CAR-002", "Gati-KWE Express", "ROAD", ["WEST", "NORTH", "SOUTH"], 50, 2, 0.87, 18.0),
    ("CAR-003", "TCI Freight", "ROAD", ["PAN_INDIA"], 30, 3, 0.85, 16.5),
    ("CAR-004", "Allcargo Sea Lines", "SEA", ["COASTAL", "EXPORT"], 20000, 10, 0.93, 1.2),
    ("CAR-005", "Rivigo Technologies", "ROAD", ["NORTH", "WEST"], 25, 2, 0.89, 17.5),
    ("CAR-006", "VRL Logistics", "ROAD", ["SOUTH", "WEST"], 30, 3, 0.86, 16.0),
    ("CAR-007", "Container Corp Rail", "RAIL", ["PAN_INDIA"], 8000, 5, 0.94, 2.1),
    ("CAR-008", "Blue Dart Cargo", "ROAD", ["PAN_INDIA"], 5, 1, 0.97, 45.0),
    ("CAR-009", "Mercator Shipping", "SEA", ["COASTAL", "EXPORT", "IMPORT"], 25000, 12, 0.90, 0.9),
    ("CAR-010", "Road Wings Ltd", "ROAD", ["EAST", "NORTH"], 40, 4, 0.83, 15.5),
]

ADDITIONAL_SUPPLIERS = [
    ("SUP-009", "Odisha Mineral Mining", "RAW_MATERIAL", 0.88, 48, "LOW"),
    ("SUP-010", "NMDC Ltd", "RAW_MATERIAL", 0.95, 24, "LOW"),
    ("SUP-011", "Coal India Ltd", "RAW_MATERIAL", 0.82, 72, "MEDIUM"),
    ("SUP-012", "Hindalco Minerals", "RAW_MATERIAL", 0.91, 36, "LOW"),
    ("SUP-013", "Tata Power Solar", "UTILITY", 0.98, 12, "LOW"),
    ("SUP-014", "Adani Ports & SEZ", "LOGISTICS", 0.94, 24, "LOW"),
    ("SUP-015", "National Aluminium Co", "RAW_MATERIAL", 0.87, 48, "LOW"),
    ("SUP-016", "Vedanta Resources", "RAW_MATERIAL", 0.85, 48, "MEDIUM"),
    ("SUP-017", "South32 India", "RAW_MATERIAL", 0.80, 72, "HIGH"),
    ("SUP-018", "Kore Mining (Import)", "RAW_MATERIAL", 0.75, 168, "HIGH"),
    ("SUP-019", "ArcelorMittal Scrap", "RAW_MATERIAL", 0.88, 24, "MEDIUM"),
    ("SUP-020", "Refractory India Ltd", "CONSUMABLE", 0.90, 48, "LOW"),
    ("SUP-021", "Graphite India Ltd", "CONSUMABLE", 0.87, 72, "MEDIUM"),
    ("SUP-022", "HEG Ltd", "CONSUMABLE", 0.86, 72, "MEDIUM"),
    ("SUP-023", "IMC Ferro Alloys", "RAW_MATERIAL", 0.84, 48, "MEDIUM"),
    ("SUP-024", "Zinc India Corp", "RAW_MATERIAL", 0.91, 36, "LOW"),
    ("SUP-025", "Hindustan Zinc", "RAW_MATERIAL", 0.93, 24, "LOW"),
    ("SUP-026", "Indian Oil Lubricants", "CONSUMABLE", 0.96, 12, "LOW"),
    ("SUP-027", "Castrol India", "CONSUMABLE", 0.97, 12, "LOW"),
    ("SUP-028", "NTPC Power Supply", "UTILITY", 0.99, 1, "LOW"),
    ("SUP-029", "Tata Power Dist", "UTILITY", 0.97, 1, "LOW"),
    ("SUP-030", "Wabco India Rolls", "CONSUMABLE", 0.89, 96, "MEDIUM"),
    ("SUP-031", "Sandvik India", "CONSUMABLE", 0.88, 120, "MEDIUM"),
    ("SUP-032", "SKF Bearings India", "CONSUMABLE", 0.91, 48, "LOW"),
]

SCENARIO_TEMPLATES = [
    "TPL-001", "TPL-002", "TPL-003", "TPL-004", "TPL-005",
    "TPL-006", "TPL-007", "TPL-008", "TPL-009", "TPL-010",
    "TPL-011", "TPL-012", "TPL-013", "TPL-014", "TPL-015",
]

# Products eligible for orders (finished and semifinished)
ORDER_ELIGIBLE_PRODUCTS = [
    "PRD-HRC", "PRD-CRC", "PRD-REB", "PRD-PLT",
    "PRD-WIRE", "PRD-BEAM", "PRD-PIPE", "PRD-GALV",
    "PRD-SHEET", "PRD-ANGLE", "PRD-STRIP", "PRD-BILLET", "PRD-SLAB",
]


def _days_ago(n: int) -> datetime:
    return REF_DATE - timedelta(days=n)


def _days_from_now(n: int) -> datetime:
    return REF_DATE + timedelta(days=n)


# ──────────────────────────────────────────────────────────────────────────────
# Generators
# ──────────────────────────────────────────────────────────────────────────────

def gen_extra_products(rng: random.Random) -> List[Dict]:
    rows = []
    for pid, pname, pcat, uom, cost in EXTRA_PRODUCTS:
        rows.append({
            "product_id": pid,
            "product_name": pname,
            "product_category": pcat,
            "base_uom": uom,
            "reference_unit_cost_inr": cost,
            "status": "ACTIVE",
        })
    return rows


def gen_customers(rng: random.Random) -> List[Dict]:
    rows = []
    for cid, name, ctype, city, state, credit, terms, tier in CUSTOMERS:
        rows.append({
            "customer_id": cid,
            "customer_name": name,
            "customer_type": ctype,
            "city": city,
            "state": state,
            "country": "IN" if state else ("SG" if "SGP" in cid else "AE" if "UAE" in cid else "IN"),
            "credit_limit_inr": credit if credit > 0 else None,
            "payment_terms_days": terms,
            "tier": tier,
            "status": "ACTIVE",
        })
    return rows


def gen_carriers(rng: random.Random) -> List[Dict]:
    rows = []
    for cid, name, ctype, zones, maxload, transit, rate_otr, cost_km in CARRIERS:
        rows.append({
            "carrier_id": cid,
            "carrier_name": name,
            "carrier_type": ctype,
            "service_zones": zones,
            "max_load_mt": maxload,
            "avg_transit_days": transit,
            "on_time_rate": rate_otr,
            "cost_per_km_inr": cost_km,
            "status": "ACTIVE",
        })
    return rows


def gen_transport_lanes(rng: random.Random) -> List[Dict]:
    """Generate 60+ transport lanes between key steel belt cities."""
    origins = [
        ("Bhilai", "CG"), ("Raipur", "CG"), ("Jamshedpur", "JH"),
        ("Bokaro", "JH"), ("Durgapur", "WB"), ("Bhubaneswar", "OD"),
        ("Visakhapatnam", "AP"), ("Hazira", "GJ"),
    ]
    dests = [
        ("Mumbai", "MH"), ("Pune", "MH"), ("Chennai", "TN"),
        ("Hyderabad", "TS"), ("Bengaluru", "KA"), ("New Delhi", "DL"),
        ("Ahmedabad", "GJ"), ("Kolkata", "WB"), ("Jaipur", "RJ"),
        ("Nagpur", "MH"), ("Lucknow", "UP"), ("Bhopal", "MP"),
    ]
    mode_carrier = {
        "ROAD": ["CAR-002", "CAR-003", "CAR-005", "CAR-006", "CAR-010"],
        "RAIL": ["CAR-001", "CAR-007"],
        "SEA": ["CAR-004", "CAR-009"],
    }
    lanes = []
    lane_counter = 1
    for orig_city, orig_state in origins:
        for dest_city, dest_state in dests:
            if orig_city == dest_city:
                continue
            # Road lane
            dist = rng.randint(400, 2500)
            carrier = rng.choice(mode_carrier["ROAD"])
            transit_min = max(1, dist // 700)
            transit_max = transit_min + rng.randint(1, 3)
            lanes.append({
                "lane_id": f"LANE-{lane_counter:04d}",
                "origin_city": orig_city,
                "origin_state": orig_state,
                "dest_city": dest_city,
                "dest_state": dest_state,
                "carrier_id": carrier,
                "mode": "ROAD",
                "distance_km": dist,
                "transit_days_min": transit_min,
                "transit_days_max": transit_max,
                "freight_rate_inr_per_mt": round(dist * rng.uniform(14.0, 22.0), 2),
                "status": "ACTIVE",
            })
            lane_counter += 1
            # Add a rail lane for longer hauls
            if dist > 800 and rng.random() < 0.6:
                carrier = rng.choice(mode_carrier["RAIL"])
                lanes.append({
                    "lane_id": f"LANE-{lane_counter:04d}",
                    "origin_city": orig_city,
                    "origin_state": orig_state,
                    "dest_city": dest_city,
                    "dest_state": dest_state,
                    "carrier_id": carrier,
                    "mode": "RAIL",
                    "distance_km": dist,
                    "transit_days_min": transit_min + 1,
                    "transit_days_max": transit_max + 2,
                    "freight_rate_inr_per_mt": round(dist * rng.uniform(1.8, 2.8), 2),
                    "status": "ACTIVE",
                })
                lane_counter += 1
    return lanes


def gen_additional_suppliers(rng: random.Random) -> List[Dict]:
    rows = []
    for sid, name, cat, otr, lead_h, risk in ADDITIONAL_SUPPLIERS:
        rows.append({
            "supplier_id": sid,
            "supplier_name": name,
            "supplier_category": cat,
            "status": "ACTIVE",
            "risk_band": risk,
            "historical_on_time_rate": otr,
            "default_lead_time_hours": lead_h,
        })
    return rows


def gen_supplier_offers(rng: random.Random, all_product_ids: List[str]) -> List[Dict]:
    """Generate 150-250 supplier offers covering all order-eligible products."""
    offers = []
    # Existing suppliers
    supplier_ids = [f"SUP-{i:03d}" for i in range(1, 9)] + [s[0] for s in ADDITIONAL_SUPPLIERS]
    # Eligible products for offers
    offer_products = [p for p in all_product_ids if not p.startswith("MAT-ELEC")]
    
    offer_id_counter = 100
    # Ensure every order-eligible product has ≥3 offers (multi-source)
    for prod_id in ORDER_ELIGIBLE_PRODUCTS:
        n_offers = rng.randint(3, 8)
        sampled_suppliers = rng.sample(supplier_ids, min(n_offers, len(supplier_ids)))
        for sup_id in sampled_suppliers:
            base_cost = next((p[4] for p in EXTRA_PRODUCTS if p[0] == prod_id), 55000.0)
            price_per_mt = round(base_cost * rng.uniform(0.88, 1.15), 2)
            offers.append({
                "offer_id": f"SOFFER-{offer_id_counter}",
                "supplier_id": sup_id,
                "item_id": prod_id,
                "product_id": prod_id,
                "unit_price_inr": price_per_mt,
                "price_uom": "MT",
                "min_order_qty": round(rng.uniform(10, 100), 1),
                "max_order_qty": round(rng.uniform(500, 5000), 1),
                "max_available_qty": round(rng.uniform(500, 5000), 1),
                "lead_time_hours": rng.randint(24, 336),
                "on_time_rate": round(rng.uniform(0.85, 0.99), 3),
                "currency": "INR",
                "effective_from": _days_ago(180).date().isoformat(),
                "effective_to": _days_from_now(180).date().isoformat(),
                "valid_from": _days_ago(180).isoformat(),
                "valid_until": _days_from_now(180).isoformat(),
                "offer_status": "ACTIVE" if rng.random() < 0.9 else "EXPIRED",
                "status": "ACTIVE" if rng.random() < 0.9 else "EXPIRED",
            })
            offer_id_counter += 1

    return offers


def gen_bom_lines(rng: random.Random) -> List[Dict]:
    """Generate BOM entries for all finished/semifinished products."""
    bom = []
    bom_counter = 100
    finished_products = [p for p in ORDER_ELIGIBLE_PRODUCTS if p.startswith("PRD-")]
    raw_materials = ["MAT-IRON", "MAT-COAL", "MAT-LIME", "MAT-REFRACT", "MAT-ELECTRODE", "MAT-SCRAP", "MAT-ALLOY", "PRD-PELLET"]
    
    # Iron ore / pellet → all finished steel
    for fp in finished_products:
        if fp in ("PRD-HRC", "PRD-CRC", "PRD-PLT", "PRD-SHEET", "PRD-GALV", "PRD-STRIP", "PRD-WIRE", "PRD-BEAM", "PRD-ANGLE"):
            # BF-BOF route: iron ore + coal + limestone
            for mat, qty in [("MAT-IRON", 1.6), ("MAT-COAL", 0.65), ("MAT-LIME", 0.12), ("MAT-REFRACT", 0.003)]:
                bom.append({
                    "bom_line_id": f"BOM-{bom_counter}",
                    "bom_id": f"BOM-{bom_counter}",
                    "output_product_id": fp,
                    "product_id": fp,
                    "input_item_id": mat,
                    "component_id": mat,
                    "quantity_per_output_unit": round(qty * rng.uniform(0.95, 1.05), 4),
                    "quantity_per_unit": round(qty * rng.uniform(0.95, 1.05), 4),
                    "consumption_uom": "MT",
                    "uom": "MT",
                    "wastage_pct": round(rng.uniform(0.01, 0.05), 4),
                    "version_status": "ACTIVE",
                    "is_critical": mat in ("MAT-IRON", "MAT-COAL"),
                })
                bom_counter += 1
        elif fp in ("PRD-REB", "PRD-PIPE", "PRD-BILLET"):
            # EAF route: scrap + electrodes + alloys
            for mat, qty in [("MAT-SCRAP", 1.08), ("MAT-ELECTRODE", 0.004), ("MAT-ALLOY", 0.02)]:
                bom.append({
                    "bom_line_id": f"BOM-{bom_counter}",
                    "bom_id": f"BOM-{bom_counter}",
                    "output_product_id": fp,
                    "product_id": fp,
                    "input_item_id": mat,
                    "component_id": mat,
                    "quantity_per_output_unit": round(qty * rng.uniform(0.95, 1.05), 4),
                    "quantity_per_unit": round(qty * rng.uniform(0.95, 1.05), 4),
                    "consumption_uom": "MT",
                    "uom": "MT",
                    "wastage_pct": round(rng.uniform(0.01, 0.04), 4),
                    "version_status": "ACTIVE",
                    "is_critical": mat == "MAT-SCRAP",
                })
                bom_counter += 1
        elif fp == "PRD-GALV":
            bom.append({
                "bom_line_id": f"BOM-{bom_counter}",
                "bom_id": f"BOM-{bom_counter}",
                "output_product_id": fp,
                "product_id": fp,
                "input_item_id": "MAT-ZINC",
                "component_id": "MAT-ZINC",
                "quantity_per_output_unit": round(0.025 * rng.uniform(0.9, 1.1), 4),
                "quantity_per_unit": round(0.025 * rng.uniform(0.9, 1.1), 4),
                "consumption_uom": "MT",
                "uom": "MT",
                "wastage_pct": 0.02,
                "version_status": "ACTIVE",
                "is_critical": True,
            })
            bom_counter += 1
    return bom


def _order_id(n: int) -> str:
    return f"ORD-{n + 2000}"


def gen_orders_and_lines(rng: random.Random) -> Tuple[List[Dict], List[Dict]]:
    """Generate 1,500–2,000 orders with 1–6 multi-line items each."""
    customer_ids = [c[0] for c in CUSTOMERS]
    entity_ids = ["EAS-HQ", "EAS-EAST", "EAS-PORT", "EAS-WEST"]  # Valid entities from seed
    statuses_dist = [
        ("OPEN", 0.30), ("IN_PROGRESS", 0.25), ("AT_RISK", 0.15),
        ("COMPLETED", 0.25), ("CANCELLED", 0.05),
    ]
    priorities_dist = [("LOW", 0.15), ("MEDIUM", 0.45), ("HIGH", 0.30), ("CRITICAL", 0.10)]
    
    def _pick(dist):
        r = rng.random()
        cumul = 0
        for val, p in dist:
            cumul += p
            if r < cumul:
                return val
        return dist[-1][0]

    orders = []
    lines = []
    n_orders = rng.randint(1500, 2000)
    line_counter = 2001

    for i in range(n_orders):
        order_date_offset = rng.randint(0, 365)
        order_date = _days_ago(order_date_offset)
        status = _pick(statuses_dist)
        priority = _pick(priorities_dist)
        customer_id = rng.choice(customer_ids)
        entity_id = rng.choice(entity_ids)
        delivery_days = rng.randint(7, 60)

        currency = "INR" if rng.random() < 0.88 else ("USD" if rng.random() < 0.7 else "EUR")
        
        # Multi-line: Pareto distribution (1 line = 35%, 2 = 30%, 3 = 20%, 4 = 10%, 5+ = 5%)
        n_lines_weights = [35, 30, 20, 10, 5]
        n_lines = rng.choices([1, 2, 3, 4, rng.randint(5, 6)], weights=n_lines_weights)[0]
        products_for_order = rng.sample(ORDER_ELIGIBLE_PRODUCTS, min(n_lines, len(ORDER_ELIGIBLE_PRODUCTS)))

        order_id = _order_id(i)
        orders.append({
            "order_id": order_id,
            "customer_ref": customer_id,
            "entity_id": entity_id,
            "status": status,
            "priority": priority,
            "currency": currency,
            "external_reference": f"EXT-{order_id}" if rng.random() < 0.4 else None,
            "created_at": order_date.isoformat(),
            "required_delivery_at": _days_from_now(delivery_days).isoformat() if status not in ("COMPLETED", "CANCELLED") else None,
            "notes": None,
            "customer_id": customer_id,
        })

        for prod_id in products_for_order:
            qty = round(rng.uniform(10, 500), 2)
            base_cost = next((p[4] for p in EXTRA_PRODUCTS if p[0] == prod_id), 58000.0)
            unit_price = round(base_cost * rng.uniform(0.92, 1.12), 2)
            lines.append({
                "order_line_id": f"LINE-{line_counter}",
                "line_id": f"LINE-{line_counter}",
                "order_id": order_id,
                "product_id": prod_id,
                "requested_qty": qty,
                "quantity": qty,
                "unit_price_inr": unit_price,
                "total_price_inr": round(qty * unit_price, 2),
                "uom": "MT",
                "line_status": status,
                "notes": None,
            })
            line_counter += 1

    return orders, lines


# ──────────────────────────────────────────────────────────────────────────────
# Database loading
# ──────────────────────────────────────────────────────────────────────────────

def _batch_insert(conn, table: str, rows: List[Dict], key_col: str, on_conflict: str = "DO NOTHING") -> int:
    """Insert rows in batches, skipping existing keys. Returns insert count."""
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT ({key_col}) {on_conflict}"
    
    inserted = 0
    batch_size = 500
    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            values = [tuple(r[c] for c in cols) for r in batch]
            cur.executemany(sql, values)
            inserted += cur.rowcount if cur.rowcount >= 0 else len(batch)
    conn.commit()
    return inserted


def _check_preserved_rows(conn) -> Dict[str, int]:
    """Return counts of critical seed data that must be preserved."""
    counts = {}
    with conn.cursor() as cur:
        for table in ("orders", "order_lines", "supplier_offers", "bill_of_materials",
                      "event_log", "scenario_instances", "products", "suppliers"):
            try:
                cur.execute(f"SELECT count(*) FROM {table};")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = -1
    return counts


def load_all(conn, dry_run: bool = False) -> Dict[str, int]:
    """Load all synthetic data into the target database."""
    rng = _rng()
    results: Dict[str, int] = {}

    baseline = _check_preserved_rows(conn)
    logger.info("Baseline rows before generation: %s", baseline)

    # 1. Extra products
    products = gen_extra_products(rng)
    logger.info("Generated %d extra products", len(products))
    if not dry_run:
        n = _batch_insert(conn, "products", products, "product_id")
        results["products_inserted"] = n

    # 2. Customers
    customers = gen_customers(rng)
    logger.info("Generated %d customers", len(customers))
    if not dry_run:
        n = _batch_insert(conn, "customers", customers, "customer_id")
        results["customers_inserted"] = n

    # 3. Carriers
    carriers = gen_carriers(rng)
    logger.info("Generated %d carriers", len(carriers))
    if not dry_run:
        n = _batch_insert(conn, "carriers", carriers, "carrier_id")
        results["carriers_inserted"] = n

    # 4. Transport lanes
    lanes = gen_transport_lanes(rng)
    logger.info("Generated %d transport lanes", len(lanes))
    if not dry_run:
        n = _batch_insert(conn, "transport_lanes", lanes, "lane_id")
        results["lanes_inserted"] = n

    # 5. Additional suppliers
    extra_suppliers = gen_additional_suppliers(rng)
    logger.info("Generated %d additional suppliers", len(extra_suppliers))
    if not dry_run:
        n = _batch_insert(conn, "suppliers", extra_suppliers, "supplier_id")
        results["suppliers_inserted"] = n

    # Fetch all product IDs now (original + new)
    all_product_ids = [p["product_id"] for p in products]
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT product_id FROM products;")
            all_product_ids = [r[0] for r in cur.fetchall()]
    except Exception:
        pass

    # 6. Supplier offers
    offers = gen_supplier_offers(rng, all_product_ids)
    logger.info("Generated %d supplier offers", len(offers))
    if not dry_run:
        # supplier_offers table check columns
        with conn.cursor() as cur:
            cur.execute("""SELECT column_name FROM information_schema.columns
                          WHERE table_name = 'supplier_offers'""")
            offer_cols = {r[0] for r in cur.fetchall()}
        filtered = []
        for o in offers:
            filtered.append({k: v for k, v in o.items() if k in offer_cols})
        if filtered:
            n = _batch_insert(conn, "supplier_offers", filtered, "offer_id")
            results["supplier_offers_inserted"] = n

    # 7. BOM lines
    bom_rows = gen_bom_lines(rng)
    logger.info("Generated %d BOM lines", len(bom_rows))
    if not dry_run:
        with conn.cursor() as cur:
            cur.execute("""SELECT column_name FROM information_schema.columns
                          WHERE table_name = 'bill_of_materials'""")
            bom_cols = {r[0] for r in cur.fetchall()}
        filtered_bom = [{k: v for k, v in b.items() if k in bom_cols} for b in bom_rows]
        if filtered_bom:
            n = _batch_insert(conn, "bill_of_materials", filtered_bom, "bom_line_id")
            results["bom_inserted"] = n

    # 8. Orders + order_lines (NEW orders; preserve existing 200)
    orders, lines = gen_orders_and_lines(rng)
    logger.info("Generated %d new orders with %d lines", len(orders), len(lines))
    if not dry_run:
        with conn.cursor() as cur:
            cur.execute("""SELECT column_name FROM information_schema.columns
                          WHERE table_name = 'orders'""")
            order_cols = {r[0] for r in cur.fetchall()}
        filtered_orders = [{k: v for k, v in o.items() if k in order_cols} for o in orders]
        n_ord = _batch_insert(conn, "orders", filtered_orders, "order_id")
        results["orders_inserted"] = n_ord

        with conn.cursor() as cur:
            cur.execute("""SELECT column_name FROM information_schema.columns
                          WHERE table_name = 'order_lines'""")
            line_cols = {r[0] for r in cur.fetchall()}
        filtered_lines = [{k: v for k, v in l.items() if k in line_cols} for l in lines]
        n_lines = _batch_insert(conn, "order_lines", filtered_lines, "order_line_id")
        results["order_lines_inserted"] = n_lines

    # Verify preservation
    after = _check_preserved_rows(conn)
    logger.info("After-generation rows: %s", after)
    for table, before_count in baseline.items():
        if before_count >= 0 and after.get(table, 0) < before_count:
            logger.error("PRESERVATION VIOLATION: %s had %d rows, now %d", table, before_count, after[table])
            raise RuntimeError(f"Row preservation violated for {table}")

    results["baseline"] = baseline
    results["after"] = after
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Synthetic Data Generator v3")
    parser.add_argument("--target", default="TEST_DATABASE_URL",
                        help="Env var holding the target PostgreSQL URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate data without loading to DB")
    parser.add_argument("--output-dir", default=None,
                        help="Directory to write JSON manifests (optional)")
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND_DIR / "db"))
    from connection import load_project_env, connect
    load_project_env()

    if args.dry_run:
        logger.info("=== DRY RUN MODE: No database writes will occur ===")
        rng = _rng()
        products = gen_extra_products(rng)
        customers = gen_customers(rng)
        carriers = gen_carriers(rng)
        lanes = gen_transport_lanes(rng)
        suppliers = gen_additional_suppliers(rng)
        bom = gen_bom_lines(rng)
        orders, lines = gen_orders_and_lines(rng)
        logger.info("Would insert: %d products, %d customers, %d carriers, %d lanes",
                    len(products), len(customers), len(carriers), len(lanes))
        logger.info("Would insert: %d suppliers, %d BOM lines", len(suppliers), len(bom))
        logger.info("Would insert: %d orders, %d order lines", len(orders), len(lines))
        return 0

    conn = connect(args.target)
    try:
        results = load_all(conn)
        logger.info("=== SYNTHETIC DATA GENERATION COMPLETE ===")
        for k, v in results.items():
            if not isinstance(v, dict):
                logger.info("  %s: %s", k, v)
        return 0
    except Exception as exc:
        logger.error("Generation failed: %s", exc)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
