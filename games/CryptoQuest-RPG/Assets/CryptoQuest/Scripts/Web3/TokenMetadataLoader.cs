using System;
using System.Numerics;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

namespace CryptoQuest.Web3
{
    public sealed class TokenMetadataLoader : MonoBehaviour
    {
        public async Task<string> LoadRawAsync(string metadataUri, BigInteger tokenId)
        {
            var expanded = ExpandErc1155Uri(metadataUri, tokenId);
            var url = IpfsUri.Resolve(expanded);
            if (string.IsNullOrWhiteSpace(url)) throw new ArgumentException("Metadata URI is empty.", nameof(metadataUri));

            using var request = UnityWebRequest.Get(url);
            var operation = request.SendWebRequest();
            while (!operation.isDone) await Task.Yield();

            if (request.result != UnityWebRequest.Result.Success)
                throw new InvalidOperationException($"Metadata request failed: {request.responseCode} {request.error}");
            return request.downloadHandler.text;
        }

        public async Task<TokenMetadata> LoadAsync(string metadataUri, BigInteger tokenId)
        {
            var raw = await LoadRawAsync(metadataUri, tokenId);
            var metadata = JsonUtility.FromJson<TokenMetadata>(raw);
            if (metadata == null) throw new InvalidOperationException("Invalid token metadata JSON.");
            return MetadataNormalizer.Normalize(metadata, $"Token #{tokenId}", ExpandErc1155Uri(metadataUri, tokenId));
        }

        public Task<TokenMetadata> LoadAsync(string metadataUri) => LoadAsync(metadataUri, BigInteger.Zero);

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

        public static string ExpandErc1155Uri(string uri, BigInteger tokenId)
        {
            if (string.IsNullOrWhiteSpace(uri)) return string.Empty;
            var idHex = tokenId.ToString("x").PadLeft(64, '0');
            return uri.Replace("{id}", idHex).Replace("%7Bid%7D", idHex).Replace("%7bid%7d", idHex);
        }
    }
}
