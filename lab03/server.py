"""Lab 3, Step 2 + 4: the pharmacy MCP server.

Exposes three read tools (percepts) and one write tool (an actuator):

    check_stock(item, strength)   read   stock rows for one medicine
    search_items(query)           read   free-text search across the stock list
    list_expiring(days)           read   rows expiring within `days` days
    record_sale(item, strength, qty)  write  reduces the quantity in the CSV

The model never executes anything: it asks, and this server does the work.
Because record_sale changes the world, it validates every argument and
refuses bad input with a message the model can relay to the user.

Run it from inside lab03/:
    python server.py

Test it with the Inspector:
    npx @modelcontextprotocol/inspector python server.py
"""

import csv
import os
import tempfile
import threading
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).resolve().parent / "data" / "pharmacy_stock.csv"
FIELDS = ["item", "strength", "form", "quantity", "unit_price_ghs", "expiry_date"]

mcp = FastMCP("pharmacy-stock")

# Two concurrent write calls must not read-modify-write the same CSV at once.
_WRITE_LOCK = threading.Lock()


# --- Storage -------------------------------------------------------------
def load() -> list[dict]:
    """Read every stock row."""
    with open(DATA, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    """Replace the CSV atomically, so a crash cannot leave it half-written."""
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8",
                                     dir=DATA.parent, delete=False) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        tmp_path = tmp.name
    os.replace(tmp_path, DATA)


def match(rows: list[dict], item: str, strength: str = "") -> list[dict]:
    item = (item or "").strip().lower()
    strength = (strength or "").strip().lower()
    hits = [r for r in rows if item and item in r["item"].lower()]
    if strength:
        hits = [r for r in hits if strength in r["strength"].lower()]
    return hits


def days_to_expiry(row: dict) -> int:
    return (date.fromisoformat(row["expiry_date"]) - date.today()).days


# --- Read tools (percepts) ----------------------------------------------
@mcp.tool()
def check_stock(item: str, strength: str = "") -> list[dict]:
    """Return stock rows for one medicine whose name contains `item` and whose
    strength contains `strength` when it is given.

    `item` must be the medicine name only (e.g. 'paracetamol', 'amoxicillin'),
    not the form. Use search_items for form words such as 'syrup', 'cream' or
    'inhaler' and for partial names. An empty list means we do not stock it.
    """
    return match(load(), item, strength)


@mcp.tool()
def search_items(query: str) -> list[dict]:
    """Free-text search across medicine name, strength and form. The words in
    `query` may be split across those fields, so 'paracetamol syrup' and
    'amoxicillin 500mg capsules' both work. Use it for form words ('syrup',
    'cream', 'inhaler'), a partial name, or when you are not sure of the exact
    medicine. Do not use it for availability questions about a known medicine;
    check_stock is exact."""
    words = [w for w in (query or "").lower().split() if w]
    if not words:
        return []
    hits = []
    for r in load():
        haystack = " ".join((r["item"], r["strength"], r["form"])).lower()
        if all(w in haystack for w in words):
            hits.append(r)
    return hits


@mcp.tool()
def list_expiring(days: int = 60) -> list[dict]:
    """Return stock rows that expire within `days` days from today, soonest
    first, with a `days_left` field. Rows already out of date have a negative
    `days_left`. Use for 'which items expire soon?' questions."""
    if days < 0:
        return []
    rows = []
    for r in load():
        left = days_to_expiry(r)
        if left <= days:
            rows.append({**r, "days_left": left})
    rows.sort(key=lambda r: r["days_left"])
    return rows


# --- Write tool (an actuator) -------------------------------------------
@mcp.tool()
def record_sale(item: str, strength: str, qty: int) -> dict:
    """Record that `qty` packs of `item` at `strength` were sold and reduce the
    quantity in stock. Refuses a non-positive quantity, an unknown or ambiguous
    item, an expired batch and any oversale. Give the strength whenever more
    than one strength of the medicine is stocked. Returns a message to relay."""
    # Never trust the model's arguments: check them here, not in the prompt.
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return {"ok": False, "message": "Refused: quantity must be a whole number."}
    if qty <= 0:
        return {"ok": False,
                "message": f"Refused: quantity must be positive, got {qty}."}

    with _WRITE_LOCK:
        rows = load()
        hits = match(rows, item, strength)
        if not hits:
            hint = f" with strength '{strength}'" if strength else ""
            return {"ok": False,
                    "message": f"Refused: no stock item named '{item}'{hint}."}
        if len(hits) > 1:
            options = ", ".join(f"{r['item']} {r['strength']}" for r in hits)
            return {"ok": False,
                    "message": f"Refused: '{item}' matches several strengths "
                               f"({options}). Call again with the strength."}

        row = hits[0]
        on_hand = int(row["quantity"])
        if on_hand < qty:
            return {"ok": False,
                    "message": f"Refused: oversale. Only {on_hand} packs of "
                               f"{row['item']} {row['strength']} are in stock, "
                               f"not {qty}."}
        if days_to_expiry(row) < 0:
            return {"ok": False,
                    "message": f"Refused: the {row['item']} {row['strength']} "
                               f"batch expired on {row['expiry_date']} and must "
                               f"not be sold."}

        row["quantity"] = str(on_hand - qty)
        save(rows)
        total = round(float(row["unit_price_ghs"]) * qty, 2)

    return {
        "ok": True,
        "message": f"Sold {qty} x {row['item']} {row['strength']} "
                   f"({row['form']}) for GHS {total:.2f}. "
                   f"{row['quantity']} packs left.",
        "item": row["item"],
        "strength": row["strength"],
        "qty_sold": qty,
        "quantity_left": int(row["quantity"]),
        "total_ghs": total,
    }


if __name__ == "__main__":
    mcp.run()
