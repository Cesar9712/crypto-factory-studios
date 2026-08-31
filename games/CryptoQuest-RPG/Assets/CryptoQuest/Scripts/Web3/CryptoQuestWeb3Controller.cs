using System;
using System.Numerics;
using System.Threading.Tasks;
using Thirdweb;
using UnityEngine;

namespace CryptoQuest.Web3
{
    public sealed class CryptoQuestWeb3Controller : MonoBehaviour
    {
        public const ulong BaseSepoliaChainId = 84532;

        [Header("Contracts - Base Sepolia")]
        [SerializeField] private string inventoryContractAddress = "";
        [SerializeField] private string marketplaceContractAddress = "";

        public string InventoryContractAddress => inventoryContractAddress;
        public string MarketplaceContractAddress => marketplaceContractAddress;
        public IThirdwebWallet ActiveWallet => ThirdwebManager.Instance != null ? ThirdwebManager.Instance.ActiveWallet : null;

        public async Task<IThirdwebWallet> ConnectGuestAsync()
        {
            var options = new WalletOptions(
                provider: WalletProvider.InAppWallet,
                chainId: new BigInteger(BaseSepoliaChainId),
                inAppWalletOptions: new InAppWalletOptions(authprovider: AuthProvider.Guest)
            );

            var wallet = await ThirdwebManager.Instance.ConnectWallet(options);
            Debug.Log($"[CryptoQuest/Web3] Connected: {await wallet.GetAddress()}");
            return wallet;
        }

        public async Task<IThirdwebWallet> ConnectGoogleAsync()
        {
            var options = new WalletOptions(
                provider: WalletProvider.InAppWallet,
                chainId: new BigInteger(BaseSepoliaChainId),
                inAppWalletOptions: new InAppWalletOptions(authprovider: AuthProvider.Google)
            );

            var wallet = await ThirdwebManager.Instance.ConnectWallet(options);
            Debug.Log($"[CryptoQuest/Web3] Connected: {await wallet.GetAddress()}");
            return wallet;
        }

        public IThirdwebWallet RequireWallet()
        {
            var wallet = ActiveWallet;
            if (wallet == null) throw new InvalidOperationException("No Thirdweb wallet is connected.");
            return wallet;
        }

        public Task<ThirdwebContract> GetInventoryContractAsync()
        {
            RequireAddress(inventoryContractAddress, "Inventory");
            return ThirdwebManager.Instance.GetContract(inventoryContractAddress, new BigInteger(BaseSepoliaChainId));
        }

        public Task<ThirdwebContract> GetMarketplaceContractAsync()
        {
            RequireAddress(marketplaceContractAddress, "Marketplace");
            return ThirdwebManager.Instance.GetContract(marketplaceContractAddress, new BigInteger(BaseSepoliaChainId));
        }

        public void ConfigureContracts(string inventoryAddress, string marketplaceAddress)
        {
            RequireAddress(inventoryAddress, "Inventory");
            RequireAddress(marketplaceAddress, "Marketplace");
            inventoryContractAddress = inventoryAddress;
            marketplaceContractAddress = marketplaceAddress;
        }

        private static void RequireAddress(string address, string label)
        {
            if (string.IsNullOrWhiteSpace(address) || !address.StartsWith("0x", StringComparison.OrdinalIgnoreCase) || address.Length != 42)
                throw new InvalidOperationException($"{label} contract address is not configured or invalid.");
        }
    }
}
