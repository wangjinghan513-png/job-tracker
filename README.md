\# 求职进度管理系统



一个用于记录求职投递进度的个人练习项目。



\## 功能



\- 添加和查看投递记录

\- 修改投递状态

\- 删除投递记录

\- 按状态筛选记录

\- 显示各状态的记录数量

\- 使用 SQLite 保存数据



\## 技术



\- Python 和 FastAPI：提供后端接口

\- SQLite：保存记录

\- HTML、CSS 和 JavaScript：提供网页界面



\## 在 Windows 上运行



在项目文件夹中打开 PowerShell，依次执行：



```powershell

python -m venv .venv

.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt

.\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload

```



在浏览器中访问 http://127.0.0.1:8000/page。



接口文档：http://127.0.0.1:8000/docs。



数据库会在首次运行时创建。音乐文件不包含在仓库中；如需使用播放器，可将自己的 MP4 文件放在项目文件夹中并命名为 `music.mp4`。



\## 学习参考



\- \[FastAPI 全栈模板](https://github.com/fastapi/full-stack-fastapi-template)



这是参考相关技术自行搭建的学习项目，并非官方模板的完整复刻。







\## 运行测试



安装项目依赖后，在项目文件夹中执行：



```powershell

.\\.venv\\Scripts\\python.exe -m pytest test\_main.py -v

```



测试会使用临时数据库，不会修改自己的投递记录。



## 账号功能

项目支持注册、登录和退出登录。每位用户只能查看和操作自己的投递记录。

目前可以通过接口文档注册账号：

1. 运行项目，打开 http://127.0.0.1:8000/docs。
2. 使用 `POST /register` 注册。
3. 打开 http://127.0.0.1:8000/page，使用注册的账号登录。

## 运行全部测试

在项目文件夹中执行：

```powershell
.\.venv\Scripts\python.exe -m pytest test_main.py test_password.py test_isolation.py -v
```

测试使用临时数据库，不会修改自己的投递记录。

当前项目供本地学习使用；公开部署前还需要完善安全配置和部署方案。

