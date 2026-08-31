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
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "Web3RuntimeConfig.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "RuntimeConfigLoader.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "ThirdwebClientIdInjector.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "ERC1155InventoryService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceDiscoveryService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceListingCache.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TokenAmountFormatter.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "ThirdwebTransactionController.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TokenMetadata.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TokenMetadataLoader.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MetadataNormalizer.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "InventoryItem.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "InventoryCatalogService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "InventoryMarketItem.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "InventoryMarketplaceService.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TransactionReceiptNormalizer.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "IpfsUri.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceDtos.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "UI" / "InventoryMarketItemView.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "UI" / "InventoryMarketPanelController.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "UI" / "MarketplaceActionController.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "AI" / "NpcAiClient.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Diagnostics" / "CryptoQuestRuntimeSmokeTest.cs",
    ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Diagnostics" / "CryptoQuestEndToEndSmokeTest.cs",
    ROOT / "Assets" / "CryptoQuest" / "Editor" / "AndroidBuild.cs",
    ROOT / "Assets" / "CryptoQuest" / "Editor" / "InventoryMarketUiBootstrap.cs",
    ROOT / "Assets" / "StreamingAssets" / "cryptoquest.runtime.example.json",
    ROOT / "docs" / "RUNTIME_AND_DEVICE_TEST.md",
]

errors: list[str] = []
for path in REQUIRED:
    if not path.is_file():
        errors.append(f"missing: {path.relative_to(ROOT)}")

manifest_path = ROOT / "Packages" / "manifest.json"
if manifest_path.is_file():
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "com.unity.toolchain.win-x86_64-linux-x86_64" in manifest.get("dependencies", {}):
            errors.append("unrelated cross-platform toolchain package must not be in the Android Unity module")
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
    re.compile(r"PRIVATE_KEY\s*=\s*[^\s\"']+", re.I),
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

web3_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "CryptoQuestWeb3Controller.cs"
web3_text = web3_path.read_text(encoding="utf-8") if web3_path.is_file() else ""
if "84532" not in web3_text:
    errors.append("Base Sepolia chain id 84532 missing from Web3 controller")
if "InAppWallet" not in web3_text:
    errors.append("Thirdweb InAppWallet integration missing")
if "using Thirdweb.Unity;" not in web3_text:
    errors.append("Thirdweb Unity v6 manager namespace missing from Web3 controller")

runtime_loader = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "RuntimeConfigLoader.cs"
runtime_text = runtime_loader.read_text(encoding="utf-8") if runtime_loader.is_file() else ""
for env_name in ("CRYPTOQUEST_THIRDWEB_CLIENT_ID", "CRYPTOQUEST_ERC1155_ADDRESS", "CRYPTOQUEST_MARKETPLACE_ADDRESS"):
    if env_name not in runtime_text:
        errors.append(f"runtime config injection missing {env_name}")
for fallback_field in ("fallbackClientId", "fallbackInventoryContractAddress", "fallbackMarketplaceContractAddress"):
    if fallback_field not in runtime_text:
        errors.append(f"embedded Android runtime fallback missing {fallback_field}")
if "ThirdwebManager.Instance.Initialize()" not in runtime_text:
    errors.append("Thirdweb manager is not initialized after runtime Client ID injection")

metadata_loader = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TokenMetadataLoader.cs"
metadata_text = metadata_loader.read_text(encoding="utf-8") if metadata_loader.is_file() else ""
if "LoadRawAsync" not in metadata_text or "ExpandErc1155Uri" not in metadata_text:
    errors.append("ERC1155 raw metadata extraction or {id} expansion missing")

marketplace_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceService.cs"
marketplace_text = marketplace_path.read_text(encoding="utf-8") if marketplace_path.is_file() else ""
if "getListing" not in marketplace_text or "buyFromListing" not in marketplace_text:
    errors.append("Marketplace V3 read/buy integration missing")

discovery_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "MarketplaceDiscoveryService.cs"
discovery_text = discovery_path.read_text(encoding="utf-8") if discovery_path.is_file() else ""
if "TotalListingsAsync" not in discovery_text or "DiscoverActiveListingIdsAsync" not in discovery_text:
    errors.append("Marketplace automatic listing discovery missing")
if "DiscoverNewestPageAsync" not in discovery_text or "DiscoverActiveListingIdsRangeAsync" not in discovery_text:
    errors.append("Marketplace paged discovery missing")
if "Task.WhenAll" not in discovery_text or "MarketplaceListingCache" not in discovery_text:
    errors.append("Marketplace batched/cached discovery missing")

panel_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "UI" / "InventoryMarketPanelController.cs"
panel_text = panel_path.read_text(encoding="utf-8") if panel_path.is_file() else ""
if "MarketplaceDiscoveryService" not in panel_text or "RefreshAfterMutationAsync" not in panel_text:
    errors.append("Inventory UI is not wired to cached discovery invalidation")

npc_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "AI" / "NpcAiClient.cs"
npc_text = npc_path.read_text(encoding="utf-8") if npc_path.is_file() else ""
if "/api/v1/cryptoquest/npc/dialogue" not in npc_text:
    errors.append("NPC client is not targeting the deployed FastAPI dialogue route")
for required_field in ("npc_id", "npc_name", "npc_role", "player_id", "player_name", "message", "world_state", "dialogue"):
    if required_field not in npc_text:
        errors.append(f"NPC client contract missing field {required_field}")

bootstrap_path = ROOT / "Assets" / "CryptoQuest" / "Editor" / "InventoryMarketUiBootstrap.cs"
bootstrap_text = bootstrap_path.read_text(encoding="utf-8") if bootstrap_path.is_file() else ""
if "Build Inventory Marketplace" not in bootstrap_text or "InventoryMarketItem.prefab" not in bootstrap_text:
    errors.append("Production inventory prefab/scene bootstrap missing")
if "using Thirdweb.Unity;" not in bootstrap_text or "AddComponent<ThirdwebManager>" not in bootstrap_text:
    errors.append("Generated production scene does not include Thirdweb Unity v6 manager")

android_build_path = ROOT / "Assets" / "CryptoQuest" / "Editor" / "AndroidBuild.cs"
android_text = android_build_path.read_text(encoding="utf-8") if android_build_path.is_file() else ""
for marker in ("InventoryMarketUiBootstrap.Build()", "InjectProductionConfig", "fallbackClientId", "com.cryptofactorystudios.cryptoquest"):
    if marker not in android_text:
        errors.append(f"production Android build wiring missing marker: {marker}")

receipt_path = ROOT / "Assets" / "CryptoQuest" / "Scripts" / "Web3" / "TransactionReceiptNormalizer.cs"
if receipt_path.is_file() and "transactionHash" not in receipt_path.read_text(encoding="utf-8"):
    errors.append("Transaction receipt normalization missing transaction hash")

if errors:
    print("CryptoQuest RPG validation FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("CryptoQuest RPG validation OK")
print(f"Validated module: {ROOT}")
