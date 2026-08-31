using System;
using System.Reflection;
using Thirdweb.Unity;
using UnityEngine;

namespace CryptoQuest.Web3
{
    public static class ThirdwebClientIdInjector
    {
        public static bool TryApply(string clientId)
        {
            if (string.IsNullOrWhiteSpace(clientId)) return false;
            var manager = ThirdwebManager.Instance;
            if (manager == null) return false;

            foreach (var name in new[] { "ClientId", "clientId", "clientID", "ClientID" })
            {
                var type = manager.GetType();
                while (type != null)
                {
                    var property = type.GetProperty(
                        name,
                        BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
                    if (property != null && property.CanWrite && property.PropertyType == typeof(string))
                    {
                        property.SetValue(manager, clientId.Trim());
                        Debug.Log("[CryptoQuest/Web3] Thirdweb Client ID injected into manager property.");
                        return true;
                    }

                    var field = type.GetField(
                        name,
                        BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
                    if (field != null && field.FieldType == typeof(string))
                    {
                        field.SetValue(manager, clientId.Trim());
                        Debug.Log("[CryptoQuest/Web3] Thirdweb Client ID injected into manager field.");
                        return true;
                    }

                    type = type.BaseType;
                }
            }

            Debug.LogWarning("[CryptoQuest/Web3] Could not locate a writable ThirdwebManager Client ID member; configure the public Client ID on the ThirdwebManager prefab.");
            return false;
        }
    }
}
