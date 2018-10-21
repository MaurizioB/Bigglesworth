#!/usr/bin/env python2.7

import os, shutil, sys
from commands import getoutput
from xml.etree import ElementTree as et

os.environ['QT_PREFERRED_BINDING'] = 'PyQt4'
from Qt import QtWidgets
app = QtWidgets.QApplication(sys.argv)

from makecurves import buildHtml, doCurves

pwd = os.path.dirname(os.path.realpath(__file__)) + '/'
srcPath = os.path.join(pwd, 'Bigglesworth/')
destPath = os.path.join(pwd, 'html/')
curvePath = os.path.join(pwd, '../resources/curves')

with open(os.path.join(srcPath, 'Wavetable Editor', 'CURVES'), 'w') as CURVES:
    CURVES.write(buildHtml())

curveFiles = doCurves()
for cf in curveFiles:
    os.remove(os.path.join(curvePath, cf))
    shutil.move(cf, curvePath)

if os.path.exists(destPath):
    shutil.rmtree(destPath)



qhcpContents = '''<?xml version="1.0" encoding="utf-8" ?>
<QHelpCollectionProject version="1.0">
    <docFiles>
        <generate>
            <file>
                <input>main.qhp</input>
                <output>main.qch</output>
            </file>
        </generate>
        <register>
            <file>main.qch</file>
        </register>
    </docFiles>
</QHelpCollectionProject>
'''

qhfContents = '''<?xml version="1.0" encoding="UTF-8"?>
<QtHelpProject version="1.0">
    <namespace>jidesk.net.Bigglesworth.1.0</namespace>
    <virtualFolder>html</virtualFolder>
    <customFilter name="Bigglesworth 1.0">
        <filterAttribute>Bigglesworth</filterAttribute>
    </customFilter>
    <filterSection>
        <filterAttribute>Bigglesworth</filterAttribute>
        <toc>
            <section title="Bigglesworth Manual" ref="index.html">
{sections}
            </section>
        </toc>
        <keywords>
{keywords}
        </keywords>
        <files>
            <file>main.css</file>
{files}
        </files>
    </filterSection>
</QtHelpProject>
'''


_Template = '''%(head_prefix)s
%(head)s
%(stylesheet)s
%(body_prefix)s
{top}
%(body_pre_docinfo)s
%(docinfo)s
{prebody}
%(body)s<br/>
%(body_suffix)s
'''

rootTemplate = _Template.format(top='{docPath}<br/>', prebody='''
<h4 class="section">Contents:</h4>
<div class="toc">{subIndex}</div>
''')

baseTemplate = _Template.format(top='{docPath}', prebody='')

indexContents = {}
sections = []
filePaths = []

def getPathHref(docPath):
    link = '/'.join('..' for s in docPath)
    text = '/ <a href=".{}/index.html">{}</a> / '.format(link, docPath[0])
    for level, d in enumerate(docPath[1:]):
        link = '/'.join('..' for s in range(len(docPath[2:]) - level))
        text += '<a href=".{}/index.html">{}</a> / '.format(link, d)
    return text.replace('...', '.')

def getContentsHref(docPath, section):
    contents = '<ol>\n'
    for fileName, title in indexContents[section]:
        link = '/'.join('..' for s in docPath[1:])
        contents += '<li><a href=".{}/{}">{}</a></li>\n'.format(
            link, 
            fileName, 
            title
            )
    contents += '</ol>'
    return contents.replace('...', '.')

def getRootContents():
    contents = '<ul>\n'
    for section in sections:
        contents += '<li><a href="{0}/index.html">{0}</a>\n<ol>\n'.format(section)
        for fileName, title in indexContents[section]:
            contents += '\t<li><a href="{}/{}">{}</a></li>\n'.format(
            section,  
            fileName, 
            title
            )
        contents += '</ol>\n</li>\n'
    for fileName, title in indexContents['Bigglesworth']:
        contents += '\t<li><a href="{}">{}</a></li>\n'.format(
        fileName, 
        title
        )
    contents += '</ul>\n'
    return contents

keywords = {}

def findKeywords(htmlPath):
    _root = et.parse(htmlPath)
    _head = _root.getiterator('{http://www.w3.org/1999/xhtml}head')[0]
    for _meta in _head.findall('{http://www.w3.org/1999/xhtml}meta'):
        if _meta.get('name') == 'keyword':
            keywords[_meta.get('content')] = htmlPath
            break

#create contents
_sectionSort = {}

