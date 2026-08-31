using System;
using System.Numerics;
using System.Threading.Tasks;
using Thirdweb;

namespace CryptoQuest.Web3
{
    public sealed class MarketplaceService
    {
        private readonly CryptoQuestWeb3Controller web3;

        public MarketplaceService(CryptoQuestWeb3Controller controller)
        {
            web3 = controller ?? throw new ArgumentNullException(nameof(controller));
        }

        public async Task<object> CreateListingAsync(BigInteger tokenId, BigInteger quantity, string currency, BigInteger unitPrice, ulong startTime, ulong endTime)
        {
            if (quantity <= 0) throw new ArgumentOutOfRangeException(nameof(quantity));
            if (endTime <= startTime) throw new ArgumentException("Invalid listing window.");
            var wallet = web3.RequireWallet();
            var market = await web3.GetMarketplaceContractAsync();
            object[] listing = { web3.InventoryContractAddress, tokenId, quantity, currency, unitPrice, new BigInteger(startTime), new BigInteger(endTime), false };
            return await market.Write(wallet, "createListing", BigInteger.Zero, listing);
        }

        public async Task<object> CancelListingAsync(BigInteger listingId)
        {
            var market = await web3.GetMarketplaceContractAsync();
            return await market.Write(web3.RequireWallet(), "cancelListing", BigInteger.Zero, listingId);
        }

        public async Task<object> AcquireListingAsync(BigInteger listingId, BigInteger quantity, string currency, BigInteger totalPrice, bool nativeCurrency)
        {
            if (quantity <= 0) throw new ArgumentOutOfRangeException(nameof(quantity));
            var wallet = web3.RequireWallet();
            var recipient = await wallet.GetAddress();
            var market = await web3.GetMarketplaceContractAsync();
            return await market.Write(wallet, "buyFromListing", nativeCurrency ? totalPrice : BigInteger.Zero, listingId, recipient, quantity, currency, totalPrice);
        }

        public async Task<BigInteger> TotalListingsAsync()
        {
            var market = await web3.GetMarketplaceContractAsync();
            return await market.Read<BigInteger>("totalListings");
        }
    }
}
