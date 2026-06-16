import os
import json
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import shutil

load_dotenv()

app = Flask(__name__)
CORS(app)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Charger les clients ──
def load_clients():
    try:
        with open('clients.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

# ── Charger les produits d'un client ──
def load_produits(client_id):
    chemin = f"documents/{client_id}/produits.json"
    try:
        with open(chemin, 'r', encoding='utf-8') as f:
            return json.load(f).get('produits', [])
    except:
        return []

# ── Recherche produits ──
def recherche_produit(client_id, query, categorie=None):
    produits = load_produits(client_id)
    if not produits:
        return []

    query_lower = query.lower()
    resultats = []

    for p in produits:
        score = 0
        # Recherche dans le nom
        if query_lower in p.get('nom', '').lower():
            score += 10
        # Recherche dans les tags
        for tag in p.get('tags', []):
            if query_lower in tag.lower() or tag.lower() in query_lower:
                score += 5
        # Recherche dans la description
        if query_lower in p.get('description', '').lower():
            score += 3
        # Recherche dans la catégorie
        if query_lower in p.get('categorie', '').lower():
            score += 4
        # Filtre catégorie si précisé
        if categorie and categorie.lower() not in p.get('categorie', '').lower():
            score = 0

        if score > 0:
            resultats.append({**p, '_score': score})

    # Trier par score
    resultats.sort(key=lambda x: x['_score'], reverse=True)
    # Retourner les 5 meilleurs sans le score
    return [{k: v for k, v in p.items() if k != '_score'} for p in resultats[:10]]

# ── Lister toutes les catégories ──
def lister_categories(client_id):
    produits = load_produits(client_id)
    categories = list(set([p.get('categorie', '') for p in produits if p.get('categorie')]))
    return sorted(categories)

# ── Définition des outils Claude ──
def get_tools():
    return [
        {
            "name": "recherche_produit",
            "description": "Recherche des produits dans le catalogue selon une requête. Utilise cet outil dès qu'un utilisateur mentionne un produit, une catégorie ou demande une recommandation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Ce que l'utilisateur cherche (ex: brume intime, massage, cadeau couple)"
                    },
                    "categorie": {
                        "type": "string",
                        "description": "Catégorie spécifique si mentionnée, sinon laisser vide"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "lister_categories",
            "description": "Liste toutes les catégories de produits disponibles. Utile quand l'utilisateur demande ce qu'on propose ou veut naviguer par catégorie.",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        }
    ]

# ── Route config client ──
@app.route('/client-config')
def client_config():
    client_id = request.args.get('client', '')
    clients = load_clients()
    config = clients.get(client_id, {})
    if not config:
        return jsonify({'error': 'Client introuvable'}), 404
    return jsonify({
        'nom':    config.get('nom', 'Assistant'),
        'titre':  config.get('titre', 'Besoin d\'aide ?'),
        'color1': config.get('color1', '#6C63FF'),
        'color2': config.get('color2', '#A78BFA'),
    })

# ── Route chat ──
@app.route('/chat', methods=['POST'])
def chat():
    data      = request.json
    messages  = data.get('messages', [])
    client_id = data.get('client', '')

    clients = load_clients()
    config  = clients.get(client_id, {})
    if not config:
        return jsonify({'error': 'Client introuvable'}), 404

    system_prompt = config.get('prompt', 'Tu es un assistant commercial bienveillant.')
    tools = get_tools()

    # ── Premier appel à Claude ──
    response = claude.messages.create(
       model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        tools=tools,
        messages=messages
    )

    # ── Claude veut appeler un outil ? ──
    while response.stop_reason == "tool_use":
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"Outil appelé : {block.name} avec {block.input}")

            if block.name == "recherche_produit":
                resultats = recherche_produit(
                    client_id,
                    block.input.get("query", ""),
                    block.input.get("categorie")
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(resultats, ensure_ascii=False)
                })

            elif block.name == "lister_categories":
                categories = lister_categories(client_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(categories, ensure_ascii=False)
                })

        # Ajouter la réponse de Claude et les résultats des outils
        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results}
        ]

        # Nouvel appel à Claude avec les résultats
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

    # ── Incrémenter stats ──
    try:
        clients[client_id]['messages'] = clients[client_id].get('messages', 0) + 1
        with open('clients.json', 'w', encoding='utf-8') as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)
    except:
        pass

    # ── Extraire le texte de la réponse finale ──
    texte = next((b.text for b in response.content if hasattr(b, 'text')), '')

    return jsonify({
        "content": [{"text": texte}],
        "messages": [
            {"role": m["role"], "content": m["content"] if isinstance(m["content"], str) else str(m["content"])}
            for m in messages
        ]
    })

