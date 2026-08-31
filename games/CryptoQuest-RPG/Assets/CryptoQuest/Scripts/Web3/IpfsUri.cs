namespace CryptoQuest.Web3
{
    public static class IpfsUri
    {
        private const string Gateway = "https://ipfs.io/ipfs/";

        public static string Resolve(string uri)
        {
            if (string.IsNullOrWhiteSpace(uri)) return string.Empty;
            if (uri.StartsWith("ipfs://")) return Gateway + uri.Substring("ipfs://".Length).TrimStart('/');
            return uri;
        }
    }
}
