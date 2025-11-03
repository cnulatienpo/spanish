
import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'

function HUD({p}){
  return <div className="hud">
    <div className="meter">🌽 {p?.tamales??0}</div>
    <div className="meter">🌶 {p?.salsa??0}</div>
    <div className="meter">🧺 {p?.supplies??0}</div>
    <div className="meter">🗣️ ES {(p?.spanish_ratio??0).toFixed(2)}</div>
  </div>
}

function App(){
  const [player,setPlayer] = useState({});
  const [seeder,setSeeder] = useState(null);
  const [fb,setFb] = useState(null);
  const [img,setImg] = useState('/assets/locations/market_row_cartoon.png');
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
    });
  }

  async function answer(){
    const v = document.getElementById('ans').value;
    const norm = await fetch(host+'/api/nlp/normalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v})}).then(r=>r.json());
    const grade = await fetch(host+'/api/nlp/grade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:norm.text, targets:[seeder.dialogue?.[0]?.es||'']})}).then(r=>r.json());
    setFb(grade.feedback);
    const reward = await fetch(host+'/api/attempts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seeder_id:seeder.id,result: grade.score>0.6?'passed':'retry'})}).then(r=>r.json());
    setPlayer(reward.player);
  }

  return <div className="app">
    <HUD p={player}/>
    <div className="scene"><img src={img} style={{maxWidth:'100%',border:'2px solid #333',borderRadius:8}}/></div>
    <div className="sidebar">
      <h3>{seeder?.title} <small>({seeder?.cefr})</small></h3>
      <div><b>NPC:</b> {seeder?.dialogue?.[0]?.npc}</div>
      <div style={{margin:'6px 0'}}><b>They say:</b> {seeder?.dialogue?.[0]?.es}</div>
      <input id="ans" placeholder="Your reply (Spanish/Spanglish)" style={{width:'100%',padding:8,background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:8}}/>
      <button onClick={answer} style={{marginTop:8,background:'#ff9a00',color:'#111',border:'none',padding:'8px 12px',borderRadius:8,fontWeight:700,cursor:'pointer'}}>Answer</button>
      {fb && <p style={{marginTop:8}}><b>Feedback:</b> {fb.message} ({fb.code})</p>}
    </div>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>)
