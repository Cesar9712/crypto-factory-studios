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
            return await DiscoverActiveListingIdsRangeAsync(start, total);
        }

        public async Task<List<BigInteger>> DiscoverActiveListingIdsRangeAsync(BigInteger startInclusive, BigInteger endExclusive)
        {
            if (startInclusive < BigInteger.Zero) throw new ArgumentOutOfRangeException(nameof(startInclusive));
            if (endExclusive < startInclusive) throw new ArgumentOutOfRangeException(nameof(endExclusive));

            var result = new List<BigInteger>();
            for (var id = startInclusive; id < endExclusive; id += BigInteger.One)
            {
                var listing = await TryGetActiveListingAsync(id);
                if (listing != null) result.Add(id);
            }
            return result;
        }

        public async Task<List<BigInteger>> DiscoverNewestPageAsync(BigInteger beforeExclusive, int pageSize = 100)
        {
            if (pageSize <= 0) throw new ArgumentOutOfRangeException(nameof(pageSize));
            var total = await marketplace.TotalListingsAsync();
            var end = beforeExclusive <= BigInteger.Zero || beforeExclusive > total ? total : beforeExclusive;
            var start = BigInteger.Max(BigInteger.Zero, end - pageSize);
            return await DiscoverActiveListingIdsRangeAsync(start, end);
        }

        public async Task<MarketplaceListingView> TryGetActiveListingAsync(BigInteger listingId)
        {
            try
            {
                var listing = await marketplace.GetListingAsync(listingId);
                if (listing == null || listing.quantity <= BigInteger.Zero) return null;
                var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                var activeByTime = listing.startTimestamp <= now && (listing.endTimestamp <= 0 || now <= listing.endTimestamp);
                return activeByTime ? listing : null;
            }
            catch
            {
                return null;
            }
        }
    }
}
