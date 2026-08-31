using System;
using System.Numerics;
using System.Threading.Tasks;
using Thirdweb;
using UnityEngine;

namespace CryptoQuest.Web3
{
    public sealed class ThirdwebTransactionController : MonoBehaviour
    {
        [SerializeField] private CryptoQuestWeb3Controller web3;

        public event Action<string> TransactionStarted;
        public event Action<Web3TransactionResult> TransactionSucceeded;
        public event Action<string, Exception> TransactionFailed;

        public async Task<Web3TransactionResult> ExecuteContractWriteAsync(ThirdwebContract contract, string methodName, BigInteger weiValue, string contractAddress, params object[] parameters)
        {
            if (contract == null) throw new ArgumentNullException(nameof(contract));
            if (string.IsNullOrWhiteSpace(methodName)) throw new ArgumentException("Method name is required.", nameof(methodName));
            if (web3 == null) throw new InvalidOperationException("CryptoQuestWeb3Controller is not assigned.");

            TransactionStarted?.Invoke(methodName);
            try
            {
                var receipt = await contract.Write(web3.RequireWallet(), methodName, weiValue, parameters);
                var normalized = TransactionReceiptNormalizer.Normalize(receipt, methodName, contractAddress);
                TransactionSucceeded?.Invoke(normalized);
                return normalized;
            }
            catch (Exception ex)
            {
                TransactionFailed?.Invoke(methodName, ex);
                Debug.LogException(ex);
                throw;
            }
        }

        public async Task<string> CurrentWalletAddressAsync() => await web3.RequireWallet().GetAddress();
        public Task<ThirdwebContract> InventoryContractAsync() => web3.GetInventoryContractAsync();
        public Task<ThirdwebContract> MarketplaceContractAsync() => web3.GetMarketplaceContractAsync();
    }
}
