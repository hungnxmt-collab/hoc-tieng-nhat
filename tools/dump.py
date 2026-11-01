import pdfplumber,sys
f=sys.argv[1]
pdf=pdfplumber.open(f)
for i,p in enumerate(pdf.pages):
    q=p.filter(lambda o: o.get('object_type')!='char' or o['size']>=8)
    print(f'<<<PAGE {i+1}>>>')
    print(q.extract_text(x_tolerance=1.5,y_tolerance=3))
