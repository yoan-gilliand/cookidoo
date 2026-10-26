# 🍳 Cookidoo Recipe Creator

Une interface de chat moderne propulsée par l'IA (Gemini) pour créer, adapter et uploader des recettes directement sur votre compte Thermomix Cookidoo.

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.50%2B-red)

> **Disclaimer:** Ce projet est non-officiel. Les développeurs ne sont pas affiliés, approuvés ou liés à Cookidoo, Vorwerk, Thermomix ou l'une de leurs filiales.

## ✨ Fonctionnalités

- **URL, texte ou photo** : collez le lien d'un site (Marmiton, CuisineAZ…), décrivez une envie ou joignez une photo de recette papier.
- **Adaptation TM6** : l'IA (Gemini) convertit chaque étape en réglages Thermomix (temps, température, vitesse, sens inverse), dans les limites de la machine.
- **Ajustements en discutant** : « pour 6 personnes », « sans lactose »… la recette est mise à jour.
- **Publication en un clic** dans « Mes créations » sur Cookidoo, avec des étapes en **cuisson guidée** (réglages cliquables sur le TM6).
- **Accès protégé** par mot de passe, mémorisé 30 jours.

---

## 🛠️ Installation

1. **Cloner le projet**
   ```bash
   git clone https://github.com/votre-username/mcp-cookidoo.git
   cd mcp-cookidoo
   ```

2. **Créer un environnement virtuel**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   # ou
   .\.venv\Scripts\activate   # Windows
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les secrets**
   Créez un fichier `.streamlit/secrets.toml` à la racine :
   ```toml
   # Identifiants Cookidoo (pour l'upload)
   cookidoo_email = "votre@email.com"
   cookidoo_password = "votre_mot_de_passe"

   # Clé API Google Gemini
   gemini_api_key = "votre_cle_api_gemini"

   # Mot de passe pour accéder à votre app Streamlit
   app_password = "choisissez_un_mot_de_passe_local"
   ```

---

## 🚀 Utilisation

Lancez simplement l'application Streamlit :

```bash
streamlit run streamlit_app.py
```

L'application sera accessible sur `http://localhost:8501` (ou votre IP réseau locale pour l'accès mobile).

---

## 👏 Crédits & Remerciements

Ce projet repose sur le travail exceptionnel de la communauté open-source.

- **Auteur API Original** : Un immense merci à **[Alexandre Patelli](https://github.com/alexandrepa)** pour sa librairie **[mcp-cookidoo](https://github.com/alexandrepa/mcp-cookidoo)**. C'est grâce à son travail de reverse-engineering de l'API Cookidoo que ce projet est possible.
- **Librairie [cookidoo-api](https://github.com/miaucl/cookidoo-api)** pour l'accès à Cookidoo.
- **UI/UX & Intégration IA** : Développé pour offrir une expérience utilisateur fluide et moderne.

---

## 📄 Licence

Distribué sous licence MIT. Voir le fichier `LICENSE` pour plus d'informations.
