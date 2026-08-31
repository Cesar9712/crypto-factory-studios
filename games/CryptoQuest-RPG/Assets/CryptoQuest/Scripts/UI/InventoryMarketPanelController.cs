using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;
using CryptoQuest.Web3;
using UnityEngine;
using UnityEngine.Networking;

namespace CryptoQuest.UI
{
    public sealed class InventoryMarketPanelController : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private TokenMetadataLoader metadataLoader;
        [SerializeField] private MarketplaceActionController actions;

        [Header("UI")]
        [SerializeField] private Transform contentRoot;
        [SerializeField] private InventoryMarketItemView itemPrefab;

        [Header("Discovery")]
        [SerializeField] private string[] tokenIds = Array.Empty<string>();
        [SerializeField] private string[] listingIds = Array.Empty<string>();
        [SerializeField] private bool refreshOnEnable = true;

        private readonly List<GameObject> spawned = new List<GameObject>();
        private bool refreshing;

        private async void OnEnable()
        {
            if (refreshOnEnable)
                await RefreshAsync();
        }

        public async Task RefreshAsync()
        {
            if (refreshing) return;
            refreshing = true;
            try
            {
                if (web3 == null || metadataLoader == null || contentRoot == null || itemPrefab == null)
                    throw new InvalidOperationException("Inventory market panel dependencies are not assigned.");

                var wallet = web3.RequireWallet();
                var owner = await wallet.GetAddress();
                var parsedTokenIds = ParseIds(tokenIds);
                var parsedListingIds = ParseIds(listingIds);

                var inventoryService = new ERC1155InventoryService(web3);
                var catalog = new InventoryCatalogService(inventoryService, metadataLoader);
                var owned = await catalog.LoadOwnedAsync(owner, parsedTokenIds);

                var marketplace = new MarketplaceService(web3);
                var merger = new InventoryMarketplaceService(marketplace);
                var merged = await merger.MergeManyAsync(owned, parsedListingIds, owner);

                Clear();
                foreach (var item in merged)
                {
                    var view = Instantiate(itemPrefab, contentRoot);
                    spawned.Add(view.gameObject);
                    var texture = await LoadTextureAsync(item.inventory?.imageUrl);
                    view.Bind(item, texture, HandleBuy, HandleSell, HandleCancel);
                }
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
            }
            finally
            {
                refreshing = false;
            }
        }

        private void HandleBuy(InventoryMarketItem item) => actions?.Buy(item, RefreshAsync);
        private void HandleSell(InventoryMarketItem item) => actions?.Sell(item, RefreshAsync);
        private void HandleCancel(InventoryMarketItem item) => actions?.Cancel(item, RefreshAsync);

        private void Clear()
        {
            foreach (var go in spawned)
                if (go != null) Destroy(go);
            spawned.Clear();
        }

        private static List<BigInteger> ParseIds(IReadOnlyList<string> ids)
        {
            var result = new List<BigInteger>();
            if (ids == null) return result;
            foreach (var value in ids)
                if (BigInteger.TryParse(value, out var id) && id >= BigInteger.Zero)
                    result.Add(id);
            return result;
        }

        private static async Task<Texture2D> LoadTextureAsync(string url)
        {
            if (string.IsNullOrWhiteSpace(url)) return null;
            using var request = UnityWebRequestTexture.GetTexture(IpfsUri.Resolve(url));
            var operation = request.SendWebRequest();
            while (!operation.isDone) await Task.Yield();
            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogWarning($"[CryptoQuest/UI] Image load failed: {request.responseCode} {request.error}");
                return null;
            }
            return DownloadHandlerTexture.GetContent(request);
        }
    }
}
