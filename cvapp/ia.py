"""Rédaction du profil du CV par l'IA (Claude, d'Anthropic).

Chaque utilisateur utilise sa propre clé API Anthropic (https://console.anthropic.com).
Elle est enregistrée uniquement sur son ordinateur : l'application publiée sur
GitHub ne contient aucune clé.
"""

import os

import yaml

MODELE = "claude-opus-5-5"
ADRESSE_CLES = "https://console.anthropic.com/settings/keys"

TONS = {
    "professionnel": "sobre et professionnel",
    "dynamique": "dynamique et enthousiaste, sans exagération",
    "chaleureux": "chaleureux et humain",
}

CONSIGNES = """\
Tu rédiges la rubrique « Profil » d'un CV, en français.

Le résultat doit être :
- un seul paragraphe de 3 à 4 phrases (45 à 75 mots), qui tient sur 3 ou 4 lignes du CV ;
- écrit à la première personne, de façon naturelle, comme la personne parlerait d'elle-même ;
- concret : appuie-toi sur son titre, ses expériences, ses formations et ses compétences ;
  termine par ce qu'elle recherche (le poste visé) si on peut le déduire ;
- fidèle : n'invente aucun fait (pas de chiffre, d'entreprise, de diplôme ou de durée absents
  des informations reçues) ;
- sans formule creuse (« passionné et motivé », « force de proposition »…) sauf si la
  personne l'a écrit elle-même.

Réponds uniquement par le paragraphe : pas de titre, pas de guillemets, pas de mise en forme."""


class ErreurIA(Exception):
    """Erreur expliquée en français, affichée telle quelle à l'utilisateur."""


def cle_par_defaut(cle_enregistree: str | None) -> str:
    """La clé enregistrée dans l'application, sinon celle de l'environnement Windows."""
    return (cle_enregistree or os.environ.get("ANTHROPIC_API_KEY") or "").strip()


def _resume_du_cv(cv: dict) -> str:
    """Les informations utiles du CV, en texte lisible (sans la photo ni le profil actuel)."""
    utile = {k: cv.get(k) for k in ("identite", "experiences", "formations",
                                     "competences", "langues", "centres_interet")}
    identite = dict(utile.get("identite") or {})
    for prive in ("email", "telephone", "site_web", "linkedin"):  # inutile pour écrire
        identite.pop(prive, None)
    utile["identite"] = identite
    utile = {k: v for k, v in utile.items() if v}
    return yaml.safe_dump(utile, allow_unicode=True, sort_keys=False)


def rediger_profil(cv: dict, description: str, ton: str, cle: str, profil_actuel: str = "") -> str:
    """Demande à Claude un paragraphe de profil. Renvoie le texte, ou lève ErreurIA."""
    import anthropic

    if not cle:
        raise ErreurIA("Indiquez d'abord votre clé API Anthropic.")

    demande = [f"Voici les informations du CV :\n\n{_resume_du_cv(cv)}"]
    if description.strip():
        demande.append(f"Ce que la personne dit d'elle-même :\n{description.strip()}")
    if profil_actuel.strip():
        demande.append(f"Son profil actuel (à améliorer, garde les idées justes) :\n{profil_actuel.strip()}")
    demande.append(f"Ton souhaité : {TONS.get(ton, TONS['professionnel'])}.")

    client = anthropic.Anthropic(api_key=cle, timeout=90.0)
    try:
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=16000,
            system=CONSIGNES,
            output_config={"effort": "low"},  # tâche courte : réponse rapide et peu coûteuse
            # Si le modèle refuse par prudence, l'API réessaie sur le modèle de secours recommandé
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": "\n\n".join(demande)}],
        )
    except anthropic.AuthenticationError:
        raise ErreurIA("Cette clé API n'est pas valide. Vérifiez-la (elle commence par « sk-ant- »).") from None
    except anthropic.PermissionDeniedError:
        raise ErreurIA("Cette clé API n'a pas le droit d'utiliser ce modèle.") from None
    except anthropic.RateLimitError:
        raise ErreurIA("Trop de demandes en peu de temps. Patientez une minute puis réessayez.") from None
    except anthropic.BadRequestError as erreur:
        message = str(getattr(erreur, "message", erreur))
        if "credit" in message.lower() or "billing" in message.lower():
            raise ErreurIA("Votre compte Anthropic n'a plus de crédit. Ajoutez-en sur "
                           "console.anthropic.com (rubrique « Billing »).") from None
        raise ErreurIA(f"La demande a été refusée : {message}") from None
    except anthropic.APIConnectionError:
        raise ErreurIA("Impossible de joindre l'IA. Vérifiez votre connexion Internet.") from None
    except anthropic.APIStatusError as erreur:
        raise ErreurIA(f"Le service d'IA a rencontré un problème ({erreur.status_code}). "
                       "Réessayez dans un instant.") from None

    if reponse.stop_reason == "refusal":
        raise ErreurIA("L'IA n'a pas voulu rédiger ce texte. Reformulez votre description et réessayez.")
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip().strip('"«» ')
    if not texte:
        raise ErreurIA("L'IA n'a rien renvoyé. Réessayez.")
    return " ".join(texte.split())
