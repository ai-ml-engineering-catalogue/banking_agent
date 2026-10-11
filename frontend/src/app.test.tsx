import {vi,test,expect,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {App,Login,Chatbot} from './main';
vi.mock('./api',()=>({api:vi.fn(),transcribe:vi.fn(),speech:vi.fn(),money:(n:number)=>'₹'+n}));
import {api,transcribe,speech} from './api';
beforeEach(()=>{cleanup();sessionStorage.clear();vi.mocked(api).mockReset();vi.mocked(transcribe).mockReset();vi.mocked(speech).mockReset()});
test('wrong credentials show error',async()=>{vi.mocked(api).mockRejectedValue(new Error('Username or password is incorrect.'));render(<MemoryRouter><Login/></MemoryRouter>);fireEvent.change(screen.getByLabelText('Username'),{target:{value:'aarav.sharma'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'wrong'}});fireEvent.click(screen.getByText('Sign in'));expect(await screen.findByRole('alert')).toHaveTextContent('incorrect');});
test('login saves token',async()=>{vi.mocked(api).mockResolvedValue({access_token:'demo'});render(<MemoryRouter><Login/></MemoryRouter>);fireEvent.change(screen.getByLabelText('Username'),{target:{value:'aarav.sharma'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'Aarav@123'}});fireEvent.click(screen.getByText('Sign in'));await waitFor(()=>expect(sessionStorage.getItem('token')).toBe('demo'));});
test('chat shows pending, answer and used tool',async()=>{let resolve:any;vi.mocked(api).mockReturnValue(new Promise(r=>resolve=r));render(<Chatbot/>);fireEvent.change(screen.getByLabelText('Your banking question'),{target:{value:'Show UPI'}});fireEvent.click(screen.getByLabelText('Send message'));expect(screen.getByRole('status')).toBeInTheDocument();resolve({answer:'You spent ₹642.00.',tools_used:[{name:'get_banking_transactions',args:{}}]});expect(await screen.findByText('You spent ₹642.00.')).toBeInTheDocument();expect(screen.getByText('get_banking_transactions')).toBeInTheDocument();fireEvent.click(screen.getByText('New chat'));expect(screen.queryByText('You spent ₹642.00.')).not.toBeInTheDocument();});
test('chat error visible',async()=>{vi.mocked(api).mockRejectedValue(new Error('Assistant unavailable'));render(<Chatbot/>);fireEvent.click(screen.getByText('Any offers on travel?'));expect(await screen.findByText('Assistant unavailable')).toBeInTheDocument();});

test("protected route redirects to login",()=>{render(<MemoryRouter initialEntries={["/"]}><App/></MemoryRouter>);expect(screen.getByText("Good to see you.")).toBeInTheDocument();});

test('chat forwards encrypted context and new chat clears it',async()=>{
 vi.mocked(api).mockResolvedValue({answer:'Answer one',tools_used:[],context_token:'encrypted-context'});
 render(<Chatbot/>);
 fireEvent.change(screen.getByLabelText('Your banking question'),{target:{value:'Show UPI'}});
 fireEvent.click(screen.getByLabelText('Send message'));
 await screen.findByText('Answer one');
 fireEvent.change(screen.getByLabelText('Your banking question'),{target:{value:'And last month?'}});
 fireEvent.click(screen.getByLabelText('Send message'));
 await waitFor(()=>expect(vi.mocked(api)).toHaveBeenLastCalledWith('/chat',expect.objectContaining({context_token:'encrypted-context'})));
 await waitFor(()=>expect(screen.getByText('New chat')).not.toBeDisabled());
 fireEvent.click(screen.getByText('New chat'));
 fireEvent.click(screen.getByText('Any offers on travel?'));
 await waitFor(()=>expect(vi.mocked(api)).toHaveBeenLastCalledWith('/chat',expect.objectContaining({context_token:undefined})));
});

class FakeRecorder{static isTypeSupported=(t:string)=>t==='audio/webm';state='inactive';mimeType='audio/webm';ondataavailable:any;onstop:any;constructor(public stream:any){}start(){this.state='recording'}stop(){this.state='inactive';this.ondataavailable({data:new Blob(['voice'],{type:'audio/webm'})});this.onstop()}}
const track={stop:vi.fn()};
function enableVoice(getUserMedia=vi.fn().mockResolvedValue({getTracks:()=>[track]})){
 vi.stubGlobal('MediaRecorder',FakeRecorder);
 Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia},configurable:true});
 URL.createObjectURL=vi.fn(()=>'blob:reply');URL.revokeObjectURL=vi.fn();
 vi.spyOn(HTMLMediaElement.prototype,'pause').mockImplementation(()=>{});
 return vi.spyOn(HTMLMediaElement.prototype,'play').mockResolvedValue(undefined);
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();delete (navigator as any).mediaDevices;});

