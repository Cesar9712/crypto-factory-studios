using CryptoQuest.UI;
using CryptoQuest.Web3;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace CryptoQuest.Editor
{
    public static class InventoryMarketUiBootstrap
    {
        private const string PrefabFolder = "Assets/CryptoQuest/Prefabs";
        private const string SceneFolder = "Assets/CryptoQuest/Scenes";
        private const string PrefabPath = PrefabFolder + "/InventoryMarketItem.prefab";
        private const string ScenePath = SceneFolder + "/InventoryMarket.unity";

        [MenuItem("CryptoQuest/UI/Build Inventory Marketplace")]
        public static void Build()
        {
            EnsureFolder("Assets/CryptoQuest", "Prefabs");
            EnsureFolder("Assets/CryptoQuest", "Scenes");
            var itemPrefab = BuildItemPrefab();
            BuildScene(itemPrefab);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[CryptoQuest] Inventory marketplace UI generated: {PrefabPath}, {ScenePath}");
        }

        private static InventoryMarketItemView BuildItemPrefab()
        {
            var root = new GameObject("InventoryMarketItem", typeof(RectTransform), typeof(Image), typeof(LayoutElement), typeof(InventoryMarketItemView));
            var rect = root.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(900f, 180f);
            root.GetComponent<LayoutElement>().preferredHeight = 180f;

            var icon = CreateRawImage(root.transform, "Icon", new Vector2(90, 90));
            var name = CreateText(root.transform, "Name", "Item", 28);
            var balance = CreateText(root.transform, "Balance", "x0", 22);
            var price = CreateText(root.transform, "Price", "Not listed", 22);
            var status = CreateText(root.transform, "Status", "Inventory", 20);
            var buy = CreateButton(root.transform, "BuyButton", "Comprar");
            var sell = CreateButton(root.transform, "SellButton", "Vender");
            var cancel = CreateButton(root.transform, "CancelButton", "Cancelar");

            var layout = root.AddComponent<HorizontalLayoutGroup>();
            layout.spacing = 12f;
            layout.padding = new RectOffset(16, 16, 16, 16);
            layout.childAlignment = TextAnchor.MiddleLeft;
            layout.childForceExpandHeight = false;
            layout.childForceExpandWidth = false;

            var view = root.GetComponent<InventoryMarketItemView>();
            var serialized = new SerializedObject(view);
            serialized.FindProperty("icon").objectReferenceValue = icon;
            serialized.FindProperty("nameText").objectReferenceValue = name;
            serialized.FindProperty("balanceText").objectReferenceValue = balance;
            serialized.FindProperty("priceText").objectReferenceValue = price;
            serialized.FindProperty("statusText").objectReferenceValue = status;
            serialized.FindProperty("buyButton").objectReferenceValue = buy;
            serialized.FindProperty("sellButton").objectReferenceValue = sell;
            serialized.FindProperty("cancelButton").objectReferenceValue = cancel;
            serialized.ApplyModifiedPropertiesWithoutUndo();

            var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath).GetComponent<InventoryMarketItemView>();
            Object.DestroyImmediate(root);
            return prefab;
        }

        private static void BuildScene(InventoryMarketItemView itemPrefab)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
            eventSystem.transform.SetParent(null);

            var canvasObject = new GameObject("InventoryMarketCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasObject.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1080, 2400);
            scaler.matchWidthOrHeight = 0.5f;

            var scroll = new GameObject("ScrollView", typeof(RectTransform), typeof(ScrollRect), typeof(Image));
            scroll.transform.SetParent(canvasObject.transform, false);
            Stretch(scroll.GetComponent<RectTransform>());

            var viewport = new GameObject("Viewport", typeof(RectTransform), typeof(RectMask2D), typeof(Image));
            viewport.transform.SetParent(scroll.transform, false);
            Stretch(viewport.GetComponent<RectTransform>());

            var content = new GameObject("Content", typeof(RectTransform), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
            content.transform.SetParent(viewport.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0, 1);
            contentRect.anchorMax = new Vector2(1, 1);
            contentRect.pivot = new Vector2(0.5f, 1);
            contentRect.sizeDelta = Vector2.zero;
            var vertical = content.GetComponent<VerticalLayoutGroup>();
            vertical.spacing = 14f;
            vertical.padding = new RectOffset(20, 20, 20, 20);
            vertical.childForceExpandHeight = false;
            vertical.childForceExpandWidth = true;
            content.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;

            var scrollRect = scroll.GetComponent<ScrollRect>();
            scrollRect.viewport = viewport.GetComponent<RectTransform>();
            scrollRect.content = contentRect;
            scrollRect.horizontal = false;

            var systems = new GameObject("CryptoQuestInventorySystems");
            var web3 = systems.AddComponent<CryptoQuestWeb3Controller>();
            var metadata = systems.AddComponent<TokenMetadataLoader>();
            var actions = systems.AddComponent<MarketplaceActionController>();
            var panel = systems.AddComponent<InventoryMarketPanelController>();

            var actionsSerialized = new SerializedObject(actions);
            actionsSerialized.FindProperty("web3").objectReferenceValue = web3;
            actionsSerialized.ApplyModifiedPropertiesWithoutUndo();

            var panelSerialized = new SerializedObject(panel);
            panelSerialized.FindProperty("web3").objectReferenceValue = web3;
            panelSerialized.FindProperty("metadataLoader").objectReferenceValue = metadata;
            panelSerialized.FindProperty("actions").objectReferenceValue = actions;
            panelSerialized.FindProperty("contentRoot").objectReferenceValue = content.transform;
            panelSerialized.FindProperty("itemPrefab").objectReferenceValue = itemPrefab;
            panelSerialized.ApplyModifiedPropertiesWithoutUndo();

            EditorSceneManager.SaveScene(scene, ScenePath);
        }

        private static RawImage CreateRawImage(Transform parent, string name, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(RawImage), typeof(LayoutElement));
            go.transform.SetParent(parent, false);
            go.GetComponent<LayoutElement>().preferredWidth = size.x;
            go.GetComponent<LayoutElement>().preferredHeight = size.y;
            return go.GetComponent<RawImage>();
        }

        private static Text CreateText(Transform parent, string name, string value, int fontSize)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Text), typeof(LayoutElement));
            go.transform.SetParent(parent, false);
            var text = go.GetComponent<Text>();
            text.text = value;
            text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = fontSize;
            text.alignment = TextAnchor.MiddleLeft;
            go.GetComponent<LayoutElement>().preferredWidth = 150f;
            return text;
        }

        private static Button CreateButton(Transform parent, string name, string label)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button), typeof(LayoutElement));
            go.transform.SetParent(parent, false);
            go.GetComponent<LayoutElement>().preferredWidth = 130f;
            go.GetComponent<LayoutElement>().preferredHeight = 64f;
            var text = CreateText(go.transform, "Label", label, 20);
            text.alignment = TextAnchor.MiddleCenter;
            Stretch(text.GetComponent<RectTransform>());
            return go.GetComponent<Button>();
        }

        private static void Stretch(RectTransform rect)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }

        private static void EnsureFolder(string parent, string child)
        {
            var path = parent + "/" + child;
            if (!AssetDatabase.IsValidFolder(path)) AssetDatabase.CreateFolder(parent, child);
        }
    }
}
