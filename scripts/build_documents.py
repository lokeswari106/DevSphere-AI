"""Build the college report and UML handbook from repository documentation."""
import argparse,json,re
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.section import WD_SECTION_START,WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output';OUT.mkdir(exist_ok=True)

def base():
 d=Document()
 for border in list(d.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
 s=d.sections[0];s.page_width=Inches(8.27);s.page_height=Inches(11.69)
 s.top_margin=s.bottom_margin=Inches(.72);s.left_margin=s.right_margin=Inches(.8)
 for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
  style=d.styles[name];style.font.name='Calibri';style.font.color.rgb=RGBColor(0,0,0)
 d.styles['Normal'].font.size=Pt(10.5);d.styles['Normal'].paragraph_format.space_after=Pt(7)
 d.styles['Normal'].paragraph_format.line_spacing=1.08
 for name,size in [('Title',30),('Heading 1',20),('Heading 2',15),('Heading 3',12)]:
  d.styles[name].font.size=Pt(size);d.styles[name].paragraph_format.keep_with_next=True
 d.core_properties.author='DevSphere AI Project';d.core_properties.subject='Final-year software engineering project'
 return d

def add_picture(d,path,maxw=6.6,maxh=7.5):
 with Image.open(path) as im:w,h=im.size
 scale=min(maxw/w,maxh/h)
 d.add_picture(str(path),width=Inches(w*scale),height=Inches(h*scale))
 # Alternative text for readers.
 el=d.inline_shapes[-1]._inline.docPr;el.set('descr',path.stem.replace('-',' '))

def add_table(d,rows):
 t=d.add_table(rows=0,cols=len(rows[0]));t.style='Table Grid'
 for n,row in enumerate(rows):
  cells=t.add_row().cells
  for c,text in zip(cells,row):
   c.text=text
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(4)
    for r in p.runs:r.font.size=Pt(9);r.bold=n==0
   tcPr=c._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
   for side in ['top','left','bottom','right']:
    v=OxmlElement('w:'+side);v.set(qn('w:w'),'90');v.set(qn('w:type'),'dxa');m.append(v)
   tcPr.append(m)
  if n==0:
   rep=OxmlElement('w:tblHeader');t.rows[-1]._tr.get_or_add_trPr().append(rep)
 borders=OxmlElement('w:tblBorders')
 for side in ['top','left','bottom','right','insideH','insideV']:
  e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D7DCDA');borders.append(e)
 t._tbl.tblPr.append(borders)
 return t

def inline(p,text):
 # Keep documentation URLs visible in an offline document.
 text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text)
 for part in re.split(r'(\*\*.*?\*\*|`[^`]+`)',text):
  if not part:continue
  r=p.add_run(part[2:-2] if part.startswith('**') else part[1:-1] if part.startswith('`') else part)
  if part.startswith('**'):r.bold=True
  if part.startswith('`'):r.font.name='Consolas';r.font.size=Pt(9)

def markdown(d,path):
 lines=path.read_text().splitlines();i=0;pagebreak=False
 while i<len(lines):
  line=lines[i];i+=1
  if not line.strip():continue
  if line=='<!-- pagebreak -->':pagebreak=True;continue
  if line.startswith('```'):
   block=[]
   while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
   i+=1
   for text in block:
    p=d.add_paragraph();p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1
    r=p.add_run(text);r.font.name='Consolas';r.font.size=Pt(8)
   d.add_paragraph();continue
  if line.startswith('|'):
   rows=[line]
   while i<len(lines) and lines[i].startswith('|'):rows.append(lines[i]);i+=1
   values=[[c.strip().replace('`','') for c in r.strip().strip('|').split('|')] for r in rows if not re.match(r'^\|[ :|\-]+\|$',r)]
   add_table(d,values);continue
  image=re.match(r'!\[([^]]*)\]\(([^)]+)\)',line)
  if image:
   target=path.parent/image[2]
   if target.exists():add_picture(d,target,maxh=4.5);d.add_paragraph(image[1],style='Caption')
   continue
  if line.startswith('#'):
   n=len(line)-len(line.lstrip('#'));p=d.add_heading(line[n:].strip(),level=min(n,3))
   if pagebreak:p.paragraph_format.page_break_before=True;pagebreak=False
   continue
  if line.startswith('- '):inline(d.add_paragraph(style='List Bullet'),line[2:]);continue
  if re.match(r'^\d+\. ',line):inline(d.add_paragraph(style='List Number'),re.sub(r'^\d+\. ','',line));continue
  inline(d.add_paragraph(),line)

def uml():
 d=base();d.add_paragraph('DevSphere AI',style='Title');d.add_paragraph('UML and Workflow Handbook',style='Subtitle')
 d.add_paragraph('Advanced Intelligent Software Engineering Assistant')
 d.add_paragraph('Fourteen UML diagram families and the PostgreSQL ER model. Editable PlantUML, SVG and PNG files accompany this handbook.')
 d.add_heading('Diagram index',level=1)
 entries=json.loads((ROOT/'docs/diagrams/index.json').read_text())
 for idx,e in enumerate(entries,1):d.add_paragraph(f'{idx:02d}  {e["title"]}')
 d.add_paragraph('Object and timing views are illustrative design examples. Actual runtime evidence is recorded separately in the testing report.')
 for e in entries:
  img=ROOT/'docs/diagrams'/f'{e["file"]}.png'
  with Image.open(img) as im:w,h=im.size
  landscape=w/h>1.45
  s=d.add_section(WD_SECTION_START.NEW_PAGE);s.orientation=WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
  s.page_width=Inches(11.69 if landscape else 8.27);s.page_height=Inches(8.27 if landscape else 11.69)
  d.add_heading(e['title'],level=1);d.add_paragraph(e['explanation'])
  add_picture(d,img,maxw=10.0 if landscape else 6.6,maxh=5.15 if landscape else 8.0)
  p=d.add_paragraph('Editable source: docs/diagrams/'+e['file']+'.puml');p.runs[0].font.size=Pt(8)
 d.save(OUT/'DevSphere-AI-UML-Handbook.docx')

def report():
 d=base();d.add_paragraph('DevSphere AI',style='Title');d.add_paragraph('Intelligent Software Engineering Assistant',style='Subtitle')
 d.add_paragraph('Final-year project report and implementation guide')
 d.add_paragraph('React JavaScript • FastAPI • PostgreSQL • Eight specialized AI agents')
 d.add_paragraph('Release 1.0 | November 2026')
 d.add_paragraph('Includes architecture, implementation, operating steps, actual validation evidence and deployment guidance. The companion UML handbook contains every requested diagram family.')
 d.add_page_break();markdown(d,ROOT/'docs/10-final-project-report.md')
 d.save(OUT/'DevSphere-AI-Project-Report.docx')

parser=argparse.ArgumentParser();parser.add_argument('--uml-only',action='store_true');args=parser.parse_args()
uml()
if not args.uml_only:report()
print('Documents saved in',OUT)
