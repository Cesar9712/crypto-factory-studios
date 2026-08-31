using System;
using UnityEngine;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class Web3RuntimeConfig
    {
        [SerializeField] private string thirdwebClientId = string.Empty;
        [SerializeField] private string inventoryContractAddress = string.Empty;
        [SerializeField] private string marketplaceContractAddress = string.Empty;

        public string ThirdwebClientId => thirdwebClientId;
        public string InventoryContractAddress => inventoryContractAddress;
        public string MarketplaceContractAddress => marketplaceContractAddress;

        public void Validate()
        {
            if (string.IsNullOrWhiteSpace(thirdwebClientId))
                throw new InvalidOperationException("Thirdweb Client ID is not configured.");
            if (string.IsNullOrWhiteSpace(inventoryContractAddress))
                throw new InvalidOperationException("ERC-1155 inventory contract address is not configured.");
            if (string.IsNullOrWhiteSpace(marketplaceContractAddress))
                throw new InvalidOperationException("Marketplace V3 contract address is not configured.");
        }
    }
}
