# CryptoQuest runtime and device test

## Runtime inputs

CryptoQuest targets Base Sepolia (`84532`). Runtime configuration is loaded from environment variables first, then from `Assets/StreamingAssets/cryptoquest.runtime.json`.

Required values:

- `CRYPTOQUEST_THIRDWEB_CLIENT_ID` — public Thirdweb Client ID.
- `CRYPTOQUEST_ERC1155_ADDRESS` — deployed ERC-1155 inventory contract on Base Sepolia.
- `CRYPTOQUEST_MARKETPLACE_ADDRESS` — deployed Marketplace V3 contract on Base Sepolia.

Do not place a Thirdweb Secret Key, wallet private key, seed phrase, or OpenAI API key in the Unity project.

## Thirdweb SDK

Android CI pins Thirdweb Unity SDK `v6.1.3` and verifies the official release asset with SHA-256:

`615fd8246a9eee6000004c9d306dbe387b0c094a600fca58fe252c88d4dccc90`

The Unity namespace used by manager-specific types is `Thirdweb.Unity`; low-level contract/wallet types remain supplied by the Thirdweb .NET SDK dependency included in the Unity package.

## Generated production scene

In a Unity-capable environment run:

`CryptoQuest > UI > Build Inventory Marketplace`

The editor bootstrap creates:

- `Assets/CryptoQuest/Prefabs/InventoryMarketItem.prefab`
- `Assets/CryptoQuest/Scenes/InventoryMarket.unity`

The generated scene contains `ThirdwebManager`, runtime config loader, Web3 controller, metadata loader, marketplace actions, inventory panel, and both smoke-test components.

## Device CI

The real Unity Android build job is intentionally gated. Configure repository variables:

- `CRYPTOQUEST_UNITY_BUILD_ENABLED=true`
- `CRYPTOQUEST_THIRDWEB_CLIENT_ID`
- `CRYPTOQUEST_ERC1155_ADDRESS`
- `CRYPTOQUEST_MARKETPLACE_ADDRESS`

Unity GameCI also requires its standard Unity license credentials in repository secrets. The workflow then downloads and verifies the pinned Thirdweb `.unitypackage`, writes the runtime configuration file, imports Thirdweb during Unity startup, builds the Android package, and uploads the device-test artifact.

## End-to-end smoke path

`CryptoQuestEndToEndSmokeTest` validates the non-destructive read path:

wallet -> Base Sepolia -> ERC-1155 balances -> token URI -> HTTP/IPFS metadata -> normalized `InventoryItem` -> Marketplace V3 listing discovery -> `InventoryMarketItem` merge.

Write actions remain user-initiated from the UI: ERC-1155 marketplace approval, create listing, buy listing, and cancel listing. After a write, marketplace discovery cache is invalidated before UI refresh.
