using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;
using UnityEngine;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class ERC1155InventoryEntry
    {
        public string tokenId;
        public string balance;
        public string metadataUri;
    }

    public sealed class ERC1155InventoryController : MonoBehaviour
    {
        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private List<string> trackedTokenIds = new List<string>();
        [SerializeField] private List<ERC1155InventoryEntry> entries = new List<ERC1155InventoryEntry>();

        public IReadOnlyList<ERC1155InventoryEntry> Entries => entries;
        public event Action<IReadOnlyList<ERC1155InventoryEntry>> InventoryChanged;

        public async Task RefreshAsync()
        {
            if (web3 == null) throw new InvalidOperationException("CryptoQuestWeb3Controller is not assigned.");
            var wallet = web3.RequireWallet();
            var owner = await wallet.GetAddress();
            var service = new ERC1155InventoryService(web3);
            var next = new List<ERC1155InventoryEntry>();

            foreach (var rawId in trackedTokenIds)
            {
                if (!BigInteger.TryParse(rawId, out var tokenId) || tokenId < BigInteger.Zero)
                    continue;

                var balance = await service.BalanceOfAsync(owner, tokenId);
                if (balance <= BigInteger.Zero) continue;

                var uri = await service.TokenUriAsync(tokenId);
                next.Add(new ERC1155InventoryEntry
                {
                    tokenId = tokenId.ToString(),
                    balance = balance.ToString(),
                    metadataUri = uri ?? string.Empty
                });
            }

            entries = next;
            InventoryChanged?.Invoke(entries);
        }

        public void SetTrackedTokenIds(IEnumerable<BigInteger> tokenIds)
        {
            trackedTokenIds.Clear();
            if (tokenIds == null) return;
            foreach (var id in tokenIds)
            {
                if (id >= BigInteger.Zero) trackedTokenIds.Add(id.ToString());
            }
        }
    }
}
