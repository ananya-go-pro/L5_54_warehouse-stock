# Issues Table

**File analysed:** `warehouse_stock_manager.py`<br>
**Tools:** Pylint, Bandit, Flake8

Line numbers refer to the original file (before fixes).

## Issues found and fixed

| Issue | Type | Line(s) | Description | Fix Approach |
| ----- | ---- | ------- | ----------- | ------------ |
| Weak hash (MD5) | Security (Bandit B324, High) | 31 | `hashlib.md5` is flagged as an insecure hash. Here it is only a short fingerprint for bin labels, not used for security. | Pass `usedforsecurity=False` to `hashlib.md5(...)` to state the intent explicitly. |
| `eval()` on supervisor formula | Security (Bandit B307, Medium) | 62 | `eval(formula, ...)` in `applyAdjustment` executes arbitrary code, so anyone with the password could run any Python (code injection). | Replaced with `safe_eval`, an `ast`-based evaluator that only allows numbers, the name `current`, and `+ - * /`. Anything else raises `ValueError`. |
| `eval()` in `main` | Security (Bandit B307, Medium) | 80 | `eval("print('stock audit complete')")` is pointless and dangerous. | Replaced with a plain `print("stock audit complete")`. |
| Hardcoded password | Security (Bandit B105, Low) | 10 | `SUPERVISOR_PASSWORD = "wh-admin-1234"` is stored in source code and version control. | Removed the constant. The password is read from the `SUPERVISOR_PASSWORD` environment variable and compared with `hmac.compare_digest`. |
| Bare `except: pass` | Security/Bug (Bandit B110, Pylint W0702, Flake8 E722) | 23-24 | `removeStock` swallows every error silently, so removing an unknown SKU such as `GHOST-9` fails without any message. | Replaced with explicit validation that raises `ValueError` for unknown SKUs. Callers log the rejection. |
| Mutable default argument | Bug (Pylint W0102) | 12 | `history=[]` is created once and shared across every call to `addStock`. | Changed the default to `None` and create a new list inside the function. |
| No input validation on `addStock` | Bug (logic) | 12-16 | Negative quantities (`WID-002`, -4) and an integer SKU (`404`) were accepted, producing negative stock and a SKU that changes type after a JSON save/load. | Validate that `sku` is a non-empty string and `qty` is a positive integer. Raise `ValueError` otherwise. |
| Oversell silently deletes SKU | Bug (logic) | 18-22 | `removeStock("WID-001", 500)` pushed stock below zero, and the `<= 0` check then deleted the SKU without any warning. | Reject removals greater than stock on hand. Only delete the SKU when stock reaches exactly 0. |
| Files opened without `with` | Code quality (Pylint R1732, W1514) | 34, 40, 63 | `open()` without a context manager can leak the file handle if an error occurs, and no encoding is specified. | Use `with open(..., encoding="utf-8")` in `load_stock`, `save_stock`, and the audit log write. |
| `global` statement | Code quality (Pylint W0603) | 35 | `loadStock` rebinds the module-level dict through `global`. | Update the dict in place with `clear()` and `update()`, so no `global` is needed. |
| Unused variable | Code quality (Pylint W0612, Flake8 F841) | 54 | `total_units` is computed in `checkReorder` and never used. | Removed it. `check_reorder` now uses a list comprehension. |
| Unused imports | Code quality (Pylint W0611, Flake8 F401) | 2, 4 | `logging` and `os` were imported but never used in the original code. | Both are now used (`logging` for warnings, `os` for the environment variable). |
| Function names not snake_case | Style (Pylint C0103) | 12, 18, 26, 29, 33, 39, 44, 49, 57 | camelCase names (`addStock`, `removeStock`, ...) break PEP 8. | Renamed to `add_stock`, `remove_stock`, `get_stock`, `sku_checksum`, `load_stock`, `save_stock`, `print_report`, `check_reorder`, `apply_adjustment`. The stock dict is `WAREHOUSE_STOCK` as a module-level constant. |
| Missing docstrings | Style (Pylint C0114, C0116) | 1, all functions | The module and every function had no docstring. | Added a module docstring and a one-line docstring for each function. |
| `%` formatting and string concatenation | Style (Pylint C0209) | 16, 47, 64 | Old-style formatting is harder to read. | Replaced with f-strings. |
| Module runs on import | Style/Design | 82 | `main()` was called at module level, so importing the file executed the demo. | Wrapped the call in `if __name__ == "__main__":`. |
| Blank lines between definitions | Formatting (Flake8 E302, E305) | between all functions, 82 | Only one blank line separated top-level definitions. | Two blank lines before and after each top-level function. |
| Lines too long | Formatting (Flake8 E501) | 47, 64 | Lines longer than 79 characters. | Wrapped the lines. |
| Missing newline at end of file | Formatting (Flake8 W292, Pylint C0304) | 82 | The file did not end with a newline. | Added a single final newline. |

## Results before and after

| Tool | Before | After |
| ---- | ------ | ----- |
| Bandit | _fill in from `bandit_report_before.txt`_ | No issues identified |
| Pylint | _fill in score from `pylint_report_before.txt`_ | _fill in score from `pylint_report_after.txt`_ (target above 9.5) |
| Flake8 | _fill in number of messages from `flake8_report_before.txt`_ | 0 messages (empty report) |

## Commits

1. Bandit fixes: `eval`, hardcoded password, MD5, silent `except`
2. Pylint fixes: naming, docstrings, validation, context managers, mutable default
3. Flake8 fixes: formatting and line length
