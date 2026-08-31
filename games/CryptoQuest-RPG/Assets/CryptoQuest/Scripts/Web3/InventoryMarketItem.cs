using System;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class InventoryMarketItem
    {
        public InventoryItem inventory;
        public MarketplaceListingView listing;
        public bool isListed;
        public bool isSeller;
        public bool canBuy;
        public bool canCancel;
    }
}
