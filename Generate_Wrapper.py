#!/usr/bin/env python3
# Created by Lin Min
# Edits by Sean Pesce tagged with '@SP'

import os.path;
import sys;
import subprocess as sub
import re;
import shutil;
import time;

# Info
print('Wrapper Generator. Copyright (C) Lin Min\n');

# Get the input parameters first.
dllname = sys.argv[1];

# @SP: Check for optional arguments:
use_default_directory = False;
allow_chains = False;
if len(sys.argv) > 2 and sys.argv[2].lower()=='-usesysdir': # @SP: Check if the user would like the C++ project to load the original DLL from the system directory
	use_default_directory = True;
	print('Wrapper will load original DLL from default system directory.');
elif len(sys.argv) > 2 and sys.argv[2].lower()=='-allowchains': # @SP: Check if the user would like the C++ project to allow DLL chaining with additional DLL wrappers
	allow_chains = True;
	print('Wrapper will allow DLL chaining.');
print('\n');

# Check whether is a dll file.
if not dllname.endswith('.dll'):
	print('You should pass a dll file to this program!');
	sys.exit(1);

# Check whether the dll file specified exists.
if os.path.exists(dllname):
	print('#############################')
	print('Reading dll file ...');
else:
	print('The Specified file \"'+dllname+'\" does not exist!');
	sys.exit(1);

# Check Architecture
architecture = 'Unknown';
p = sub.Popen('dumpbin_tools/dumpbin.exe /headers '+dllname,stdout=sub.PIPE,stderr=sub.PIPE);
output, errors = p.communicate();
output = output.decode('utf-8');
if 'x86' in output:
	print('x86 dll detected ...');
	architecture = 'x86';
elif 'x64' in output:
	print('x64 dll detected ...');
	architecture = 'x64';
else:
	print('invalid dll file, exiting ...');
	
# Get Export List
p = sub.Popen('dumpbin_tools/dumpbin.exe /exports '+dllname,stdout=sub.PIPE,stderr=sub.PIPE);
output, errors = p.communicate();
output = output.decode('utf-8');
lines = output.split('\r\n');
start = 0; idx1 = 0; idx2 = 0; idx3 = 0; idx4 = 0; LoadNames = []; WrapFcn = []; DefItem = [];
for line in lines:
	if 'ordinal' in line and 'hint' in line and 'RVA' in line and 'name' in line:
		start = 1;
		idx1 = line.find('ordinal');
		idx2 = line.find('hint');
		idx3 = line.find('RVA');
		idx4 = line.find('name');
		continue;
	if start == 1:
		start = 2;
		continue;
	if start == 2:
		if len(line) == 0:
			break;
		splt = re.compile("\s+").split(line.strip());

		if len(splt) > 3 and splt[3] == "(forwarded":
			splt = splt[:-3]

		ordinal = splt[0];
		fcnname = splt[-1];
		if fcnname == '[NONAME]':
			LoadNames.append( '(LPCSTR)'+ordinal );
			WrapFcn.append('ExportByOrdinal'+ordinal);
			DefItem.append('ExportByOrdinal'+ordinal+' @'+ordinal+' NONAME');
		else:
			LoadNames.append( '\"'+fcnname+'\"' );
			WrapFcn.append(fcnname+'_wrapper');
			DefItem.append(fcnname+'='+fcnname+'_wrapper'+' @'+ordinal);
			
# Generate Def File
print('Generating .def File');
f = open(dllname.replace('.dll','.def'),'w');
f.write('LIBRARY '+dllname+'\n');
f.write('EXPORTS\n');
for item in DefItem:
	f.write('\t'+item+'\n');
f.close();

# Generate CPP File
print('Generating .cpp file');

f = open(dllname.replace('.dll','.cpp'),'w');
f.write('#include <windows.h>\n#include <stdio.h>\n');
f.write('HINSTANCE mHinst = 0, mHinstDLL = 0;\n');

if architecture == 'x64':  # For X64
	f.write('extern \"C\" ');

f.write('UINT_PTR mProcs['+str(len(LoadNames))+'] = {0};\n\n');
if use_default_directory or allow_chains: # @SP
	f.write('void LoadOriginalDll();\n');
