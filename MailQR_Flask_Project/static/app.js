(() => {
const keys=["to","cc","bcc","subject","body"];
const $=id=>document.getElementById(id);
const form=$("emailForm"), qr=$("qrcode"), results=$("results");
function vals(){const v={};keys.forEach(k=>v[k]=$(k).value.trim());return v}
function mailto(v){const p=new URLSearchParams();if(v.cc)p.set("cc",v.cc);if(v.bcc)p.set("bcc",v.bcc);if(v.subject)p.set("subject",v.subject);if(v.body)p.set("body",v.body);return "mailto:"+v.to+(p.toString()?"?"+p.toString():"")}
function intent(v){const p=new URLSearchParams();p.set("to",v.to);if(v.cc)p.set("cc",v.cc);if(v.bcc)p.set("bcc",v.bcc);if(v.subject)p.set("subject",v.subject);if(v.body)p.set("body",v.body);return "intent://co?"+p.toString()+"#Intent;scheme=googlegmail;package=com.google.android.gm;end"}
function share(v){const u=new URL(location.origin+location.pathname);keys.forEach(k=>{if(v[k])u.searchParams.set(k,v[k])});return u.toString()}
form.addEventListener("submit",e=>{e.preventDefault();const v=vals();if(!v.to)return;qr.innerHTML="";const m=mailto(v),g=intent(v);
if(typeof QRCode==="undefined"){ $("status").textContent="QR library did not load. Check internet and reload.";return;}
new QRCode(qr,{text:m,width:230,height:230,colorDark:"#111827",colorLight:"#ffffff",correctLevel:QRCode.CorrectLevel.M});
$("shareUrl").value=share(v);$("gmailUrl").value=g;$("openGmail").href=g;$("openMail").href=m;results.hidden=false;$("status").textContent="QR and links generated. Test on your phone before sharing.";
});
$("clear").addEventListener("click",()=>{form.reset();qr.innerHTML="";results.hidden=true});
$("download").addEventListener("click",()=>{const c=qr.querySelector("canvas"),i=qr.querySelector("img"),src=c?c.toDataURL("image/png"):(i?i.src:"");if(!src)return;const a=document.createElement("a");a.href=src;a.download="mailqr.png";a.click()});
document.querySelectorAll("[data-copy]").forEach(b=>b.addEventListener("click",async()=>{const el=$(b.dataset.copy);try{await navigator.clipboard.writeText(el.value);$("status").textContent="Copied."}catch{el.select();document.execCommand("copy");$("status").textContent="Copy selected; copy manually if needed."}}));
if(keys.some(k=>$(k).value.trim()))setTimeout(()=>form.requestSubmit(),150);
})();
