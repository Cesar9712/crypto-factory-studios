using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace CryptoQuest.Avatars
{
    public sealed class AvatarService : MonoBehaviour
    {
        [SerializeField] private MonoBehaviour providerComponent;
        private IAvatarProvider provider;
        private GameObject currentAvatar;

        private void Awake()
        {
            provider = providerComponent as IAvatarProvider;
            if (provider == null)
                Debug.LogError("Avatar provider must implement IAvatarProvider.");
        }

        public async Task<GameObject> SetAvatarAsync(string avatarIdOrUrl, Transform parent, CancellationToken cancellationToken = default)
        {
            if (provider == null) throw new System.InvalidOperationException("Avatar provider is not configured.");
            if (currentAvatar != null) provider.Release(currentAvatar);
            currentAvatar = await provider.LoadAvatarAsync(avatarIdOrUrl, parent, cancellationToken);
            return currentAvatar;
        }
    }
}
