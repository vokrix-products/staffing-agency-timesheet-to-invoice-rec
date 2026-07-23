Staffing Agency Timesheet-to-Invoice Reconciliation Auto-Processor
============================================================

A backend pipeline that automatically reconciles client-signed timesheets,
agency internal records, and rate agreements to produce discrepancy reports
and corrected invoices.

## Product Archetype

The system is organized into three layers:
- **Extractor** (`extractor.py`) – reads rate agreements (CSV or PDF).
  PDF extraction uses the DeepSeek model when an API key is set; otherwise
  falls back to sample data.
- **Reconciler** (`reconciliation.py`) – core logic: merges files, flags
  hour/rate mismatches, outputs `discrepancy:critical` or `reconciled:good`
  statuses.
- **Poller** (`poller.py`) – CLI entry point that accepts file paths and
  writes result CSVs. This is what a scheduler (e.g. cron, Railway CRON)
  would invoke.

## What the Poller Expects

The poller (`poller.py`) is invoked with three mandatory positional arguments
and two optional ones:

```
python3 poller.py client_timesheet.csv agency_internal.csv rate_agreement.{csv,pdf} \
    --output-discrepancy disc.csv \
    --output-invoice invoice.csv
```

**Input files:**
1. `client_timesheet.csv` – columns: `worker_id`, `date`, `hours_approved`.
2. `agency_internal.csv` – columns: `worker_id`, `date`, `hours_submitted`, `rate_used`.
3. `rate_agreement` – either a CSV with columns `worker_id`, `worker_name`, `rate`,
   or a PDF from which the extractor will attempt to parse rate data.

**Output files (optional):**
- `--output-discrepancy` – CSV of rows with any mismatch.
- `--output-invoice` – CSV of all rows with computed bill amounts and statuses.

## Quick Test

```bash
python3 run_demo.py
```

## Files

- `extractor.py` – PDF/CSV rate agreement reader.
- `reconciliation.py` – merge, discrepancy detection, status assignment.
- `poller.py` – command-line poller.
- `run_demo.py` – zero-argument demo with hardcoded data.
- `run_tests.py` – unit tests.
- `config.py` – configuration stub (reserved for future settings).
- `processor.py` – processor stub (reserved for future enrichment).
