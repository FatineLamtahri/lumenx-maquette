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
import streamlit as st
import streamlit.components.v1 as components

# layout="wide" = pleine largeur ; le titre apparaît dans l'onglet du navigateur.
st.set_page_config(page_title="LumenX | Investir et gérer sa trésorerie d'entreprise",
                   layout="wide", initial_sidebar_state="expanded")

# ---------- STYLE GLOBAL (s'applique à tous les écrans) ----------
# Certains écrans (auth, onboarding) réinjectent ensuite leur propre CSS par-dessus.
st.markdown(
    """
    <style>
    /* Polices de marque chargées depuis Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,600;1,600&family=Poppins:wght@400;500;600;700;800&display=swap');
    /* Poppins = police par défaut du corps de texte sur tout l'app */
    html, body, [class*="css"], .stApp, p, div, span, label, button, input, select, textarea {
        font-family: 'Poppins', sans-serif;
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
    /* --- Cartes de questions du profil (bordure bleue translucide) --- */
    [class*='qcard']{background:rgba(45,107,255,0.06) !important;border:1px solid rgba(45,107,255,0.45) !important;border-radius:14px !important;padding:10px 22px 16px !important;margin-bottom:16px !important;}
    [class*='qcard'] div[role='radiogroup'] label{margin:6.75px 0 !important;gap:12px !important;}
    [class*='qcard'] div[role='radiogroup']{gap:4.5px !important;}
    [class*='qcard'] [data-testid='stWidgetLabel'] p{font-size:15.5px !important;font-weight:600 !important;margin-bottom:8px !important;}
    [class*='qcard'] div[role='radiogroup'] label p{font-size:15px !important;font-weight:400 !important;}
    /* Case « Simuler un compte existant » : garder sur une seule ligne */
    .st-key-simu_existant label p{white-space:nowrap !important;}
    /* --- Bouton d'avis flottant --- */
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
ETAPES = ["Entreprise", "Dirigeant", "Secteur d'activité", "Objectifs", "Bénéficiaires", "Validation", "Signature", "Comptes"]


# Widget "trésorerie" affiché à droite de l'accueil (flux -> horizons -> placement,
# avec animations SVG). Rendu via components.html (iframe) pour garder les anims.
WIDGET_TRESORERIE = """
<style>html,body{margin:0;background:transparent;}</style>
<div style="background:#0B1220;border:0.5px solid #1E2A3D;border-radius:16px;padding:1.75rem;max-width:720px;font-family:'Segoe UI',Arial,sans-serif;position:relative;overflow:hidden;margin:0 auto">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:22px">
    <span style="font-size:13px;color:#7C8AA5">Trésorerie consolidée</span>
    <span style="background:rgba(29,158,117,0.15);color:#5DCAA5;font-size:12px;font-weight:600;padding:3px 8px;border-radius:6px">▲ +4,2 %</span>
  </div>
  <svg width="100%" viewBox="0 0 580 250" style="display:block">
    <defs>
      <linearGradient id="lnIn2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#3B7DE8" stop-opacity="0.6"/><stop offset="100%" stop-color="#3B7DE8" stop-opacity="0.15"/></linearGradient>
      <linearGradient id="lnOut2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#6FE0C4" stop-opacity="0.15"/><stop offset="100%" stop-color="#6FE0C4" stop-opacity="0.85"/></linearGradient>
    </defs>
    <path d="M150,36 C185,36 190,90 200,110" fill="none" stroke="url(#lnIn2)" stroke-width="2"/>
    <path d="M150,90 C185,90 195,105 200,115" fill="none" stroke="url(#lnIn2)" stroke-width="2"/>
    <path d="M150,144 C185,144 190,130 200,120" fill="none" stroke="url(#lnIn2)" stroke-width="2"/>
    <circle r="3.5" fill="#6FE0C4"><animateMotion dur="2.4s" repeatCount="indefinite" path="M150,36 C185,36 190,90 200,110"/></circle>
    <circle r="3.5" fill="#6FE0C4"><animateMotion dur="2.8s" repeatCount="indefinite" path="M150,90 C185,90 195,105 200,115"/></circle>
    <circle r="3.5" fill="#6FE0C4"><animateMotion dur="2.2s" repeatCount="indefinite" path="M150,144 C185,144 190,130 200,120"/></circle>
    <g>
      <rect x="10" y="14" width="140" height="44" rx="10" fill="#111B2C" stroke="#1E2A3D"/>
      <circle cx="30" cy="36" r="9" fill="#1D2C42"/>
      <path d="M25,39 l4,-8 l3,4 l5,-8" stroke="#5DCAA5" stroke-width="1.3" fill="none"/>
      <text x="46" y="32" font-size="10" fill="#B8C2D6">Encaissements clients</text>
      <text x="46" y="46" font-size="11" fill="#FFFFFF" font-weight="600">+620 000 €</text>
    </g>
    <g>
      <rect x="10" y="68" width="140" height="44" rx="10" fill="#111B2C" stroke="#1E2A3D"/>
      <circle cx="30" cy="90" r="9" fill="#1D2C42"/>
      <path d="M25,87 l4,8 l3,-4 l5,8" stroke="#D85A30" stroke-width="1.3" fill="none"/>
      <text x="46" y="86" font-size="10" fill="#B8C2D6">Sorties fournisseurs</text>
      <text x="46" y="100" font-size="11" fill="#FFFFFF" font-weight="600">-210 000 €</text>
    </g>
    <g>
      <rect x="10" y="122" width="140" height="44" rx="10" fill="#111B2C" stroke="#1E2A3D"/>
      <circle cx="30" cy="144" r="9" fill="#1D2C42"/>
      <path d="M25,141 l4,6 l3,-3 l5,6" stroke="#D85A30" stroke-width="1.3" fill="none"/>
      <text x="46" y="140" font-size="10" fill="#B8C2D6">Salaires &amp; charges</text>
      <text x="46" y="154" font-size="11" fill="#FFFFFF" font-weight="600">-90 000 €</text>
    </g>
    <rect x="200" y="10" width="170" height="215" rx="14" fill="#0F1A2C" stroke="#2A3A52" stroke-width="1.5"/>
    <text x="285" y="30" text-anchor="middle" font-size="11" fill="#7C8AA5">Trésorerie totale — 1 240 000 €</text>
    <rect x="212" y="45" width="146" height="48" rx="8" fill="rgba(59,125,232,0.14)" stroke="#3B7DE8" stroke-width="1"/>
    <text x="222" y="64" font-size="10" fill="#8FB4EE">Court terme</text>
    <text x="222" y="80" font-size="13" fill="#FFFFFF" font-weight="600">620 000 €</text>
    <rect x="212" y="101" width="146" height="48" rx="8" fill="rgba(127,119,221,0.16)" stroke="#7F77DD" stroke-width="1"/>
    <text x="222" y="120" font-size="10" fill="#BDB8F0">Moyen terme</text>
    <text x="222" y="136" font-size="13" fill="#FFFFFF" font-weight="600">380 000 €</text>
    <rect x="212" y="157" width="146" height="48" rx="8" fill="rgba(83,74,183,0.2)" stroke="#534AB7" stroke-width="1"/>
    <text x="222" y="176" font-size="10" fill="#B3ACE8">Long terme</text>
    <text x="222" y="192" font-size="13" fill="#FFFFFF" font-weight="600">240 000 €</text>
    <path d="M358,181 C395,181 400,181 418,181" fill="none" stroke="url(#lnOut2)" stroke-width="2.5"/>
    <circle r="4" fill="#6FE0C4"><animateMotion dur="1.8s" repeatCount="indefinite" path="M358,181 L418,181"/></circle>
    <rect x="418" y="136" width="152" height="92" rx="14" fill="#0F1A2C" stroke="#5DCAA5" stroke-width="1.5"/>
    <circle cx="444" cy="160" r="10" fill="rgba(93,202,165,0.15)"/>
    <path d="M439,163 l3,-7 l3,4 l5,-9" stroke="#5DCAA5" stroke-width="1.4" fill="none"/>
    <text x="460" y="158" font-size="10" fill="#7C8AA5">Excédent</text>
    <text x="460" y="171" font-size="10" fill="#7C8AA5">automatiquement</text>
    <text x="460" y="184" font-size="10" fill="#7C8AA5">investi</text>
    <text x="494" y="212" text-anchor="middle" font-size="14" fill="#5DCAA5" font-weight="600">240 000 €</text>
  </svg>
  <div style="margin-top:14px;font-size:11px;color:#5A6478;text-align:center">Vos flux sont classés par horizon, l'excédent long terme est placé automatiquement</div>
</div>
"""


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
    _, col_text, col_viz, _ = st.columns([0.5, 1.2, 1.3, 0.4], vertical_alignment="center")
    with col_text:
        # --- Encart texte : titre + accroche ---
        st.markdown(
            """
            <h1 style="font-family:'Fraunces',serif;font-size:52px;line-height:1.06;margin:0;font-weight:600;color:#fff;">Faites votre métier<br><span style="color:#3B82F6;font-size:40px;font-style:italic;">Nous faisons fructifier votre succès</span></h1>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:4px 0;">Votre priorité est de développer votre activité, d'innover et de satisfaire vos clients.</p>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:4px 0;">Le notre est de .... ?.</p>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:4px 0;">LumenX est la plateforme qui vous aide à optimiser l'argent de votre entreprise.</p>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:4px 0;">Laisser votre trésorerie dormir sur un compte courant classique n'est pas un choix de sécurité, c'est une perte sèche.</p>
            <p style="color:#C2C6D2;font-size:16px;font-weight:400;margin:0 0 28px;">Ne choisissez plus entre gérer votre entreprise et optimiser vos finances. Faites les deux!.</p>
            """,
            unsafe_allow_html=True,
        )
        # --- Encart de connexion : boutons + mention sécurité (alignés à gauche) ---
        bcol, _ = st.columns([2, 1])
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
        # --- Widget trésorerie (flux -> horizons -> placement, animé) ---
        components.html(WIDGET_TRESORERIE, height=430)

    # ===== BANDEAU BAS : footer (logo + liens légaux + copyright) =====
    st.markdown(
        """
        <div style="position:fixed;left:0;right:0;bottom:0;z-index:50;background:#16244D;border-top:1px solid #20202c;padding:14px 48px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;">
          <div>
            <span style="font-family:'Fraunces',serif;font-size:20px;font-weight:700;color:#fff;">Lumen<span style="color:#2D6BFF;">X</span></span>
            <span style="font-size:13px;color:#c2c6d2;margin-left:14px;">Faites votre métier. Nous faisons fructifier votre succès.</span>
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
        st.caption("Choisissez un profil.")
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
                <div style="font-family:'Fraunces',serif;font-size:28px;font-weight:700;color:#fff;margin-bottom:26px;">Lumen<span style="color:#2D6BFF;">X</span></div>
                <div style="font-family:'Fraunces',serif;font-size:32px;font-weight:600;color:#fff;line-height:1.12;">Faites votre métier,<br><span style="font-style:italic;color:#3B82F6;">Nous faisons fructifier votre succès.</span></div>
                <div style="margin-top:34px;display:flex;flex-direction:column;gap:18px;">
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Tous vos comptes en un seul endroit</div>
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Visualisation ordonnée de votre trésorerie</div>
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Prévisions de cash en temps réel</div>
                  <div style="color:#C2C6D2;font-size:18px;"><span style="color:#2D6BFF;">✓</span> Placement calibré de votre excédent</div>
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
                    "🧪 Simuler un compte existant",
                    key="simu_existant",
                    help="Démo : si coché, « Se connecter » mène directement au tableau de bord, "
                         "sans repasser par la création d'espace (KYB).",
                )


