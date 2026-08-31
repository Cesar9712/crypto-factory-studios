using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;

namespace CryptoQuest.Web3
{
    public sealed class InventoryMarketplaceService
    {
        private readonly MarketplaceService marketplace;

        public InventoryMarketplaceService(MarketplaceService marketplaceService)
        {
            marketplace = marketplaceService ?? throw new ArgumentNullException(nameof(marketplaceService));
        }

        public async Task<InventoryMarketItem> MergeAsync(InventoryItem inventory, BigInteger listingId, string walletAddress)
        {
            if (inventory == null) throw new ArgumentNullException(nameof(inventory));
            var listing = await marketplace.GetListingAsync(listingId);
            var seller = listing?.seller ?? string.Empty;
            var isSeller = !string.IsNullOrWhiteSpace(walletAddress) && string.Equals(seller, walletAddress, StringComparison.OrdinalIgnoreCase);
            var sameToken = listing != null && listing.tokenId == inventory.TokenId;
            var active = sameToken && listing.quantity > BigInteger.Zero;

            return new InventoryMarketItem
            {
                inventory = inventory,
                listing = listing,
                isListed = active,
                isSeller = isSeller,
                canBuy = active && !isSeller,
                canCancel = active && isSeller
            };
        }

        public async Task<List<InventoryMarketItem>> MergeManyAsync(IReadOnlyList<InventoryItem> inventory, IReadOnlyList<BigInteger> listingIds, string walletAddress)
        {
            var result = new List<InventoryMarketItem>();
            if (inventory == null || inventory.Count == 0) return result;

            var byToken = new Dictionary<string, InventoryMarketItem>();
            foreach (var item in inventory)
                byToken[item.tokenId] = new InventoryMarketItem { inventory = item };

            if (listingIds != null)
            {
                foreach (var listingId in listingIds)
                {
                    var listing = await marketplace.GetListingAsync(listingId);
                    if (listing == null) continue;
                    var key = listing.tokenId.ToString();
                    if (!byToken.TryGetValue(key, out var merged)) continue;
                    var isSeller = string.Equals(listing.seller, walletAddress, StringComparison.OrdinalIgnoreCase);
                    var active = listing.quantity > BigInteger.Zero;
                    merged.listing = listing;
                    merged.isListed = active;
                    merged.isSeller = isSeller;
                    merged.canBuy = active && !isSeller;
                    merged.canCancel = active && isSeller;
                }
            }

            result.AddRange(byToken.Values);
            return result;
        }
    }
}
