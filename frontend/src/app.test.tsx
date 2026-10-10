import {vi,test,expect,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {App,Login,Chatbot} from './main';
vi.mock('./api',()=>({api:vi.fn(),money:(n:number)=>'₹'+n}));
import {api} from './api';
beforeEach(()=>{cleanup();sessionStorage.clear();vi.mocked(api).mockReset()});
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
