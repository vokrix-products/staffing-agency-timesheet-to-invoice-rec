import unittest, os, tempfile
import pandas as pd
from reconciliation import reconcile, STATUS_CRITICAL, STATUS_GOOD
from extractor import extract_rate_from_pdf

class TestExtractor(unittest.TestCase):
    def test_dummy_data_returned_without_api_key(self):
        # Without API key, dummy DataFrame should be returned
        df = extract_rate_from_pdf("dummy.pdf")
        self.assertIn("worker_id", df.columns)
        self.assertIn("worker_name", df.columns)
        self.assertIn("rate", df.columns)
        self.assertEqual(len(df), 2)

class TestReconciliation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_csv(self, name, content):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_no_discrepancy(self):
        client_csv = self.write_csv("client.csv", "worker_id,date,hours_approved\nW001,2025-01-06,8.0\nW001,2025-01-07,8.0\n")
        agency_csv = self.write_csv("agency.csv", "worker_id,date,hours_submitted,rate_used\nW001,2025-01-06,8.0,25.0\nW001,2025-01-07,8.0,25.0\n")
        rate_csv = self.write_csv("rates.csv", "worker_id,worker_name,rate\nW001,Alice,25.0\n")
        disc, invo = reconcile(client_csv, agency_csv, rate_csv)
        self.assertTrue(disc.empty)
        self.assertEqual(len(invo), 2)
        self.assertTrue(all(invo["status"] == STATUS_GOOD))
        self.assertTrue(all(invo["bill_amount"] == 8.0 * 25.0))  # 200

    def test_hour_discrepancy(self):
        client_csv = self.write_csv("client.csv", "worker_id,date,hours_approved\nW001,2025-01-06,8.0\n")
        agency_csv = self.write_csv("agency.csv", "worker_id,date,hours_submitted,rate_used\nW001,2025-01-06,7.0,25.0\n")
        rate_csv = self.write_csv("rates.csv", "worker_id,worker_name,rate\nW001,Alice,25.0\n")
        disc, invo = reconcile(client_csv, agency_csv, rate_csv)
        self.assertEqual(len(disc), 1)
        self.assertEqual(disc.iloc[0]["status"], STATUS_CRITICAL)
        self.assertTrue(disc.iloc[0]["hour_discrepancy"])
        self.assertFalse(disc.iloc[0]["rate_discrepancy"])
        # Bill amount should use client hours (8) * correct rate (25) = 200
        self.assertAlmostEqual(disc.iloc[0]["bill_amount"], 200.0)

    def test_rate_discrepancy(self):
        client_csv = self.write_csv("client.csv", "worker_id,date,hours_approved\nW002,2025-01-07,8.0\n")
        agency_csv = self.write_csv("agency.csv", "worker_id,date,hours_submitted,rate_used\nW002,2025-01-07,8.0,35.0\n")
        rate_csv = self.write_csv("rates.csv", "worker_id,worker_name,rate\nW002,Bob,30.0\n")
        disc, invo = reconcile(client_csv, agency_csv, rate_csv)
        self.assertEqual(len(disc), 1)
        self.assertEqual(disc.iloc[0]["status"], STATUS_CRITICAL)
        self.assertTrue(disc.iloc[0]["rate_discrepancy"])
        self.assertTrue(disc.iloc[0]["hour_discrepancy"] == False)
        self.assertAlmostEqual(disc.iloc[0]["bill_amount"], 8.0 * 30.0)

    def test_both_discrepancies(self):
        client_csv = self.write_csv("client.csv", "worker_id,date,hours_approved\nW003,2025-01-08,6.0\n")
        agency_csv = self.write_csv("agency.csv", "worker_id,date,hours_submitted,rate_used\nW003,2025-01-08,6.5,22.0\n")
        rate_csv = self.write_csv("rates.csv", "worker_id,worker_name,rate\nW003,Charlie,20.0\n")
        disc, invo = reconcile(client_csv, agency_csv, rate_csv)
        self.assertEqual(disc.iloc[0]["status"], STATUS_CRITICAL)
        self.assertTrue(disc.iloc[0]["hour_discrepancy"])
        self.assertTrue(disc.iloc[0]["rate_discrepancy"])
        self.assertAlmostEqual(disc.iloc[0]["bill_amount"], 6.0 * 20.0)

    def test_status_strings_exact(self):
        # Ensure that status values are exactly as specified
        client_csv = self.write_csv("client.csv", "worker_id,date,hours_approved\nW004,2025-02-01,8.0\n")
        agency_csv = self.write_csv("agency.csv", "worker_id,date,hours_submitted,rate_used\nW004,2025-02-01,8.0,40.0\n")
        rate_csv = self.write_csv("rates.csv", "worker_id,worker_name,rate\nW004,Diana,40.0\n")
        disc, invo = reconcile(client_csv, agency_csv, rate_csv)
        self.assertEqual(invo.loc[0, "status"], STATUS_GOOD)

if __name__ == "__main__":
    unittest.main()
