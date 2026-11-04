[[技术项目.canvas]]

> 参考于 [GitHub 入门](【Git+Github核心概念大串讲，从零到一全攻略，详细实战教程-哔哩哔哩】 https://b23.tv/oSaZoTP) 

# Git 与 Github

## Git 入门

> 在熟练了之后，就可以用 AI 来帮你完成，你得先学会基本知识再去用 AI

git 与 github 的绑定：
~~~
把这个文件夹初始化成 git项目，并且推送到 github上面 
~~~
 
- 一个用与版本控制的系统
	- .git 来存放版本控制信息
	- commit 版本控制的基本单元，每次改动会生成一个快照
- 基本操作
	- git init:初始化
		- 在 VS code 里面选择 openfolder，打开文件夹，点击左侧的 source control，点第一个，就成功初始化了
	- .gitignore:不被 git 管理
		- 直接在那个文件里面写文件名
		- node 项目的 node_modules 文件夹，要添加进去要在文件夹后面添加一个 **/** 来表示这是一个目录
> 对于 AI：把这个目录进行 git 初始化，注意把不要的内容删除

---

- commit： VS code ——> 进入项目目录 -> 添加一个文件 fruits.txt（这里是个例子，在仓库里添加水果） -> 添加一些信息 -> 点击左侧的 source control 按钮 -> 有个 commit，输入是**提交摘要**（你做了什么事情）-> 修改错了，点击 source control里面文件右侧第二个的 discard change -> 回到上一次提交 -> 下面的 GRAPH 里面，可以看到每次提交的历史链路（这里面只能查看，不能更改，因为 detached：分离头指针，表示当前不处于任意分支的管理中，直接修改容易搞丢代码）-> 想要让仓库回到最新的状态，点击 GRAPH 里面左下角的按钮，点击 master，使仓库回到主干 -> 每次提交都有 ID ，鼠标指在某一次提交上面，在里面有一个数字加英文的小编号（这个就是 commit ID，是 git 通过 [哈希算法](https://www.cnblogs.com/duanxz/p/3506424.html) 算出来的）
> 把 commit ID粘贴给 AI ：
~~~
你把仓库还原到这次提交的状态，后面的改动都不要了
~~~
以下是底层命令
~~~
git reset --hard <commit ID>
~~~

> 如果只想撤回一次提交：

~~~
 把这一次提交撤销掉，（commit ID），保持其他不变
~~~

底层：生成一个反向提交，抵消历史操作
~~~
git revert <commit ID>
~~~
> 让 AI 给你编程的时候，每次更改功能点的时候就提交一个 commit

**后悔药**：

| git 操作 | discard           | reset           | revert                  |
| ------ | ----------------- | --------------- | ----------------------- |
| 行为     | 放弃还没提交的 commit 更改 | 把仓库强制退回到某次历史状态  | 生成反向 commit，抵消某次 commit |
| 场景     | 未提交               | 单人使用的分支还未提交远端仓库 | 多人协作的分支                 |


---

- branch: 存储库的不同开发线
	- 默认一个 main\master（主干分支） 
	- 创建分支是通过指针来实现的
	- 分支代码修改不会相互影响
	- 功能开发结束就可以合并 merge commit
		- VS code 点击左小角的 master 分支，点击 create new branch，命名
		- 合并之后一般要删除，但是 git 不允许删除当前分支，需要先切换到其他分支
	- 也可以基于任意一次提交建立分支
		- GRAPH 里面右键点击 create branch
合并分支
~~~
git merge
~~~

- 仓库回退到历史状态：
	- checkout（detached），分离头指针，最好不修改，容易丢失
	- 基于某个历史提交创建分支
- HEAD：当前仓库处于那一次 commit上
	- 如果一直在一个 commit 上可能是处于 detached 的状态

---

- WorkTree：本质上就是用 git 创建一个新的分支，然后将这个新分支的代码完整的复制一份到新的文件夹里（这个文件夹就是一个 worktree）
	- （存疑）一个另存编辑的模式

> 可用 Claude --worktree 分支名字编辑
> 合并也可直接说

- conflict：两个分支修改了同一行文件的同一行代码，git 无法自动确认保留哪一个改动，需要人工决定保留那一段代码，代码上叫解决冲突，操作比较繁琐

> 去搜不用 AI 怎么解决冲突

---

- Git Areas（分区）
	- working directory（工作区）：电脑磁盘的本地文件夹
		- git add + git commit：本地工作区的改动提交到本地目录
	- local repository（本地仓库）：commit之后的改动就保存在这里
		- git push：将本地仓库的改动推送到远端仓库
	- remote repository（远程仓库）：一般我们用 github
		- git clone：远端仓库保存到本地，同时创建出本地存储库和本地工作目录（远程仓库）->  （工作区）
		- git pull：将远端存储库的最新改动更新并且合并到本地（git fetch + git merge）
	- staging/index（暂存区）：commit之前的一个检查点
		- git add 将工作区文件保存到暂存区，之后用 git commit 将暂存区的所有改动提交到本地仓库

- 实战

## Github 入门