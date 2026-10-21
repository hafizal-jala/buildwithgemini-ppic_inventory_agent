# My agent: ppic-inventory-agent
One-liner: A conversational agent that helps production and inventory teams track in/out logs, monitor stock levels, and plan electronic component orders with a catalog of electronic parts.

Tool coverage:
- Memory: Remembers recurring suppliers, minimum safety stock rules, frequently requested parts, and project BOM preferences across sessions.
- Tools: Log in/out transactions (record_component_movement), check real-time stock and reorder thresholds (get_stock_status), and search component catalog (search_components).
- Catalog/UI: Inventory parts table and transaction history cards (SKU, component name, specs, current stock, threshold, bin location).
- Image gen: Generates component package/pinout diagrams or warehouse bin layout visual references.
- Sandbox: Computes Bill of Materials (BOM) cost calculations, safety stock deficit estimates, and lead-time projections.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): code sandbox for BOM and inventory calculations, Cloud Trace