test('voice question is transcribed, answered through chat and read aloud',async()=>{
 const play=enableVoice();
 vi.mocked(transcribe).mockResolvedValue('When is my credit card bill due?');
 vi.mocked(api).mockResolvedValue({answer:'Your bill is due on 5 Nov.',tools_used:[{name:'get_credit_card_transactions',args:{}}],context_token:'ctx'});
 vi.mocked(speech).mockResolvedValue(new Blob(['mp3'],{type:'audio/mpeg'}));
 render(<Chatbot/>);
 fireEvent.click(screen.getByLabelText('Ask by voice'));
 fireEvent.click(await screen.findByLabelText('Stop recording'));
 expect(await screen.findByText('Your bill is due on 5 Nov.')).toBeInTheDocument();
 expect(vi.mocked(transcribe).mock.calls[0][0].type).toBe('audio/webm');
 expect(vi.mocked(api)).toHaveBeenCalledWith('/chat',expect.objectContaining({message:'When is my credit card bill due?'}));
 expect(screen.getByText('Spoken question')).toBeInTheDocument();
 await waitFor(()=>expect(vi.mocked(speech)).toHaveBeenCalledWith('Your bill is due on 5 Nov.'));
 await waitFor(()=>expect(play).toHaveBeenCalled());
 expect(track.stop).toHaveBeenCalled();
 expect(await screen.findByLabelText('Stop reading aloud')).toBeInTheDocument();
});

test('typed answers are only read aloud on request and voice replies can be turned off',async()=>{
 enableVoice();
 vi.mocked(api).mockResolvedValue({answer:'Typed answer',tools_used:[]});
 vi.mocked(speech).mockResolvedValue(new Blob(['mp3']));
 vi.mocked(transcribe).mockResolvedValue('Any offers?');
 render(<Chatbot/>);
 fireEvent.click(screen.getByText('Any offers on travel?'));
 await screen.findByText('Typed answer');
 expect(vi.mocked(speech)).not.toHaveBeenCalled();
 fireEvent.click(screen.getByLabelText('Listen to this answer'));
 await waitFor(()=>expect(vi.mocked(speech)).toHaveBeenCalledTimes(1));
 fireEvent.click(screen.getByText(/Voice replies on/));
 fireEvent.click(screen.getByLabelText('Ask by voice'));
 fireEvent.click(await screen.findByLabelText('Stop recording'));
 await waitFor(()=>expect(screen.getAllByText('Typed answer')).toHaveLength(2));
 expect(vi.mocked(speech)).toHaveBeenCalledTimes(1);
});

test('blocked microphone and failed transcription show errors without sending',async()=>{
 enableVoice(vi.fn().mockRejectedValue(Object.assign(new Error('denied'),{name:'NotAllowedError'})));
 render(<Chatbot/>);
 fireEvent.click(screen.getByLabelText('Ask by voice'));
 expect(await screen.findByRole('alert')).toHaveTextContent('Microphone access is blocked');
 cleanup();
 enableVoice();
 vi.mocked(transcribe).mockRejectedValue(new Error('Voice is unavailable right now. You can still type your question.'));
 render(<Chatbot/>);
 fireEvent.click(screen.getByLabelText('Ask by voice'));
 fireEvent.click(await screen.findByLabelText('Stop recording'));
 expect(await screen.findByRole('alert')).toHaveTextContent('Voice is unavailable');
 expect(vi.mocked(api)).not.toHaveBeenCalled();
});

test('microphone is hidden when the browser cannot record',()=>{
 render(<Chatbot/>);
 expect(screen.queryByLabelText('Ask by voice')).not.toBeInTheDocument();
 expect(screen.getByLabelText('Your banking question')).toBeInTheDocument();
});
