import opendataloader_pdf as odlp
from typing import List

class Convert:
    @staticmethod
    def pdf_to_markdown(path:str|List[str],output_dir="output/"):
        """
        Convert PDF(s) into the requested output format(s).
        
            Args:
                input_path: One or more input PDF file paths or directories
                output_dir: Directory where output files are written. Default: input file directory
        """
        odlp.convert(input_path=path,output_dir=output_dir,format="markdown")