if allow_chains:
	f.write('int InitSettings();\n\n');
else:
	f.write('\n');
f.write('LPCSTR mImportNames[] = {');
for idx, val in enumerate(LoadNames):
	if idx != 0:
		f.write(', ');
	f.write(val);
f.write('};\n');
f.write('BOOL WINAPI DllMain( HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved ) {\n');
f.write('\tmHinst = hinstDLL;\n');
f.write('\tif ( fdwReason == DLL_PROCESS_ATTACH ) {\n');

if use_default_directory: 	# @SP
	f.write('\t\tLoadOriginalDll();\n');
elif allow_chains:
	f.write('\t\tInitSettings();\n');
	f.write('\t\tif (!mHinstDLL)\n\t\t{\n');
	f.write('\t\t\t// No chain was loaded; get original DLL from system directory\n');
	f.write('\t\t\tLoadOriginalDll();\n\t\t}\n');
else:
	f.write('\t\tmHinstDLL = LoadLibrary( \"ori_'+dllname+'\" );\n');
if not use_default_directory:
	f.write('\t\tif ( !mHinstDLL )\n');
	f.write('\t\t\treturn ( FALSE );\n');
f.write('\t\tfor ( int i = 0; i < '+str(len(LoadNames))+'; i++ )\n');
f.write('\t\t\tmProcs[ i ] = (UINT_PTR)GetProcAddress( mHinstDLL, mImportNames[ i ] );\n');
f.write('\t} else if ( fdwReason == DLL_PROCESS_DETACH ) {\n');
f.write('\t\tFreeLibrary( mHinstDLL );\n');
f.write('\t}\n');
f.write('\treturn ( TRUE );\n');
f.write('}\n\n');

if architecture == 'x64':
	for item in WrapFcn:
		f.write('extern \"C\" void '+item+'();\n');
else:
	for idx, item in enumerate(WrapFcn):
		f.write('extern \"C\" __declspec(naked) void __stdcall '+item+'(){__asm{jmp mProcs['+str(idx)+'*4]}}\n');
if use_default_directory or allow_chains:
	# @SP: Write LoadOriginalDll() function, which loads the original DLL from the default directory (so the original doesn't need to be included)
	f.write('\n\n// Loads the original DLL from the default system directory\n');
	f.write('//\tFunction originally written by Michael Koch\n');
	f.write('void LoadOriginalDll()\n{\n');
	f.write('\tchar buffer[MAX_PATH];\n\n');
	f.write('\t// Get path to system dir and to '+dllname+'\n');
	f.write('\tGetSystemDirectory(buffer, MAX_PATH);\n\n');
	f.write('\t// Append DLL name\n');
	f.write('\tstrcat_s(buffer, \"\\\\'+dllname+'\");\n\n');
	f.write('\t// Try to load the system\'s '+dllname+', if pointer empty\n');
	f.write('\tif (!mHinstDLL) mHinstDLL = LoadLibrary(buffer);\n\n');
	f.write('\t// Debug\n\tif (!mHinstDLL)\n\t{\n');
	f.write('\t\tOutputDebugString(\"PROXYDLL: Original '+dllname+' not loaded ERROR ****\\r\\n\");\n');
	f.write('\t\tExitProcess(0); // Exit the hard way\n\t}\n}\n\n');
if allow_chains:
	# @SP: Write InitSettings() function, which loads the next wrapper DLL in the chain (if one exists)
	f.write('\n// Parses '+dllname.replace('.dll','.ini')+' for intialization settings\n');
	f.write('int InitSettings()\n{\n');
	f.write('\tchar dll_chain_buffer[128];\n\n\t// Check settings file for DLL chain\n');
	f.write('\tGetPrivateProfileString(\"'+dllname.replace('.dll','')+'\", "DLL_Chain", NULL, dll_chain_buffer, 128, \".\\\\'+dllname.replace('.dll','.ini')+'\");\n\n');
	f.write('\tif (dll_chain_buffer[0] != \'\\0\') // Found DLL_Chain entry in settings file\n\t{\n');
	f.write('\t\tmHinstDLL = LoadLibrary(dll_chain_buffer);\n');
	f.write('\t\tif (!mHinstDLL)\n\t\t{\n');
	f.write('\t\t\t// Failed to load next wrapper DLL\n');
	f.write('\t\t\tOutputDebugString(\"PROXYDLL: Failed to load chained DLL; loading original from system directory instead...\\r\\n\");\n');
	f.write('\t\t\treturn 2; // Return 2 if given DLL could not be loaded\n\t\t}\n\t}\n')
	f.write('\telse\n\t{\n');
	f.write('\t\tOutputDebugString(\"PROXYDLL: No DLL chain specified; loading original from system directory...\\r\\n\");\n');
	f.write('\t\treturn 1; // Return 1 if '+dllname.replace('.dll','.ini')+' or DLL_Chain entry could not be located\n\t}\n');
	f.write('\treturn 0; // Return 0 on success\n}\n\n');
