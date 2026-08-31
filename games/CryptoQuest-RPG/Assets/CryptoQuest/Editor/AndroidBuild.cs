#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace CryptoQuest.Editor
{
    public static class AndroidBuild
    {
        private const string OutputDirectory = "Builds/Android";
        private const string OutputApk = OutputDirectory + "/CryptoQuest-RPG.apk";

        [MenuItem("CryptoQuest/Build/Android APK")]
        public static void BuildAndroidApk()
        {
            Directory.CreateDirectory(OutputDirectory);
            PlayerSettings.applicationIdentifier = "com.cryptofactorystudios.cryptoquest";
            PlayerSettings.productName = "CryptoQuest RPG";
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            EditorUserBuildSettings.buildAppBundle = false;

            var scenes = Array.FindAll(EditorBuildSettings.scenes, scene => scene.enabled);
            if (scenes.Length == 0)
                throw new InvalidOperationException("No enabled scenes found in Build Settings.");

            var scenePaths = Array.ConvertAll(scenes, scene => scene.path);
            var options = new BuildPlayerOptions
            {
                scenes = scenePaths,
                locationPathName = OutputApk,
                target = BuildTarget.Android,
                options = BuildOptions.None
            };

            var report = BuildPipeline.BuildPlayer(options);
            if (report.summary.result != BuildResult.Succeeded)
                throw new InvalidOperationException($"Android build failed: {report.summary.result}, errors={report.summary.totalErrors}");

            Debug.Log($"CryptoQuest Android APK built: {OutputApk} ({report.summary.totalSize} bytes)");
        }
    }
}
#endif
