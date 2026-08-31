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

        public IThirdwebWallet ActiveWallet => ThirdwebManager.Instance.ActiveWallet;

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

        private static void RequireAddress(string address, string label)
        {
            if (string.IsNullOrWhiteSpace(address))
                throw new System.InvalidOperationException($"{label} contract address is not configured.");
        }
    }
}
