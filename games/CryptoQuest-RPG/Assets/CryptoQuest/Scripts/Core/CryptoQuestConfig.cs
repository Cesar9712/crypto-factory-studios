using UnityEngine;

namespace CryptoQuest.Core
{
    [CreateAssetMenu(menuName = "CryptoQuest/Runtime Config", fileName = "CryptoQuestConfig")]
    public sealed class CryptoQuestConfig : ScriptableObject
    {
        public const ulong BaseSepoliaChainId = 84532;

        [Header("Platform Backend")]
        public string backendBaseUrl = "https://crypto-factory-studios.onrender.com";

        [Header("Thirdweb")]
        [Tooltip("Public Thirdweb Client ID only. Never put Secret Key here.")]
        public string thirdwebClientId = "";
        public string applicationId = "com.cryptofactorystudios.cryptoquest";

        [Header("Contracts - Base Sepolia")]
        public string inventoryContractAddress = "";
        public string marketplaceContractAddress = "";
    }
}
