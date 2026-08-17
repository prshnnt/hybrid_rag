from reranker import search
def main():
    print("Search For Document Chunks--")
    query = input("Enter the search query: ")
    results = search(query=query)
    for r in results:
        print("Document : ",r)

if __name__ == "__main__":
    main()