# ==================================================================
# INSCRIPTION — Acceptation des CGU
# ==================================================================
# Pages web des documents légaux (hébergées sur GitHub Pages du dépôt).
# ⚠️ Adapter le nom d'utilisateur/dépôt si besoin, puis activer Pages
#    (Settings → Pages → Deploy from a branch → main → /root).
_URL_CGU = "https://fatinelamtahri.github.io/lumenx-maquette/cgu.html"
_URL_RGPD = "https://fatinelamtahri.github.io/lumenx-maquette/confidentialite.html"


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
    _, centre, _ = st.columns([1, 0.9, 1])
    with centre:
        st.button("← Retour", key="cgu_retour", on_click=go, args=("auth",))
        with st.container(key="cgu_card"):
            st.markdown(
                "<div style=\"font-family:'Fraunces',serif;font-size:30px;font-weight:700;color:#1c1a17;\">Conditions générales</div>"
                "<div style='color:#777;font-size:14px;margin:8px 0 18px;'>Dernière étape avant de créer votre espace.</div>",
                unsafe_allow_html=True,
            )
            cgu = st.checkbox(
                f"J'ai lu et j'accepte les [conditions générales d'utilisation]({_URL_CGU}) (CGU)."
            )
            rgpd = st.checkbox(
                f"J'accepte la [politique de confidentialité]({_URL_RGPD}) (RGPD)."
            )
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
                f'<span style="width:32px;height:32px;border-radius:50%;background:#5A96FF;color:#fff;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{i+1}</span>'
                f'<span style="color:#ffffff;font-size:18px;font-weight:600;">{nom}</span></div>'
            )
        elif i < active:
            lignes += (
                '<div style="display:flex;align-items:center;gap:16px;padding:15px 18px;margin-bottom:8px;">'
                '<span style="width:32px;height:32px;border-radius:50%;background:#22C55E;color:#fff;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">✓</span>'
                f'<span style="color:#dbe2ef;font-size:18px;">{nom}</span></div>'
            )
        else:
            lignes += (
                '<div style="display:flex;align-items:center;gap:16px;padding:15px 18px;margin-bottom:8px;">'
                f'<span style="width:32px;height:32px;border-radius:50%;border:1px solid #3a4566;color:#8a93ad;font-size:18px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{i+1}</span>'
                f'<span style="color:#8a93ad;font-size:18px;">{nom}</span></div>'
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
            col_ok, col_non = st.columns(2)
            col_ok.button(
                "✅ C'est bien ma société",
                type="primary", use_container_width=True,
                on_click=go, args=("onb_representant",),
            )
            col_non.button(
                "Ce n'est pas ma société",
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
            on_click=go, args=("onb_secteur",),
        )


# Étape « Secteur d'activité » (index 2) : non gérée dans le MVP, insérée après
# Dirigeant. Elle décale toutes les étapes suivantes d'un cran.
# Secteurs proposés à l'étape 3, avec une icône Material par secteur.
_SECTEURS = [
    ("saas", "Tech / SaaS", ":material/cloud:"),
    ("industrie", "Industrie / Manufacturing", ":material/factory:"),
    ("btob", "Services BtoB", ":material/handshake:"),
    ("perso", "Professions libérales / Indépendants", ":material/person:"),
    ("finance", "Finance / Conseil", ":material/account_balance:"),
    ("retail", "Commerce / Retail", ":material/storefront:"),
]


def choisir_secteur(nom):
    """Mémorise le secteur choisi (sélection unique), sans changer d'écran."""
    st.session_state.secteur = nom


def ecran_onb_secteur():
    """Étape 3 (Secteur d'activité) — ACTIVE : 6 secteurs en cartes cliquables,
    sélection unique, pictogramme SVG par secteur. Le nom reste dans la carte."""
    stepper_panel(2)
    st.button("← Retour", on_click=go, args=("onb_representant",))
    titre_section("Secteur d'activité",
                  "Sélectionnez le secteur principal de votre entreprise — il adapte la catégorisation.")
    # Chaque secteur = un vrai bouton (cliquable de façon fiable), stylé en carte.
    # Secteur choisi -> type "primary" (bordure bleue) ; les autres -> "secondary".
    st.markdown(
        "<style>"
        "[class*='st-key-sectbtn_'] button{min-height:94px !important;border-radius:14px !important;"
        "justify-content:flex-start !important;text-align:left !important;padding:14px 16px !important;}"
        "[class*='st-key-sectbtn_'] [data-testid='stBaseButton-secondary']{background:#0F1A2C !important;"
        "border:1px solid #1E2A3D !important;}"
        "[class*='st-key-sectbtn_'] [data-testid='stBaseButton-primary']{background:rgba(45,107,255,0.12) !important;"
        "border:2px solid #2D6BFF !important;}"
        "[class*='st-key-sectbtn_'] button p{white-space:normal !important;font-weight:600 !important;"
        "font-size:14px !important;line-height:1.25 !important;color:#fff !important;overflow-wrap:anywhere;}"
        "[class*='st-key-sectbtn_'] button [data-testid='stIconMaterial']{font-size:26px !important;"
        "color:#5A96FF !important;margin-right:8px;}"
        "</style>",
        unsafe_allow_html=True,
    )
    choisi = st.session_state.get("secteur")
    for debut in (0, 3):
        cols = st.columns(3, gap="medium")
        for j, (k, nom, ic) in enumerate(_SECTEURS[debut:debut + 3]):
            with cols[j]:
                with st.container(key=f"sectbtn_{k}"):
                    st.button(
                        nom, icon=ic, key=f"sb_{k}", use_container_width=True,
                        type="primary" if choisi == nom else "secondary",
                        on_click=choisir_secteur, args=(nom,),
                    )
    st.write("")
    _, cbtn = st.columns([4, 1])
    with cbtn:
        st.button("Continuer", type="primary", use_container_width=True,
                  on_click=go, args=("onb_investisseur",))


# Étapes (Bénéficiaires, Validation, Signature) : non gérées dans le MVP.
# Elles réutilisent toutes le même gabarit grisé `ecran_grise`.
def ecran_onb_ubo():
    ecran_grise(4, "Bénéficiaires effectifs", [], "onb_profil4", "onb_validation")


def ecran_onb_validation():
    ecran_grise(5, "Validation du dossier", [], "onb_ubo", "onb_signature")


def ecran_onb_signature():
    ecran_grise(6, "Signature", [], "onb_validation", "onb_banque")


# ==================================================================
# ONBOARDING — Type d'investisseur (ACTIF)
# ==================================================================
# L'étape « Profil » (index 2) est découpée en 4 sous-étapes qui s'enchaînent.
# Toutes affichent stepper_panel(2) : « Profil » reste l'étape active à gauche.
# Chaque question est présentée dans une CARTE encadrée (style A).

def _question(label, options, key):
    """Une question (radio) dans une carte à bordure bleue."""
    with st.container(key=f"qcard_{key}"):
        st.radio(label, options, index=None, key=key)

def _btn_continuer(cible):
    """Bouton « Continuer » petit, aligné à droite."""
    _, c = st.columns([3, 1])
    with c:
        st.button("Continuer", type="primary", use_container_width=True,
                  on_click=go, args=(cible,))

def _barre_progression(section, debut, fin, total=12):
    """Barre de progression basée sur le nombre de questions (façon typeform).
    Rendue dans une colonne [2, 0.5] identique à celle des questions, pour que la
    barre ait exactement la même largeur que les encarts de questions."""
    pct = int(fin / total * 100)
    libelle = f"Question {debut}" if debut == fin else f"Questions {debut} à {fin}"
    c, _ = st.columns([2, 0.5])
    with c:
        st.markdown(
            f"<div style='margin:0 0 22px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:12px;color:#7e89a8;margin-bottom:6px;'>"
            f"<span>Section {section} sur 4</span><span>{libelle} sur {total}</span></div>"
            f"<div style='height:6px;background:#1c2740;border-radius:3px;overflow:hidden;'>"
            f"<div style='height:100%;width:{pct}%;background:#2D6BFF;border-radius:3px;'></div></div></div>",
            unsafe_allow_html=True,
        )


def ecran_onb_investisseur():
    """Profil — Section 1/4 (écran 1/2) : visibilité & trésorerie dormante."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_secteur",))
    titre_section("LumenX et vous", "Où en est votre trésorerie aujourd'hui ?")
    _barre_progression(1, 1, 2)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Quelle visibilité avez-vous aujourd'hui sur votre trésorerie à venir "
            "(encaissements et décaissements futurs) ?",
            ["Moins de 3 mois", "3 à 6 mois", "6 mois à 1 an", "Plus d'1 an", "Je ne sais pas"],
            "p1_visibilite",
        )
        _question(
            "Quel est le montant moyen de votre trésorerie « dormante », celle qui reste "
            "sur le compte courant sans être utilisée d'un mois sur l'autre ?",
            ["Moins de 50 k€", "50 – 150 k€", "150 – 500 k€", "Plus de 500 k€", "Je ne sais pas"],
            "p1_dormante",
        )
        _btn_continuer("onb_profil1b")


def ecran_onb_profil1b():
    """Profil — Section 1/4 (écran 2/2) : coussin de sécurité."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_investisseur",))
    titre_section("LumenX et vous", "Où en est votre trésorerie aujourd'hui ?")
    _barre_progression(1, 3, 3)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Connaissez-vous votre « coussin de sécurité » minimum, le niveau de trésorerie "
            "(souvent exprimé en mois de charges fixes) sous lequel vous ne voulez jamais descendre ?",
            ["1 mois de charges fixes", "3 mois de charges fixes", "6 mois de charges fixes",
             "Je ne l'ai pas encore défini"],
            "p1_coussin",
        )
        _btn_continuer("onb_profil2a")


def ecran_onb_profil2a():
    """Profil — Section 2/4 (écran 1/3) : représentation & tolérance au risque."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil1b",))
    titre_section("LumenX et vous", "Quel investisseur êtes-vous ?")
    _barre_progression(2, 4, 5)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Quand vous pensez « placement de trésorerie », quel mot vous vient en premier ?",
            ["Sécurité", "Rendement", "Fiscalité", "Inflation", "Je ne sais pas"],
            "p2_mot",
        )
        _question(
            "Quelle est votre tolérance face à une baisse temporaire de la valeur de vos placements ?",
            [
                "Nulle — je veux récupérer chaque euro placé, même si le rendement est très faible.",
                "Faible — acceptable sur une petite partie de la trésorerie, si le potentiel de gain le justifie sur le long terme.",
                "Modérée — j'accepte les fluctuations de marché pour viser une meilleure performance à moyen ou long terme.",
            ],
            "p2_tolerance",
        )
        _btn_continuer("onb_profil2b")


def ecran_onb_profil2b():
    """Profil — Section 2/4 (écran 2/3) : expérience & satisfaction."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil2a",))
    titre_section("LumenX et vous", "Quel investisseur êtes-vous ?")
    _barre_progression(2, 6, 7)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Quelle est votre expérience des placements financiers ?",
            [
                "Débutant — je n'ai jamais réalisé de placement",
                "Intermédiaire — moins de 5 placements par an",
                "Confirmé — de 5 à 15 placements par an",
                "Expérimenté — plus de 15 placements par an",
            ],
            "p2_experience",
        )
        with st.container(key="qcard_satisf"):
            sans_objet = st.checkbox("Sans objet — je n'ai jamais placé", key="p2_satisf_na")
            st.slider(
                "Globalement, à quel point êtes-vous satisfait(e) de vos expériences de placement "
                "passées ? (0 = très insatisfait, 10 = très satisfait)",
                0, 10, 5, disabled=sans_objet, key="p2_satisf",
            )
        _btn_continuer("onb_profil2c")


def ecran_onb_profil2c():
    """Profil — Section 2/4 (écran 3/3) : blocage vs flexibilité."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil2b",))
    titre_section("LumenX et vous", "Quel investisseur êtes-vous ?")
    _barre_progression(2, 8, 8)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Préférez-vous bloquer des fonds sur une durée connue à l'avance pour un rendement "
            "garanti, ou garder de la flexibilité quitte à accepter un taux variable ?",
            [
                "Bloquer mes fonds pour un rendement garanti, mais plus faible",
                "Garder de la flexibilité pour un rendement potentiellement plus élevé, mais incertain",
                "Un équilibre entre les deux",
            ],
            "p2_blocage",
        )
        _btn_continuer("onb_profil3a")


def ecran_onb_profil3a():
    """Profil — Section 3/4 (écran 1/2) : liquidité & suivi."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil2c",))
    titre_section("LumenX et vous", "Sous quelles contraintes opérez-vous ?")
    _barre_progression(3, 9, 10)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "En cas de coup dur, sous quel délai maximum devez-vous pouvoir récupérer les fonds placés ?",
            ["Sous 48 h", "Sous 1 mois", "Sous 3 mois", "Sous 1 an", "Plus d'1 an"],
            "p3_delai",
        )
        _question(
            "Quelle part de votre temps souhaitez-vous consacrer au suivi de ces placements ?",
            ["Quotidiennement", "Chaque semaine", "Chaque mois", "Chaque trimestre",
             "Une fois par an ou moins"],
            "p3_temps",
        )
        _btn_continuer("onb_profil3b")


