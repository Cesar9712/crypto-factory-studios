using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;

namespace CryptoQuest.Web3
{
    public sealed class InventoryCatalogService
    {
        private readonly ERC1155InventoryService inventory;
        private readonly TokenMetadataLoader metadataLoader;

        public InventoryCatalogService(ERC1155InventoryService inventoryService, TokenMetadataLoader loader)
        {
            inventory = inventoryService ?? throw new ArgumentNullException(nameof(inventoryService));
            metadataLoader = loader ?? throw new ArgumentNullException(nameof(loader));
        }

        public async Task<List<InventoryItem>> LoadOwnedAsync(string owner, IReadOnlyList<BigInteger> tokenIds)
        {
            if (tokenIds == null || tokenIds.Count == 0) return new List<InventoryItem>();
            var owners = new string[tokenIds.Count];
            for (var i = 0; i < owners.Length; i++) owners[i] = owner;
            var balances = await inventory.BalanceOfBatchAsync(owners, tokenIds);
            var result = new List<InventoryItem>(tokenIds.Count);

            for (var i = 0; i < tokenIds.Count; i++)
            {
                var balance = balances[i];
                if (balance <= BigInteger.Zero) continue;
                var tokenId = tokenIds[i];
                var uri = await inventory.TokenUriAsync(tokenId);
                var metadata = await metadataLoader.LoadAsync(uri, tokenId);
                result.Add(ToInventoryItem(tokenId, balance, uri, metadata));
            }
            return result;
        }

        public async Task<InventoryItem> LoadOneAsync(string owner, BigInteger tokenId)
        {
            var balance = await inventory.BalanceOfAsync(owner, tokenId);
            var uri = await inventory.TokenUriAsync(tokenId);
            var metadata = await metadataLoader.LoadAsync(uri, tokenId);
            return ToInventoryItem(tokenId, balance, uri, metadata);
        }

        private static InventoryItem ToInventoryItem(BigInteger tokenId, BigInteger balance, string uri, TokenMetadata metadata)
        {
            return new InventoryItem
            {
                tokenId = tokenId.ToString(),
                balance = balance.ToString(),
                metadataUri = TokenMetadataLoader.ExpandErc1155Uri(uri, tokenId),
                name = metadata?.name ?? $"Token #{tokenId}",
                description = metadata?.description ?? string.Empty,
                imageUrl = metadata?.ResolvedImageUrl ?? string.Empty,
                animationUrl = metadata?.ResolvedAnimationUrl ?? string.Empty,
                attributes = metadata?.attributes ?? Array.Empty<TokenAttribute>()
            };
        }
    }
}
