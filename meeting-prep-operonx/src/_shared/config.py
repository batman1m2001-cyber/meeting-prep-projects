"""The settings, read from the environment once. The only file that reads it."""
import os

# where the approval email links: the app itself, or a public address that forwards to it
APPROVE_URL = os.environ.get("PREP_APPROVE_URL", "http://127.0.0.1:8200/approve")
