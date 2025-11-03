
import express from 'express'; import cors from 'cors'; import fs from 'fs'; import path from 'path';
const app = express(); app.use(cors()); app.use(express.json());
const DATA = path.resolve(process.cwd(),'data/seeders');
function list(){ const out=[]; const w=(p)=>{ for(const f of fs.readdirSync(p)){ const full=path.join(p,f);
 const s=fs.statSync(full); if(s.isDirectory()) w(full); else if(f.endsWith('.json')) out.push(JSON.parse(fs.readFileSync(full,'utf8')));} };
 w(DATA); return out; }
function find(id){ const all=list(); return all.find(x=>x.id===id)||null; }
app.get('/api/seeders',(req,res)=> res.json({results:list()}));
app.get('/api/seeders/:id',(req,res)=>{ const s=find(req.params.id); if(!s)return res.status(404).json({error:'not found'}); res.json(s);});
app.post('/api/nlp/normalize',(req,res)=> res.json({text:(req.body.text||'').replace(/\bano\b/g,'año')}));
app.post('/api/nlp/grade',(req,res)=> res.json({score:1,feedback:{code:'PERFECTO',message:'¡Así se habla!'}}));
app.get('/api/player',(req,res)=> res.json({tamales:0,salsa:0,supplies:0,spanish_ratio:0.2}));
app.post('/api/attempts',(req,res)=> res.json({ok:true,player:{tamales:25,salsa:10,supplies:10,spanish_ratio:0.22}}));
app.listen(8787, ()=> console.log('API http://localhost:8787'));
