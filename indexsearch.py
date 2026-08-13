import bm25s
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("./docs/pdfs/coi.pdf")
pages = loader.load()[31:100]
# text = "\n".join([page.page_content for page in pages])

splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1000,chunk_overlap=200,separators=["\n\n"]
)

chunks = [chunk.page_content for chunk in splitter.split_documents(pages)]

class IndexSearch:
    def __init__(self,retriver:bm25s.BM25=None):
        if retriver is None:
            self.retriver = retriver
        else:
            self.retriver = bm25s.BM25()
    @classmethod
    def load(cls,path) -> "IndexSearch":
        retriver = bm25s.BM25()
        retriver.load(path)
        return cls(retriver)
    def search(self,query:str,k:int=5):
        query_token = bm25s.tokenize([query],stopwords="en")
        result = self.retriver.retrieve(query_token,k=k)
        return result
    def index(self,documents):
        self.retriver.index(documents)
    def save(self,path):
        self.retriver.save(path)