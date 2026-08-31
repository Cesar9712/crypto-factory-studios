using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

namespace CryptoQuest.Web3
{
    public sealed class TokenMetadataLoader : MonoBehaviour
    {
        public async Task<TokenMetadata> LoadAsync(string metadataUri)
        {
            var url = IpfsUri.Resolve(metadataUri);
            if (string.IsNullOrWhiteSpace(url)) throw new ArgumentException("Metadata URI is empty.", nameof(metadataUri));

            using var request = UnityWebRequest.Get(url);
            var operation = request.SendWebRequest();
            while (!operation.isDone) await Task.Yield();

            if (request.result != UnityWebRequest.Result.Success)
                throw new InvalidOperationException($"Metadata request failed: {request.responseCode} {request.error}");

            var json = request.downloadHandler.text;
            var metadata = JsonUtility.FromJson<TokenMetadata>(json);
            if (metadata == null) throw new InvalidOperationException("Invalid token metadata JSON.");
            return metadata;
        }

        public async Task<Texture2D> LoadImageAsync(TokenMetadata metadata)
        {
            var url = metadata?.ResolvedImageUrl;
            if (string.IsNullOrWhiteSpace(url)) return null;

            using var request = UnityWebRequestTexture.GetTexture(url);
            var operation = request.SendWebRequest();
            while (!operation.isDone) await Task.Yield();

            if (request.result != UnityWebRequest.Result.Success)
                throw new InvalidOperationException($"Image request failed: {request.responseCode} {request.error}");

            return DownloadHandlerTexture.GetContent(request);
        }
    }
}
