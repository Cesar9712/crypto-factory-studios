using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;

namespace CryptoQuest.Web3
{
    public sealed class MarketplaceDiscoveryService
    {
        private readonly MarketplaceService marketplace;

        public MarketplaceDiscoveryService(MarketplaceService marketplaceService)
        {
            marketplace = marketplaceService ?? throw new ArgumentNullException(nameof(marketplaceService));
        }

        public async Task<List<BigInteger>> DiscoverActiveListingIdsAsync(int maxListingsToScan = 500)
        {
            if (maxListingsToScan <= 0) throw new ArgumentOutOfRangeException(nameof(maxListingsToScan));

            var total = await marketplace.TotalListingsAsync();
            var capped = BigInteger.Min(total, new BigInteger(maxListingsToScan));
            var start = total > capped ? total - capped : BigInteger.Zero;
            var result = new List<BigInteger>();

            for (var id = start; id < total; id += BigInteger.One)
            {
                try
                {
                    var listing = await marketplace.GetListingAsync(id);
                    if (listing == null || listing.quantity <= BigInteger.Zero) continue;
                    var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                    var activeByTime = listing.startTimestamp <= now && (listing.endTimestamp <= 0 || now <= listing.endTimestamp);
                    if (activeByTime) result.Add(id);
                }
                catch
                {
                    // Marketplace V3 can contain removed/invalid historical ids; discovery must continue.
                }
            }

            return result;
        }
    }
}
