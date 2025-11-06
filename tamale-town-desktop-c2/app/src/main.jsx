
import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'

const spanishLexicon = new Set([
  'hola','adios','gracias','por','para','porque','pero','tambien','muy','mas','menos',
  'si','no','yo','tu','usted','el','ella','nosotros','ustedes','ellos',
  'me','te','se','lo','la','los','las','le','les',
  'de','del','al','en','con','sin','sobre','entre','hasta','desde',
  'como','cuando','donde','quien','que','cual','cuanto',
  'ser','estar','tener','hacer','poder','ir','ven','venir','quiero','puedo','tengo',
  'bien','mal','mucho','poco','aqui','alli','hoy','ayer','manana',
  '¿','¡'
]);

function mixCefrDefaultMin(cefr){
  const c = String(cefr||'').toUpperCase();
  if(c==='A0') return 1;
  if(c==='A1') return 2;
  if(c==='A2') return 3;
  if(c==='B1') return 5;
  if(c==='B2') return 7;
  if(c==='C1') return 10;
  if(c==='C2') return 12;
  return 2;
}

function tokenize(str=''){
  let s = str.toLowerCase();
  const punct = '.,!?;:"()[]{}¿¡';
  for(const ch of punct){ s = s.split(ch).join(' '); }
  while(s.includes('  ')) s = s.replace(/  +/g,' ');
  s = s.trim();
  if(!s) return [];
  return s.split(' ');
}

function hasDiacritic(tok){
  return /[áéíóúñ]/.test(tok);
}

function buildExpectedSet(expected){
  const set = new Set();
  if(Array.isArray(expected)){
    for(const phrase of expected){
      for(const t of tokenize(phrase)) set.add(t);
    }
  }
  return set;
}

function isSpanishToken(tok, expectedSet){
  if(hasDiacritic(tok)) return true;
  if(tok==='¿' || tok==='¡') return true;
  if(expectedSet?.has(tok)) return true;
  if(spanishLexicon.has(tok)) return true;
  return false;
}

function countSpanishTokens(user, expected){
  const toks = tokenize(user);
  const set = buildExpectedSet(expected);
  let count = 0;
  for(const t of toks){ if(isSpanishToken(t,set)) count++; }
  return count;
}

function HUD({p}){
  return <div className="hud">
    <div className="meter">⭐ XP {p?.xp??0}</div>
    <div className="meter">🗣️ Mix {(p?.mix_ratio??0).toFixed(2)}</div>
  </div>
}

function App(){
  const [player,setPlayer] = useState({});
  const [seeder,setSeeder] = useState(null);
  const [fb,setFb] = useState(null);
  const [img,setImg] = useState('/assets/locations/market_row_cartoon.png');
  const [input,setInput] = useState('');
  const [score,setScore] = useState(null);
  const host = 'http://localhost:8787';

  useEffect(()=>{ fetch(host+'/api/player').then(r=>r.json()).then(setPlayer) },[]);
  useEffect(()=>{
    fetch(host+'/api/seeders').then(r=>r.json()).then(d=>{
      const s = d.results?.find(x=>x.id==='stage00_greetings_01') || d.results?.[0];
      if(s) select(s.id);
    });
  },[]);

  function select(id){
    fetch(host+'/api/seeders/'+id).then(r=>r.json()).then(s=>{
      setSeeder(s);
      setImg(
        s.visual_source==='photo_market_row' ? '/assets/locations/market_row_photo.jpg' :
        s.visual_source==='sepia_memory' ? '/assets/locations/market_row_sepia.jpg' :
        s.visual_source==='psychedelic_carniceria' ? '/assets/locations/carniceria_psy.png' :
        '/assets/locations/market_row_cartoon.png'
      );
      setInput('');
      setFb(null);
      setScore(null);
    });
  }

  const expected = useMemo(()=> seeder?.targets?.expected_spanish ?? [], [seeder]);
  const minTarget = useMemo(()=>{
    if(seeder?.mix && typeof seeder.mix.min_tokens === 'number') return seeder.mix.min_tokens;
    return mixCefrDefaultMin(seeder?.cefr);
  },[seeder]);
  const usedCount = useMemo(()=> countSpanishTokens(input, expected),[input, expected]);

  async function answer(){
    if(!seeder) return;
    const v = input;
    const norm = await fetch(host+'/api/nlp/normalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v})}).then(r=>r.json());
    const grade = await fetch(host+'/api/nlp/grade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:norm.text, seeder_id: seeder.id})}).then(r=>r.json());
    setFb(grade.feedback);
    setScore(grade.score);
    if(grade.player) setPlayer(grade.player);
    if(grade.score?.pass && grade.next_seeder){
      setSeeder(grade.next_seeder);
      setImg(
        grade.next_seeder.visual_source==='photo_market_row' ? '/assets/locations/market_row_photo.jpg' :
        grade.next_seeder.visual_source==='sepia_memory' ? '/assets/locations/market_row_sepia.jpg' :
        grade.next_seeder.visual_source==='psychedelic_carniceria' ? '/assets/locations/carniceria_psy.png' :
        '/assets/locations/market_row_cartoon.png'
      );
      setInput('');
      setScore(null);
    }
  }

  return <div className="app">
    <HUD p={player}/>
    <div className="scene"><img src={img} style={{maxWidth:'100%',border:'2px solid #333',borderRadius:8}}/></div>
    <div className="sidebar">
      <h3>{seeder?.title} <small>({seeder?.cefr})</small></h3>
      <div><b>NPC:</b> {seeder?.dialogue?.[0]?.npc}</div>
      <div style={{margin:'6px 0'}}><b>They say:</b> {seeder?.dialogue?.[0]?.es}</div>
      <div style={{margin:'8px 0 4px',fontSize:14,color:'#ccc'}}>
        Target: at least {minTarget} Spanish word{minTarget===1?'':'s'} · Used: {usedCount}
      </div>
      <textarea
        id="ans"
        value={input}
        onChange={e=>setInput(e.target.value)}
        placeholder="Your reply (Spanish/Spanglish)"
        style={{width:'100%',minHeight:80,padding:8,background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:8}}
      />
      <button onClick={answer} style={{marginTop:8,background:'#ff9a00',color:'#111',border:'none',padding:'8px 12px',borderRadius:8,fontWeight:700,cursor:'pointer'}}>Answer</button>
      {fb && <p style={{marginTop:8}}><b>Feedback:</b> {fb.message} ({fb.code})</p>}
      {score && !score.pass && <p style={{marginTop:4,color:'#aaa'}}>Need {score.need} more Spanish word{score.need===1?'':'s'}.</p>}
    </div>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>)
