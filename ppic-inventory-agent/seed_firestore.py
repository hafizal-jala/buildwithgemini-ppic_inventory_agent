"""Seed script for PPIC Electronic Component Inventory in Firestore."""
import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-bb958ae685da"
db = firestore.Client(project=PROJECT_ID)

COMPONENTS = [
    {
        "sku": "IC-ESP32-WROOM32D",
        "name": "ESP32-WROOM-32D Wi-Fi & BT MCU Module",
        "category": "Microcontroller",
        "package": "SMD-38",
        "quantity": 150,
        "min_safety_stock": 50,
        "unit": "pcs",
        "location": "Rack-A1-Bin03",
        "unit_price_usd": 2.85,
        "supplier": "Espressif Direct",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "sku": "IC-STM32F401CCU6",
        "name": "STM32F401CCU6 ARM Cortex-M4 MCU 84MHz",
        "category": "Microcontroller",
        "package": "UFQFPN-48",
        "quantity": 30,
        "min_safety_stock": 40,  # Below threshold
        "unit": "pcs",
        "location": "Rack-A1-Bin05",
        "unit_price_usd": 3.40,
        "supplier": "STMicroelectronics Authorized",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "sku": "REG-AMS1117-3.3",
        "name": "AMS1117-3.3V 1A LDO Voltage Regulator",
        "category": "Power IC",
        "package": "SOT-223",
        "quantity": 500,
        "min_safety_stock": 100,
        "unit": "pcs",
        "location": "Rack-B2-Bin12",
        "unit_price_usd": 0.15,
        "supplier": "Advanced Monolithic Systems",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "sku": "RES-0805-10K",
        "name": "10k Ohm 1% 1/8W SMD Resistor 0805",
        "category": "Passive",
        "package": "0805",
        "quantity": 2500,
        "min_safety_stock": 500,
        "unit": "pcs",
        "location": "Rack-C3-Reel01",
        "unit_price_usd": 0.008,
        "supplier": "Yageo Distributor",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "sku": "CAP-0805-100NF",
        "name": "100nF (0.1uF) 50V X7R Ceramic Capacitor 0805",
        "category": "Passive",
        "package": "0805",
        "quantity": 1800,
        "min_safety_stock": 500,
        "unit": "pcs",
        "location": "Rack-C3-Reel04",
        "unit_price_usd": 0.012,
        "supplier": "Murata Electronics",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "sku": "IC-CH340C",
        "name": "CH340C USB to Serial Converter IC (Built-in Crystal)",
        "category": "Interface IC",
        "package": "SOP-16",
        "quantity": 12,
        "min_safety_stock": 25,  # Below threshold
        "unit": "pcs",
        "location": "Rack-B1-Bin02",
        "unit_price_usd": 0.65,
        "supplier": "WCH Authorized",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
]

def seed():
    print(f"Seeding components into Firestore project '{PROJECT_ID}'...")
    collection_ref = db.collection("components")
    for comp in COMPONENTS:
        sku = comp["sku"]
        collection_ref.document(sku).set(comp)
        print(f"  ✓ Seeded component: {sku} ({comp['name']})")
    print(f"Successfully seeded {len(COMPONENTS)} components!")

if __name__ == "__main__":
    seed()
