from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "ProjectSettings" / "ProjectVersion.txt",
    ROOT / "Packages" / "manifest.json",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "CryptoQuestWeb3Controller.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "ERC1155InventoryService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "ThirdwebTransactionController.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "AI" / "NpcAiClient.cs",
]

errors: list[str] = []
for path in REQUIRED:
    if not path.is_file():
        errors.append(f"missing: {path.relative_to(ROOT)}")

manifest_path = ROOT / "Packages" / "manifest.json"
if manifest_path.is_file():
    try:
        json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid Packages/manifest.json: {exc}")

version_path = ROOT / "ProjectSettings" / "ProjectVersion.txt"
if version_path.is_file():
    version_text = version_path.read_text(encoding="utf-8")
    if "2022.3" not in version_text:
        errors.append("Unity project must remain on 2022.3 LTS until migration is explicit")

secret_patterns = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*=\s*[^\s\"']+", re.I),
    re.compile(r"THIRDWEB_SECRET", re.I),
]
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".cs", ".json", ".md", ".txt", ".xml", ".yml", ".yaml"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for pattern in secret_patterns:
        if pattern.search(text):
            errors.append(f"possible client-side secret in {path.relative_to(ROOT)}")

web3_text = (ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "CryptoQuestWeb3Controller.cs").read_text(encoding="utf-8") if (ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "CryptoQuestWeb3Controller.cs").is_file() else ""
if "84532" not in web3_text:
    errors.append("Base Sepolia chain id 84532 missing from Web3 controller")

if errors:
    print("CryptoQuest RPG validation FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("CryptoQuest RPG validation OK")
print(f"Validated module: {ROOT}")
