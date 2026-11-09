from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from backtester.core.segmented_history import SegmentError, build, read_range


class SegmentedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.src = self.root / 'raw.csv'; self.dest = self.root / 'normalized'
        self.src.write_text('timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n60,11,13,10,12,6\n180,12,14,11,13,7\n')

    def test_contiguous_segments_query_and_gap_refusal(self):
        metadata = build(self.src,self.dest,asset='SOL',quote='unknown',source_description='unverified fixture')
        self.assertEqual((metadata['count'],metadata['gap_runs'],metadata['missing_slots']),(3,1,1))
        self.assertEqual(read_range(self.dest,0,60)[-1][4],12.)
        with self.assertRaisesRegex(SegmentError,'missing'):
            read_range(self.dest,0,180)
        self.assertEqual(self.src.read_bytes(),(self.dest/'candles.csv').read_bytes())
        self.assertEqual((self.dest/'candles.csv').stat().st_mode & 0o777,0o600)

    def test_tampered_segment_is_rejected(self):
        build(self.src,self.dest,asset='SOL',source_description='fixture')
        p=self.dest/'candles.csv';data=p.read_bytes().replace(b'0,10,12',b'0,10,13',1);p.write_bytes(data)
        with self.assertRaisesRegex(SegmentError,'checksum'):
            read_range(self.dest,0,60)

    def test_invalid_or_duplicate_data_never_publishes_index(self):
        self.src.write_text('timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n0,10,12,9,11,5\n')
        with self.assertRaises(SegmentError):
            build(self.src,self.dest,asset='SOL',source_description='fixture')
        self.assertFalse((self.dest/'index.sqlite').exists())

    def test_range_crossing_index_chunk_boundary(self):
        self.src.write_text('timestamp,open,high,low,close,volume\n'+''.join(f'{i*60},10,12,9,11,5\n' for i in range(1442)))
        build(self.src,self.dest,asset='SOL',source_description='fixture')
        self.assertEqual(len(read_range(self.dest,1439*60,1441*60)),3)


if __name__ == '__main__':
    unittest.main()
