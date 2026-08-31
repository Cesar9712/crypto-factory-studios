using System;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class TokenAttribute
    {
        public string trait_type;
        public string value;
    }

    [Serializable]
    public sealed class TokenMetadata
    {
        public string name;
        public string description;
        public string image;
        public string animation_url;
        public TokenAttribute[] attributes;

        public string ResolvedImageUrl => IpfsUri.Resolve(image);
        public string ResolvedAnimationUrl => IpfsUri.Resolve(animation_url);
    }
}
