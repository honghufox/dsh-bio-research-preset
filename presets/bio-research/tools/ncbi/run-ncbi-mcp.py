#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Launch the ncbi-mcp (NCBI E-utilities) MCP server via the system Python.

Requires: pip install ncbi-mcp 以及 mcp SDK 1.x（`pip install "mcp>=1.0,<2"`）。
Reads NCBI_EMAIL / NCBI_API_KEY from the environment (set in the preset row).
"""
import sys

from ncbi_mcp.server import main

if __name__ == "__main__":
    sys.exit(main())
