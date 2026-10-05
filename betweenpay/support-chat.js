(()=>{
  if(window.__betweenPayChatLoaded)return;
  window.__betweenPayChatLoaded=true;

  const API="https://lvqnwnzuqcxpdryppmpm.supabase.co/functions/v1/betweenpay-chat";
  const KEY="bp_support_chat_session";
  let sessionId=sessionStorage.getItem(KEY)||"";
  let started=false,internalNav=false,busy=false;

  const style=document.createElement("style");
  style.textContent=`
  #bpchat-launch{position:fixed;right:22px;bottom:22px;z-index:2147483000;border:0;border-radius:999px;background:linear-gradient(135deg,#06263a,#0a6970);color:#fff;box-shadow:0 14px 38px rgba(5,39,55,.28);padding:14px 18px;display:flex;align-items:center;gap:10px;font:800 14px/1.1 system-ui,-apple-system,Segoe UI,sans-serif;cursor:pointer}
  #bpchat-launch:hover{transform:translateY(-1px)}#bpchat-launch .dot{width:10px;height:10px;border-radius:50%;background:#7cf0d4;box-shadow:0 0 0 4px rgba(124,240,212,.14)}
  #bpchat-panel{position:fixed;right:22px;bottom:84px;width:min(390px,calc(100vw - 28px));height:min(620px,calc(100vh - 120px));z-index:2147483001;background:#fff;border:1px solid #d7e4e8;border-radius:24px;box-shadow:0 26px 70px rgba(5,34,50,.24);display:none;overflow:hidden;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#102f40}
  #bpchat-panel.open{display:flex;flex-direction:column}
  .bpchat-head{padding:16px 17px;background:linear-gradient(135deg,#06263a,#0b5f68);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:12px}
  .bpchat-title{display:flex;align-items:center;gap:10px}.bpchat-logo{width:36px;height:36px;border-radius:11px;background:linear-gradient(135deg,#0c6c77,#1ab8a2);display:grid;place-items:center;font-weight:950}.bpchat-title strong{display:block;font-size:15px}.bpchat-title small{display:block;color:#bde8e1;font-size:11px;margin-top:2px}
  .bpchat-close{border:0;background:rgba(255,255,255,.12);color:#fff;width:32px;height:32px;border-radius:10px;font-size:20px;cursor:pointer}
  .bpchat-log{flex:1;overflow:auto;padding:16px;background:#f6fafb;scroll-behavior:smooth}
  .bpmsg{display:flex;margin:0 0 11px}.bpmsg.user{justify-content:flex-end}.bpmsg .bubble{max-width:82%;padding:10px 12px;border-radius:15px;font-size:13px;line-height:1.45;white-space:pre-wrap}.bpmsg.bot .bubble{background:#fff;border:1px solid #dde8ec;border-bottom-left-radius:5px}.bpmsg.user .bubble{background:#0a4d5d;color:#fff;border-bottom-right-radius:5px}
  .bpchat-quick{display:flex;gap:7px;flex-wrap:wrap;margin:7px 0 13px}.bpchat-chip{border:1px solid #cfe0e5;background:#fff;border-radius:999px;padding:7px 9px;font:750 11px system-ui;color:#244c5a;cursor:pointer}.bpchat-chip:hover{background:#eef8f7}
  .bpchat-support-btn{display:inline-flex;border:1px solid #b9ddd6;background:#eaf8f4;color:#08766d;border-radius:10px;padding:8px 10px;font:850 11px system-ui;cursor:pointer;margin:2px 0 12px}
  .bpchat-compose{border-top:1px solid #dce7eb;padding:11px;background:#fff}.bpchat-row{display:flex;gap:8px}.bpchat-input{flex:1;border:1px solid #cbdbe1;border-radius:13px;padding:11px 12px;font:13px system-ui;outline:none}.bpchat-input:focus{border-color:#11978c;box-shadow:0 0 0 3px rgba(17,151,140,.10)}.bpchat-send{border:0;border-radius:12px;background:#062b40;color:#fff;padding:0 15px;font-weight:900;cursor:pointer}.bpchat-send:disabled{opacity:.55;cursor:wait}
  .bpchat-note{font-size:9.5px;color:#84969f;text-align:center;margin-top:7px;line-height:1.35}
  .bpchat-form{background:#fff;border:1px solid #d8e5e9;border-radius:15px;padding:12px;margin:8px 0 12px}.bpchat-form h4{margin:0 0 5px;font-size:13px}.bpchat-form p{margin:0 0 10px;color:#69808b;font-size:11px;line-height:1.4}.bpchat-form input,.bpchat-form textarea{width:100%;box-sizing:border-box;border:1px solid #cadbe0;border-radius:10px;padding:9px 10px;font:12px system-ui;margin-bottom:8px}.bpchat-form textarea{min-height:85px;resize:vertical}.bpchat-form-actions{display:flex;gap:7px}.bpchat-form-actions button{border:0;border-radius:9px;padding:8px 10px;font:800 11px system-ui;cursor:pointer}.bpchat-form-actions .submit{background:#07334a;color:#fff}.bpchat-form-actions .cancel{background:#edf3f5;color:#46606c}.bpchat-error{font-size:11px;color:#a12b38;margin:2px 0 8px}
  @media(max-width:560px){#bpchat-launch{right:14px;bottom:14px;padding:13px 15px}#bpchat-panel{right:7px;bottom:72px;width:calc(100vw - 14px);height:min(650px,calc(100vh - 86px));border-radius:20px}}
  `;
  document.head.appendChild(style);

  const launch=document.createElement("button");
  launch.id="bpchat-launch";launch.type="button";
  launch.innerHTML='<span class="dot"></span><span>Questions? Chat with us</span>';
  const panel=document.createElement("section");panel.id="bpchat-panel";panel.setAttribute("aria-label","BetweenPay Support Assistant");
  panel.innerHTML=`
    <div class="bpchat-head">
      <div class="bpchat-title"><div class="bpchat-logo">BP</div><div><strong>BetweenPay Support</strong><small>Automated assistant · No live agent</small></div></div>
      <button class="bpchat-close" type="button" aria-label="Close chat">×</button>
    </div>
    <div class="bpchat-log" id="bpchat-log"></div>
    <div class="bpchat-compose">
      <div class="bpchat-row"><input class="bpchat-input" id="bpchat-input" maxlength="1600" placeholder="Ask a question about BetweenPay…"><button class="bpchat-send" id="bpchat-send" type="button">Send</button></div>
      <div class="bpchat-note">Chats are saved for support and transcripts are emailed to BetweenPay Support.</div>
    </div>`;
  document.body.append(launch,panel);

  const log=panel.querySelector("#bpchat-log"),input=panel.querySelector("#bpchat-input"),send=panel.querySelector("#bpchat-send");
  function scroll(){log.scrollTop=log.scrollHeight}
  function msg(text,who="bot"){const row=document.createElement("div");row.className="bpmsg "+who;const b=document.createElement("div");b.className="bubble";b.textContent=text;row.appendChild(b);log.appendChild(row);scroll()}
  function quicks(){
    const d=document.createElement("div");d.className="bpchat-quick";
    ["What is BetweenPay?","How can I pay?","How do I sign in?","Is there a subscription?"].forEach(t=>{const b=document.createElement("button");b.className="bpchat-chip";b.type="button";b.textContent=t;b.onclick=()=>ask(t);d.appendChild(b)});
    log.appendChild(d);scroll();
  }
  function supportButton(prefill=""){
    const b=document.createElement("button");b.className="bpchat-support-btn";b.type="button";b.textContent="Send this to Support →";b.onclick=()=>showSupport(prefill);log.appendChild(b);scroll();
  }
  async function call(payload,keepalive=false){
    const r=await fetch(API,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),keepalive});
    let j={};try{j=await r.json()}catch{}
    if(!r.ok)throw new Error(j.error||"Support chat is temporarily unavailable.");
    return j;
  }
  async function start(){
    if(started&&sessionId)return;
    if(sessionId){started=true;msg("Welcome back. How can I help with BetweenPay?");quicks();return}
    try{
      const j=await call({action:"start",page_url:location.href.split("#")[0]});
      sessionId=j.session_id;sessionStorage.setItem(KEY,sessionId);started=true;msg(j.greeting);quicks();
    }catch(e){msg("The support assistant is temporarily unavailable. You can still use the Support page to send a message.");supportButton()}
  }
  async function ask(text){
    text=String(text||"").trim();if(!text||busy)return;
    msg(text,"user");input.value="";busy=true;send.disabled=true;
    try{
      if(!sessionId)await start();
      const j=await call({action:"message",session_id:sessionId,message:text});
      msg(j.reply||"I couldn't answer that.");
      if(j.needs_support)supportButton(text);
    }catch(e){msg(e.message||"Support chat is temporarily unavailable.");supportButton(text)}
    finally{busy=false;send.disabled=false;input.focus()}
  }
  function showSupport(prefill=""){
    if(log.querySelector(".bpchat-form"))return;
    const f=document.createElement("div");f.className="bpchat-form";
    f.innerHTML='<h4>Send to BetweenPay Support</h4><p>No live agent is connected. Send this conversation to support and receive a reply by email.</p><input class="sf-email" type="email" placeholder="Your email address"><input class="sf-subject" maxlength="160" placeholder="Subject"><textarea class="sf-message" maxlength="4000" placeholder="What do you need help with?"></textarea><div class="bpchat-error" style="display:none"></div><div class="bpchat-form-actions"><button class="submit" type="button">Send request</button><button class="cancel" type="button">Cancel</button></div>';
    f.querySelector(".sf-message").value=prefill||"";
    f.querySelector(".cancel").onclick=()=>f.remove();
    f.querySelector(".submit").onclick=async()=>{
      const email=f.querySelector(".sf-email").value.trim(),subject=f.querySelector(".sf-subject").value.trim(),message=f.querySelector(".sf-message").value.trim(),err=f.querySelector(".bpchat-error"),btn=f.querySelector(".submit");
      err.style.display="none";
      if(!email.includes("@")||subject.length<3||message.length<10){err.textContent="Please enter a valid email, subject and a little more detail.";err.style.display="block";return}
      btn.disabled=true;btn.textContent="Sending…";
      try{
        const j=await call({action:"support",session_id:sessionId,email,subject,message});
        f.remove();msg(j.message||"Your support request was sent.");
        sessionStorage.removeItem(KEY);
      }catch(e){err.textContent=e.message||"Could not send support request.";err.style.display="block";btn.disabled=false;btn.textContent="Send request"}
    };
    log.appendChild(f);scroll();
  }
  async function finalize(){
    if(!sessionId)return;
    const id=sessionId;sessionId="";started=false;sessionStorage.removeItem(KEY);
    try{await call({action:"finalize",session_id:id},true)}catch{}
  }

  launch.onclick=async()=>{panel.classList.add("open");launch.style.display="none";await start();setTimeout(()=>input.focus(),100)};
  panel.querySelector(".bpchat-close").onclick=async()=>{panel.classList.remove("open");launch.style.display="flex";await finalize();log.innerHTML=""};
  send.onclick=()=>ask(input.value);
  input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask(input.value)}});

  document.addEventListener("click",e=>{
    const a=e.target.closest&&e.target.closest("a[href]");if(!a)return;
    try{const u=new URL(a.href,location.href);if(u.origin===location.origin)internalNav=true}catch{}
  },true);
  window.addEventListener("pagehide",()=>{
    if(internalNav){internalNav=false;return}
    if(sessionId){
      const id=sessionId;sessionStorage.removeItem(KEY);
      fetch(API,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"finalize",session_id:id}),keepalive:true}).catch(()=>{});
    }
  });
})();