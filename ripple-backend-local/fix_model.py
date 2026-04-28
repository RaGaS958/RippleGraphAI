# Run this once from ripple-backend-local folder to fix the model name
# python fix_model.py

import re
from pathlib import Path

f = Path("app/agents/adk_pipeline.py")
content = f.read_text()
updated = content.replace("gemini-1.5-flash", "gemini-2.0-flash")
f.write_text(updated)
count = content.count("gemini-1.5-flash")
print(f"Replaced {count} occurrence(s) of gemini-1.5-flash → gemini-2.0-flash")
print("Restart backend: uvicorn app.main:app --port 8080 --reload")
