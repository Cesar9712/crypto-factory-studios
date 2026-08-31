using System.Collections.Generic;
using System.Numerics;
using CryptoQuest.Web3;
using NUnit.Framework;

namespace CryptoQuest.Tests.EditMode
{
    public sealed class MarketplacePipelineTests
    {
        private sealed class ResultBox
        {
            public object Result { get; set; }
        }

        [Test]
        public void ListingDecoder_DecodesMarketplaceV3TupleOrder()
        {
            var nested = new List<object>
            {
                new ResultBox
                {
                    Result = new object[]
                    {
                        new BigInteger(7),
                        new BigInteger(42),
                        new BigInteger(3),
                        BigInteger.Parse("1000000000000000"),
                        new BigInteger(100),
                        new BigInteger(200),
                        "0x1111111111111111111111111111111111111111",
                        "0x2222222222222222222222222222222222222222",
                        "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                        new BigInteger(1),
                        new BigInteger(1),
                        false
                    }
                }
            };

            var listing = MarketplaceListingDecoder.Decode(nested);

            Assert.AreEqual(new BigInteger(7), listing.listingId);
            Assert.AreEqual(new BigInteger(42), listing.tokenId);
            Assert.AreEqual(new BigInteger(3), listing.quantity);
            Assert.AreEqual("0x1111111111111111111111111111111111111111", listing.seller);
            Assert.IsTrue(listing.IsCreated);
            Assert.IsFalse(listing.reserved);
        }

        [Test]
        public void TokenAmountFormatter_FormatsWeiDeterministically()
        {
            Assert.AreEqual("1 ETH", TokenAmountFormatter.FormatNative(BigInteger.Parse("1000000000000000000")));
            Assert.AreEqual("0.001 ETH", TokenAmountFormatter.FormatNative(BigInteger.Parse("1000000000000000")));
            Assert.AreEqual("0 ETH", TokenAmountFormatter.FormatNative(BigInteger.Zero));
        }
    }
}
