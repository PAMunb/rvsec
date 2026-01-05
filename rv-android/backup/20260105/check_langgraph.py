"""Check LangGraph installation structure."""
import sys
import os

# Check LangGraph
try:
    import langgraph
    lg_path = os.path.dirname(langgraph.__file__)
    print(f"✅ LangGraph imported from: {lg_path}")
    print(f"\nContents of {lg_path}:")
    for item in sorted(os.listdir(lg_path)):
        item_path = os.path.join(lg_path, item)
        if os.path.isdir(item_path):
            print(f"  📁 {item}/")
        else:
            print(f"  📄 {item}")
except Exception as e:
    print(f"❌ LangGraph import failed: {e}")

# Check prebuilt module
print("\n" + "="*60)
print("Testing prebuilt imports...")
print("="*60)

try:
    from langgraph import prebuilt
    print(f"✅ from langgraph import prebuilt - SUCCESS")
    print(f"   prebuilt location: {prebuilt.__file__}")
    print(f"   prebuilt contents: {dir(prebuilt)}")
except Exception as e:
    print(f"❌ from langgraph import prebuilt - FAILED: {e}")

try:
    from langgraph.prebuilt import ToolNode
    print(f"✅ from langgraph.prebuilt import ToolNode - SUCCESS")
except Exception as e:
    print(f"❌ from langgraph.prebuilt import ToolNode - FAILED: {e}")

try:
    from langgraph.prebuilt import tools_condition
    print(f"✅ from langgraph.prebuilt import tools_condition - SUCCESS")
except Exception as e:
    print(f"❌ from langgraph.prebuilt import tools_condition - FAILED: {e}")

# Check langgraph-prebuilt package
print("\n" + "="*60)
print("Checking langgraph-prebuilt package...")
print("="*60)

try:
    import langgraph_prebuilt
    print(f"✅ langgraph_prebuilt imported")
    print(f"   Location: {langgraph_prebuilt.__file__}")
except Exception as e:
    print(f"❌ langgraph_prebuilt import failed: {e}")

# Check site-packages
print("\n" + "="*60)
print("Site-packages check...")
print("="*60)
venv_path = sys.prefix
print(f"Virtual environment: {venv_path}")
print(f"Python version: {sys.version}")
py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
site_packages = os.path.join(venv_path, 'lib', py_version, 'site-packages')
print(f"Site-packages: {site_packages}")

if os.path.exists(site_packages):
    langgraph_items = [item for item in os.listdir(site_packages) if 'langgraph' in item.lower()]
    print(f"\nLangGraph-related packages:")
    for item in sorted(langgraph_items):
        print(f"  - {item}")
