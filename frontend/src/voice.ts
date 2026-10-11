import {useEffect,useRef,useState} from 'react';
export const MAX_RECORDING_SECONDS=60;
// A silent clip played inside the tap gesture lets Safari autoplay the spoken reply later.
const SILENCE='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
const TYPES=['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg;codecs=opus'];
export const voiceSupported=()=>typeof MediaRecorder!=='undefined'&&!!navigator.mediaDevices?.getUserMedia;
function micError(e:unknown){
 const name=(e as DOMException)?.name;
 if(name==='NotAllowedError'||name==='SecurityError')return 'Microphone access is blocked. Allow it in your browser settings, or type your question.';
 if(name==='NotFoundError')return 'No microphone was found. You can type your question instead.';
 return 'Could not start recording. You can type your question instead.';
}
export function useRecorder(onAudio:(audio:Blob)=>void,onError:(message:string)=>void){
 const [recording,R]=useState(false);const [seconds,S]=useState(0);
 const recorder=useRef<MediaRecorder|null>(null);const timer=useRef<number|undefined>(undefined);const discard=useRef(false);
 const handlers=useRef({onAudio,onError});handlers.current={onAudio,onError};
 function release(){window.clearInterval(timer.current);recorder.current?.stream.getTracks().forEach(t=>t.stop());recorder.current=null;R(false);S(0);}
 function stop(){if(recorder.current?.state==='recording')recorder.current.stop();}
 async function start(){
  if(recorder.current)return;
  discard.current=false;
  try{
   const stream=await navigator.mediaDevices.getUserMedia({audio:true});
   const type=TYPES.find(t=>MediaRecorder.isTypeSupported?.(t));
   const r=new MediaRecorder(stream,type?{mimeType:type}:undefined);const chunks:Blob[]=[];
   r.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
   r.onstop=()=>{const audio=new Blob(chunks,{type:r.mimeType||type||'audio/webm'});release();if(!discard.current)handlers.current.onAudio(audio);};
   recorder.current=r;r.start();R(true);
   const began=Date.now();
   timer.current=window.setInterval(()=>{const s=Math.floor((Date.now()-began)/1000);S(s);if(s>=MAX_RECORDING_SECONDS)stop();},250);
  }catch(e){release();handlers.current.onError(micError(e));}
 }
 useEffect(()=>()=>{discard.current=true;stop();release();},[]);
 return {recording,seconds,start,stop};
}
export function usePlayer(){
 const player=useRef<HTMLAudioElement|null>(null);const urls=useRef(new Map<string,string>());
 const [playing,setPlaying]=useState<string|null>(null);const active=useRef<string|null>(null);
 const P=(id:string|null)=>{active.current=id;setPlaying(id);};const finish=(id:string)=>{if(active.current===id)P(null);};
 const audio=()=>player.current??=new Audio();
 function unlock(){const a=audio();if(!a.paused)return;a.src=SILENCE;a.play()?.catch(()=>{});}
 function stop(){const a=player.current;if(a){a.pause();a.onended=null;}P(null);}
 async function play(id:string,load:()=>Promise<Blob>){
  stop();P(id);
  try{
   let url=urls.current.get(id);
   if(!url){url=URL.createObjectURL(await load());urls.current.set(id,url);}
   const a=audio();if(active.current!==id)return;
   a.src=url;a.onended=()=>finish(id);
   await a.play();
  }catch(e){finish(id);throw e;}
 }
 function reset(){stop();urls.current.forEach(u=>URL.revokeObjectURL(u));urls.current.clear();}
 useEffect(()=>reset,[]);
 return {playing,play,stop,unlock,reset};
}
