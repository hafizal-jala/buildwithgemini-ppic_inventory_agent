# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Optional, List, Dict, Any
from google.cloud import firestore
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-03-bb958ae685da"
LOCATION = "us-east1"
MEMORY_BANK_ID = "7655814801808949248"
SANDBOX_RESOURCE = "projects/376929194509/locations/us-east1/reasoningEngines/7655814801808949248/sandboxEnvironments/8296971917802340352"
MODEL = "gemini-3.8-flash"

# Lazy-init Firestore client with hardcoded project ID
_db = None

def get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_all_components() -> str:
    """Lists all electronic components in the inventory with their SKU, name, quantity, safety stock threshold, and bin location.
    
    Returns:
        A formatted summary string of all registered components.
    """
    db = get_db()
    docs = db.collection("components").stream()
    items = []
    for doc in docs:
        d = doc.to_dict()
        qty = d.get("quantity", 0)
        min_stock = d.get("min_safety_stock", 0)
        warning = " ⚠️ LOW STOCK" if qty <= min_stock else ""
        items.append(
            f"- SKU: {d.get('sku')} | Name: {d.get('name')} | Category: {d.get('category')} | Qty: {qty} {d.get('unit', 'pcs')} (Min: {min_stock}){warning} | Bin: {d.get('location')}"
        )
    if not items:
        return "No components found in inventory."
    return "\n".join(items)


def search_components(query: str) -> str:
    """Searches electronic components in inventory by SKU, name, category, or package type.
    
    Args:
        query: Search term (e.g., 'ESP32', 'resistor', 'Microcontroller', 'SOT-223').
        
    Returns:
        A list of matching components with details.
    """
    db = get_db()
    query_lower = query.lower()
    docs = db.collection("components").stream()
    matches = []
    for doc in docs:
        d = doc.to_dict()
        sku = d.get("sku", "")
        name = d.get("name", "")
        cat = d.get("category", "")
        pkg = d.get("package", "")
        
        if (query_lower in sku.lower() or 
            query_lower in name.lower() or 
            query_lower in cat.lower() or 
            query_lower in pkg.lower()):
            qty = d.get("quantity", 0)
            min_stock = d.get("min_safety_stock", 0)
            warning = " ⚠️ LOW STOCK" if qty <= min_stock else ""
            matches.append(
                f"- SKU: {sku}\n"
                f"  Name: {name}\n"
                f"  Category: {cat} | Package: {pkg}\n"
                f"  Quantity: {qty} {d.get('unit', 'pcs')} (Safety Stock: {min_stock}){warning}\n"
                f"  Location: {d.get('location')}\n"
                f"  Price: ${d.get('unit_price_usd', 0):.3f} | Supplier: {d.get('supplier', 'N/A')}"
            )
            
    if not matches:
        return f"No components found matching '{query}'."
    return "\n\n".join(matches)


def record_component_movement(
    sku: str,
    movement_type: str,
    quantity: int,
    reference_number: str = "N/A",
    notes: str = ""
) -> str:
    """Records an incoming (IN / receiving) or outgoing (OUT / production requisition) electronic component movement, and updates stock.
    
    Args:
        sku: Component SKU identifier (e.g. 'IC-ESP32-WROOM32D', 'REG-AMS1117-3.3').
        movement_type: Either 'IN' (stock received) or 'OUT' (stock issued to production/project).
        quantity: Positive integer representing how many units moved.
        reference_number: Purchase order (PO) or Work Order (WO) number.
        notes: Reason, destination, or remarks for the movement.
        
    Returns:
        A status message indicating the new stock balance and movement log entry.
    """
    if quantity <= 0:
        return "Error: Quantity must be greater than zero."
        
    movement_type_upper = movement_type.strip().upper()
    if movement_type_upper not in ["IN", "OUT"]:
        return "Error: movement_type must be either 'IN' or 'OUT'."
        
    db = get_db()
    doc_ref = db.collection("components").document(sku)
    doc = doc_ref.get()
    
    if not doc.exists:
        return f"Error: Component with SKU '{sku}' not found in inventory."
        
    data = doc.to_dict()
    current_qty = data.get("quantity", 0)
    min_safety = data.get("min_safety_stock", 0)
    
    if movement_type_upper == "OUT" and current_qty < quantity:
        return f"Error: Insufficient stock. Current stock is {current_qty}, cannot issue {quantity} units."
        
    new_qty = current_qty + quantity if movement_type_upper == "IN" else current_qty - quantity
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Update component stock in Firestore
    doc_ref.update({
        "quantity": new_qty,
        "last_updated": now_str,
    })
    
    # Record movement transaction log
    movement_log = {
        "sku": sku,
        "component_name": data.get("name"),
        "type": movement_type_upper,
        "quantity": quantity,
        "previous_quantity": current_qty,
        "new_quantity": new_qty,
        "reference_number": reference_number,
        "notes": notes,
        "timestamp": now_str,
    }
    db.collection("inventory_movements").add(movement_log)
    
    alert = ""
    if new_qty <= min_safety:
        alert = f"\n⚠️ WARNING: Stock ({new_qty}) is at or below safety stock threshold ({min_safety})! Consider creating a reorder."
        
    return (
        f"✓ Movement recorded successfully:\n"
        f"- SKU: {sku} ({data.get('name')})\n"
        f"- Type: {movement_type_upper} {quantity} {data.get('unit', 'pcs')}\n"
        f"- Reference: {reference_number}\n"
        f"- Previous Stock: {current_qty} -> New Stock: {new_qty}{alert}"
    )


