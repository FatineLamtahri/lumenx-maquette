# -*- coding: utf-8 -*-
"""
LumenX — Maquette d'onboarding (NON FONCTIONNELLE)
====================================================

But : valider le RENDU et le PARCOURS avec les associés et 10-15 testeurs,
avant de coder la vraie application. Aucune donnée réelle, aucun backend :
les boutons ne font que changer d'écran.

Architecture (volontairement simple, tout dans un seul fichier) :
  - Un "routeur" maison : st.session_state["screen"] contient le nom de
    l'écran courant ; le dictionnaire `ecrans` (en bas) associe chaque nom
    à une fonction ecran_*() ; la dernière ligne appelle l'écran courant.
  - La navigation se fait par callbacks on_click (go / set_profil / connexion)
    qui modifient session_state["screen"], puis Streamlit relance le script.
  - Le style est injecté en CSS via st.markdown(..., unsafe_allow_html=True).

Parcours :
  Accueil ─┬─ "Tester la démo" ───────────────► choix profil ──► tableau de bord
           └─ "Se connecter"  ──► connexion ─┬─ compte existant ► tableau de bord
                                             └─ nouveau client ► CGU ► onboarding
                                               (Entreprise → … → Comptes) ► tableau de bord

Polices : Fraunces (titres) + Inter (corps), identiques sur tous les écrans.
Lancer  : streamlit run app.py
"""

import datetime as dt
import urllib.parse
import urllib.request
import streamlit as st

# layout="wide" = pleine largeur ; le titre apparaît dans l'onglet du navigateur.
st.set_page_config(page_title="LumenX | Investir et gérer sa trésorerie d'entreprise",
                   layout="wide", initial_sidebar_state="expanded")