def ecran_onb_profil3b():
    """Profil — Section 3/4 (écran 2/2) : critères extra-financiers."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil3a",))
    titre_section("LumenX et vous", "Sous quelles contraintes opérez-vous ?")
    _barre_progression(3, 11, 11)
    col, _ = st.columns([2, 0.5])
    with col:
        _question(
            "Avez-vous des critères extra-financiers importants, par exemple investir dans des "
            "fonds responsables (ISR/ESG) ou soutenir l'économie locale ?",
            ["Oui, c'est important pour moi", "Non", "Je ne sais pas"],
            "p3_esg",
        )
        _btn_continuer("onb_profil4")


def ecran_onb_profil4():
    """Profil — Section 4/4 : objectifs (choix multiple)."""
    stepper_panel(3)
    st.button("← Retour", on_click=go, args=("onb_profil3b",))
    titre_section("LumenX et vous", "Quels sont vos objectifs financiers ?")
    _barre_progression(4, 12, 12)
    col, _ = st.columns([2, 0.5])
    with col:
        with st.container(key="qcard_objectifs"):
            st.caption("Plusieurs réponses possibles.")
            st.checkbox("Faire fructifier la trésorerie excédentaire de mon entreprise", key="p4_fructifier")
            st.checkbox("Avoir une visibilité globale sur la trésorerie de mon entreprise", key="p4_visibilite")
            st.checkbox("Avoir une compréhension fine des mouvements de trésorerie de mon entreprise", key="p4_comprehension")
        _btn_continuer("onb_ubo")


# ==================================================================
# ONBOARDING — 3 bis. Connexion bancaire fictive (ACTIF)
# ==================================================================
def ecran_onb_banque():
    """Étape 8 (Comptes) — ACTIVE mais fictive. Une tuile « + » de connexion
    remplace les anciens boutons : un clic charge un compte fictif -> dashboard."""
    stepper_panel(7)
    st.button("← Retour", on_click=go, args=("onb_signature",))
    titre_section("Vos comptes", "Contrat signé et documents validés — connectez vos comptes.")
    col, _ = st.columns([1.4, 2])
    with col:
        encadre("🧪 Pour le MVP, la connexion se fait sur un faux compte bancaire "
                "(données fictives).", "info")
        # Tuile dessinée en HTML + bouton transparent posé par-dessus (cliquable).
        st.markdown(
            "<style>"
            ".st-key-tuile_wrap{position:relative;max-width:320px;}"
            ".st-key-tuile_wrap .st-key-tuile_btn{position:absolute;inset:0;z-index:3;}"
            ".st-key-tuile_wrap .st-key-tuile_btn button{width:100% !important;height:100% !important;"
            "min-height:200px !important;background:transparent !important;border:none !important;"
            "box-shadow:none !important;opacity:0 !important;cursor:pointer !important;}"
            ".st-key-tuile_wrap:hover .tuile-visuel{background:rgba(45,107,255,0.06) !important;}"
            "</style>",
            unsafe_allow_html=True,
        )
        with st.container(key="tuile_wrap"):
            st.markdown(
                "<div class='tuile-visuel' style='border:1.5px dashed #2D6BFF;border-radius:16px;height:200px;"
                "display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;transition:background .15s;'>"
                "<svg width='54' height='54' viewBox='0 0 54 54'>"
                "<circle cx='27' cy='27' r='25' fill='none' stroke='#2D6BFF' stroke-width='2.5'/>"
                "<line x1='27' y1='16' x2='27' y2='38' stroke='#2D6BFF' stroke-width='3' stroke-linecap='round'/>"
                "<line x1='16' y1='27' x2='38' y2='27' stroke='#2D6BFF' stroke-width='3' stroke-linecap='round'/></svg>"
                "<div style='color:#dbe2ef;font-weight:600;font-size:15px;text-align:center;line-height:1.35;'>"
                "Connexion aux comptes<br>bancaires</div></div>",
                unsafe_allow_html=True,
            )
            with st.container(key="tuile_btn"):
                st.button("Connexion aux comptes bancaires", key="tuile_compte",
                          use_container_width=True,
                          on_click=set_profil, args=("Démo", "dashboard"))


# ==================================================================
# ESPACE CLIENT — barre latérale de navigation (commune à tous les écrans
# de l'espace connecté : tableau de bord, mon profil, documents…)
# ==================================================================
# Rubriques de la barre latérale : (écran cible, icône Material, libellé).
# cible = None -> rubrique "à venir" (ouvre un écran grisé).
# Deux groupes séparés par une ligne : principal puis personnel.
# Barre latérale groupée : (titre du groupe, [(écran cible, icône Material, libellé)]).
# cible = None -> rubrique "à venir" (ouvre l'écran grisé espace_avenir).
NAV_GROUPES = [
    ("PILOTAGE", [
        ("dashboard", ":material/dashboard:",     "Tableau de bord"),
        (None,        ":material/notifications:",  "Alertes"),
    ]),
    ("OPÉRATIONS", [
        (None,        ":material/account_balance:", "Comptes & connexions"),
        (None,        ":material/receipt_long:",    "Transactions"),
        (None,        ":material/trending_up:",     "Placements"),
    ]),
    ("DOSSIER", [
        ("espace_documents", ":material/description:", "Documents"),
        ("espace_profil",    ":material/business:",    "Entreprise & profil"),
    ]),
    ("ACCOMPAGNEMENT", [
        (None, ":material/support_agent:", "Aide & Support"),
        (None, ":material/auto_awesome:",  "(AI)nalytics"),
    ]),
    ("COMPTE", [
        (None, ":material/settings:", "Paramètres"),
        (None, ":material/payments:", "Facturation & abonnement"),
    ]),
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
        for gtitre, items in NAV_GROUPES:
            st.markdown(
                f"<div style='color:#6f7b95;font-size:10.5px;font-weight:700;"
                f"letter-spacing:1.4px;padding:14px 12px 3px;'>{gtitre}</div>",
                unsafe_allow_html=True,
            )
            for cible, icone, label in items:
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


def _barre(label, valeur, pct, couleur="#2D6BFF"):
    return (
        "<div style='display:flex;align-items:center;gap:10px;margin:12px 0;'>"
        f"<div style='width:170px;font-size:14px;color:#c2c6d2;'>{label}</div>"
        "<div style='flex:1;height:10px;background:#1c1c2a;border-radius:6px;'>"
        f"<div style='width:{pct}%;height:100%;background:{couleur};border-radius:6px;'></div></div>"
        f"<div style='width:95px;text-align:right;font-size:14px;color:#fff;font-weight:600;'>{valeur}</div></div>"
    )


# ---- Compte de résultat cash · Vue d'ensemble --------------------------------
# Charges fixes mensuelles et taux de charges variables : DÉRIVÉS du Charges Tracker,
# source unique. Le taux variable exprime un poids par rapport au CA — à ne pas
# confondre avec un taux de croissance.
_CRC_CH_FIX = 154.2   # k€/mois = lignes 'stable' + 'échéancier' du Charges Tracker
_CRC_TX_VAR = 0.135   # 13,5 % du CA = lignes 'variable' du Charges Tracker
# (mois, historique, CA récurrent, CA variable/aléatoire, charges aléatoires) en k€
_CRC_MOIS = [
    ("Jan", True, 182, 18, 4), ("Fév", True, 190, 20, 6), ("Mar", True, 176, 15, 3),
    ("Avr", True, 205, 25, 5), ("Mai", True, 198, 22, 4), ("Jun", True, 210, 30, 5),
    ("Jul", True, 208, 27, 6), ("Aoû", False, 212, 33, 5), ("Sep", False, 214, 36, 5),
    ("Oct", False, 218, 37, 6),
]
# La projection s'arrête à M+3, comme le Charges Tracker, le Revenu Tracker et le
# calendrier fiscal : une seule fenêtre projetée dans toute l'application.


def _crc_calc(m):
    """Dérive les agrégats d'un mois. Charges fixes et taux variable viennent du
    Charges Tracker (_CRC_CH_FIX / _CRC_TX_VAR), pas de valeurs en dur."""
    lbl, hist, ca_rec, ca_var, ch_alea = m
    ca = ca_rec + ca_var
    ch_var = round(_CRC_TX_VAR * ca)
    dec = _CRC_CH_FIX + ch_var + ch_alea
    return {"lbl": lbl, "hist": hist, "ca_rec": ca_rec, "ca_var": ca_var, "ca": ca,
            "ch_rec": _CRC_CH_FIX, "ch_var": ch_var, "ch_alea": ch_alea,
            "enc": ca, "dec": dec, "net": ca - dec}


def _crc_svg(rows, sel):
    """Bâtonnets encaissements (haut) / décaissements (bas), historique plein,
    projeté hachuré, mois sélectionné surligné."""
    axis, x0, step, bw = 175, 44, 58, 22
    maxv = max(max(r["enc"], r["dec"]) for r in rows)
    scale = 150.0 / maxv
    parts = []
    for i, r in enumerate(rows):
        x = x0 + i * step
        eh, dh = r["enc"] * scale, r["dec"] * scale
        w = 24 if i == sel else bw
        xo = x - 1 if i == sel else x
        if i == sel:
            sg = sr = ' stroke="#fff" stroke-width="1.5"'
        elif not r["hist"]:
            sg = ' stroke="#5DCAA5" stroke-dasharray="3 2"'
            sr = ' stroke="#E0604A" stroke-dasharray="3 2"'
        else:
            sg = sr = ""
        fg = "#5DCAA5" if r["hist"] else "url(#hG)"
        fr = "#E0604A" if r["hist"] else "url(#hR)"
        col = "#fff" if i == sel else ("#8a90a0" if r["hist"] else "#5a6478")
        fw = ' font-weight="700"' if i == sel else ""
        parts.append(
            f'<rect x="{xo}" y="{axis-eh:.0f}" width="{w}" height="{eh:.0f}" fill="{fg}"{sg}/>'
            f'<rect x="{xo}" y="{axis}" width="{w}" height="{dh:.0f}" fill="{fr}"{sr}/>'
            f'<text x="{x+bw//2}" y="306" text-anchor="middle" font-size="10" fill="{col}"{fw}>{r["lbl"]}</text>'
        )
    last_hist = max(i for i, r in enumerate(rows) if r["hist"])
    dvx = x0 + last_hist * step + bw // 2 + step // 2
    div = (f'<line x1="{dvx}" y1="20" x2="{dvx}" y2="290" stroke="#5a6478" stroke-dasharray="3 4"/>'
           f'<text x="{dvx+5}" y="32" font-size="10.5" fill="#8a90a0">aujourd&#39;hui</text>')
    # Échelle verticale en k€ : ligne 0 (axe) + repères 100 / 200 au-dessus (encaissements)
    # et en dessous (décaissements).
    grid = ('<text x="10" y="30" font-size="9.5" fill="#8a90a0">k€</text>'
            f'<text x="36" y="{axis+3}" text-anchor="end" font-size="9" fill="#8a90a0">0</text>')
    for gv in (100, 200):
        uy, dy = axis - gv * scale, axis + gv * scale
        grid += (f'<line x1="40" y1="{uy:.0f}" x2="740" y2="{uy:.0f}" stroke="#1c2740" stroke-dasharray="2 4"/>'
                 f'<line x1="40" y1="{dy:.0f}" x2="740" y2="{dy:.0f}" stroke="#1c2740" stroke-dasharray="2 4"/>'
                 f'<text x="36" y="{uy+3:.0f}" text-anchor="end" font-size="9" fill="#5a6478">{gv}</text>'
                 f'<text x="36" y="{dy+3:.0f}" text-anchor="end" font-size="9" fill="#5a6478">{gv}</text>')
    return (
        '<div style="background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;padding:16px 18px;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        '<div><div style="font-size:15px;font-weight:700;color:#e8ecf4;">Encaissements vs décaissements</div>'
        '<div style="font-size:11.5px;color:#8a90a0;">Mensuel · historique plein, projeté hachuré</div></div>'
        '<div style="font-size:11px;color:#c3ccdd;text-align:right;">'
        '<span style="color:#5DCAA5;">■</span> Encaissements&nbsp;&nbsp;'
        '<span style="color:#E0604A;">■</span> Décaissements</div></div>'
        '<svg viewBox="0 0 760 320" style="width:100%;height:auto;margin-top:6px;">'
        '<defs>'
        '<pattern id="hG" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
        '<rect width="6" height="6" fill="#0E1A16"/><line x1="0" y1="0" x2="0" y2="6" stroke="#5DCAA5" stroke-width="2"/></pattern>'
        '<pattern id="hR" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
        '<rect width="6" height="6" fill="#1A100E"/><line x1="0" y1="0" x2="0" y2="6" stroke="#E0604A" stroke-width="2"/></pattern>'
        '</defs>'
        + grid
        + f'<line x1="30" y1="{axis}" x2="740" y2="{axis}" stroke="#2b3a52"/>'
        + div + "".join(parts) + '</svg></div>'
    )


def _crc_detail_html(r):
    """Panneau de détail du mois sélectionné : montant (€) ET % du CA côte à côte."""
    ca = r["ca"]

    def pct(v):
        return f"{v/ca*100:.1f}".replace(".", ",") + " %"

    def ligne(lbl, v, coul, bold=False):
        tc = "#fff" if bold else "#c3ccdd"
        vc = "#fff"
        fw = "700" if bold else "400"
        return (
            '<div style="display:flex;align-items:center;padding:7px 0;border-top:1px solid #1E2A3D;">'
            '<span style="width:3px;height:15px;background:' + coul + ';display:inline-block;margin-right:10px;"></span>'
            '<span style="flex:1;color:' + tc + ';font-size:12.5px;font-weight:' + fw + ';">' + lbl + '</span>'
            '<span style="width:120px;text-align:right;color:#fff;font-size:12.5px;font-weight:' + fw + ';">' + str(v) + ' k€</span>'
            '<span style="width:100px;text-align:right;color:' + vc + ';font-size:12.5px;font-weight:' + fw + ';">' + pct(v) + '</span></div>'
        )
    entete = (
        '<div style="display:flex;align-items:center;padding:0 0 4px;">'
        '<span style="width:13px;"></span>'
        '<span style="flex:1;font-size:10.5px;font-weight:700;letter-spacing:0.5px;color:#7C8AA5;">POSTE</span>'
        '<span style="width:120px;text-align:right;font-size:10.5px;font-weight:700;letter-spacing:0.5px;color:#7C8AA5;">MONTANT</span>'
        '<span style="width:100px;text-align:right;font-size:10.5px;font-weight:700;letter-spacing:0.5px;color:#7C8AA5;">% DU CA</span></div>'
    )
    corps = (
        entete
        + ligne("CA récurrent", r["ca_rec"], "#5DCAA5")
        + ligne("CA variable / aléatoire", r["ca_var"], "#5DCAA5")
        + ligne("Charges récurrentes", r["ch_rec"], "#E0604A")
        + ligne("Charges variables", r["ch_var"], "#E0604A")
        + ligne("Charges aléatoires", r["ch_alea"], "#E0604A")
        + ligne("Solde net", r["net"], "#5DCAA5", bold=True)
    )
    return (
        '<div style="background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;padding:16px 18px;margin-top:12px;">'
        '<div style="font-size:14px;font-weight:700;color:#e8ecf4;margin-bottom:6px;">Détail — ' + r["lbl"] + ' 2026</div>'
        + corps + '</div>'
    )


def _crc_kpi_html(rows, sel):
    """Panneau KPI calculés pour le mois sélectionné : charges fixes cumulées 1/3/6 mois,
    ratio CA/charges fixes (3 mois glissants) et ARR (CA récurrent du mois annualisé)."""
    m = rows[sel]
    f1 = m["ch_rec"]
    lo = max(0, sel - 2)
    fen = rows[lo:sel + 1]
    ratio = (sum(r["ca"] for r in fen) / len(fen)) / f1
    arr = m["ca_rec"] * 12
    ratio_s = f"{ratio:.1f}".replace(".", ",")
    arr_s = f"{arr/1000.0:.2f}".replace(".", ",")

    def barre(lbl, val, w):
        return (
            '<div style="display:flex;align-items:center;margin-top:9px;">'
            '<span style="width:52px;color:#8a90a0;font-size:12px;">' + lbl + '</span>'
            '<span style="height:12px;width:' + str(w) + 'px;background:#E0604A;border-radius:3px;"></span>'
            '<span style="flex:1;text-align:right;color:#fff;font-size:12px;font-weight:700;">' + str(val) + ' k€</span></div>'
        )
    return (
        '<div style="background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;padding:16px 18px;margin-top:54px;">'
        '<div style="font-size:15px;font-weight:700;color:#e8ecf4;">Indicateurs clés</div>'
        '<div style="font-size:12px;color:#c3ccdd;margin-top:12px;">Charges fixes cumulées</div>'
        + barre("1 mois", f1, 25) + barre("3 mois", f1 * 3, 75) + barre("6 mois", f1 * 6, 150)
        + '<div style="border-top:1px solid #1E2A3D;margin-top:14px;padding-top:12px;font-size:12px;color:#c3ccdd;">CA / charges fixes · moy. 3 mois</div>'
        + '<div style="font-size:24px;font-weight:800;color:#5DCAA5;margin-top:2px;">' + ratio_s + '×</div>'
        + '<div style="font-size:11px;color:#8a90a0;">le CA couvre ' + ratio_s + '× les charges fixes</div>'
        + '<div style="border-top:1px solid #1E2A3D;margin-top:14px;padding-top:12px;font-size:12px;color:#c3ccdd;">ARR — CA récurrent annualisé</div>'
        + '<div style="font-size:24px;font-weight:800;color:#fff;margin-top:2px;">' + arr_s + ' M€</div>'
        + '</div>'
    )


def _report_flux():
    """Vue d'ensemble du Compte de résultat cash : bâtonnets encaissements/
    décaissements (historique + projeté), détail du mois au choix (€ ou % du CA)
    et KPI (charges fixes cumulées, CA/charges fixes, ARR)."""
    rows = [_crc_calc(m) for m in _CRC_MOIS]
    # Les mois projetés sont écrasés par les valeurs des trackers : une seule vérité.
    proj = _flux_projetes()
    i = 0
    for r in rows:
        if not r["hist"]:
            r.update(proj[i])
            i += 1
    labels = [r["lbl"] for r in rows]
    col_l, col_r = st.columns([2.3, 1], gap="medium")
    with col_l:
        sc1, _sc2 = st.columns([1.5, 3], vertical_alignment="center")
        sel_lbl = sc1.selectbox("Mois analysé", labels, index=5,
                                key="crc_mois", label_visibility="collapsed")
        sel = labels.index(sel_lbl)
        st.markdown(_crc_svg(rows, sel), unsafe_allow_html=True)
        st.markdown(_crc_detail_html(rows[sel]), unsafe_allow_html=True)
    with col_r:
        st.markdown(_crc_kpi_html(rows, sel), unsafe_allow_html=True)


# ---- Charges Tracker : vue mensuelle (3 mois réalisés + 3 mois projetés) ----------
# Fenêtre temporelle commune à toute l'application, ancrée sur le dernier relevé
# bancaire (31/07/2026). Écran symétrique du Revenu Tracker.
_CT_MOIS_REAL = [(2026, 5, "Mai"), (2026, 6, "Juin"), (2026, 7, "Juil")]
_CT_MOIS_PROJ = [(2026, 8, "Août"), (2026, 9, "Sept"), (2026, 10, "Oct")]

# profil -> (libellé affiché, compte dans les CHARGES FIXES)
# Les charges fixes = 'stable' + 'échéancier'. C'est le dénominateur de la
# couverture affichée dans le Revenu Tracker.
_CT_PROFILS = {
    "stable":     ("récurrent · stable", True),
    "échéancier": ("récurrent · échéancier", True),
    "variable":   ("récurrent · variable", False),
    "ponctuel":   ("ponctuel", False),
}

# (id, Level 1, Level 2, profil, inclus dans le prévisionnel, réalisés k€, justification)
# reals = None -> valeurs dérivées du calendrier fiscal (ligne impôts).
_CT_CATS = [
    ("rem", "Exploitation", "Rémunérations", "stable", True, (74.5, 75.0, 75.5),
     "Masse salariale stable sur 12 mois, écart ±1 % — reconduite à l'identique"),
    ("soc", "Exploitation", "Charges sociales", "stable", True, (31.5, 31.7, 31.9),
     "Échéancier légal mensuel, indexé sur la masse salariale — dates connues"),
    ("ach", "Exploitation", "Achats liés à l'activité", "variable", True, (25.8, 28.1, 26.2),
     "Indexé sur le CA : 11,0 % observé sur 12 mois — suit la projection de revenus"),
    ("loc", "Exploitation", "Locaux & énergie", "stable", True, (15.0, 15.0, 15.0),
     "Loyer contractuel + énergie lissée — pas d'indexation avant janvier"),
    ("abo", "Exploitation", "Assurances & abonnements", "stable", True, (8.0, 8.0, 8.0),
     "Prélèvements fixes identiques sur 12 mois"),
    ("hon", "Exploitation", "Honoraires", "stable", True, (5.0, 5.0, 5.0),
     "Expert-comptable et conseil, forfait mensuel"),
    ("ace", "Exploitation", "Autres charges externes", "variable", True, (4.2, 5.1, 4.5),
     "Moyenne 3 mois — dispersion faible, pas d'indexation retenue"),
    ("dep", "Exploitation", "Déplacements & véhicules", "ponctuel", False, (2.1, 5.4, 2.4),
     "Aucune périodicité détectée — exclu de la projection, réintégrable d'un clic"),
    ("avt", "Exploitation", "Avantages sociaux", "stable", True, (2.5, 2.5, 2.5),
     "Tickets restaurant et mutuelle, montant fixe par salarié"),
    ("imp", "Impôts & taxes", "Impôts & taxes (IS, CFE, CVAE)", "échéancier", True, None,
     "Montants et dates issus du calendrier fiscal — acomptes trimestriels, non lissés"),
    ("emp", "Financement", "Emprunts (échéances)", "stable", True, (7.0, 7.0, 7.0),
     "Tableau d'amortissement contractuel — échéance fixe jusqu'en 2029"),
    ("fin", "Financement", "Résultat financier (agios)", "variable", True, (0.9, 1.1, 1.0),
     "Agios et frais bancaires — moyenne 3 mois"),
    ("exc", "Exceptionnel", "Charges exceptionnelles", "ponctuel", False, (0.0, 25.0, 0.0),
     "Événement isolé en juin — imprévisible, exclu de la projection"),
]


def _ct_k(v):
    """Formate un montant en k€ à une décimale, séparateurs français."""
    return f"{v:,.1f}".replace(",", " ").replace(".", ",")


def _ct_impots_mensuels():
    """IS et CFE par mois, DÉRIVÉS du calendrier fiscal : source unique de vérité.
    La TVA est volontairement exclue (neutre au compte de résultat)."""
    par_mois = {}
    for _rid, d, typ, _lib, mnt, _real in _FISC_SEED:
        if typ in ("IS", "CFE"):
            par_mois[(d.year, d.month)] = par_mois.get((d.year, d.month), 0.0) + mnt / 1000.0
    return par_mois


def _ct_reals(cat):
    """Les 3 mois réalisés d'une catégorie."""
    if cat[5] is None:
        pm = _ct_impots_mensuels()
        return [pm.get((y, m), 0.0) for y, m, _ in _CT_MOIS_REAL]
    return list(cat[5])


