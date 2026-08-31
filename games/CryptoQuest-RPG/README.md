# CryptoQuest RPG

Isolated Unity game module for Crypto Factory Studios.

Target: Unity 2022.3 LTS+ / Android / Web3.

Integrations:
- thirdweb Unity SDK v6 (package imported by Unity editor/build environment)
- OpenAI NPC gateway through the existing server backend; no API secret is stored in Unity
- Avatar abstraction layer. Ready Player Me hosted services are retired and are not called at runtime.

Never commit thirdweb secret keys, OpenAI API keys, wallet private keys, or seed phrases.
