import torch
import re
from functools import lru_cache
import layoutparser as lp
import pdf2image
from PIL import Image
from huggingface_hub import hf_hub_download, snapshot_download
from molscribe import MolScribe
from rxnscribe import RxnScribe, MolDetect
from chemiener import ChemNER
from .chemrxnextractor import ChemRxnExtractor
from .tableextractor import TableExtractor
from .utils import *

class OpenChemIE:
    def __init__(self, device=None):
        """
        Initialization function of OpenChemIE
        Parameters:
            device: str of either cuda device name or 'cpu'
        """
        if device is None:
            self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        else:
            self.device = torch.device(device)

        self._molscribe = None
        self._rxnscribe = None
        self._pdfparser = None
        self._moldet = None
        self._chemrxnextractor = None
        self._chemner = None
        self._coref = None

    @property
    def molscribe(self):
        if self._molscribe is None:
            self.init_molscribe()
        return self._molscribe

    @lru_cache(maxsize=None)
    def init_molscribe(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = hf_hub_download("yujieq/MolScribe", "swin_base_char_aux_1m.pth")
        self._molscribe = MolScribe(ckpt_path, device=self.device)
    

    @property
    def rxnscribe(self):
        if self._rxnscribe is None:
            self.init_rxnscribe()
        return self._rxnscribe

    @lru_cache(maxsize=None)
    def init_rxnscribe(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = hf_hub_download("yujieq/RxnScribe", "pix2seq_reaction_full.ckpt")
        self._rxnscribe = RxnScribe(ckpt_path, device=self.device)
    

    @property
    def pdfparser(self):
        if self._pdfparser is None:
            self.init_pdfparser()
        return self._pdfparser

    @lru_cache(maxsize=None)
    def init_pdfparser(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        config_path = "lp://efficientdet/PubLayNet/tf_efficientdet_d1"
        self._pdfparser = lp.AutoLayoutModel(config_path, model_path=ckpt_path, device=self.device.type)
    

    @property
    def moldet(self):
        if self._moldet is None:
            self.init_moldet()
        return self._moldet

    @lru_cache(maxsize=None)
    def init_moldet(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = hf_hub_download("Ozymandias314/MolDetectCkpt", "best_hf.ckpt")
        self._moldet = MolDetect(ckpt_path, device=self.device)
        

    @property
    def coref(self):
        if self._coref is None:
            self.init_coref()
        return self._coref

    @lru_cache(maxsize=None)
    def init_coref(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = hf_hub_download("Ozymandias314/MolDetectCkpt", "coref_best_hf.ckpt")
        self._coref = MolDetect(ckpt_path, device=self.device, coref=True)


    @property
    def chemrxnextractor(self):
        if self._chemrxnextractor is None:
            self.init_chemrxnextractor()
        return self._chemrxnextractor

    @lru_cache(maxsize=None)
    def init_chemrxnextractor(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = snapshot_download(repo_id="amberwang/chemrxnextractor-training-modules")
        self._chemrxnextractor = ChemRxnExtractor("", None, ckpt_path, self.device.type)


    @property
    def chemner(self):
        if self._chemner is None:
            self.init_chemner()
        return self._chemner

    @lru_cache(maxsize=None)
    def init_chemner(self, ckpt_path=None):
        """
        Set model to custom checkpoint
        Parameters:
            ckpt_path: path to checkpoint to use, if None then will use default
        """
        if ckpt_path is None:
            ckpt_path = hf_hub_download("Ozymandias314/ChemNERckpt", "best.ckpt")
        self._chemner = ChemNER(ckpt_path, device=self.device)

    
    @property
    def tableextractor(self):
        return TableExtractor()


    def extract_figures_from_pdf(self, pdf, num_pages=None, output_bbox=False, output_image=True):
        """
        Find and return all figures from a pdf page
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
            output_bbox: whether to output bounding boxes for each individual entry of a table
            output_image: whether to include PIL image for figures. default is True
        Returns:
            list of content in the following format
            [
                { # first figure
                    'title': str,
                    'figure': {
                        'image': PIL image or None,
                        'bbox': list in form [x1, y1, x2, y2],
                    }
                    'table': {
                        'bbox': list in form [x1, y1, x2, y2] or empty list,
                        'content': {
                            'columns': list of column headers,
                            'rows': list of list of row content,
                        } or None
                    }
                    'footnote': str or empty,
                    'page': int
                }
                # more figures
            ]
        """
        pages = pdf2image.convert_from_path(pdf, last_page=num_pages)

        table_ext = self.tableextractor
        table_ext.set_pdf_file(pdf)
        table_ext.set_output_image(output_image)

        table_ext.set_output_bbox(output_bbox)
        
        return table_ext.extract_all_tables_and_figures(pages, self.pdfparser, content='figures')

    def extract_tables_from_pdf(self, pdf, num_pages=None, output_bbox=False, output_image=True):
        """
        Find and return all tables from a pdf page
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
            output_bbox: whether to include bboxes for individual entries of the table
            output_image: whether to include PIL image for figures. default is True
        Returns:
            list of content in the following format
            [
                { # first table
                    'title': str,
                    'figure': {
                        'image': PIL image or None,
                        'bbox': list in form [x1, y1, x2, y2] or empty list,
                    }
                    'table': {
                        'bbox': list in form [x1, y1, x2, y2] or empty list,
                        'content': {
                            'columns': list of column headers,
                            'rows': list of list of row content,
                        }
                    }
                    'footnote': str or empty,
                    'page': int
                }
                # more tables
            ]
        """
        pages = pdf2image.convert_from_path(pdf, last_page=num_pages)

        table_ext = self.tableextractor
        table_ext.set_pdf_file(pdf)
        table_ext.set_output_image(output_image)

        table_ext.set_output_bbox(output_bbox)
        
        return table_ext.extract_all_tables_and_figures(pages, self.pdfparser, content='tables')

    def extract_molecules_from_figures_in_pdf(self, pdf, batch_size=16, num_pages=None):
        """
        Get all molecules and their information from a pdf
        Parameters:
            pdf: path to pdf, or byte file
            batch_size: batch size for inference in all models
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            A list of dictionaries, with each dictionary containing
            'smiles': SMILES string of the molecule
            'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
            'image': cropped image of the molecule
            'page': page number of the molecule
        """
        if type(pdf) == str:
            pages = pdf2image.convert_from_path(pdf, last_page=num_pages)
        else:
            pages = pdf2image.convert_from_bytes(pdf, last_page=num_pages)
        figures = get_figures_from_pages(pages, self.pdfparser)
        return self.extract_molecules_from_figures(figures, batch_size=batch_size)
    
    def extract_molecule_bboxes_from_figures(self, figures, batch_size=16):
        """
        Get molecule bboxes from figures
        Parameters:
            figures: a list of dictionaries, with each dictionary containing
            'image': image of the figure
            'page': page number of the figure
            batch_size: batch size for inference in all models
        Returns:
            A list of dictionaries, with each dictionary corresponding to an image
            and containing a list of dictionaries, with each dictionary containing
            'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
            'score': confidence score of the molecule detection
        """
        images = [fig['image'] for fig in figures]
        results = self.moldet.predict_images(images, batch_size=batch_size)
        return results
    
    def extract_molecules_from_figures(self, figures, batch_size=16):
        """
        Get all molecules and their information from figures
        Parameters:
            figures: a list of dictionaries, with each dictionary containing
            'image': image of the figure
            'page': page number of the figure
            batch_size: batch size for inference in all models
        Returns:
            A list of dictionaries, with each dictionary containing
            'smiles': SMILES string of the molecule
            'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
            'image': cropped image of the molecule
            'page': page number of the molecule
        """
        images = [np.asarray(fig['image']) for fig in figures]
        bboxes = self.extract_molecule_bboxes_from_figures(figures, batch_size=batch_size)
        results, cropped, references = clean_bbox_output(images, bboxes)
        smiles = self.molscribe.predict_images(cropped, batch_size=batch_size)
        for i, smi in enumerate(smiles):
            references[i]['smiles'] = smi['smiles']
        final_results = []
        for i in range(len(results)):
            for j in range(len(results[i]['molecules'])):
                results[i]['molecules'][j]['page'] = figures[i]['page']
                final_results.append(results[i]['molecules'][j])
        return final_results
    
    def extract_molecule_corefs_from_figures_in_pdf(self, pdf, batch_size=16, num_pages=None, molscribe = True, ocr = True):
        """
        Get all molecules and their information from a pdf
        Parameters:
            pdf: path to pdf
            batch_size: batch size for inference in all models
            num_pages: process only first `num_pages` pages, if `None` then process all
            molscribe: whether to use molscribe to get SMILES strings
            ocr: whether to use ocr to get text
        Returns:
            A list of dictionaries, with each dictionary containing
            'smiles': SMILES string of the molecule
            'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
            'image': cropped image of the molecule
            'page': page number of the molecule
        """
        pages = pdf2image.convert_from_path(pdf, last_page=num_pages)
        figures = get_figures_from_pages(pages, self.pdfparser)
        return self.extract_molecule_corefs_from_figures(figures, batch_size=batch_size, molscribe=molscribe, ocr=ocr)
        
    def extract_molecule_corefs_from_figures(self, figures, batch_size=16, molscribe=True, ocr=True):
        """
        Get all molecules and their information from figures
        Parameters:
            figures: a list of dictionaries, with each dictionary containing
            'image': image of the figure
            'page': page number of the figure
            batch_size: batch size for inference in all models
            molscribe: whether to use molscribe to get SMILES strings
            ocr: whether to use ocr to get text
        Returns:
            A list of dictionaries, with each dictionary containing
            'smiles': SMILES string of the molecule
            'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
            'image': cropped image of the molecule
            'page': page number of the molecule
        """
        images = [np.asarray(fig['image']) for fig in figures]
        results = self.coref.predict_images(images, batch_size=batch_size)
        if molscribe:
            mol_images = [elt['image'] for res in results for elt in res['mol_bboxes']]
            smiles = self.molscribe.predict_images(mol_images, batch_size=batch_size)
            cur = 0
            for res in results:
                for elt in res['mol_bboxes']:
                    elt['smiles'] = smiles[cur]['smiles']
                    cur += 1
        if ocr:
            for i, result in enumerate(results):
                result['idt_bboxes'] = self.molscribe.ocr.predict_images([b['image'] for b in result['idt_bboxes']],
                                                                    batch_size=batch_size)
                result['text'] = self.molscribe.ocr.predict_images([images[i]], batch_size=batch_size)[0]
        return results

    def extract_reactions_from_figures_in_pdf(self, pdf, batch_size=16, num_pages=None, molscribe=True, ocr=True):
        """
        Get all reactions and their information from a pdf
        Parameters:
            pdf: path to pdf
            batch_size: batch size for inference in all models
            num_pages: process only first `num_pages` pages, if `None` then process all
            molscribe: whether to use molscribe to get SMILES strings for molecules
            ocr: whether to use ocr to get text for other reaction components
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        figures = self.extract_figures_from_pdf(pdf, num_pages=num_pages)
        results = self.extract_reactions_from_figures(figures, batch_size=batch_size, molscribe=molscribe, ocr=ocr)
        
        # for result in results:
        #     result['page'] = figure['page']
        #     if figure['table']['content'] is not None:
        #         content = figure['table']['content']
        #         if len(result['reactions']) > 1:
        #             print("Warning: multiple reactions detected for table")
        #         elif len(result['reactions']) == 0:
        #             continue
        #         orig_reaction = result['reactions'][0]
        #         graphs = get_atoms_and_bonds(figure['figure']['image'], orig_reaction, self.molscribe)
        #         relevant_locs = find_relevant_groups(graphs, content['columns'])
        #         conditions_to_extend = []
        #         for row in content['rows']:
        #             r_groups = {}
        #             expanded_conditions = orig_reaction['conditions'][:]
        #             replaced = False
        #             for col, entry in zip(content['columns'], row):
        #                 if col['tag'] != 'alkyl group':
        #                     expanded_conditions.append({
        #                         'category': '[Table]',
        #                         'text': entry['text'], 
        #                         'tag': col['tag'],
        #                         'header': col['text'],
        #                     })
        #                 else:
        #                     found = re.match(r'^(\w+-)?(?P<group>[\w-]+)( \(\w+\))?$', entry['text'])
        #                     if found is not None:
        _ = [res.pop('diagram_bboxes', None) for res in results]
        return process_tables(figures, results, self.molscribe, batch_size=batch_size)

    def extract_reactions_from_figures(self, figures, batch_size=16, molscribe=True, ocr=True):
        """
        Get all reactions and their information from a list of figures
        Parameters:
            figures: a list of dictionaries, with each dictionary containing
            'image': image of the figure
            'page': page number of the figure
            batch_size: batch size for inference in all models
            molscribe: whether to use molscribe to get SMILES strings for molecules
            ocr: whether to use ocr to get text for other reaction components
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        images = [fig['image'] for fig in figures]
        results = self.rxnscribe.predict_images(images, batch_size=batch_size, molscribe=molscribe, ocr=ocr)
        for result, figure in zip(results, figures):
            result['page'] = figure['page']
        return results

    def extract_molecules_from_text_in_pdf(self, pdf, batch_size=16, num_pages=None):
        """
        Get all molecules and their information from text in a pdf
        Parameters:
            pdf: path to pdf
            batch_size: batch size for inference in all models
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        self.chemner.set_pdf_file(pdf)
        self.chemner.set_pages(num_pages)
        return self.chemner.extract_compounds()


    def extract_reactions_from_text_in_pdf(self, pdf, num_pages=None):
        """
        Get all reactions and their information from text in a pdf
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        self.chemrxnextractor.set_pdf_file(pdf)
        self.chemrxnextractor.set_pages(num_pages)
        return self.chemrxnextractor.extract_reactions_from_text()


    def extract_reactions_from_text_in_pdf_combined(self, pdf, num_pages=None):
        """
        Get all reactions and their information from text in a pdf
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        self.chemrxnextractor.set_pdf_file(pdf)
        self.chemrxnextractor.set_pages(num_pages)
        result = self.chemrxnextractor.extract_reactions_from_text()
        self.chemner.set_pdf_file(pdf)
        self.chemner.set_pages(num_pages)
        compounds = self.chemner.extract_compounds()
        for i in range(len(result)):
            for j in range(len(result[i]['reactions'])):
                for k in range(len(result[i]['reactions'][j]['reactions'])):
                    # print(result[i]['reactions'][j])
                    for m in range(len(result[i]['reactions'][j]['reactions'][k]['products'])):
                        for c in compounds:
                            if result[i]['reactions'][j]['reactions'][k]['products'][m] in c['text']:
                                result[i]['reactions'][j]['reactions'][k]['products'][m] = c['smiles']

        return result
    
    def extract_reactions_from_figures_and_tables_in_pdf(self, pdf, num_pages=None, batch_size=16, molscribe=True, ocr=True):
        """
        Get all reactions and their information from figures in a pdf
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        # pages = pdf2image.convert_from_path(pdf, last_page=num_pages)
        # layout = self.pdfparser.detect(pages[0])
        # text_blocks = lp.Layout([b for b in layout if b.type=='Text'])
        # for txt in text_blocks:
        #     print(txt)
        # return
        figures = self.extract_figures_from_pdf(pdf, num_pages=num_pages)
        # for f in figures:
        #     print(f['page'])
        results = self.extract_reactions_from_figures(figures, batch_size=batch_size, molscribe=molscribe, ocr=ocr)
        return replace_rgroups_in_figure(figures, results, self.extract_molecule_corefs_from_figures(figures), self.molscribe, batch_size=batch_size)


    def extract_reactions_from_pdf(self, pdf, num_pages=None, batch_size=16):
        """
        Get all reactions and their information from a pdf
        Parameters:
            pdf: path to pdf
            num_pages: process only first `num_pages` pages, if `None` then process all
        Returns:
            a dictionary containing
            'reactions': a list of reactions, with each reaction a dictionary containing
                'reactants': a list of reactants
                'conditions': a list of conditions
                'products': a list of products
            'molecules': a list of molecules, with each molecule containing
                'smiles': SMILES string of the molecule
                'bbox': bounding box of the molecule in the format of [x1, y1, x2, y2]
                'image': cropped image of the molecule
                'page': page number of the molecule
        """
        results_from_text = self.extract_reactions_from_text_in_pdf(pdf, num_pages=num_pages)
        figures = self.extract_figures_from_pdf(pdf, num_pages=num_pages)
        results_from_figures = self.extract_reactions_from_figures(figures, batch_size=batch_size)
        results_from_figures = replace_rgroups_in_figure(figures, results_from_figures, self.extract_molecule_corefs_from_figures(figures), self.molscribe, batch_size=batch_size)
        results = backout(results_from_figures, self.extract_molecule_corefs_from_figures(figures), self.molscribe)
        #results = expand_reactions_with_backout(results_from_figures, self.extract_molecule_corefs_from_figures(figures), self.molscribe)
        # for res in results_from_figures:
        #     print(len(res['reactions']))
        #     if len(res['reactions']) > 0:
        #         print(res['reactions'])
        #         print('------------------')
        return {
            'from_text': results_from_text,
            'from_figures': results
        }

class ChemicalExtractionInterface:
    def __init__(self, model_path=None, device=None, output_dir=None):
        """
        Initializes the chemical extraction interface.

        Args:
            model_path (str, optional): Path to the model checkpoint. Defaults to None.
            device (str, optional): Device to run the model on ('cuda' or 'cpu'). Defaults to None.
            output_dir (str, optional): Directory to save output files. Defaults to None.
        """
        self.extractor = OpenChemIE(device=device)
        self.output_dir = output_dir or "results"
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_from_pdf_figures(self, pdf_path, num_pages=None, batch_size=16):
        """
        Extracts chemical reactions from figures in a PDF.

        Args:
            pdf_path (str): Path to the PDF file.
            num_pages (int, optional): Number of pages to process. Defaults to all.
            batch_size (int, optional): Batch size for processing. Defaults to 16.

        Returns:
            dict: Extracted reaction data.
        """
        try:
            results = self.extractor.extract_reactions_from_figures_in_pdf(
                pdf_path, num_pages=num_pages, batch_size=batch_size
            )
            return {"status": "success", "data": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def extract_from_text(self, text_content, num_pages=None):
        """
        Extracts chemical reactions from text content.

        Args:
            text_content (str): Path to a text file or raw text.
            num_pages (int, optional): Not currently used for text, for API consistency.

        Returns:
            dict: Extracted reaction data.
        """
        try:
            # Assuming text_content is a path to a PDF for ChemRxnExtractor
            # This part might need adjustment if raw text is the input
            if os.path.exists(text_content):
                results = self.extractor.extract_reactions_from_text_in_pdf(text_content, num_pages=num_pages)
                return {"status": "success", "data": results}
            else:
                # Placeholder for raw text extraction
                return {"status": "error", "message": "Raw text extraction not yet implemented."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_full_extraction(self, pdf_path, num_pages=None, batch_size=16):
        """
        Performs a full extraction from a PDF, including figures and text.

        Args:
            pdf_path (str): Path to the PDF file.
            num_pages (int, optional): Number of pages to process. Defaults to all.
            batch_size (int, optional): Batch size for processing. Defaults to 16.

        Returns:
            dict: Combined extracted data.
        """
        try:
            results = self.extractor.extract_reactions_from_pdf(
                pdf_path, num_pages=num_pages, batch_size=batch_size
            )
            return {"status": "success", "data": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Chemical Extraction Interface CLI")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--num_pages", type=int, help="Number of pages to process")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size for processing")
    parser.add_argument("--output_file", default="extraction_results.json", help="Output JSON file")
    
    args = parser.parse_args()

    interface = ChemicalExtractionInterface()
    results = interface.run_full_extraction(args.pdf_path, args.num_pages, args.batch_size)

    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=4)

    print(f"Extraction complete. Results saved to {args.output_file}")

if __name__ == "__main__":
    main()
