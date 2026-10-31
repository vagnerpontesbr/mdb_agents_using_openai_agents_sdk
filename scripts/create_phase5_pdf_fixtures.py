"""Render bounded synthetic evaluation sources; no publication or provider calls."""

from pathlib import Path
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from xml.sax.saxutils import escape


def main():
    root=Path('artifacts/phase5/pdf')
    root.mkdir(parents=True,exist_ok=False)
    styles=getSampleStyleSheet()
    documents={}
    for name,filename in [('legacy','legacy-ont-procedure.md'),('current','current-ont-procedure.md')]:
        source=Path('examples/telecom/governance')/filename
        documents[name]=source.read_text().split('---',2)[2].strip()
    documents['wifi']='# Wi-Fi placement\n\nSynthetic evaluation fixture. For indoor wireless coverage, place the router centrally, away from metal cabinets. Wi-Fi placement does not resolve a provisioning alarm E17.'
    documents['invoice']='# Billing support\n\nSynthetic evaluation fixture. To dispute an invoice, ask billing support to review the line item. Billing review does not change the provisioning profile or resolve E17.'
    for name,text in documents.items():
        flow=[]
        for paragraph in text.split('\n\n'):
            heading=paragraph.startswith('# ')
            flow.append(Paragraph(escape(paragraph.lstrip('# ').replace('`','')),
                                  styles['Title'] if heading else styles['BodyText']))
            flow.append(Spacer(1,14))
        SimpleDocTemplate(str(root/f'{name}.pdf'),pagesize=(612,792),
                          leftMargin=54,rightMargin=54,topMargin=54,bottomMargin=54).build(flow)
    print('Four synthetic PDFs created; inspect rendering before extraction.')


if __name__=='__main__': main()
