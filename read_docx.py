import zipfile
import xml.etree.ElementTree as ET

def get_docx_text(path):
    try:
        doc = zipfile.ZipFile(path)
        xml_content = doc.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        # Namespace map
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        paragraphs = []
        for paragraph in root.findall('.//w:p', ns):
            texts = [node.text for node in paragraph.findall('.//w:t', ns) if node.text]
            if texts:
                paragraphs.append("".join(texts))
            else:
                paragraphs.append("")
        return paragraphs
    except Exception as e:
        return [f"Error reading docx: {str(e)}"]

if __name__ == '__main__':
    path = "g:/hoc_tap/python/rs/rs_TA_test.docx"
    paragraphs = get_docx_text(path)
    with open("rs_TA_test.txt", "w", encoding="utf-8") as f:
        for i, p in enumerate(paragraphs):
            f.write(f"[{i}] {p}\n")
    print("Done writing to rs_TA_test.txt")
