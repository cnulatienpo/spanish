
const { app, BrowserWindow } = require('electron');
function create(){
  const win = new BrowserWindow({width:1280,height:800});
  win.loadURL('http://localhost:5173').catch(()=> win.loadFile('../app/dist/index.html'));
}
app.whenReady().then(create);
app.on('window-all-closed',()=>{ if(process.platform!=='darwin') app.quit(); });
