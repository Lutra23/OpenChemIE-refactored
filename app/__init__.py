"""OpenChemIE - Chemical Information Extraction Package"""

__version__ = "2.0.0"
__author__ = "OpenChemIE Team"
__email__ = "contact@openchemie.org"

from app.core.extractor import OpenChemIEExtractor
from app.core.interface import ChemicalExtractionInterface

__all__ = [
    "OpenChemIEExtractor", 
    "ChemicalExtractionInterface"
]