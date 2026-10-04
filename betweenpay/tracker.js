(function(){
  const cfg=window.BETWEENPAY_CONFIG||{};
  const endpoint=(cfg.SUPABASE_URL||"https://lvqnwnzuqcxpdryppmpm.supabase.co")+"/functions/v1/betweenpay-track";
  const qs=new URLSearchParams(location.search);
  const get=(k)=>qs.get(k)||sessionStorage.getItem("bp_"+k)||"";
  ["utm_source","utm_medium","utm_campaign","utm_content"].forEach(k=>{const v=qs.get(k);if(v)sessionStorage.setItem("bp_"+k,v)});
  let sid=localStorage.getItem("bp_session_id");if(!sid){sid=(crypto.randomUUID?crypto.randomUUID():Date.now()+"-"+Math.random());localStorage.setItem("bp_session_id",sid)}
  window.bpTrack=function(event_name,metadata={}){
    const body={event_name,session_id:sid,path:location.pathname,source:get("utm_source"),medium:get("utm_medium"),campaign:get("utm_campaign"),content:get("utm_content"),referrer:document.referrer||"",metadata};
    fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",...(cfg.SUPABASE_PUBLISHABLE_KEY?{"apikey":cfg.SUPABASE_PUBLISHABLE_KEY}:{})},body:JSON.stringify(body),keepalive:true}).catch(()=>{});
  };
})();