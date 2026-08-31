using System;
using System.Globalization;
using System.Numerics;

namespace CryptoQuest.Web3
{
    public static class TokenAmountFormatter
    {
        public static string FormatUnits(BigInteger value, int decimals, int maxFractionDigits = 6)
        {
            if (decimals < 0) throw new ArgumentOutOfRangeException(nameof(decimals));
            if (maxFractionDigits < 0) throw new ArgumentOutOfRangeException(nameof(maxFractionDigits));

            var negative = value.Sign < 0;
            var absolute = BigInteger.Abs(value);
            var divisor = BigInteger.Pow(10, decimals);
            var whole = decimals == 0 ? absolute : absolute / divisor;
            var remainder = decimals == 0 ? BigInteger.Zero : absolute % divisor;
            if (decimals == 0 || remainder.IsZero)
                return (negative ? "-" : string.Empty) + whole.ToString(CultureInfo.InvariantCulture);

            var fraction = remainder.ToString(CultureInfo.InvariantCulture).PadLeft(decimals, '0');
            if (fraction.Length > maxFractionDigits)
                fraction = fraction.Substring(0, maxFractionDigits);
            fraction = fraction.TrimEnd('0');
            return (negative ? "-" : string.Empty) + whole.ToString(CultureInfo.InvariantCulture) + (fraction.Length > 0 ? "." + fraction : string.Empty);
        }

        public static string FormatNative(BigInteger wei, string symbol = "ETH")
        {
            return $"{FormatUnits(wei, 18, 6)} {symbol}";
        }
    }
}
