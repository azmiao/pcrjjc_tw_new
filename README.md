
# 新版台服竞技场查询插件【pcrjjc_tw_new】

## 各版本区别

|                                 版本                                 |     说明     |           备注            | 
|:------------------------------------------------------------------:|:----------:|:-----------------------:|
|   [(当前) pcrjjc_tw_new](https://github.com/azmiao/pcrjjc_tw_new)    |   台服专用版    | 适配合服配置，并增加全局禁用推送功能和各种优化 | 
|         [pcrjjc3-tw](https://github.com/azmiao/pcrjjc3-tw)         |   台服专用版    |        额外支持多服查询         | 
| [pcrjjc_huannai](https://github.com/SonderXiaoming/pcrjjc_huannai) | pcrjjc2魔改版 |         各种优化和简化         |
|            [pcrjjc2](https://github.com/cc004/pcrjjc2)             | pcrjjc重制版  |      适配了各种服（包括台服）       | 
|          [pcrjjc](https://github.com/lulu666lulu/pcrjjc)           |    初始版本    |         梦开始的地方          |

## 台服合服后的适配说明

#### 已由【[AZMIAO](https://github.com/azmiao)】适配了【新版V2】账号配置文件的查询(2023-07-20更新后)

#### 感谢【[2佬](https://github.com/sdyxxjj123)】适配了【新版V1】账号配置文件的查询(2023-05-10更新后)

#### 感谢【[辣鱼佬](https://github.com/layvsan)】适配了【旧版】账号配置文件的查询

#### 感谢【[电线佬](https://github.com/CYDXDianXian)】提供了非常多的更新和优化以及图片设计

#### 本项目只是修改版非原作者，感谢各位用爱发电的各位大佬的鼎力相助

#### 感谢解包数据源 [priconne-diff](https://github.com/Expugn/priconne-diff)

## 本仓库的特性

> ✨增加全局禁用推送功能，不需要自动推送的直接关闭即可✨

> ✨优化查询逻辑，经测试极大地提高了多次查询的速度和稳定性✨

> ✨自动识别新版和旧版的账号配置文件，可以同时兼容查询✨

## 更新日志

2024-11-12  v1.2.3   减小不必要的定时查询开销，修改新增用户默认不推送，推送改为合并统一消息，规避下风控风险

2024-08-20  v1.2.2   修复获取解包资源失败的问题

2024-07-10  v1.2.1   详细查询深域部分，公主骑士等级采用解包数据进行计算，数据源自 [priconne-diff](https://github.com/Expugn/priconne-diff)

2024-06-24  v1.2.0   详细查询新增深域相关的查询图片，可见最下方图片预览，但公主骑士等级由于计算公式暂未解包，因此暂不可用

<details>
<summary>更以前的更新日志</summary>

2024-03-28  v1.1.2   由于谷歌页面经常变化，去除自动更新版本号，改为手动使用命令更新

2023-12-21  v1.1.1   修复自动更新版本号的BUG

2023-08-10  v1.1.0   适配游戏版本v4.0.2后的配置文件

2023-06-29  v1.0.0   优化查询逻辑

2023-06-19  v0.0.3-beta 简化代码，[PR #5](https://github.com/azmiao/pcrjjc_tw_new/pull/5)

2023-06-17  v0.0.2-beta 适配新版台服竞技场查询，感谢各位大佬

2023-05-10  v0.0.1-beta 测试版本

</details>

## 如何更新

一直摸兜里，直接`git pull`就完事了

## 使用方法

### 如果之前没用过pcrjjc3-tw

1. 拿个不用的号登录PCR，然后把data/data/tw.sonet.princessconnect/shared_prefs/tw.sonet.princessconnect.v2.playerprefs.xml复制到该目录

    注意：每个号至少得开启加好友功能，一服为"台服一服"，台服二三四服合服后视为一个"台服其他服"

2. 给你的`tw.sonet.princessconnect.v2.playerprefs.xml`加上前缀名，例如：
    ```
    台服一服：
    first_tw.sonet.princessconnect.v2.playerprefs.xml
    台服其他服：
    other_tw.sonet.princessconnect.v2.playerprefs.xml
    ```
    如果没有某个服的配置文件或者不需要该服就不用管，台服二三四服只需要一个即可，可以用电脑模拟器开游戏生成

3. 安装依赖：
    ```
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```
    
4. 配置account.json设置代理：localhost就行，只要改端口，自行更换和你代理软件代理的端口一样就行，是代理端口哦，不是软件监听端口，开PAC模式不改变系统代理就行

    注意：如果你不需要代理，请打开`account.json`并将里面改成`{"proxy":{}}`

5. 开启插件，并重启Hoshino即可食用

### 如果之前用过pcrjjc3-tw

1. 将原来`pcrjjc3-tw`插件目录下的`account.json`, `binds.json`, `frame.json` 复制过来，不要复制`headers.json`，不要复制`headers.json`，不要复制`headers.json`！

2. 将原来的`xxx_tw.sonet.princessconnect.v2.playerprefs.xml`的配置文件都复制过来，一服的文件改名`first_tw.sonet.princessconnect.v2.playerprefs.xml`，其他服的改名为`other_tw.sonet.princessconnect.v2.playerprefs.xml`

3. 在hoshino中禁用插件`pcrjjc3-tw`，并启用插件`pcrjjc_tw_new`，重启bot即可

## 重点注意

1. 和pcrjjc2一样，由于使用了不验证ssl的方式，因此可能产生ssl的验证warning [issue #7](https://github.com/azmiao/pcrjjc3-tw/issues/7)，可采用在hoshino文件夹下的`aiorequests.py`文件内加上几行：
    ```
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    ```
    来禁止该warning显示

2. 本插件现已支持每个群友自定义头像框，默认为彩色头像框（为[前川未来佬](https://github.com/shirakami-fubuki)从不知道什么鬼鬼地方使劲抠出来的彩框2333），其余rank框均为游戏解包抠出来的原图。

    如果你需要自己添加其他头像框也是没问题滴，直接把图片扔进本目录下的/img/frame/文件夹里即可，并且不用重启hoshino即可，大多数常见的图片格式一般都行，会自动转RGBA所以一般来说不用担心

3. 本插件现已支持自动更新版本号，妈妈再也不用担心我每次游戏版本更新时，都得手动改插件的版本号再重启hoshino了

4. 若运行过程中出现`TypeError: __init__() got an unexpected keyword argument 'strict_map_key'`报错，为依赖问题，请在终端中进行如下操作，一行一行依次复制执行，过程中提示是否卸载，选择Y：

   ```
   pip uninstall msgpack_python
   pip uninstall msgpack
   pip install msgpack~=1.0.2
   ```

5. 本插件主要适配新版hoshino，但也兼容了部分旧版hoshino，如遇问题请更新星乃本体，如果实在不方便更新可以提交issue反馈等待适配。

6. 不想要推送功能的，维护组可以直接使用命令全局禁用推送功能

## 命令

注：@BOT为@机器人

|         关键词          |               说明                |
|:--------------------:|:-------------------------------:|
|      竞技场绑定 uid       |             绑定竞技场信息             |
|       竞技场订阅状态        |             查看绑定状态              |
|       删除竞技场绑定        |             删除绑定的信息             |
|      竞技场查询 uid       |      查询竞技场简要信息（绑定后无需输入uid）      |
|       详细查询 uid       |      查询账号详细信息（绑定后无需输入uid）       |
|       启用竞技场订阅        |     启用战斗竞技场排名变动推送，全局推送启用时有效     |
|       停止竞技场订阅        |          停止战斗竞技场排名变动推送          |
|      启用公主竞技场订阅       |     启用公主竞技场排名变动推送，全局推送启用时有效     |
|      停止公主竞技场订阅       |          停止公主竞技场排名变动推送          |
|        竞技场历史         | 查询战斗竞技场变化记录（战斗竞技场订阅开启有效，可保留10条） |
|       公主竞技场历史        | 查询公主竞技场变化记录（公主竞技场订阅开启有效，可保留10条） |
|        查询头像框         |       查看自己设置的详细查询里的角色头像框        |
|        更换头像框         |        更换详细查询生成的头像框，默认彩色        |
|         查询群数         |           查询bot所在群的数目           |
|       查询竞技场订阅数       |           查询绑定账号的总数量            |
|       查询竞技场版本号       |          查询本插件当前支持的版本号          |
|    @BOT全局启用竞技场推送     |     启用所有群的竞技场排名推送功能(仅限维护组)      |
|    @BOT全局禁用竞技场推送     |         禁用所有推送功能(仅限维护组)         |
|     @BOT清空竞技场订阅      |        清空所有绑定的账号(仅限维护组)         |
| @BOT手动更新竞技场版本号 4.4.0 |       手动将版本号更新至某版本(仅限维护组)       |

## 详细查询图片预览

### 这里现在用的是我自己的号截图，主图和支援图是由[电线佬](https://github.com/CYDXDianXian)设计的代码，非常感谢！！！

<details>
<summary>点击查看图片</summary>

![主图](https://raw.githubusercontent.com/azmiao/pcrjjc_tw_new/main/readme_img/%E4%B8%BB%E5%9B%BE.PNG)

![支援图](https://raw.githubusercontent.com/azmiao/pcrjjc_tw_new/main/readme_img/%E6%94%AF%E6%8F%B4%E5%9B%BE.PNG)

![深域图](https://raw.githubusercontent.com/azmiao/pcrjjc_tw_new/main/readme_img/%E6%B7%B1%E5%9F%9F%E5%9B%BE.PNG)

</details>