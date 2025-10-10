import zipfile, os, shutil
from pathlib import Path

base = Path(".")
out_dir = base / "TCG_All_In_One_Patch_v2_seeded"
out_zip = base / "TCG_All_In_One_Patch_v2_seeded.zip"

# Reset folder
if out_dir.exists():
    shutil.rmtree(out_dir)
(out_dir / "server").mkdir(parents=True, exist_ok=True)
(out_dir / "static").mkdir(parents=True, exist_ok=True)
(out_dir / "data").mkdir(parents=True, exist_ok=True)

# Unpack relevance v2 code
with zipfile.ZipFile("TCG_Relevance_Patch_v2.zip", "r") as z:
    for n in z.namelist():
        if n.endswith(("server/ai_relevance_v2.py",
                       "server/routes_weights_v2_fastapi.py",
                       "server/routes_weights_v2_flask.py",
                       "static/static_weights_v2.js",
                       "static/static_weights_v2.css",
                       "README_PATCH_V2.md")):
            z.extract(n, out_dir)

# Pull seeded Excel from the data zip
with zipfile.ZipFile("TCG_Agency_AI_Matching_Patch_v8_seeded.zip", "r") as z:
    with z.open("data/AI_Matching_Rules_full.xlsx") as f:
        (out_dir / "data" / "AI_Matching_Rules_full.xlsx").write_bytes(f.read())

# Minimal top-level readme
(out_dir / "README_ALL_IN_ONE.md").write_text(
    "Single-bundle: data + server + static. Use /api/step2/ai/weights_v2 and static_weights_v2.* in Step 2A.",
    encoding="utf-8"
)

# Zip it
if out_zip.exists():
    out_zip.unlink()
with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(out_dir):
        for fn in files:
            p = Path(root) / fn
            z.write(p, arcname=str(p.relative_to(out_dir)))

print("Created:", out_zip)
