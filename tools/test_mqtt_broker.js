// Broker MQTT 3.1.1 tối giản qua WebSocket (chỉ để kiểm thử)
const http=require('http'),crypto=require('crypto');
const clients=new Set();
function frame(buf){const n=buf.length;let h;if(n<126)h=Buffer.from([0x82,n]);else if(n<65536){h=Buffer.alloc(4);h[0]=0x82;h[1]=126;h.writeUInt16BE(n,2)}else{h=Buffer.alloc(10);h[0]=0x82;h[1]=127;h.writeBigUInt64BE(BigInt(n),2)}return Buffer.concat([h,buf])}
function str(b,o){const l=b.readUInt16BE(o);return[b.slice(o+2,o+2+l).toString(),o+2+l]}
function match(f,t){const fa=f.split('/'),ta=t.split('/');for(let i=0;i<fa.length;i++){if(fa[i]==='#')return true;if(fa[i]!=='+'&&fa[i]!==ta[i])return false}return fa.length===ta.length}
function pub(topic,payload){const tb=Buffer.from(topic);const body=Buffer.concat([Buffer.from([tb.length>>8,tb.length&255]),tb,payload]);const len=[];let x=body.length;do{let d=x%128;x=Math.floor(x/128);if(x)d|=128;len.push(d)}while(x);return Buffer.concat([Buffer.from([0x30,...len]),body])}
function deliver(topic,payload){for(const c of clients)if(c.subs.some(f=>match(f,topic)))c.send(pub(topic,payload))}
function onPacket(c,type,flags,b){
  if(type===1){let o=0;[,o]=str(b,o);o+=1;const fl=b[o++];o+=2;let cid;[cid,o]=str(b,o);if(fl&4){let wt,wm;[wt,o]=str(b,o);[wm,o]=str(b,o);c.will=[wt,Buffer.from(wm)]}c.send(Buffer.from([0x20,2,0,0]));console.log('CONNECT',cid)}
  else if(type===8){const pid=b.readUInt16BE(0);let o=2;while(o<b.length){let f;[f,o]=str(b,o);o++;c.subs.push(f)}c.send(Buffer.from([0x90,3,pid>>8,pid&255,0]))}
  else if(type===3){let o=0,t;[t,o]=str(b,o);if((flags>>1)&3)o+=2;deliver(t,b.slice(o))}
  else if(type===12)c.send(Buffer.from([0xD0,0]));
  else if(type===14){c.will=null;c.sock.end()}
}
const srv=http.createServer();
srv.on('upgrade',(req,sock)=>{
  const key=crypto.createHash('sha1').update(req.headers['sec-websocket-key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${key}\r\nSec-WebSocket-Protocol: mqtt\r\n\r\n`);
  const c={sock,subs:[],will:null,send:b=>{try{sock.write(frame(b))}catch{}}};clients.add(c);
  let wbuf=Buffer.alloc(0),mbuf=Buffer.alloc(0);
  sock.on('data',d=>{wbuf=Buffer.concat([wbuf,d]);
    while(wbuf.length>=2){let len=wbuf[1]&127,o=2;if(len===126){len=wbuf.readUInt16BE(2);o=4}else if(len===127){len=Number(wbuf.readBigUInt64BE(2));o=10}
      const mask=wbuf[1]&128;if(wbuf.length<o+(mask?4:0)+len)break;const mk=mask?wbuf.slice(o,o+4):null;o+=mask?4:0;
      const p=Buffer.from(wbuf.slice(o,o+len));if(mk)for(let i=0;i<p.length;i++)p[i]^=mk[i&3];const op=wbuf[0]&15;wbuf=wbuf.slice(o+len);
      if(op===8){sock.end();return}if(op!==2&&op!==0)continue;mbuf=Buffer.concat([mbuf,p]);
      while(mbuf.length>=2){let mul=1,L=0,j=1,dd;do{dd=mbuf[j++];L+=(dd&127)*mul;mul*=128}while(dd&128&&j<mbuf.length);if(mbuf.length<j+L)break;onPacket(c,mbuf[0]>>4,mbuf[0]&15,mbuf.slice(j,j+L));mbuf=mbuf.slice(j+L)}}
  });
  const bye=()=>{if(!clients.has(c))return;clients.delete(c);if(c.will)deliver(c.will[0],c.will[1])};sock.on('close',bye);sock.on('error',bye);
});
srv.listen(8769,()=>console.log('broker 8769'));
