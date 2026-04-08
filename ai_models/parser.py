import xml.etree.ElementTree as ET

def parse_report(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    findings = root.find(".//FINDINGS")
    impression = root.find(".//IMPRESSION")

    return {
        "findings": findings.text if findings is not None else "",
        "impression": impression.text if impression is not None else ""
    }