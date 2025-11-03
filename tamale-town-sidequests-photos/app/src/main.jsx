
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
  const host = 'http://localhost:8787';
  const [p,setP] = useState({}); const [s,setS]=useState(null); const [img,setImg]=useState('/assets/locations/market_row_cartoon.png'); const [fb,setFb]=useState(null);
  useEffect(()=>{ fetch(host+'/api/player').then(r=>r.json()).then(setP) },[]);
  useEffect(()=>{ fetch(host+'/api/seeders').then(r=>r.json()).then(d=>{ const first=d.results?.find(x=>x.id==='stage00_greetings_01')||d.results?.[0]; if(first) pick(first.id); }) },[]);

  function pick(id){
    fetch(host+'/api/seeders/'+id).then(r=>r.json()).then(se=>{
      setS(se);
      setImg(
        se.visual_source==='photo_market_row' ? '/assets/locations/market_row_photo.jpg' :
        se.visual_source==='sepia_memory' ? '/assets/locations/market_row_sepia.jpg' :
        se.visual_source?.startsWith('photo_') ? `/assets/locations/user_${se.visual_source.split('photo_')[1]}.jpg` :
        se.visual_source==='psychedelic_carniceria' ? '/assets/locations/carniceria_psy.png' :
        '/assets/locations/market_row_cartoon.png'
      );
    })
  }

  async function answer(){
    const v = document.getElementById('ans').value;
    const norm = await fetch(host+'/api/nlp/normalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v})}).then(r=>r.json());
    const grade = await fetch(host+'/api/nlp/grade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:norm.text, targets:[s.dialogue?.[0]?.es||'']})}).then(r=>r.json());
    setFb(grade.feedback);
    const reward = await fetch(host+'/api/attempts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seeder_id:s.id,result: grade.score>0.6?'passed':'retry'})}).then(r=>r.json());
    setP(reward.player);
  }

  return <div className="app">
    <HUD p={p}/>
    <div className="scene"><img src={img} style={{maxWidth:'100%',border:'2px solid #333',borderRadius:8}}/></div>
    <div className="sidebar">
      <h3>{s?.title} <small>({s?.cefr})</small></h3>
      <div><b>NPC:</b> {s?.dialogue?.[0]?.npc}</div>
      <div style={{margin:'6px 0'}}><b>They say:</b> {s?.dialogue?.[0]?.es}</div>
      <input id="ans" placeholder="Your reply (Spanish/Spanglish)" style={{width:'100%',padding:8,background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:8}}/>
      <button className="btn" onClick={answer}>Answer</button>
      {fb && <p style={{marginTop:8}}><b>Feedback:</b> {fb.message} ({fb.code})</p>}
      <hr/>
      <button className="btn" onClick={()=>pick('sq_dia_de_los_muertos')}>Día de los Muertos</button>
      <button className="btn" style={{marginLeft:6}} onClick={()=>pick('sq_independence_parade')}>Independence Day Parade</button>
      <button className="btn" style={{marginLeft:6}} onClick={()=>pick('sq_la_virgen_miracle_booth')}>La Virgen</button>
      <div style={{marginTop:6}}>
        <button className="btn" onClick={()=>pick('sq_santa_muerte_midnight')}>Santa Muerte</button>
        <button className="btn" style={{marginLeft:6}} onClick={()=>pick('sq_anime_y_abuela_karaoke')}>Anime & Abuela</button>
        <button className="btn" style={{marginLeft:6}} onClick={()=>pick('sq_lowrider_blessing')}>Lowrider Blessing</button>
      </div>
    </div>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>)
