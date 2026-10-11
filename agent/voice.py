"""Speech-to-text and text-to-speech around the existing text assistant.

Voice never bypasses the agent: transcripts are sent through the normal chat
endpoint, and speech is synthesised from answers the agent already produced.
"""
import os
import re
from openai import AsyncOpenAI

MAX_AUDIO_BYTES=4*1024*1024  # Below Vercel's 4.5 MB request body limit.
MAX_SPEECH_CHARS=1500  # Keeps MP3 replies well below Vercel's response limit.
AUDIO_TYPES={'audio/webm':'webm','audio/ogg':'ogg','audio/mp4':'mp4','audio/x-m4a':'m4a','audio/mpeg':'mp3','audio/wav':'wav','audio/x-wav':'wav'}

class VoiceError(ValueError):
    pass

def client():
    if not os.getenv('OPENAI_API_KEY'): raise RuntimeError('Set OPENAI_API_KEY in .env to enable voice.')
    return AsyncOpenAI(timeout=45,max_retries=1)

def audio_extension(content_type):
    base=(content_type or '').split(';')[0].strip().lower()
    if base not in AUDIO_TYPES: raise VoiceError('Unsupported audio format. Record again in a supported browser.')
    return AUDIO_TYPES[base]

async def transcribe(audio, content_type):
    ext=audio_extension(content_type)
    if not audio: raise VoiceError('No audio received. Hold the microphone a little longer.')
    if len(audio)>MAX_AUDIO_BYTES: raise VoiceError('Recording is too long. Keep voice questions under a minute.')
    result=await client().audio.transcriptions.create(
        model=os.getenv('OPENAI_TRANSCRIBE_MODEL','gpt-4o-mini-transcribe'),
        file=(f'question.{ext}',audio,content_type.split(';')[0]),
        prompt='A customer asking a banking assistant about UPI, NEFT, IMPS, credit card dues, rupees and offers.',
    )
    return result.text.strip()[:2000]

def speech_text(markdown):
    """Turn a markdown answer into plain text that reads naturally aloud."""
    lines=[]
    for line in markdown.splitlines():
        line=line.strip()
        if re.fullmatch(r'\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?',line): continue  # table separator
        if line.startswith('|'): line=', '.join(c.strip() for c in line.strip('|').split('|') if c.strip())+'.'
        line=re.sub(r'^#{1,6}\s+|^[-*+]\s+|^>\s*','',line)
        line=re.sub(r'!?\[([^\]]*)\]\([^)]*\)',r'\1',line)
        line=re.sub(r'[*_`~]+','',line)
        if line: lines.append(line)
    text=re.sub(r'\s+',' ',' '.join(lines)).strip()
    if len(text)>MAX_SPEECH_CHARS:
        cut=text[:MAX_SPEECH_CHARS]
        end=max(cut.rfind('. '),cut.rfind('? '),cut.rfind('! '))
        text=(cut[:end+1] if end>MAX_SPEECH_CHARS//2 else cut)+' The full details are shown on screen.'
    return text

async def speak(answer):
    text=speech_text(answer)
    if not text: raise VoiceError('Nothing to read aloud.')
    model=os.getenv('OPENAI_TTS_MODEL','gpt-4o-mini-tts')
    style={'instructions':'Warm, clear and calm banking assistant voice with a neutral Indian English accent. Read ₹ amounts as rupees.'} if model.startswith('gpt-') else {}
    response=await client().audio.speech.create(model=model,voice=os.getenv('OPENAI_TTS_VOICE','alloy'),input=text,response_format='mp3',**style)
    return response.content
