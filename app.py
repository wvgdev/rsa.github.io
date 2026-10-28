"""Dashboard local: execute python app.py e abra http://localhost:8765."""
import csv, io, json, math, re, threading, time, webbrowser
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
lock = threading.RLock()
records = deque(maxlen=3000)
state = dict(mode='desconectado', error='', invalid=0, last=None, session=0)
stop = threading.Event()
worker = None
FIELDS = ['recebido_em','origem','esquerdo','direito','sup_esq','sup_dir','inf_esq','inf_dir','angulo_h','angulo_v','tolerancia','diferenca_h','diferenca_v','estado','superior','inferior','erro_h','erro_v','luz_h','luz_v','estado_h','estado_v','acao_h','unidade','limiar_luz']

def directional(d):
    for k in ['superior','inferior','esquerdo','direito','angulo_v']:
        v=d.get(k)
        maximum=175 if k=='angulo_v' else 4095
        minimum=5 if k=='angulo_v' else 0
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not minimum<=v<=maximum:
            raise ValueError('Valor inválido: '+k)
    eh=math.log(d['esquerdo']+1)-math.log(d['direito']+1)
    ev=math.log(d['superior']+1)-math.log(d['inferior']+1)
    for k in ['erro_h','erro_v']:
        if k in d and (not isinstance(d[k],(int,float)) or isinstance(d[k],bool) or not math.isfinite(d[k])):
            raise ValueError('Erro inválido: '+k)
    lh=max(d['esquerdo'],d['direito'])>50
    lv=max(d['superior'],d['inferior'])>50
    sh='Luz insuficiente' if not lh else 'Dentro da tolerância' if abs(eh)<=.30 else 'Erro acima da tolerância'
    sv='Luz insuficiente' if not lv else 'Dentro da tolerância' if abs(ev)<=.30 else 'Erro acima da tolerância'
    condition='Luz insuficiente nos dois eixos' if not lh and not lv else 'Diferença de luz detectada' if (lh and abs(eh)>.30) or (lv and abs(ev)>.30) else 'Dentro da tolerância nos eixos com luz'
    d.update(diferenca_h=d['esquerdo']-d['direito'],diferenca_v=d['superior']-d['inferior'],
             erro_h=d.get('erro_h',eh),erro_v=d.get('erro_v',ev),luz_h=lh,luz_v=lv,
             estado_h=sh,estado_v=sv,estado=condition,acao_h='Não informado pelo firmware',
             unidade='log',limiar_luz=50,tolerancia=.30,angulo_h=None)
    return {k:d.get(k) for k in FIELDS}

def parse(line):
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        m = re.fullmatch(r'Esquerdo:\s*(\d+)\s*\|\s*Direito:\s*(\d+)\s*\|\s*Angulo:\s*(\d+)\s*', line)
        if not m:
            n=re.fullmatch(r'Sup:\s*(\d+)\s*\|\s*Inf:\s*(\d+)\s*\|\s*Esq:\s*(\d+)\s*\|\s*Dir:\s*(\d+)\s*\|\s*DifV:\s*([+-]?\d+(?:\.\d+)?)\s*\|\s*DifH:\s*([+-]?\d+(?:\.\d+)?)\s*\|\s*AngV:\s*(\d+)\s*',line)
            if not n: raise ValueError('Formato desconhecido: confira firmware e baud 115200.')
            return directional(dict(superior=int(n[1]),inferior=int(n[2]),esquerdo=int(n[3]),direito=int(n[4]),erro_v=float(n[5]),erro_h=float(n[6]),angulo_v=int(n[7])))
        d = dict(esquerdo=int(m[1]), direito=int(m[2]), angulo_h=int(m[3]))
    if not isinstance(d, dict): raise ValueError('JSON deve ser um objeto.')
    if 'superior' in d or 'inferior' in d: return directional(d)
    four = all(k in d for k in ['sup_esq','sup_dir','inf_esq','inf_dir'])
    keys = ['sup_esq','sup_dir','inf_esq','inf_dir'] if four else ['esquerdo','direito']
    for k in keys:
        v = d.get(k)
        if isinstance(v, bool) or not isinstance(v, (float,int)) or not math.isfinite(v) or not 0 <= v <= 4095:
            raise ValueError('Leitura inválida: '+k)
    if four:
        d['esquerdo'] = (d['sup_esq']+d['inf_esq'])/2
        d['direito'] = (d['sup_dir']+d['inf_dir'])/2
        d['diferenca_v'] = (d['sup_esq']+d['sup_dir']-d['inf_esq']-d['inf_dir'])/2
    else:
        for k in ['sup_esq','sup_dir','inf_esq','inf_dir','diferenca_v']: d[k] = None
    for k in ['angulo_h','angulo_v']:
        v = d.get(k)
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0 <= v <= 180):
            raise ValueError('Ângulo inválido: '+k)
    t = d.get('tolerancia',30)
    if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or not 0 <= t <= 4095: raise ValueError('Tolerância inválida')
    d['unidade']='ADC'; d['tolerancia'] = t
    d['diferenca_h'] = d['esquerdo']-d['direito']
    d['estado'] = 'Desequilíbrio de luz' if max(abs(d['diferenca_h']),abs(d.get('diferenca_v') or 0)) > t else 'Luz equilibrada'
    return {k:d.get(k) for k in FIELDS}

