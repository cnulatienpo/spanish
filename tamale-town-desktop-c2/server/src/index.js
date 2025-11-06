
import express from 'express';
import cors from 'cors';
import { listSeederJSON, getSeederById } from './services/storage.js';
import { scoreLadder } from './services/scoring.js';

const app = express();
app.use(cors());
app.use(express.json());

// --- naïve player memory ---
const players = new Map();
function ensurePlayer(id='local'){
  if(!players.has(id)) players.set(id,{
    xp: 0,
    mix_ratio: 0.15,
    seen: []
  });
  return players.get(id);
}

// --- normalization & grading (dev-simplified) ---
function normalizeAccents(text){
  let t = (text||'').trim();
  t = t.replace(/\bano(s)?\b/gi,'año$1');
  t = t.replace(/\bcomo estas\??/i,'¿Cómo estás?');
  return t;
}
function formatFeedback(score){
  if(score.code === 'PERFECTO') return { code: 'PERFECTO', message: '¡Así se habla!' };
  if(score.code === 'CLOSE') return { code: 'CLOSE', message: 'Casi perfecto — ajusta un detalle.' };
  if(score.code === 'PASS') return { code: 'PASS', message: '¡Bien! Sigue mezclando español.' };
  if(score.code === 'ADD_ONE_MORE'){
    const need = score.need || 1;
    const plural = need === 1 ? 'palabra' : 'palabras';
    return { code: 'ADD_ONE_MORE', message: `Dame ${need} ${plural} más en español.` };
  }
  return { code: score.code, message: 'Sigue intentando.' };
}

// --- routes ---
app.get('/api/seeders', async (req,res)=>{
  try{
    const results = await listSeederJSON('seeders/');
    res.json({ results });
  }catch(e){ res.status(500).json({error:e.message}); }
});
app.get('/api/seeders/:id', async (req,res)=>{
  const id = req.params.id;
  const s = await getSeederById(id,'seeders/');
  if(!s) return res.status(404).json({error:'not found'});
  res.json(s);
});
app.post('/api/nlp/normalize',(req,res)=>{
  res.json({ text: normalizeAccents(req.body.text||'') });
});
app.post('/api/nlp/grade', async (req,res)=>{
  const { text='', seeder_id } = req.body||{};
  if(!seeder_id) return res.status(400).json({ error: 'seeder_id required' });
  const seeder = await getSeederById(seeder_id,'seeders/');
  if(!seeder) return res.status(404).json({ error: 'seeder not found' });

  const score = scoreLadder(text, seeder);
  const fb = formatFeedback(score);
  const player = ensurePlayer('local');

  if(score.pass){
    const rewards = seeder.rewards || {};
    const xp = Number(rewards.xp||0);
    player.xp += xp;
    if(!player.seen.includes(seeder.id)) player.seen.push(seeder.id);
    if(score.code === 'PERFECTO'){
      const bump = Number(rewards.mix_bump||0);
      player.mix_ratio = Math.min(1, Math.max(0, player.mix_ratio + bump));
    }
  }

  let nextSeeder = null;
  if(score.pass){
    const all = await listSeederJSON('seeders/');
    nextSeeder = all.find(s=>!player.seen.includes(s.id)) || (all.length>0 ? all[Math.floor(Math.random()*all.length)] : null);
  }

  res.json({
    score,
    feedback: fb,
    player: { id:'local', ...player },
    next_seeder: nextSeeder
  });
});
app.get('/api/player',(req,res)=> res.json({ id:'local', ...ensurePlayer('local') }));

const PORT = process.env.PORT || 8787;
app.listen(PORT, ()=> console.log('API on http://localhost:'+PORT));