# ── Lire tous les clients ──
@app.route('/admin/clients', methods=['GET'])
def admin_get_clients():
    return jsonify(load_clients())

# ── Créer ou modifier un client ──
@app.route('/admin/clients', methods=['POST'])
def admin_save_client():
    data = request.json
    clients = load_clients()
    client_id = data.get('id')
    if not client_id:
        return jsonify({'error': 'ID manquant'}), 400
    
    # Créer le dossier documents si nouveau client
    dossier = f"documents/{client_id}"
    if not os.path.exists(dossier):
        os.makedirs(dossier)

    clients[client_id] = {
        'nom':          data.get('nom', ''),
        'titre':        data.get('titre', ''),
        'color1':       data.get('color1', '#6C63FF'),
        'color2':       data.get('color2', '#A78BFA'),
        'prompt':       data.get('prompt', ''),
        'statut':       data.get('statut', 'actif'),
        'champs_extra': data.get('champs_extra', []),
        'messages':     clients.get(client_id, {}).get('messages', 0),
        'documents':    clients.get(client_id, {}).get('documents', []),
        'date':         clients.get(client_id, {}).get('date', __import__('datetime').date.today().strftime('%d/%m/%Y'))
    }

    with open('clients.json', 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True})

# ── Supprimer un client ──
@app.route('/admin/clients/<client_id>', methods=['DELETE'])
def admin_delete_client(client_id):
    clients = load_clients()
    if client_id not in clients:
        return jsonify({'error': 'Client introuvable'}), 404
    
    del clients[client_id]
    with open('clients.json', 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

    # Supprimer le dossier documents
    dossier = f"documents/{client_id}"
    if os.path.exists(dossier):
        shutil.rmtree(dossier)

    return jsonify({'success': True})

# ── Uploader un document ──
@app.route('/admin/clients/<client_id>/documents', methods=['POST'])
def admin_upload_doc(client_id):
    clients = load_clients()
    if client_id not in clients:
        return jsonify({'error': 'Client introuvable'}), 404

    fichier = request.files.get('file')
    if not fichier:
        return jsonify({'error': 'Fichier manquant'}), 400

    dossier = f"documents/{client_id}"
    os.makedirs(dossier, exist_ok=True)
    chemin = f"{dossier}/{fichier.filename}"
    fichier.save(chemin)

    # Mettre à jour la liste des documents
    if fichier.filename not in clients[client_id].get('documents', []):
        clients[client_id].setdefault('documents', []).append(fichier.filename)
        with open('clients.json', 'w', encoding='utf-8') as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True, 'fichier': fichier.filename})

# ── Supprimer un document ──
@app.route('/admin/clients/<client_id>/documents/<doc_name>', methods=['DELETE'])
def admin_delete_doc(client_id, doc_name):
    clients = load_clients()
    if client_id not in clients:
        return jsonify({'error': 'Client introuvable'}), 404

    chemin = f"documents/{client_id}/{doc_name}"
    if os.path.exists(chemin):
        os.remove(chemin)

    clients[client_id]['documents'] = [
        d for d in clients[client_id].get('documents', []) if d != doc_name
    ]
    with open('clients.json', 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True})

# ── Lancer convert.py pour un client ──
@app.route('/admin/clients/<client_id>/convert', methods=['POST'])
def admin_convert(client_id):
    clients = load_clients()
    if client_id not in clients:
        return jsonify({'error': 'Client introuvable'}), 404

    try:
        from convert import convertir_docs_en_json
        result = convertir_docs_en_json(client_id)
        if result:
            nb = len(result.get('produits', []))
            return jsonify({'success': True, 'produits': nb})
        return jsonify({'error': 'Conversion échouée'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Stats ──
@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    clients = load_clients()
    return jsonify({
        'total_clients': len(clients),
        'clients_actifs': len([c for c in clients.values() if c.get('statut') == 'actif']),
        'total_messages': sum(c.get('messages', 0) for c in clients.values()),
        'total_documents': sum(len(c.get('documents', [])) for c in clients.values())
    })

# ── Routes statiques ──
@app.route('/')
def demo():
    return send_from_directory('.', 'demo.html')

@app.route('/widget.js')
def widget():
    return send_from_directory('.', 'widget.js')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
