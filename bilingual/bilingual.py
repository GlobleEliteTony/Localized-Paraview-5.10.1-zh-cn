# ParaView 5.10.1 bilingual presentation layer. Does not rewrite proxy values.
import os,sys,re,json,traceback,html
ROOT=os.environ.get('PARAVIEW_BILINGUAL_ROOT') or os.getcwd()
BIN=os.environ.get('PARAVIEW_BILINGUAL_BIN') or ROOT+'/ParaView 5.10.1/bin'
LOG=os.path.join(ROOT,'logs');os.makedirs(LOG,exist_ok=True)
sys.path.insert(0,ROOT+'/runtime')
_dll_handles=[os.add_dll_directory(p) for p in [ROOT+'/runtime/shiboken2',ROOT+'/runtime/PySide2',BIN]]
from PySide2 import QtCore,QtGui,QtWidgets
G=json.load(open(ROOT+'/machine.json',encoding='utf8')) if os.path.exists(ROOT+'/machine.json') else {}
for line in open(ROOT+'/glossary.txt',encoding='utf-8-sig'):
 if '|' in line:
  en,zh=line.strip().split('|',1);G[en]=zh
NORMALIZED={re.sub(r'\s+',' ',k.replace('&','')).strip():v for k,v in G.items()}
unknown=set();seen=set()
def translate(text):
 if not text or re.search('[\u4e00-\u9fff]',text):return text
 if '<' in text and '>' in text and re.search(r'<[a-zA-Z/]',text):
  return re.sub(r'>([^<>]+)<',lambda m:'>'+translate(m[1])+'<',text)
 if '\t' in text:
  label,shortcut=text.split('\t',1);return translate(label)+'\t'+shortcut
 m=re.match(r'^(Layout #)(\d+)$',text)
 if m:return '布局 '+m[2]+'（'+text+'）'
 m=re.match(r'^(First Frame|Last Frame) (\(.*\))$',text)
 if m:return ('第一帧' if m[1]=='First Frame' else '最后一帧')+m[2]+'（'+text+'）'
 key=text.replace('&','').strip()
 if key in G:
  if not re.search('[\u4e00-\u9fff]',G[key]):return text
  seen.add(key);return G[key]+'（'+text+'）'
 suffix=''
 for ending in ('...', '\u2026', ':'):
  if key.endswith(ending):key=key[:-len(ending)].rstrip();suffix=ending;break
 zh=G.get(key) or G.get(key[:1].upper()+key[1:]) or NORMALIZED.get(re.sub(r'\s+',' ',key))
 if zh and re.search('[\u4e00-\u9fff]',zh):
  seen.add(key)
  # Keep original accelerators and punctuation in the English half.
  return zh+'（'+text+'）'
 m=re.match(r'^Requires (?:a |an )?(any-except-field|point|cell) attribute array(?: with (\d+) component\(s\))?$',text)
 if m:
  kind={'any-except-field':'非场数据','point':'点','cell':'单元'}[m[1]]
  return '需要'+kind+'属性数组'+('（'+m[2]+' 个分量）' if m[2] else '')+'（'+text+'）'
 if re.search('[A-Za-z]{3}',text) and len(text)<250:unknown.add(text)
 return text
OPTION_TYPES=[QtWidgets.QStyleOptionMenuItem,QtWidgets.QStyleOptionButton,QtWidgets.QStyleOptionComboBox,QtWidgets.QStyleOptionTab,QtWidgets.QStyleOptionHeader,QtWidgets.QStyleOptionToolButton,QtWidgets.QStyleOptionGroupBox,QtWidgets.QStyleOptionViewItem]
class BilingualStyle(QtWidgets.QProxyStyle):
 def option(self,opt):
  for cls in OPTION_TYPES:
   if isinstance(opt,cls):
    copy=cls(opt)
    prop='currentText' if isinstance(copy,QtWidgets.QStyleOptionComboBox) else 'text'
    if hasattr(copy,prop):setattr(copy,prop,translate(getattr(copy,prop)))
    return copy
  return opt
 def drawControl(self,e,opt,p,w=None):return super().drawControl(e,self.option(opt),p,w)
 def drawComplexControl(self,e,opt,p,w=None):return super().drawComplexControl(e,self.option(opt),p,w)
 def sizeFromContents(self,t,opt,size,w=None):
  # Let Qt compute menu/tab/button geometry from the bilingual display string.
  new=self.option(opt)
  out=super().sizeFromContents(t,new,size,w)
  prop='currentText' if isinstance(new,QtWidgets.QStyleOptionComboBox) else 'text'
  if hasattr(new,prop) and hasattr(opt,prop):
   a=getattr(opt,prop);b=getattr(new,prop)
   if a!=b:
    delta=opt.fontMetrics.horizontalAdvance(b)-opt.fontMetrics.horizontalAdvance(a)
    out.setWidth(max(out.width(),size.width()+max(0,delta)))
  return out
 def drawItemText(self,p,rect,flags,palette,enabled,text,role=QtGui.QPalette.NoRole):
  return super().drawItemText(p,rect,flags,palette,enabled,translate(text),role)
class BilingualTranslator(QtCore.QTranslator):
 def __init__(self):
  super().__init__();self.qt=QtCore.QTranslator();self.qt.load(ROOT+'/runtime/PySide2/translations/qt_zh_CN.qm')
 def translate(self,context,sourceText,disambiguation=None,n=-1):
  new=translate(sourceText)
  if new!=sourceText:return new
  zh=self.qt.translate(context,sourceText,disambiguation,n)
  return zh+'（'+sourceText+'）' if zh and zh!=sourceText and re.search('[\u4e00-\u9fff]',zh) else ''
