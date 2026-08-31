# CryptoQuest RPG

Isolated Unity 2022.3 LTS module for Crypto Factory Studios.

## Runtime targets
- Unity: 2022.3 LTS
- Android application id: `com.cryptofactorystudios.cryptoquest`
- Thirdweb Unity SDK: v6.1.3
- Network: Base Sepolia (`84532`)
- Player wallets: Thirdweb In-App Wallet
- Inventory: ERC-1155
- Marketplace: Thirdweb Marketplace V3 direct listings
- NPC AI: Crypto Factory Studios backend -> OpenAI (server-side key only)
- Avatars: modular provider architecture; no runtime dependency on Ready Player Me

## Web3 runtime configuration
Set these values in Unity runtime configuration/inspector before enabling live transactions:
- Thirdweb Client ID
- ERC-1155 inventory contract address on Base Sepolia
- Marketplace V3 contract address on Base Sepolia

Never place Thirdweb Secret Key, private keys, recovery phrases, or OpenAI API keys in this Unity module.

## Implemented modules
- `Scripts/Core/CryptoQuestConfig.cs`
- `Scripts/Web3/CryptoQuestWeb3Controller.cs`
- `Scripts/Web3/ThirdwebTransactionController.cs`
- `Scripts/Web3/ERC1155InventoryService.cs`
- `Scripts/Web3/ERC1155InventoryController.cs`
- `Scripts/Web3/MarketplaceService.cs`
- `Scripts/Web3/MarketplaceDtos.cs`
- `Scripts/Web3/IpfsUri.cs`
- `Scripts/Web3/TokenMetadata.cs`
- `Scripts/Web3/TokenMetadataLoader.cs`
- `Scripts/AI/NpcAiClient.cs`
- `Scripts/AI/NpcDialogueModels.cs`
- `Scripts/Avatars/IAvatarProvider.cs`
- `Scripts/Avatars/PrefabAvatarProvider.cs`
- `Scripts/Avatars/AvatarService.cs`

## Validation
Run from repository root:

```bash
python games/CryptoQuest-RPG/ci/validate_module.py
```

The validator checks required module files, Unity version, Base Sepolia configuration, Thirdweb wallet integration, IPFS support, and scans the Unity module for client-side secrets.
