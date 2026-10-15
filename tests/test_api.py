import unittest, tempfile, os
from concurrent.futures import ThreadPoolExecutor
from app import server

class TestNexo(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();server.DB=os.path.join(self.temp.name,'test.sqlite3');server.setup()
    def tearDown(self):self.temp.cleanup()
    def call(self,verb,path,body=None):return server.process(verb,path,body)
    def seed(self,stock=3,quantity=2):
        pid=self.call('POST','/products',{'name':'Caja','stock':stock})[1]['id']
        rid=self.call('POST','/requests',{'customer':'Ana','product_id':pid,'quantity':quantity})[1]['id']
        return pid,rid
    def test_product_and_request(self):
        pid,rid=self.seed();self.assertEqual(self.call('GET','/requests')[1]['requests'][0]['status'],'PENDIENTE')
    def test_reservation_decrements_stock(self):
        pid,rid=self.seed();self.assertEqual(self.call('POST',f'/requests/{rid}/reserve')[1]['status'],'RESERVADA');self.assertEqual(self.call('GET','/products')[1]['products'][0]['stock'],1)
    def test_insufficient_stock_keeps_state(self):
        pid,rid=self.seed(1,2)
        with self.assertRaises(server.ApiError) as exc:self.call('POST',f'/requests/{rid}/reserve')
        self.assertEqual(exc.exception.code,409);self.assertEqual(self.call('GET','/requests')[1]['requests'][0]['status'],'PENDIENTE')
    def test_no_double_reservation(self):
        pid,rid=self.seed();self.call('POST',f'/requests/{rid}/reserve')
        with self.assertRaises(server.ApiError):self.call('POST',f'/requests/{rid}/reserve')
        self.assertEqual(self.call('GET','/products')[1]['products'][0]['stock'],1)
    def test_delivery_lifecycle(self):
        pid,rid=self.seed();self.call('POST',f'/requests/{rid}/reserve');did=self.call('POST','/deliveries',{'request_id':rid,'assignee':'Luis'})[1]['id'];self.call('POST',f'/deliveries/{did}/complete');self.assertEqual(self.call('GET','/requests')[1]['requests'][0]['status'],'ENTREGADA')
    def test_delivery_requires_reservation(self):
        pid,rid=self.seed()
        with self.assertRaises(server.ApiError):self.call('POST','/deliveries',{'request_id':rid,'assignee':'Luis'})
    def test_suggestion_and_review(self):
        pid,rid=self.seed(1,2);s=self.call('POST',f'/requests/{rid}/suggest')[1];self.assertEqual(s['suggestion'],'REVISAR_STOCK');result=self.call('POST',f"/decisions/{s['id']}/review",{'reviewer':'Docente','approved':False})[1];self.assertFalse(result['approved'])
    def test_invalid_quantity(self):
        pid,_=self.seed()
        with self.assertRaises(server.ApiError):self.call('POST','/requests',{'customer':'Ana','product_id':pid,'quantity':-2})
    def test_duplicate_product(self):
        self.seed()
        with self.assertRaises(server.ApiError):self.call('POST','/products',{'name':'Caja','stock':2})
    def test_health(self):self.assertEqual(self.call('GET','/health')[1]['status'],'ok')
    def test_missing_product_returns_404(self):
        with self.assertRaises(server.ApiError) as err:self.call('POST','/requests',{'customer':'Ana','product_id':99999,'quantity':1})
        self.assertEqual(err.exception.code,404)
    def test_duplicate_delivery_returns_409(self):
        _,rid=self.seed();self.call('POST',f'/requests/{rid}/reserve');self.call('POST','/deliveries',{'request_id':rid,'assignee':'Ana'})
        with self.assertRaises(server.ApiError) as err:self.call('POST','/deliveries',{'request_id':rid,'assignee':'Luis'})
        self.assertEqual(err.exception.code,409)
    def test_missing_decision_returns_404(self):
        with self.assertRaises(server.ApiError) as err:self.call('POST','/decisions/99999/review',{'reviewer':'Ana','approved':True})
        self.assertEqual(err.exception.code,404)
    def test_double_delivery_completion_returns_409(self):
        _,rid=self.seed();self.call('POST',f'/requests/{rid}/reserve');did=self.call('POST','/deliveries',{'request_id':rid,'assignee':'Ana'})[1]['id'];self.call('POST',f'/deliveries/{did}/complete')
        with self.assertRaises(server.ApiError) as err:self.call('POST',f'/deliveries/{did}/complete')
        self.assertEqual(err.exception.code,409)
    def test_concurrent_reservation_only_once(self):
        pid,rid=self.seed(stock=3,quantity=2)
        def reserve(_):
            try:return self.call('POST',f'/requests/{rid}/reserve')[0]
            except server.ApiError as e:return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(reserve,range(2)))
        self.assertEqual(sorted(outcomes),[200,409])
        self.assertEqual(self.call('GET','/products')[1]['products'][0]['stock'],1)
if __name__=='__main__':unittest.main()
