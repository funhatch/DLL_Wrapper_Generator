# DLL Wrapper Generator  

  
## Description  
Automatically generates DLL wrappers for 32-bit and 64-bit DLLs.  
  
## Usage  
  
```
python Generate_Wrapper.py DLLname.dll [-usesysdir | -allowchains]  

	-usesysdir	Generated DLL will check the system default directory
			for the original DLL, rather than checking the local
			directory for "ori_$(DLLname).dll"  
      
	-allowchains	Generated DLL will parse "$(DLLname).ini" for a
			"DLL_Chain=" entry containing the name of a local DLL
			to load. This allows multiple DLL wrappers to be loaded
			for the same DLL. If no entry is found, generated DLL
			checks the system default directory for the original DLL.  
```  


## Authors  
 * **Lin "MavenLin" Min** - Original author  - [GitHub](https://github.com/mavenlin)  
 * **Sean Pesce** - Extended functionality - [Website](https://SeanPesce.github.io) | [GitHub](https://github.com/SeanPesce)  
   
  
## Original Source  
https://github.com/mavenlin/Dll_Wrapper_Gen  
  
