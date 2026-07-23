import pandas as pd
from extractor import load_rate_agreement

STATUS_CRITICAL = "discrepancy:critical"
STATUS_GOOD = "reconciled:good"

def reconcile(client_timesheet_path: str, agency_internal_path: str, rate_agreement_path: str):
    """
    Match worker/date across client timesheet and agency internal CSV,
    compare hours and rates, and produce:
        - discrepancy_report (DataFrame): rows with any mismatch
        - reconciled_invoice (DataFrame): all rows with corrected amount and status
    """
    client = pd.read_csv(client_timesheet_path)
    agency = pd.read_csv(agency_internal_path)
    rates = load_rate_agreement(rate_agreement_path)

    # Normalize column names (lowercase, strip)
    for df in [client, agency, rates]:
        df.columns = df.columns.str.strip().str.lower()

    # Expected columns:
    # client: worker_id, date, hours_approved
    # agency: worker_id, date, hours_submitted, rate_used
    # rates: worker_id, rate
    # If 'worker_name' exists in client/agency, we could match by name later, but here we use worker_id.
    # Ensure worker_id is string
    client["worker_id"] = client["worker_id"].astype(str)
    agency["worker_id"] = agency["worker_id"].astype(str)
    rates["worker_id"] = rates["worker_id"].astype(str)

    merged = pd.merge(client, agency, on=["worker_id", "date"], how="outer", suffixes=("_client", "_agency"))
    merged = pd.merge(merged, rates, on="worker_id", how="left")

    # Fill missing approved hours with 0 or agency hours? For safety, keep NaN and treat as discrepancy later.
    # We'll create a consistent base: use client hours if present, else 0.
    merged["hours_client"] = merged["hours_approved"].fillna(0)
    merged["hours_agency"] = merged["hours_submitted"].fillna(0)
    merged["rate_used"] = merged["rate_used"].fillna(0)
    merged["correct_rate"] = merged["rate"].fillna(0)

    # Discrepancy flags
    merged["hour_discrepancy"] = abs(merged["hours_client"] - merged["hours_agency"]) > 0.001
    merged["rate_discrepancy"] = abs(merged["rate_used"] - merged["correct_rate"]) > 0.001

    # Status per row
    merged["status"] = merged.apply(
        lambda row: STATUS_CRITICAL if row["hour_discrepancy"] or row["rate_discrepancy"] else STATUS_GOOD,
        axis=1
    )

    # Bill amount: use client hours * correct rate
    merged["bill_amount"] = merged["hours_client"] * merged["correct_rate"]

    # Sort
    merged.sort_values(["worker_id", "date"], inplace=True)

    # Discrepancy report = rows with any discrepancy
    discrepancy_report = merged[merged["status"] == STATUS_CRITICAL].copy()

    # Select output columns
    out_columns = [
        "worker_id", "date",
        "hours_client", "hours_agency",
        "hour_discrepancy", "rate_used", "correct_rate", "rate_discrepancy",
        "bill_amount", "status"
    ]
    discrepancy_report = discrepancy_report[out_columns]
    reconciled_invoice = merged[out_columns]

    return discrepancy_report, reconciled_invoice
