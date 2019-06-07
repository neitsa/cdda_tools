cross_compile_clang

# Cross Compilation using clang-cl

The following step have been executed on a Linux Ubuntu 18.10 although any Linux distribution should be fine, as long as you have access to the following requirements:

* `llvm` 8.0.0+
* `Wine`
    - optional if you have access to a Windows partition where Visual Studio is installed.
    - `winetricks`: optional but allows easier installation of the .NET frameworks on wine.

## ToC

* [LLVM](#LLVM)



# LLVM

The cross compiler from LLVM, targeting Windows, is named `clang-cl`. It is technically a front-end loader for `clang`. The particularity of `clang-cl` is that it can use exactly the same flags as the Microsoft compiler and linker (respectively cl.exe and link.exe).

You can either use the one provided by your distribution, compile it from source, or use the provided binaries from the LLVM web site.

This documentation assumes that the llvm binaries are in your `$PATH`.

```bash
$ clang-cl --version
clang version 8.0.0 (tags/RELEASE_800/final)
Target: x86_64-pc-windows-msvc
Thread model: posix
InstalledDir: /opt/llvm/binaries
```

# Microsoft SDK

We will use the Windows 10 SDK (or newer) for compiling the code, but we'll only use the headers, not the binaries (i.e. the compiler or the linker) provided by the SDK.

Please note that it is totally possible to install any another version of the SDK.

There are multiple ways to do this:

- Install - using the SDK installer - the Windows SDK under wine.
- Have access to a Windows partition.
- Extract and install the relevant parts of the SDK by using wine.

We'll use the last option here, although you might want to try the other ones they haven't been tested.

Please note that if you want to install the Windows SDK by using its installer, you'll have to also install the .NET framework which is an adventure by itself.

## Installing Wine

To install the Windows SDK on Linux you'll need to install it on wine. The steps are as follows:

* Install wine
* Mount the SDK ISO file
* Installer some selected parts of the SDK on wine

### Wine Installation

Wine (Wine is not an emulator) probably comes already packaged for your distribution. You might also compile it from source are use the official Wine Personal Package Archive (ppa).

On Ubuntu it is as simple as:

```
$ sudo apt install wine
```

Once wine is installed don't forget to run, at least once, the wine configuration (you can just click `OK` on the new window):

```
$ winecfg
```

You might need to install `winbind` on some Linux if you see an error about NTLM while trying to run wine.


#### Installing Winetricks

Next you'll need to install `winetricks` which we'll use to install the .NET frameworks. This step is optional but avoids to fall into some problems while installing the .NET frameworks.

* [winetricks official repository](https://github.com/Winetricks/winetricks)
* [Winetricks documentation on Wine website](https://wiki.winehq.org/Winetricks)


On Ubuntu the script comes already packaged (although not necessarily up to date) so you can install it using `apt`:

```
$ sudo apt install winetricks
```

If you want the latest version you can just install it somewhere on your home directory for example:

```
$ mkdir -P ~/src/winetricks
$ cd ~/src/winetricks
$ wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
$ mv winetricks winetricks.sh
$ chmod +x winetricks.sh
```

The next commands show in this document use a script named `winetricks` available in the `$PATH`.

### Installing the .NET Frameworks

The Windows SDK won't install without having the .NET frameworks 2 **and** 4 already installed.

* [Link to .NET 2.0 installation on Wine website](https://appdb.winehq.org/objectManager.php?sClass=version&iId=3754)
* [Link to .NET 4.0 installation on Wine website](https://appdb.winehq.org/objectManager.php?sClass=version&iId=17886)

**Warning** Be wary into which wine prefix you are installing the .NET Frameworks (32 vs. 64-bit prefix). It will become relevant later when installing the SDK.
If you are confused about wine prefixes, please read the official documentation about them: https://wiki.winehq.org/FAQ#Wineprefixes .

The recommended way to install the .NET frameworks in wine is to put them on a 32-bit prefix. If you want to install in a 32-bit prefix while on a 64-bit Linux machine, then you need to prepend `WINEARCH=win32` to your command.

If you have installed `winetricks` the following command should be enough to install the .NET Framework 2.0 (here we are using a 32-bit prefix):

```
$ env WINEARCH=win32 WINEPREFIX=$HOME/.winedotnet winetricks dotnet20
```

And then the .NET Framework 4.0 (using a new prefix, as recommended per the documentation):

```
$ env WINEARCH=win32 WINEPREFIX=$HOME/.winedotnet winetricks dotnet40 corefonts
```

### Installing the Windows SDK

We'll now install the SDK in the wine prefix where we installed both of the .NET Frameworks. The ISO file for the Windows 7 SDK is technically called `Microsoft Windows SDK for Windows 7 and .NET Framework 4 (ISO)`. You can download it using the link below:

* [Microsoft Windows SDK for Windows 7 and .NET Framework 4 (ISO)](https://www.microsoft.com/en-us/download/details.aspx?id=8442)

It exists in 3 versions:

* x86 ISO File Name: GRMSDK_EN_DVD.iso 
* x64 ISO File Name: GRMSDKX_EN_DVD.iso 
* Itanium ISO File Name: GRMSDKIAI_EN_DVD.iso 

There are two possibilities:

* If you installed the .NET frameworks in a 32-bit prefix, use the x86 version.
* If you installed the .NET frameworks in a 64-bit prefix, use the x64 version.

Mount the ISO file; be wary that the ISO file is built using a UDF file system (ISO-13346) so you'll probably want to mount it as follow:

```
$ mount -o loop -t udf,iso9660 /path/to/image.iso /mnt/
```

You should now be able to access its content (example with the x86 version):

```
neitsa@thorondor:~$ ls -al /mnt
total 346
dr-xr-xr-x  3 nobody nogroup    364 mai   14  2010 .
drwxr-xr-x 26 root   root      4096 avril 17 21:06 ..
-r-xr-xr-x  1 nobody nogroup     27 avril 20  2010 Autorun.inf
-r-xr-xr-x  1 nobody nogroup 148026 mai   11  2010 ReleaseNotes.Htm
dr-xr-xr-x 29 nobody nogroup   2548 mai   14  2010 Setup
-r-xr-xr-x  1 nobody nogroup  73544 mai   14  2010 setup.exe
-r-xr-xr-x  1 nobody nogroup 121344 mai   14  2010 winsdk_dvdx86.msi
```

Now run the `setup.exe` file in wine (remove `WINEARCH=win32` if you are in a 64-bit prefix):

```
$ env WINEARCH=win32 WINEPREFIX=$HOME/.winedotnet wine /mnt/setup.exe
```

The SDK should now be available in your prefix. If you didn't change the installation path:

```
$ cd ~/.winedotnet/drive_c/Program\ Files/Microsoft\ SDKs/Windows/v7.1
$ 
```

#### Side  Notes

Be wary that the Windows SDK setup will create program menu entries on your Linux for the installed Windows programs.

You might want to disable this behavior by looking at the following link:

* [How can I prevent Wine from changing the filetype associations on my system or adding unwanted menu entries/desktop links?](https://wiki.winehq.org/FAQ#How_can_I_prevent_Wine_from_changing_the_filetype_associations_on_my_system_or_adding_unwanted_menu_entries.2Fdesktop_links.3F)


## Mount a Windows Partition

In case you already have a Windows partition with a Windows SDK installed, you just need to have access to that partition.
You'll need a way to have access to the Windows partition where the Windows SDK is installed and mount it through a convenient mount point on your Linux.

It is however not recommended to use a partition on a network share (e.g CIFS / Samba).

# Windows Includes

Be it on your wine prefix or a path to a mounted Windows partition, pay a particular attention to set the include path to a variable.

INC_SDK=~/.winedotnet/drive_c/Program\ Files/Microsoft\ SDKs/Windows/v7.1/Include
INC_VS=~/.winedotnet/drive_c/Program\ Files/Microsoft\ Visual Studio\10.0/VC/Include
LIB_SDK=~/.winedotnet/drive_c/Program\ Files/Microsoft\ SDKs/Windows/v7.1/Lib
LIB_VS=~/.winedotnet/drive_c/Program\ Files/Microsoft\ Visual\ Studio\ 10.0/VC/lib

[TODO] make distinction between VS path (c++ stuff) and include path (windows stuff)
[TODO] talk about the include paths

## Check if everything works

We'll create a dummy C++ program and see if we can compile it using `clang-cl` and the newly installed Windows SDK.

```
$ cd ~/src/_tests
$ cat hello_world.cpp
#include <iostream>

int main(void) 
{
    std::cout << "Hello world!" << std::endl;
    
    return 0;
}
```

## Compiler Flags

ciopfs "$INC_VS" /tmp/src/inc_vs
ciopfs "$INC_SDK" /tmp/src/inc_sdk/
clang-cl /c /W1 /EHsc /nologo /I /tmp/src/inc_vs /I /tmp/src/inc_sdk hello_world.cpp
lld-link  /SUBSYSTEM:CONSOLE /LIBPATH:"$LIB_SDK" /LIBPATH:"$LIB_VS" hello_world.obj

The most important compiler flag here is the `/I` flag, which instructs to clang-cl where to find the includes directories.

Be it on your wine prefix or a path to a mounted Windows partition, pay a particular attention to set the path to a variable.

INC_SDK=~/.winedotnet/drive_c/Program\ Files/Microsoft\ SDKs/Windows/v7.1/Include
INC_VS=~/.winedotnet/drive_c/Program\ Files/Microsoft\ Visual Studio\10.0/VC/Include

cl.exe /c /W4 /nologo /EHsc /I %INC_VS% /I %INC_SDK_SH% /I %INC_SDK_UM% prog.c








/nologo 
/Yu"stdafx.h" 
/MP 
/GS 
/W1 
/wd"4819" 
/wd"4146" 
/Gy 
/Zc:wchar_t 
/I"K:\cdda\Cataclysm-DDA\msvc-full-features\..\WinDepend\SDL2-2.0.9\include" 
/I"K:\cdda\Cataclysm-DDA\msvc-full-features\..\WinDepend\SDL2_ttf-2.0.14\include" 
/I"K:\cdda\Cataclysm-DDA\msvc-full-features\..\WinDepend\SDL2_mixer-2.0.4\include" 
/I"K:\cdda\Cataclysm-DDA\msvc-full-features\..\WinDepend\SDL2_image-2.0.4\include" 
/I"K:\cdda\Cataclysm-DDA\msvc-full-features\..\WinDepend\gettext\include" 
/Zi 
/Gm- 
/O2 
/sdl 
/Fd"x64\Release\Cataclysm_lib\Cataclysm_lib.pdb" 
/FI"stdafx.h" 
/Zc:inline 
/fp:precise 
/D "BACKTRACE" 
/D "SDL_BUILDING_LIBRARY" 
/D "_SCL_SECURE_NO_WARNINGS" 
/D "_CRT_SECURE_NO_WARNINGS" 
/D "WIN32_LEAN_AND_MEAN" 
/D "NDEBUG" 
/D "_WINDOWS" 
/D "SDL_SOUND" 
/D "TILES" 
/D "LOCALIZE" 
/D "_MBCS" 
/errorReport:prompt 
/WX- 
/Zc:forScope 
/Gd 
/Oi 
/MD 
/Fa"x64\Release\Cataclysm_lib\" 
/EHsc
/Fo"x64\Release\Cataclysm_lib\" 
/Fp"x64\Release\Cataclysm_lib\Cataclysm_lib.pch" 