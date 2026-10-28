import unittest, json
from app import parse
class TelemetryTests(unittest.TestCase):
    def test_old(self):
        d=parse('Esquerdo: 500 | Direito: 510 | Angulo: 90')
        self.assertEqual(d['estado'],'Luz equilibrada')
        self.assertIsNone(d['angulo_v'])
    def test_four(self):
        d=parse(json.dumps(dict(sup_esq=2000,sup_dir=1900,inf_esq=1000,inf_dir=900,angulo_h=80,angulo_v=100)))
        self.assertEqual(d['diferenca_h'],100)
        self.assertEqual(d['diferenca_v'],1000)
        self.assertEqual(d['estado'],'Desequilíbrio de luz')
    def test_threshold(self):
        self.assertEqual(parse('{"esquerdo":30,"direito":0}')['estado'],'Luz equilibrada')
        self.assertEqual(parse('{"esquerdo":31,"direito":0}')['estado'],'Desequilíbrio de luz')
    def test_invalid(self):
        for s in ['{}','[]','debug','{"esquerdo":5000,"direito":0}','{"esquerdo":true,"direito":0}','{"esquerdo":NaN,"direito":0}','{"esquerdo":0,"direito":0,"angulo_h":181}']:
            with self.subTest(s=s),self.assertRaises(ValueError): parse(s)
class CurrentFirmwareTests(unittest.TestCase):
    def test_serial_current(self):
        d=parse('Sup: 1800 | Inf: 1800 | Esq: 2200 | Dir: 1000 | DifV: 0.000 | DifH: 0.788 | AngV: 90')
        self.assertEqual(d['superior'],1800)
        self.assertEqual(d['estado_h'],'Erro acima da tolerância')
        self.assertEqual(d['estado_v'],'Dentro da tolerância')
        self.assertIsNone(d['angulo_h'])
        self.assertEqual(d['erro_h'],.788)
    def test_dark(self):
        d=parse('Sup: 50 | Inf: 0 | Esq: 0 | Dir: 50 | DifV: 3.932 | DifH: -3.932 | AngV: 175')
        self.assertEqual(d['estado'],'Luz insuficiente nos dois eixos')
    def test_vertical(self):
        d=parse('Sup: 2000 | Inf: 100 | Esq: 1000 | Dir: 1000 | DifV: 2.986 | DifH: 0.000 | AngV: 5')
        self.assertEqual(d['estado_v'],'Erro acima da tolerância')
        self.assertEqual(d['estado_h'],'Dentro da tolerância')
    def test_rounded_boundary(self):
        d=parse('Sup: 1000 | Inf: 1000 | Esq: 1350 | Dir: 1000 | DifV: 0.000 | DifH: 0.300 | AngV: 90')
        self.assertEqual(d['estado_h'],'Dentro da tolerância')
    def test_directional_json(self):
        d=parse('{"superior":1000,"inferior":1000,"esquerdo":1000,"direito":1000,"angulo_v":90}')
        self.assertEqual(d['erro_h'],0)
if __name__=='__main__': unittest.main()
