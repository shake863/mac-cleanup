# clean-zd

### A cleanup script for macOS

</br>

<details>
  <summary>
  What does script do?
  </summary>

</br>

* Empty the Trash on All Mounted Volumes and the Main HDD
* Clear System Log Files
* Clear Adobe Cache Files
* Cleanup iOS Applications
* Remove iOS Device Backups
* Cleanup Xcode Derived Data and Archives
* Reset iOS simulators
* Cleanup Homebrew Cache
* Cleanup Any Old Versions of Gems
* Cleanup Dangling Docker Images
* Purge Inactive Memory
* Cleanup pip cache
* Cleanup Pyenv-VirtualEnv Cache
* Cleanup npm Cache
* Cleanup Yarn Cache
* Cleanup Docker Images and Stopped Containers
* Cleanup CocoaPods Cache Files
* Cleanup composer cache
* Cleanup Dropbox cache
* Remove PhpStorm logs
* Remove Minecraft logs and cache
* Remove Steam logs and cache
* Remove Lunar Client logs and cache
* Remove Microsoft Teams logs and cache
* Remove Wget logs and hosts
* Removes Cacher logs
* Deletes Android caches
* Clears Gradle caches
* Deletes Kite logs
* Clears Go module cache
* Clears Poetry cache

</details>



## Install Automatically

### Using homebrew

> 需先自建 `shake863/homebrew-tap` 仓库后此方式才生效。

```bash
brew tap shake863/tap
brew install shake863/tap/clean-zd
```
<details>
  <summary>
  Error: SHA256 mismatch
  </summary>

> If you'll see ```Error: SHA256 mismatch``` try this:
> 1. Copy "Actual" hash from error
> 2. Run ```brew edit shake863/tap/clean-zd```
> 3. Press ```I``` and change ```sha256 "<some hash>"``` with hash from step 1
> 4. Press ```:```, then ```wq``` and ```Enter```
> 5. Re-run installation \
> ```brew install shake863/tap/clean-zd```

</details>


### Using curl

```bash
curl -fsSL https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh | bash -s install
```

### Using wget

```bash
wget https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh -O - | bash -s install
```

## Step by Step Install

1. Download: `curl -o clean-zd https://raw.githubusercontent.com/shake863/mac-cleanup/master/clean-zd`
2. Make it executable: `chmod +x clean-zd`
3. Move to make it globally usable: `sudo mv clean-zd /usr/local/bin/clean-zd`

## Update

### Using curl

```bash
curl -fsSL "https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh" | bash -s update
```

### Using wget

```bash
wget "https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh" -O - | bash -s update
```

## Uninstall

### Using curl

```bash
curl -fsSL "https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh" | bash -s uninstall
```

### Using wget

```bash
wget "https://raw.githubusercontent.com/shake863/mac-cleanup/master/installer.sh" -O - | bash -s uninstall
```

## Usage Options

Help menu:

```
$ clean-zd -h

A Mac Cleaning up Utility (clean-zd)
https://github.com/shake863/mac-cleanup

USAGE:
 clean-zd [FLAGS]

FLAGS:
-h, --help       Prints help menu
-d, --dry-run    Print approx space to be cleaned
-v, --verbose    Print script debug info
-u, --update     Run brew update
```

## Credits

本项目 fork 自 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh)，在其基础上做了个人定制（conda / pnpm / 腾讯会议缓存清理等）。感谢原作者及所有贡献者。
