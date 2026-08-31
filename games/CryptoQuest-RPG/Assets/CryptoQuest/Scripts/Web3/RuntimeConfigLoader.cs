using System;
using System.IO;
using Thirdweb.Unity;
using UnityEngine;

namespace CryptoQuest.Web3
{
    public sealed class RuntimeConfigLoader : MonoBehaviour
    {
        public const string ClientIdEnv = "CRYPTOQUEST_THIRDWEB_CLIENT_ID";
        public const string InventoryEnv = "CRYPTOQUEST_ERC1155_ADDRESS";
        public const string MarketplaceEnv = "CRYPTOQUEST_MARKETPLACE_ADDRESS";

        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private string streamingAssetsFileName = "cryptoquest.runtime.json";
        [SerializeField] private bool applyOnAwake = true;

        public static Web3RuntimeConfig Current { get; private set; }

        private void Awake()
        {
            if (applyOnAwake) Apply();
        }

        public void Apply()
        {
            var config = Load();
            config.Validate();
            if (web3 == null) throw new InvalidOperationException("CryptoQuestWeb3Controller is not assigned.");
            if (ThirdwebManager.Instance == null) throw new InvalidOperationException("ThirdwebManager is missing from the active scene.");

            var injected = ThirdwebClientIdInjector.TryApply(config.ThirdwebClientId);
            if (!injected && !ThirdwebManager.Instance.Initialized)
                throw new InvalidOperationException("Thirdweb Client ID could not be injected before manager initialization.");

            if (!ThirdwebManager.Instance.Initialized)
                ThirdwebManager.Instance.Initialize();

            web3.ConfigureContracts(config.InventoryContractAddress, config.MarketplaceContractAddress);
            Current = config;
            Debug.Log("[CryptoQuest/Web3] Runtime config applied for Base Sepolia 84532.");
        }

        public Web3RuntimeConfig Load()
        {
            var fileConfig = LoadFile();
            var clientId = FirstNonEmpty(Environment.GetEnvironmentVariable(ClientIdEnv), fileConfig?.ThirdwebClientId);
            var inventory = FirstNonEmpty(Environment.GetEnvironmentVariable(InventoryEnv), fileConfig?.InventoryContractAddress);
            var marketplace = FirstNonEmpty(Environment.GetEnvironmentVariable(MarketplaceEnv), fileConfig?.MarketplaceContractAddress);
            return Web3RuntimeConfig.Create(clientId, inventory, marketplace);
        }

        private Web3RuntimeConfig LoadFile()
        {
            var path = Path.Combine(Application.streamingAssetsPath, streamingAssetsFileName);
            if (!File.Exists(path)) return null;
            var json = File.ReadAllText(path);
            if (string.IsNullOrWhiteSpace(json)) return null;
            return JsonUtility.FromJson<Web3RuntimeConfig>(json);
        }

        private static string FirstNonEmpty(string first, string second) =>
            !string.IsNullOrWhiteSpace(first) ? first.Trim() : (second ?? string.Empty).Trim();
    }
}
