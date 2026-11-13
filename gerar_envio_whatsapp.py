"""Prepara o envio diário dos painéis dos RCAs por WhatsApp (botões, sem API).

Uso: python3 gerar_envio_whatsapp.py <pasta ou zip com painel_RCA_*_<data>.html> <pasta do repositório> [AAAA-MM-DD]

1. Cada painel de RCA vai para <repo>/rca/<token>/index.html, compactado e criptografado (AES-GCM, chave
   PBKDF2 da senha do RCA). O endereço é fixo por RCA (o mesmo link todo dia) e o conteúdo só abre com a senha.
   O navegador do RCA guarda a senha depois da primeira vez.
2. Gera a página de envio do Yghor: um botão por RCA que abre o WhatsApp com a mensagem e o link prontos,
   um botão para mandar a senha (primeira vez) e botões para compartilhar a imagem dos rankings.
   - <repo>/envio/<token>/index.html: criptografada com a senha do Yghor (para abrir no celular).
   - privado/envio_whatsapp_<data>.html: sem senha, fica só na pasta privada (fora do git).
Tokens, senhas e telefones ficam em privado/whatsapp_rcas.json (fora do git). Telefone vazio = o WhatsApp pede o contato.
"""
import base64
import gzip
import html
import io
import json
import os
import re
import secrets
import sys
import zipfile
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'privado' / 'whatsapp_rcas.json'
SITE = 'https://gehlen-gif.github.io/acompanhamento-boped/'
ITER = 250_000
ALFA = 'abcdefghjkmnpqrstuvwxyz23456789'


def nova_senha():
    return '-'.join(''.join(secrets.choice(ALFA) for _ in range(4)) for _ in range(3))


def cifrar(conteudo: bytes, senha: str) -> dict:
    sal, iv = os.urandom(16), os.urandom(12)
    chave = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITER).derive(senha.encode())
    dado = AESGCM(chave).encrypt(iv, gzip.compress(conteudo, 9), None)
    b = lambda x: base64.b64encode(x).decode()
    return {'s': b(sal), 'i': b(iv), 'n': ITER, 'd': b(dado)}


