"""Local OCR smoke check only; no sales publication or source edits."""
import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('image', type=Path)
args = parser.parse_args()
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
os.environ.setdefault('FLAGS_use_mkldnn', '0')
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='korean', use_doc_orientation_classify=False,
                use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False,
                text_detection_model_name='PP-OCRv5_mobile_det',
                text_det_limit_side_len=640, text_det_limit_type='max', cpu_threads=1)
result = list(ocr.predict(str(args.image)))
count = sum(len(item.get('rec_texts', [])) for item in result)
if count == 0:
    raise SystemExit('OCR found no text in the migration sample')
print('ocr_prediction_verified texts=' + str(count))
