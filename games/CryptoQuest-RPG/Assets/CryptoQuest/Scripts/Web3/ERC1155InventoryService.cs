using System;
using System.Collections.Generic;
using System.Numerics;
using System.Threading.Tasks;
using Thirdweb;

namespace CryptoQuest.Web3
{
    public sealed class ERC1155InventoryService
    {
        private readonly CryptoQuestWeb3Controller web3;

        public ERC1155InventoryService(CryptoQuestWeb3Controller web3Controller)
        {
            web3 = web3Controller ?? throw new ArgumentNullException(nameof(web3Controller));
        }

        public async Task<BigInteger> BalanceOfAsync(string owner, BigInteger tokenId)
        {
            RequireAddress(owner, nameof(owner));
            var contract = await web3.GetInventoryContractAsync();
            return await contract.Read<BigInteger>("balanceOf", owner, tokenId);
        }

        public async Task<List<BigInteger>> BalanceOfBatchAsync(IReadOnlyList<string> owners, IReadOnlyList<BigInteger> tokenIds)
        {
            if (owners == null || tokenIds == null || owners.Count == 0 || owners.Count != tokenIds.Count)
                throw new ArgumentException("owners/tokenIds must be non-empty and have identical lengths.");

            var ownerArray = new string[owners.Count];
            var idArray = new BigInteger[tokenIds.Count];
            for (var i = 0; i < owners.Count; i++)
            {
                RequireAddress(owners[i], $"owners[{i}]");
                ownerArray[i] = owners[i];
                idArray[i] = tokenIds[i];
            }

            var contract = await web3.GetInventoryContractAsync();
            return await contract.Read<List<BigInteger>>("balanceOfBatch", ownerArray, idArray);
        }

        public async Task<string> TokenUriAsync(BigInteger tokenId)
        {
            var contract = await web3.GetInventoryContractAsync();
            return await contract.Read<string>("uri", tokenId);
        }

        public async Task<bool> IsApprovedForMarketplaceAsync(string owner)
        {
            RequireAddress(owner, nameof(owner));
            var marketplace = web3.MarketplaceContractAddress;
            RequireAddress(marketplace, nameof(marketplace));
            var contract = await web3.GetInventoryContractAsync();
            return await contract.Read<bool>("isApprovedForAll", owner, marketplace);
        }

        public async Task<object> SetMarketplaceApprovalAsync(bool approved)
        {
            var wallet = web3.RequireWallet();
            var marketplace = web3.MarketplaceContractAddress;
            RequireAddress(marketplace, nameof(marketplace));
            var contract = await web3.GetInventoryContractAsync();
            return await contract.Write(wallet, "setApprovalForAll", BigInteger.Zero, marketplace, approved);
        }

        public async Task<object> TransferAsync(string to, BigInteger tokenId, BigInteger amount)
        {
            RequireAddress(to, nameof(to));
            if (amount <= BigInteger.Zero) throw new ArgumentOutOfRangeException(nameof(amount));

            var wallet = web3.RequireWallet();
            var from = await wallet.GetAddress();
            var contract = await web3.GetInventoryContractAsync();
            return await contract.Write(wallet, "safeTransferFrom", BigInteger.Zero, from, to, tokenId, amount, Array.Empty<byte>());
        }

        private static void RequireAddress(string address, string label)
        {
            if (string.IsNullOrWhiteSpace(address) || !address.StartsWith("0x", StringComparison.OrdinalIgnoreCase) || address.Length != 42)
                throw new ArgumentException($"Invalid EVM address: {label}");
        }
    }
}
