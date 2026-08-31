using System;

namespace CryptoQuest.AI
{
    [Serializable]
    public sealed class NpcDialogueRequest
    {
        public string npcId;
        public string playerId;
        public string message;
        public string location;
        public int playerLevel;
    }

    [Serializable]
    public sealed class NpcDialogueResponse
    {
        public string dialogue;
        public string questId;
        public string questTitle;
        public bool questOffered;
    }
}
