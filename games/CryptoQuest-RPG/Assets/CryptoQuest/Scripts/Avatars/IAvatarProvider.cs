using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace CryptoQuest.Avatars
{
    public interface IAvatarProvider
    {
        string ProviderId { get; }
        Task<GameObject> LoadAvatarAsync(string avatarIdOrUrl, Transform parent, CancellationToken cancellationToken = default);
        void Release(GameObject avatarInstance);
    }
}
