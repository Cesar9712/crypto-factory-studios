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

        public static Web3RuntimeConfig Create(string clientId, string inventoryAddress, string marketplaceAddress)
        {
            return new Web3RuntimeConfig
            {
                thirdwebClientId = clientId?.Trim() ?? string.Empty,
                inventoryContractAddress = inventoryAddress?.Trim() ?? string.Empty,
                marketplaceContractAddress = marketplaceAddress?.Trim() ?? string.Empty
            };
        }

        public void Validate()
        {
            if (string.IsNullOrWhiteSpace(thirdwebClientId))
                throw new InvalidOperationException("Thirdweb Client ID is not configured.");
            RequireAddress(inventoryContractAddress, "ERC-1155 inventory");
            RequireAddress(marketplaceContractAddress, "Marketplace V3");
        }

        private static void RequireAddress(string value, string label)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Length != 42 || !value.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"{label} contract address is invalid.");
        }
    }
}
