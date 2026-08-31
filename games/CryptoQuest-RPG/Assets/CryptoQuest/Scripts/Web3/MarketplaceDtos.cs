using System;
using System.Numerics;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class MarketplaceListingView
    {
        public BigInteger listingId;
        public string seller;
        public string assetContract;
        public BigInteger tokenId;
        public BigInteger quantity;
        public string currency;
        public BigInteger pricePerToken;
        public long startTimestamp;
        public long endTimestamp;
        public bool reserved;
    }

    [Serializable]
    public sealed class Web3TransactionResult
    {
        public string transactionHash;
        public bool submitted;
        public string action;
        public string contractAddress;
    }
}
