#!/usr/bin/env python3
"""
Test script to verify employer filtering functionality.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from server import apply_employer_filter_to_query, set_employer_id_filter


def test_query_filtering():
    """Test the query filtering functionality."""

    # Set employer filter
    set_employer_id_filter(123)

    test_cases = [
        # Basic SELECT queries
        ("SELECT * FROM job", "SELECT * FROM job WHERE job.employer_id = 123"),
        (
            "SELECT * FROM candidate",
            "SELECT * FROM candidate WHERE candidate.employer_id = 123",
        ),
        ("SELECT * FROM company", "SELECT * FROM company WHERE company.id = 123"),
        ("SELECT * FROM hr", "SELECT * FROM hr WHERE hr.employer_id = 123"),
        # Queries with existing WHERE clauses
        (
            "SELECT * FROM job WHERE status = 'published'",
            "SELECT * FROM job WHERE job.employer_id = 123 AND status = 'published'",
        ),
        (
            "SELECT * FROM candidate WHERE full_name LIKE '%John%'",
            "SELECT * FROM candidate WHERE candidate.employer_id = 123 AND full_name LIKE '%John%'",
        ),
        # Queries that already have employer_id filter (should not be modified)
        (
            "SELECT * FROM job WHERE employer_id = 456",
            "SELECT * FROM job WHERE employer_id = 456",
        ),
        # Non-SELECT queries (should not be modified)
        ("INSERT INTO job VALUES (1, 'test')", "INSERT INTO job VALUES (1, 'test')"),
        ("UPDATE job SET title = 'test'", "UPDATE job SET title = 'test')"),
        # Complex queries with JOINs
        (
            "SELECT j.title, c.full_name FROM job j JOIN application a ON j.id = a.job_id JOIN candidate c ON a.candidate_id = c.id",
            "SELECT j.title, c.full_name FROM job j JOIN application a ON j.id = a.job_id JOIN candidate c ON a.candidate_id = c.id WHERE job.employer_id = 123",
        ),
    ]

    print("Testing query filtering functionality...")
    print("Employer ID filter set to: 123")
    print("-" * 80)

    for i, (original, expected) in enumerate(test_cases, 1):
        result = apply_employer_filter_to_query(original)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        print(f"Test {i}: {status}")
        print(f"Original:  {original}")
        print(f"Expected:  {expected}")
        print(f"Result:    {result}")

        if result != expected:
            print("❌ MISMATCH!")

        print("-" * 80)


if __name__ == "__main__":
    test_query_filtering()
