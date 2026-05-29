# 🐾 Dynamic SubAgent — Français

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

Un plugin AstrBot permettant à l'agent principal de créer et gérer dynamiquement des sous-agents, avec **isolation des permissions** et **limites de profondeur d'imbrication** pour un système multi-agents sécurisé.

## ✨ Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| 🧠 Création dynamique | `spawn_agent` crée des sous-agents à la demande avec permissions/modèles/persistence configurables |
| 🔄 Transfert de tâches | `transfer_to_agent` délègue des tâches aux sous-agents existants |
| 🔒 Isolation des permissions | Trois niveaux : `safe` / `medium` / `full` — les sous-agents ne peuvent pas escalader |
| 🛡 Limite de profondeur | Les sous-agents ne peuvent pas créer d'autres sous-agents, empêchant les chaînes infinies |
| 💾 Mémoire persistante | Les agents persistants conservent le contexte après redémarrage + injection d'historique |
| 🕥 Traçage de collaboration | Suivi complet des chaînes spawn/transfer et rapports |

## ⚙️ Système de permissions

| Niveau | Outils intégrés | Outils plugin | Peut spawn | Description |
|:------:|:---------------:|:-------------:|:----------:|-------------|
| `safe` | ❌ | Liste blanche | ❌ | Recherche + gestion uniquement |
| `medium` | Fichier R/W | Liste noire | ❌ | Sans shell/python |
| `full` | ✅ Tous | ✅ Tous | ❌ | Identique à l'agent principal |

> Les sous-agents ne peuvent jamais utiliser les exécuteurs Python/IPython ni créer de sous-agents.

## 📦 Installation

Recherchez `dynamic_subagent` dans le Marketplace de plugins AstrBot, ou clonez manuellement :

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Démarrage rapide

```python
# 1. Créer un sous-agent avec tâche immédiate
spawn_agent(
    name="code_reviewer",
    description="Assistant de revue de code",
    permission_level="medium",
    task="Veuillez examiner le code suivant : ..."
)

# 2. Créer un sous-agent persistant pour transfert ultérieur
spawn_agent(
    name="memory_bot",
    description="Assistant avec mémoire qui se souvient des conversations",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Continuons notre sujet précédent..."
)

# 3. Voir le rapport de collaboration
show_collaboration_report()
```

## 📝 Licence

MIT

---
*Cette introduction est rédigée en français.*
