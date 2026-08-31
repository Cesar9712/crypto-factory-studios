using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Numerics;
using System.Reflection;

namespace CryptoQuest.Web3
{
    [Serializable]
    public sealed class MarketplaceListingView
    {
        public BigInteger listingId;
        public BigInteger tokenId;
        public BigInteger quantity;
        public BigInteger pricePerToken;
        public long startTimestamp;
        public long endTimestamp;
        public string listingCreator;
        public string assetContract;
        public string currency;
        public int tokenType;
        public int status;
        public bool reserved;

        public string seller => listingCreator;
        public bool IsCreated => status == 1;
    }

    public static class MarketplaceListingDecoder
    {
        public static MarketplaceListingView Decode(IReadOnlyList<object> raw)
        {
            var values = new List<object>();
            Flatten(raw, values);
            if (values.Count < 12)
                throw new InvalidOperationException($"Marketplace V3 getListing returned {values.Count} decoded fields; expected at least 12.");

            return new MarketplaceListingView
            {
                listingId = AsBigInteger(values[0]),
                tokenId = AsBigInteger(values[1]),
                quantity = AsBigInteger(values[2]),
                pricePerToken = AsBigInteger(values[3]),
                startTimestamp = AsLong(values[4]),
                endTimestamp = AsLong(values[5]),
                listingCreator = AsString(values[6]),
                assetContract = AsString(values[7]),
                currency = AsString(values[8]),
                tokenType = AsInt(values[9]),
                status = AsInt(values[10]),
                reserved = AsBool(values[11])
            };
        }

        private static void Flatten(object value, List<object> output)
        {
            if (value == null) return;
            if (IsLeaf(value))
            {
                output.Add(value);
                return;
            }

            var resultProperty = value.GetType().GetProperty("Result", BindingFlags.Instance | BindingFlags.Public);
            if (resultProperty != null)
            {
                Flatten(resultProperty.GetValue(value), output);
                return;
            }

            if (value is IEnumerable enumerable && value is not string && value is not byte[])
            {
                foreach (var child in enumerable) Flatten(child, output);
                return;
            }

            output.Add(value);
        }

        private static bool IsLeaf(object value) =>
            value is string || value is bool || value is byte || value is sbyte || value is short || value is ushort ||
            value is int || value is uint || value is long || value is ulong || value is BigInteger || value is decimal;

        private static BigInteger AsBigInteger(object value)
        {
            if (value is BigInteger big) return big;
            if (value == null) return BigInteger.Zero;
            return BigInteger.Parse(Convert.ToString(value, CultureInfo.InvariantCulture) ?? "0", CultureInfo.InvariantCulture);
        }

        private static long AsLong(object value)
        {
            var big = AsBigInteger(value);
            if (big > long.MaxValue || big < long.MinValue) throw new OverflowException("Marketplace timestamp exceeds Int64 range.");
            return (long)big;
        }

        private static int AsInt(object value)
        {
            var big = AsBigInteger(value);
            if (big > int.MaxValue || big < int.MinValue) throw new OverflowException("Marketplace enum exceeds Int32 range.");
            return (int)big;
        }

        private static string AsString(object value) => value?.ToString() ?? string.Empty;

        private static bool AsBool(object value)
        {
            if (value is bool boolean) return boolean;
            return bool.TryParse(value?.ToString(), out var parsed) && parsed;
        }
    }

    [Serializable]
    public sealed class Web3TransactionResult
    {
        public string transactionHash;
        public bool submitted;
        public string action;
        public string contractAddress;
    }
}
