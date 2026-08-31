using System;
using System.Numerics;
using System.Threading.Tasks;
using CryptoQuest.Web3;
using UnityEngine;

namespace CryptoQuest.Diagnostics
{
    public sealed class CryptoQuestRuntimeSmokeTest : MonoBehaviour
    {
        [SerializeField] private CryptoQuestWeb3Controller web3;
        [SerializeField] private TokenMetadataLoader metadataLoader;
        [SerializeField] private bool runOnStart;
        [SerializeField] private string smokeMetadataUri = "";
        [SerializeField] private string smokeTokenId = "0";

        public bool LastRunPassed { get; private set; }
        public string LastMessage { get; private set; } = "Not run";

        private async void Start()
        {
            if (runOnStart) await RunAsync();
        }

        public async Task<bool> RunAsync()
        {
            try
            {
                if (web3 == null) throw new InvalidOperationException("Web3 controller missing.");
                if (metadataLoader == null) throw new InvalidOperationException("Metadata loader missing.");
                if (CryptoQuestWeb3Controller.BaseSepoliaChainId != 84532) throw new InvalidOperationException("Wrong chain id.");

                if (!string.IsNullOrWhiteSpace(smokeMetadataUri))
                {
                    var tokenId = BigInteger.Parse(smokeTokenId);
                    var metadata = await metadataLoader.LoadAsync(smokeMetadataUri, tokenId);
                    if (metadata == null || string.IsNullOrWhiteSpace(metadata.name))
                        throw new InvalidOperationException("Metadata normalization failed.");
                }

                if (web3.ActiveWallet != null)
                {
                    var address = await web3.ActiveWallet.GetAddress();
                    if (string.IsNullOrWhiteSpace(address)) throw new InvalidOperationException("Connected wallet has no address.");
                }

                LastRunPassed = true;
                LastMessage = "CryptoQuest runtime smoke test OK";
                Debug.Log(LastMessage);
                return true;
            }
            catch (Exception ex)
            {
                LastRunPassed = false;
                LastMessage = ex.Message;
                Debug.LogError($"CryptoQuest runtime smoke test FAILED: {ex}");
                return false;
            }
        }
    }
}
