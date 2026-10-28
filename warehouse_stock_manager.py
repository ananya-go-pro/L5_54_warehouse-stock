"""Warehouse stock manager: receive, issue, report and adjust stock."""

import ast
import hashlib
import hmac
import json
import logging
import operator
import os
from datetime import datetime

AUDIT_FILE = "warehouse_audit.log"
LOGGER = logging.getLogger(__name__)

WAREHOUSE_STOCK = {}

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_NUM = (int, float)

def safe_eval(formula, current):
    """Evaluate simple arithmetic using only numbers and 'current'."""

    def _ev(node):
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, _NUM):
            return node.value
        if isinstance(node, ast.Name) and node.id == "current":
            return current
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_ev(node.left), _ev(node.right))
        raise ValueError("Unsupported formula")

    try:
        return _ev(ast.parse(formula, mode="eval"))
    except (SyntaxError, ZeroDivisionError) as err:
        raise ValueError(f"Invalid formula: {formula!r}") from err

def _is_authorized(password):
    """Compare password with the SUPERVISOR_PASSWORD env variable."""
    expected = os.environ.get("SUPERVISOR_PASSWORD")
    if not expected:
        return False
    return hmac.compare_digest(
        str(password).encode("utf-8"), expected.encode("utf-8")
    )

def add_stock(sku, qty, history=None):
    """Receive qty units of sku. Rejects invalid SKUs and quantities."""
    if history is None:
        history = []
    if not isinstance(sku, str) or not sku:
        raise ValueError(f"Invalid SKU: {sku!r}")
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty!r}")
    WAREHOUSE_STOCK[sku] = WAREHOUSE_STOCK.get(sku, 0) + qty
    history.append(f"{datetime.now()}: Received {qty} units of {sku}")
    return history

def remove_stock(sku, qty):
    """Issue qty units of sku. Rejects unknown SKUs and oversell."""
    if sku not in WAREHOUSE_STOCK:
        raise ValueError(f"Unknown SKU: {sku!r}")
    on_hand = WAREHOUSE_STOCK[sku]
    if qty <= 0 or qty > on_hand:
        raise ValueError(f"Cannot remove {qty} of {sku}; only {on_hand} in stock")
    WAREHOUSE_STOCK[sku] = on_hand - qty
    if WAREHOUSE_STOCK[sku] == 0:
        del WAREHOUSE_STOCK[sku]

def get_stock(sku):
    """Return the stock level for sku."""
    return WAREHOUSE_STOCK[sku]

def sku_checksum(sku):
    """Short fingerprint used on printed bin labels (not for security)."""
    digest = hashlib.md5(sku.encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()[:6]

def load_stock(path="warehouse.json"):
    """Load stock levels from a JSON file."""
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    WAREHOUSE_STOCK.clear()
    WAREHOUSE_STOCK.update(data)

def save_stock(path="warehouse.json"):
    """Save stock levels to a JSON file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(WAREHOUSE_STOCK, handle)

def print_report():
    """Print every SKU with its quantity and label checksum."""
    print("Warehouse Stock Report")
    for sku, qty in WAREHOUSE_STOCK.items():
        print(f"{sku} -> {qty} units [chk: {sku_checksum(sku)}]")

def check_reorder(threshold=10):
    """Return the SKUs whose stock is below threshold."""
    return [sku for sku, qty in WAREHOUSE_STOCK.items() if qty < threshold]

def apply_adjustment(sku, formula, password):
    """Set a SKU's quantity from a supervisor formula."""
    if not _is_authorized(password):
        LOGGER.warning("Adjustment denied for %s: bad credentials", sku)
        return False
    current = WAREHOUSE_STOCK.get(sku, 0)
    result = safe_eval(formula, current)
    if result < 0:
        raise ValueError("Adjustment would make stock negative")
    WAREHOUSE_STOCK[sku] = result
    with open(AUDIT_FILE, "a", encoding="utf-8") as audit:
        audit.write(
            f"adjusted {sku} using formula {formula} at {datetime.now()}\n"
        )
    return True

def main():
    """Run a short demonstration of the stock manager."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    history = []
    add_stock("WID-001", 40, history)
    add_stock("WID-002", 4, history)
    for sku, qty in (("WID-002", -4), (404, 15)):
        try:
            add_stock(sku, qty, history)
        except ValueError as err:
            LOGGER.warning("Rejected add: %s", err)

    for sku, qty in (("WID-001", 12), ("GHOST-9", 1), ("WID-001", 500)):
        try:
            remove_stock(sku, qty)
        except ValueError as err:
            LOGGER.warning("Rejected removal: %s", err)

    print("WID-002 stock:", get_stock("WID-002"))
    print("Needs reorder:", check_reorder())

    password = os.environ.get("SUPERVISOR_PASSWORD", "")
    apply_adjustment("WID-002", "current + 25", password)

    save_stock()
    load_stock()
    print_report()
    print("stock audit complete")

if __name__ == "__main__":
    main()