app=QtWidgets.QApplication.instance()
translator=BilingualTranslator();app.installTranslator(translator)
style=BilingualStyle(QtWidgets.QStyleFactory.create(app.style().objectName()))
app.setStyle(style)
_font=QtGui.QFont('Microsoft YaHei UI');_font.setPixelSize(13);app.setFont(_font)
app.setStyleSheet('QTabBar::tab { min-width: 175px; min-height: 23px; }')
# QLabel and group boxes compute their own size hints from source text; update
# these descriptive widgets only. Models, actions, combo entries and proxy values
# retain their original English data and are translated solely while painting.
class BilingualComboDelegate(QtWidgets.QStyledItemDelegate):
 def displayText(self,value,locale):
  return translate(super().displayText(value,locale))
 def paint(self,painter,option,index):
  opt=QtWidgets.QStyleOptionViewItem(option)
  self.initStyleOption(opt,index)
  opt.text=translate(opt.text)
  widget=option.widget
  painter.save()
  (widget.style() if widget else app.style()).drawControl(QtWidgets.QStyle.CE_ItemViewItem,opt,painter,widget)
  painter.restore()
 def sizeHint(self,option,index):
  result=super().sizeHint(option,index)
  raw=str(index.data(QtCore.Qt.DisplayRole) or '')
  result.setWidth(max(result.width(),option.fontMetrics.horizontalAdvance(translate(raw))+36))
  return result

def ensure_combo_popup(combo):
 # Translate only the delegate's paint options. Never replace DisplayRole or
 # itemText: ParaView uses the English strings as representation/material keys.
 if not isinstance(combo.itemDelegate(),BilingualComboDelegate):
  delegate=BilingualComboDelegate(combo.view())
  combo.setItemDelegate(delegate)
  combo._pv_bilingual_delegate=delegate
  combo.view().setTextElideMode(QtCore.Qt.ElideNone)
  combo.view().setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
 if combo.count():
  fm=combo.fontMetrics()
  width=max(fm.horizontalAdvance(translate(combo.itemText(i))) for i in range(combo.count()))+54
  screen=combo.screen()
  if screen:width=min(width,max(200,screen.availableGeometry().width()-60))
  combo.view().setMinimumWidth(max(combo.width(),width))

class Refresh(QtCore.QObject):
 def tick(self):
  try:
   for w in app.allWidgets():
    if isinstance(w,QtWidgets.QComboBox):ensure_combo_popup(w)
    f=w.font()
    if f.pixelSize()!=13:
     f.setPixelSize(13);f.setFamily('Microsoft YaHei UI');w.setFont(f)
    for a in w.actions():
     old=a.text();new=translate(old)
     if new!=old:a.setText(new)
     for prop,setter in [('toolTip','setToolTip'),('statusTip','setStatusTip')]:
      old=getattr(a,prop)();new=translate(old)
      if new!=old:getattr(a,setter)(new)
    if isinstance(w,QtWidgets.QAbstractButton):
     old=w.text();new=translate(old)
     if new!=old:w.setText(new)
    if isinstance(w,QtWidgets.QTabWidget):
     for i in range(w.count()):
      old=w.tabText(i);new=translate(old)
      if new!=old:w.setTabText(i,new)
    if isinstance(w,QtWidgets.QLineEdit):
     old=w.placeholderText();new=translate(old)
     if new!=old:w.setPlaceholderText(new)
    for prop,setter in [('toolTip','setToolTip'),('statusTip','setStatusTip')]:
     old=getattr(w,prop)();new=translate(old)
     if new!=old:getattr(w,setter)(new)
    if isinstance(w,QtWidgets.QTabBar):
     w.setExpanding(False);w.setElideMode(QtCore.Qt.ElideNone)
     for i in range(w.count()):
      old=w.tabText(i);new=translate(old)
      if new!=old:w.setTabText(i,new)
    if isinstance(w,QtWidgets.QLabel):
     old=w.text();new=translate(old)
     if new!=old:w.setText(new)
    elif isinstance(w,QtWidgets.QGroupBox):
     old=w.title();new=translate(old)
     if new!=old:w.setTitle(new)
   with open(LOG+'/coverage.json','w',encoding='utf8') as f:
    json.dump({'translated':sorted(seen),'untranslated':sorted(unknown)},f,ensure_ascii=False,indent=2)
  except:open(LOG+'/runtime-error.txt','a').write(traceback.format_exc())
refresh=Refresh();timer=QtCore.QTimer();timer.timeout.connect(refresh.tick);timer.start(1200)
def ready():
 refresh.tick()
 for w in app.topLevelWidgets():
  if w.objectName()=='pqClientMainWindow':
   w.setWindowTitle('ParaView 5.10.1 - 中文双语（Chinese / English）');w.show();
   if os.environ.get('PARAVIEW_BILINGUAL_SCREENSHOT'):w.grab().save(os.environ['PARAVIEW_BILINGUAL_SCREENSHOT'])
QtCore.QTimer.singleShot(7000,ready)


_foam=os.environ.get('PARAVIEW_BILINGUAL_FOAM')
if _foam:
 from paraview.simple import OpenFOAMReader,Show,GetActiveViewOrCreate,Render
 _reader=OpenFOAMReader(registrationName=os.path.basename(os.environ.get('PARAVIEW_BILINGUAL_FOAM_ORIGINAL') or _foam),FileName=_foam)
 _view=GetActiveViewOrCreate('RenderView');Show(_reader,_view);_view.ResetCamera();Render(_view)
_user_script=os.environ.get('PARAVIEW_BILINGUAL_USER_SCRIPT')
if _user_script:
 import tokenize
 with tokenize.open(_user_script) as _f:_user_code=_f.read()
 exec(compile(_user_code,_user_script,'exec'),globals(),globals())
