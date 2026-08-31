using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace CryptoQuest.Avatars
{
    public sealed class PrefabAvatarProvider : MonoBehaviour, IAvatarProvider
    {
        [Serializable]
        private struct AvatarEntry
        {
            public string id;
            public GameObject prefab;
        }

        [SerializeField] private AvatarEntry[] avatars = Array.Empty<AvatarEntry>();
        private Dictionary<string, GameObject> lookup;

        public string ProviderId => "local-prefab";

        private void Awake()
        {
            lookup = new Dictionary<string, GameObject>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in avatars)
                if (!string.IsNullOrWhiteSpace(entry.id) && entry.prefab != null)
                    lookup[entry.id] = entry.prefab;
        }

        public Task<GameObject> LoadAvatarAsync(string avatarIdOrUrl, Transform parent, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (lookup == null) Awake();
            if (!lookup.TryGetValue(avatarIdOrUrl, out var prefab))
                throw new KeyNotFoundException($"Avatar '{avatarIdOrUrl}' is not registered.");

            return Task.FromResult(Instantiate(prefab, parent, false));
        }

        public void Release(GameObject avatarInstance)
        {
            if (avatarInstance != null) Destroy(avatarInstance);
        }
    }
}
