import ast
import hashlib
import hmac
import json
import logging
import operator
import os
from datetime import datetime

# Global variables
warehouse_stock = {}
AUDIT_FILE = "warehouse_audit.log"

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_NUM = (int, float)


def safeEval(formula, current):
    # replaces eval(): only numbers, "current" and + - * / are allowed
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
        raise ValueError("Invalid formula: " + repr(formula)) from err


def isAuthorized(password):
    expected = os.environ.get("SUPERVISOR_PASSWORD")
    if not expected:
        return False
    return hmac.compare_digest(
        str(password).encode("utf-8"), expected.encode("utf-8")
    )


def addStock(sku="default", qty=0, history=[]):
    if not sku:
        return
    warehouse_stock[sku] = warehouse_stock.get(sku, 0) + qty
    history.append("%s: Received %d units of %s" % (str(datetime.now()), qty, sku))


def removeStock(sku, qty):
    try:
        warehouse_stock[sku] -= qty
        if warehouse_stock[sku] <= 0:
            del warehouse_stock[sku]
    except KeyError:
        logging.warning("Unknown SKU: %s", sku)


def getStock(sku):
    return warehouse_stock[sku]


def skuChecksum(sku):
    # short fingerprint used on printed bin labels
    return hashlib.md5(sku.encode(), usedforsecurity=False).hexdigest()[:6]


def loadStock(file="warehouse.json"):
    f = open(file, "r")
    global warehouse_stock
    warehouse_stock = json.loads(f.read())
    f.close()


def saveStock(file="warehouse.json"):
    f = open(file, "w")
    f.write(json.dumps(warehouse_stock))
    f.close()


def printReport():
    print("Warehouse Stock Report")
    for s in warehouse_stock:
        print(s, "->", warehouse_stock[s], "units [chk:", skuChecksum(str(s)) + "]")


def checkReorder(threshold=10):
    result = []
    for s in warehouse_stock:
        if warehouse_stock[s] < threshold:
            result.append(s)
    total_units = sum(warehouse_stock.values())
    return result


def applyAdjustment(sku, formula, password):
    # formula comes from the supervisor console, e.g. "current * 2"
    if not isAuthorized(password):
        return

    current = warehouse_stock.get(sku, 0)
    warehouse_stock[sku] = safeEval(formula, current)
    audit = open(AUDIT_FILE, "a")
    audit.write("adjusted " + str(sku) + " using formula " + formula + " at " + str(datetime.now()) + "\n")
    audit.close()


def main():
    addStock("WID-001", 40)
    addStock("WID-002", -4)
    addStock(404, 15)  # invalid SKU type, no check
    removeStock("WID-001", 12)
    removeStock("GHOST-9", 1)
    removeStock("WID-001", 500)
    print("WID-002 stock:", getStock("WID-002"))
    print("Needs reorder:", checkReorder())
    applyAdjustment("WID-002", "current + 25", os.environ.get("SUPERVISOR_PASSWORD", ""))
    saveStock()
    loadStock()
    printReport()
    print("stock audit complete")


main()