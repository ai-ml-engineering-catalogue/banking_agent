from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from common.auth import create_token
from backend.app.main import app
from agent import voice

client=TestClient(app)
headers={'Authorization':'Bearer '+create_token(1)}

class FakeOpenAI:
    def __init__(self):
        self.calls=[]
        async def transcription(**kwargs):
            self.calls.append(('transcribe',kwargs)); return SimpleNamespace(text='  Show my last 5 UPI payments ')
        async def speech(**kwargs):
            self.calls.append(('speak',kwargs)); return SimpleNamespace(content=b'ID3-mp3')
        self.audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcription),speech=SimpleNamespace(create=speech))

@pytest.fixture
def openai(monkeypatch):
    fake=FakeOpenAI()
    monkeypatch.setattr(voice,'client',lambda: fake)
    return fake

def test_voice_requires_authentication(openai):
    assert client.post('/api/voice/transcribe',content=b'abc',headers={'Content-Type':'audio/webm'}).status_code==401
    assert client.post('/api/voice/speak',json={'text':'hi'}).status_code==401
    assert client.post('/api/voice/speak',json={'text':'hi'},headers={'Authorization':'Bearer broken'}).status_code==401
    assert openai.calls==[]

def test_transcribe_sends_audio_to_openai(openai):
    r=client.post('/api/voice/transcribe',content=b'webm-bytes',headers={**headers,'Content-Type':'audio/webm;codecs=opus'})
    assert r.status_code==200 and r.json()=={'text':'Show my last 5 UPI payments'}
    kind,kwargs=openai.calls[0]
    assert kind=='transcribe' and kwargs['file']==('question.webm',b'webm-bytes','audio/webm')
    assert kwargs['model']=='gpt-4o-mini-transcribe'
    client.post('/api/voice/transcribe',content=b'm4a',headers={**headers,'Content-Type':'audio/mp4'})
    assert openai.calls[1][1]['file'][0]=='question.mp4'

def test_transcribe_validates_format_and_size(openai,monkeypatch):
    assert client.post('/api/voice/transcribe',content=b'x',headers={**headers,'Content-Type':'text/plain'}).status_code==422
    assert client.post('/api/voice/transcribe',content=b'',headers={**headers,'Content-Type':'audio/webm'}).status_code==422
    monkeypatch.setattr(voice,'MAX_AUDIO_BYTES',10)
    assert client.post('/api/voice/transcribe',content=b'x'*11,headers={**headers,'Content-Type':'audio/webm'}).status_code==413
    assert openai.calls==[]

def test_speak_returns_mp3_of_plain_text(openai):
    r=client.post('/api/voice/speak',json={'text':'## Summary\n**Total:** ₹642.00\n\n| Merchant | Amount |\n|---|---:|\n| Swiggy | ₹642.00 |\n- [Offer](http://x) `CODE`'},headers=headers)
    assert r.status_code==200 and r.headers['content-type']=='audio/mpeg' and r.content==b'ID3-mp3'
    kwargs=openai.calls[0][1]
    assert kwargs['input']=='Summary Total: ₹642.00 Merchant, Amount. Swiggy, ₹642.00. Offer CODE'
    assert kwargs['model']=='gpt-4o-mini-tts' and kwargs['response_format']=='mp3' and 'instructions' in kwargs
    assert client.post('/api/voice/speak',json={'text':'| --- |'},headers=headers).status_code==422

def test_speech_is_bounded_for_serverless_responses():
    text=voice.speech_text('Your spending was high. '*200)
    assert len(text)<=voice.MAX_SPEECH_CHARS+60 and text.endswith('The full details are shown on screen.')

def test_voice_errors_are_friendly(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=client.post('/api/voice/speak',json={'text':'hello'},headers=headers)
    assert r.status_code==502 and r.json()['detail']['error']=='VOICE_UNAVAILABLE'
    r=client.post('/api/voice/transcribe',content=b'a',headers={**headers,'Content-Type':'audio/webm'})
    assert r.status_code==502

def test_voice_routes_in_vercel_entrypoint(openai,monkeypatch,database):
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('JWT_SECRET','test-only-vercel-secret-with-at-least-32-characters')
    from main import app as vercel_app
    hosted=TestClient(vercel_app)
    auth={'Authorization':'Bearer '+create_token(1)}
    assert hosted.post('/api/voice/transcribe',content=b'ogg',headers={**auth,'Content-Type':'audio/ogg'}).json()['text']=='Show my last 5 UPI payments'
    assert hosted.post('/api/voice/speak',json={'text':'Hello'},headers=auth).content==b'ID3-mp3'