f.close();

# @SP: Generate .ini file (if "-allowchains" was specified)
if allow_chains:
	print('Generating .ini file');
	f = open(dllname.replace('.dll','.ini'),'w');
	f.write('['+dllname.replace('.dll','')+']\n');
	f.write('DLL_Chain=\n\n');
	f.close();

# Generate ASM File
print('Generating .asm file');
if architecture == 'x86':
	print('x86 wrapper will use inline asm.');
else:
	f = open(dllname.replace('.dll','_asm.asm'),'w');
	f.write('.code\nextern mProcs:QWORD\n');
	for idx, item in enumerate(WrapFcn):
		f.write(item+' proc\n\tjmp mProcs['+str(idx)+'*8]\n'+item+' endp\n');
	f.write('end\n');
	f.close();
	
# Generate MS Visual Studio Project Files.

if os.path.exists(dllname.replace('.dll','')):
	shutil.rmtree(dllname.replace('.dll',''));
time.sleep(2);
os.mkdir(dllname.replace('.dll',''));
os.mkdir(dllname.replace('.dll','')+'\\'+dllname.replace('.dll',''));

# Generate x64
if architecture == 'x64':
	sln = open('Visual Studio Project Template\\x64\\MyName.sln','r');
	targetsln = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.sln','w');
	for line in sln:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetsln.write(line);
	targetsln.close();
	sln.close();
	
	prj = open('Visual Studio Project Template\\x64\\MyName\\MyName.vcxproj','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	prj = open('Visual Studio Project Template\\x64\\MyName\\MyName.vcxproj.filters','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj.filters','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	prj = open('Visual Studio Project Template\\x64\\MyName\\MyName.vcxproj.user','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj.user','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	shutil.copy('Visual Studio Project Template\\x64\\MyName.suo',dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.suo');
	
	shutil.move(dllname.replace('.dll','.cpp'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
	shutil.move(dllname.replace('.dll','.def'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
	shutil.move(dllname.replace('.dll','_asm.asm'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
	if allow_chains: # @SP: move the .ini file
		shutil.move(dllname.replace('.dll','.ini'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');

else:
	sln = open('Visual Studio Project Template\\x86\\MyName.sln','r');
	targetsln = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.sln','w');
	for line in sln:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetsln.write(line);
	targetsln.close();
	sln.close();
	
	prj = open('Visual Studio Project Template\\x86\\MyName\\MyName.vcxproj','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	prj = open('Visual Studio Project Template\\x86\\MyName\\MyName.vcxproj.filters','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj.filters','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	prj = open('Visual Studio Project Template\\x86\\MyName\\MyName.vcxproj.user','r');
	targetprj = open(dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.vcxproj.user','w');
	for line in prj:
		line = line.replace('MyName',dllname.replace('.dll',''));
		line = line.replace('MYNAME',dllname.replace('.dll','').upper());
		targetprj.write(line);
	targetprj.close();
	prj.close();
	
	shutil.copy('Visual Studio Project Template\\x86\\MyName.suo',dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'.suo');
	
	shutil.move(dllname.replace('.dll','.cpp'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
	shutil.move(dllname.replace('.dll','.def'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
	if allow_chains: # @SP: move the .ini file
		shutil.move(dllname.replace('.dll','.ini'),dllname.replace('.dll','')+'\\'+dllname.replace('.dll','')+'\\');
