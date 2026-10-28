# Reflection QnA

**File analysed:** `warehouse_stock_manager.py`

## 1. Which issues were the easiest and which were the hardest to fix, and why?

The easiest fixes were the mechanical ones: removing the unused `total_units` variable and unused imports, renaming functions to snake_case, adding docstrings, and fixing the blank lines and line lengths Flake8 reported. Each had a clear message that said exactly what to change, and fixing one never affected another.

The hardest was replacing `eval()` in `applyAdjustment`. Bandit only says that `eval` is dangerous, but the supervisor still needs to type formulas like `current * 2`, so deleting it would have broken a real feature. I had to write a small `ast`-based evaluator (`safe_eval`) that only accepts numbers, the name `current`, and the operators `+ - * /`, and test that it rejects anything else. The hardcoded password was also not a one-line fix, because moving it to an environment variable meant changing how the program gets the password and how the demo calls the function.

## 2. Did any tool report a false positive, or miss a problem that you found yourself?

The MD5 warning (Bandit B324) is arguably a false positive in context. The hash is only a short fingerprint printed on bin labels and is not used for passwords or integrity checks, so there is no real security risk. I kept MD5 and passed `usedforsecurity=False`, which silences the warning and documents the intent. A reviewer should still decide whether that is acceptable.

The tools also missed several logic bugs that I only found by running the program and reading the output:

- `addStock("WID-002", -4)` created negative stock, and `addStock(404, 15)` accepted an integer SKU.
- `removeStock("WID-001", 500)` oversold the item and then deleted the SKU without any message.
- Removing an unknown SKU (`GHOST-9`) failed silently. Bandit and Pylint flagged the bare `except: pass` as a pattern, but they could not tell me what the wrong behaviour was.

Static analysis finds patterns, so it cannot know that negative stock makes no sense in a warehouse.

## 3. How would you integrate static analysis into a real development workflow?

I would run all three tools automatically so that problems are caught before they reach the main branch:

- **Locally:** a pre-commit hook that runs Flake8, Pylint and Bandit on staged files, so simple issues are fixed before the commit is created.
- **In CI:** a GitHub Actions workflow on every pull request that runs the same tools and fails the build if Bandit finds any Medium or High issue, if Flake8 reports anything, or if the Pylint score drops below an agreed threshold such as 9.5.
- **In the editor:** Pylint and Flake8 plugins give feedback while writing code, which is the cheapest time to fix things.

I would also keep one shared configuration file (for example `setup.cfg` or `.pylintrc`) so everyone on the team gets the same rules, and I would require a written justification for any suppression such as `# nosec` or `# pylint: disable`.

## 4. What improvements did you see in the code after the fixes?

The code is safer, more correct, and easier to read:

- **Security:** no more `eval`, no password in source code, and Bandit reports no issues. A supervisor formula can no longer run arbitrary code.
- **Correctness:** invalid SKUs and quantities are rejected, oversell is blocked, unknown SKUs give a clear error instead of being ignored, and the shared mutable `history` list bug is gone. The demo output is now sensible: WID-002 shows 4 units instead of -4, and WID-001 is no longer silently deleted.
- **Maintainability:** consistent snake_case names, docstrings, f-strings, `with open(...)` for every file, and a `__main__` guard so the module can be imported (and tested) without running the demo.
- **Measurable results:** the Pylint score rose from the original score to 10.00/10, Bandit went from several findings to none, and Flake8 went from many messages to an empty report. The numbers are in `issues.md` and the before/after report files.