ABOUTME — Claim Automation (User-First + Roadmap + Error Panel)
=====================================================================

Who this is for
---------------
• Anyone using the app (non‑technical or technical).  
• Collaborators/developers who need the big picture and concrete steps.  
Everything runs **locally** (CPU‑only is fine) and respects your master Excel layout.

---------------------------------------------------------------------
Quick FAQ (for anyone using the app)
---------------------------------------------------------------------
Do I need a special computer or a graphics card?
- No. It runs on a normal laptop (CPU‑only).

How fast is it with the AI check ON for every claim?
- Today’s AI check (name‑focused): ~9–15 sec per claim.
- Future broader AI check (more fields): ~20–35 sec per claim.
- With ~40 claims/day: ~6–10 min automation (today) or ~13–23 min (broader check).

How accurate is it?
- Automation‑only: ~96–98% today; ~97–99% with broader check.
- With a quick human glance after: ~99%+ verified.

Will it change my master workbook formulas or summaries?
- No. It only appends into the main table above your summary/notes sections and preserves formulas and styles.

Will it fill the Insurance column (B) automatically?
- Not by default. Column B stays BLANK for you to type. You can turn on auto‑fill later if you enable the optional Client List.

What does the Word export contain?
- Only the screenshot (no text).

Do I have to use the AI review?
- No, but the default is to keep it ON for every claim for safety. It’s still fast on CPU.

Can I use this with my existing master files?
- Yes. You can pick the master file per counselor; new rows go to the correct place.

---------------------------------------------------------------------
User Guide (what it does & how to use it)
---------------------------------------------------------------------
What it does today (short version)
- Drag a screenshot of an ERA/EOB into the app.
- The app reads the picture (OCR), pulls out name/date/amounts.
- It does the payout math.
- It adds a row to your Excel and creates a Word file (image only).
- Runs fully on your computer (no internet needed).
- AI double‑check is available and stays ON each time by default.

Your Excel mapping (exact columns A–L)
A  Client Name               → From OCR/validation
B  Client Insurance          → BLANK (manual)
C  Date of Service           → From OCR/validation
D  Client CoPay              → Cleaned number
E  Deductible being met      → Cleaned number
F  Insurance Paid            → Cleaned number
G  Insurance Contract        → Workbook formula (=D+E+F)
H  65% Counselor rate        → Workbook formula (=G*0.65)
I  Amount to Counselor       → Workbook formula (=F-(D+E))
J  35% Amount to GWC         → Workbook formula (=G*0.35)
K  Total payout              → Existing running‑total formula
L  ACH order date            → BLANK (manual)

We never write into the summary/notes blocks (e.g., “Percentage of insurance clients…”, “Incomplete Notes…”, “Aflac … policy”).

Quick start (step‑by‑step)
1) Open the app.
2) Drag an ERA/EOB screenshot into the window.
3) (If broader AI is enabled) glance at colors: green=good, yellow=check, red=likely wrong.
4) Click Export. A row is added to your master Excel; a Word file with the screenshot is created.
5) Type Insurance in Column B and ACH date in Column L when ready.

Toggles you control in the app
- Always run AI review: ON (recommended for safety; still fast).
- Broader AI review: OFF by default; turns on deeper checks (slower but still practical).
- Fill Insurance (Column B) from Client List: OFF by default; enable only if you want auto‑fill.
- Client List panel: Add/Edit/Delete/Import/Export clients (stored in clients.json).

Timing & accuracy (assume ~40 claims/day, CPU‑only)
- Today (name‑focused AI ON): ~9–15 sec/claim; ~6–10 min/day automation; ~96–98% auto → ~99%+ with quick human check.
- Future broader AI ON: ~20–35 sec/claim; ~13–23 min/day automation; ~97–99% auto → ~99%+ with quick human check.

---------------------------------------------------------------------
Planned “Issues” Panel in the GUI (user‑friendly errors)
---------------------------------------------------------------------
What you’ll see
- A right‑side panel with three tabs: Errors, Warnings, Activity.
- Clear, color‑coded entries and a details box.
- Short human hints (e.g., “Tesseract not found. Install it, then set its path in Settings → OCR.”).
- Quick actions: Copy, Save log, Open logs folder. Optional: Retry.

What happens behind the scenes
- The app’s logger sends messages straight to the panel.
- When something fails (OCR, Excel export, LLM), you’ll see:
  • What failed (context)  
  • A short reason (message)  
  • A helpful suggestion (hint)  
  • Details (stack/trace) for developers

