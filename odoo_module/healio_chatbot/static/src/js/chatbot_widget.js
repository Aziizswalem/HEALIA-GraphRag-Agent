/** @odoo-module **/

// Vanilla JS implementation compatible with Odoo 15
function mountHealiaChatbot() {
    const mountEl = document.getElementById("healio_chatbot_mount");
    if (!mountEl) return;
    if (mountEl.dataset.mounted) return;
    mountEl.dataset.mounted = "true";

    // Nettoyer l'ancien écouteur postMessage s'il existe (SPA navigation)
    if (mountEl._healioMessageListener) {
        window.removeEventListener('message', mountEl._healioMessageListener);
        delete mountEl._healioMessageListener;
    }

    const configUrl = mountEl.dataset.configUrl || "/healio/config/ui";
    
    // Remove loading spinner
    const loader = document.getElementById("healio_loading");
    if (loader) loader.remove();

    // Fetch config
    fetch(configUrl, { credentials: "same-origin" })
        .then(res => res.json())
        .then(config => {
            if (config.use_iframe && config.frontend_url) {
                // Iframe Mode — passe session_id + infos utilisateur en query params
                const url = new URL(config.frontend_url);
                if (config.active_session_id) {
                    url.searchParams.set('session_id', config.active_session_id);
                }
                if (config.user_name) {
                    url.searchParams.set('user_name', config.user_name);
                }
                if (config.user_email) {
                    url.searchParams.set('user_email', config.user_email);
                }
                if (config.user_id) {
                    url.searchParams.set('odoo_user_id', config.user_id);
                }
                mountEl.innerHTML = `
                    <div style="width:100%; height:100%; border-radius:8px; overflow:hidden;">
                        <iframe src="${url.toString()}" style="width:100%; height:100%; border:none;" allow="clipboard-write"></iframe>
                    </div>
                `;

                // Écouter les messages postMessage de l'iframe pour lier le session_id
                const iframeOrigin = new URL(config.frontend_url).origin;
                function onMessage(event) {
                    if (event.origin !== iframeOrigin) return;
                    if (!event.data || event.data.type !== 'healio_session_id') return;
                    const sid = event.data.session_id;
                    if (!sid) return;
                    fetch('/healio/session/link', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fastapi_session_id: sid }),
                        credentials: 'same-origin',
                    }).catch(err => console.warn('Healia: session link failed', err));
                }
                window.addEventListener('message', onMessage);
                // Nettoyer le listener si le widget est démonté
                mountEl._healioMessageListener = onMessage;
            } else {
                // Native Chat Mode (Simplified)
                mountEl.innerHTML = `
                    <div style="display:flex; flex-direction:column; height:100%; font-family:sans-serif; background:#f9f9fb; border-radius:8px; overflow:hidden; border:1px solid #ddd;">
                        <div style="background:#fff; padding:15px; border-bottom:1px solid #ddd; display:flex; align-items:center; gap:10px;">
                            <div style="font-size:24px;">🧠</div>
                            <div>
                                <h2 style="margin:0; font-size:16px;">Assistant IA Healia</h2>
                                <span style="font-size:12px; color:#666;">Posez vos questions sur les données de santé</span>
                            </div>
                        </div>
                        <div id="healio_chat_messages" style="flex:1; overflow-y:auto; padding:15px; display:flex; flex-direction:column; gap:10px;">
                            <div style="background:#e0e7ff; padding:10px 15px; border-radius:15px; align-self:flex-start; max-width:80%;">
                                Bonjour ! Je suis l'assistant IA Healia. Posez-moi une question !
                            </div>
                        </div>
                        <div style="padding:15px; background:#fff; border-top:1px solid #ddd; display:flex; gap:10px;">
                            <input type="text" id="healio_chat_input" placeholder="Posez votre question en français..." style="flex:1; padding:10px; border:1px solid #ccc; border-radius:20px; outline:none;" />
                            <button id="healio_chat_send" style="background:#4f46e5; color:#fff; border:none; padding:10px 20px; border-radius:20px; cursor:pointer;">Envoyer</button>
                        </div>
                    </div>
                `;

                const input = document.getElementById("healio_chat_input");
                const sendBtn = document.getElementById("healio_chat_send");
                const messagesDiv = document.getElementById("healio_chat_messages");
                const proxyUrl = mountEl.dataset.proxyUrl || "/healio/chat";

                function addMessage(text, isUser) {
                    const div = document.createElement("div");
                    div.style.padding = "10px 15px";
                    div.style.borderRadius = "15px";
                    div.style.maxWidth = "80%";
                    div.style.marginBottom = "10px";
                    if (isUser) {
                        div.style.background = "#4f46e5";
                        div.style.color = "#fff";
                        div.style.alignSelf = "flex-end";
                    } else {
                        div.style.background = "#e0e7ff";
                        div.style.color = "#000";
                        div.style.alignSelf = "flex-start";
                    }
                    div.innerText = text;
                    messagesDiv.appendChild(div);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }

                function sendMessage() {
                    const text = input.value.trim();
                    if (!text) return;
                    input.value = "";
                    addMessage(text, true);

                    const loadingDiv = document.createElement("div");
                    loadingDiv.innerText = "⏳ En réflexion...";
                    loadingDiv.style.alignSelf = "flex-start";
                    loadingDiv.style.color = "#666";
                    loadingDiv.style.fontSize = "12px";
                    messagesDiv.appendChild(loadingDiv);

                    fetch(proxyUrl, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ message: text })
                    })
                    .then(r => r.json())
                    .then(data => {
                        loadingDiv.remove();
                        addMessage(data.answer || "Pas de réponse", false);
                    })
                    .catch(err => {
                        loadingDiv.remove();
                        addMessage("❌ Erreur de connexion", false);
                    });
                }

                sendBtn.addEventListener("click", sendMessage);
                input.addEventListener("keypress", (e) => {
                    if (e.key === "Enter") sendMessage();
                });
            }
        })
        .catch(err => {
            mountEl.innerHTML = `<div style="padding:20px; color:red;">Erreur de chargement de la configuration: ${err.message}</div>`;
        });
}

// Odoo SPA Navigation Hook — wait for DOM to be ready
function _initHealiaObserver() {
    if (!document.body) {
        // Body not ready yet, retry shortly
        setTimeout(_initHealiaObserver, 100);
        return;
    }
    const observer = new MutationObserver(() => {
        mountHealiaChatbot();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Initial check
    setTimeout(mountHealiaChatbot, 500);
}
_initHealiaObserver();
