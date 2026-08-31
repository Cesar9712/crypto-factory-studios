using System;
using System.Collections.Generic;

namespace CryptoQuest.Web3
{
    public static class MetadataNormalizer
    {
        public static TokenMetadata Normalize(TokenMetadata source, string fallbackName, string metadataUri)
        {
            source ??= new TokenMetadata();
            source.name = Clean(source.name, fallbackName);
            source.description = Clean(source.description, string.Empty);
            source.image = NormalizeUri(source.image, metadataUri);
            source.animation_url = NormalizeUri(source.animation_url, metadataUri);
            source.attributes = NormalizeAttributes(source.attributes);
            return source;
        }

        private static TokenAttribute[] NormalizeAttributes(TokenAttribute[] source)
        {
            if (source == null || source.Length == 0) return Array.Empty<TokenAttribute>();
            var result = new List<TokenAttribute>(source.Length);
            foreach (var item in source)
            {
                if (item == null) continue;
                var trait = Clean(item.trait_type, string.Empty);
                var value = Clean(item.value, string.Empty);
                if (trait.Length == 0 && value.Length == 0) continue;
                result.Add(new TokenAttribute { trait_type = trait, value = value });
            }
            return result.ToArray();
        }

        private static string NormalizeUri(string value, string metadataUri)
        {
            value = Clean(value, string.Empty);
            if (value.Length == 0) return string.Empty;
            if (value.StartsWith("ipfs://", StringComparison.OrdinalIgnoreCase) ||
                value.StartsWith("http://", StringComparison.OrdinalIgnoreCase) ||
                value.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                return value;

            var resolvedMetadata = IpfsUri.Resolve(metadataUri);
            if (Uri.TryCreate(resolvedMetadata, UriKind.Absolute, out var baseUri) && Uri.TryCreate(baseUri, value, out var combined))
                return combined.ToString();
            return value;
        }

        private static string Clean(string value, string fallback) => string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
    }
}
