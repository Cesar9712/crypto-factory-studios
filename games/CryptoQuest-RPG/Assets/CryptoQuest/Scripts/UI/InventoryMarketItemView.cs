using System;
using CryptoQuest.Web3;
using UnityEngine;
using UnityEngine.UI;

namespace CryptoQuest.UI
{
    public sealed class InventoryMarketItemView : MonoBehaviour
    {
        [SerializeField] private RawImage icon;
        [SerializeField] private Text nameText;
        [SerializeField] private Text balanceText;
        [SerializeField] private Text priceText;
        [SerializeField] private Text statusText;
        [SerializeField] private Button buyButton;
        [SerializeField] private Button sellButton;
        [SerializeField] private Button cancelButton;

        private InventoryMarketItem item;
        private Action<InventoryMarketItem> onBuy;
        private Action<InventoryMarketItem> onSell;
        private Action<InventoryMarketItem> onCancel;

        public InventoryMarketItem Item => item;

        public void Bind(
            InventoryMarketItem value,
            Texture2D texture,
            Action<InventoryMarketItem> buy,
            Action<InventoryMarketItem> sell,
            Action<InventoryMarketItem> cancel)
        {
            item = value ?? throw new ArgumentNullException(nameof(value));
            onBuy = buy;
            onSell = sell;
            onCancel = cancel;

            if (icon != null) icon.texture = texture;
            if (nameText != null) nameText.text = item.inventory?.name ?? "Unknown item";
            if (balanceText != null) balanceText.text = $"x{item.inventory?.balance ?? "0"}";

            var listing = item.listing;
            if (priceText != null)
                priceText.text = item.isListed && listing != null
                    ? TokenAmountFormatter.FormatNative(listing.pricePerToken)
                    : "Not listed";

            if (statusText != null)
                statusText.text = item.isSeller ? "Your listing" : item.isListed ? "Marketplace" : "Inventory";

            if (buyButton != null)
            {
                buyButton.gameObject.SetActive(item.canBuy);
                buyButton.onClick.RemoveAllListeners();
                buyButton.onClick.AddListener(() => onBuy?.Invoke(item));
            }

            if (sellButton != null)
            {
                var canSell = !item.isListed && item.inventory != null && item.inventory.Balance > 0;
                sellButton.gameObject.SetActive(canSell);
                sellButton.onClick.RemoveAllListeners();
                sellButton.onClick.AddListener(() => onSell?.Invoke(item));
            }

            if (cancelButton != null)
            {
                cancelButton.gameObject.SetActive(item.canCancel);
                cancelButton.onClick.RemoveAllListeners();
                cancelButton.onClick.AddListener(() => onCancel?.Invoke(item));
            }
        }
    }
}
