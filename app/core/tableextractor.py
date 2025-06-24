import pdf2image
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import layoutparser as lp
import cv2

from PyPDF2 import PdfReader, PdfWriter
import pandas as pd

import pdfminer.high_level
import pdfminer.layout
from operator import itemgetter

# inputs: pdf_file, page #, bounding box (optional) (llur or ullr), output_bbox
class TableExtractor(object):
    def __init__(self, output_bbox=True):
        self.pdf_file = ""
        self.page = ""
        self.image_dpi = 200
        self.pdf_dpi = 72
        self.output_bbox = output_bbox
        self.blocks = {}
        self.title_y = 0
        self.column_header_y = 0
        self.model = None
        self.img = None
        self.output_image = True
        self.tagging = {
            'substance': ['compound', 'salt', 'base', 'solvent', 'CBr4', 'collidine', 'InX3', 'substrate', 'ligand', 'PPh3', 'PdL2', 'Cu', 'compd', 'reagent', 'reagant', 'acid', 'aldehyde', 'amine', 'Ln', 'H2O', 'enzyme', 'cofactor', 'oxidant', 'Pt(COD)Cl2', 'CuBr2', 'additive'],
            'ratio': [':'],
            'measurement': ['μM', 'nM', 'IC50', 'CI', 'excitation', 'emission', 'Φ', 'φ', 'shift', 'ee', 'ΔG', 'ΔH', 'TΔS', 'Δ', 'distance', 'trajectory', 'V', 'eV'],
            'temperature': ['temp', 'temperature', 'T', '°C'],
            'time': ['time', 't(', 't ('],
            'result': ['yield', 'aa', 'result', 'product', 'conversion', '(%)'],
            'alkyl group': ['R', 'Ar', 'X', 'Y'],
            'solvent': ['solvent'],
            'counter': ['entry', 'no.'],
            'catalyst': ['catalyst', 'cat.'],
            'conditions': ['condition'],
            'reactant': ['reactant'],
        }
        
    def set_output_image(self, oi):
        self.output_image = oi
    
    def set_pdf_file(self, pdf):
        self.pdf_file = pdf
    
    def set_page_num(self, pn):
        self.page = pn
        
    def set_output_bbox(self, ob):
        self.output_bbox = ob
        
    def run_model(self, page_info):
        
        img = np.asarray(page_info)
        self.img = img
        
        layout_result = self.model.detect(img)
        
        text_blocks = lp.Layout([b for b in layout_result if b.type == 'Text'])
        title_blocks = lp.Layout([b for b in layout_result if b.type == 'Title'])
        list_blocks = lp.Layout([b for b in layout_result if b.type == 'List'])
        table_blocks = lp.Layout([b for b in layout_result if b.type == 'Table'])
        figure_blocks = lp.Layout([b for b in layout_result if b.type == 'Figure'])
        
        self.blocks.update({'text': text_blocks})
        self.blocks.update({'title': title_blocks})
        self.blocks.update({'list': list_blocks})
        self.blocks.update({'table': table_blocks})
        self.blocks.update({'figure': figure_blocks})
# ... existing code continues (341 lines total) ...