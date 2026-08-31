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
        public event Action<string> TransactionSucceeded;
        public event Action<string, Exception> TransactionFailed;

        public async Task<object> ExecuteContractWriteAsync(ThirdwebContract contract, string methodName, BigInteger weiValue, params object[] parameters)
        {
            if (contract == null) throw new ArgumentNullException(nameof(contract));
            if (string.IsNullOrWhiteSpace(methodName)) throw new ArgumentException("Method name is required.", nameof(methodName));
            if (web3 == null) throw new InvalidOperationException("CryptoQuestWeb3Controller is not assigned.");

            TransactionStarted?.Invoke(methodName);
            try
            {
                var receipt = await contract.Write(web3.RequireWallet(), methodName, weiValue, parameters);
                TransactionSucceeded?.Invoke(methodName);
                return receipt;
            }
            catch (Exception ex)
            {
                TransactionFailed?.Invoke(methodName, ex);
                Debug.LogException(ex);
                throw;
            }
        }

        public async Task<string> CurrentWalletAddressAsync()
        {
            return await web3.RequireWallet().GetAddress();
        }

        public Task<ThirdwebContract> InventoryContractAsync() => web3.GetInventoryContractAsync();
        public Task<ThirdwebContract> MarketplaceContractAsync() => web3.GetMarketplaceContractAsync();
    }
}
