// Automated-test fixture only. Never used by live demonstrations.
const http=require('node:http');
let mode='ok';
http.createServer(async(req,res)=>{
 if(req.url==='/control'&&req.method==='POST'){let body=req.body;if(!body){let b='';for await(const c of req)b+=c;body=JSON.parse(b);}mode=body.mode;res.end('{}');return;}
 if(req.url!=='/api/chat'||req.method!=='POST'){res.statusCode=501;res.end('Unsupported fixture endpoint');return;}
 let body=req.body;
 if(!body){let b='';for await(const c of req)b+=c;try{body=JSON.parse(b);}catch{res.statusCode=400;res.end('{}');return;}}
 if(!body.model||!body.messages||!body.format||body.stream!==false){res.statusCode=400;res.end(JSON.stringify({error:'Invalid request contract'}));return;}
 if(mode==='failure'){res.statusCode=503;res.setHeader('content-type','application/json');res.end(JSON.stringify({error:'fixture outage'}));return;}
 if(mode==='timeout'){await new Promise(r=>setTimeout(r,2500));}
 const content=mode==='malformed'?'not json':JSON.stringify({summary:'Fixture plan',classification:'test_fixture',milestones:['Fixture'],tasks:[],constraints:['Automated tests only']});
 res.setHeader('content-type','application/json');res.end(JSON.stringify({model:body.model,done:true,done_reason:'stop',message:{role:'assistant',content},prompt_eval_count:12,eval_count:15}));
}).listen(process.env.PORT);
