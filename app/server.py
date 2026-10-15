# NexoEntrega 360 - API educativa sin dependencias externas.
import json, sqlite3, os, re
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DB = os.environ.get('NEXO_DB', 'nexo.sqlite3')

class ApiError(Exception):
    def __init__(self, code, msg): self.code, self.msg=code, msg

def connect():
    conn=sqlite3.connect(DB, timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def setup():
    with closing(connect()) as c, c:
        c.executescript("""CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, stock INTEGER NOT NULL CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, customer TEXT NOT NULL, product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity>0), status TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(status IN ('PENDIENTE','RESERVADA','ENTREGADA')), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL UNIQUE REFERENCES requests(id), assignee TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('ASIGNADA','ENTREGADA')) DEFAULT 'ASIGNADA');
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL REFERENCES requests(id), suggestion TEXT NOT NULL, rationale TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0 CHECK(approved IN (0,1)), reviewer TEXT);""")

def fields(data, names):
    for k in names:
        if k not in data: raise ApiError(400,'Falta campo: '+k)

def positive_int(v):
    if type(v)!=int or v<=0: raise ApiError(400,'Se requiere entero positivo')
    return v

def nonempty(v):
    if not isinstance(v,str) or not v.strip() or len(v)>120: raise ApiError(400,'Texto obligatorio (max 120)')
    return v.strip()

def process(method,path,data=None):
    data=data or {}
    with closing(connect()) as c, c:
        if method=='GET' and path=='/health': return 200,{'status':'ok'}
        if method=='GET' and path=='/products': return 200,{'products':[dict(x) for x in c.execute('SELECT * FROM products ORDER BY id')]}
        if method=='GET' and path=='/requests': return 200,{'requests':[dict(x) for x in c.execute('SELECT * FROM requests ORDER BY id')]}
        if method=='GET' and path=='/deliveries': return 200,{'deliveries':[dict(x) for x in c.execute('SELECT * FROM deliveries ORDER BY id')]}
        if method=='GET' and path=='/decisions': return 200,{'decisions':[dict(x) for x in c.execute('SELECT * FROM decisions ORDER BY id')]}
        if method=='POST' and path=='/products':
            fields(data,['name','stock']); name=nonempty(data['name']); stock=data['stock']
            if type(stock)!=int or stock<0: raise ApiError(400,'Stock invalido')
            try: cursor=c.execute('INSERT INTO products(name,stock) VALUES (?,?)',(name,stock))
            except sqlite3.IntegrityError: raise ApiError(409,'Producto duplicado')
            return 201,{'id':cursor.lastrowid,'name':name,'stock':stock}
        if method=='POST' and path=='/requests':
            fields(data,['customer','product_id','quantity']); customer=nonempty(data['customer']); pid=positive_int(data['product_id']); qty=positive_int(data['quantity'])
            if not c.execute('SELECT id FROM products WHERE id=?',(pid,)).fetchone():raise ApiError(404,'Producto no existe')
            cursor=c.execute('INSERT INTO requests(customer,product_id,quantity) VALUES (?,?,?)',(customer,pid,qty))
            return 201,{'id':cursor.lastrowid,'status':'PENDIENTE'}
        match=re.fullmatch(r'/requests/(\d+)/reserve',path)
        if method=='POST' and match:
            rid=int(match.group(1)); c.execute('BEGIN IMMEDIATE'); req=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
            if not req:raise ApiError(404,'Solicitud no existe')
            if req['status']!='PENDIENTE':raise ApiError(409,'Solicitud ya procesada')
            res=c.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?', (req['quantity'],req['product_id'],req['quantity']))
            if res.rowcount==0:raise ApiError(409,'Stock insuficiente')
            c.execute('UPDATE requests SET status=? WHERE id=?',('RESERVADA',rid))
            return 200,{'id':rid,'status':'RESERVADA'}
        if method=='POST' and path=='/deliveries':
            fields(data,['request_id','assignee']); rid=positive_int(data['request_id']); assignee=nonempty(data['assignee'])
            req=c.execute('SELECT status FROM requests WHERE id=?',(rid,)).fetchone()
            if not req:raise ApiError(404,'Solicitud no existe')
            if req['status']!='RESERVADA':raise ApiError(409,'Primero se reserva inventario')
            try: cursor=c.execute('INSERT INTO deliveries(request_id,assignee) VALUES (?,?)',(rid,assignee))
            except sqlite3.IntegrityError:raise ApiError(409,'Entrega ya asignada')
            return 201,{'id':cursor.lastrowid,'status':'ASIGNADA'}
        match=re.fullmatch(r'/deliveries/(\d+)/complete',path)
        if method=='POST' and match:
            did=int(match.group(1)); d=c.execute('SELECT * FROM deliveries WHERE id=?',(did,)).fetchone()
            if not d:raise ApiError(404,'Entrega no existe')
            if d['status']=='ENTREGADA':raise ApiError(409,'Ya entregada')
            c.execute('UPDATE deliveries SET status=? WHERE id=?',('ENTREGADA',did))
            c.execute('UPDATE requests SET status=? WHERE id=?',('ENTREGADA',d['request_id']))
            return 200,{'id':did,'status':'ENTREGADA'}
        match=re.fullmatch(r'/requests/(\d+)/suggest',path)
        if method=='POST' and match:
            rid=int(match.group(1)); req=c.execute('SELECT r.*,p.stock FROM requests r JOIN products p ON r.product_id=p.id WHERE r.id=?',(rid,)).fetchone()
            if not req:raise ApiError(404,'Solicitud no existe')
            suggestion='REVISAR_STOCK' if req['status']=='PENDIENTE' and req['stock']<req['quantity'] else ('PREPARAR_DESPACHO' if req['status']=='RESERVADA' else 'VALIDAR_SOLICITUD')
            rationale='Sugerencia automatizada basada exclusivamente en estado, cantidad y stock; requiere validacion humana.'
            cursor=c.execute('INSERT INTO decisions(request_id,suggestion,rationale) VALUES (?,?,?)',(rid,suggestion,rationale))
            return 201,{'id':cursor.lastrowid,'suggestion':suggestion,'rationale':rationale,'approved':False,'type':'reglas_explicables_no_modelo_generativo'}
        match=re.fullmatch(r'/decisions/(\d+)/review',path)
        if method=='POST' and match:
            fields(data,['reviewer','approved']); did=int(match.group(1)); reviewer=nonempty(data['reviewer'])
            if type(data['approved'])!=bool:raise ApiError(400,'approved debe ser booleano')
            if not c.execute('SELECT id FROM decisions WHERE id=?',(did,)).fetchone():raise ApiError(404,'Decision no existe')
            c.execute('UPDATE decisions SET reviewer=?,approved=? WHERE id=?',(reviewer,int(data['approved']),did))
            return 200,{'id':did,'reviewer':reviewer,'approved':data['approved']}
        raise ApiError(404,'Ruta no encontrada')

class Handler(BaseHTTPRequestHandler):
    def _respond(self,method):
        try:
            path=urlparse(self.path).path
            body={}
            if method=='POST':
                length=int(self.headers.get('Content-Length','0'))
                if length>100000:raise ApiError(413,'Solicitud muy grande')
                try:body=json.loads(self.rfile.read(length))
                except (ValueError,UnicodeDecodeError):raise ApiError(400,'JSON invalido')
                if not isinstance(body,dict):raise ApiError(400,'Objeto JSON requerido')
            status,result=process(method,path,body)
        except ApiError as e:status,result=e.code,{'error':e.msg}
        except sqlite3.Error:status,result=500,{'error':'Error interno de base de datos'}
        raw=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):self._respond('GET')
    def do_POST(self):self._respond('POST')

if __name__=='__main__':
    setup();print('NexoEntrega 360: http://localhost:8000');ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
