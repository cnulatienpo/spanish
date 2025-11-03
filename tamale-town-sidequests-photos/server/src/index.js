
import express from 'express';
import cors from 'cors';
import { listSeederJSON, getSeederById } from './services/storage.js';

const app = express();
app.use(cors());
app.use(express.json());

const players = new Map();
function ensurePlayer(id='local'){
  if(!players.has(id)) players.set(id,{tamales:0,salsa:0,supplies:0,spanish_ratio:0.15});
  return players.get(id);
}

function normalizeAccents(text){
  let t = (text||'').trim();
  t = t.replace(/\bano(s)?\b/gi,'año$1');
  t = t.replace(/\bcomo estas\??/i,'¿Cómo estás?');
  return t;
}
function strip(s){
  return (s||'').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
    .replace(/[¿¡.,!?]/g,'').trim();
}
function simpleScore(user,target){
  const U = new Set(strip(user).split(' '));
  const T = strip(target).split(' ');
  let hit=0; for(const w of T){ if(U.has(w)) hit++; }
  return hit/Math.max(1,T.length);
}
function feedback(user,target){
  const sc = simpleScore(user,target);
  if(sc>0.9) return {code:'PERFECTO',message:'¡Así se habla!'};
  if(sc>0.6) return {code:'CLOSE',message:'Casi: ajusta un detalle.'};
  return {code:'NUDGE',message:'Probemos otra vez con una frase más simple.'};
}

app.get('/api/seeders', async (req,res)=>{
  try{ res.json({ results: await listSeederJSON('seeders/') }); }
  catch(e){ res.status(500).json({error:e.message}); }
});
app.get('/api/seeders/:id', async (req,res)=>{
  const s = await getSeederById(req.params.id,'seeders/');
  if(!s) return res.status(404).json({error:'not found'});
  res.json(s);
});
app.post('/api/nlp/normalize',(req,res)=> res.json({ text: normalizeAccents(req.body.text||'') }));
app.post('/api/nlp/grade',(req,res)=>{
  const { text, targets } = req.body||{};
  const target = (targets && targets[0]) || '';
  const fb = feedback(text||'', target);
  const sc = simpleScore(text||'', target);
  const p = ensurePlayer('local');
  if(fb.code==='PERFECTO') p.spanish_ratio = Math.min(1, p.spanish_ratio + 0.02);
  res.json({ score: sc, feedback: fb, spanish_ratio: p.spanish_ratio });
});
app.get('/api/player',(req,res)=> res.json({ id:'local', ...ensurePlayer('local') }));
app.post('/api/attempts',(req,res)=>{
  const p = ensurePlayer('local'); p.tamales+=25; p.salsa+=10; p.supplies+=10;
  res.json({ ok:true, player:p });
});

const PORT = process.env.PORT || 8787;
app.listen(PORT, ()=> console.log('API on http://localhost:'+PORT));