def _ct_init():
    """Sème l'état des projections : mode de réglage et valeurs par défaut.
    Les postes exclus du prévisionnel démarrent à 0 mais restent modifiables :
    si le client saisit un montant, c'est le sien qui prime.

    Appelé à CHAQUE rendu, sans drapeau : Streamlit détruit l'état des champs qui ne
    sont pas affichés, et les trackers vivent dans des sous-onglets exclusifs. Un
    semis unique laisserait donc les champs retomber à 0 au changement de pilule."""
    for cat in _CT_CATS:
        cid, profil, inclus = cat[0], cat[3], cat[4]
        if profil == "échéancier":
            continue  # piloté par le calendrier fiscal, pas de saisie
        defaut = round(sum(_ct_reals(cat)) / 3.0, 1) if inclus else 0.0
        st.session_state.setdefault(f"ct_mode_{cid}", "€")
        st.session_state.setdefault(f"ct_g_{cid}", 0.0)
        for k in range(3):
            st.session_state.setdefault(f"ct_p{k}_{cid}", defaut)


def _ct_projections(cat, base):
    """Les 3 mois projetés. En mode %, le taux de CROISSANCE est appliqué au dernier
    chiffre de proche en proche (base×(1+g), puis ×(1+g)...). À ne pas confondre avec
    le % de charges variables, qui exprime un poids par rapport au CA."""
    cid, profil, inclus = cat[0], cat[3], cat[4]
    if profil == "échéancier":
        pm = _ct_impots_mensuels()
        return [pm.get((y, m), 0.0) for y, m, _ in _CT_MOIS_PROJ]
    # Un poste exclu du prévisionnel part de 0, pas de sa moyenne observée.
    defaut = base if inclus else 0.0
    if st.session_state.get(f"ct_mode_{cid}", "€") == "%":
        g = st.session_state.get(f"ct_g_{cid}", 0.0) / 100.0
        vals, v = [], defaut
        for _ in range(3):
            v = v * (1.0 + g)
            vals.append(round(v, 1))
        return vals
    return [round(st.session_state.get(f"ct_p{k}_{cid}", defaut), 1) for k in range(3)]


