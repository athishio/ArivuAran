import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
external_dir = os.path.join(WORKSPACE_ROOT, "data", "external")

print("======================================================================")
print("INSPECTION OF EXTERNAL DATASET (data/external/)")
print("======================================================================")

if not os.path.exists(external_dir):
    print(f"Directory status: NOT FOUND ({external_dir} does not exist)")
    print("Files found: 0")
    print("Action required: Please place the external dataset file(s) into 'data/external/'")
else:
    files = os.listdir(external_dir)
    print(f"Directory status: FOUND ({external_dir})")
    print(f"Files found: {len(files)} -> {files}")
