import asyncio
import os
import sys
import json
from pathlib import Path

# Setup Project Paths
BACKEND_ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(BACKEND_ROOT))

async def test_rag_and_ingestion():
    print("🚀 Starting Backend Feature Verification...\n")
    
    # --- 1. Test PDF Extraction ---
    print("💎 Testing PDF Extraction logic...")
    # Import from backend/mcp_servers
    try:
        from mcp_servers.server_rag_civic import convert_pdf_to_markdown
        
        # Find a sample PDF in backend/data
        data_dir = BACKEND_ROOT / "data"
        sample_pdfs = list(data_dir.rglob("*.pdf"))
        
        if sample_pdfs:
            sample_pdf = sample_pdfs[0]
            print(f"📄 Found local sample PDF: {sample_pdf.name}")
            try:
                extraction = convert_pdf_to_markdown(str(sample_pdf))
                if extraction.markdown and "PAGE_START" in extraction.markdown:
                    print(f"✅ PDF Extraction successful. Content length: {len(extraction.markdown)}")
                else:
                    print("❌ PDF Extraction failed or returned empty content.")
            except Exception as e:
                print(f"❌ PDF Extraction error: {e}")
        else:
            print("⚠️ No sample PDF found to test extraction.")
    except ImportError as e:
        print(f"❌ Failed to import server_rag_civic: {e}")

    # --- 2. Test Web Extraction ---
    print("\n🌍 Testing Web Extraction logic...")
    try:
        from mcp_servers.server_rag_civic import extract_web_content_civic
        
        # Test with a simple static page
        test_url = "https://trafilatura.readthedocs.io/en/latest/" 
        try:
            web_content = extract_web_content_civic(test_url)
            if web_content and len(web_content) > 100:
                print(f"✅ Web Extraction successful. Content length: {len(web_content)}")
            else:
                print(f"⚠️ Web extraction result: {web_content}")
        except Exception as e:
            print(f"❌ Web Extraction error: {e}")
    except ImportError as e:
        print(f"❌ Failed to import extract_web_content_civic: {e}")

    # --- 3. Test RAG Search ---
    print("\n🔍 Testing Civic RAG Search...")
    try:
        from mcp_servers.server_rag_civic import search_stored_documents_rag_civic
        
        # Mock a search query
        query = "civic lens"
        results = search_stored_documents_rag_civic(query)
        
        if results and isinstance(results, list) and not any("Error" in str(r) for r in results):
            print(f"✅ RAG Search successful. Found {len(results)} matches.")
            for i, res in enumerate(results[:2]):
                print(f"   Match {i+1}: {res[:100]}...")
        else:
            print(f"⚠️ RAG Search result: {results}")
    except ImportError as e:
        print(f"❌ Failed to import search_stored_documents_rag_civic: {e}")
    except Exception as e:
        print(f"❌ RAG Search error: {e}")

    # --- 4. Test Service Pathing ---
    print("\n📂 Testing LibrarianService Pathing...")
    try:
        from services.librarian_service import LibrarianService
        
        service = LibrarianService()
        print(f"✅ LibrarianService initialized.")
        print(f"   Data Dir: {service.data_dir}")
        print(f"   Index Dir: {service.index_dir}")
        
        if service.data_dir.exists() and service.index_dir.exists():
            print("✅ Deployment paths verified.")
        else:
            print("❌ Deployment paths MISSING or INACCESSIBLE.")
    except ImportError as e:
        print(f"❌ Failed to import LibrarianService: {e}")
    except Exception as e:
        print(f"❌ LibrarianService initialization error: {e}")

    print("\n🏁 Feature Verification Completed!")

if __name__ == "__main__":
    asyncio.run(test_rag_and_ingestion())