def _crc_charges_tracker():
    """Charges Tracker : 3 mois réalisés + 3 mois projetés par catégorie de taxonomie.
    La ligne 'Charges fixes du mois' alimente la couverture du Revenu Tracker."""
    _ct_init()
    st.markdown(
        "<style>"
        ".st-key-ct_card{background:#0E1626;border:1px solid #1E2A3D;border-radius:16px;padding:14px 18px;margin-top:12px;}"
        "[class*='st-key-ct_p'] button[data-testid='stNumberInputStepUp'],"
        "[class*='st-key-ct_p'] button[data-testid='stNumberInputStepDown'],"
        "[class*='st-key-ct_g_'] button[data-testid='stNumberInputStepUp'],"
        "[class*='st-key-ct_g_'] button[data-testid='stNumberInputStepDown']{display:none !important;}"
        "[class*='st-key-ct_p'] input,[class*='st-key-ct_g_'] input{text-align:right !important;font-size:12px !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    rat = [2.4, 1.2, 0.6, 0.55, 0.55, 0.55, 0.7, 1.1, 0.95, 0.95, 0.95]
    ent = "font-size:9.5px;font-weight:700;letter-spacing:0.5px;color:#5a6478;"
    gris = "color:#c3ccdd;font-size:11.5px;text-align:right;"

    # Agrégats par mois : total, et charges fixes (stable + échéancier)
    tot_r = [0.0, 0.0, 0.0]
    tot_p = [0.0, 0.0, 0.0]
    fix_r = [0.0, 0.0, 0.0]
    fix_p = [0.0, 0.0, 0.0]
    for cat in _CT_CATS:
        reals = _ct_reals(cat)
        base = round(sum(reals) / 3.0, 1)
        projs = _ct_projections(cat, base)
        est_fixe = _CT_PROFILS[cat[3]][1]
        for k in range(3):
            tot_r[k] += reals[k]
            if est_fixe:
                fix_r[k] += reals[k]
            if projs:
                tot_p[k] += projs[k]
                if est_fixe:
                    fix_p[k] += projs[k]

    st.markdown(
        '<div style="background:rgba(45,107,255,0.08);border-radius:8px;padding:9px 14px;'
        'font-size:12px;color:#9fc0ff;">Dernier relevé bancaire : 31/07/2026 — 3 mois réalisés '
        '+ 3 mois projetés · montants en k€ · le % est un taux de <b>croissance</b> appliqué au mois précédent</div>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;">'
        + _ct_tuile("Charges fixes · août 2026", _ct_k(fix_p[0]) + " k€", "#fff")
        + _ct_tuile("Charges variables · août 2026", _ct_k(tot_p[0] - fix_p[0]) + " k€", "#fff")
        + _ct_tuile("Ponctuel · exclu du prévisionnel",
                    _ct_k(sum(sum(_ct_reals(c)) / 3.0 for c in _CT_CATS if not c[4])) + " k€", "#8a93ad")
        + _ct_tuile("Total projeté · août 2026", _ct_k(tot_p[0]) + " k€", "#E0604A")
        + '</div>', unsafe_allow_html=True)

    with st.container(key="ct_card"):
        h = st.columns(rat)
        for i, lbl in enumerate(["POSTE", "PROFIL", "PRÉV."]):
            h[i].markdown(f"<div style='{ent}'>{lbl}</div>", unsafe_allow_html=True)
        for i, (_y, _m, nom) in enumerate(_CT_MOIS_REAL):
            h[3 + i].markdown(f"<div style='{ent}text-align:right;'>{nom.upper()}</div>", unsafe_allow_html=True)
        h[6].markdown(f"<div style='{ent}text-align:right;'>BASE</div>", unsafe_allow_html=True)
        # aligné à gauche comme les pastilles €/% qui se placent en début de colonne
        h[7].markdown(f"<div style='{ent}'>MODE</div>", unsafe_allow_html=True)
        for i, (_y, _m, nom) in enumerate(_CT_MOIS_PROJ):
            h[8 + i].markdown(f"<div style='{ent}text-align:center;'>{nom.upper()}</div>", unsafe_allow_html=True)
        st.markdown("<div style='border-top:1px solid #1E2A3D;'></div>", unsafe_allow_html=True)

        niveau = None
        for cat in _CT_CATS:
            # justif : conservé dans le modèle, destiné au futur détail au clic (ⓘ)
            cid, l1, lib, profil, inclus, _r, _justif = cat
            if l1 != niveau:
                niveau = l1
                st.markdown("<div style='font-size:11.5px;font-weight:700;letter-spacing:0.5px;"
                            "color:#c3ccdd;margin:10px 0 2px;'>" + l1.upper() + "</div>",
                            unsafe_allow_html=True)
            reals = _ct_reals(cat)
            base = round(sum(reals) / 3.0, 1)
            projs = _ct_projections(cat, base)
            c = st.columns(rat, vertical_alignment="center")
            coul_lib = "#fff" if inclus else "#c3ccdd"
            c[0].markdown(f"<div style='color:{coul_lib};font-size:12px;'>{lib}</div>", unsafe_allow_html=True)
            c[1].markdown(f"<div style='color:#8a90a0;font-size:10.5px;'>{_CT_PROFILS[profil][0]}</div>",
                          unsafe_allow_html=True)
            c[2].markdown("<div style='font-size:10.5px;color:"
                          + ("#5DCAA5;'>inclus" if inclus else "#8a93ad;'>exclu") + "</div>",
                          unsafe_allow_html=True)
            for k in range(3):
                txt = "—" if (profil == "échéancier" and reals[k] == 0) else _ct_k(reals[k])
                c[3 + k].markdown(f"<div style='{gris}'>{txt}</div>", unsafe_allow_html=True)
            c[6].markdown(f"<div style='color:#fff;font-size:11.5px;text-align:right;font-weight:600;'>"
                          f"{_ct_k(base)}</div>", unsafe_allow_html=True)
            # Mode de réglage
            if profil == "échéancier":
                c[7].markdown("<div style='font-size:10px;color:#E0A04A;text-align:center;'>calendrier</div>",
                              unsafe_allow_html=True)
            else:
                with c[7]:
                    mode = st.pills("mode", ["€", "%"], key=f"ct_mode_{cid}",
                                    label_visibility="collapsed")
                    if not mode:
                        mode = st.session_state.get(f"ct_mode_{cid}", "€") or "€"
                    if mode == "%":
                        st.number_input("taux", step=0.5, key=f"ct_g_{cid}",
                                        label_visibility="collapsed")
            # Projections
            for k in range(3):
                if profil == "échéancier":
                    coul = "#E0A04A" if projs[k] else "#5a6478"
                    c[8 + k].markdown(f"<div style='text-align:right;color:{coul};font-size:11.5px;"
                                      f"font-weight:600;'>{_ct_k(projs[k])}</div>", unsafe_allow_html=True)
                elif st.session_state.get(f"ct_mode_{cid}", "€") == "%":
                    c[8 + k].markdown(f"<div style='text-align:right;color:#9fc0ff;font-size:11.5px;"
                                      f"font-weight:600;'>{_ct_k(projs[k])}</div>", unsafe_allow_html=True)
                else:
                    c[8 + k].number_input("p", step=0.5, key=f"ct_p{k}_{cid}",
                                          label_visibility="collapsed")

        # Totaux
        st.markdown("<div style='border-top:1px solid #1E2A3D;margin-top:6px;'></div>",
                    unsafe_allow_html=True)
        t = st.columns(rat, vertical_alignment="center")
        t[0].markdown("<div style='font-size:11.5px;font-weight:700;color:#c3ccdd;'>Charges fixes du mois</div>",
                      unsafe_allow_html=True)
        for k in range(3):
            t[3 + k].markdown(f"<div style='{gris}font-weight:700;'>{_ct_k(fix_r[k])}</div>",
                              unsafe_allow_html=True)
        for k in range(3):
            coul = "#E0A04A" if fix_p[k] > fix_p[(k + 1) % 3] or fix_p[k] > 150 else "#c3ccdd"
            t[8 + k].markdown(f"<div style='text-align:right;color:{coul};font-size:11.5px;"
                              f"font-weight:700;'>{_ct_k(fix_p[k])}</div>", unsafe_allow_html=True)
        g = st.columns(rat, vertical_alignment="center")
        g[0].markdown("<div style='font-size:13px;font-weight:700;color:#fff;'>Total des charges</div>",
                      unsafe_allow_html=True)
        for k in range(3):
            g[3 + k].markdown(f"<div style='{gris}font-weight:700;'>{_ct_k(tot_r[k])}</div>",
                              unsafe_allow_html=True)
        for k in range(3):
            g[8 + k].markdown(f"<div style='text-align:right;color:#E0604A;font-size:12.5px;"
                              f"font-weight:800;'>{_ct_k(tot_p[k])}</div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='background:rgba(224,160,74,0.06);border-radius:8px;padding:10px 14px;"
        "margin-top:12px;font-size:11px;color:#f0c489;'>La ligne « Charges fixes du mois » est le "
        "dénominateur de la couverture du Revenu Tracker. Elle n'est pas plate : les mois portant un "
        "acompte d'IS pèsent plus lourd. Montants et dates des impôts proviennent du calendrier fiscal.</div>"
        "<div style='height:80px;'></div>", unsafe_allow_html=True)


def _ct_tuile(titre, valeur, coul, suffixe=""):
    suf = ('<span style="font-size:12px;color:#5a6478;margin-left:8px;">' + suffixe + '</span>') if suffixe else ''
    return ('<div style="background:#111B2C;border:1px solid #1E2A3D;border-radius:12px;padding:12px 16px;">'
            '<div style="font-size:12px;color:#8a90a0;">' + titre + '</div>'
            '<div style="font-size:22px;font-weight:800;color:' + coul + ';margin-top:4px;">' + valeur + suf + '</div></div>')


def _flux_projetes():
    """Encaissements et décaissements projetés (M+1..M+3), DÉRIVÉS des trackers.
    La Vue d'ensemble ne doit pas raconter autre chose que le Revenu Tracker et le
    Charges Tracker : ses bâtonnets projetés viennent d'ici, pas d'un jeu figé."""
    _rt_init()
    _ct_init()
    ca_rec, ca_pon = [0.0] * 3, [0.0] * 3
    for cid, _s, _l, profil, reals in _RT_CATS:
        base = round(sum(reals) / 3.0, 1)
        pr = _rt_projections(cid, profil, base)
        cible = ca_rec if _RT_PROFILS[profil][1] else ca_pon
        for k in range(3):
            cible[k] += pr[k]
    ch_fix, ch_var, ch_pon = [0.0] * 3, [0.0] * 3, [0.0] * 3
    for cat in _CT_CATS:
        base = round(sum(_ct_reals(cat)) / 3.0, 1)
        pr = _ct_projections(cat, base)
        cible = (ch_fix if _CT_PROFILS[cat[3]][1]
                 else (ch_var if cat[3] == "variable" else ch_pon))
        for k in range(3):
            cible[k] += pr[k]
    return [{"ca_rec": round(ca_rec[k]), "ca_var": round(ca_pon[k]),
             "ca": round(ca_rec[k] + ca_pon[k]),
             "ch_rec": round(ch_fix[k]), "ch_var": round(ch_var[k]),
             "ch_alea": round(ch_pon[k]),
             "enc": round(ca_rec[k] + ca_pon[k]),
             "dec": round(ch_fix[k] + ch_var[k] + ch_pon[k]),
             "net": round(ca_rec[k] + ca_pon[k] - ch_fix[k] - ch_var[k] - ch_pon[k])}
            for k in range(3)]


def _charges_fixes_par_mois():
    """Charges fixes projetées sur M+1..M+3, DÉRIVÉES du Charges Tracker.
    C'est le dénominateur de la couverture affichée dans le Revenu Tracker : si une
    charge bouge là-bas, la couverture bouge ici."""
    fix = [0.0, 0.0, 0.0]
    for cat in _CT_CATS:
        if not _CT_PROFILS[cat[3]][1]:
            continue
        base = round(sum(_ct_reals(cat)) / 3.0, 1)
        projs = _ct_projections(cat, base)
        for k in range(3):
            fix[k] += projs[k]
    return fix


# ---- Revenu Tracker : vue mensuelle, symétrique du Charges Tracker ---------------
# profil -> (libellé affiché, compte dans le CA RÉCURRENT)
_RT_PROFILS = {
    "stable":   ("récurrent · stable", True),
    "variable": ("récurrent · variable", True),
    "ponctuel": ("ponctuel", False),
}
# (id, section, libellé, profil, réalisés k€)
_RT_CATS = [
    ("gc",   "B2B — contrats", "Grands comptes", "stable", (84.0, 84.0, 84.0)),
    ("b2b",  "B2B — contrats", "Autres comptes B2B", "stable", (31.2, 32.0, 31.5)),
    ("abo",  "Abonnements", "Abonnements", "variable", (20.8, 21.1, 21.4)),
    ("soc",  "Retail & vente directe", "Socle d'activité", "stable", (42.0, 43.5, 42.8)),
    ("pva",  "Retail & vente directe", "Part variable d'activité", "variable", (18.0, 26.5, 21.2)),
    ("pla",  "Vente en ligne & plateformes", "Reversements plateformes", "variable", (11.2, 12.4, 12.4)),
    ("vpo",  "Ponctuel & projets", "Ventes ponctuelles", "ponctuel", (15.0, 42.0, 27.0)),
    ("sub",  "Autres revenus", "Subventions & aides", "ponctuel", (0.0, 0.0, 0.0)),
    ("rfi",  "Autres revenus", "Revenus financiers", "stable", (1.1, 1.2, 1.3)),
    ("ref",  "Autres revenus", "Refacturations & remboursements", "ponctuel", (1.9, 4.2, 2.3)),
]


def _rt_init():
    """Sème les projections. Comme pour les charges, un poste ponctuel démarre à 0
    mais reste modifiable : on ne projette pas un encaissement sans périodicité.
    Appelé à chaque rendu (cf. _ct_init) : sans cela les champs retombent à 0 quand
    on quitte le sous-onglet."""
    for cid, _sec, _lib, profil, reals in _RT_CATS:
        defaut = round(sum(reals) / 3.0, 1) if profil != "ponctuel" else 0.0
        st.session_state.setdefault(f"rt_mode_{cid}", "€")
        st.session_state.setdefault(f"rt_g_{cid}", 0.0)
        for k in range(3):
            st.session_state.setdefault(f"rt_p{k}_{cid}", defaut)


def _rt_projections(cid, profil, base):
    """Projections M+1..M+3. En mode %, le taux de croissance s'applique au mois
    précédent de proche en proche."""
    defaut = base if profil != "ponctuel" else 0.0
    if st.session_state.get(f"rt_mode_{cid}", "€") == "%":
        g = st.session_state.get(f"rt_g_{cid}", 0.0) / 100.0
        vals, v = [], defaut
        for _ in range(3):
            v = v * (1.0 + g)
            vals.append(round(v, 1))
        return vals
    return [round(st.session_state.get(f"rt_p{k}_{cid}", defaut), 1) for k in range(3)]


def _crc_revenu_tracker():
    """Revenu Tracker : 3 mois réalisés + 3 mois projetés, par nature de rentrée.
    La couverture des charges fixes est calculée mois par mois, jamais en moyenne."""
    _rt_init()
    _ct_init()  # nécessaire : la couverture dépend des projections de charges
    st.markdown(
        "<style>"
        ".st-key-rt_card{background:#0E1626;border:1px solid #1E2A3D;border-radius:16px;padding:14px 18px;margin-top:12px;}"
        "[class*='st-key-rt_p'] button[data-testid='stNumberInputStepUp'],"
        "[class*='st-key-rt_p'] button[data-testid='stNumberInputStepDown'],"
        "[class*='st-key-rt_g_'] button[data-testid='stNumberInputStepUp'],"
        "[class*='st-key-rt_g_'] button[data-testid='stNumberInputStepDown']{display:none !important;}"
        "[class*='st-key-rt_p'] input,[class*='st-key-rt_g_'] input{text-align:right !important;font-size:12px !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    rat = [2.6, 1.4, 0.55, 0.55, 0.55, 0.7, 1.1, 0.95, 0.95, 0.95]
    ent = "font-size:9.5px;font-weight:700;letter-spacing:0.5px;color:#5a6478;"
    gris = "color:#c3ccdd;font-size:11.5px;text-align:right;"

    rec_r, rec_p = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    tot_r, tot_p = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for cid, _sec, _lib, profil, reals in _RT_CATS:
        base = round(sum(reals) / 3.0, 1)
        projs = _rt_projections(cid, profil, base)
        for k in range(3):
            tot_r[k] += reals[k]
            tot_p[k] += projs[k]
            if _RT_PROFILS[profil][1]:
                rec_r[k] += reals[k]
                rec_p[k] += projs[k]
    fixes = _charges_fixes_par_mois()
    couv = [(rec_p[k] / fixes[k] * 100.0) if fixes[k] else 0.0 for k in range(3)]

    st.markdown(
        '<div style="background:rgba(45,107,255,0.08);border-radius:8px;padding:9px 14px;'
        'font-size:12px;color:#9fc0ff;">M0 = juillet 2026, dernier mois clôturé · réalisés M-2 à M0, '
        'projetés M+1 à M+3 · montants en k€ · le % est un taux de <b>croissance</b> appliqué au mois précédent</div>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;">'
        + _ct_tuile("CA récurrent · M+1", _ct_k(rec_p[0]) + " k€", "#5DCAA5")
        + _ct_tuile("Ponctuel observé · moy. réalisée",
                    _ct_k(sum(sum(c[4]) / 3.0 for c in _RT_CATS if c[3] == "ponctuel")) + " k€", "#8a93ad")
        + _ct_tuile("Total projeté · M+1", _ct_k(tot_p[0]) + " k€", "#fff")
        + _ct_tuile("Couverture charges fixes · M+1", f"{couv[0]:.0f} %".replace(".", ","),
                    "#5DCAA5" if couv[0] >= 100 else "#E0604A")
        + '</div>', unsafe_allow_html=True)

    with st.container(key="rt_card"):
        h = st.columns(rat)
        h[0].markdown(f"<div style='{ent}'>POSTE</div>", unsafe_allow_html=True)
        h[1].markdown(f"<div style='{ent}'>PROFIL</div>", unsafe_allow_html=True)
        for i, (_y, _m, nom) in enumerate(_CT_MOIS_REAL):
            h[2 + i].markdown(f"<div style='{ent}text-align:right;'>{nom.upper()}</div>", unsafe_allow_html=True)
        h[5].markdown(f"<div style='{ent}text-align:right;'>BASE</div>", unsafe_allow_html=True)
        h[6].markdown(f"<div style='{ent}'>MODE</div>", unsafe_allow_html=True)
        for i, (_y, _m, nom) in enumerate(_CT_MOIS_PROJ):
            h[7 + i].markdown(f"<div style='{ent}text-align:center;'>{nom.upper()}</div>", unsafe_allow_html=True)
        st.markdown("<div style='border-top:1px solid #1E2A3D;'></div>", unsafe_allow_html=True)

        section = None
        for cid, sec, lib, profil, reals in _RT_CATS:
            if sec != section:
                section = sec
                st.markdown("<div style='font-size:11.5px;font-weight:700;letter-spacing:0.5px;"
                            "color:#c3ccdd;margin:10px 0 2px;'>" + sec.upper() + "</div>",
                            unsafe_allow_html=True)
            base = round(sum(reals) / 3.0, 1)
            projs = _rt_projections(cid, profil, base)
            c = st.columns(rat, vertical_alignment="center")
            c[0].markdown(f"<div style='color:#fff;font-size:12px;'>{lib}</div>", unsafe_allow_html=True)
            c[1].markdown(f"<div style='color:#8a90a0;font-size:10.5px;'>{_RT_PROFILS[profil][0]}</div>",
                          unsafe_allow_html=True)
            for k in range(3):
                c[2 + k].markdown(f"<div style='{gris}'>{_ct_k(reals[k])}</div>", unsafe_allow_html=True)
            c[5].markdown(f"<div style='color:#fff;font-size:11.5px;text-align:right;font-weight:600;'>"
                          f"{_ct_k(base)}</div>", unsafe_allow_html=True)
            with c[6]:
                mode = st.pills("mode", ["€", "%"], key=f"rt_mode_{cid}", label_visibility="collapsed")
                if not mode:
                    mode = st.session_state.get(f"rt_mode_{cid}", "€") or "€"
                if mode == "%":
                    st.number_input("taux", step=0.5, key=f"rt_g_{cid}", label_visibility="collapsed")
            for k in range(3):
                if st.session_state.get(f"rt_mode_{cid}", "€") == "%":
                    c[7 + k].markdown(f"<div style='text-align:right;color:#9fc0ff;font-size:11.5px;"
                                      f"font-weight:600;'>{_ct_k(projs[k])}</div>", unsafe_allow_html=True)
                else:
                    c[7 + k].number_input("p", step=0.5, key=f"rt_p{k}_{cid}",
                                          label_visibility="collapsed")

        st.markdown("<div style='border-top:1px solid #1E2A3D;margin-top:6px;'></div>",
                    unsafe_allow_html=True)
        for titre, vr, vp, coul in (("CA récurrent", rec_r, rec_p, "#5DCAA5"),
                                    ("Total des revenus", tot_r, tot_p, "#fff")):
            t = st.columns(rat, vertical_alignment="center")
            t[0].markdown(f"<div style='font-size:12px;font-weight:700;color:{coul};'>{titre}</div>",
                          unsafe_allow_html=True)
            for k in range(3):
                t[2 + k].markdown(f"<div style='{gris}font-weight:700;'>{_ct_k(vr[k])}</div>",
                                  unsafe_allow_html=True)
            for k in range(3):
                t[7 + k].markdown(f"<div style='text-align:right;color:{coul};font-size:11.5px;"
                                  f"font-weight:700;'>{_ct_k(vp[k])}</div>", unsafe_allow_html=True)
        # Couverture calculée mois par mois : une moyenne masquerait les creux
        cv = st.columns(rat, vertical_alignment="center")
        cv[0].markdown("<div style='font-size:12px;font-weight:700;color:#c3ccdd;'>"
                       "Couverture des charges fixes</div>", unsafe_allow_html=True)
        for k in range(3):
            coul = "#5DCAA5" if couv[k] >= 130 else ("#E0A04A" if couv[k] >= 100 else "#E0604A")
            cv[7 + k].markdown(f"<div style='text-align:right;color:{coul};font-size:11.5px;"
                               f"font-weight:700;'>{couv[k]:.0f} %</div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='background:rgba(93,202,165,0.06);border-radius:8px;padding:10px 14px;"
        "margin-top:12px;font-size:11px;color:#8fe0c4;'>La couverture divise le CA récurrent projeté "
        "par les charges fixes du même mois, issues du Charges Tracker. Elle est calculée mois par mois : "
        "une moyenne masquerait les mois portant un acompte d'impôt.</div>"
        "<div style='height:80px;'></div>", unsafe_allow_html=True)


# ---- Fiscalité Tracker : paramètres + calendrier des échéances --------------------
# type d'échéance -> (fond pastille, bordure, texte)
_FISC_TYPES = {
    "TVA":   ("rgba(45,107,255,0.18)",  "#2D6BFF", "#9fc0ff"),
    "IS":    ("rgba(127,119,221,0.18)", "#7F77DD", "#b9b3f0"),
    "CFE":   ("rgba(224,160,74,0.18)",  "#E0A04A", "#f0c489"),
    "Autre": ("rgba(107,118,136,0.18)", "#6b7688", "#aab3c7"),
}
# Calendrier calculé depuis le régime (réel normal mensuel, clôture 31/12).
# Fenêtre commune à toute l'application : 3 mois réalisés + 3 mois projetés minimum,
# ancrée sur le dernier relevé bancaire (31/07/2026).
# (id, date, type, libellé, montant €, réalisé)
_FISC_SEED = [
    ("r1", dt.date(2026, 5, 19),  "TVA", "Déclaration TVA — avril",      21000, True),
    ("r2", dt.date(2026, 6, 15),  "IS",  "Acompte IS n°2",               22000, True),
    ("r3", dt.date(2026, 6, 19),  "TVA", "Déclaration TVA — mai",        22000, True),
    ("r4", dt.date(2026, 7, 21),  "TVA", "Déclaration TVA — juin",       24000, True),
    ("f1", dt.date(2026, 8, 19),  "TVA", "Déclaration TVA — juillet",    23000, False),
    ("f2", dt.date(2026, 9, 15),  "IS",  "Acompte IS n°3",               22000, False),
    ("f3", dt.date(2026, 9, 21),  "TVA", "Déclaration TVA — août",       24000, False),
    ("f4", dt.date(2026, 10, 19), "TVA", "Déclaration TVA — septembre",  25000, False),
    ("f5", dt.date(2026, 11, 20), "TVA", "Déclaration TVA — octobre",    25000, False),
    ("f6", dt.date(2026, 12, 15), "IS",  "Acompte IS n°4",               24000, False),
    ("f7", dt.date(2026, 12, 15), "CFE", "Solde CFE",                     8000, False),
    ("f8", dt.date(2026, 12, 21), "TVA", "Déclaration TVA — novembre",   26000, False),
    ("f9", dt.date(2027, 5, 15),  "IS",  "Solde IS — exercice 2026",     12000, False),
]


def _fisc_init():
    """Sème le calendrier une seule fois. Les échéances réalisées sont des faits
    (pas de widget, pas d'exclusion possible) ; les échéances à venir vivent dans
    les clés des widgets, ce qui permet de détecter les ajustements."""
    if "fisc_rows" in st.session_state:
        return
    rows = []
    for rid, d, typ, lib, mnt, realise in _FISC_SEED:
        if not realise:
            st.session_state.setdefault(f"fisc_date_{rid}", d)
            st.session_state.setdefault(f"fisc_mnt_{rid}", mnt)
        rows.append({"id": rid, "type": typ, "lib": lib, "date_calc": d,
                     "montant_calc": mnt, "exclue": False, "creee": False,
                     "realise": realise})
    st.session_state.fisc_rows = rows
    st.session_state.fisc_seq = 0


def _fisc_ajouter():
    """Crée une échéance manuelle (supprimable, contrairement aux calculées)."""
    st.session_state.fisc_seq += 1
    rid = f"u{st.session_state.fisc_seq}"
    st.session_state[f"fisc_date_{rid}"] = dt.date(2026, 12, 31)
    st.session_state[f"fisc_mnt_{rid}"] = 0
    st.session_state.fisc_rows.append(
        {"id": rid, "type": "Autre", "lib": "Nouvelle échéance", "date_calc": None,
         "montant_calc": None, "exclue": False, "creee": True})


def _fisc_supprimer(rid):
    st.session_state.fisc_rows = [r for r in st.session_state.fisc_rows if r["id"] != rid]


def _fisc_exclure(rid, val):
    """Exclure ne détruit rien : on mémorise les valeurs pour pouvoir réactiver."""
    for r in st.session_state.fisc_rows:
        if r["id"] != rid:
            continue
        if val:
            r["date_save"] = st.session_state.get(f"fisc_date_{rid}", r["date_calc"])
            r["montant_save"] = st.session_state.get(f"fisc_mnt_{rid}", r["montant_calc"])
        else:
            st.session_state[f"fisc_date_{rid}"] = r.get("date_save", r["date_calc"])
            st.session_state[f"fisc_mnt_{rid}"] = r.get("montant_save", r["montant_calc"])
        r["exclue"] = val


def _fisc_reset(rid):
    """Rétablit la date et le montant calculés par l'outil."""
    for r in st.session_state.fisc_rows:
        if r["id"] == rid and not r["creee"]:
            st.session_state[f"fisc_date_{rid}"] = r["date_calc"]
            st.session_state[f"fisc_mnt_{rid}"] = r["montant_calc"]


def _fisc_pastille(typ):
    """Pastille de type. Largeur/hauteur FIXES et texte centré : toutes les pastilles
    ont la même taille quel que soit le mot (TVA, IS, CFE, Autre)."""
    fond, bord, txt = _FISC_TYPES.get(typ, _FISC_TYPES["Autre"])
    return ("<span style='display:inline-block;box-sizing:border-box;width:62px;height:22px;"
            "line-height:20px;text-align:center;border-radius:11px;"
            "font-size:11px;font-weight:500;letter-spacing:0.2px;"
            "background:" + fond + ";border:1px solid " + bord + ";color:" + txt + ";'>" + typ + "</span>")


def _fisc_source(r):
    """Nature exacte de la modification, pour la colonne SOURCE."""
    if r.get("realise"):
        return "réalisé", "#5DCAA5"
    if r["creee"]:
        return "créée par utilisateur", "#5DCAA5"
    d_mod = st.session_state.get(f"fisc_date_{r['id']}") != r["date_calc"]
    m_mod = st.session_state.get(f"fisc_mnt_{r['id']}") != r["montant_calc"]
    if d_mod and m_mod:
        return "date + montant ajustés", "#5A96FF"
    if d_mod:
        return "date ajustée", "#5A96FF"
    if m_mod:
        return "montant ajusté", "#5A96FF"
    return "calculée", "#8a90a0"


def _crc_fiscalite_tracker():
    """Fiscalité Tracker : paramètres du régime + calendrier des échéances.
    Les échéances calculées ne sont pas supprimables — elles s'excluent (réversible) ;
    seules les échéances créées par l'utilisateur peuvent être supprimées."""
    _fisc_init()
    st.markdown(
        "<style>"
        ".st-key-fisc_params{background:#111B2C;border:1px solid #1E2A3D;border-radius:12px;padding:12px 16px;}"
        ".st-key-fisc_cal{background:#0E1626;border:1px solid #1E2A3D;border-radius:16px;padding:14px 18px;margin-top:12px;}"
        # champs montant : pas de boutons +/-, texte à gauche
        "[class*='st-key-fisc_mnt_'] button[data-testid='stNumberInputStepUp'],"
        "[class*='st-key-fisc_mnt_'] button[data-testid='stNumberInputStepDown']{display:none !important;}"
        "[class*='st-key-fisc_mnt_'] input{text-align:right !important;}"
        # petits boutons d'action
        "[class*='st-key-fisc_ex_'] button,[class*='st-key-fisc_rs_'] button,"
        "[class*='st-key-fisc_del_'] button,[class*='st-key-fisc_re_'] button{"
        "padding:2px 9px !important;font-size:12px !important;min-height:0 !important;}"
        ".st-key-fisc_add button{background:rgba(45,107,255,0.14) !important;"
        "border:1px solid #2D6BFF !important;color:#5A96FF !important;}"
        "</style>",
        unsafe_allow_html=True,
    )

    with st.container(key="fisc_params"):
        p1, p2, p3, p4, p5, p6 = st.columns([2, 1, 1.3, 1, 1.3, 0.8],
                                            vertical_alignment="bottom")
        p1.selectbox("Régime TVA",
                     ["Réel normal — mensuel", "Réel normal — trimestriel", "Réel simplifié"],
                     key="fisc_regime")
        p2.number_input("Taux de TVA (%)", min_value=0.0, max_value=30.0, value=20.0,
                        step=0.5, key="fisc_taux")
        p3.date_input("Clôture d'exercice", value=dt.date(2026, 12, 31),
                      format="DD/MM/YYYY", key="fisc_cloture")
        p4.selectbox("CFE / CVAE", ["Oui", "Non"], key="fisc_cfe")
        p5.button("+ Ajouter échéance", key="fisc_add", on_click=_fisc_ajouter,
                  use_container_width=True)
        p6.button("Import", key="fisc_import", use_container_width=True)
        # Rappel de la limite actuelle de la maquette (cf. moteur de régénération).
        st.markdown(
            "<div style='font-size:10.5px;color:#E0A04A;margin-top:8px;'>"
            "⚠️ Maquette — modifier ces paramètres ne régénère pas encore le calendrier : "
            "le moteur de régénération reste à construire.</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="fisc_cal"):
        st.markdown(
            "<div style='font-size:15px;font-weight:700;color:#e8ecf4;'>Calendrier des échéances</div>"
            "<div style='font-size:11.5px;color:#8a90a0;margin-bottom:4px;'>Généré depuis vos paramètres · "
            "les champs modifiés sont signalés individuellement</div>",
            unsafe_allow_html=True,
        )
        ent = "font-size:10px;font-weight:700;letter-spacing:0.5px;color:#5a6478;"
        h1, h2, h3, h4, h5, h6 = st.columns([1.5, 0.8, 3, 1.4, 1.6, 1.1])
        h1.markdown(f"<div style='{ent}'>DATE</div>", unsafe_allow_html=True)
        h2.markdown(f"<div style='{ent}'>TYPE</div>", unsafe_allow_html=True)
        h3.markdown(f"<div style='{ent}'>LIBELLÉ</div>", unsafe_allow_html=True)
        h4.markdown(f"<div style='{ent}text-align:right;'>MONTANT</div>", unsafe_allow_html=True)
        h5.markdown(f"<div style='{ent}'>SOURCE</div>", unsafe_allow_html=True)
        # ACTION est centré sur la même demi-colonne que les boutons (voir plus bas),
        # sinon l'intitulé se retrouve décalé par rapport à l'icône.
        with h6:
            _ha1, _ha2 = st.columns(2)
            _ha2.markdown(f"<div style='{ent}text-align:center;'>ACTION</div>",
                          unsafe_allow_html=True)

        total, total_exclu, nb_exclu, total_realise = 0, 0, 0, 0
        for r in list(st.session_state.fisc_rows):
            rid = r["id"]
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 0.8, 3, 1.4, 1.6, 1.1],
                                                vertical_alignment="center")
            if r.get("realise"):
                # Échéance passée : c'est un fait constaté sur les relevés, donc
                # ni modifiable ni excluable. Elle alimente les charges fixes des
                # mois réalisés (dénominateur de la couverture).
                gris = "color:#8a90a0;font-size:12.5px;"
                c1.markdown(f"<div style='{gris}'>{r['date_calc'].strftime('%d/%m/%Y')}</div>",
                            unsafe_allow_html=True)
                c2.markdown(_fisc_pastille(r["type"]), unsafe_allow_html=True)
                c3.markdown(f"<div style='{gris}'>{r['lib']}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='{gris}text-align:right;'>"
                            + f"{r['montant_calc']:,.0f}".replace(",", " ") + " €</div>",
                            unsafe_allow_html=True)
                c5.markdown("<span style='color:#5DCAA5;font-size:11px;'>réalisé</span>",
                            unsafe_allow_html=True)
                total_realise += r["montant_calc"]
                continue
            if r["exclue"]:
                gris = "color:#5a6478;text-decoration:line-through;font-size:12.5px;"
                d_aff = r.get("date_save") or r["date_calc"]
                m_aff = r.get("montant_save") or r["montant_calc"] or 0
                c1.markdown(f"<div style='{gris}'>{d_aff.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:#5a6478;font-size:11px;'>{r['type']}</span>", unsafe_allow_html=True)
                c3.markdown(f"<div style='{gris}'>{r['lib']}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='{gris}text-align:right;'>{m_aff:,.0f} €</div>".replace(",", " "),
                            unsafe_allow_html=True)
                c5.markdown("<span style='color:#E0A04A;font-size:11px;'>exclue de la projection</span>",
                            unsafe_allow_html=True)
                c6.button("réactiver", key=f"fisc_re_{rid}", on_click=_fisc_exclure,
                          args=(rid, False), use_container_width=True)
                total_exclu += m_aff
                nb_exclu += 1
                continue

            with c1:
                st.date_input("date", key=f"fisc_date_{rid}", format="DD/MM/YYYY",
                              label_visibility="collapsed")
                if not r["creee"] and st.session_state.get(f"fisc_date_{rid}") != r["date_calc"]:
                    st.markdown("<div style='font-size:10px;color:#5a6478;margin-top:-6px;'>calculé : "
                                + r["date_calc"].strftime("%d/%m/%Y") + "</div>", unsafe_allow_html=True)
            c2.markdown(_fisc_pastille(r["type"]), unsafe_allow_html=True)
            c3.markdown(f"<div style='color:#c3ccdd;font-size:12.5px;'>{r['lib']}</div>",
                        unsafe_allow_html=True)
            with c4:
                st.number_input("montant", step=500, key=f"fisc_mnt_{rid}",
                                label_visibility="collapsed")
                if not r["creee"] and st.session_state.get(f"fisc_mnt_{rid}") != r["montant_calc"]:
                    st.markdown("<div style='font-size:10px;color:#5a6478;text-align:right;margin-top:-6px;'>"
                                "calculé : " + f"{r['montant_calc']:,.0f}".replace(",", " ") + " €</div>",
                                unsafe_allow_html=True)
            lbl, coul = _fisc_source(r)
            c5.markdown(f"<span style='color:{coul};font-size:11px;'>{lbl}</span>", unsafe_allow_html=True)
            with c6:
                # Même gabarit pour tous : ↺ en a1, ⊘ ou 🗑 en a2 (donc même taille).
                a1, a2 = st.columns(2)
                if r["creee"]:
                    a2.button("🗑", key=f"fisc_del_{rid}", on_click=_fisc_supprimer,
                              args=(rid,), help="Supprimer cette échéance",
                              use_container_width=True)
                else:
                    if lbl != "calculée":
                        a1.button("↺", key=f"fisc_rs_{rid}", on_click=_fisc_reset,
                                  args=(rid,), help="Rétablir la valeur calculée",
                                  use_container_width=True)
                    a2.button("⊘", key=f"fisc_ex_{rid}", on_click=_fisc_exclure,
                              args=(rid, True), help="Exclure de la projection (réversible)",
                              use_container_width=True)
            total += st.session_state.get(f"fisc_mnt_{rid}", 0)

        # Le total est rendu dans la MÊME grille que les lignes, sinon il se colle au
        # bord droit de la carte au lieu de tomber sous la colonne MONTANT.
        st.markdown("<div style='border-top:1px solid #1E2A3D;margin-top:8px;'></div>",
                    unsafe_allow_html=True)
        _t1, _t2, t3, t4, _t5, _t6 = st.columns([1.5, 0.8, 3, 1.4, 1.6, 1.1],
                                                vertical_alignment="center")
        t3.markdown("<div style='font-size:13.5px;font-weight:700;color:#fff;'>Total à venir</div>"
                    "<div style='font-size:11px;color:#8a90a0;'>Réalisé sur les 3 derniers mois : "
                    + f"{total_realise:,.0f}".replace(",", " ") + " €</div>",
                    unsafe_allow_html=True)
        # padding-right : aligne le total sur les chiffres saisis dans les champs montant.
        t4.markdown("<div style='font-size:14px;font-weight:800;color:#E0604A;"
                    "text-align:right;padding-right:12px;'>"
                    + f"{total:,.0f}".replace(",", " ") + " €</div>", unsafe_allow_html=True)
        if nb_exclu:
            t3.markdown("<div style='font-size:11px;color:#E0A04A;'>"
                        + str(nb_exclu) + " échéance(s) exclue(s) de la projection : "
                        + f"{total_exclu:,.0f}".replace(",", " ") + " €</div>",
                        unsafe_allow_html=True)
    # Marge basse : évite que le total soit masqué par le bouton flottant de Streamlit.
    st.markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)


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


