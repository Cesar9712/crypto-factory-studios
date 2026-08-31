using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;

namespace CryptoQuest.Web3
{
    public sealed class MarketplaceDiscoveryService
    {
        private readonly MarketplaceService marketplace;
        private readonly MarketplaceListingCache cache;

        public MarketplaceDiscoveryService(MarketplaceService marketplaceService, MarketplaceListingCache listingCache = null)
        {
            marketplace = marketplaceService ?? throw new ArgumentNullException(nameof(marketplaceService));
            cache = listingCache ?? new MarketplaceListingCache();
        }

        public async Task<List<BigInteger>> DiscoverActiveListingIdsAsync(int maxListingsToScan = 500, bool forceRefresh = false)
        {
            if (maxListingsToScan <= 0) throw new ArgumentOutOfRangeException(nameof(maxListingsToScan));
            if (!forceRefresh && cache.TryGet(out var cached)) return new List<BigInteger>(cached);

            var total = await marketplace.TotalListingsAsync();
            var capped = BigInteger.Min(total, new BigInteger(maxListingsToScan));
            var start = total > capped ? total - capped : BigInteger.Zero;
            var result = await DiscoverActiveListingIdsRangeAsync(start, total);
            cache.Store(result);
            return result;
        }

        public async Task<List<BigInteger>> DiscoverActiveListingIdsRangeAsync(BigInteger startInclusive, BigInteger endExclusive, int batchSize = 8)
        {
            if (startInclusive < BigInteger.Zero) throw new ArgumentOutOfRangeException(nameof(startInclusive));
            if (endExclusive < startInclusive) throw new ArgumentOutOfRangeException(nameof(endExclusive));
            if (batchSize <= 0) throw new ArgumentOutOfRangeException(nameof(batchSize));

            var result = new List<BigInteger>();
            for (var cursor = startInclusive; cursor < endExclusive; cursor += batchSize)
            {
                var batchEnd = BigInteger.Min(endExclusive, cursor + batchSize);
                var tasks = new List<Task<KeyValuePair<BigInteger, MarketplaceListingView>>>();
                for (var id = cursor; id < batchEnd; id += BigInteger.One)
                {
                    var captured = id;
                    tasks.Add(ReadPairAsync(captured));
                }

                var rows = await Task.WhenAll(tasks);
                foreach (var row in rows)
                    if (row.Value != null) result.Add(row.Key);
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

        public void InvalidateCache() => cache.Invalidate();

        private async Task<KeyValuePair<BigInteger, MarketplaceListingView>> ReadPairAsync(BigInteger listingId)
        {
            return new KeyValuePair<BigInteger, MarketplaceListingView>(listingId, await TryGetActiveListingAsync(listingId));
        }
    }
}
