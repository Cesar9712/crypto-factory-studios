using System;
using System.Reflection;

namespace CryptoQuest.Web3
{
    public static class TransactionReceiptNormalizer
    {
        public static Web3TransactionResult Normalize(object receipt, string action, string contractAddress)
        {
            return new Web3TransactionResult
            {
                transactionHash = ReadString(receipt, "TransactionHash", "transactionHash", "Hash", "hash"),
                submitted = receipt != null,
                action = action ?? string.Empty,
                contractAddress = contractAddress ?? string.Empty
            };
        }

        private static string ReadString(object source, params string[] names)
        {
            if (source == null) return string.Empty;
            var type = source.GetType();
            foreach (var name in names)
            {
                var property = type.GetProperty(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.IgnoreCase);
                if (property != null)
                {
                    var value = property.GetValue(source);
                    if (value != null) return value.ToString();
                }
                var field = type.GetField(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.IgnoreCase);
                if (field != null)
                {
                    var value = field.GetValue(source);
                    if (value != null) return value.ToString();
                }
            }
            return source.ToString() ?? string.Empty;
        }
    }
}
