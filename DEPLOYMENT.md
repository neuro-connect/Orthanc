# Orthanc PACS — Guide de déploiement

Infrastructure Docker Compose pour un serveur PACS Orthanc avec authentification Keycloak (SSO), visualisation OHIF/Stone Web Viewer, envoi d'email via Brevo, et pipelines d'analyse (SurgeryFlow, Epinsight).

## Sommaire

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Démarrage rapide](#démarrage-rapide)
- [Configuration](#configuration)
- [Customisation](#customisation)
- [Post-déploiement (Keycloak)](#post-déploiement-keycloak)
- [Sécurité](#sécurité)

## Architecture

| Service | Image / build | Rôle | Exposé |
|---|---|---|---|
| `nginx` | `orthancteam/orthanc-nginx` | Reverse proxy, point d'entrée unique | `:80` (ou `:443` en HTTPS) |
| `orthanc` | `./orthanc` (build local) | Serveur DICOM + OrthancExplorer2 + plugins Python custom | `:4242` (DICOM) |
| `orthanc-db` | `postgres:14` | Base de données d'Orthanc | `:5432` |
| `orthanc-auth-service` | `orthancteam/orthanc-auth-service` | Pont entre Keycloak et les permissions Orthanc (`permissions.jsonc`) | interne |
| `keycloak` | `orthancteam/orthanc-keycloak` | SSO / gestion des utilisateurs et rôles | interne (routé par nginx) |
| `keycloak-db` | `postgres:14` | Base de données de Keycloak | interne |
| `smtp-to-brevo` | `./relay` (build local) | Relais SMTP → API Brevo, utilisé par Keycloak pour les emails (reset mdp, etc.) | `:2525` |

Tout le trafic web passe par `nginx`, qui route vers `orthanc`, `keycloak` et `orthanc-auth-service` selon le chemin (`/orthanc/`, `/keycloak/`, etc.).

Les plugins `surgeryflow-plugin` et `epinsight-plugin` tournent **dans** le conteneur `orthanc` mais lancent chacun un second conteneur Docker (`docker run --gpus=all ...`) via le socket Docker de l'hôte monté en volume (`/var/run/docker.sock`). C'est pourquoi ce socket est monté dans le service `orthanc`.

## Prérequis

- Docker Engine + plugin Docker Compose (`docker compose`, v2).
- **GPU NVIDIA + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)** installés sur l'hôte si les boutons SurgeryFlow / Epinsight sont utilisés — ces pipelines lancent des conteneurs `--gpus=all`.
- Accès Docker Hub (ou registre équivalent) pour tirer les images `onsetlab/surgeryflow:*` et `onsetlab/epinsight:*` utilisées par les plugins.
- Un compte [Brevo](https://www.brevo.com) avec une adresse d'expéditeur vérifiée et une clé API — utilisé pour tous les emails sortants (reset mot de passe Keycloak, notifications de fin de job IA).
- Un hostname/domaine accessible par les utilisateurs finaux (ex. `chum67945`, ou `localhost` pour un test local). Cette valeur doit être cohérente partout où elle apparaît (voir [Configuration](#configuration)).

## Démarrage rapide

```bash
git clone <repo> && cd Orthanc

# 1. Copier les templates (les fichiers réels ne sont jamais committés, voir .gitignore)
cp docker-compose_template.yml docker-compose.yml
cp template_orthanc.json orthanc.json

# 2. Remplacer toutes les valeurs "change-me" / placeholders
#    dans docker-compose.yml ET orthanc.json (voir section Configuration)
grep -rn "change-me" docker-compose.yml orthanc.json

# 3. Lancer
docker compose up -d --build
```

Le premier démarrage prend 1-2 minutes (init des bases Postgres + Keycloak). Une fois prêt :
- Orthanc : `http://<hostname>/orthanc/ui/app/`
- Keycloak : `http://<hostname>/keycloak`

Passer ensuite par la section [Post-déploiement](#post-déploiement-keycloak) pour créer les comptes admin et les rôles.

## Configuration

`docker-compose.yml` et `orthanc.json` sont **volontairement absents du dépôt** (listés dans `.gitignore`) car ils contiennent des secrets et des valeurs propres à chaque site. Toujours partir des templates `docker-compose_template.yml` et `template_orthanc.json`, qui doivent rester génériques (aucun secret réel, aucune IP interne réelle).

> Si vous améliorez l'infra (nouvelle variable, nouveau volume, nouveau plugin), reportez le changement dans le template correspondant pour que les autres déploiements restent synchronisables.

### `docker-compose.yml` — valeurs à personnaliser par site

| Variable | Service | Description |
|---|---|---|
| `BREVO_API_KEY`, `BREVO_EMAIL`, `BREVO_NAME` | `orthanc` | Clé API Brevo et identité d'expéditeur, utilisées par les plugins IA pour notifier la fin d'un job |
| `SECRET_KEY` | `orthanc-auth-service` | Clé de signature des tokens — aléatoire, propre à chaque déploiement |
| `KEYCLOAK_CLIENT_SECRET` | `orthanc-auth-service` | Doit correspondre au secret du client `orthanc` créé dans Keycloak |
| `PUBLIC_ORTHANC_ROOT`, `PUBLIC_LANDING_ROOT`, `PUBLIC_OHIF_ROOT` | `orthanc-auth-service` | URLs publiques — remplacer `localhost` par le hostname réel du site |
| `KC_BOOTSTRAP_ADMIN_PASSWORD` | `keycloak` | Mot de passe du 1er admin Keycloak (à changer immédiatement après le 1er login, voir plus bas) |
| `KC_DB_PASSWORD` / `POSTGRES_PASSWORD` (keycloak-db) | `keycloak`, `keycloak-db` | Doivent être identiques entre les deux services |
| `KC_HOSTNAME` | `keycloak` | Hostname public — doit correspondre à `PUBLIC_*_ROOT` ci-dessus |
| `BREVO_API_KEY`, `SENDER_EMAIL`, `SENDER_NAME` | `smtp-to-brevo` | Mêmes infos Brevo que côté `orthanc`, réutilisées pour les emails Keycloak |
| `USERS` | `orthanc-auth-service` | Mot de passe du `share-user` technique utilisé pour signer les liens de partage |

Toutes les URLs `http://localhost/...` du template doivent être remplacées de façon cohérente par le hostname réel du déploiement.

### `orthanc.json` — clés principales

| Clé | Description |
|---|---|
| `DicomAet`, `DicomPort` | AE Title et port DICOM du serveur Orthanc lui-même |
| `DicomModalities` | PACS/modalités distants autorisés à communiquer avec Orthanc. Deux formats supportés : `{"AET": "...", "Host": "...", "Port": ...}` (objet) ou `["AET", "Host", Port]` (tableau) |
| `OrthancExplorer2.CustomLogoUrl`, `CustomTitle`, `Theme` | Branding de l'interface (voir [Customisation](#customisation)) |
| `OrthancExplorer2.UiOptions.OhifViewer3PublicRoot` | Doit correspondre à `PUBLIC_OHIF_ROOT` dans `docker-compose.yml` |
| `OrthancExplorer2.UiOptions.CustomButtons.study` | Boutons custom (déclenchent les pipelines IA) |
| `OrthancExplorer2.Keycloak.Url` | URL publique de Keycloak, doit correspondre à `KC_HOSTNAME` |
| `Authorization.WebServicePassword` | Doit être identique au mot de passe `share-user` défini dans `USERS` (docker-compose) |
| `Authorization.ExtraPermissions` | Autorise chaque endpoint custom (`surgeryflow-apply`, `epinsight-apply`, ...) — à compléter à chaque nouveau plugin |

### `permissions.jsonc` — rôles et permissions

Définit les rôles Orthanc (`admin-role`, `doctor-role`, `external-role`, ...) et les permissions/labels associés. C'est ce fichier qui est ensuite référencé lors de l'assignation des rôles dans Keycloak (voir [Post-déploiement](#post-déploiement-keycloak)). Ajoutez un rôle ici avant de pouvoir l'assigner côté Keycloak.

## Customisation

### Branding (logo, couleurs, thème)

- `assets/custom.css` : CSS injecté dans OrthancExplorer2 (monté en lecture seule dans le conteneur `orthanc`).
- `orthanc.json` → `OrthancExplorer2.CustomLogoUrl`, `CustomTitle`, `Theme` (`"dark"` / `"light"`).
- Thème de connexion Keycloak : logo, fond d'écran et CSS de la page de login sont montés via des volumes **commentés par défaut** dans `docker-compose_template.yml` (service `keycloak`) :
  ```yaml
  - ./assets/onset_logo_no_bg.png:/opt/keycloak/themes/orthanc/login/resources/img/orthanc-logo-text.png:ro
  - ./assets/onset_logo_no_bg.png:/opt/keycloak/themes/orthanc/login/resources/img/orthanc-logo-text-shadow.png:ro
  - ./assets/background_50.png:/opt/keycloak/themes/orthanc/login/resources/img/keycloak-bg.png:ro
  - ./assets/login.css:/opt/keycloak/themes/orthanc/login/resources/css/login.css:ro
  ```
  Décommentez-les et remplacez les fichiers dans `assets/` par vos propres visuels pour rebrander la page de connexion.

### Template d'email Keycloak

Le dossier `email_theme/` contient un thème d'email personnalisé (`email_theme/email/html/*.ftl`). Il est monté dans Keycloak et doit être sélectionné manuellement dans l'interface (Realm settings → Email → Theme).

### Boutons custom / pipelines

Chaque bouton dans `orthanc.json` → `CustomButtons.study` appelle un endpoint exposé par un plugin Python (`plugins/<nom>-plugin/`). Pour ajouter un nouveau pipeline :

1. Créer `plugins/mon-plugin/` avec un `plugin_info.json` (nom, description, endpoint) et le script Python qui enregistre l'endpoint Orthanc.
2. L'importer dans `plugins/load_plugins.py`.
3. Ajouter le bouton correspondant dans `orthanc.json` (`CustomButtons.study`) — donner un `Id` **unique** au bouton.
4. Autoriser l'endpoint dans `Authorization.ExtraPermissions`.
5. Reporter les étapes 3-4 dans `template_orthanc.json` pour que le template reste à jour.

Les plugins existants (`surgeryflow-plugin`, `epinsight-plugin`) lancent un conteneur Docker GPU (`docker run --gpus=all onsetlab/...`) depuis le conteneur `orthanc` et envoient une notification par email (via `smtp-to-brevo`/Brevo) à la fin du job — voir `notifications.py` dans chaque dossier de plugin.

### Modalités DICOM distantes

Ajouter une entrée dans `orthanc.json` → `DicomModalities` pour chaque PACS/modalité distant autorisé à interroger ou envoyer des études à Orthanc.

## Post-déploiement (Keycloak)

1. Se connecter à `http://<hostname>/keycloak` avec `admin` / mot de passe défini dans `KC_BOOTSTRAP_ADMIN_PASSWORD`.
2. Dans le realm `master`, créer un nouvel utilisateur admin, puis **supprimer le compte `admin`** par défaut.
3. Pour ajouter un utilisateur Orthanc : sélectionner le realm `orthanc` (menu `Manage realms`) → `Users` → `Add user`.
4. Une fois l'utilisateur créé, aller dans `Role Mapping` → `Assign role`, filtrer par `Filter by realm roles`, et choisir le rôle voulu. Les permissions de chaque rôle sont définies dans `permissions.jsonc`.
5. Dans `Realm settings` → `Email`, sélectionner le thème `email_theme` pour utiliser le template d'email custom.

## Sécurité

- `docker-compose.yml`, `orthanc.json` et tout fichier contenant des secrets réels **ne doivent jamais être committés** — ils sont dans `.gitignore`. Seuls les templates (`docker-compose_template.yml`, `template_orthanc.json`) sont versionnés, et doivent rester exempts de secrets réels ou d'IPs internes sensibles.
- Avant toute mise en production, remplacer **toutes** les valeurs `change-me` (`grep -rn "change-me" docker-compose.yml orthanc.json`) par des secrets générés aléatoirement, distincts par déploiement.
- Le compte `admin` par défaut de Keycloak doit être supprimé après création d'un compte nominatif (voir ci-dessus).
- Pour une exposition publique, activer HTTPS : décommenter les 4 lignes prévues dans le service `nginx` du `docker-compose.yml` (`ENABLE_HTTPS: "true"`, `ports: ["443:443"]`, montage des certificats) et commenter `ports: ["80:80"]`.
- Le socket Docker (`/var/run/docker.sock`) est monté dans le conteneur `orthanc`, ce qui lui donne un accès équivalent à root sur l'hôte — nécessaire pour les pipelines, mais à garder en tête dans l'analyse de risque du déploiement.
