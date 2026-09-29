#!/usr/bin/env python3
"""Seed the database with roles, users, detection rules, and parser registry.

Idempotent. Safe to run multiple times.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.init_db import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("Seed complete.")