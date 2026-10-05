(function(){
  const cfg=window.BETWEENPAY_CONFIG||{};
  const endpoint=(cfg.SUPABASE_URL||"https://lvqnwnzuqcxpdryppmpm.supabase.co")+"/functions/v1/betweenpay-track";
  const qs=new URLSearchParams(location.search);
  const keys=["utm_source","utm_medium","utm_campaign","utm_content","utm_term","ref","gclid","fbclid"];
  keys.forEach(k=>{
    const v=qs.get(k);
    if(v){
      sessionStorage.setItem("bp_"+k,v);
      localStorage.setItem("bp_last_"+k,v);
      if(!localStorage.getItem("bp_first_"+k))localStorage.setItem("bp_first_"+k,v);
    }
  });
  if(document.referrer){
    sessionStorage.setItem("bp_referrer",document.referrer);
    localStorage.setItem("bp_last_referrer",document.referrer);
    if(!localStorage.getItem("bp_first_referrer"))localStorage.setItem("bp_first_referrer",document.referrer);
  }
  let sid=localStorage.getItem("bp_session_id");
  if(!sid){sid=(crypto.randomUUID?crypto.randomUUID():Date.now()+"-"+Math.random());localStorage.setItem("bp_session_id",sid)}
  const get=k=>qs.get(k)||sessionStorage.getItem("bp_"+k)||localStorage.getItem("bp_last_"+k)||"";
  window.bpAttribution=function(){
    return {
      session_id:sid,
      source:get("utm_source"),medium:get("utm_medium"),campaign:get("utm_campaign"),content:get("utm_content"),term:get("utm_term"),
      ref:get("ref"),gclid:get("gclid"),fbclid:get("fbclid"),
      referrer:sessionStorage.getItem("bp_referrer")||localStorage.getItem("bp_last_referrer")||document.referrer||"",
      first_source:localStorage.getItem("bp_first_utm_source")||"",
      first_medium:localStorage.getItem("bp_first_utm_medium")||"",
      first_campaign:localStorage.getItem("bp_first_utm_campaign")||"",
      first_referrer:localStorage.getItem("bp_first_referrer")||""
    };
  };
  window.bpTrack=function(event_name,metadata={}){
    const a=window.bpAttribution();
    const body={event_name,session_id:sid,path:location.pathname,source:a.source,medium:a.medium,campaign:a.campaign,content:a.content,referrer:a.referrer,metadata:{referral_code:a.ref||null,term:a.term||null,gclid:a.gclid||null,fbclid:a.fbclid||null,first_source:a.first_source||null,first_medium:a.first_medium||null,first_campaign:a.first_campaign||null,first_referrer:a.first_referrer||null,...metadata}};
    fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json",...(cfg.SUPABASE_PUBLISHABLE_KEY?{"apikey":cfg.SUPABASE_PUBLISHABLE_KEY}:{})},body:JSON.stringify(body),keepalive:true}).catch(()=>{});
  };
})();