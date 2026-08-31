using System;
using System.Numerics;
using System.Threading.Tasks;
using CryptoQuest.Web3;
using UnityEngine;

namespace CryptoQuest.UI
{
    public sealed class MarketplaceActionController : MonoBehaviour
    {
        private const string NativeTokenAddress = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE";

        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private string listingPriceWei = "100000000000000";
        [SerializeField] private uint listingDurationHours = 24;

        private bool busy;

        public async void Buy(InventoryMarketItem item, Func<Task> after)
        {
            if (busy || item?.listing == null || !item.canBuy) return;
            busy = true;
            try
            {
                var listing = item.listing;
                var service = new MarketplaceService(RequireWeb3());
                var total = listing.pricePerToken;
                await service.AcquireListingAsync(listing.listingId, BigInteger.One, listing.currency, total, IsNative(listing.currency));
                await InvokeAfter(after);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
            finally
            {
                busy = false;
            }
        }

        public async void Sell(InventoryMarketItem item, Func<Task> after)
        {
            if (busy || item?.inventory == null || item.isListed || !item.inventory.Owned) return;
            busy = true;
            try
            {
                if (!BigInteger.TryParse(listingPriceWei, out var price) || price <= BigInteger.Zero)
                    throw new InvalidOperationException("listingPriceWei must be a positive integer.");

                var controller = RequireWeb3();
                var inventory = new ERC1155InventoryService(controller);
                var owner = await controller.RequireWallet().GetAddress();
                if (!await inventory.IsApprovedForMarketplaceAsync(owner))
                    await inventory.SetMarketplaceApprovalAsync(true);

                var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                var end = now + Math.Max(1, listingDurationHours) * 3600L;
                var market = new MarketplaceService(controller);
                await market.CreateListingAsync(
                    item.inventory.TokenId,
                    BigInteger.One,
                    NativeTokenAddress,
                    price,
                    (ulong)now,
                    (ulong)end);

                await InvokeAfter(after);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
            finally
            {
                busy = false;
            }
        }

        public async void Cancel(InventoryMarketItem item, Func<Task> after)
        {
            if (busy || item?.listing == null || !item.canCancel) return;
            busy = true;
            try
            {
                var market = new MarketplaceService(RequireWeb3());
                await market.CancelListingAsync(item.listing.listingId);
                await InvokeAfter(after);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
            finally
            {
                busy = false;
            }
        }

        private CryptoQuestWeb3Controller RequireWeb3()
        {
            if (web3 == null) throw new InvalidOperationException("CryptoQuestWeb3Controller is not assigned.");
            return web3;
        }

        private static bool IsNative(string currency) =>
            string.Equals(currency, NativeTokenAddress, StringComparison.OrdinalIgnoreCase);

        private static async Task InvokeAfter(Func<Task> callback)
        {
            if (callback != null) await callback();
        }
    }
}
