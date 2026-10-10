export const money=(value:number)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(value);
export async function api(path:string,body?:unknown){
 const token=sessionStorage.getItem('token');
 const r=await fetch('/api'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})});
 if(r.status===401&&path!='/auth/login'){sessionStorage.removeItem('token');window.location.assign('/login');}
 if(!r.ok){const error=await r.json().catch(()=>null);throw new Error(r.status===401?'Username or password is incorrect.':error?.detail?.message|| (typeof error?.detail==='string'?error.detail:'Unable to load. Please try again.'));}
 return r.json();
}
