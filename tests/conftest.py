"""Pytest configuration and test environment fixtures."""

import os

# Ensure unit test executions do not attempt outbound external API calls in sandbox
os.environ["MOCK_LLM"] = "true"