def ingest(line, source):
    try: d = parse(line)
    except (ValueError,TypeError) as e:
        with lock: state['invalid'] += 1; state['error'] = str(e)
        return
    d.update(recebido_em=datetime.now(timezone.utc).isoformat(),origem=source)
    with lock:
        records.append(d); state['last']=time.time(); state['error']=''
    path = ROOT / 'registros' / ('simulacao_v2.csv' if source=='SIMULAÇÃO' else 'leituras_reais_v2.csv')
    path.parent.mkdir(exist_ok=True)
    with path.open('a',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=FIELDS)
        if f.tell()==0: w.writeheader()
        w.writerow(d)

def reader(port,baud):
    try:
        import serial
        with serial.Serial(port, baud, timeout=0.5) as s:
            while not stop.is_set():
                b = s.read_until(b'\n',size=4096)
                if b.endswith(b'\n'): ingest(b.decode('utf-8',errors='replace').strip(),'ESP32')
                elif b:
                    with lock: state['invalid']+=1; state['error']='Linha incompleta; use println e envio periódico.'
    except Exception as e:
        with lock: state['error']=str(e); state['mode']='desconectado'

def simulator():
    n=0
    while not stop.wait(.3):
        n+=1; delta=170*math.sin(n/15)
        ingest(json.dumps(dict(superior=int(1800+400*math.sin(n/20)),inferior=int(1800-400*math.sin(n/20)),esquerdo=int(1900+delta*4),direito=int(1900-delta*4),angulo_v=round(90+30*math.sin(n/25)))),'SIMULAÇÃO')

def connect(mode,port='',baud=115200):
    global worker
    stop.set()
    if worker: worker.join(2)
    if worker and worker.is_alive(): raise ValueError('Aguarde a porta serial encerrar.')
    stop.clear()
    with lock:
        records.clear(); state.update(mode=mode,error='',last=None,invalid=0,session=state['session']+1)
    target = simulator if mode=='simulacao' else reader
    worker = threading.Thread(target=target,args=() if mode=='simulacao' else (port,baud),daemon=True) if mode!='desconectado' else None
    if worker: worker.start()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,data,typ='application/json',status=200):
        body = data.encode() if isinstance(data,str) else json.dumps(data,allow_nan=False).encode()
        self.send_response(status); self.send_header('Content-Type',typ+'; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path=='/': return self.send((ROOT/'dashboard.html').read_text(encoding='utf-8'),'text/html')
        if self.path=='/api/ports':
            try:
                from serial.tools import list_ports
                return self.send([dict(port=p.device,label=p.description) for p in list_ports.comports()])
            except ImportError: return self.send({'error':'Instale as dependências: python -m pip install -r requirements.txt'},status=503)
        if self.path=='/api/state':
            with lock: return self.send(dict(**state,age=None if state['last'] is None else time.time()-state['last'],records=list(records)))
        if self.path=='/api/export':
            with lock: snapshot=list(records)
            out=io.StringIO(); w=csv.DictWriter(out,fieldnames=FIELDS); w.writeheader(); w.writerows(snapshot)
            return self.send(out.getvalue(),'text/csv')
        self.send({'error':'Não encontrado'},status=404)
    def do_POST(self):
        if self.headers.get('Origin') not in (None,'http://localhost:8765','http://127.0.0.1:8765'): return self.send({'error':'Origem inválida'},status=403)
        if self.path!='/api/connect': return self.send({'error':'Não encontrado'},status=404)
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<4096: raise ValueError('Requisição inválida')
            d=json.loads(self.rfile.read(size)); mode=d.get('mode')
            if mode not in ['serial','simulacao','desconectado']: raise ValueError('Modo inválido')
            baud=int(d.get('baud',115200))
            if baud not in [9600,57600,115200]: raise ValueError('Baud inválido')
            connect(mode,str(d.get('port','')),baud); self.send({'ok':True})
        except (ValueError,TypeError) as e: self.send({'error':str(e)},status=400)

if __name__=='__main__':
    print('Dashboard: http://localhost:8765 — Ctrl+C para encerrar')
    webbrowser.open('http://localhost:8765')
    try: ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
    except KeyboardInterrupt: stop.set()
