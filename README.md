# hirunner-backend

## 安装部署说明  
本代码未完全调试完，请自行调试，并变化对应的配置内容
### 下载代码，并安装依赖
部分依赖模块写在requirements.txt中，并不完全，请自行调试并安装

### 初始化建库并导入初始化表和数据
建库: hirunner
初始化表和数据sql文件：deploy/dump-hirunner-init.sql


### 安装或配置jenkins  
安装步骤略，请自行百度  
配置:  
1.新建一个pipeline流水线，名称为hirunner_run_python_job  
2.新建字符参数NODE，默认值为node-19.168.1.9(请自行根据情况变化,需要自行新建jenkins节点，并配置默认并行任务数来增加并发量)  
3.新建字符参数GIT_REPOSITORY，默认值为你的git主工程地址  
4.新建字符参数GIT_NAME，默认值为你的git主工程的git名称，如hitest  
5.新建字符参数GIT_BRANCH，默认为你的git主工程的master分支  
6.新建字符参数RUNNER_DIR，默认为你的默认运行节点的D:/jenkins/hirunner/1/  
7.新建字符参数GIT_PULL,默认值为true  
8.新建字符参数SRC_DIR,默认值为D:/jenkins/hirunner/1/hitest  
9.新建字符参数RUN_CMD,默认值为python3 run_test.py  
10.新建文本参数EXECUTE_INFO,默认值为{"execute_id":"0"}  
11.在高级项目选项中的流水线，定义选择Pipeline script  
   脚本内容填写为  deploy/hirunner_run_python_job.pipeline


### redis(可选)
略，请自行百度  

### 运行django并调试
python3 manage.py runserver 0.0.0.0:8000

### api接口文档使用
访问：http://localhost:8000/swagger/  
用户密码：admin/qa123456

### gunicorn托管  
详细步骤请百度，提供django应用程序的：gunicorn_conf配置文件，后端代码部署开机启动的gunicorn.service文件、jenkins agent的开机启动管理hirunneragent.service文件