for dirPath, dirs, files in os.walk(srcPath):
    docPath = dirPath[len(pwd):].rstrip('/').split('/')
    section = docPath[-1]
    templatePath = os.path.join(dirPath, 'baseTemplate')
    with open(templatePath, 'w') as bt:
        bt.write(baseTemplate.format(docPath=getPathHref(docPath)))
    htmlFiles = []
    for subDir in dirs:
        os.makedirs(os.path.join(destPath, *docPath[1:]) + subDir)
    for fileName in files:
        if fileName == 'sort':
            with open(os.path.join(dirPath, fileName)) as sf:
                i = int(sf.readlines()[0])
                _sectionSort[i] = section
#                sections.insert(i, section)
        elif fileName == 'index.rst':
            continue
        elif fileName.endswith('.rst'):
            rstFileName = os.path.join(dirPath, fileName)
            with open(rstFileName, 'r') as fi:
                lines = fi.readlines()
                if lines:
                    splitName = fileName[:-4].split('-')
                    print(fileName, splitName)
                    index = int(splitName[0])
                    htmlName = '-'.join(splitName[1:]) + '.html'
                    htmlFiles.append((index, htmlName, lines[0].rstrip('\n')))
                    htmlPath = os.path.join(os.path.join(destPath, *docPath[1:]), htmlName)
                    output = getoutput('rst2html.py --template "{t}" --stylesheet=/html/main.css --link-stylesheet "{src}" "{dest}"'.format(
                        t=templatePath, 
                        src=rstFileName, 
                        dest=htmlPath
                        ))
                    if output:
                        print('Error?\n{}'.format(output))
                    else:
                        findKeywords(htmlPath)
                    print(htmlPath)
                    filePaths.append(htmlPath)
    htmlFiles.sort(key=lambda c: c[0])
    indexContents[section] = [(h, t) for _, h, t in htmlFiles]

sections = [_sectionSort[s] for s in sorted(_sectionSort.keys())]

#create indexes
for dirPath, dirs, files in os.walk(srcPath):
    docPath = dirPath[len(pwd):].rstrip('/').split('/')
    section = docPath[-1]
    templatePath = os.path.join(dirPath, 'rootTemplate')
    
    if len(docPath) == 1:
        contents = getRootContents()
    else:
        contents = getContentsHref(docPath, section)
    with open(templatePath, 'w') as rt:
        rt.write(rootTemplate.format(
            docPath=getPathHref(docPath), 
            section=section, 
            subIndex=contents
            ))
    for f in files:
        if f == 'index.rst':
            htmlPath = os.path.join(os.path.join(destPath, *docPath[1:]), 'index.html')
            output = getoutput('rst2html.py --template "{t}" --stylesheet=/html/main.css --table-style="borderless" --link-stylesheet "{src}" "{dest}"'.format(
                t=templatePath, 
                src=os.path.join(dirPath, f), 
                dest=htmlPath
                ))
            if output:
                print('Error?\n{}'.format(output))
            else:
                findKeywords(htmlPath)
            filePaths.append(htmlPath)

qhfSections = ''
for section in sections:
    qhfSections += '\t\t\t\t<section title="{0}" ref="{0}/index.html">\n'.format(section)
    for fileName, title in indexContents[section]:
        qhfSections += '\t\t\t\t\t<section title="{}" ref="{}/{}"/>\n'.format(
        title,  
        section, 
        fileName
        )
    qhfSections += '\t\t\t\t</section>\n'
for fileName, title in indexContents['Bigglesworth']:
    qhfSections += '\t\t\t\t\t<section title="{}" ref="{}"/>\n'.format(
    title,  
    fileName
    )

qhfFiles = ''
for f in filePaths:
    qhfFiles += '\t\t\t<file>{}</file>\n'.format(f[len(destPath):])

qhfKeywords = ''
for k, v in keywords.items():
    qhfKeywords += '\t\t\t<keyword id="{}" ref="{}"/>\n'.format(k, v[len(destPath):])

shutil.copyfile('main.css', 'html/main.css')

with open('html/bigglesworth.qhp', 'w') as qhcp:
    qhcp.write(qhfContents.format(sections=qhfSections, files=qhfFiles, keywords=qhfKeywords))

print(getoutput('qcollectiongenerator bigglesworth.qhcp -o bigglesworth.qhc'))
shutil.copyfile('bigglesworth.qhc', '../bigglesworth/help.qhc')
shutil.copyfile('help.qch', '../bigglesworth/help.qch')

print(indexContents)

#import helpTest
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../bigglesworth'))
from help import HelpDialog
w = HelpDialog()
w.show()
sys.exit(app.exec_())

