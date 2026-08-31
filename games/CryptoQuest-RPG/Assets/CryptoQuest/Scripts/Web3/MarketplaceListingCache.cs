using System;
using System.Collections.Generic;
using System.Numerics;

namespace CryptoQuest.Web3
{
    public sealed class MarketplaceListingCache
    {
        private readonly TimeSpan ttl;
        private DateTimeOffset expiresAt = DateTimeOffset.MinValue;
        private readonly List<BigInteger> listingIds = new List<BigInteger>();

        public MarketplaceListingCache(TimeSpan? timeToLive = null)
        {
            ttl = timeToLive ?? TimeSpan.FromSeconds(30);
        }

        public bool TryGet(out IReadOnlyList<BigInteger> ids)
        {
            if (DateTimeOffset.UtcNow >= expiresAt || listingIds.Count == 0)
            {
                ids = Array.Empty<BigInteger>();
                return false;
            }

            ids = listingIds.ToArray();
            return true;
        }

        public void Store(IEnumerable<BigInteger> ids)
        {
            listingIds.Clear();
            if (ids != null)
            {
                foreach (var id in ids)
                    if (id >= BigInteger.Zero) listingIds.Add(id);
            }
            expiresAt = DateTimeOffset.UtcNow.Add(ttl);
        }

        public void Invalidate()
        {
            listingIds.Clear();
            expiresAt = DateTimeOffset.MinValue;
        }
    }
}
