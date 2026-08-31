# CryptoQuest ERC-1155 Inventory + Marketplace Pipeline

Status: implemented on `feat/cryptoquest-unity-bootstrap`.

Runtime flow:
1. `TokenMetadataLoader.LoadRawAsync` fetches ERC-1155 metadata over HTTP/IPFS and expands `{id}` using 64-character lowercase hex token IDs.
2. `MetadataNormalizer` normalizes mandatory fields, relative media URLs, and attributes.
3. `ERC1155InventoryService` reads `balanceOf`, `balanceOfBatch`, `uri`, approvals, and transfers from the Base Sepolia inventory contract.
4. `InventoryCatalogService` joins balances + metadata into `InventoryItem`.
5. `MarketplaceService` reads Marketplace V3 listings and performs create/cancel/buy writes.
6. `InventoryMarketplaceService` joins visible inventory with real listing data into `InventoryMarketItem`.
7. `TransactionReceiptNormalizer` converts Thirdweb write results into `Web3TransactionResult`.
8. `CryptoQuestRuntimeSmokeTest` checks chain configuration, normalized metadata, and connected wallet state.
9. `Assets/CryptoQuest/Editor/AndroidBuild.cs` and `.github/workflows/cryptoquest-android-device-build.yml` prepare ARM64 APK builds for device tests.

Required runtime configuration:
- Chain: Base Sepolia `84532`
- Thirdweb Client ID: public client-side identifier only
- ERC-1155 inventory contract address
- Marketplace V3 contract address

Android CI build is gated by repository variable `CRYPTOQUEST_UNITY_BUILD_ENABLED=true` and Unity licensing secrets. Static CryptoQuest validation still runs without those build credentials.

No OpenAI API key, Thirdweb secret key, private key, or recovery phrase belongs in this Unity module.
