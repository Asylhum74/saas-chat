(function() {
  // ── Récupérer l'ID client depuis l'URL du script ──
  const scriptTag = document.currentScript;
  const urlParams = new URLSearchParams(scriptTag.src.split('?')[1] || '');
  const clientId  = urlParams.get('client');
  const apiBase   = scriptTag.src.split('/widget.js')[0];

  if (!clientId) { console.error('[ChatSaaS] Paramètre "client" manquant'); return; }

  // ── Récupérer la config du client depuis l'API ──
  fetch(`${apiBase}/client-config?client=${clientId}`)
    .then(r => r.json())
    .then(config => initWidget(config, apiBase))
    .catch(() => {
      // Fallback si pas d'API encore : config par défaut
      initWidget({
        nom:    'Assistant',
        titre:  'Besoin d\'aide ?',
        color1: '#6C63FF',
        color2: '#A78BFA',
      }, apiBase);
    });

  function initWidget(config, apiBase) {
    const color1 = config.color1 || '#6C63FF';
    const color2 = config.color2 || '#A78BFA';
    const titre  = config.titre  || 'Besoin d\'aide ?';
    const nom    = config.nom    || 'Assistant';

    // ── Injection CSS ──
    const style = document.createElement('style');
    style.textContent = `
      #chatsaas-widget * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

      #chatsaas-bubble {
        position: fixed; bottom: 24px; right: 24px;
        width: 56px; height: 56px; border-radius: 50%;
        background: linear-gradient(135deg, ${color1}, ${color2});
        box-shadow: 0 8px 32px rgba(0,0,0,.25);
        cursor: pointer; z-index: 9998;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; transition: transform .3s, box-shadow .3s;
        border: none;
      }
      #chatsaas-bubble:hover { transform: scale(1.08); box-shadow: 0 12px 40px rgba(0,0,0,.3); }
      #chatsaas-bubble.open { transform: scale(0.9); }

      #chatsaas-badge {
        position: fixed; bottom: 68px; right: 20px;
        background: #EF4444; color: #fff;
        width: 18px; height: 18px; border-radius: 50%;
        font-size: 11px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        z-index: 9999; display: none;
      }

      #chatsaas-window {
        position: fixed; bottom: 92px; right: 24px;
        width: 380px; height: 560px;
        background: #fff; border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,.2);
        display: flex; flex-direction: column;
        z-index: 9997; overflow: hidden;
        opacity: 0; pointer-events: none;
        transform: translateY(20px) scale(.95);
        transition: all .3s cubic-bezier(.34,1.56,.64,1);
      }
      #chatsaas-window.open {
        opacity: 1; pointer-events: all;
        transform: translateY(0) scale(1);
      }

      #chatsaas-header {
        background: linear-gradient(135deg, ${color1}, ${color2});
        padding: 16px 20px;
        display: flex; align-items: center; justify-content: space-between;
        flex-shrink: 0;
      }
      #chatsaas-header-left { display: flex; align-items: center; gap: 12px; }
      #chatsaas-avatar {
        width: 40px; height: 40px; border-radius: 50%;
        background: rgba(255,255,255,.25);
        display: flex; align-items: center; justify-content: center;
        font-size: 20px;
      }
      #chatsaas-header-info h3 { font-size: 15px; font-weight: 700; color: #fff; }
      #chatsaas-header-info p { font-size: 11px; color: rgba(255,255,255,.75); display: flex; align-items: center; gap: 4px; }
      #chatsaas-header-info p::before { content: '●'; font-size: 8px; color: #4ade80; }

      #chatsaas-close {
        background: rgba(255,255,255,.2); border: none;
        color: #fff; width: 28px; height: 28px; border-radius: 8px;
        cursor: pointer; font-size: 14px;
        display: flex; align-items: center; justify-content: center;
        transition: background .2s;
      }
      #chatsaas-close:hover { background: rgba(255,255,255,.3); }

      #chatsaas-messages {
        flex: 1; overflow-y: auto; padding: 20px;
        display: flex; flex-direction: column; gap: 12px;
        background: #F8F9FC;
        scrollbar-width: thin; scrollbar-color: #ddd transparent;
      }

      .cs-msg { display: flex; gap: 8px; animation: csFadeUp .3s ease; }
      .cs-msg.user { flex-direction: row-reverse; }

      @keyframes csFadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      .cs-msg-avatar {
        width: 28px; height: 28px; border-radius: 50%;
        background: linear-gradient(135deg, ${color1}, ${color2});
        display: flex; align-items: center; justify-content: center;
        font-size: 13px; flex-shrink: 0; margin-top: 2px;
      }
      .cs-msg.user .cs-msg-avatar { background: #E5E7EB; }

      .cs-msg-bubble {
        max-width: 75%; padding: 10px 14px;
        border-radius: 16px; font-size: 13px; line-height: 1.6;
        color: #1F2937;
        background: #fff;
        box-shadow: 0 1px 4px rgba(0,0,0,.08);
        border-top-left-radius: 4px;
      }
      .cs-msg.user .cs-msg-bubble {
        background: linear-gradient(135deg, ${color1}, ${color2});
        color: #fff; border-top-left-radius: 16px;
        border-top-right-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,.15);
      }

      .cs-typing { display: flex; gap: 4px; align-items: center; padding: 12px 14px; }
      .cs-typing span {
        width: 6px; height: 6px; border-radius: 50%;
        background: #9CA3AF; animation: csBounce 1.2s infinite ease-in-out;
      }
      .cs-typing span:nth-child(2) { animation-delay: .15s; }
      .cs-typing span:nth-child(3) { animation-delay: .3s; }
      @keyframes csBounce {
        0%,60%,100% { transform: translateY(0); opacity:.4; }
        30% { transform: translateY(-5px); opacity:1; }
      }

      #chatsaas-footer {
        padding: 12px 16px;
        background: #fff;
        border-top: 1px solid #F0F0F5;
        flex-shrink: 0;
      }

      #chatsaas-input-wrap {
        display: flex; gap: 8px; align-items: flex-end;
        background: #F3F4F6; border-radius: 14px;
        padding: 8px 8px 8px 14px;
        border: 1.5px solid transparent;
        transition: border-color .2s;
      }
      #chatsaas-input-wrap:focus-within { border-color: ${color1}; background: #fff; }

      #chatsaas-input {
        flex: 1; border: none; background: transparent;
        font-size: 13px; color: #1F2937;
        resize: none; outline: none; max-height: 80px;
        line-height: 1.5;
      }
      #chatsaas-input::placeholder { color: #9CA3AF; }

      #chatsaas-send {
        width: 34px; height: 34px; border-radius: 10px;
        background: linear-gradient(135deg, ${color1}, ${color2});
        border: none; color: #fff; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; flex-shrink: 0;
        transition: transform .2s, opacity .2s;
      }
      #chatsaas-send:hover:not(:disabled) { transform: scale(1.05); }
      #chatsaas-send:disabled { opacity: .4; cursor: not-allowed; }

      #chatsaas-hint {
        font-size: 10px; color: #9CA3AF; text-align: center;
        margin-top: 6px;
      }

      #chatsaas-welcome {
        text-align: center; padding: 20px 16px;
      }
      #chatsaas-welcome h4 { font-size: 15px; font-weight: 700; color: #1F2937; margin-bottom: 6px; }
      #chatsaas-welcome p { font-size: 12px; color: #6B7280; margin-bottom: 16px; line-height: 1.5; }
      .cs-suggestion {
        background: #fff; border: 1.5px solid #E5E7EB;
        border-radius: 10px; padding: 8px 12px;
        font-size: 12px; color: #374151; cursor: pointer;
        text-align: left; width: 100%; margin-bottom: 6px;
        transition: border-color .2s, background .2s;
      }
      .cs-suggestion:hover { border-color: ${color1}; background: #F5F3FF; }

      @media (max-width: 480px) {
        #chatsaas-window { width: calc(100vw - 16px); right: 8px; bottom: 80px; height: 70vh; }
        #chatsaas-bubble { bottom: 16px; right: 16px; }
      }
    `;
    document.head.appendChild(style);

    // ── HTML du widget ──
    const widget = document.createElement('div');
    widget.id = 'chatsaas-widget';
    widget.innerHTML = `
      <div id="chatsaas-badge"></div>

      <button id="chatsaas-bubble" aria-label="Ouvrir le chat">💬</button>

      <div id="chatsaas-window" role="dialog" aria-label="Chat assistant">
        <div id="chatsaas-header">
          <div id="chatsaas-header-left">
            <div id="chatsaas-avatar">🤖</div>
            <div id="chatsaas-header-info">
              <h3>${nom}</h3>
              <p>En ligne · répond en quelques secondes</p>
            </div>
          </div>
          <button id="chatsaas-close" aria-label="Fermer">✕</button>
        </div>

        <div id="chatsaas-messages">
          <div id="chatsaas-welcome">
            <h4>Bonjour ! 👋</h4>
            <p>Je suis l'assistant de <strong>${nom}</strong>. Comment puis-je vous aider ?</p>
            <button class="cs-suggestion" onclick="csUseSuggestion('Bonjour, j\\'ai une question')">💬 Poser une question</button>
            <button class="cs-suggestion" onclick="csUseSuggestion('Quels sont vos produits ?')">🛍️ Voir les produits</button>
            <button class="cs-suggestion" onclick="csUseSuggestion('J\\'ai besoin d\\'aide')">🆘 Obtenir de l\\'aide</button>
          </div>
        </div>

        <div id="chatsaas-footer">
          <div id="chatsaas-input-wrap">
            <textarea id="chatsaas-input" placeholder="Écrivez votre message…" rows="1"
              onkeydown="csHandleKey(event)" oninput="csAutoResize(this)"></textarea>
            <button id="chatsaas-send" onclick="csSend()" aria-label="Envoyer">➤</button>
          </div>
          <div id="chatsaas-hint">Propulsé par ChatSaaS</div>
        </div>
      </div>
    `;
    document.body.appendChild(widget);

    // ── State ──
    let isOpen = false;
    let history = [];
    let unread = 0;

    // ── Toggle ──
    document.getElementById('chatsaas-bubble').addEventListener('click', () => {
      isOpen = !isOpen;
      document.getElementById('chatsaas-window').classList.toggle('open', isOpen);
      document.getElementById('chatsaas-bubble').classList.toggle('open', isOpen);
      document.getElementById('chatsaas-bubble').textContent = isOpen ? '✕' : '💬';
      if (isOpen) {
        unread = 0;
        document.getElementById('chatsaas-badge').style.display = 'none';
        setTimeout(() => document.getElementById('chatsaas-input').focus(), 300);
      }
    });

    document.getElementById('chatsaas-close').addEventListener('click', () => {
      isOpen = false;
      document.getElementById('chatsaas-window').classList.remove('open');
      document.getElementById('chatsaas-bubble').classList.remove('open');
      document.getElementById('chatsaas-bubble').textContent = '💬';
    });

    // ── Send ──
    window.csSend = function() {
      const input = document.getElementById('chatsaas-input');
      const text = input.value.trim();
      if (!text) return;

      // Supprimer welcome screen
      const welcome = document.getElementById('chatsaas-welcome');
      if (welcome) welcome.remove();

      csAppendMessage('user', text);
      history.push({ role: 'user', content: text });
      input.value = '';
      csAutoResize(input);

      const typingId = csAppendTyping();

      fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, client: clientId })
      })
      .then(r => r.json())
      .then(data => {
        csRemoveTyping(typingId);
        const reply = data.content[0].text;
        // On garde tout l'historique enrichi renvoyé par le serveur
        if (data.messages) {
          history = data.messages;
        }
        history.push({ role: 'assistant', content: reply });
        csAppendMessage('assistant', reply);
        if (!isOpen) {
          unread++;
          const badge = document.getElementById('chatsaas-badge');
          badge.textContent = unread;
          badge.style.display = 'flex';
        }
      })
      .catch(() => {
        csRemoveTyping(typingId);
        csAppendMessage('assistant', 'Désolé, une erreur est survenue. Veuillez réessayer.');
      });
    };

    window.csUseSuggestion = function(text) {
      document.getElementById('chatsaas-input').value = text;
      csSend();
    };

    window.csHandleKey = function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); csSend(); }
    };

    window.csAutoResize = function(el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 80) + 'px';
    };

    function csAppendMessage(role, text) {
      const area = document.getElementById('chatsaas-messages');
      const div = document.createElement('div');
      div.className = `cs-msg ${role}`;
      const avatar = role === 'assistant' ? '🤖' : '👤';
      div.innerHTML = `
        <div class="cs-msg-avatar">${avatar}</div>
        <div class="cs-msg-bubble">${csFormat(text)}</div>`;
      area.appendChild(div);
      area.scrollTop = area.scrollHeight;
    }

    function csAppendTyping() {
      const area = document.getElementById('chatsaas-messages');
      const id = 'cs-typing-' + Date.now();
      const div = document.createElement('div');
      div.className = 'cs-msg assistant'; div.id = id;
      div.innerHTML = `
        <div class="cs-msg-avatar">🤖</div>
        <div class="cs-msg-bubble">
          <div class="cs-typing"><span></span><span></span><span></span></div>
        </div>`;
      area.appendChild(div);
      area.scrollTop = area.scrollHeight;
      return id;
    }

    function csRemoveTyping(id) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }

    function csFormat(text) {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    }
  }
})();
