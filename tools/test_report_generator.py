"""Test report formatting with synthetic fixtures kept in a temporary directory.
These fixture values are NOT benchmark results and must never be published as evidence.
"""
import json
import tempfile
import unittest
from pathlib import Path
from run_benchmark import write_report, fmt

class ReportTests(unittest.TestCase):
    def test_report_formats_rows_and_subscores(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            row = {'benchmark':'de.backendlab.bench.CacheBenchmark.mixed','params':{'strategy':'snapshot','count':'100000'},'threads':5,
                   'primaryMetric':{'score':12.5,'scoreError':0.5,'scoreUnit':'ops/s'},
                   'secondaryMetrics':{'mixed:reader':{'score':10,'scoreError':0.3,'scoreUnit':'ops/s'},'mixed:writer':{'score':2.5,'scoreError':'NaN','scoreUnit':'ops/s'}}}
            file=path/'mixed.json'; file.write_text(json.dumps([row]))
            write_report(path, {}, [file]);report=(path/'REPORT.md').read_text(encoding='utf-8')
            self.assertIn('mixed / mixed:reader | snapshot | 100000 | 5 | 10',report)
            self.assertIn('mixed / mixed:writer | snapshot | 100000 | 5 | 2.5 | n/a',report)
            self.assertIn('not a fixed 80/20 operation ratio',report)
    def test_non_finite_error(self):
        self.assertEqual('n/a',fmt(float('nan')))
        self.assertEqual('n/a',fmt(float('inf')))
        self.assertEqual('n/a',fmt(None))

if __name__ == '__main__': unittest.main()
