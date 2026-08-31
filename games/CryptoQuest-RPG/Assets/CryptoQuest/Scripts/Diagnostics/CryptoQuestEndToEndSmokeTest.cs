using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;
using CryptoQuest.Web3;
using UnityEngine;

namespace CryptoQuest.Diagnostics
{
    public sealed class CryptoQuestEndToEndSmokeTest : MonoBehaviour
    {
        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private TokenMetadataLoader metadataLoader;
        [SerializeField] private string[] tokenIds = Array.Empty<string>();
        [SerializeField, Min(1)] private int maxListingsToScan = 100;
        [SerializeField] private bool runOnStart;

        public bool LastRunPassed { get; private set; }
        public string LastMessage { get; private set; } = "Not run";

        private async void Start()
        {
            if (runOnStart) await RunAsync();
        }

        public async Task<bool> RunAsync()
        {
            try
            {
                if (web3 == null) throw new InvalidOperationException("Web3 controller missing.");
                if (metadataLoader == null) throw new InvalidOperationException("Metadata loader missing.");
                if (CryptoQuestWeb3Controller.BaseSepoliaChainId != 84532) throw new InvalidOperationException("Expected Base Sepolia 84532.");

                var wallet = web3.RequireWallet();
                var owner = await wallet.GetAddress();
                if (string.IsNullOrWhiteSpace(owner)) throw new InvalidOperationException("Wallet address unavailable.");

                var parsedIds = ParseIds(tokenIds);
                var inventoryService = new ERC1155InventoryService(web3);
                var catalog = new InventoryCatalogService(inventoryService, metadataLoader);
                var owned = await catalog.LoadOwnedAsync(owner, parsedIds);

                foreach (var item in owned)
                {
                    if (item == null || string.IsNullOrWhiteSpace(item.tokenId))
                        throw new InvalidOperationException("Inventory normalization failed.");
                    if (item.Balance <= BigInteger.Zero)
                        throw new InvalidOperationException("Owned inventory item has non-positive balance.");
                }

                var marketplace = new MarketplaceService(web3);
                var discovery = new MarketplaceDiscoveryService(marketplace);
                var listingIds = await discovery.DiscoverActiveListingIdsAsync(maxListingsToScan, true);
                var merger = new InventoryMarketplaceService(marketplace);
                var merged = await merger.MergeManyAsync(owned, listingIds, owner);

                if (merged.Count != owned.Count)
                    throw new InvalidOperationException("Inventory/market merge lost owned items.");

                LastRunPassed = true;
                LastMessage = $"E2E read smoke OK: wallet={owner}, owned={owned.Count}, activeListings={listingIds.Count}.";
                Debug.Log($"[CryptoQuest/Smoke] {LastMessage}");
                return true;
            }
            catch (Exception ex)
            {
                LastRunPassed = false;
                LastMessage = ex.Message;
                Debug.LogError($"[CryptoQuest/Smoke] E2E FAILED: {ex}");
                return false;
            }
        }

        private static List<BigInteger> ParseIds(IEnumerable<string> values)
        {
            var result = new List<BigInteger>();
            if (values == null) return result;
            foreach (var value in values)
                if (BigInteger.TryParse(value, out var id) && id >= BigInteger.Zero)
                    result.Add(id);
            return result;
        }
    }
}