CASCA = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>__TITULO__</title><style>
:root{--bg:#f4f6fa;--card:#fff;--tx:#1b2330;--mu:#5d6878;--ac:#1f6feb;--er:#c62828}
@media (prefers-color-scheme:dark){:root{--bg:#11151c;--card:#1b212b;--tx:#e6ebf2;--mu:#9aa6b6;--ac:#5b9bff;--er:#ff7b7b}}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}
form{background:var(--card);padding:24px;border-radius:12px;max-width:340px;width:100%;box-shadow:0 2px 12px #0002}
h1{font-size:19px;margin:0 0 6px}p{color:var(--mu);margin:0 0 16px;font-size:14px}
input,button{width:100%;box-sizing:border-box;font-size:17px;padding:12px;border-radius:8px;border:1px solid #8894;background:var(--bg);color:var(--tx)}
button{margin-top:10px;background:var(--ac);color:#fff;border:0;font-weight:600}#e{color:var(--er);font-size:14px;min-height:18px;margin-top:8px}
</style></head><body><form id="f"><h1>__TITULO__</h1><p>Digite a senha que você recebeu. Ela fica salva neste aparelho.</p>
<input id="p" type="password" autocomplete="current-password" autocapitalize="off" placeholder="senha"><button>Abrir</button><div id="e"></div></form>
<script>
(()=>{
const D=__DADOS__,K='senha:'+location.pathname;
const u=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function abrir(senha,auto){
  const e=document.getElementById('e');e.textContent='Abrindo...';
  try{
    const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(senha.trim().toLowerCase()),'PBKDF2',false,['deriveKey']);
    const c=await crypto.subtle.deriveKey({name:'PBKDF2',salt:u(D.s),iterations:D.n,hash:'SHA-256'},k,{name:'AES-GCM',length:256},false,['decrypt']);
    const z=await crypto.subtle.decrypt({name:'AES-GCM',iv:u(D.i)},c,u(D.d));
    const t=await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    try{localStorage.setItem(K,senha)}catch(_){}
    document.open();document.write(t);document.close();
  }catch(_){
    e.textContent=auto?'':'Senha incorreta.';
    if(auto){try{localStorage.removeItem(K)}catch(_){}}
  }
}
document.getElementById('f').onsubmit=ev=>{ev.preventDefault();abrir(document.getElementById('p').value,false)};
let s=null;try{s=localStorage.getItem(K)}catch(_){}
if(s)abrir(s,true);
})();
</script></body></html>"""


def pagina_cifrada(conteudo: bytes, senha: str, titulo: str) -> str:
    dados = json.dumps(cifrar(conteudo, senha), separators=(',', ':'))
    return CASCA.replace('__TITULO__', html.escape(titulo)).replace('__DADOS__', dados)


def ler_paineis(origem: Path):
    """{slug: (nome do arquivo, bytes)} de uma pasta ou zip com painel_[RCA_]<SLUG>_<AAAA-MM-DD>.html."""
    pat = re.compile(r'painel_(?:RCA_)?(.+?)_(\d{4}-\d{2}-\d{2})\.html$')
    itens = []
    if origem.suffix == '.zip':
        with zipfile.ZipFile(origem) as z:
            itens = [(Path(n).name, z.read(n)) for n in z.namelist()]
    else:
        itens = [(p.name, p.read_bytes()) for p in sorted(origem.glob('painel_*.html'))]
    out, datas = {}, set()
    for nome, b in itens:
        m = pat.match(nome)
        if m:
            out[m.group(1)] = (nome, b)
            datas.add(m.group(2))
    return out, max(datas) if datas else None


def nome_bonito(slug):
    return ' '.join(w.lower() if w in ('DE', 'DA', 'DO', 'DOS', 'DAS', 'E') else w if len(w) <= 2 else w.capitalize()
                    for w in slug.split('_'))


def ranking_jpg(dia):
    """Imagens dos rankings do dia, reduzidas para JPEG (base64), para compartilhar pela página de envio."""
    from PIL import Image
    out = []
    for time in ('behikes', 'boinas'):
        f = HERE / 'rankings' / f'ranking_alta_atividade_{time}_{dia}.png'
        if not f.exists():
            continue
        im = Image.open(f).convert('RGB')
        if im.width > 1280:
            im = im.resize((1280, round(im.height * 1280 / im.width)))
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=85, optimize=True)
        out.append({'time': time.upper(), 'arquivo': f'ranking_{time}_{dia}.jpg', 'b64': base64.b64encode(buf.getvalue()).decode()})
    return out


ENVIO = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Envio dos painéis</title><style>
:root{--bg:#f4f6fa;--card:#fff;--tx:#1b2330;--mu:#5d6878;--wa:#1a8f4c;--ln:#d9dee7;--ac:#1f6feb}
@media (prefers-color-scheme:dark){:root{--bg:#11151c;--card:#1b212b;--tx:#e6ebf2;--mu:#9aa6b6;--wa:#25a35a;--ln:#2c3440;--ac:#5b9bff}}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:640px;margin:0 auto;padding:16px}h1{font-size:20px;margin:4px 0}.mu{color:var(--mu);font-size:13px}
.c{background:var(--card);border:1px solid var(--ln);border-radius:10px;padding:12px;margin:10px 0}
.r{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.n{font-weight:600;flex:1 1 140px}
input{font-size:15px;padding:8px;border-radius:6px;border:1px solid var(--ln);background:var(--bg);color:var(--tx);width:150px}
a.b,button{display:inline-block;padding:9px 12px;border-radius:8px;border:0;font-size:14px;font-weight:600;text-decoration:none;cursor:pointer}
.w{background:var(--wa);color:#fff}.s{background:transparent;color:var(--ac);border:1px solid var(--ac)!important}
.ok{opacity:.55}textarea{width:100%;box-sizing:border-box;font:14px system-ui;padding:8px;border-radius:6px;border:1px solid var(--ln);background:var(--bg);color:var(--tx)}
</style></head><body><main>
<h1>Envio dos painéis</h1><div class="mu">Pedidos até __DATA__. Toque em <b>Enviar painel</b> e depois em enviar no WhatsApp. O link é o mesmo todo dia; a senha só precisa ser mandada uma vez.</div>
<div class="c"><div class="mu" style="margin-bottom:6px">Mensagem ({nome} e {link} são trocados)</div><textarea id="msg" rows="3"></textarea></div>
<div id="lista"></div><div id="rk"></div>
<div class="mu" style="margin-top:14px">Telefone com DDD (só números). Fica salvo neste aparelho; sem telefone, o WhatsApp pede para escolher o contato.</div>
</main><script>
const R=__RCAS__,RK=__RANK__,DATA='__DATA__',DIA='__DIA__';
const g=(k,d)=>{try{return localStorage.getItem(k)??d}catch(_){return d}},p=(k,v)=>{try{localStorage.setItem(k,v)}catch(_){}};
const M0='Bom dia, {nome}! Seu painel BOPED com os pedidos até '+DATA+' está atualizado: {link}';
const msg=document.getElementById('msg');msg.value=g('msg',M0);msg.oninput=()=>p('msg',msg.value);
const wa=(tel,t)=>{tel=(tel||'').replace(/\\D/g,'');if(tel&&tel.length<=11)tel='55'+tel;return 'https://wa.me/'+tel+'?text='+encodeURIComponent(t)};
const L=document.getElementById('lista');
R.forEach(r=>{
  const d=document.createElement('div');d.className='c';
  d.innerHTML='<div class="r"><span class="n"></span><input inputmode="tel" placeholder="DDD + número"></div><div class="r" style="margin-top:8px"><a class="b w" target="_blank" rel="noopener">Enviar painel</a><a class="b s" target="_blank" rel="noopener">Enviar senha</a></div>';
  d.querySelector('.n').textContent=r.nome;
  const i=d.querySelector('input'),[a,s]=d.querySelectorAll('a');i.value=g('tel:'+r.slug,r.tel||'');
  const up=()=>{a.href=wa(i.value,msg.value.replaceAll('{nome}',r.nome).replaceAll('{link}',r.link));
    s.href=wa(i.value,'Senha do seu painel BOPED: '+r.senha+'\\nDigite uma vez; depois o celular lembra.')};
  i.oninput=()=>{p('tel:'+r.slug,i.value);up()};msg.addEventListener('input',up);up();
  if(g('env:'+r.slug)===DIA)a.classList.add('ok');a.onclick=()=>{p('env:'+r.slug,DIA);a.classList.add('ok')};
  L.appendChild(d)});
const K=document.getElementById('rk');
RK.forEach(r=>{
  const d=document.createElement('div');d.className='c';
  d.innerHTML='<div class="r"><span class="n"></span><button class="w">Compartilhar imagem</button></div><img style="width:100%;margin-top:8px;border-radius:6px">';
  d.querySelector('.n').textContent='Ranking '+r.time;const src='data:image/jpeg;base64,'+r.b64;d.querySelector('img').src=src;
  d.querySelector('button').onclick=async()=>{
    const b=await (await fetch(src)).blob(),f=new File([b],r.arquivo,{type:'image/jpeg'});
    if(navigator.canShare&&navigator.canShare({files:[f]})){try{await navigator.share({files:[f]})}catch(_){}}
    else{const x=document.createElement('a');x.href=src;x.download=r.arquivo;x.click()}};
  K.appendChild(d)});
</script></body></html>"""


def main(origem, repo, dia=None):
    origem, repo = Path(origem), Path(repo)
    paineis, dia_arq = ler_paineis(origem)
    if not paineis:
        sys.exit(f'nenhum painel_RCA_*_<data>.html em {origem}')
    dia = dia or dia_arq or date.today().isoformat()
    cfg = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    if '_envio' not in cfg:
        cfg['_envio'] = {'token': secrets.token_hex(8), 'senha': nova_senha()}
    rcas = []
    for slug, (nome_arq, conteudo) in sorted(paineis.items()):
        c = cfg.setdefault(slug, {'nome': nome_bonito(slug), 'telefone': '', 'token': secrets.token_hex(8), 'senha': nova_senha()})
        destino = repo / 'rca' / c['token'] / 'index.html'
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(pagina_cifrada(conteudo, c['senha'], f"Painel BOPED - {c['nome']}"), encoding='utf-8')
        rcas.append({'slug': slug, 'nome': c['nome'], 'tel': c.get('telefone', ''), 'senha': c['senha'],
                     'link': f"{SITE}rca/{c['token']}/"})
        print(f"{slug}: {nome_arq} -> rca/{c['token']}/ ({destino.stat().st_size // 1024} KB)")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
    d = date.fromisoformat(dia)
    envio = (ENVIO.replace('__RCAS__', json.dumps(rcas, ensure_ascii=False))
             .replace('__RANK__', json.dumps(ranking_jpg(dia)))
             .replace('__DATA__', d.strftime('%d/%m')).replace('__DIA__', dia))
    (HERE / 'privado' / f'envio_whatsapp_{dia}.html').write_text(envio, encoding='utf-8')
    e = cfg['_envio']
    destino = repo / 'envio' / e['token'] / 'index.html'
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(pagina_cifrada(envio.encode(), e['senha'], 'Envio dos painéis BOPED'), encoding='utf-8')
    print(f"página de envio: {SITE}envio/{e['token']}/ ({destino.stat().st_size // 1024} KB) e privado/envio_whatsapp_{dia}.html")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
