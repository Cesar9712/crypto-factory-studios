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

        [Serializable]
        private sealed class Request
        {
            public string npc_id;
            public string npc_name;
            public string npc_role;
            public string player_id;
            public string player_name;
            public string message;
            public string world_state;
        }

        [Serializable]
        public sealed class Reply
        {
            public string npc_id;
            public string npc_name;
            public string dialogue;
            public string model;
        }

        public IEnumerator Talk(
            string npcId,
            string npcName,
            string npcRole,
            string playerId,
            string playerName,
            string message,
            string worldState,
            Action<Reply> ok,
            Action<string> fail)
        {
            if (string.IsNullOrWhiteSpace(npcId) || string.IsNullOrWhiteSpace(npcName) || string.IsNullOrWhiteSpace(message))
            {
                fail?.Invoke("npcId, npcName and message are required.");
                yield break;
            }

            var payload = new Request
            {
                npc_id = npcId.Trim(),
                npc_name = npcName.Trim(),
                npc_role = string.IsNullOrWhiteSpace(npcRole) ? "adventurer" : npcRole.Trim(),
                player_id = string.IsNullOrWhiteSpace(playerId) ? "guest" : playerId.Trim(),
                player_name = string.IsNullOrWhiteSpace(playerName) ? "Traveler" : playerName.Trim(),
                message = message.Trim(),
                world_state = worldState?.Trim() ?? string.Empty
            };

            var body = JsonUtility.ToJson(payload);
            using var request = new UnityWebRequest(backendBaseUrl.TrimEnd('/') + "/api/v1/cryptoquest/npc/dialogue", "POST");
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            request.timeout = 35;

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                fail?.Invoke($"NPC backend error {request.responseCode}: {request.error}");
                yield break;
            }

            var reply = JsonUtility.FromJson<Reply>(request.downloadHandler.text);
            if (reply == null || string.IsNullOrWhiteSpace(reply.dialogue))
            {
                fail?.Invoke("NPC backend returned an invalid response.");
                yield break;
            }

            ok?.Invoke(reply);
        }

        public IEnumerator Talk(string npcId, string message, string context, Action<Reply> ok, Action<string> fail)
        {
            return Talk(npcId, npcId, "adventurer", "guest", "Traveler", message, context, ok, fail);
        }
    }
}
