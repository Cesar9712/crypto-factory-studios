using System;
using System.Numerics;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class InventoryItem
    {
        public string tokenId;
        public string balance;
        public string metadataUri;
        public string name;
        public string description;
        public string imageUrl;
        public string animationUrl;
        public TokenAttribute[] attributes = Array.Empty<TokenAttribute>();

        public BigInteger TokenId => BigInteger.Parse(tokenId);
        public BigInteger Balance => BigInteger.Parse(balance);
        public bool Owned => Balance > BigInteger.Zero;
    }
}