def _placeholder_onglet(titre, desc=""):
    """Contenu 'à venir' pour un onglet non encore construit (dans la DA)."""
    st.markdown(
        "<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "min-height:340px;color:#8a93ad;text-align:center;background:#0E0E16;border:1px solid #20202c;"
        "border-radius:16px;margin-top:14px;'>"
        "<div style='font-size:40px;margin-bottom:10px;'>🚧</div>"
        f"<div style=\"font-family:'Fraunces',serif;font-size:24px;color:#fff;\">{titre}</div>"
        f"<div style='font-size:14px;margin-top:8px;max-width:540px;'>{desc}</div></div>",
        unsafe_allow_html=True,
    )


def _onglet_ma_treso():
    """Onglet 'Ma tréso' : courbe d'évolution, comptes connectés, période d'analyse,
    derniers mouvements (banque + n° de compte), et hypothèses éditables."""
    # CSS injecté UNE fois, hors des colonnes (sinon il crée un élément fantôme
    # qui décale l'espacement). Espacement vertical uniforme des cartes + style
    # de la carte 'Comptes connectés'.
    st.markdown(
        "<style>"
        # Gap auto de Streamlit neutralisé (=0) : l'écart entre les cartes est fixé
        # par le margin-top de CHAQUE carte (voir plus bas), pas ici.
        ".st-key-mt_grid [data-testid='stColumn'] > [data-testid='stVerticalBlock']{gap:0 !important;}"
        ".st-key-mt_comptes{background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;padding:14px 18px;height:172px !important;box-sizing:border-box;}"
        ".st-key-mt_comptes .stButton button{background:rgba(45,107,255,0.14) !important;"
        "border:1px solid #2D6BFF !important;color:#5A96FF !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="mt_grid"):
        col_g, col_d = st.columns([1.2, 1], gap="medium")
    with col_g:
        st.markdown(
            """
            <div style="background:#0E0E16;border:1px solid #20202c;border-radius:16px;padding:16px 18px;height:300px;box-sizing:border-box;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:16px;font-weight:600;color:#e8ecf4;">Évolution de la trésorerie</span>
                <span style="font-size:11px;color:#8a90a0;">16/04/2026 → 15/07/2026</span></div>
              <div style="font-size:12px;color:#8a90a0;margin-top:2px;">Balance agrégée des comptes courants</div>
              <div style="font-size:24px;font-weight:800;color:#fff;margin-top:8px;">1 240 000 €
                <span style="font-size:13px;color:#28c76f;font-weight:600;">▲ +4,2 %</span></div>
              <div style="display:flex;gap:18px;font-size:11px;color:#c3ccdd;margin-top:6px;">
                <span><span style="color:#2D6BFF;font-weight:700;">━</span> Historique</span>
                <span><span style="color:#5DCAA5;font-weight:700;">╌╌</span> Projection</span></div>
              <svg viewBox="0 0 320 110" preserveAspectRatio="none" style="width:100%;height:110px;margin-top:8px;">
                <defs><linearGradient id="gdmt" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2D6BFF" stop-opacity="0.30"/><stop offset="1" stop-color="#2D6BFF" stop-opacity="0"/></linearGradient></defs>
                <polygon fill="url(#gdmt)" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50 240,110 0,110"/>
                <polyline fill="none" stroke="#2D6BFF" stroke-width="2.5" points="0,90 30,82 60,86 90,70 120,74 150,58 180,62 210,46 240,50"/>
                <polyline fill="none" stroke="#5DCAA5" stroke-width="2.5" stroke-dasharray="7 5" points="240,50 270,40 300,30 320,26"/>
                <line x1="240" y1="8" x2="240" y2="110" stroke="#8a90a0" stroke-width="0.7" stroke-dasharray="3 4"/>
              </svg>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Résumé LECTURE SEULE des moteurs, dérivé des trackers. Plus aucune saisie
        # ici : un chiffre ne se règle qu'à l'endroit où il est le plus précis.
        m = _hyp_moteurs()
        postes = [("CA récurrent", "rec", "#5DCAA5"), ("CA ponctuel", "pon", "#5DCAA5"),
                  ("Charges fixes", "fix", "#E0604A"), ("Charges variables", "var", "#E0604A"),
                  ("Charges ponctuelles", "ponc", "#E0604A")]
        lignes_h = ""
        for lib, cle, barre in postes:
            r, p = m[cle]
            lignes_h += (
                "<div style='display:flex;align-items:center;padding:9px 0;"
                "border-top:1px solid #1E2A3D;'>"
                "<span style='width:3px;height:15px;background:" + barre + ";display:inline-block;"
                "margin-right:10px;'></span>"
                "<span style='flex:1;color:#c3ccdd;font-size:13px;'>" + lib + "</span>"
                "<span style='width:90px;text-align:right;color:#8a90a0;font-size:12.5px;'>"
                + _ct_k(r) + "</span>"
                "<span style='width:90px;text-align:right;color:#fff;font-size:12.5px;"
                "font-weight:600;'>" + _ct_k(p) + "</span></div>")
        sr, sp = m["solde"]
        st.markdown(
            "<div style='background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;"
            "padding:16px 18px;margin-top:20px;'>"
            "<div style='font-size:16px;font-weight:600;color:#e8ecf4;'>Principales hypothèses</div>"
            "<div style='font-size:12px;color:#8a90a0;margin-bottom:6px;'>Moyennes mensuelles en k€ — "
            "calculées depuis les trackers, modifiables à leur source</div>"
            "<div style='display:flex;padding-bottom:4px;'>"
            "<span style='flex:1;'></span>"
            "<span style='width:90px;text-align:right;font-size:9.5px;font-weight:700;"
            "letter-spacing:0.5px;color:#5a6478;'>RÉALISÉ</span>"
            "<span style='width:90px;text-align:right;font-size:9.5px;font-weight:700;"
            "letter-spacing:0.5px;color:#5a6478;'>PROJETÉ</span></div>"
            + lignes_h +
            "<div style='display:flex;align-items:center;padding:10px 0 0;"
            "border-top:1px solid #1E2A3D;margin-top:4px;'>"
            "<span style='flex:1;color:#fff;font-size:13px;font-weight:700;'>Solde net moyen</span>"
            "<span style='width:90px;text-align:right;color:#8a90a0;font-size:12.5px;"
            "font-weight:700;'>+ " + _ct_k(sr) + "</span>"
            "<span style='width:90px;text-align:right;color:#5DCAA5;font-size:13px;"
            "font-weight:800;'>+ " + _ct_k(sp) + "</span></div></div>",
            unsafe_allow_html=True,
        )

    with col_d:
        with st.container(key="mt_comptes"):
            cc1, cc2 = st.columns([1.5, 1], vertical_alignment="center")
            cc1.markdown(
                "<div style='font-size:15px;font-weight:600;color:#fff;'>Comptes connectés</div>"
                "<div style='margin-top:4px;'><span style='font-size:26px;font-weight:800;color:#fff;'>4</span>"
                "<span style='font-size:12.5px;color:#c3ccdd;margin-left:9px;'>comptes · 1 240 000 € agrégés</span></div>",
                unsafe_allow_html=True,
            )
            cc2.button("Gérer les comptes →", key="matreso_gerer",
                       on_click=go, args=("espace_avenir",), use_container_width=True)
        st.markdown(
            """
            <div style="background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;padding:16px 18px;margin-top:10px;height:150px;box-sizing:border-box;">
              <div style="font-size:15px;font-weight:600;color:#fff;">Période d'analyse</div>
              <div style="font-size:12px;color:#8a90a0;margin-bottom:12px;">Points extrêmes de trésorerie, agrégés par compte</div>
              <div style="display:flex;justify-content:space-between;">
                <div><div style="font-size:12.5px;color:#c3ccdd;">Point haut</div>
                  <div style="font-size:18px;font-weight:700;color:#5DCAA5;">1 310 000 €</div>
                  <div style="font-size:11.5px;color:#8a90a0;">12/03/2026</div></div>
                <div><div style="font-size:12.5px;color:#c3ccdd;">Point bas</div>
                  <div style="font-size:18px;font-weight:700;color:#E0604A;">940 000 €</div>
                  <div style="font-size:11.5px;color:#8a90a0;">28/01/2026</div></div>
                <div><div style="font-size:12.5px;color:#c3ccdd;">Amplitude</div>
                  <div style="font-size:18px;font-weight:700;color:#fff;">370 000 €</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        mvts = [
            ("14/07", "Encaissement client A", "BNP · FR76 •••• 4021", "+ 84 000 €", "#5DCAA5"),
            ("12/07", "Salaires & charges", "BNP · FR76 •••• 4021", "− 90 000 €", "#E0604A"),
            ("10/07", "Encaissement client B", "Qonto · FR76 •••• 8830", "+ 52 300 €", "#5DCAA5"),
            ("08/07", "Fournisseur logistique", "BNP · FR76 •••• 4021", "− 34 500 €", "#E0604A"),
            ("05/07", "Remboursement TVA", "Crédit Agricole · FR76 •••• 6094", "+ 18 900 €", "#5DCAA5"),
        ]
        lignes = ""
        for d, lib, cpt, montant, coul in mvts:
            lignes += (
                "<div style='display:flex;justify-content:space-between;align-items:flex-start;"
                "padding:18px 0;border-top:1px solid #1E2A3D;'>"
                "<div style='display:flex;gap:12px;'>"
                f"<span style='font-size:11.5px;color:#8a90a0;min-width:38px;'>{d}</span>"
                f"<div><div style='font-size:13px;color:#c3ccdd;'>{lib}</div>"
                f"<div style='font-size:10.5px;color:#8a90a0;'>{cpt}</div></div></div>"
                f"<span style='font-size:13px;font-weight:600;color:{coul};'>{montant}</span></div>"
            )
        st.markdown(
            "<div style=\"background:#111B2C;border:1px solid #1E2A3D;border-radius:16px;"
            "padding:16px 18px;margin-top:25px;height:438px;box-sizing:border-box;\">"
            "<div style='font-size:15px;font-weight:600;color:#fff;margin-bottom:2px;'>5 derniers mouvements</div>"
            + lignes + "</div>",
            unsafe_allow_html=True,
        )


def _hyp_moteurs():
    """Agrège les moteurs du modèle DEPUIS les trackers. Rien n'est saisi ici :
    tout est dérivé, ce qui rend la double saisie impossible par construction.
    Retourne des moyennes mensuelles (réalisé M-2→M0, projeté M+1→M+3)."""
    _rt_init()
    _ct_init()

    def moy(v):
        return sum(v) / 3.0

    rec_r = rec_p = pon_r = pon_p = 0.0
    for cid, _s, _l, profil, reals in _RT_CATS:
        base = round(sum(reals) / 3.0, 1)
        projs = _rt_projections(cid, profil, base)
        if _RT_PROFILS[profil][1]:
            rec_r += moy(reals)
            rec_p += moy(projs)
        else:
            pon_r += moy(reals)
            pon_p += moy(projs)

    fix_r = fix_p = var_r = var_p = ponc_r = ponc_p = 0.0
    for cat in _CT_CATS:
        reals = _ct_reals(cat)
        base = round(sum(reals) / 3.0, 1)
        projs = _ct_projections(cat, base)
        if _CT_PROFILS[cat[3]][1]:
            fix_r += moy(reals)
            fix_p += moy(projs)
        elif cat[3] == "variable":
            var_r += moy(reals)
            var_p += moy(projs)
        else:
            ponc_r += moy(reals)
            ponc_p += moy(projs)

    pm = _ct_impots_mensuels()
    fisc_r = sum(pm.get((y, m), 0.0) for y, m, _ in _CT_MOIS_REAL) / 3.0
    fisc_p = sum(pm.get((y, m), 0.0) for y, m, _ in _CT_MOIS_PROJ) / 3.0
    return {
        "rec": (rec_r, rec_p), "pon": (pon_r, pon_p),
        "fix": (fix_r, fix_p), "fisc": (fisc_r, fisc_p),
        "var": (var_r, var_p), "ponc": (ponc_r, ponc_p),
        "solde": (rec_r + pon_r - fix_r - var_r - ponc_r,
                  rec_p + pon_p - fix_p - var_p - ponc_p),
    }


def _hyp_ajustements():
    """Compte les lignes dont la projection s'écarte de sa valeur par défaut.
    Sert à dire au client si sa projection reproduit l'historique ou non."""
    _rt_init()
    _ct_init()
    nb_rev = 0
    for cid, _s, _l, profil, reals in _RT_CATS:
        base = round(sum(reals) / 3.0, 1)
        defaut = base if profil != "ponctuel" else 0.0
        if _rt_projections(cid, profil, base) != [defaut] * 3:
            nb_rev += 1
    nb_chg = 0
    for cat in _CT_CATS:
        if cat[3] == "échéancier":
            continue  # piloté par le calendrier, pas ajustable ici
        reals = _ct_reals(cat)
        base = round(sum(reals) / 3.0, 1)
        defaut = base if cat[4] else 0.0
        if _ct_projections(cat, base) != [defaut] * 3:
            nb_chg += 1
    return nb_rev, nb_chg


def _hyp_confirmer():
    st.session_state.hyp_verifie = dt.date.today().strftime("%d/%m/%Y")


def _onglet_hypotheses():
    """Onglet 'Hypothèses' : synthèse en LECTURE SEULE des moteurs du modèle.
    Un chiffre ne se saisit qu'à l'endroit où il est le plus précis — donc dans les
    trackers. Ici on montre ce que le modèle utilise, comment c'est calculé et d'où
    ça vient."""
    m = _hyp_moteurs()
    nb_rev, nb_chg = _hyp_ajustements()
    verifie = st.session_state.get("hyp_verifie")

    st.markdown(
        "<style>"
        ".st-key-hyp_card{background:#0E1626;border:1px solid #1E2A3D;border-radius:16px;padding:14px 18px;margin-top:12px;}"
        ".st-key-hyp_ok button{background:rgba(93,202,165,0.14) !important;"
        "border:1px solid #5DCAA5 !important;color:#8fe0c4 !important;font-size:12px !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="background:rgba(45,107,255,0.08);border-radius:8px;padding:9px 14px;'
        'font-size:12px;color:#9fc0ff;">M0 = juillet 2026, dernier mois clôturé · toutes les valeurs '
        'sont des moyennes mensuelles en k€ · pour corriger un chiffre, allez à sa source</div>',
        unsafe_allow_html=True)

    # ---- État des ajustements (recalculé, jamais figé) ----
    def bloc(titre, nb):
        if nb:
            return ("<span style='color:#5DCAA5;'>●</span> <span style='color:#c3ccdd;'>" + titre
                    + " — <b style='color:#5DCAA5;'>" + str(nb) + " modification"
                    + ("s" if nb > 1 else "") + "</b></span>")
        return ("<span style='color:#E0A04A;'>▲</span> <span style='color:#c3ccdd;'>" + titre
                + " — <b style='color:#E0A04A;'>aucune modification, la projection "
                  "reproduit l'historique</b></span>")

    fond = "rgba(93,202,165,0.07)" if verifie else "rgba(224,160,74,0.07)"
    bord = "#5DCAA5" if verifie else "#E0A04A"
    with st.container(key="hyp_etat"):
        st.markdown(
            "<div style='background:" + fond + ";border:1px solid " + bord
            + "66;border-radius:10px;padding:10px 14px;margin-top:10px;'>"
            "<div style='font-size:12.5px;font-weight:700;color:" + bord + ";'>État des ajustements"
            + ("<span style='font-weight:400;color:#8a90a0;font-size:10px;margin-left:10px;'>vérifié le "
               + verifie + "</span>" if verifie else "") + "</div>"
            "<div style='font-size:11.5px;margin-top:6px;'>" + bloc("Revenus", nb_rev)
            + "<span style='margin:0 26px;'></span>" + bloc("Charges", nb_chg) + "</div></div>",
            unsafe_allow_html=True)
        if not verifie:
            b1, _b2 = st.columns([1.4, 4])
            b1.button("J'ai vérifié, rien à ajuster", key="hyp_ok",
                      on_click=_hyp_confirmer, use_container_width=True)

    # ---- Moteurs du modèle ----
    rat = [2.0, 3.4, 0.9, 0.9, 1.4]
    ent = "font-size:9.5px;font-weight:700;letter-spacing:0.5px;color:#5a6478;"
    with st.container(key="hyp_card"):
        st.markdown("<div style='font-size:15px;font-weight:700;color:#e8ecf4;'>Moteurs du modèle</div>"
                    "<div style='font-size:11px;color:#8a90a0;'>Valeurs calculées depuis vos relevés · "
                    "lecture seule · corriger à la source</div>", unsafe_allow_html=True)
        h = st.columns(rat)
        h[0].markdown(f"<div style='{ent}'>MOTEUR</div>", unsafe_allow_html=True)
        h[1].markdown(f"<div style='{ent}'>MÉTHODE DE CALCUL</div>", unsafe_allow_html=True)
        h[2].markdown(f"<div style='{ent}text-align:right;'>RÉALISÉ</div>", unsafe_allow_html=True)
        h[3].markdown(f"<div style='{ent}text-align:right;'>PROJETÉ</div>", unsafe_allow_html=True)
        h[4].markdown(f"<div style='{ent}text-align:right;'>SOURCE</div>", unsafe_allow_html=True)
        st.markdown("<div style='border-top:1px solid #1E2A3D;'></div>", unsafe_allow_html=True)

        # (libellé, méthode, clé, source, retrait, couleur du projeté)
        lignes = [
            ("ENCAISSEMENTS", None, None, None, False, None),
            ("CA récurrent", "Moyenne mensuelle des flux récurrents détectés",
             "rec", "Revenu Tracker", False, "#5DCAA5"),
            ("CA ponctuel", "Moyenne mensuelle des encaissements sans périodicité",
             "pon", "Revenu Tracker", False, "#fff"),
            ("DÉCAISSEMENTS", None, None, None, False, None),
            ("Charges fixes", "Moyenne mensuelle des postes stables et échéanciers",
             "fix", "Charges Tracker", False, "#fff"),
            ("dont échéances fiscales", "Moyenne mensuelle des échéances du calendrier fiscal",
             "fisc", "Calendrier fiscal", True, "#8a90a0"),
            ("Charges variables", "Moyenne mensuelle des charges indexées sur le CA",
             "var", "Charges Tracker", False, "#fff"),
            ("Charges ponctuelles", "Moyenne mensuelle des décaissements sans périodicité",
             "ponc", "Charges Tracker", False, "#E0A04A"),
        ]
        for lib, meth, cle, src, retrait, coul in lignes:
            if meth is None:
                st.markdown("<div style='font-size:10.5px;font-weight:700;letter-spacing:0.5px;"
                            "color:#c3ccdd;margin:10px 0 2px;'>" + lib + "</div>",
                            unsafe_allow_html=True)
                continue
            r, p = m[cle]
            c = st.columns(rat, vertical_alignment="center")
            pad = "padding-left:16px;" if retrait else ""
            tc = "#8a90a0" if retrait else "#fff"
            c[0].markdown(f"<div style='color:{tc};font-size:12px;{pad}'>{lib}</div>",
                          unsafe_allow_html=True)
            c[1].markdown(f"<div style='color:#8a90a0;font-size:11px;'>{meth}</div>",
                          unsafe_allow_html=True)
            c[2].markdown(f"<div style='color:#c3ccdd;font-size:11.5px;text-align:right;'>"
                          f"{_ct_k(r)}</div>", unsafe_allow_html=True)
            c[3].markdown(f"<div style='color:{coul};font-size:11.5px;text-align:right;"
                          f"font-weight:700;'>{_ct_k(p)}</div>", unsafe_allow_html=True)
            c[4].markdown(f"<div style='color:#5A96FF;font-size:11px;text-align:right;'>{src} →</div>",
                          unsafe_allow_html=True)

        st.markdown("<div style='border-top:1px solid #1E2A3D;margin-top:8px;'></div>",
                    unsafe_allow_html=True)
        sr, sp = m["solde"]
        t = st.columns(rat, vertical_alignment="center")
        t[0].markdown("<div style='font-size:12.5px;font-weight:700;color:#fff;'>Solde net moyen</div>",
                      unsafe_allow_html=True)
        t[1].markdown("<div style='color:#8a90a0;font-size:11px;'>Encaissements moins décaissements</div>",
                      unsafe_allow_html=True)
        t[2].markdown(f"<div style='color:#c3ccdd;font-size:12px;text-align:right;font-weight:700;'>"
                      f"+ {_ct_k(sr)}</div>", unsafe_allow_html=True)
        t[3].markdown(f"<div style='color:#5DCAA5;font-size:12.5px;text-align:right;font-weight:800;'>"
                      f"+ {_ct_k(sp)}</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)


def ecran_dashboard():
    """Tableau de bord : 4 onglets horizontaux (Ma tréso, Compte de résultat cash,
    Smart tréso, Smart allocation). Le Compte de résultat cash a 4 sous-onglets
    en pilules (Vue d'ensemble, Charges, Fiscalité, Revenu). Données fictives."""
    sidebar_espace("dashboard")
    profil = st.session_state.profil or "—"
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <div style="display:flex;align-items:flex-end;gap:14px;"><span style="font-family:'Fraunces',serif;font-size:42px;font-weight:700;color:#fff;line-height:1;">Tableau de bord</span>
            <span style="font-size:15px;color:#cdd8f5;background:rgba(45,107,255,.14);border:1px solid #2D6BFF;border-radius:22px;padding:6px 16px;">Profil · {profil}</span></div>
        </div>
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
    top = st.tabs(["Ma tréso", "Hypothèses", "Compte de résultat cash", "Smart tréso", "Smart allocation"])
    with top[0]:
        _onglet_ma_treso()
    with top[1]:
        _onglet_hypotheses()
    with top[2]:
        sub = st.pills(
            "Sous-onglets du compte de résultat cash",
            ["Vue d'ensemble", "Charges Tracker", "Fiscalité Tracker", "Revenu Tracker"],
            default="Vue d'ensemble", label_visibility="collapsed", key="crc_sub",
        )
        if sub == "Charges Tracker":
            _crc_charges_tracker()
        elif sub == "Fiscalité Tracker":
            _crc_fiscalite_tracker()
        elif sub == "Revenu Tracker":
            _crc_revenu_tracker()
        else:  # Vue d'ensemble
            _report_flux()
    with top[3]:
        _placeholder_onglet(
            "Smart Tréso",
            "Allocation de la trésorerie en poches (fonctionnement, précaution, "
            "investissement, legacy). À venir.")
    with top[4]:
        _report_placements()


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
    "onb_secteur": ecran_onb_secteur,
    "onb_investisseur": ecran_onb_investisseur,
    "onb_profil1b": ecran_onb_profil1b,
    "onb_profil2a": ecran_onb_profil2a,
    "onb_profil2b": ecran_onb_profil2b,
    "onb_profil2c": ecran_onb_profil2c,
    "onb_profil3a": ecran_onb_profil3a,
    "onb_profil3b": ecran_onb_profil3b,
    "onb_profil4": ecran_onb_profil4,
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
