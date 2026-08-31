using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace CryptoQuest.AI
{
    public sealed class NpcAiClient : MonoBehaviour
    {
        [SerializeField] private string backendBaseUrl = "https://crypto-factory-studios.onrender.com";

        [Serializable] private class Request { public string npcId; public string playerMessage; public string context; }
        [Serializable] public class Reply { public string text; public string questId; }

        public IEnumerator Talk(string npcId, string message, string context, Action<Reply> ok, Action<string> fail)
        {
            var body = JsonUtility.ToJson(new Request { npcId = npcId, playerMessage = message, context = context });
            using var req = new UnityWebRequest(backendBaseUrl.TrimEnd('/') + "/api/cryptoquest/npc/respond", "POST");
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            yield return req.SendWebRequest();
            if (req.result != UnityWebRequest.Result.Success) { fail?.Invoke(req.error); yield break; }
            ok?.Invoke(JsonUtility.FromJson<Reply>(req.downloadHandler.text));
        }
    }
}
