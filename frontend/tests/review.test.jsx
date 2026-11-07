import React from "react";
import {render,screen,fireEvent,waitFor,cleanup} from "@testing-library/react";
import {MemoryRouter,Routes,Route} from "react-router-dom";
import {afterEach,it,expect,vi} from "vitest";
vi.mock('../src/api',()=>({api:{post:vi.fn()},errorText:e=>e.message,label:s=>s}));
import {api} from '../src/api';
import ReviewInput,{validateReviewFiles} from '../src/components/ReviewInput';
import ReviewFinding from '../src/components/ReviewFinding';
afterEach(()=>{cleanup();vi.resetAllMocks();});
it('rejects unsafe paths, duplicate paths, binary content and oversized UTF-8 source',()=>{
  for (const files of [
    [{path:'../app.js',content:'x'}], [{path:'app.js',content:'\0'}],
    [{path:'app.js',content:'é'.repeat(50001)}],
    [{path:'app.js',content:'x'},{path:'APP.js',content:'y'}],
    [{path:'.env',content:'secret'}],
  ]) expect(()=>validateReviewFiles(files)).toThrow();
  expect(validateReviewFiles([{path:'src/app.js',content:'const x = 1;'}])).toHaveLength(1);
});
it('saves pasted source into a new workspace and starts review without code execution',async()=>{
  api.post.mockResolvedValueOnce({data:{id:'new-review',revision:1}})
    .mockResolvedValueOnce({data:{id:'source-approval',artifact_hash:'hash'}})
    .mockResolvedValueOnce({data:{status:'approved'}}).mockResolvedValueOnce({data:{status:'queued'}});
  render(<MemoryRouter initialEntries={['/review']}><Routes><Route path='/review' element={<ReviewInput/>}/><Route path='/projects/:id' element={<p>Review workspace opened</p>}/></Routes></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Source code'),{target:{value:'function add(a,b) { return a-b; }'}});
  fireEvent.click(screen.getByRole('button',{name:'Save & review code'}));
  await screen.findByText('Review workspace opened');
  expect(api.post.mock.calls[1][1].files[0].content).toContain('a-b');
  expect(api.post.mock.calls[3]).toEqual(['/projects/new-review/execute',expect.objectContaining({workflow_type:'quick_review'})]);
  expect(api.post.mock.calls.some(([url])=>url.includes('run-tests'))).toBe(false);
});
it('validates uploaded sources before creating a project',async()=>{
  render(<MemoryRouter><ReviewInput/></MemoryRouter>);
  fireEvent.click(screen.getByRole('tab',{name:'Upload files'}));
  const file=new File(['binary'], 'archive.zip',{type:'application/zip'});
  file.text=()=>Promise.resolve('binary');
  fireEvent.change(screen.getByLabelText('Choose source files'),{target:{files:[file]}});
  await screen.findByRole('alert');
  expect(api.post).not.toHaveBeenCalled();
});
it('shows a replacement and copies it without changing source',async()=>{
  const writeText=vi.fn().mockResolvedValue();
  Object.defineProperty(navigator,'clipboard',{value:{writeText},configurable:true});
  render(<ReviewFinding finding={{id:'f',file_path:'app.js',line_number:1,severity:'high',issue_description:'Incorrect addition',suggested_fix:'Replace add',improved_code:'function add(a,b) { return a+b; }',evidence_status:'ai_hypothesis',issue_type:'correctness'}} source={{file_content:'function add(a,b) { return a-b; }'}}/>);
  expect(screen.getByText('Suggested replacement code')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Copy code'}));
  await waitFor(()=>expect(writeText).toHaveBeenCalledWith('function add(a,b) { return a+b; }'));
  expect(api.post).not.toHaveBeenCalled();
});