Why this helps
- Users get simple guidance instead of cryptic errors.
- Developers get fast diagnostics without asking for log files separately.

---------------------------------------------------------------------
Under the hood (simple flow)
---------------------------------------------------------------------
1) OCR — read the screenshot and extract fields.
2) Numeric Sanitizer — fix typos (125.0O → 125.00), block letters in amounts.
3) Validation — catch oddities (e.g., header as name, missing values).
4) AI review — suggest fixes; you accept or ignore.
5) Calculations — the formulas you already use.
6) Export — append to Excel (A–L) and create Word (screenshot only).
7) Logging — everything is logged, and the Issues panel shows it live.

Everything is local. If AI isn’t available, the app still works and logs “not AI‑verified.”

---------------------------------------------------------------------
Developer Notes (architecture & phases)
---------------------------------------------------------------------
Modular pipeline
- OCR → numeric_sanitizer → validation → (client_db) → (AI review) → calculations → export
  • OCR: extraction only (no heuristics).
  • Numeric Sanitizer: deterministic currency cleaner (rejects letters; fixes O↔0).
  • Validation: “weirdness checks” (header‑as‑name, missing fields, non‑negative checks).
  • Client DB (optional): lookup/merge known client info (insurer, member ID, notes).
  • AI review (optional but ON by default for safety): advisory fixes with reasons.
  • Calculations: pure formulas; no side effects.
  • Export: append into master Excel table; Word is screenshot only.
  • Logging: `debugger.py` + GUI Issues panel sink.

Exact Excel behavior
- Append above summary blocks; preserve formulas/styles.
- Respect A–L mapping; Column B and L remain blank by default.
- No remark codes written to files (internal use only).

Phased changes (what changes vs what stays)
Phase 1 — Output format fixes (now)
  Changes: Excel & Word layout rules enforced; add numeric_sanitizer.
  Stays: OCR behavior, math, CPU‑only operation.
  Time/accuracy: ~9–15 sec/claim; ~96–98% auto; ~99%+ with human check.

Phase 2 — Master file integration
  Changes: Append into real master files; GUI path per counselor.
  Stays: Column B/L manual by default.
  Time/accuracy: same as Phase 1.

Phase 2.5 — Broader AI review (optional)
  Changes: multi‑field AI check + highlights + “Apply Suggested Fixes”.
  Stays: Works fine with basic AI check only.
  Time/accuracy: ~20–35 sec/claim; ~97–99% auto; ~99%+ with human check.

Phase 2.6 — Client List (optional)
  Changes: client_db.py + GUI panel; optional auto‑fill for Column B (OFF by default).
  Stays: No retroactive edits to past Excel rows; manual control kept.
  Impact: negligible time; fewer repeat typing mistakes.

Phase 3 — On‑site install & real data test
  Set up Python, Tesseract, and local AI model; connect master files; verify 10–20 screenshots.

Phase 4 — CPU‑only performance check
  Measure timings; if broader AI feels slow, stay with basic AI (still ON per claim).

Phase 5 — Packaging
  Windows installer (.EXE); no behavior changes.

Files/Modules to add or adjust
- + modules/numeric_sanitizer.py (strict currency cleaner).
- + modules/client_db.py (JSON now; plan SQLite migration).
- + modules/ui_errors.py (Issues panel widgets + Qt log handler).
- = modules/validation_module.py (name/header checks; consistency).
- = modules/llm_validator_v2.py (advisory fixes).
- = modules/excel_module.py (append; guard before summaries).
- = modules/word_module.py (screenshot only).
- = modules/ocr_module.py (extraction only).
- = modules/calculations_module.py (formulas).
- = gui.py (toggles, client panel, master path picker, Issues panel dock).
- = config.py (paths, toggles).
- = debugger.py (stage‑tagged logs + GUI handler).

Testing checklist
1) Golden samples → Excel row equals expected A–L mapping; Word image‑only.
2) Numeric fuzzer → sanitizer accepts only valid currency; rejects letters.
3) Header‑as‑name detector → flags synthetic headers; normal names pass.
4) Client DB roundtrip → add/lookup/edit/export/import (stable IDs, aliases).
5) AI OFF vs ON parity → ignoring AI suggestions yields OCR‑equivalent rows.
6) Issues panel → emits a user‑hint for common failures (missing Tesseract, missing master path).
