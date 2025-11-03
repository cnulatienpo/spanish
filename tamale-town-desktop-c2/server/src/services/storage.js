
import fs from 'fs';
import path from 'path';
import { S3Client, ListObjectsV2Command, GetObjectCommand } from '@aws-sdk/client-s3';
import dotenv from 'dotenv';
dotenv.config();

const DATA_DIR = path.resolve(process.cwd(), 'data');

const cfg = {
  source: process.env.SEEDER_SOURCE || 'local',
  endpoint: process.env.B2_ENDPOINT,
  region: process.env.B2_REGION,
  bucket: process.env.B2_BUCKET,
  keyId: process.env.B2_ACCESS_KEY_ID,
  keySecret: process.env.B2_SECRET_ACCESS_KEY
};

let s3 = null;
if (cfg.source === 'b2') {
  s3 = new S3Client({
    region: cfg.region,
    endpoint: cfg.endpoint,
    forcePathStyle: true,
    credentials: { accessKeyId: cfg.keyId || '', secretAccessKey: cfg.keySecret || '' }
  });
}

export async function listSeederJSON(prefix='seeders/') {
  if (cfg.source !== 'b2') {
    const base = path.join(DATA_DIR, 'seeders');
    const results = [];
    const walk = (p)=>{
      for(const f of fs.readdirSync(p)){
        const full = path.join(p,f);
        const stat = fs.statSync(full);
        if(stat.isDirectory()) walk(full);
        else if(f.endsWith('.json')){
          try{ results.push(JSON.parse(fs.readFileSync(full,'utf8'))); }catch{}
        }
      }
    };
    if(fs.existsSync(base)) walk(base);
    return results;
  }
  const out = [];
  const cmd = new ListObjectsV2Command({ Bucket: cfg.bucket, Prefix: prefix });
  const resp = await s3.send(cmd);
  if (!resp.Contents) return out;
  for (const obj of resp.Contents) {
    if (!obj.Key.endsWith('.json')) continue;
    const get = new GetObjectCommand({ Bucket: cfg.bucket, Key: obj.Key });
    const data = await s3.send(get);
    const body = await streamToString(data.Body);
    try { out.push(JSON.parse(body)); } catch {}
  }
  return out;
}

export async function getSeederById(id, prefix='seeders/') {
  if (cfg.source !== 'b2') {
    const base = path.join(DATA_DIR, 'seeders');
    const found = findLocal(base, id);
    return found;
  }
  const all = await listSeederJSON(prefix);
  return all.find(s => s.id === id) || null;
}

function findLocal(p, id){
  if(!fs.existsSync(p)) return null;
  for(const f of fs.readdirSync(p)){
    const full = path.join(p,f);
    const stat = fs.statSync(full);
    if(stat.isDirectory()){ const v = findLocal(full, id); if(v) return v; }
    else if(f.endsWith('.json')){
      try{ const j = JSON.parse(fs.readFileSync(full,'utf8')); if(j.id===id) return j; }catch{}
    }
  }
  return null;
}

async function streamToString(stream) {
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}
