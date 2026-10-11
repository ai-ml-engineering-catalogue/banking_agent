export const money=(value:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(value);
async function request(path:string,init:RequestInit){
 const token=sessionStorage.getItem('token');
 const r=await fetch('/api'+path,{...init,headers:{...init.headers as Record<string,string>,...(token?{Authorization:'Bearer '+token}:{})}});
 if(r.status===401&&path!='/auth/login'){sessionStorage.removeItem('token');window.location.assign('/login');}
 if(!r.ok){const error=await r.json().catch(()=>null);throw new Error(r.status===401?'Username or password is incorrect.':error?.detail?.message|| (typeof error?.detail==='string'?error.detail:'Unable to load. Please try again.'));}
 return r;
}
export async function api(path:string,body?:unknown){
 return (await request(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})})).json();
}
export async function transcribe(audio:Blob):Promise<string>{
 return (await (await request('/voice/transcribe',{method:'POST',headers:{'Content-Type':audio.type||'audio/webm'},body:audio})).json()).text;
}
export async function speech(text:string):Promise<Blob>{
 return (await request('/voice/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})).blob();
}
