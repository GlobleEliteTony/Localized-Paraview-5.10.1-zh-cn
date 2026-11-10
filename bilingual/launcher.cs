using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Security.Cryptography;
using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Windows.Forms;
class BilingualLauncher {
 static bool IsAscii(string s){foreach(char c in s)if(c>127)return false;return true;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
 static extern SafeFileHandle CreateFile(string path,uint access,uint share,IntPtr sec,uint mode,uint flags,IntPtr template);
 [DllImport("kernel32.dll",SetLastError=true)]
 static extern bool DeviceIoControl(SafeFileHandle h,uint code,byte[] input,int size,IntPtr output,int outputSize,out int returned,IntPtr overlapped);
 static string CaseAlias(string foam,string root) {
  if(IsAscii(foam))return foam;
  string target=Path.GetDirectoryName(foam);
  if(IsAscii(target))return Path.Combine(target,"paraview-zh.foam");
  string aliases=Path.Combine(root,"case-paths");
  if(!IsAscii(aliases))aliases=Path.Combine(Path.GetTempPath(),"ParaViewBilingualCasePaths");
  byte[] hash;using(SHA256 sha=SHA256.Create())hash=sha.ComputeHash(Encoding.Unicode.GetBytes(target.ToUpperInvariant()));
  string key=BitConverter.ToString(hash).Replace("-","");
  Directory.CreateDirectory(aliases);string alias=Path.Combine(aliases,key);
  if(!Directory.Exists(alias)) {
   Directory.CreateDirectory(alias);
   byte[] sub=Encoding.Unicode.GetBytes("\\??\\"+target),display=Encoding.Unicode.GetBytes(target);
   byte[] buffer;
   using(MemoryStream ms=new MemoryStream())using(BinaryWriter b=new BinaryWriter(ms)){
    b.Write((uint)0xA0000003);b.Write((ushort)(8+sub.Length+2+display.Length+2));b.Write((ushort)0);
    b.Write((ushort)0);b.Write((ushort)sub.Length);b.Write((ushort)(sub.Length+2));b.Write((ushort)display.Length);
    b.Write(sub);b.Write((ushort)0);b.Write(display);b.Write((ushort)0);buffer=ms.ToArray();
   }
   using(SafeFileHandle h=CreateFile(alias,0x40000000,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero)){
    int returned;
    if(h.IsInvalid||!DeviceIoControl(h,0x000900A4,buffer,buffer.Length,IntPtr.Zero,0,out returned,IntPtr.Zero)){
     int error=Marshal.GetLastWin32Error();Directory.Delete(alias);throw new System.ComponentModel.Win32Exception(error,"Cannot create OpenFOAM path alias");
    }
   }
   File.WriteAllText(Path.Combine(aliases,key+".source.txt"),target,new UTF8Encoding(false));
  }
  return Path.Combine(alias,"paraview-zh.foam");
 }

 static string Quote(string s) {
  StringBuilder b=new StringBuilder("\""); int slashes=0;
  foreach(char c in s) { if(c=='\\'){slashes++;continue;} if(c=='"'){b.Append('\\',slashes*2+1);b.Append(c);}else{b.Append('\\',slashes);b.Append(c);}slashes=0; }
  b.Append('\\',slashes*2);b.Append('"');return b.ToString();
 }
 [STAThread] static int Main(string[] args) {
  try {
   string bin=AppDomain.CurrentDomain.BaseDirectory;
   string root=Path.Combine(Path.GetDirectoryName(bin.TrimEnd(Path.DirectorySeparatorChar)),"bilingual");
   string core=Path.Combine(bin,"paraview-core.exe");
   if(!File.Exists(core)||!File.Exists(Path.Combine(root,"bilingual.py")))throw new FileNotFoundException("Bilingual runtime or original executable is missing.");
   StringBuilder command=new StringBuilder(); string userScript=null; string foam=null; string bootstrap=null;
   for(int i=0;i<args.Length;i++) {
    string a=args[i];
    if(a.StartsWith("--script=")){userScript=a.Substring(9);continue;}
    if(a=="--script"&&i+1<args.Length){userScript=args[++i];continue;}
    if(a.StartsWith("--data=") && a.Substring(7).EndsWith(".foam",StringComparison.OrdinalIgnoreCase)){foam=Path.GetFullPath(a.Substring(7));continue;}
    if(a=="--data" && i+1<args.Length && args[i+1].EndsWith(".foam",StringComparison.OrdinalIgnoreCase)){foam=Path.GetFullPath(args[++i]);continue;}
    if(a.EndsWith(".foam",StringComparison.OrdinalIgnoreCase)&&File.Exists(a)){foam=Path.GetFullPath(a);continue;}
    command.Append(Quote(a)).Append(' ');
   }
   string scriptPath=Path.Combine(root,"bilingual.py");
   bool ascii=true;foreach(char c in scriptPath)if(c>127)ascii=false;
   if(!ascii){bootstrap=Path.Combine(Path.GetTempPath(),"paraview-zh-"+Guid.NewGuid().ToString("N")+".py");File.WriteAllText(bootstrap,"import os\n_p=os.path.join(os.environ['PARAVIEW_BILINGUAL_ROOT'],'bilingual.py')\nexec(compile(open(_p,encoding='utf-8-sig').read(),_p,'exec'),globals(),globals())\n",new UTF8Encoding(false));scriptPath=bootstrap;}
   command.Append(Quote("--script="+scriptPath));
   ProcessStartInfo info=new ProcessStartInfo(core,command.ToString());
   info.UseShellExecute=false;
   info.WorkingDirectory=Environment.CurrentDirectory;
   info.EnvironmentVariables["PARAVIEW_BILINGUAL_ROOT"]=root;
   info.EnvironmentVariables["PARAVIEW_BILINGUAL_FOAM_ORIGINAL"]=foam??"";
   info.EnvironmentVariables["PARAVIEW_BILINGUAL_FOAM"]=foam==null?"":CaseAlias(foam,root);
   info.EnvironmentVariables["PARAVIEW_BILINGUAL_BIN"]=bin;
   info.EnvironmentVariables["PARAVIEW_BILINGUAL_USER_SCRIPT"]=userScript==null?"":Path.GetFullPath(userScript);
   using(Process p=Process.Start(info)){p.WaitForExit();if(bootstrap!=null)try{File.Delete(bootstrap);}catch{}return p.ExitCode;}
  } catch(Exception e){MessageBox.Show(e.Message,"ParaView bilingual launcher",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
 }
}
