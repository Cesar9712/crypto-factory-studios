#if UNITY_EDITOR
using System;
using System.IO;
using System.Reflection;
using CryptoQuest.Web3;
using Thirdweb.Unity;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace CryptoQuest.Editor
{
    public static class AndroidBuild
    {
        private const string OutputDirectory = "Builds/Android";
        private const string OutputApk = OutputDirectory + "/CryptoQuest-RPG.apk";
        private const string ScenePath = "Assets/CryptoQuest/Scenes/InventoryMarket.unity";

        [MenuItem("CryptoQuest/Build/Android APK")]
        public static void BuildAndroidApk()
        {
            var clientId = RequireEnv(RuntimeConfigLoader.ClientIdEnv);
            var inventoryAddress = RequireAddressEnv(RuntimeConfigLoader.InventoryEnv);
            var marketplaceAddress = RequireAddressEnv(RuntimeConfigLoader.MarketplaceEnv);

            InventoryMarketUiBootstrap.Build();
            InjectProductionConfig(clientId, inventoryAddress, marketplaceAddress);

            Directory.CreateDirectory(OutputDirectory);
            PlayerSettings.applicationIdentifier = "com.cryptofactorystudios.cryptoquest";
            PlayerSettings.productName = "CryptoQuest RPG";
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            EditorUserBuildSettings.buildAppBundle = false;

            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = OutputApk,
                target = BuildTarget.Android,
                options = BuildOptions.None
            };

            var report = BuildPipeline.BuildPlayer(options);
            if (report.summary.result != BuildResult.Succeeded)
                throw new InvalidOperationException($"Android build failed: {report.summary.result}, errors={report.summary.totalErrors}");

            Debug.Log($"CryptoQuest Android APK built: {OutputApk} ({report.summary.totalSize} bytes)");
        }

        private static void InjectProductionConfig(string clientId, string inventoryAddress, string marketplaceAddress)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var manager = UnityEngine.Object.FindObjectOfType<ThirdwebManager>();
            var web3 = UnityEngine.Object.FindObjectOfType<CryptoQuestWeb3Controller>();
            var loader = UnityEngine.Object.FindObjectOfType<RuntimeConfigLoader>();
            if (manager == null || web3 == null || loader == null)
                throw new InvalidOperationException("Generated inventory scene is missing Thirdweb/runtime components.");

            SetNonPublicProperty(manager, "ClientId", clientId);
            SetNonPublicProperty(manager, "InitializeOnAwake", false);

            var web3Serialized = new SerializedObject(web3);
            web3Serialized.FindProperty("inventoryContractAddress").stringValue = inventoryAddress;
            web3Serialized.FindProperty("marketplaceContractAddress").stringValue = marketplaceAddress;
            web3Serialized.ApplyModifiedPropertiesWithoutUndo();

            var loaderSerialized = new SerializedObject(loader);
            loaderSerialized.FindProperty("fallbackClientId").stringValue = clientId;
            loaderSerialized.FindProperty("fallbackInventoryContractAddress").stringValue = inventoryAddress;
            loaderSerialized.FindProperty("fallbackMarketplaceContractAddress").stringValue = marketplaceAddress;
            loaderSerialized.ApplyModifiedPropertiesWithoutUndo();

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
        }

        private static void SetNonPublicProperty(object target, string propertyName, object value)
        {
            var type = target.GetType();
            PropertyInfo property = null;
            while (type != null && property == null)
            {
                property = type.GetProperty(propertyName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
                type = type.BaseType;
            }
            if (property == null || !property.CanWrite)
                throw new InvalidOperationException($"Thirdweb property {propertyName} was not found or is read-only.");
            property.SetValue(target, value);
        }

        private static string RequireEnv(string name)
        {
            var value = Environment.GetEnvironmentVariable(name)?.Trim();
            if (string.IsNullOrWhiteSpace(value)) throw new InvalidOperationException($"Missing required environment variable {name}.");
            return value;
        }

        private static string RequireAddressEnv(string name)
        {
            var value = RequireEnv(name);
            if (value.Length != 42 || !value.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"{name} is not a valid EVM address.");
            return value;
        }
    }
}
#endif
