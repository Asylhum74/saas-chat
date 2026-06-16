import os
import json
import base64
import anthropic
from dotenv import load_dotenv

load_dotenv()

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def lire_pdf(chemin):
    with open(chemin, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')

def convertir_lot(client_id, fichiers, champs_extra):
    dossier = f"documents/{client_id}"
    messages_content = []

    for fichier in fichiers:
        chemin = f"{dossier}/{fichier}"
        if fichier.endswith(".pdf"):
            messages_content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": lire_pdf(chemin)
                }
            })
        elif fichier.endswith(".txt"):
            with open(chemin, 'r', encoding='utf-8') as f:
                messages_content.append({
                    "type": "text",
                    "text": f"--- {fichier} ---\n{f.read()}"
                })

    champs_str = ""
    if champs_extra:
        champs_str = "\n".join([f'      "{champ}": "valeur ou null",' for champ in champs_extra])
        champs_str = "\n" + champs_str

   prompt = f"""Analyse ces documents et extrais tous les produits mentionnés.

    RÈGLES STRICTES :
    - Extrais TOUS les produits sans exception
    - Pour la description : copie le texte descriptif du document le plus fidèlement possible, ne résume pas
    - Pour les tags : inclus TOUS ces éléments séparément : nom du produit, catégorie, ingrédients principaux, effets, zone du corps, type d'utilisation, synonymes courants
    - Ne réécris pas, ne résume pas, ne reformule pas — copie fidèlement les informations du document
    - Si une information n'est pas dans le document, mets null
    
    Retourne UNIQUEMENT un JSON valide sans texte avant ou après, sans backticks :
    {{
      "produits": [
        {{
          "nom": "nom EXACT du produit tel qu'il apparaît dans le document",
          "categorie": "catégorie exacte",
          "description": "texte descriptif complet copié fidèlement depuis le document",
          "prix": "prix exact si mentionné sinon null",{champs_str}
          "tags": ["tous", "les", "mots", "clés", "possibles", "synonymes", "inclus"]
        }}
      ]
    }}
    {"Pour les champs supplémentaires (" + ", ".join(champs_extra) + "), copie ces informations exactement depuis les documents sans les résumer." if champs_extra else ""}"""
    
    messages_content.append({"type": "text", "text": prompt})

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": messages_content}]
    )

    try:
        json_str = response.content[0].text.strip()
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Erreur parsing JSON lot : {e}")
        print("Réponse brute :", response.content[0].text[:300])
        return None

def convertir_docs_en_json(client_id, taille_lot=10):
    dossier = f"documents/{client_id}"
    if not os.path.exists(dossier):
        print(f"Dossier '{dossier}' introuvable")
        return

    # Charger les champs extra du client
    try:
        with open('clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
        champs_extra = clients.get(client_id, {}).get('champs_extra', [])
    except:
        champs_extra = []

    # Lister les fichiers à traiter
    fichiers = [
        f for f in os.listdir(dossier)
        if f.endswith(('.txt', '.pdf')) and f != 'produits.json'
    ]

    if not fichiers:
        print("Aucun document trouvé !")
        return

    print(f"{len(fichiers)} fichiers trouvés, traitement par lots de {taille_lot}...")

    tous_les_produits = []
    nb_lots = (len(fichiers) + taille_lot - 1) // taille_lot

    for i in range(0, len(fichiers), taille_lot):
        lot = fichiers[i:i+taille_lot]
        num_lot = i // taille_lot + 1
        print(f"\nLot {num_lot}/{nb_lots} : {len(lot)} fichiers...")

        result = convertir_lot(client_id, lot, champs_extra)
        if result:
            nb = len(result.get('produits', []))
            tous_les_produits.extend(result.get('produits', []))
            print(f"✓ {nb} produits extraits de ce lot")
        else:
            print(f"⚠️ Lot {num_lot} échoué, on continue...")

    if not tous_les_produits:
        print("Aucun produit extrait !")
        return None

    # Fusionner et sauvegarder
    final = {'produits': tous_les_produits}
    output = f"{dossier}/produits.json"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Total : {len(tous_les_produits)} produits extraits !")
    print(f"✓ Sauvegardé dans {output}")

    # Aperçu
    print("\n── Aperçu ──")
    for p in tous_les_produits[:3]:
        print(f"  • {p['nom']} ({p['categorie']}) — {p.get('prix') or 'prix non renseigné'}")
    if len(tous_les_produits) > 3:
        print(f"  ... et {len(tous_les_produits)-3} autres")

    return final

if __name__ == "__main__":
    convertir_docs_en_json("demo")