# ---------- STYLE GLOBAL (s'applique à tous les écrans) ----------
# Certains écrans (auth, onboarding) réinjectent ensuite leur propre CSS par-dessus.
st.markdown(
    """
    <style>
    /* Polices de marque chargées depuis Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,600;1,600&family=Inter:wght@400;600;700;800&display=swap');
    /* Inter = police par défaut du corps de texte sur tout l'app */
    html, body, [class*="css"], .stApp, p, div, span, label, button, input, select, textarea {
        font-family: 'Inter', sans-serif;
    }
    /* Fraunces (serif) réservée aux titres */
    h1, h2, h3 { font-family: 'Fraunces', serif; }
    /* Fond sombre + halo bleu en bas (identité visuelle de l'accueil) */
    .stApp {
        background: radial-gradient(1300px 520px at 50% 115%, rgba(45,107,255,.28), transparent), #0A0A0F;
    }
    /* En-tête natif laissé en place mais transparent : on conserve ainsi le
       chevron natif qui replie/rouvre la barre latérale (comportement Streamlit
       par défaut, fiable). On ne masque AUCUN contrôle de la barre. */
    [data-testid="stHeader"] { background: transparent !important; }
    /* Conteneur principal : sans marge, centré verticalement */
    .block-container { padding: 0 !important; max-width: 100% !important; min-height: 100vh; display: flex; flex-direction: column; justify-content: center; }
    /* Remonte légèrement le contenu (le centrage strict est cassé par Streamlit) */
    .block-container > div { flex: 0 0 auto !important; width: 100%; margin-bottom: 4cm; }
    /* Empêche une barre de défilement horizontale due aux bandeaux fixes */
    html, body { overflow-x: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- ÉTAT / NAVIGATION ----------
# st.session_state survit aux relances du script (à chaque clic Streamlit
# réexécute tout le fichier). On y stocke l'écran courant et les données saisies.
if "screen" not in st.session_state:
    st.session_state.screen = "accueil"          # écran affiché
if "profil" not in st.session_state:
    st.session_state.profil = None               # profil démo choisi (PME, SaaS, …)
if "societe_found" not in st.session_state:
    st.session_state.societe_found = False       # SIRET validé ?
    st.session_state.societe = None              # infos société (fictives)
    st.session_state.societe_error = ""          # message d'erreur SIRET

def go(screen):
    """Change d'écran (utilisé par la plupart des boutons via on_click)."""
    st.session_state.screen = screen

def set_profil(p, screen):
    """Mémorise le profil démo choisi puis va à l'écran demandé."""
    st.session_state.profil = p
    st.session_state.screen = screen

def connexion(existant):
    """Aiguillage après login (simulé via la case 'compte existant').
    Compte existant -> accès direct au tableau de bord (branche courte, sans onboarding).
    Sinon -> création d'espace (CGU puis parcours KYB)."""
    if existant:
        st.session_state.profil = "Mon entreprise"
        st.session_state.screen = "dashboard"
    else:
        st.session_state.screen = "cgu"

def rechercher_societe():
    """Valide le SIRET saisi et fabrique une société FICTIVE.
    (Dans la vraie app, un appel à l'API INSEE/Sirene remplirait ces champs.)
    Vérifie : non vide, uniquement des chiffres, exactement 14 chiffres."""
    siret = st.session_state.get("siret_input", "").replace(" ", "").strip()
    if not siret:
        st.session_state.societe_found = False
        st.session_state.societe_error = "Veuillez saisir un SIRET."
        return
    if not siret.isdigit():
        st.session_state.societe_found = False
        st.session_state.societe_error = "Format invalide : le SIRET ne doit contenir que des chiffres."
        return
    if len(siret) != 14:
        st.session_state.societe_found = False
        st.session_state.societe_error = (
            f"Format invalide : le SIRET doit comporter 14 chiffres "
            f"(vous en avez saisi {len(siret)})."
        )
        return
    st.session_state.societe = {
        "raison": "Société Démo SAS",
        "siren": siret[:9],
        "siret": siret,
        "forme": "SAS",
        "adresse": "xx rue de la Démo, 7500x Paris",
        "naf": "xxxxZ — Autres activités",
    }
    st.session_state.societe_found = True
    st.session_state.societe_error = ""

def reset_societe():
    """Annule la société trouvée (bouton « Ce n'est pas ça ») pour ressaisir un SIRET."""
    st.session_state.societe_found = False
    st.session_state.societe = None
    st.session_state.societe_error = ""

# ---------- Étapes du parcours de création d'espace ----------
# Utilisé par stepper_panel() (panneau vertical à gauche des écrans d'onboarding).
ETAPES = ["Entreprise", "Dirigeant", "Profil", "Bénéficiaires", "Validation", "Signature", "Comptes"]


# ==================================================================
# ACCUEIL
# ==================================================================
def ecran_accueil():
    """Landing page : bandeau de navigation fixe, accroche + 2 boutons d'entrée
    (se connecter / tester la démo), aperçu produit à droite, footer fixe."""
    # ===== BANDEAU HAUT : barre de navigation (logo LumenX + liens) =====
    st.markdown(
        """
        <div style="position:fixed;top:0;left:0;right:0;z-index:50;display:flex;align-items:center;gap:44px;background:#06060A;padding:16px 48px;border-bottom:1px solid #20202c;">
            <div style="font-family:'Fraunces',serif;font-size:26px;font-weight:700;color:#fff;letter-spacing:-.5px;">Lumen<span style="color:#2D6BFF;">X</span></div>
            <div style="display:flex;gap:46px;font-size:18px;color:#c2c6d2;">
                <span>Solutions</span>
                <span>Fonctionnalités</span>
                <span>Ressources</span>
                <span>À propos</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # ===== CONTENU CENTRAL : encart texte (gauche) + encart dashboard (droite) =====
    _, col_text, col_viz, _ = st.columns([0.6, 1, 1, 0.4], vertical_alignment="center")
    with col_text:
        # --- Encart texte : titre + accroche ---
        st.markdown(
            """
            <h1 style="font-family:'Fraunces',serif;font-size:52px;line-height:1.06;margin:0;font-weight:600;color:#fff;">Pilotez votre trésorerie<br><span style="color:#3B82F6;font-size:40px;font-style:italic;">En temps réel</span></h1>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:26px 0 4px;max-width:440px;">LumenX est la plateforme qui vous aide à optimiser l'argent de votre entreprise.</p>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:0 0 28px;max-width:440px;">Suivez vos flux de cash, gérez votre budget, optimisez votre trésorerie.</p>
            """,
            unsafe_allow_html=True,
        )
        # --- Encart de connexion : boutons + mention sécurité ---
        bcol, _ = st.columns(2)
        with bcol:
            st.button(
                "Se connecter / S'inscrire",
                type="primary", use_container_width=True,
                on_click=go, args=("auth",),
            )
            st.caption("🔒 Connexion sécurisée via Microsoft")
            st.write("")
            st.button(
                "Tester la démo",
                use_container_width=True,
                on_click=set_profil, args=("Démo", "dashboard"),
            )
    with col_viz:
        # --- Encart dashboard (aperçu produit) + encart "Placer mon excédent" ---
        st.markdown(
            """
            <div style="position:relative;max-width:660px;margin:0 auto 24px;">
              <div style="background:#0E0E16;border:1px solid #20202c;border-radius:20px;padding:36px 36px 30px;box-shadow:0 24px 60px rgba(0,0,0,.45);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:13px;color:#8a90a0;">Trésorerie consolidée</span>
                  <span style="font-size:12px;color:#28c76f;background:rgba(40,199,111,.12);padding:3px 9px;border-radius:20px;">▲ +4,2 %</span>
                </div>
                <div style="font-size:42px;font-weight:800;color:#fff;margin:8px 0 2px;">1 240 000 €</div>
                <svg viewBox="0 0 320 110" preserveAspectRatio="none" style="width:100%;height:160px;margin-top:12px;">
                  <defs><linearGradient id="grad" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2D6BFF" stop-opacity="0.35"/><stop offset="1" stop-color="#2D6BFF" stop-opacity="0"/></linearGradient></defs>
                  <polygon fill="url(#grad)" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50 270,34 300,40 320,28 320,110 0,110"/>
                  <polyline fill="none" stroke="#2D6BFF" stroke-width="2.5" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50 270,34 300,40 320,28"/>
                </svg>
                <div style="display:flex;gap:10px;margin-top:8px;">
                  <div style="flex:1;background:#15151f;border-radius:12px;padding:12px;"><div style="font-size:11px;color:#8a90a0;">Encaissements 30 j</div><div style="font-size:16px;font-weight:700;color:#fff;">320 k€</div></div>
                  <div style="flex:1;background:#15151f;border-radius:12px;padding:12px;"><div style="font-size:11px;color:#8a90a0;">Comptes</div><div style="font-size:16px;font-weight:700;color:#fff;">4</div></div>
                </div>
              </div>
              <div style="position:absolute;left:-22px;bottom:-20px;width:310px;background:#12121c;border:1px solid #2a2a3a;border-radius:18px;padding:20px;box-shadow:0 18px 44px rgba(0,0,0,.55);">
                <div style="display:flex;align-items:center;gap:8px;font-size:14px;color:#c2c6d2;"><span style="width:20px;height:20px;border-radius:50%;background:#2D6BFF;display:inline-block;"></span> Placer mon excédent</div>
                <div style="font-size:32px;font-weight:800;color:#fff;margin:10px 0 2px;">250 000 €</div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#8a90a0;margin-bottom:10px;">Disponible <span style="color:#c2c6d2;">500 000 €</span></div>
                <div style="display:flex;gap:6px;">
                  <span style="flex:1;text-align:center;font-size:11px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:6px 0;">25%</span>
                  <span style="flex:1;text-align:center;font-size:11px;color:#fff;background:#2D6BFF;border-radius:8px;padding:6px 0;">50%</span>
                  <span style="flex:1;text-align:center;font-size:11px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:6px 0;">75%</span>
                  <span style="flex:1;text-align:center;font-size:11px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:6px 0;">100%</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ===== BANDEAU BAS : footer (logo + liens légaux + copyright) =====
    st.markdown(
        """
        <div style="position:fixed;left:0;right:0;bottom:0;z-index:50;background:#16244D;border-top:1px solid #20202c;padding:14px 48px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;">
          <div>
            <span style="font-family:'Fraunces',serif;font-size:20px;font-weight:700;color:#fff;">Lumen<span style="color:#2D6BFF;">X</span></span>
            <span style="font-size:13px;color:#c2c6d2;margin-left:14px;">Pilotez votre trésorerie en temps réel.</span>
          </div>
          <div style="font-size:13px;color:#c2c6d2;display:flex;align-items:center;gap:24px;">
            <span>Mentions légales</span><span>CGU</span><span>Confidentialité</span>
            <span style="color:#8aa0d0;">© 2026 LumenX — Tous droits réservés.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==================================================================
# BRANCHE DÉMO — Choix du profil
# ==================================================================
def ecran_demo_profil():
    """Branche démo : le testeur choisit un profil, qui charge un jeu de
    données fictives et l'envoie directement au tableau de bord."""
    st.button("← Retour à l'accueil", on_click=go, args=("accueil",))
    gauche, centre, droite = st.columns([1, 2, 1])
    with centre:
        st.title("Tester la démo")
        st.caption("Choisissez un profil — il charge des données de trésorerie fictives.")
        st.write("")
        # Chaque bouton mémorise le profil puis va au tableau de bord.
        for p in ["PME", "Free-Lance", "SaaS", "Libéral"]:
            st.button(p, use_container_width=True, on_click=set_profil, args=(p, "dashboard"))


# ==================================================================
# BRANCHE INSCRIPTION — Connexion
# ==================================================================
def ecran_auth():
    """Écran de connexion en deux volets : à gauche la marque + arguments de
    valeur, à droite les boutons Microsoft / Google. La case « compte existant »
    (en bas) simule un client déjà inscrit : voir la fonction connexion()."""
    # CSS propre à cet écran (positionnement des deux volets, boutons blancs).
    # .st-key-XXX cible un widget via son paramètre key="XXX".
    st.markdown(
        """
        <style>
        .stApp { background: #0A0A0F !important; }
        .st-key-left_pane { position: relative; z-index: 2; width: 420px; margin-left: auto; margin-right: 76px; }
        .st-key-right_pane { padding-left: 114px; }
        .st-key-retour_btn { margin-top: 38px; }
        .st-key-retour_btn button { background: transparent !important; border: 1px solid rgba(255,255,255,.3) !important; box-shadow: none !important; }
        .st-key-retour_btn button p { color: #C2C6D2 !important; }
        .st-key-ms_btn button, .st-key-google_btn button {
            background: #ffffff !important;
            border: 1.5px solid #31333F !important;
            box-shadow: 0 3px 12px rgba(0,0,0,.25);
            font-weight: 800;
            padding: 0.7rem 1rem;
            transition: all .15s ease;
        }
        .st-key-ms_btn button p, .st-key-google_btn button p { color: #1b1b1b !important; font-weight: 800 !important; }
        .st-key-ms_btn button:hover, .st-key-google_btn button:hover {
            background: #ffffff !important;
            box-shadow: 0 6px 18px rgba(0,0,0,.3);
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # --- Fond dégradé fixe (moitié gauche), sans texte ---
    st.markdown(
        '<div style="position:fixed;left:0;top:0;bottom:0;width:50%;z-index:0;pointer-events:none;'
        'background:radial-gradient(1300px 520px at 50% 115%, rgba(45,107,255,.28), transparent), #0A0A0F;"></div>',
        unsafe_allow_html=True,
    )
    gauche, droite = st.columns(2)
    # --- Volet gauche : marque + valeur (texte gauche, bloc à 2 cm du centre) ---
    with gauche:
        with st.container(key="left_pane"):
            st.markdown(
                """
                <div style="font-family:'Fraunces',serif;font-size:34px;font-weight:700;color:#fff;margin-bottom:26px;">Lumen<span style="color:#2D6BFF;">X</span></div>
                <div style="font-family:'Fraunces',serif;font-size:48px;font-weight:600;color:#fff;line-height:1.12;">Votre trésorerie,<br><span style="font-style:italic;color:#3B82F6;">pilotée en temps<br>réel.</span></div>
                <div style="margin-top:34px;display:flex;flex-direction:column;gap:18px;">
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Tous vos comptes en un seul endroit</div>
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Prévisions de cash en temps réel</div>
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Placez votre excédent en 1 clic</div>
                </div>
                <div style="margin-top:30px;color:#7e8596;font-size:13px;">🔒 Connexion sécurisée · données chiffrées</div>
                """,
                unsafe_allow_html=True,
            )
            st.button("← Retour à l'accueil", key="retour_btn", on_click=go, args=("accueil",))
    # --- Volet droit : formulaire de connexion ---
    with droite:
        with st.container(key="right_pane"):
            st.markdown(
                "<div style=\"font-family:'Fraunces',serif;font-size:44px;font-weight:700;color:#fff;line-height:1.1;\">Se connecter /<br>S'inscrire</div>"
                "<div style='color:#C2C6D2;font-size:17px;margin:14px 0 26px;'>Connexion sécurisée, gérée par votre fournisseur.</div>",
                unsafe_allow_html=True,
            )
            col_actions, _ = st.columns([1, 1.6])
            with col_actions:
                # La case (rendue plus bas) persiste dans st.session_state : on lit
                # sa valeur ici pour router la connexion vers la bonne destination.
                existant = st.session_state.get("simu_existant", False)
                st.button("Continuer avec Microsoft", key="ms_btn", use_container_width=True, on_click=connexion, args=(existant,))
                st.button("Continuer avec Google", key="google_btn", use_container_width=True, on_click=connexion, args=(existant,))
                st.caption("Utilisez votre e-mail professionnel.")
                st.markdown(
                    "<div style='margin-top:64px;background:#16244D;border-radius:10px;padding:12px 14px;font-size:14px;color:#C2C6D2;'>🔐 Pour une sécurité optimale, activez la double authentification (MFA).</div>",
                    unsafe_allow_html=True,
                )
                # Outil de démo (n'existe pas dans le produit réel) :
                # coché -> connexion directe au tableau de bord, sans onboarding.
                st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
                st.checkbox(
                    "🧪 Simuler un compte déjà existant",
                    key="simu_existant",
                    help="Démo : si coché, « Se connecter » mène directement au tableau de bord, "
                         "sans repasser par la création d'espace (KYB).",
                )


# ==================================================================
# INSCRIPTION — Acceptation des CGU
# ==================================================================
def ecran_cgu():
    """Acceptation CGU + RGPD (carte blanche sur fond sombre). Le bouton
    « Continuer » reste désactivé tant que les deux cases ne sont pas cochées."""
    # Carte blanche + surcharges de couleurs (texte foncé) ciblées via la key.
    st.markdown(
        """
        <style>
        .st-key-cgu_card { background:#FFFFFF; border:1px solid #EAEAEA; border-radius:18px; padding:34px 36px; box-shadow:0 18px 50px rgba(0,0,0,.45); }
        .st-key-cgu_card p, .st-key-cgu_card label, .st-key-cgu_card span { color:#333 !important; }
        .st-key-cgu_card button p { color:#ffffff !important; }
        .st-key-cgu_continue button[disabled] { background:#A9C5FF !important; border-color:#A9C5FF !important; opacity:1 !important; }
        .st-key-cgu_retour button { background:transparent !important; border:1px solid rgba(255,255,255,.3) !important; box-shadow:none !important; }
        .st-key-cgu_retour button p { color:#C2C6D2 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _, centre, _ = st.columns([1.3, 1, 1.3])
    with centre:
        st.button("← Retour", key="cgu_retour", on_click=go, args=("auth",))
        with st.container(key="cgu_card"):
            st.markdown(
                "<div style=\"font-family:'Fraunces',serif;font-size:30px;font-weight:700;color:#1c1a17;\">Conditions générales</div>"
                "<div style='color:#777;font-size:14px;margin:8px 0 18px;'>Dernière étape avant de créer votre espace.</div>",
                unsafe_allow_html=True,
            )
            cgu = st.checkbox("J'ai lu et j'accepte les conditions générales d'utilisation (CGU).")
            rgpd = st.checkbox("J'accepte la politique de confidentialité (RGPD).")
            st.write("")
            st.button(
                "Continuer",
                key="cgu_continue",
                type="primary", use_container_width=True,
                disabled=not (cgu and rgpd),
                on_click=go, args=("onb_societe",),
            )
            if not (cgu and rgpd):
                st.markdown(
                    "<div style='text-align:center;color:#999;font-size:12.5px;margin-top:8px;'>Cochez les deux cases pour continuer.</div>",
                    unsafe_allow_html=True,
                )


# ==================================================================
# ONBOARDING — éléments communs (panneau gauche + titre + encadrés)
# ==================================================================
def stepper_panel(active):
    """Panneau d'étapes vertical fixe à gauche (#060B1C) + thème sombre du centre.

    `active` = index de l'étape courante dans ETAPES.
    Étapes passées = pastille verte ✓ ; courante = pastille bleu clair ;
    à venir = contour gris. Injecte aussi le style sombre du contenu de droite
    (texte blanc, champs #1b2f52)."""
    st.markdown(
        """
        <style>
        .stApp { background: #0A0A0F !important; }
        .block-container { padding: 56px 64px 56px 522px !important; max-width: 100% !important; min-height: 100vh; display: block !important; }
        .block-container > div { margin-bottom: 0 !important; }
        .block-container p, .block-container label, .block-container li,
        .block-container [data-testid="stWidgetLabel"] p,
        .block-container [data-testid="stCaptionContainer"],
        .block-container [data-testid="stCaptionContainer"] p {
            color: #ffffff !important;
            -webkit-font-smoothing: antialiased;
            text-rendering: optimizeLegibility;
        }
        .block-container input, .block-container textarea, .block-container [data-baseweb="select"] > div,
        .block-container [data-testid="stFileUploaderDropzone"] { background: #1b2f52 !important; color: #ffffff !important; border: 1px solid #2c456f !important; }
        .block-container [data-testid="stBaseButton-secondary"] { background: #1b2f52 !important; border: 1px solid #2c456f !important; }
        .block-container [data-testid="stBaseButton-secondary"] p { color: #e6e8ee !important; }
        .block-container [data-testid="stBaseButton-primary"] p { color: #ffffff !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    lignes = ""
    for i, nom in enumerate(ETAPES):
        if i == active:
            lignes += (
                '<div style="display:flex;align-items:center;gap:16px;padding:15px 18px;margin-bottom:8px;border-radius:12px;background:rgba(90,150,255,.18);">'
                f'<span style="width:39px;height:39px;border-radius:50%;background:#5A96FF;color:#fff;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{i+1}</span>'
                f'<span style="color:#ffffff;font-size:21px;font-weight:600;">{nom}</span></div>'
            )
        elif i < active:
            lignes += (
                '<div style="display:flex;align-items:center;gap:16px;padding:15px 18px;margin-bottom:8px;">'
                '<span style="width:39px;height:39px;border-radius:50%;background:#22C55E;color:#fff;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">✓</span>'
                f'<span style="color:#dbe2ef;font-size:21px;">{nom}</span></div>'
            )
        else:
            lignes += (
                '<div style="display:flex;align-items:center;gap:16px;padding:15px 18px;margin-bottom:8px;">'
                f'<span style="width:39px;height:39px;border-radius:50%;border:1px solid #3a4566;color:#8a93ad;font-size:18px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{i+1}</span>'
                f'<span style="color:#8a93ad;font-size:21px;">{nom}</span></div>'
            )
    st.markdown(
        '<div style="position:fixed;left:0;top:0;bottom:0;width:450px;z-index:10;background:#060B1C;'
        'padding:52px 40px 52px 76px;box-sizing:border-box;overflow:auto;">'
        '<div style="font-family:\'Fraunces\',serif;font-size:33px;font-weight:700;color:#fff;margin-bottom:8px;">Lumen<span style="color:#2D6BFF;">X</span></div>'
        '<div style="color:#7e89a8;font-size:18px;margin-bottom:42px;">Création de votre espace</div>'
        + lignes + '</div>',
        unsafe_allow_html=True,
    )


def titre_section(txt, sous=""):
    """Titre Fraunces blanc + sous-titre gris, en tête du contenu de droite."""
    html = f"<div style=\"font-family:'Fraunces',serif;font-size:32px;font-weight:700;color:#ffffff;\">{txt}</div>"
    if sous:
        html += f"<div style='color:#9aa6bd;font-size:14px;margin:6px 0 24px;'>{sous}</div>"
    st.markdown(html, unsafe_allow_html=True)


# Encadré coloré réutilisable. ton : "ok" (vert), "error" (rouge),
# "muted" (gris, section désactivée), "info" (bleu).
_BOX = {
    "ok":    ("rgba(34,197,94,.16)",  "#22C55E", "#bbf7d0"),
    "error": ("rgba(239,68,68,.16)",  "#EF4444", "#fecaca"),
    "muted": ("rgba(148,163,184,.14)", "#475569", "#cbd5e1"),
    "info":  ("rgba(45,107,255,.14)",  "#2D6BFF", "#cdd8f5"),
}

def encadre(texte, ton="info"):
    """Affiche un petit encadré coloré (message d'état) selon `ton` (voir _BOX)."""
    bg, bord, txt = _BOX[ton]
    st.markdown(
        f"<div style='background:{bg};border:1px solid {bord};border-radius:10px;"
        f"padding:11px 14px;color:{txt};font-size:15px;margin:6px 0 14px;'>{texte}</div>",
        unsafe_allow_html=True,
    )


def ecran_onb_societe():
    """Étape 1 (Entreprise) — ACTIVE. Saisie du SIRET ; si valide, affiche une
    fiche société fictive à confirmer (simule l'API INSEE/Sirene)."""
    stepper_panel(0)
    st.button("← Retour", on_click=go, args=("cgu",))
    titre_section("Votre entreprise", "Saisissez votre SIRET — les informations sont récupérées via l'INSEE.")
    col, _ = st.columns([1.4, 2])
    with col:
        if not st.session_state.societe_found:
            st.text_input("SIRET (14 chiffres)", key="siret_input", placeholder="ex. 12345678900012")
            st.button("Rechercher", type="primary", on_click=rechercher_societe)
            if st.session_state.societe_error:
                encadre(st.session_state.societe_error, "error")
        else:
            s = st.session_state.societe
            encadre("Société trouvée. Vérifiez les informations puis confirmez.", "ok")
            with st.container(border=True):
                st.markdown(f"**{s['raison']}**")
                st.write(f"SIREN : {s['siren']}  ·  SIRET : {s['siret']}")
                st.write(f"Forme juridique : {s['forme']}")
                st.write(f"Adresse : {s['adresse']}")
                st.write(f"Code NAF / APE : {s['naf']}")
                st.caption("Données issues du répertoire Sirene de l'INSEE.")
            col_ok, col_non = st.columns(2)
            col_ok.button(
                "✅ C'est bien ma société",
                type="primary", use_container_width=True,
                on_click=go, args=("onb_representant",),
            )
            col_non.button(
                "Ce n'est pas ça",
                use_container_width=True,
                on_click=reset_societe,
            )


def ecran_grise(index, sous_titre, champs, precedent, suivant):
    """Écran d'une section non gérée dans le MVP : affiché mais grisé."""
    stepper_panel(index)
    st.button("← Retour", on_click=go, args=(precedent,))
    titre_section(sous_titre, "Étape non gérée dans le MVP — affichée à titre indicatif.")
    col, _ = st.columns([1.4, 2])
    with col:
        encadre("🔒 Section non gérée dans le MVP — champs désactivés. À venir.", "muted")
        for champ in champs:
            st.text_input(champ, disabled=True)
        st.divider()
        st.button(
            "Continuer",
            type="primary", use_container_width=True,
            on_click=go, args=(suivant,),
        )


# Liste déroulante des fonctions possibles du dirigeant (écran suivant).
FONCTIONS = [
    "Président",
    "Directeur Général",
    "Gérant",
    "Directeur Administratif et Financier (DAF)",
    "Trésorier",
    "Associé",
    "Autre",
]

def ecran_onb_representant():
    """Étape 2 (Dirigeant) — partiellement active : identité saisissable,
    pièces justificatives désactivées (hors MVP)."""
    stepper_panel(1)
    st.button("← Retour", on_click=go, args=("onb_societe",))
    titre_section("Le dirigeant", "Identité du représentant légal de l'entreprise.")
    col, _ = st.columns([1.4, 2])
    with col:
        st.text_input("Nom")
        st.text_input("Prénom")
        st.date_input(
            "Date de naissance",
            value=None,
            min_value=dt.date(1930, 1, 1),
            max_value=dt.date.today(),
            format="DD/MM/YYYY",
        )
        st.selectbox(
            "Fonction dans l'entreprise",
            FONCTIONS,
            index=None,
            placeholder="Sélectionnez une fonction",
        )
        encadre("🔒 Le reste de cette section est désactivé dans le MVP (à venir).", "muted")
        st.file_uploader("Pièce d'identité", disabled=True)
        st.file_uploader("Justificatif de pouvoir (Kbis < 3 mois)", disabled=True)
        st.divider()
        st.button(
            "Continuer",
            type="primary", use_container_width=True,
            on_click=go, args=("onb_investisseur",),
        )


# Étapes 4-6 (Bénéficiaires, Validation, Signature) : non gérées dans le MVP.
# Elles réutilisent toutes le même gabarit grisé `ecran_grise`.
def ecran_onb_ubo():
    ecran_grise(3, "Bénéficiaires effectifs", [], "onb_investisseur", "onb_validation")


def ecran_onb_validation():
    ecran_grise(4, "Validation du dossier", [], "onb_ubo", "onb_signature")


def ecran_onb_signature():
    ecran_grise(5, "Signature", [], "onb_validation", "onb_banque")


# ==================================================================
# ONBOARDING — Type d'investisseur (ACTIF)
# ==================================================================
def ecran_onb_investisseur():
    """Étape 3 (Profil) — ACTIVE. Questions de profilage (type d'investisseur,
    problématique, objectif, montant) qui personnaliseraient le tableau de bord."""
    stepper_panel(2)
    st.button("← Retour", on_click=go, args=("onb_representant",))
    titre_section("Votre profil & objectifs", "Ces réponses personnalisent votre tableau de bord.")
    col, _ = st.columns([1.4, 2])
    with col:
        st.selectbox("Type d'investisseur", ["Débutant", "Intermédiaire", "Expérimenté"])
        st.selectbox(
            "Votre problématique",
            [
                "Je me repose sur mon banquier / comptable",
                "J'ai peur de perdre de l'argent",
                "Mon suivi Excel est chronophage",
                "Je n'ai pas le temps",
                "Je ne sais pas par où commencer",
                "Autre",
            ],
        )
        st.selectbox(
            "Votre objectif",
            [
                "Faire fructifier l'épargne de mon entreprise",
                "Préparer un achat important",
                "Organiser ma trésorerie",
                "Épargner en cas de coup dur",
            ],
        )
        st.selectbox(
            "Montant de trésorerie excédentaire",
            ["< 10 k€", "10–50 k€", "50–150 k€", "150–500 k€", "> 500 k€"],
        )
        st.divider()
        st.button(
            "Continuer",
            type="primary", use_container_width=True,
            on_click=go, args=("onb_ubo",),
        )


# ==================================================================
# ONBOARDING — 3 bis. Connexion bancaire fictive (ACTIF)
# ==================================================================
def ecran_onb_banque():
    """Étape 7 (Comptes) — ACTIVE mais fictive. La connexion bancaire réelle
    (agrégateur) est remplacée par le choix d'un profil démo."""
    stepper_panel(6)
    st.button("← Retour", on_click=go, args=("onb_signature",))
    titre_section("Vos comptes", "Contrat signé et documents validés — connectez vos comptes.")
    col, _ = st.columns([1.4, 2])
    with col:
        encadre(
            "Pour le MVP, la connexion réelle est désactivée. Choisissez un type "
            "d'entreprise : il charge un jeu de données de trésorerie fictives.",
            "info",
        )
        for p in ["PME", "Free-Lance", "SaaS", "Libéral"]:
            st.button(
                p,
                use_container_width=True,
                on_click=set_profil, args=(p, "dashboard"),
            )


# ==================================================================
# ESPACE CLIENT — barre latérale de navigation (commune à tous les écrans
# de l'espace connecté : tableau de bord, mon profil, documents…)
# ==================================================================
# Rubriques de la barre latérale : (écran cible, icône Material, libellé).
# cible = None -> rubrique "à venir" (ouvre un écran grisé).
# Deux groupes séparés par une ligne : principal puis personnel.
NAV_PRINCIPAL = [
    ("dashboard", ":material/dashboard:",     "Tableau de bord"),
    (None,        ":material/account_balance:", "Comptes"),
    (None,        ":material/swap_horiz:",     "Flux"),
    (None,        ":material/show_chart:",     "Prévisionnel"),
    (None,        ":material/trending_up:",    "Placements"),
]
NAV_PERSO = [
    ("espace_profil",    ":material/person:",      "Mon profil"),
    ("espace_documents", ":material/description:", "Documents"),
    (None,               ":material/settings:",    "Paramètres"),
]

def _sep_sidebar():
    st.markdown("<div style='height:1px;background:#1a2336;margin:12px 6px;'></div>", unsafe_allow_html=True)

def _nav_item(cible, icone, label, active):
    """Un bouton de navigation. Icône native Material (cliquable). La rubrique
    courante reçoit la key 'nav_active' qui déclenche son surlignage en CSS."""
    est_actif = (cible == active)
    st.button(
        label, icon=icone, use_container_width=True,
        key="nav_active" if est_actif else f"nav_{label}",
        on_click=go, args=(cible or "espace_avenir",),
    )

def sidebar_espace(active):
    """Barre latérale de l'espace client (st.sidebar restylé en bleu nuit, comme
    le panneau d'onboarding). Items alignés à gauche, deux groupes séparés par
    une ligne. La rubrique `active` est surlignée. Ne jamais passer active=None."""
    st.markdown(
        """
        <style>
        /* Contenu principal : on annule le centrage global, padding normal */
        .block-container { padding: 26px 34px !important; max-width: 100% !important;
            min-height: 100vh; display: block !important; }
        .block-container > div { margin-bottom: 0 !important; }
        /* Barre latérale aux couleurs de la marque */
        [data-testid="stSidebar"] { background: #060B1C; border-right: 1px solid #1a2336; }

        /* Colonne pleine hauteur pour pouvoir coller un bloc tout en bas */
        [data-testid="stSidebarUserContent"] { min-height: calc(100vh - 1.5rem); display: flex; flex-direction: column; }
        [data-testid="stSidebarUserContent"] > div { flex: 1 1 auto; display: flex; flex-direction: column; }
        [data-testid="stSidebar"] .st-key-nav_bottom { margin-top: auto !important; }

        /* Boutons de nav : transparents + alignés à GAUCHE (icône puis texte) */
        [data-testid="stSidebar"] button {
            background: transparent !important; border: none !important; box-shadow: none !important;
            color: #aab3c7 !important; font-weight: 500 !important; padding: 7px 12px !important;
            justify-content: flex-start !important; text-align: left !important;
        }
        [data-testid="stSidebar"] button > div { justify-content: flex-start !important; width: 100% !important; text-align: left !important; }
        [data-testid="stSidebar"] button p { text-align: left !important; }
        [data-testid="stSidebar"] button:hover { background: rgba(45,107,255,.12) !important; color: #ffffff !important; }
        /* Rubrique courante : surlignée en bleu */
        [data-testid="stSidebar"] .st-key-nav_active button { background: rgba(45,107,255,.16) !important; color: #ffffff !important; font-weight: 600 !important; }
        [data-testid="stSidebar"] .st-key-nav_active button p { color: #ffffff !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown(
            "<div style=\"font-family:'Fraunces',serif;font-size:30px;font-weight:700;"
            "color:#fff;margin-top:-10px;padding:0 6px 18px;\">Lumen<span style='color:#2D6BFF;'>X</span></div>",
            unsafe_allow_html=True,
        )
        for cible, icone, label in NAV_PRINCIPAL:
            _nav_item(cible, icone, label, active)
        _sep_sidebar()
        for cible, icone, label in NAV_PERSO:
            _nav_item(cible, icone, label, active)
        # Bloc bas épinglé tout en bas de la barre (voir CSS .st-key-nav_bottom).
        with st.container(key="nav_bottom"):
            _sep_sidebar()
            st.markdown(
                "<div style='color:#e8ecf4;font-size:16px;font-weight:600;padding:2px 12px 6px;'>Société Démo</div>",
                unsafe_allow_html=True,
            )
            st.button("Se déconnecter", icon=":material/logout:", key="nav_logout",
                      use_container_width=True, on_click=go, args=("accueil",))


# ------- petite carte HTML réutilisable (titre + contenu) pour l'espace -------
def _carte(html_interne, titre=None):
    haut = (f"<div style='font-size:14px;color:#c2c6d2;margin-bottom:12px;'>{titre}</div>" if titre else "")
    st.markdown(
        "<div style='background:#0E0E16;border:1px solid #20202c;border-radius:16px;"
        f"padding:18px 20px;margin-bottom:14px;'>{haut}{html_interne}</div>",
        unsafe_allow_html=True,
    )


def _report_previsionnel():
    """Onglet Prévisionnel : solde projeté, runway, courbe de prévision, mouvements."""
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;display:flex;justify-content:space-between;">Solde projeté (fin de mois)
              <span style="color:#28c76f;background:rgba(40,199,111,.12);border-radius:20px;padding:1px 7px;font-size:11px;">▲ 5,6 %</span></div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">1 310 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Runway (mois de trésorerie)</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">14 mois</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Point bas projeté</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">980 000 € <span style="font-size:13px;color:#8a90a0;font-weight:500;">· J+52</span></div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px;margin-top:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:16px;font-weight:600;color:#e8ecf4;">Projection de trésorerie (90 j)</span><span style="font-size:13px;color:#8a90a0;">réel —— · prévision - - -</span></div>
          <svg viewBox="0 0 320 120" preserveAspectRatio="none" style="width:100%;height:300px;margin-top:12px;">
            <defs><linearGradient id="gp" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2D6BFF" stop-opacity="0.30"/><stop offset="1" stop-color="#2D6BFF" stop-opacity="0"/></linearGradient></defs>
            <polygon fill="url(#gp)" points="0,80 40,72 80,76 120,58 160,64 160,120 0,120"/>
            <polyline fill="none" stroke="#2D6BFF" stroke-width="2.5" points="0,80 40,72 80,76 120,58 160,64"/>
            <polyline fill="none" stroke="#5A96FF" stroke-width="2.5" stroke-dasharray="6 5" points="160,64 200,92 240,60 280,48 320,34"/>
            <line x1="160" y1="8" x2="160" y2="120" stroke="#3a4566" stroke-width="1" stroke-dasharray="3 3"/>
          </svg>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:6px;">Prochains mouvements majeurs</div>
          <div style="display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">28/06 · Encaissement client Acme</span><span style="color:#28c76f;font-size:15px;font-weight:700;">+85 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">30/06 · Salaires</span><span style="color:#ff7a7a;font-size:15px;font-weight:700;">−142 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">05/07 · TVA</span><span style="color:#ff7a7a;font-size:15px;font-weight:700;">−38 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">10/07 · Abonnements clients</span><span style="color:#28c76f;font-size:15px;font-weight:700;">+60 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">15/07 · Loyer</span><span style="color:#ff7a7a;font-size:15px;font-weight:700;">−12 000 €</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _barre(label, valeur, pct, couleur="#2D6BFF"):
    return (
        "<div style='display:flex;align-items:center;gap:10px;margin:12px 0;'>"
        f"<div style='width:170px;font-size:14px;color:#c2c6d2;'>{label}</div>"
        "<div style='flex:1;height:10px;background:#1c1c2a;border-radius:6px;'>"
        f"<div style='width:{pct}%;height:100%;background:{couleur};border-radius:6px;'></div></div>"
        f"<div style='width:95px;text-align:right;font-size:14px;color:#fff;font-weight:600;'>{valeur}</div></div>"
    )


def _report_flux():
    """Onglet Flux & catégories : encaissements/décaissements et répartition."""
    enc = (
        _barre("Ventes & abonnements", "430 000 €", 80)
        + _barre("Subventions", "60 000 €", 20)
        + _barre("Autres", "50 000 €", 16)
    )
    dec = (
        _barre("Salaires", "210 000 €", 75, "#5A96FF")
        + _barre("Fournisseurs", "120 000 €", 43, "#5A96FF")
        + _barre("Charges & impôts", "82 000 €", 29, "#5A96FF")
    )
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Encaissements (mois)</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">540 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Décaissements (mois)</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">412 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Flux net</div>
            <div style="font-size:25px;font-weight:800;color:#28c76f;margin-top:6px;">+128 000 €</div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:6px;">Flux de trésorerie du mois (Sankey)</div>
          <svg viewBox="0 0 820 300" style="width:100%;height:auto;">
            <path d="M223,20 C301,20 301,20 380,20 L380,211 C301,211 301,211 223,211 Z" fill="rgba(40,199,111,.28)"/>
            <path d="M223,211 C301,211 301,211 380,211 L380,238 C301,238 301,238 223,238 Z" fill="rgba(40,199,111,.28)"/>
            <path d="M223,238 C301,238 301,238 380,238 L380,260 C301,260 301,260 223,260 Z" fill="rgba(40,199,111,.28)"/>
            <path d="M400,20 C480,20 480,20 560,20 L560,113 C480,113 480,113 400,113 Z" fill="rgba(90,150,255,.28)"/>
            <path d="M400,113 C480,113 480,113 560,113 L560,167 C480,167 480,167 400,167 Z" fill="rgba(90,150,255,.28)"/>
            <path d="M400,167 C480,167 480,167 560,167 L560,203 C480,203 480,203 400,203 Z" fill="rgba(90,150,255,.28)"/>
            <path d="M400,203 C480,203 480,203 560,203 L560,260 C480,260 480,260 400,260 Z" fill="rgba(40,199,111,.28)"/>
            <rect x="208" y="20" width="15" height="191" rx="2" fill="#28c76f"/>
            <rect x="208" y="211" width="15" height="27" rx="2" fill="#28c76f"/>
            <rect x="208" y="238" width="15" height="22" rx="2" fill="#28c76f"/>
            <rect x="380" y="20" width="20" height="240" rx="2" fill="#2D6BFF"/>
            <rect x="560" y="20" width="15" height="93" rx="2" fill="#5A96FF"/>
            <rect x="560" y="113" width="15" height="54" rx="2" fill="#5A96FF"/>
            <rect x="560" y="167" width="15" height="36" rx="2" fill="#5A96FF"/>
            <rect x="560" y="203" width="15" height="57" rx="2" fill="#28c76f"/>
            <g font-family="Inter,sans-serif" font-size="12.5" fill="#e8ecf4">
              <text x="200" y="119" text-anchor="end">Ventes &amp; abonnements · 430 k€</text>
              <text x="200" y="228" text-anchor="end">Subventions · 60 k€</text>
              <text x="200" y="252" text-anchor="end">Autres · 50 k€</text>
              <text x="390" y="13" text-anchor="middle" fill="#9fc0ff">Trésorerie · 540 k€</text>
              <text x="583" y="70" text-anchor="start">Salaires · 210 k€</text>
              <text x="583" y="143" text-anchor="start">Fournisseurs · 120 k€</text>
              <text x="583" y="188" text-anchor="start">Charges &amp; impôts · 82 k€</text>
              <text x="583" y="234" text-anchor="start">Épargne / placé · 128 k€</text>
            </g>
          </svg>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;">
          <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;">
            <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:8px;">Encaissements par catégorie</div>{enc}</div>
          <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;">
            <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:8px;">Décaissements par catégorie</div>{dec}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ligne_budget(poste, budget, reel, ecart, coul):
    cell = "padding:14px 10px;border-top:1px solid #20202c;font-size:15px;"
    return (
        f"<div style='{cell}color:#fff;'>{poste}</div>"
        f"<div style='{cell}color:#c2c6d2;text-align:right;'>{budget}</div>"
        f"<div style='{cell}color:#fff;text-align:right;'>{reel}</div>"
        f"<div style='{cell}color:{coul};text-align:right;font-weight:700;'>{ecart}</div>"
    )


def _report_budget():
    """Onglet Budget vs réalisé : comparaison par poste et écarts."""
    entete = "padding:0 10px 8px;font-size:13px;color:#8a90a0;"
    lignes = (
        _ligne_budget("Salaires", "210 000 €", "210 000 €", "0 €", "#8a90a0")
        + _ligne_budget("Marketing", "60 000 €", "48 000 €", "−12 000 € (−20 %)", "#28c76f")
        + _ligne_budget("Fournisseurs", "110 000 €", "120 000 €", "+10 000 € (+9 %)", "#ff7a7a")
        + _ligne_budget("Charges & impôts", "70 000 €", "34 000 €", "−36 000 € (−51 %)", "#28c76f")
    )
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Budget (mois)</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">450 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Réalisé</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">412 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Écart</div>
            <div style="font-size:25px;font-weight:800;color:#28c76f;margin-top:6px;">−38 000 € <span style="font-size:14px;font-weight:600;">(−8,4 %)</span></div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:10px;">Par poste — budget vs réalisé</div>
          <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;">
            <div style="{entete}">Poste</div><div style="{entete}text-align:right;">Budget</div><div style="{entete}text-align:right;">Réalisé</div><div style="{entete}text-align:right;">Écart</div>
            {lignes}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _report_placements():
    """Onglet Placements : détail par produit (montant, rendement, gain, maturité)."""
    cell = "padding:14px 10px;border-top:1px solid #20202c;font-size:15px;"
    def lg(prod, montant, rdt, gain, mat):
        return (
            f"<div style='{cell}color:#fff;'>{prod}</div>"
            f"<div style='{cell}color:#fff;text-align:right;'>{montant}</div>"
            f"<div style='{cell}color:#9fc0ff;text-align:right;'>{rdt}</div>"
            f"<div style='{cell}color:#28c76f;text-align:right;'>{gain}</div>"
            f"<div style='{cell}color:#c2c6d2;text-align:right;'>{mat}</div>"
        )
    ent = "padding:0 10px 8px;font-size:13px;color:#8a90a0;"
    lignes = (
        lg("Compte à terme 12 mois", "100 000 €", "3,8 %", "3 800 €", "15/03/2027")
        + lg("Fonds monétaire", "80 000 €", "3,2 %", "2 560 €", "Liquide")
        + lg("Obligations d'État", "50 000 €", "3,0 %", "1 500 €", "20/06/2028")
        + lg("Livret pro", "20 000 €", "2,1 %", "420 €", "Liquide")
    )
    maturite = (
        _barre("Liquide", "100 000 €", 40, "#28c76f")
        + _barre("1–2 ans", "100 000 €", 40)
        + _barre("> 2 ans", "50 000 €", 20, "#5A96FF")
    )
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Total placé</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">250 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Rendement moyen</div>
            <div style="font-size:25px;font-weight:800;color:#9fc0ff;margin-top:6px;">3,4 %</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Gain annuel estimé</div>
            <div style="font-size:25px;font-weight:800;color:#28c76f;margin-top:6px;">8 280 €</div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:10px;">Détail des placements</div>
          <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1.2fr;">
            <div style="{ent}">Produit</div><div style="{ent}text-align:right;">Montant</div><div style="{ent}text-align:right;">Rendement</div><div style="{ent}text-align:right;">Gain / an</div><div style="{ent}text-align:right;">Maturité</div>
            {lignes}
          </div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:8px;">Répartition par maturité</div>{maturite}</div>
        """,
        unsafe_allow_html=True,
    )


def _report_global():
    """Onglet Vue globale : synthèse agrégée (patrimoine, répartition, indicateurs)."""
    row = "display:flex;justify-content:space-between;padding:13px 0;border-top:1px solid #20202c;font-size:15px;"
    indicateurs = (
        f"<div style='{row}'><span style='color:#c2c6d2;'>Trésorerie consolidée</span><span style='color:#fff;font-weight:700;'>1 240 000 €</span></div>"
        f"<div style='{row}'><span style='color:#c2c6d2;'>Placements (rendement 3,4 %)</span><span style='color:#fff;font-weight:700;'>250 000 €</span></div>"
        f"<div style='{row}'><span style='color:#c2c6d2;'>Encaissements 30 j</span><span style='color:#fff;font-weight:700;'>320 000 €</span></div>"
        f"<div style='{row}'><span style='color:#c2c6d2;'>Flux net mensuel</span><span style='color:#28c76f;font-weight:700;'>+128 000 €</span></div>"
        f"<div style='{row}'><span style='color:#c2c6d2;'>Runway (mois de trésorerie)</span><span style='color:#fff;font-weight:700;'>14 mois</span></div>"
    )
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Patrimoine total</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">1 490 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Rendement global</div>
            <div style="font-size:25px;font-weight:800;color:#9fc0ff;margin-top:6px;">3,4 %</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Flux net mensuel</div>
            <div style="font-size:25px;font-weight:800;color:#28c76f;margin-top:6px;">+128 000 €</div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:12px;">Répartition du patrimoine</div>
          <div style="display:flex;height:20px;border-radius:10px;overflow:hidden;">
            <div style="width:83%;background:#2D6BFF;"></div><div style="width:17%;background:#28c76f;"></div></div>
          <div style="display:flex;gap:24px;margin-top:12px;font-size:14px;color:#c2c6d2;">
            <span><span style="color:#2D6BFF;">●</span> Disponible · 1 240 000 € (83 %)</span>
            <span><span style="color:#28c76f;">●</span> Placé · 250 000 € (17 %)</span></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="font-size:16px;font-weight:600;color:#e8ecf4;margin-bottom:2px;">Indicateurs clés agrégés</div>{indicateurs}</div>
        """,
        unsafe_allow_html=True,
    )


def ecran_dashboard():
    """Tableau de bord de l'espace client : onglets de reporting (Synthèse + 3).
    Barre latérale + KPI + courbe + placement + comptes (Synthèse), puis
    Prévisionnel, Flux & catégories, Budget vs réalisé. Données fictives."""
    sidebar_espace("dashboard")
    profil = st.session_state.profil or "—"
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <div style="display:flex;align-items:flex-end;gap:14px;"><span style="font-family:'Fraunces',serif;font-size:42px;font-weight:700;color:#fff;line-height:1;">Tableau de bord</span>
            <span style="font-size:15px;color:#cdd8f5;background:rgba(45,107,255,.14);border:1px solid #2D6BFF;border-radius:22px;padding:6px 16px;">Profil · {profil}</span></div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:15px;color:#a9c0f0;background:rgba(45,107,255,.10);border-left:3px solid #2D6BFF;padding:10px 14px;border-radius:0 8px 8px 0;">🧪 Données de démonstration · jeu de transactions fictif</div>
        """,
        unsafe_allow_html=True,
    )
    # ----- Onglets de reporting (Synthèse + 3 rapports) -----
    st.markdown(
        "<style>"
        "[data-baseweb='tab-list']{gap:7px !important;border-bottom:1px solid #1a2336;}"
        "button[data-baseweb='tab']{"
        "background:#0d1526 !important;border:1px solid #1a2336 !important;border-bottom:none !important;"
        "border-radius:10px 10px 0 0 !important;padding:10px 26px !important;margin:0 !important;"
        "font-size:15px !important;color:#aab3c7 !important;}"
        "button[data-baseweb='tab'] p{color:inherit !important;font-size:15px !important;}"
        "button[data-baseweb='tab']:hover{background:#13203a !important;color:#ffffff !important;}"
        "button[data-baseweb='tab'][aria-selected='true']{background:#15294d !important;color:#ffffff !important;font-weight:600 !important;}"
        "[data-baseweb='tab-highlight']{background:#2D6BFF !important;height:3px !important;}"
        "[data-baseweb='tab-border']{background:transparent !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    onglets = st.tabs(["Synthèse", "Prévisionnel", "Flux & catégories", "Budget vs réalisé", "Placements", "Vue globale"])
    with onglets[0]:
        st.markdown(
            """
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px;">
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;display:flex;justify-content:space-between;">Trésorerie consolidée
              <span style="color:#28c76f;background:rgba(40,199,111,.12);border-radius:20px;padding:1px 7px;font-size:11px;">▲ 4,2 %</span></div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">1 240 000 €</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Encaissements 30 j</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">320 k€</div></div>
          <div style="background:#15151f;border-radius:12px;padding:14px 16px;">
            <div style="font-size:16px;color:#aab4c4;">Comptes connectés</div>
            <div style="font-size:25px;font-weight:800;color:#fff;margin-top:6px;">4</div></div>
        </div>

        <div style="display:grid;grid-template-columns:1.6fr 1fr;gap:12px;margin-top:12px;">
          <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:16px;font-weight:600;color:#e8ecf4;">Évolution de la trésorerie</span><span style="font-size:11px;color:#8a90a0;">90 j</span></div>
            <svg viewBox="0 0 320 110" preserveAspectRatio="none" style="width:100%;height:380px;margin-top:12px;">
              <defs><linearGradient id="gd" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2D6BFF" stop-opacity="0.35"/><stop offset="1" stop-color="#2D6BFF" stop-opacity="0"/></linearGradient></defs>
              <polygon fill="url(#gd)" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50 270,34 300,40 320,28 320,110 0,110"/>
              <polyline fill="none" stroke="#2D6BFF" stroke-width="2.5" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50 270,34 300,40 320,28"/>
            </svg></div>
          <div style="background:#12121c;border:1px solid #2a2a3a;border-radius:16px;padding:18px;min-height:440px;display:flex;flex-direction:column;">
            <div style="display:flex;align-items:center;gap:8px;font-size:16px;font-weight:600;color:#e8ecf4;"><span style="width:16px;height:16px;border-radius:50%;background:#2D6BFF;display:inline-block;"></span>Placer mon excédent</div>
            <div style="font-size:28px;font-weight:800;color:#fff;margin:14px 0 2px;">250 000 €</div>
            <div style="display:flex;justify-content:space-between;font-size:14px;color:#9aa4b5;margin-bottom:16px;">Disponible <span style="color:#dfe5f0;">500 000 €</span></div>
            <div style="display:flex;gap:6px;">
              <span style="flex:1;text-align:center;font-size:14px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:9px 0;">25%</span>
              <span style="flex:1;text-align:center;font-size:14px;color:#fff;background:#2D6BFF;border-radius:8px;padding:9px 0;">50%</span>
              <span style="flex:1;text-align:center;font-size:14px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:9px 0;">75%</span>
              <span style="flex:1;text-align:center;font-size:14px;color:#c2c6d2;background:#1c1c2a;border-radius:8px;padding:9px 0;">100%</span></div>
            <div style="flex:1;"></div>
            <div style="text-align:center;font-size:15px;font-weight:600;color:#fff;background:#2D6BFF;border-radius:9px;padding:13px 0;">Simuler un placement</div></div>
        </div>

        <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;margin-top:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:16px;font-weight:600;color:#e8ecf4;">Comptes bancaires</span><span style="font-size:14px;color:#2D6BFF;">Voir tout</span></div>
          <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #20202c;margin-top:6px;"><span style="color:#fff;font-size:15px;">Compte courant — BNP <span style='color:#8a90a0;'>· FR76 •••• 4021</span></span><span style="color:#fff;font-size:15px;font-weight:700;">540 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">Livret société — Qonto <span style='color:#8a90a0;'>· FR76 •••• 8830</span></span><span style="color:#fff;font-size:15px;font-weight:700;">420 000 €</span></div>
          <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #20202c;"><span style="color:#fff;font-size:15px;">Compte épargne — Crédit Agricole <span style='color:#8a90a0;'>· FR76 •••• 6094</span></span><span style="color:#fff;font-size:15px;font-weight:700;">280 000 €</span></div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with onglets[1]:
        _report_previsionnel()
    with onglets[2]:
        _report_flux()
    with onglets[3]:
        _report_budget()
    with onglets[4]:
        _report_placements()
    with onglets[5]:
        _report_global()


def espace_profil():
    """Mon profil : informations entreprise + dirigeant en lecture seule (démo)."""
    sidebar_espace("espace_profil")
    s = st.session_state.societe
    raison = s["raison"] if s else "Société Démo SAS"
    siren = s["siren"] if s else "812 345 678"
    forme = s["forme"] if s else "SAS"
    adresse = s["adresse"] if s else "12 rue de la Démo, 75002 Paris"
    naf = s["naf"] if s else "6201Z — Programmation informatique"
    st.markdown(
        "<div style=\"font-family:'Fraunces',serif;font-size:30px;font-weight:700;color:#fff;margin-bottom:16px;\">Mon profil</div>",
        unsafe_allow_html=True,
    )
    ligne = "<div style='display:flex;justify-content:space-between;padding:9px 0;border-top:1px solid #20202c;font-size:15px;'><span style='color:#8a90a0;'>{k}</span><span style='color:#fff;'>{v}</span></div>"
    _carte(
        "".join([
            ligne.format(k="Raison sociale", v=raison),
            ligne.format(k="SIREN", v=siren),
            ligne.format(k="Forme juridique", v=forme),
            ligne.format(k="Siège social", v=adresse),
            ligne.format(k="Code NAF / APE", v=naf),
        ]),
        titre="🏢 Entreprise",
    )
    _carte(
        "".join([
            ligne.format(k="Dirigeant", v="Camille Démo"),
            ligne.format(k="Fonction", v="Président"),
            ligne.format(k="E-mail", v="camille@societe-demo.fr"),
        ]),
        titre="👤 Représentant légal",
    )
    st.caption("Lecture seule dans le MVP — la modification arrivera plus tard.")


def espace_documents():
    """Documents : pièces de conformité et relevés (démo, téléchargement inerte)."""
    sidebar_espace("espace_documents")
    st.markdown(
        "<div style=\"font-family:'Fraunces',serif;font-size:30px;font-weight:700;color:#fff;margin-bottom:16px;\">Documents</div>",
        unsafe_allow_html=True,
    )
    docs = [
        ("Extrait Kbis", "PDF · 240 Ko", "Validé", "#22C55E"),
        ("Pièce d'identité du dirigeant", "PDF · 1,1 Mo", "Validé", "#22C55E"),
        ("RIB — compte courant BNP", "PDF · 88 Ko", "Validé", "#22C55E"),
        ("Contrat LumenX", "PDF · 320 Ko", "Signé", "#2D6BFF"),
        ("Relevé de trésorerie — T1 2026", "PDF · 510 Ko", "Disponible", "#8a90a0"),
    ]
    lignes = ""
    for nom, meta, statut, coul in docs:
        lignes += (
            "<div style='display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-top:1px solid #20202c;'>"
            f"<div style='display:flex;align-items:center;gap:12px;'><span style='font-size:18px;'>📄</span>"
            f"<div><div style='color:#fff;font-size:15px;'>{nom}</div><div style='color:#8a90a0;font-size:11.5px;'>{meta}</div></div></div>"
            f"<div style='display:flex;align-items:center;gap:14px;'>"
            f"<span style='font-size:11.5px;color:{coul};border:1px solid {coul};border-radius:20px;padding:2px 9px;'>{statut}</span>"
            "<span style='color:#2D6BFF;font-size:12.5px;'>⬇ Télécharger</span></div></div>"
        )
    _carte(lignes)
    st.caption("Documents de démonstration — téléchargement désactivé dans la maquette.")


def espace_avenir():
    """Rubrique de l'espace non développée dans le MVP (Comptes, Flux, etc.)."""
    sidebar_espace("espace_avenir")  # ne correspond à aucune rubrique -> aucun surlignage
    st.markdown(
        "<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "min-height:60vh;color:#8a93ad;text-align:center;'>"
        "<div style='font-size:42px;margin-bottom:10px;'>🚧</div>"
        "<div style=\"font-family:'Fraunces',serif;font-size:26px;color:#fff;\">Rubrique à venir</div>"
        "<div style='font-size:14px;margin-top:8px;'>Cette section n'est pas développée dans le MVP.</div></div>",
        unsafe_allow_html=True,
    )


# ==================================================================
# BOUTON D'AVIS — flottant, présent sur tous les écrans.
# Envoie nom + écran courant + commentaire vers un Google Form (qui alimente
# une Google Sheet). Pas de clé/secret : on POST sur l'URL publique du form.
# ==================================================================
_FORM_ACTION = ("https://docs.google.com/forms/d/e/"
                "1FAIpQLScmI4n2npD2S4soyTazoU7Cjz1MNcBm5AEk_bmALuGb72M4Eg/formResponse")
_FORM_FIELDS = {
    "nom": "entry.1772696514",
    "ecran": "entry.306899172",
    "commentaire": "entry.1362605707",
}
# Noms lisibles des écrans (pour la colonne « Écran » de la feuille).
ECRAN_LABELS = {
    "accueil": "Accueil", "demo_profil": "Choix profil démo", "auth": "Connexion",
    "cgu": "CGU / RGPD", "onb_societe": "Onboarding – Entreprise",
    "onb_representant": "Onboarding – Dirigeant", "onb_investisseur": "Onboarding – Profil",
    "onb_ubo": "Onboarding – Bénéficiaires", "onb_validation": "Onboarding – Validation",
    "onb_signature": "Onboarding – Signature", "onb_banque": "Onboarding – Comptes",
    "dashboard": "Tableau de bord", "espace_profil": "Mon profil",
    "espace_documents": "Documents", "espace_avenir": "Rubrique à venir",
}

def _envoyer_avis(nom, ecran, commentaire):
    """POST le commentaire vers le Google Form. Renvoie True si l'envoi a réussi."""
    data = urllib.parse.urlencode({
        _FORM_FIELDS["nom"]: nom,
        _FORM_FIELDS["ecran"]: ecran,
        _FORM_FIELDS["commentaire"]: commentaire,
    }).encode("utf-8")
    req = urllib.request.Request(_FORM_ACTION, data=data,
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        urllib.request.urlopen(req, timeout=6)
        return True
    except Exception:
        return False

def widget_avis():
    """Bouton flottant '💬 Donner mon avis' affiché sur chaque écran."""
    st.markdown(
        "<style>.st-key-feedback_fab{position:fixed;right:28px;bottom:70px;z-index:9999;}"
        ".st-key-feedback_fab [data-testid='stPopover'] button{background:#2D6BFF !important;"
        "color:#fff !important;border:none !important;font-weight:600 !important;border-radius:24px !important;"
        "padding:10px 18px !important;box-shadow:0 6px 18px rgba(0,0,0,.35) !important;}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="feedback_fab"):
        with st.popover("💬 Donner mon avis"):
            st.markdown("**Votre avis sur cet écran**")
            nom = st.text_input("Votre nom (optionnel)", key="avis_nom")
            commentaire = st.text_area("Commentaire", key="avis_txt",
                                       placeholder="Ce qui vous plaît, ce qui cloche, vos idées…")
            if st.button("Envoyer", type="primary", key="avis_send"):
                if commentaire.strip():
                    ecran = ECRAN_LABELS.get(st.session_state.screen, st.session_state.screen)
                    if _envoyer_avis(nom.strip() or "Anonyme", ecran, commentaire.strip()):
                        st.success("Merci, votre avis est envoyé ✅")
                    else:
                        st.error("Échec de l'envoi — réessayez dans un instant.")
                else:
                    st.warning("Écrivez un commentaire avant d'envoyer.")


# ---------- ROUTEUR ----------
# Associe chaque nom d'écran à sa fonction. La dernière ligne exécute l'écran
# dont le nom est dans st.session_state["screen"] (mis à jour par les boutons).
ecrans = {
    "accueil": ecran_accueil,
    "demo_profil": ecran_demo_profil,
    "auth": ecran_auth,
    "cgu": ecran_cgu,
    "onb_societe": ecran_onb_societe,
    "onb_representant": ecran_onb_representant,
    "onb_investisseur": ecran_onb_investisseur,
    "onb_ubo": ecran_onb_ubo,
    "onb_validation": ecran_onb_validation,
    "onb_banque": ecran_onb_banque,
    "onb_signature": ecran_onb_signature,
    "dashboard": ecran_dashboard,
    "espace_profil": espace_profil,
    "espace_documents": espace_documents,
    "espace_avenir": espace_avenir,
}
# Affiche l'écran courant.
ecrans[st.session_state.screen]()
# Bouton d'avis flottant, sur tous les écrans.
widget_avis()