def get_low_stock_alerts() -> str:
    """Checks all components and returns those with stock at or below minimum safety stock threshold.
    
    Returns:
        List of components requiring reordering.
    """
    db = get_db()
    docs = db.collection("components").stream()
    low_stock = []
    for doc in docs:
        d = doc.to_dict()
        qty = d.get("quantity", 0)
        min_stock = d.get("min_safety_stock", 0)
        if qty <= min_stock:
            deficit = min_stock - qty
            low_stock.append(
                f"- SKU: {d.get('sku')} | {d.get('name')}\n"
                f"  Current Stock: {qty} {d.get('unit', 'pcs')} | Safety Threshold: {min_stock} (Deficit: {deficit})\n"
                f"  Supplier: {d.get('supplier', 'N/A')} | Est. Unit Price: ${d.get('unit_price_usd', 0):.3f}"
            )
            
    if not low_stock:
        return "All component stocks are healthy above minimum safety thresholds."
def requisition_production_kit(
    engineer_name: str,
    work_order: str,
    items_json: str,
    notes: str = ""
) -> str:
    """Issues and deducts multiple electronic components for a production engineer/work order, and provides a picking list with bin locations.

    Args:
        engineer_name: Name of the production engineer requesting the parts.
        work_order: Work order number or project identifier (e.g., 'WO-2026-08').
        items_json: JSON string representing a list of requested items, e.g. '[{"sku": "IC-ESP32-WROOM32D", "quantity": 10}, {"sku": "REG-AMS1117-3.3", "quantity": 10}]'.
        notes: Purpose or additional remarks for the requisition.

    Returns:
        A formatted picking list with bin locations, deducted quantities, remaining stock, and any low stock warnings.
    """
    import json
    try:
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
        if not isinstance(items, list) or not items:
            return "Error: items must be a non-empty list of items with 'sku' and 'quantity'."
    except Exception as e:
        return f"Error parsing items_json: {e}. Expected format: '[{{\"sku\": \"...\", \"quantity\": 10}}]'"

    db = get_db()
    # Step 1: Validate stock for all items first
    validation_errors = []
    comp_docs = {}
    for item in items:
        sku = item.get("sku")
        qty = item.get("quantity", 0)
        if not sku or qty <= 0:
            validation_errors.append(f"Invalid entry: SKU '{sku}' with quantity {qty}")
            continue
        
        doc_ref = db.collection("components").document(sku)
        doc = doc_ref.get()
        if not doc.exists:
            validation_errors.append(f"SKU '{sku}' not found in inventory.")
            continue
        
        data = doc.to_dict()
        comp_docs[sku] = (doc_ref, data)
        current_qty = data.get("quantity", 0)
        if current_qty < qty:
            validation_errors.append(f"Insufficient stock for {sku} ({data.get('name')}): Requested {qty}, Available {current_qty}")

    if validation_errors:
        return "❌ Requisition aborted due to errors:\n" + "\n".join(f"- {err}" for err in validation_errors)

    # Step 2: Deduct stock and log movements
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    picking_lines = []
    alerts = []

    for item in items:
        sku = item.get("sku")
        qty = item.get("quantity")
        doc_ref, data = comp_docs[sku]
        current_qty = data.get("quantity", 0)
        min_safety = data.get("min_safety_stock", 0)
        new_qty = current_qty - qty

        # Update stock
        doc_ref.update({
            "quantity": new_qty,
            "last_updated": now_str,
        })

        # Log movement
        db.collection("inventory_movements").add({
            "sku": sku,
            "component_name": data.get("name"),
            "type": "OUT",
            "quantity": qty,
            "previous_quantity": current_qty,
            "new_quantity": new_qty,
            "reference_number": work_order,
            "engineer_name": engineer_name,
            "notes": notes,
            "timestamp": now_str,
        })

        location = data.get("location", "Unknown Location")
        picking_lines.append(
            f"📍 {location} -> Take {qty} {data.get('unit', 'pcs')} of {data.get('name')} (SKU: {sku}) | Remaining: {new_qty}"
        )

        if new_qty <= min_safety:
            alerts.append(f"⚠️ {sku} stock is now {new_qty} (below safety limit of {min_safety})")

    result = [
        f"✅ Production Kit Requisition Issued for {engineer_name} [{work_order}]",
        "\n📦 Picking List (Warehouse Locations):",
    ] + [f"- {line}" for line in picking_lines]

    if alerts:
        result.append("\n🚨 PPIC Safety Stock Alerts:")
        result.extend([f"- {a}" for a in alerts])

    return "\n".join(result)


def get_currency_exchange_rates(base_currency: str = "USD") -> str:
    """Fetches real-time foreign exchange rates (e.g., USD to IDR, CNY, EUR, JPY) to estimate procurement and BOM costs from international component suppliers.

    Args:
        base_currency: The base currency code (defaults to 'USD').

    Returns:
        A formatted string with key exchange rates.
    """
    import urllib.request
    import json
    
    base_clean = base_currency.strip().upper() or "USD"
    url = f"https://open.er-api.com/v6/latest/{base_clean}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PPIC-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            
        if data.get("result") != "success":
            return f"Error: Unable to fetch rates for {base_clean}."
            
        rates = data.get("rates", {})
        idr = rates.get("IDR", 0)
        cny = rates.get("CNY", 0)
        eur = rates.get("EUR", 0)
        jpy = rates.get("JPY", 0)
        sgd = rates.get("SGD", 0)
        
        return (
            f"💱 Real-time Exchange Rates (Base: 1 {base_clean}):\n"
            f"- Indonesian Rupiah (IDR): Rp {idr:,.2f}\n"
            f"- Chinese Yuan (CNY): ¥ {cny:.4f}\n"
            f"- Euro (EUR): € {eur:.4f}\n"
            f"- Japanese Yen (JPY): ¥ {jpy:.2f}\n"
            f"- Singapore Dollar (SGD): S$ {sgd:.4f}\n"
            f"(Source: ExchangeRate-API / Public Forex Rates)"
        )
    except Exception as e:
        return f"Error fetching exchange rates: {e}"


async def generate_component_image(
    sku_or_name: str,
    visual_description: str,
    tool_context: ToolContext,
) -> str:
    """Generates a technical visual/diagram for an electronic component or warehouse bin layout, saves it as an artifact in Playground, uploads it to public Cloud Storage, and returns the public image URL.

    Args:
        sku_or_name: The SKU or component name (e.g., 'IC-ESP32-WROOM32D', 'AMS1117-3.3').
        visual_description: Description of the visual (e.g., 'Pinout diagram of ESP32 chip module showing GPIO pins', 'Warehouse bin placement map for Rack A1').

    Returns:
        The public HTTPS URL of the uploaded image along with artifact confirmation.
    """
    import os
    import re
    import time
    from google import genai
    from google.genai import types as genai_types
    from google.cloud import storage

    BUCKET_NAME = "ppic-inventory-assets-qwiklabs-gcp-03-bb958ae685da"
    
    # Clean SKU for filename
    clean_sku = re.sub(r"[^a-zA-Z0-9_\-]", "_", sku_or_name).lower()
    filename = f"{clean_sku}_{int(time.time())}.jpg"
    
    prompt = (
        f"Professional electronic component visual: {sku_or_name}. "
        f"{visual_description}. "
        f"Clean engineering schematic or component photography style, crisp details, high contrast."
    )
    
    # 1. Generate image using gemini-3.1-flash-lite-image in global location
    client = genai.Client(http_options={"api_version": "v1"})
    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
    )
    
    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break
                
    if not image_bytes:
        return f"Error: No image was generated by gemini-3.1-flash-lite-image for '{sku_or_name}'."

    # 2. Save artifact to Playground UI
    artifact_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    try:
        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part,
            custom_metadata={"sku": sku_or_name, "model": "gemini-3.1-flash-lite-image"}
        )
    except Exception as e:
        print(f"Warning: Failed to save session artifact: {e}")

    # 3. Upload image bytes directly to Public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    
    return (
        f"🖼️ Generated Component Visual for **{sku_or_name}**:\n\n"
        f"Public Image URL: {public_url}\n\n"
        f"![{sku_or_name}]({public_url})\n\n"
        f"Artifact saved: `{filename}`"
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback executed after each agent turn to send conversation facts to Vertex AI Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE,
    ),
    instruction=(
        "You are an expert PPIC (Production Planning and Inventory Control) AI Assistant "
        "specializing in electronic components management. You help the factory team track stock, "
        "log incoming components (PO/receiving), assist production engineers with material requisitions and picking lists, "
        "generate component diagrams and packaging visuals, convert import component prices using live forex rates, "
        "perform complex mathematical calculations via secure sandbox Python code execution, "
        "and monitor safety stock levels to prevent assembly line shortages.\n\n"
        "You remember user preferences, recurring suppliers, common project names, and engineer roles across sessions.\n\n"
        "Always provide clear, structured information. When stock falls below safety threshold, "
        "alert the user immediately."
    ),
    tools=[
        PreloadMemoryTool(),
        list_all_components,
        search_components,
        record_component_movement,
        requisition_production_kit,
        get_low_stock_alerts,
        get_currency_exchange_rates,
        generate_component_image,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
    memory_service=VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    ),
)
